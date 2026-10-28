"""Focused CPU controls: provenance, honest measurement and owned-child cleanup.

No model or GPU is loaded. The complete orchestration fixtures explicitly mock
GPU discovery, board power, runner execution and independent neural audit.
"""
import copy
import hashlib
import json
import signal
import subprocess
import sys
import types
from pathlib import Path

import pytest

import retirement_service as service


def source_fixture(tmp_path, monkeypatch):
    root=tmp_path/'source';root.mkdir()
    rows=[]
    for name in service.REQUIRED_SOURCES:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(name.encode())
        rows.append(dict(path=name,sha256=service.file_sha(path),bytes=path.stat().st_size))
    manifest=tmp_path/'SOURCE.json';source=dict(code_commit='a'*40,files=rows)
    manifest.write_text(json.dumps(source))
    replies={('rev-parse','--show-toplevel'):str(root),('cat-file','-t','a'*40):'commit',
      ('rev-parse','HEAD'):'a'*40,('config','--get','core.autocrlf'):'false',
      ('status','--porcelain','--untracked-files=all'):'',
      ('ls-files','-z'):'\x00'.join(row['path'] for row in rows)+'\x00'}
    monkeypatch.setattr(service,'git',lambda base,*args:replies[args])
    return root,manifest,source,replies


def test_source_manifest_requires_complete_clean_resolvable_execution_commit(tmp_path,monkeypatch):
    root,manifest,source,replies=source_fixture(tmp_path,monkeypatch)
    identity=service.verify_source(manifest,root)
    assert identity['full_commit_resolvable'] and identity['git_clean']
    assert identity['files_verified']==len(service.REQUIRED_SOURCES)
    replies[('status','--porcelain','--untracked-files=all')]='?? later.py'
    with pytest.raises(ValueError,match='dirty'):
        service.verify_source(manifest,root)
    replies[('status','--porcelain','--untracked-files=all')]=''
    replies[('rev-parse','HEAD')]='b'*40
    with pytest.raises(ValueError,match='equal checkout HEAD'):
        service.verify_source(manifest,root)


def test_source_byte_and_full_file_inventory_mismatches_fail_closed(tmp_path,monkeypatch):
    root,manifest,source,replies=source_fixture(tmp_path,monkeypatch)
    first=root/source['files'][0]['path'];first.write_bytes(b'changed')
    with pytest.raises(ValueError,match='source bytes changed'):
        service.verify_source(manifest,root)
    first.write_bytes(source['files'][0]['path'].encode())
    source['files'].pop();manifest.write_text(json.dumps(source))
    with pytest.raises(ValueError,match='tracked file sets differ'):
        service.verify_source(manifest,root)


def audio_manifest(tmp_path):
    rows=[]
    for i in range(3):
        path=tmp_path/f'{i}.wav';path.write_bytes(bytes([i]))
        rows.append(dict(source_id=f'source-{i}',path=str(path),audio_sha256=str(i)*64,
                         duration=10.+i,language='English'))
    return dict(sessions=rows,status='FROZEN_METADATA_ORDER')


def test_metadata_prefix_preserves_full_audio_and_refuses_duplicate_sources(tmp_path):
    raw=audio_manifest(tmp_path);before=copy.deepcopy(raw)
    result=service.selected_manifest(raw,2,disk=tmp_path)
    assert result['sessions']==raw['sessions'][:2] and raw==before
    assert result['sessions'][1]['duration']==11.
    raw['sessions'][1]['audio_sha256']=raw['sessions'][0]['audio_sha256']
    with pytest.raises(ValueError,match='duplication'):
        service.selected_manifest(raw,2,disk=tmp_path)
    with pytest.raises(ValueError,match='independent session count'):
        service.selected_manifest(before,4,disk=tmp_path)


def options(tmp_path,**updates):
    model=tmp_path/'models'/'qwen';model.mkdir(parents=True,exist_ok=True)
    argv=['--out',str(tmp_path/'results/revtrace/physical_retirement_20261028/cell'),
          '--source-manifest',str(tmp_path/'SOURCE.json'),'--manifest',str(tmp_path/'INPUT.json'),
          '--model',str(model),'--policy','covered','--method','standard_fair','--sessions','2']
    a=service.parser().parse_args(argv)
    for key,value in updates.items():setattr(a,key,value)
    return a


