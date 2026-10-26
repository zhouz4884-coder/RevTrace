"""Byte-preserving source snapshot; archives only owned allowlisted sources."""
from pathlib import Path
import sys,subprocess,shutil,json,hashlib,tarfile
W=Path(__file__).resolve().parent;name=sys.argv[1];D=W/name;assert not D.exists();D.mkdir()
for p in (W/'runtime').rglob('*'):
    if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts:
        out=D/'runtime'/p.relative_to(W/'runtime');out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
extra=[f for f in ['m_format_audit.py','content_fault.py','test_content_fault.py','m_format_control.py','test_audit_contracts.py','x_certificate_audit.py','x_service_audit.py','x_service_metrics.py','x_service_oracle.py','m_independent_audit.py','m_old_controls.py','x_service_controller.py','m_orthogonal.py','s_independent_audit.py','cpu_full_counterexample.py','test_kernel_cow.py','test_historical_display.py','test_prefix_plan.py'] if (W/f).exists()]
for f in ['PROTOCOL.md','x_gpu_probe.py','X_PROFILES_v1.json']+extra:
    shutil.copyfile(W/f,D/f)
for f in ['memory_gpu_pilot.py','memory_app.py']:
    shutil.copyfile(W.parent/'evidence_retirement_20261026'/f,D/f)
shutil.copyfile(W.parent/'evidence_retirement_20261026/MEMORY_TASKS_v4.json',D/'MEMORY_TASKS_v4.json')
def git(*args):return subprocess.check_output(['git','-C',str(D),*args])
git('init','-b','codex/lp1-'+name);git('config','core.autocrlf','false');git('add','--','runtime','PROTOCOL.md','x_gpu_probe.py','X_PROFILES_v1.json','memory_gpu_pilot.py','memory_app.py','MEMORY_TASKS_v4.json',*extra)
git('-c','user.name=Research Artifact','-c','user.email=artifact@example.invalid','-c','commit.gpgsign=false','commit','-m','Freeze LP1 current-input operator feasibility source')
files=[dict(path=p.relative_to(D).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    for p in sorted(D.rglob('*')) if p.is_file() and '.git' not in p.parts]
record=dict(code_commit=git('rev-parse','HEAD').decode().strip(),baseline='62b1003c2db6766118244c78fa95e2c3fac42c16',files=files)
(D/'SOURCE_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n');(W/(name+'_SOURCE.json')).write_text(json.dumps(record,indent=2)+'\n')
with tarfile.open(W/(name+'.tar.gz'),'w:gz') as arc:
    for r in files:arc.add(D/r['path'],arcname=r['path'])
    arc.add(D/'SOURCE_MANIFEST.json',arcname='SOURCE_MANIFEST.json')
print(json.dumps(dict(code_commit=record['code_commit'],files=len(files),tar_sha256=hashlib.sha256((W/(name+'.tar.gz')).read_bytes()).hexdigest())))
