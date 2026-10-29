"""Correct offline empty-display expectation; preserve v8 execution/source/gate.

The corrected audit never changes the actual Consumer, model, selections,
service metrics or offered denominators. Any continuation invokes unchanged
v8 native_service with the original frozen v8 cell/config/source identities.
"""
import argparse,pathlib,json,hashlib,subprocess,sys,datetime,os,shutil,time,traceback
from native_audit import audit_cell,audit_campaign
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text())
def put(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def record(out,plan,manifest,mode):
    commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip();m=read(manifest)
    assert commit==m['source_commit'] and not subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True)
    for row in m['files']:
        b=(R/row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
    out.mkdir(parents=True,exist_ok=False);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,scope='CPU audit/controller only; native child retains separate frozen v8 environment'))
    put(out/'CONFIG.json',dict(mode=mode,frozen_native_plan=str(plan),frozen_native_plan_sha256=sha(plan),native_execution_source=read(plan)['source_commit'],audit_controller_source=commit))
    put(out/'RUN_RECORD.json',dict(experiment_id='SC_NATIVE_EMPTY_DISPLAY_AUDITFIX_V1_'+mode.upper(),code_commit=commit,native_execution_source=read(plan)['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return commit
def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['recount','continue'],required=True);p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--witness-recount',type=pathlib.Path);a=p.parse_args()
    assert sha(a.plan)=='b3b8d5612ae3adc9faee5332514184d6fc2471eebcc4a5154db8acff07e35e47';commit=record(a.out,a.plan,a.manifest,a.mode);plan=read(a.plan);completed=[]
    try:
        if a.mode=='recount':
            original=[]
            for cell in plan['cells'][:2]:
                first=audit_cell(cell['out']);second=audit_cell(cell['out']);assert first==second
                original.append(dict(cell_id=cell['cell_id'],native_execution_source=plan['source_commit'],audit=first));put(a.out/(cell['cell_id']+'_AUDIT.json'),first)
            source=pathlib.Path(plan['cells'][1]['out']);rows=[json.loads(x) for x in (source/'consumer.jsonl').read_text().splitlines()]
            empty=next(i for i,x in enumerate(rows) if x['private_job'] is not None and not x['text']);controls=[]
            for name in ['empty_forged_progress','private_text_mutation','foreign_canonical_parent']:
                target=a.out/('fixture_'+name);shutil.copytree(source,target);mutated=[dict(x) for x in rows]
                if name=='empty_forged_progress':mutated[empty]['visible_frontier']=16000
                elif name=='private_text_mutation':mutated[empty]['text']='forged'
                else:
                    sid=rows[empty]['source_id'];foreign=next(x['canonical_sha'] for x in rows if x['source_id']!=sid);mutated[empty]['canonical_sha']=foreign
                (target/'consumer.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in mutated))
                try:audit_cell(target);raise AssertionError('forged fixture accepted')
                except ValueError as e:controls.append(dict(fixture=name,rejected=True,reason=str(e)))
            audits=[x['audit'] for x in original];changed=sum(x['nonempty_corrected_interleavings'] for x in audits);same=sum(x['nonempty_unchanged_interleavings'] for x in audits)
            witness=dict(status='PASS_NATURAL_NONEMPTY_CORRECTED_AND_UNCHANGED_INTERLEAVINGS' if changed and same else 'NO_NATURAL_BOTH_TYPE_NONEMPTY_INTERLEAVING_IN_FIXED_FOUR_SOURCES',corrected_interleavings=changed,unchanged_interleavings=same,all_corrected_updates=sum(x['corrected_updates'] for x in audits),all_unchanged_updates=sum(x['unchanged_updates'] for x in audits),sources=[s for x in audits for s in x['source_ids']])
            put(a.out/'WITNESS_GATE.json',witness);put(a.out/'SUMMARY.json',dict(status='PASS_CORRECTIVE_OFFLINE_WITNESS_RECOUNT',native_execution_source=plan['source_commit'],corrective_audit_source=commit,original_controller_failure_preserved=True,repeat_exact=True,controls=controls,witness_gate=witness,cells=original));put(a.out/'GATE.json',dict(status='PASS_CORRECTIVE_OFFLINE_WITNESS_RECOUNT'));return
        assert a.witness_recount and read(a.witness_recount/'GATE.json')['status']=='PASS_CORRECTIVE_OFFLINE_WITNESS_RECOUNT'
        assert read(a.witness_recount/'WITNESS_GATE.json')['status']=='PASS_NATURAL_NONEMPTY_CORRECTED_AND_UNCHANGED_INTERLEAVINGS'
        execution=pathlib.Path(plan['runtime_source']);execution_manifest=pathlib.Path(plan['source_manifest'])
        assert plan['source_commit']=='61c9afac00561f7ff1351f3eba9fd95adb239e8c'
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
        for cell in plan['cells'][2:]:assert not pathlib.Path(cell['out']).exists(),'formal output already exists; never rerun under same frozen identity'
        for cell in plan['cells'][2:]:
            command=[sys.executable,'-B',str(execution/'native_service.py'),'--config',cell['config'],'--source-manifest',str(execution_manifest),'--out',cell['out']]
            with (a.out/(cell['cell_id']+'.log')).open('x') as f:child=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);put(a.out/'ACTIVE_CHILD.json',dict(cell_id=cell['cell_id'],pid=child.pid));rc=child.wait()
            assert rc==0,'actual v8 formal native cell failed and remains preserved'
            value=audit_cell(cell['out']);completed.append(dict(cell_id=cell['cell_id'],audit=value));put(a.out/'PROGRESS.json',dict(completed=completed,remaining=12-len(completed)))
            for _ in range(30):
                apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
                if not apps:break
                time.sleep(.2)
            assert not apps,'previous native GPU context still present'
        result=audit_campaign(plan);put(a.out/'SUMMARY.json',result);put(a.out/'GATE.json',dict(status=result['status']))
    except BaseException:
        (a.out/'failure.txt').write_text(traceback.format_exc());put(a.out/'SUMMARY.json',dict(completed=completed));put(a.out/'GATE.json',dict(status='FAIL_AUDITFIX_OPERATION_PRESERVED'));raise
if __name__=='__main__':main()
