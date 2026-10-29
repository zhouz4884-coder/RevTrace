from pathlib import Path
import ast,hashlib,json,shutil,subprocess
H=Path(__file__).resolve().parent;R=H.parents[1];S=H/'source_v1';S.mkdir(exist_ok=False)
shutil.copyfile(H/'case.py',S/'case.py');shutil.copyfile(R/'experiments/dsn_service_stability_20261028/trace_illustration_v1/source_v2/interaction_opportunities_v1.py',S/'interaction_opportunities_v1.py')
(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8');(S/'.gitattributes').write_text('* -text\n',encoding='utf8')
(S/'PROTOCOL.md').write_text('Post-hoc explanatory single-arm actual full2s non-EOS interval case from completed c16-staggered repeat0 R1S0 source3570. Reuse only already-downloaded source7 Consumer/events/complete worker records and original timely witness. Show original clock relative to F14 ready, full input compatibility at new rootF12, actual LCP changes, D2 missing read and exact later recovered text. No Joint counterfactual, no token/audio alignment, no new primary outcome, no change to original36/48 denominators or negative c12 strong decision.\n',encoding='utf8')
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
subprocess.run(['git','-C',str(S),'init'],check=True,capture_output=True);git('config','core.autocrlf','false');git('checkout','-b','codex/timely-full-interval-case-v1');git('add','.');git('commit','-m','Freeze single-arm actual timely full-interval content withdrawal case')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=dict(code_commit=git('rev-parse','HEAD'),scope='Pure local case explanation and publication artwork, not new service/primary evidence',files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()])
with (H/'SOURCE_v1.json').open('x',encoding='utf8',newline='\n') as f:json.dump(m,f,indent=2);f.write('\n')
git('bundle','create',str(H/'SOURCE_v1.bundle'),'HEAD')
P=R/'experiments/dsn_service_stability_20261028/trace_illustration_v1/RESULTS_v1/R1_S0';inputs={}
files={k:P/n for k,n in [('consumer','CONSUMER.json'),('events','EVENTS.json'),('workers','WORKER_RECORDS.json'),('session','SESSION.json'),('episode','EPISODE.json')]}
files['timely_windows']=R/'experiments/dsn_manuscript_update_20261028/timely_continuity_v1/RESULTS_v1/TIMELY_LOSS_WINDOWS.json'
for key,p in files.items():inputs[key]=dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p))
cfg=dict(experiment_id='REVTRACE-POSTHOC-TIMELY-FULL2S-CONTENT-CASE-20261029-V1',cell_id='stability-c16-staggered-r1_s0-r0',session_id=7,source_id='3570-5694-0003',offered_F=224000,canonical_F=192000,version=6,
    inputs=inputs,measured_neural_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',prior_raw_extraction_commit='c9e8a89a7df2f269fad0007a4891922da02d728d',
    selection='User-attachment motivated post-hoc explanatory full interval; no population/prevalence inference and no paired Joint counterfactual',expected_D=1.4439057689160109,expected_loss_start=1.543663284741342,expected_C=3.7196051217615604,new_model_calls=0)
with (H/'CONFIG_v1.json').open('x',encoding='utf8',newline='\n') as f:json.dump(cfg,f,indent=2);f.write('\n')
assert not git('status','--porcelain','--untracked-files=all');print(json.dumps(dict(code_commit=m['code_commit'],manifest_sha256=sha(H/'SOURCE_v1.json'),config_sha256=sha(H/'CONFIG_v1.json'),inputs=len(inputs),all_data_already_local=True)))
