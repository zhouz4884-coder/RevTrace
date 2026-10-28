import copy,hashlib,json,subprocess
from pathlib import Path
T=Path(__file__).resolve().parents[1];R=T.parents[1];P=T/'packages';D=T/'confirmation_design'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf8') as f:json.dump(v,f,indent=2);f.write('\n')
M=P/'SOURCE_v3.json';commit=json.loads(M.read_text())['code_commit']
current=R/'experiments/repository_identity_20261027/CURRENT.json';v=json.loads(current.read_text());put(T/'CURRENT_BEFORE_v3.json',v)
v.update(source_worktree=str(T/'source_v3'),source_commit=commit,source_manifest=str(M),source_manifest_sha256=sha(M),previous_pointer=str(T/'CURRENT_BEFORE_v3.json'))
current.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
subprocess.run(['python',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(T/'SOURCE_GATE_v3.json')],check=True)
reports=[]
for old_name,new_name in [('PLAN.json','PLAN_v3.json'),('DEV_PREFLIGHT_PLAN_v2.json','DEV_PREFLIGHT_PLAN_v3.json')]:
 old_path=D/old_name;old=json.loads(old_path.read_text());new=copy.deepcopy(old)
 new.update(code_commit=commit,source_manifest_sha256=sha(M),experiment_id=old['experiment_id']+'-AUDITV3',
  source_identity_replacement=dict(previous_plan_sha256=sha(old_path),previous_code_commit=old['code_commit'],
    reason='Only independent auditor handling of proved empty pre-arrival epoch views changed; no runtime/model/data/factor/load/outcome selection change',
    runtime_byte_identity_record=str(P/'RUNTIME_BYTE_IDENTITY_v2_v3.json')))
 for k,val in list(new.items()):
  if isinstance(val,str):new[k]=val.replace('/source_v2','/source_v3').replace('/SOURCE_v2.json','/SOURCE_v3.json').replace('/confirmation_v2','/confirmation_v3').replace('/confirmation_dev_v2','/confirmation_dev_v3')
 for c in new['cells']:
  c['output']=c['output'].replace('/confirmation_v2/','/confirmation_v3/').replace('/confirmation_dev_v2/','/confirmation_dev_v3/')
  c['argv']=[x.replace('/source_v2/','/source_v3/').replace('/SOURCE_v2.json','/SOURCE_v3.json').replace('/confirmation_v2/','/confirmation_v3/').replace('/confirmation_dev_v2/','/confirmation_dev_v3/') for x in c['argv']]
 for a,b in zip(old['cells'],new['cells']):
  assert {k:v for k,v in a.items() if k not in ['argv','output']}=={k:v for k,v in b.items() if k not in ['argv','output']}
 target=D/new_name;put(target,new);reports.append(dict(plan=new_name,sha256=sha(target),cells=len(new['cells'])))
print(json.dumps(reports,indent=2))
