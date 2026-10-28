"""CPU-only parser, fail-closed ownership, clock and fairness controls.

No GPU, no real signal, no remote process. Real GPU study is still unexecuted.
"""
from pathlib import Path
from types import SimpleNamespace
import copy
import hashlib
import json
import struct
import tempfile
import unittest
from unittest.mock import patch

import paired_recovery_controller as c
import paired_recovery_audit as audit
try:
    from revtrace.recovery_fault import parse_post_sync_target,target_in_synced_group
except ModuleNotFoundError:
    # Temporary review package before parent integration into runtime/src.
    from revtrace.recovery_fault import parse_post_sync_target,target_in_synced_group


def put(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x),encoding='utf8')


def jsonl(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps(y)+'\n' for y in x),encoding='utf8')


def framed(p,records):
    previous='';out=b''
    for i,row in enumerate(records):
        body=json.dumps(dict(row,sequence=i,previous_sha256=previous),sort_keys=True,separators=(',',':')).encode()
        digest=hashlib.sha256(body).digest();out+=struct.pack('>I',len(body))+body+digest;previous=digest.hex()
    p.write_bytes(out)


def identities():
    owner=dict(pid=100,pgid=100,parent_pid=90,state='S',linux_start_ticks='200',command_sha256='a')
    workers=[dict(pid=101,pgid=100,parent_pid=100,state='S',linux_start_ticks='201',command_sha256='b',name='proposal-0'),
             dict(pid=102,pgid=100,parent_pid=100,state='S',linux_start_ticks='202',command_sha256='c',name='authority-1')]
    tracker=dict(pid=103,pgid=100,parent_pid=100,state='S',linux_start_ticks='203',command_sha256='d')
    return owner,workers,[owner,*workers,tracker]


