from pathlib import Path
import hashlib,json,shutil,subprocess
H=Path(__file__).resolve().parent;I=H/'trace_illustration_v1';I.mkdir(exist_ok=False);S=I/'source';S.mkdir()
for name in ('trace_extract.py','trace_plot.py'):shutil.copyfile(H/name,S/name)
shutil.copyfile(H/'analysis_source_v2/interaction_opportunities_v1.py',S/'interaction_opportunities_v1.py')
(S/'.gitignore').write_text('__pycache__/\n*.pyc\n');(S/'PROTOCOL.md').write_text('Offline actual-trace illustration only, no GPU/model calls. Fixed c16-staggered repeat 0; same source and complete selected history in R1S0/R1S1. Require witnessed compatible-ahead event at a shared F in both arms, then choose largest R1S0 source rollback area, tie by source ID. Preserve original per-session clocks. This is diagnostic illustration, not prevalence.\n')
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['git','-C',str(S),'init'],check=True,capture_output=True);git('config','core.autocrlf','false');git('checkout','-b','codex/dsn-actual-compatible-trace-v1');git('add','.');git('commit','-m','Freeze actual same-root Consumer trace extraction and plotting')
m=dict(code_commit=git('rev-parse','HEAD'),scope='CPU-only diagnostic extraction and publication figure from already completed 36 cells',files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()])
with (I/'TRACE_SOURCE_v1.json').open('x') as f:json.dump(m,f,indent=2);f.write('\n')
git('bundle','create',str(I/'TRACE_SOURCE_v1.bundle'),'HEAD')
R=H/'RESULTS_v1';metrics=json.loads((R/'aggregate/SOURCE_METRICS.json').read_text());updates=json.loads((R/'opportunities/UPDATES.json').read_text());inputs=json.loads((R/'opportunities/ANALYSIS_RECORD.json').read_text())['inputs']
cells={'R1_S0':'stability-c16-staggered-r1_s0-r0','R1_S1':'stability-c16-staggered-r1_s1-r0'}
pool=[]
for sid in range(16):
    fs={arm:{u['F'] for u in updates if u['cell_id']==cell and u['session_id']==sid and u['clock_scope']=='consumer_apply' and u['ahead'] and u['compatible'] is True} for arm,cell in cells.items()}
    row=next(r for r in metrics if r['cell_id']==cells['R1_S0'] and r['session_id']==sid)
    pool.append(dict(session_id=sid,source_id=row['source_id'],R1S0_area=row['rollback_area_audio_seconds_x_wall_seconds'],shared_compatible_F=sorted(fs['R1_S0']&fs['R1_S1'])))
eligible=sorted((r for r in pool if r['shared_compatible_F']),key=lambda r:(-r['R1S0_area'],r['source_id']));selected=eligible[0];assert selected['session_id']==7
F=selected['shared_compatible_F'][-1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/physical_retirement_20261028/dsn_service_stability_v1'
records=[];expected={}
for arm,cell in cells.items():
    update=next(u for u in updates if u['cell_id']==cell and u['session_id']==selected['session_id'] and u['clock_scope']=='consumer_apply' and u['F']==F)
    records.append(dict(arm=arm,cell_id=cell,path=O+'/'+cell,expected_visible_job=update['visible_job_id'],expected_selected_job=update['selected_job_id']))
    for name in ('events.jsonl','consumer.jsonl','worker_records.jsonl','sessions.json'):
        path=O+'/'+cell+'/attempt0/'+name;expected[path]=inputs[path]
cfg=dict(experiment_id='REVTRACE-DSN-ACTUAL-SHARED-COMPATIBLE-TRACE-20261029-V1',source_id=selected['source_id'],session_id=selected['session_id'],shared_F=F,
    measured_neural_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',parent_plan_sha256='bd06a99155b2f962b0ba9e832424ee84c9ce7d98cff79fad2091c756792fe39f',cells=records,expected_inputs=expected,
    selection=dict(fixed_block='c16-staggered repeat0',rule='Among sources with actual same-F compatible ahead in both R1S0/R1S1, maximize R1S0 withdrawal area, tie by source ID; choose greatest shared F for highlighting.',pool=pool,
        excluded_global_area_max='sid13 has the largest R1S0 area but no Joint ahead update; not suitable for a shared-interleaving mechanism illustration.',prevalence_claim=False),
    clocks='each actual observed_perf minus that run original episode origin_perf plus session offset; never align update times',new_model_calls=0)
with (I/'CONFIG_v1.json').open('x') as f:json.dump(cfg,f,indent=2);f.write('\n')
receipt=dict(code_commit=m['code_commit'],source_manifest_sha256=sha(I/'TRACE_SOURCE_v1.json'),bundle_sha256=sha(I/'TRACE_SOURCE_v1.bundle'),config_sha256=sha(I/'CONFIG_v1.json'),source_id=selected['source_id'],shared_F=F,new_model_calls=0)
with (I/'FREEZE_RECEIPT_v1.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
assert not git('status','--porcelain','--untracked-files=all');print(json.dumps(receipt))
