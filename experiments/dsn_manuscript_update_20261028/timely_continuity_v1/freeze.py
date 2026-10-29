"""Freeze bounded read-only analysis; this script never executes a neural model."""
import hashlib,json,subprocess
from pathlib import Path
F=Path(__file__).resolve().parent
R=F.parents[2]
S=F/'source_v1'
def git(*args,cwd=S):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def h(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
if not (S/'.git').exists():
    git('init','-b','codex/timely-continuity-v1')
    git('config','core.autocrlf','false')
    git('add','.');git('commit','-m','Freeze timely-delivery continuity secondary analysis and CPU controls')
commit=git('rev-parse','HEAD')
files=[dict(path=p,**h(S/p)) for p in git('ls-files').splitlines()]
write(F/'SOURCE_v1.json',dict(code_commit=commit,files=files))
git('bundle','create',str(F/'SOURCE_v1.bundle'),'--all')
git('fetch',str(F/'SOURCE_v1.bundle'),'HEAD:refs/heads/codex/timely-continuity-v1',cwd=R)
P=R/'experiments/dsn_service_stability_20261028'
plan=json.loads((P/'PLAN_v1.json').read_text(encoding='utf8'))
record=json.loads((P/'RESULTS_v1/aggregate/ANALYSIS_RECORD.json').read_text(encoding='utf8'))
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
op=B+'/results/revtrace/physical_retirement_20261028/dsn_service_stability_analysis_v1/opportunities/UPDATES.json'
inputs={op:h(P/'RESULTS_v1/opportunities/UPDATES.json')}
cells=[]
for c in plan['cells']:
    argv=c.get('argv',[])
    raw=argv[argv.index('--out')+1] if '--out' in argv else c['output']
    for rel in ['attempt0/consumer.jsonl','audit/FRONTIERS.json']:
        path=raw+'/'+rel;inputs[path]=record['inputs'][path]
    cells.append(dict(raw_path=raw,meta={k:c[k] for k in ['cell_id','arm','cohort','arrival','repeat','sessions','paired_block']}))
out=B+'/results/revtrace/dsn_timely_continuity_20261029/v1'
write(F/'CONFIG_v1.json',dict(experiment_id='REVTRACE-DSN-TIMELY-CONTINUITY-20261029-V1',
    status='FROZEN_BEFORE_SECONDARY_RECOUNT',analysis_source_commit=commit,
    source_manifest_sha256=h(F/'SOURCE_v1.json')['sha256'],
    measured_neural_commit=plan['code_commit'],parent_plan_sha256=h(P/'PLAN_v1.json')['sha256'],
    definitions='source_v1/PROTOCOL.md',primary_first_credit_unchanged=True,
    output=out,summary=out+'/SUMMARY.json',gate=out+'/GATE.json',
    environment=out+'/ENVIRONMENT.json',raw_result_location=[c['raw_path'] for c in cells],
    CPU_controls='six frozen synthetic controls; no neural calls',opportunities=op,cells=cells,input_files=inputs))
write(F/'FREEZE_RECEIPT_v1.json',dict(analysis_source_commit=commit,source_manifest=h(F/'SOURCE_v1.json'),
    frozen_config=h(F/'CONFIG_v1.json'),input_files=len(inputs),input_bytes=sum(x['bytes'] for x in inputs.values()),
    experiment_id='REVTRACE-DSN-TIMELY-CONTINUITY-20261029-V1',next='Run six CPU controls then all 36 read-only recount on designated disk'))
print(json.dumps(dict(commit=commit,input_files=len(inputs),input_bytes=sum(x['bytes'] for x in inputs.values()))))