class Ownership(unittest.TestCase):
    def test_accept_exact_owned_group(self):
        o,w,s=identities();self.assertEqual(len(c.validate_group(o,w,s)),4)
    def test_pid_reuse_failclosed(self):
        o,w,s=identities();s=copy.deepcopy(s);s[1]['linux_start_ticks']='999'
        with self.assertRaises(RuntimeError):c.validate_group(o,w,s)
    def test_command_change_failclosed(self):
        o,w,s=identities();s=copy.deepcopy(s);s[2]['command_sha256']='evil'
        with self.assertRaises(RuntimeError):c.validate_group(o,w,s)
    def test_foreign_pgid_member_failclosed(self):
        o,w,s=identities();s.append(dict(pid=104,pgid=100,parent_pid=1,state='S',linux_start_ticks='300',command_sha256='e'))
        with self.assertRaises(RuntimeError):c.validate_group(o,w,s)
    def test_missing_worker_failclosed(self):
        o,w,s=identities()
        with self.assertRaises(KeyError):c.validate_group(o,w,s[:2])
    def test_dead_worker_failclosed(self):
        o,w,s=identities();s=copy.deepcopy(s);s[1]['state']='Z'
        with self.assertRaises(RuntimeError):c.validate_group(o,w,s)
    def test_wrong_worker_set_failclosed(self):
        o,w,s=identities();w=copy.deepcopy(w);w[0]['name']='foreign'
        with self.assertRaises(RuntimeError):c.validate_group(o,w,s)
    def test_parse_stat_with_parentheses(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'123';p.mkdir()
            fields=['S','90','123','123','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','991']
            (p/'stat').write_text('123 (strange)name) '+' '.join(fields));(p/'cmdline').write_bytes(b'python\0worker\0')
            result=c.proc_identity(123,Path(td));self.assertEqual(result['linux_start_ticks'],'991');self.assertEqual(result['pgid'],123)


class FaultAndPair(unittest.TestCase):
    def test_target_exact_interval(self):
        target=parse_post_sync_target('0:192000')
        row=dict(session_id=0,event=dict(event='canonical-segment-committed',audio_end_sample=192000))
        self.assertTrue(target_in_synced_group([row],target))
        self.assertFalse(target_in_synced_group([row],(0,96000)))
        self.assertFalse(target_in_synced_group([row],(1,192000)))
    def test_bad_target_rejected(self):
        for value in ('-1:2','0:0','0:192000:0','x:192000','0:-1'):
            with self.subTest(value=value),self.assertRaises(ValueError):parse_post_sync_target(value)
    def test_balanced_plan(self):
        plan=c.cells(3)
        self.assertEqual(len(plan),12)
        for rep in range(3):
            subset=[r for r in plan if r['repeat']==rep]
            self.assertEqual({(r['method'],r['restart_startup_order']) for r in subset},set((m,s) for m in c.METHODS for s in c.MODES))
            self.assertTrue(all(r['prefix_startup_order']=='full_first' and r['processor_mode']=='reuse' for r in subset))
    def test_prefix_same_restart_intervention(self):
        a=SimpleNamespace(model=Path('/model'),sessions=4,runtime_timeout=240,render_descriptor=Path('/descriptor'),render_descriptor_sha256='a'*64,fault_target='0:192000')
        D=Path('/D');E=Path('/D/cell');source={'code_commit':'b'*40}
        cell=dict(restart_startup_order='descriptor_workers_first')
        p=c.command(source,a,D,E,cell,0);r=c.command(source,a,D,E,cell,1)
        self.assertEqual(p[p.index('--startup-order')+1],'full_first')
        self.assertEqual(r[r.index('--startup-order')+1],'descriptor_workers_first')
        self.assertIn('--pause-post-sync-target',p);self.assertNotIn('--pause-post-sync-target',r)
        for flag in ('--episode-context','--input-journal-path','--durable-journal-path','--envelope-config','--arrival-schedule','--max-new-tokens','--microbatch'):
            self.assertEqual(p[p.index(flag)+1],r[r.index(flag)+1])
    def test_unmatched_cut_never_paired(self):
        rows=[dict(cell=dict(method='dgft_original',repeat=0,restart_startup_order=mode),fault_cut_sha256=str(i),recovery={}) for i,mode in enumerate(c.MODES)]
        r=c.paired_rows(rows)[0]
        self.assertFalse(r['exact_fault_cut_match']);self.assertNotIn('paired_seconds_difference_overlap_minus_full',r)
    def test_matched_cut_null_debt_preserved(self):
        rows=[dict(cell=dict(method='dgft_original',repeat=0,restart_startup_order=mode),fault_cut_sha256='same',recovery=dict(
            RTO_old_all_durable_facts=10-i,RTO_new_first_certified_fact=20-i,RTO_precrash_accepted_debt=None)) for i,mode in enumerate(c.MODES)]
        r=c.paired_rows(rows)[0]['paired_seconds_difference_overlap_minus_full']
        self.assertEqual(r['RTO_new_first_certified_fact'],-1);self.assertIsNone(r['RTO_precrash_accepted_debt'])


class DurableFrames(unittest.TestCase):
    def test_checksum_rejects_complete_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'wal';framed(p,[dict(kind='genesis')]);data=bytearray(p.read_bytes());data[-1]^=1;p.write_bytes(data)
            with self.assertRaises(AssertionError):audit.frames(p,True)
    def test_partial_tail_never_invented_frame(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'wal';framed(p,[dict(kind='genesis')]);p.write_bytes(p.read_bytes()+b'\0\0')
            records,tail=audit.frames(p,True);self.assertEqual((len(records),tail),(1,2))
            with self.assertRaises(AssertionError):audit.frames(p,False)
    def test_wrong_chain_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'wal';framed(p,[dict(kind='genesis')]);body=json.dumps(dict(kind='commit',sequence=1,previous_sha256='bad')).encode()
            p.write_bytes(p.read_bytes()+struct.pack('>I',len(body))+body+hashlib.sha256(body).digest())
            with self.assertRaises(AssertionError):audit.frames(p)
    def test_same_input_different_model_fact_unmatched(self):
        with tempfile.TemporaryDirectory() as td:
            E=Path(td);gen=dict(kind='genesis',states={'0':dict(audio_frontier_window=0,prompt_tokens=[],checkpoint_id=0)})
            row=dict(kind='commit',session_id=0,transaction_id='0:0:192000',parent_checkpoint_id=0,
                state_delta=dict(audio_start_sample=0,audio_end_sample=192000,segment_tokens=[1],next_prompt_tokens=[2]),
                event=dict(checkpoint_id=1,committed_text='hello'))
            framed(E/'canonical.wal.pre-recovery',[gen,row]);framed(E/'input.wal.pre-recovery',[dict(kind='envelope-snapshot',snapshot=dict(sessions={'0':dict(accepted=200000,rejected=False)}))])
            marker=dict(durable_frontiers={'0':192000},transactions=['0:0:192000'])
            first=c.logical_cut(E,marker);row['state_delta']['next_prompt_tokens']=[9]
            framed(E/'canonical.wal.pre-recovery',[gen,row]);second=c.logical_cut(E,marker)
            self.assertNotEqual(first['exact_logical_cut_sha256'],second['exact_logical_cut_sha256'])


class ConsumerClocks(unittest.TestCase):
    def test_applied_old_text_must_match_wal_fact(self):
        state=dict(F=32000,version=1,P=(2,));canonical={(0,'t'):dict(event=dict(checkpoint_id=1,committed_text='trusted'),
            state_delta=dict(audio_end_sample=32000,next_prompt_tokens=[2],segment_tokens=[1]))}
        row=dict(session_id=0,certified_transaction='t',certified_frontier=32000,canonical_version=1,certified_text='trusted',
            certified_text_sha256=hashlib.sha256(b'trusted').hexdigest(),certified_P_sha256=audit.tokens([2]),certified_Z_sha256=audit.tokens([1]))
        audit.check_certified_view(row,state,canonical)
        row['certified_text']='untrusted cached display'
        with self.assertRaises(AssertionError):audit.check_certified_view(row,state,canonical)
    def test_old_fact_projection_sha_cannot_be_relabelled(self):
        state=dict(F=32000,version=1,P=(2,));canonical={(0,'t'):dict(event=dict(checkpoint_id=1,committed_text='trusted'),
            state_delta=dict(audio_end_sample=32000,next_prompt_tokens=[2],segment_tokens=[1]))}
        row=dict(session_id=0,certified_transaction='t',certified_frontier=32000,canonical_version=1,certified_text='trusted',
            certified_text_sha256=hashlib.sha256(b'trusted').hexdigest(),certified_P_sha256=audit.tokens([9]),certified_Z_sha256=audit.tokens([1]))
        with self.assertRaises(AssertionError):audit.check_certified_view(row,state,canonical)
    def fixture(self,E,accepted=32000):
        put(E/'KILL.json',dict(kill_perf=100.))
        put(E/'attempt1/initial_states.json',[dict(session_id=0,state=dict(audio_frontier_window=16000))])
        framed(E/'input.wal.pre-recovery',[dict(kind='envelope-snapshot',snapshot=dict(sessions={'0':dict(accepted=accepted)}))])
        put(E/'attempt1/EXECUTORS_READY.json',dict(observed_perf=118.))
        jsonl(E/'attempt1/consumer.jsonl',[
            dict(session_id=0,certified_frontier=16000,observed_perf=110.),
            dict(session_id=0,certified_frontier=24000,observed_perf=120.),
            dict(session_id=0,certified_frontier=32000,observed_perf=130.),
            dict(session_id=0,certified_frontier=64000,observed_perf=150.)])
    def test_old_new_debt_distinct_not_eof(self):
        with tempfile.TemporaryDirectory() as td:
            E=Path(td);self.fixture(E);r=audit.recovery_clocks(E)
            self.assertEqual((r['RTO_old_all_durable_facts'],r['RTO_new_first_certified_fact'],r['RTO_precrash_accepted_debt']),(10,20,30))
            self.assertTrue(r['old_facts_applied_before_workers_ready'])
    def test_no_debt_is_na_not_zero(self):
        with tempfile.TemporaryDirectory() as td:
            E=Path(td);self.fixture(E,16000);r=audit.recovery_clocks(E)
            self.assertIsNone(r['RTO_precrash_accepted_debt']);self.assertTrue(r['no_precrash_debt_is_not_zero_rto'])
    def test_durable_view_not_fresh_work(self):
        with tempfile.TemporaryDirectory() as td:
            E=Path(td);self.fixture(E,16000)
            jsonl(E/'attempt1/consumer.jsonl',[dict(session_id=0,certified_frontier=16000,observed_perf=110.)])
            r=audit.recovery_clocks(E);self.assertEqual(r['RTO_old_all_durable_facts'],10);self.assertIsNone(r['RTO_new_first_certified_fact'])
    def test_false_debt_clear_fails(self):
        with tempfile.TemporaryDirectory() as td:
            E=Path(td);self.fixture(E,32000)
            jsonl(E/'attempt1/consumer.jsonl',[dict(session_id=0,certified_frontier=16000,observed_perf=110.)])
            with self.assertRaises(ValueError):audit.recovery_clocks(E)


def test_renderer_plan_declares_backend_not_fake_startup_order():
    from paired_recovery_controller import render_program_cells
    plan=render_program_cells(1)
    assert len(plan)==4
    assert {(c['method'],c['restart_owner_render_backend']) for c in plan}=={(m,b) for m in ['dgft_original','standard_fair'] for b in ['native','light']}
    assert all(c['restart_startup_order']=='descriptor_workers_first' and c['prefix_owner_render_backend']=='native' for c in plan)


if __name__=='__main__':
    unittest.main()
