import hashlib,json,subprocess
from pathlib import Path
F=Path(__file__).resolve().parent;R=F.parents[2];S=F/'source_v1'
U=R/'experiments/physical_retirement_20261028/source_v3'
def git(*args,cwd=S):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def proof(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
assert git('rev-parse','HEAD',cwd=U)=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
assert not git('status','--porcelain','--untracked-files=all',cwd=U)
mapping=[
 ('Authority selection, protected WAL, actual installation; R on complete ancestry','runtime/src/revtrace/live_qwen.py','_commit_ready; lines 587-682'),
 ('WAL protected installation hook and role dispatch','runtime/src/revtrace/kernel_runtime.py','protocol_dispatch, protocol_row, protocol_install and journal wrapper; lines 103-144'),
 ('Same-F/P complete ancestry and frozen in-flight input','runtime/src/revtrace/continuity_proof.py','eligible_chain; whole file'),
 ('Independent certified lane, compatible whole provisional S, no suffix joining','runtime/src/revtrace/certified_display.py','ContinuityView.consume/_compatible and RealtimeConsumer; lines 44-203'),
 ('K actual installed Canonical coverage, proposal-only request','runtime/src/revtrace/retirement_runtime.py','reason_for/_request_retirement; lines 14-100'),
 ('Decode safe point, mutually exclusive terminals, synchronized full-batch drain','runtime/scripts/row_delivery_worker.py','poll_cancellations/emit/finish; lines 58-185'),
 ('Row completion does not release physical lease; BatchDrained does','runtime/scripts/row_delivery_executor.py','cancel_job/poll; lines 35-105')]
write(S/'SOURCE_MAP.json',dict(execution_source_commit=git('rev-parse','HEAD',cwd=U),
    mapping=[dict(figure_relation=a,source_relative=b,anchors=c,**proof(U/b)) for a,b,c in mapping],
    scope='Actual f0 implementation; controlled native adapter and candidate handoff are not depicted'))
git('init','-b','codex/coordination-figure-v1');git('config','core.autocrlf','false');git('add','.');git('commit','-m','Freeze actual RevTrace coordination protocol method figure')
commit=git('rev-parse','HEAD')
write(F/'SOURCE_v1.json',dict(code_commit=commit,files=[dict(path=n,**proof(S/n)) for n in git('ls-files').splitlines()]))
git('bundle','create',str(F/'SOURCE_v1.bundle'),'--all')
git('fetch',str(F/'SOURCE_v1.bundle'),'HEAD:refs/heads/codex/coordination-figure-v1',cwd=R)
paths=[U/b for _,b,_ in mapping]+[F.parent/'SEMANTIC_SPINE.zh.md',F.parent/'ROUND4_INDEPENDENT_DECISION.zh.md']
write(F/'CONFIG_v1.json',dict(experiment_id='REVTRACE-DSN-COORDINATION-METHOD-FIGURE-20261029-V1',
    evidence_type='method illustration, no measured serving results',execution_source_commit=git('rev-parse','HEAD',cwd=U),
    plot_source_commit=commit,source_manifest_sha256=proof(F/'SOURCE_v1.json')['sha256'],
    width_inches=7.15,minimum_font_pt=8,output=str(F/'FIGURES_v1'),input_files={str(p):proof(p) for p in paths}))
write(F/'FREEZE_RECEIPT_v1.json',dict(plot_source_commit=commit,source_manifest=proof(F/'SOURCE_v1.json'),frozen_config=proof(F/'CONFIG_v1.json')))
print(json.dumps(dict(plot_source_commit=commit,files=len(git('ls-files').splitlines()))))
