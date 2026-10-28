"""Freeze a read-only path resolver correction; never modify the neural plan."""
import hashlib,json,shutil,subprocess
from pathlib import Path
T=Path(__file__).resolve().parents[1];A=T/'analysis_tools/frozen_aggregate_v2';A.mkdir(exist_ok=False)
P=T/'packages'
text=(T/'analysis_tools/aggregate_service.py').read_text(encoding='utf8')
old="argv=raw.get('argv',[]);target=raw.get('out',raw.get('output',flag(argv,'--out')))"
new="""argv=raw.get('argv',[]);command_target=flag(argv,'--out')
        target=command_target or raw.get('output') or raw.get('out')
        if command_target and raw.get('output'):
            need(command_target==raw['output'],'command/output path disagreement')
        # The historical `out` planning alias was not retargeted in v3.
        # Measured command and controller output agree; retain the discrepancy.
        alias_disagreement=bool(raw.get('out') and raw['out']!=target)"""
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("cell=dict(raw,cell_id=cid,out=target)","cell=dict(raw,cell_id=cid,out=target,historical_out_alias_disagreement=alias_disagreement)")
text=text.replace("planned_cells=len(cells),accepted_cells=len(accepted),", "planned_cells=len(cells),accepted_cells=len(accepted),historical_out_alias_disagreements=sum(c['historical_out_alias_disagreement'] for c in cells),")
(A/'aggregate_service_v5.py').write_text(text,encoding='utf8')
(A/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
(A/'PROTOCOL.md').write_text('Analysis-only correction. Authoritative measured argv --out must agree with controller output. Historical out alias retained and counted. No neural source, frozen plan, raw result, metric or scientific criterion changed. Previous all-missing analysis remains preserved. New GPU calls: zero.\n',encoding='utf8')
def git(*args):return subprocess.check_output(['git','-C',str(A),*args],text=True).strip()
subprocess.run(['git','-C',str(A),'init'],check=True,capture_output=True)
git('config','core.autocrlf','false');git('checkout','-b','codex/aggregate-pathfix-v2');git('add','.');git('commit','-m','Resolve measured H3 output from frozen execution argv')
commit=git('rev-parse','HEAD');assert not git('status','--porcelain','--untracked-files=all')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=dict(code_commit=commit,scope='Independent read-only analysis; measured neural source remains f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',files=[dict(path=n,bytes=(A/n).stat().st_size,sha256=sha(A/n)) for n in git('ls-files').splitlines()])
with (P/'AGGREGATE_SOURCE_v2.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
bundle=P/'AGGREGATE_SOURCE_v2.bundle';git('bundle','create',str(bundle),'HEAD')
print(json.dumps(dict(code_commit=commit,files=len(manifest['files']),manifest_sha256=sha(P/'AGGREGATE_SOURCE_v2.json'),bundle_sha256=sha(bundle))))
