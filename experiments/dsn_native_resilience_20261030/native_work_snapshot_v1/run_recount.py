"""Frozen no-model batch of literal selected-record/strict recovery observations."""
import argparse,datetime,hashlib,json,os,pathlib,platform,subprocess,sys
from native_work import selected_record_counts,post_fault_clock_audit
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def put(p,x):pathlib.Path(p).write_bytes((json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def identity(source,manifest):
 source=pathlib.Path(source);m=read(manifest);git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
 assert git('rev-parse','HEAD')==m['source_commit'] and not git('status','--porcelain','--untracked-files=all');assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
 for r in m['files']:assert (source/r['path']).stat().st_size==r['bytes'] and sha(source/r['path'])==r['sha256']
 return m['source_commit']
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();cfg=read(a.config);source=pathlib.Path(__file__).resolve().parent;commit=identity(source,a.manifest);assert cfg['code_commit']==commit
 assert len(cfg['cells'])==len({c['cell_id'] for c in cfg['cells']})==cfg['expected_cells']
 nn=pathlib.Path(cfg['runtime_source']);assert identity(nn,cfg['runtime_manifest'])==cfg['runtime_source_commit'];sys.path.insert(0,str(nn));from resilience_storage import scan
 out=a.out;out.mkdir();put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0));put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(a.config),config_sha256=sha(a.config),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=[c['out'] for c in cfg['cells']],aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),new_model_calls=0,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 results=[]
 for cell in cfg['cells']:
  root=pathlib.Path(cell['out']);config=read(root/'CONFIG.json');summary=read(root/'SUMMARY.json');assert config['source_commit']==summary['source_commit']==cfg['runtime_source_commit'];paths=[root/'CONFIG.json',root/'SUMMARY.json',root/'facts.wal',root/'consumer.jsonl'];inputs={str(p):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in paths};facts={obj['sequence']:obj['body'] for obj,_ in scan(root/'facts.wal',repair_tail=False) if obj['kind']=='canonical'};counts=selected_record_counts(body['record'] for body in facts.values());assert counts['canonical_selected_steps']==summary['integrity']['expected_canonical_steps'];rows=[json.loads(x) for x in (root/'consumer.jsonl').read_bytes().splitlines() if x.strip()]
  condition=config.get('fault',{}).get('kind','none');applicable=condition not in ('none','duplicate_late');audits=[post_fault_clock_audit(rows,facts,event) for event in summary['recovery']['events']] if applicable else []
  result=dict(cell_id=config['cell_id'],arm=config['arm'],condition=condition,source_commit=cfg['runtime_source_commit'],canonical_selected_record_counts=counts,strict_recovery_clock_applicable=applicable,strict_recovery_clock_audits=audits,inputs=inputs,new_model_calls=0);put(out/(config['cell_id']+'.json'),result);results.append(result)
  for path,r in inputs.items():assert pathlib.Path(path).stat().st_size==r['bytes'] and sha(path)==r['sha256']
 checks=[a for r in results for a in r['strict_recovery_clock_audits']];summary=dict(status='PASS_COMPLETE_LITERAL_NATIVE_RECORD_COUNTS_AND_STRICT_CLOCK_AUDIT',code_commit=commit,actual_neural_source_commit=cfg['runtime_source_commit'],cells=len(results),selected_canonical_steps=sum(r['canonical_selected_record_counts']['canonical_selected_steps'] for r in results),kill_fault_cells=sum(r['strict_recovery_clock_applicable'] for r in results),clock_events=len(checks),original_chosen_strict_true=sum(a['original_selected_strict_verified'] is True for a in checks),original_chosen_strict_false=sum(a['original_selected_strict_verified'] is False for a in checks),original_chosen_strict_unknown=sum(a['original_selected_strict_verified'] is None for a in checks),strict_post_fault_actual_endpoint_found=sum(a['strict_first_actual_consume'] is not None for a in checks),new_model_calls=0,results=results,scope='Literal selected-Canonical observations and independent strict post-fault consumption endpoints. Original reported clock is retained, false/unknown is not silently repaired. Marker is not a decoder/kernel-forward probe and selected-call seconds are not total paid work.')
 put(out/'SUMMARY.json',summary);put(out/'GATE.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='results'}))
if __name__=='__main__':main()