def test_full_service_command_shares_selection_kernel_input_consumer_and_deadlines(tmp_path):
    a=options(tmp_path,fixture=tmp_path/'fixture.json',retain='no',rho=3)
    command=service.build_command(a,a.out,dict(code_commit='a'*40),root=tmp_path/'source')
    for flag in ['--protocol-kernel','--trusted-text-binding','--capture-model-inputs',
                 '--disable-private-retention','--input-journal-path','--durable-journal-path']:
        assert flag in command
    assert command[command.index('--study-authority-rho')+1]=='3'
    assert command[command.index('--physical-retirement')+1]=='covered'
    assert command[command.index('--kernel-copy-mode')+1]=='event-cow'
    assert command[command.index('--consumer-policy')+1]=='two_lane'
    assert command[command.index('--result-delivery')+1]=='row'
    assert command[command.index('--retirement-fault-fixture')+1]==str(a.out/'fixture.json')
    assert not any('ces-' in arg or 'dispatch-wait' in arg or 'prefix-executor' in arg for arg in command)
    assert '--online-study-method' not in command


def test_whisper_confirmation_uses_declared_context_policy_and_no_cancel(tmp_path):
    a=options(tmp_path,adapter='whisper',policy='row_complete')
    service.validate_options(a,disk=tmp_path,root=tmp_path/'source')
    command=service.build_command(a,a.out,dict(code_commit='a'*40))
    assert command[command.index('--whisper-context-policy')+1]=='reserve-generation-tail-v1'
    a.policy='causal'
    with pytest.raises(ValueError,match='Whisper confirmation'):
        service.validate_options(a,disk=tmp_path,root=tmp_path/'source')


def test_power_measures_both_declared_gpus_and_requires_real_bracketing():
    rows=[dict(observed_perf=t,GPUs={0:dict(watts=10.+t),1:dict(watts=20.+t),2:dict(watts=999.)}) for t in [0.,1.,2.]]
    # GPU0+GPU1 sum is 30+2t: integral over [0.5,1.5] is 32 J.
    assert service.integrate_power(rows,.5,1.5)==pytest.approx(32.)
    with pytest.raises(ValueError,match='bracket'):
        service.integrate_power(rows,-.1,1.5)
    with pytest.raises(ValueError,match='positive actual'):
        service.integrate_power(rows,1.,1.)
    rows[1]['observed_perf']=0.
    with pytest.raises(ValueError,match='nonmonotone'):
        service.integrate_power(rows,.5,1.5)


def test_existing_gpu_work_stops_before_launch_without_termination(monkeypatch):
    monkeypatch.setattr(service.subprocess,'check_output',lambda *args,**kwargs:'421, GPU-owned-by-other, 1234 MiB')
    with pytest.raises(RuntimeError,match='no child launched'):
        service.require_idle()


def test_timeout_terminates_only_the_created_isolated_process_group(tmp_path,monkeypatch):
    class Child:
        pid=41721
        rc=None
        waits=0
        def poll(self):return self.rc
        def wait(self,timeout):
            self.waits+=1
            if self.waits==1:raise subprocess.TimeoutExpired('exact-child',timeout)
            self.rc=-15;return self.rc
    child=Child();launches=[];signals=[]
    def popen(command,**kwargs):launches.append((command,kwargs));return child
    identity=dict(pid=child.pid,parent_pid=1,process_group=child.pid,session=child.pid,linux_start_ticks='100',state='S')
    monkeypatch.setattr(service.subprocess,'Popen',popen)
    monkeypatch.setattr(service,'process_identity',lambda pid:dict(identity))
    monkeypatch.setattr(service.os,'killpg',lambda pid,sig:signals.append((pid,sig)),raising=False)
    with pytest.raises(TimeoutError,match='offered work retained'):
        service.run_child(['frozen-runner'],tmp_path,.1)
    assert launches[0][1]['start_new_session'] is True
    assert signals==[(child.pid,signal.SIGTERM)]
    assert json.loads((tmp_path/'OWNED_RUNNER.json').read_text())['linux_start_ticks']=='100'


def test_pid_reuse_or_nonisolated_group_is_never_signalled(monkeypatch):
    child=types.SimpleNamespace(pid=42,poll=lambda:None)
    old=dict(pid=42,process_group=42,session=42,linux_start_ticks='7')
    monkeypatch.setattr(service,'process_identity',lambda pid:dict(old,linux_start_ticks='8'))
    monkeypatch.setattr(service.os,'killpg',lambda *args:pytest.fail('foreign signal'),raising=False)
    with pytest.raises(RuntimeError,match='changed owned process'):
        service.terminate_owned(child,old)


