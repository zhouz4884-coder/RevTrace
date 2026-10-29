from pathlib import Path
import ast,hashlib,json,shutil,subprocess,sys,platform
H=Path(__file__).resolve().parent;R=H.parents[1];OLD=R/'experiments/dsn_streamcorrect_adaptation_20261028/final_native_v8_evidence';S=H/'source_v1';S.mkdir(exist_ok=False)
for n in ('analyze_content.py','test_content.py'):shutil.copyfile(H/n,S/n)
(S/'PROTOCOL.md').write_text((H/'PLAN_DEFINITION.zh.md').read_text(encoding='utf8'),encoding='utf8',newline='\n')
(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8');(S/'.gitattributes').write_text('* -text\n',encoding='utf8')
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
subprocess.run(['git','-C',str(S),'init'],check=True,capture_output=True);git('config','core.autocrlf','false');git('checkout','-b','codex/native-content-endpoints-v1');git('add','.');git('commit','-m','Freeze read-only original14 text events and LCP occurrence endpoints')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=dict(code_commit=git('rev-parse','HEAD'),scope='Independent standard-library CPU content endpoints; no changes to measured native source or original primary credit',files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()])
with (H/'SOURCE_v1.json').open('x',encoding='utf8') as f:json.dump(m,f,indent=2);f.write('\n')
git('bundle','create',str(H/'SOURCE_v1.bundle'),'HEAD')
plan=json.loads((OLD/'NATIVE_CAMPAIGN_v8_FROZEN.json').read_text(encoding='utf8'));primary=json.loads((OLD/'native_postanalyses_v8/primary_quantiles/SUMMARY.json').read_text(encoding='utf8'));records={r['cell_id']:r for r in primary['cells']}
assert len(plan['cells'])==len(records)==14
cells=[]
for c in plan['cells']:
 r=records[c['cell_id']];cells.append(dict(cell_id=c['cell_id'],stage=c['stage'],cohort=c['cohort'],arm=c['arm'],repeat=c['repeat'],path=c['out'],
    expected=r['raw_inputs'],offered_frontiers=r['offered_frontiers'],offered_audio_seconds=r['offered_audio_seconds'],original_dual_credit_audio_seconds=r['dual_deadline_audio_credit_seconds']))
cfg=dict(experiment_id='REVTRACE-NATIVE-OLD14-CONTENT-ENDPOINTS-20261029-V1',measured_neural_commit=plan['source_commit'],cells=cells,
    max_input_bytes=16000000,max_output_bytes=32000000,source_plan_sha256=sha(OLD/'NATIVE_CAMPAIGN_v8_FROZEN.json'),
    upstream_primary_recount_sha256=sha(OLD/'native_postanalyses_v8/primary_quantiles/SUMMARY.json'),
    raw_normalization='identity',secondary_normalization='remove Unicode whitespace only; preserve case, punctuation and all other codepoints',
    endpoint_identity='LCP suffix occurrence (cell,source,mode,actual row version,offset); no token/audio alignment or semantic-correctness claim',
    original_D2_C8='unchanged',original_credit='must match every original14 cell',new_model_calls=0,
    output='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_content_20261029/analysis_v1')
with (H/'CONFIG_v1.json').open('x',encoding='utf8') as f:json.dump(cfg,f,indent=2);f.write('\n')
D=H/'CPU_CONTROLS_v1';D.mkdir();control=dict(experiment_id=cfg['experiment_id']+'-CPU-CONTROLS',source_commit=m['code_commit'],test='test_content.py',new_model_calls=0)
for name,v in [('CONFIG',control),('ENVIRONMENT',dict(python=sys.version,platform=platform.platform())),('RUN_RECORD',dict(experiment_id=control['experiment_id'],code_commit=m['code_commit'],source_manifest_sha256=sha(H/'SOURCE_v1.json'),frozen_config_sha256=hashlib.sha256(json.dumps(control,sort_keys=True).encode()).hexdigest(),raw_result_location=str(D/'RAW.log'),aggregate_summary_location=str(D/'SUMMARY.json'),gate_decision_location=str(D/'GATE.json')))]:
 with (D/(name+'.json')).open('x',encoding='utf8') as f:json.dump(v,f,indent=2);f.write('\n')
with (D/'RAW.log').open('x',encoding='utf8') as f:p=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_content'],cwd=S,stdout=f,stderr=subprocess.STDOUT)
with (D/'SUMMARY.json').open('x',encoding='utf8') as f:json.dump(dict(returncode=p.returncode,registered_controls=8,new_model_calls=0),f,indent=2);f.write('\n')
with (D/'GATE.json').open('x',encoding='utf8') as f:json.dump(dict(gate='PASS_EIGHT_CPU_CONTENT_CONTROLS' if p.returncode==0 else 'FAIL_PRESERVED',new_model_calls=0),f,indent=2);f.write('\n')
assert p.returncode==0 and not git('status','--porcelain','--untracked-files=all')
print(json.dumps(dict(source_commit=m['code_commit'],manifest_sha256=sha(H/'SOURCE_v1.json'),config_sha256=sha(H/'CONFIG_v1.json'),controls=8,new_model_calls=0)))