def orchestration_fixture(tmp_path,monkeypatch,*,defer=False,rc=0):
    a=options(tmp_path)
    source_path=tmp_path/'SOURCE.json';source_path.write_text('{}')
    input_path=tmp_path/'INPUT.json';input_path.write_text(json.dumps(audio_manifest(tmp_path)))
    original_validate=service.validate_options
    original_select=service.selected_manifest
    monkeypatch.setattr(service,'validate_options',lambda args:original_validate(args,disk=tmp_path,root=tmp_path/'source'))
    monkeypatch.setattr(service,'selected_manifest',lambda raw,n:original_select(raw,n,disk=tmp_path))
    identity=dict(code_commit='a'*40,source_manifest_sha256=service.file_sha(source_path),files_verified=42)
    monkeypatch.setattr(service,'verify_source',lambda path:dict(identity))
    monkeypatch.setattr(service,'collect_environment',lambda *args:dict(packages={'torch':'CPU-MOCK'},not_gpu_evidence=True))
    monkeypatch.setattr(service,'require_idle',lambda:None)
    class Power:
        rows=[{},{}]
        def __init__(self,path):path.write_text('MOCK_CPU_ONLY')
        def joules(self,start,end):return end-start
        def close(self):pass
    monkeypatch.setattr(service,'DualPower',Power)
    def child(command,episode,timeout):
        record=service.read(episode/'RUN_RECORD.json')
        assert record['frozen_config_sha256']==service.file_sha(Path(record['frozen_config']))
        assert record['environment_record_sha256']==service.file_sha(Path(record['environment_record']))
        assert record['command_record_sha256']==service.file_sha(Path(record['command_record']))
        assert service.read(episode/'envelope.json')['method']=='standard_fair'
        raw=episode/'attempt0';raw.mkdir()
        service.put(raw/'power_samples.json',dict(measurement_start_perf=101.,measurement_end_perf=102.))
        (raw/'RAW_RETAINED.txt').write_text('CPU MOCK ONLY')
        return dict(returncode=rc,launch_perf=100.,exit_perf=103.,pid=4242)
    monkeypatch.setattr(service,'run_child',child)
    calls=[]
    def audit(episode,manifest):
        calls.append(episode)
        assert len(manifest['sessions'])==2
        return dict(status='PASS_CPU_MOCK_NOT_GPU',service={}),{'FRONTIERS':[]}
    def write_tables(path,summary,tables):
        path.mkdir();service.put(path/'SUMMARY.json',summary)
    monkeypatch.setitem(sys.modules,'retirement_audit',types.SimpleNamespace(audit_episode=audit,write_tables=write_tables))
    argv=['--out',str(a.out),'--source-manifest',str(source_path),'--manifest',str(input_path),
          '--model',str(a.model),'--policy','covered','--method','standard_fair','--sessions','2']
    if defer:argv.append('--defer-audit')
    return a,argv,calls


def test_complete_cell_freezes_before_child_and_runs_audit_after_real_exit_fixture(tmp_path,monkeypatch):
    a,argv,calls=orchestration_fixture(tmp_path,monkeypatch)
    summary=service.main(argv)
    assert len(calls)==1 and summary['status']=='COMPLETE_SINGLE_CELL_AND_INDEPENDENT_AUDIT'
    assert service.read(a.out/'GATE.json')['performance_superiority']=='REQUIRES_CROSS_ARM_COMPARISON'
    assert (a.out/'audit/SUMMARY.json').exists()
    freeze=service.read(a.out/'FREEZE.json')['frozen_config']
    assert freeze['display_slo_seconds']==2. and freeze['commit_slo_seconds']==8.
    assert freeze['policy']=='covered' and freeze['method']=='standard_fair'


def test_deferred_smoke_cannot_be_labelled_a_completed_audited_experiment(tmp_path,monkeypatch):
    a,argv,calls=orchestration_fixture(tmp_path,monkeypatch,defer=True)
    summary=service.main(argv)
    assert not calls and summary['evidence_complete'] is False
    assert service.read(a.out/'GATE.json')['gate']=='INCOMPLETE_AUDIT_DEFERRED'
    assert not (a.out/'INDEPENDENT_SUMMARY.json').exists()


def test_failed_child_preserves_raw_and_denies_success_without_retry(tmp_path,monkeypatch):
    a,argv,calls=orchestration_fixture(tmp_path,monkeypatch,rc=19)
    with pytest.raises(RuntimeError,match='rc=19'):
        service.main(argv)
    assert not calls and (a.out/'attempt0/RAW_RETAINED.txt').exists()
    assert service.read(a.out/'STOP.json')['runner']['returncode']==19
    assert service.read(a.out/'GATE.json')['gate']=='NO_GO_SINGLE_CELL_FAILURE_PRESERVED'
    assert not (a.out/'SUMMARY.json').exists()
