"""Approved-helper upload and actual remote CPU/source prerequisite; no GPU."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_streamcorrect_encoder_profile_20261029';O=B+'/results/revtrace/dsn_streamcorrect_encoder_profile_20261029'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    c=ssh_client();s=c.open_sftp()
    try:
        def mkdir(path):
            assert path.startswith(B+'/')
            try:s.stat(path)
            except FileNotFoundError:
                mkdir(str(pathlib.PurePosixPath(path).parent));s.mkdir(path)
        mkdir(P);mkdir(P+'/references_v1');mkdir(O)
        files=[(F/'packages/SOURCE_v2.bundle',P+'/SOURCE_v2.bundle'),(F/'packages/SOURCE_v2.json',P+'/SOURCE_v2.json'),(F/'PROFILE_PLAN_v2_FROZEN.json',P+'/PROFILE_PLAN_v2_FROZEN.json')]
        files += [(p,P+'/references_v1/'+p.name) for p in sorted((F/'references_v1').iterdir())]
        for local,remote in files:
            try:s.stat(remote)
            except FileNotFoundError:s.put(str(local),remote)
            else:
                with s.open(remote,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==sha(local)
        script='''import datetime,hashlib,json,pathlib,subprocess,os,sys
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);cfg=json.loads((P/'PROFILE_PLAN_v2_FROZEN.json').read_text());src=P/'source_v2'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(P/'PROFILE_PLAN_v2_FROZEN.json')==PLAN_SHA
if not src.exists():
 subprocess.run(['git','init',str(src)],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['git','fetch',str(P/'SOURCE_v2.bundle'),'HEAD'],cwd=src,check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['git','checkout','--detach',cfg['profile_source_commit']],cwd=src,check=True,stdout=subprocess.DEVNULL)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==cfg['profile_source_commit']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
for name,h in cfg['profile_source_files'].items():assert sha(src/name)==h
for p,h in cfg['frozen_input_files'].items():assert sha(p)==h
author=pathlib.Path(cfg['settings']['backend']['author_root'])
for filename,key in [('model.py','original_model_py_sha256'),('audio.py','original_audio_py_sha256')]:assert sha(author/'simul_whisper/whisper'/filename)==cfg['encoder_identity'][key]
mel=(author/'simul_whisper/whisper/assets/mel_filters.npz').read_bytes();assert hashlib.sha1(b'blob '+str(len(mel)).encode()+b'\\0'+mel).hexdigest()==cfg['encoder_identity']['mel_filters_git_blob']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=author,text=True).strip()==cfg['encoder_identity']['original_author_commit']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=author,text=True).strip()
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
subprocess.run([sys.executable,'-B',str(src/'run_cpu_gate.py'),'--config',str(P/'PROFILE_PLAN_v2_FROZEN.json'),'--out',str(O/'cpu_gate_v2')],env=env,check=True)
gate=json.loads((O/'cpu_gate_v2/GATE.json').read_text());assert gate['status'].startswith('PASS_17')
print(json.dumps(dict(status='PASS_REMOTE_SOURCE_AUTHOR_AND_17_CPU_PREREQUISITES',gate=gate,gate_path=str(O/'cpu_gate_v2/GATE.json'),gate_sha256=sha(O/'cpu_gate_v2/GATE.json'),models_constructed=False,gpu_calls=False)))
'''.replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('PLAN_SHA',repr(sha(F/'PROFILE_PLAN_v2_FROZEN.json')))
        i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=60);i.write(script);i.flush();i.channel.shutdown_write()
        out=o.read().decode();err=e.read().decode();code=o.channel.recv_exit_status()
        (F/'REMOTE_STAGE_CPU_v2.stdout.log').write_text(out,encoding='utf-8');(F/'REMOTE_STAGE_CPU_v2.stderr.log').write_text(err,encoding='utf-8')
        print(out);print(err,file=sys.stderr);assert code==0
        record=json.loads(out.splitlines()[-1]);(F/'CPU_PREREQUISITE_v2.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        for name in ('GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json'):
            target=F/'CPU_GATE_RESULTS_v2'/name;target.parent.mkdir(exist_ok=True);s.get(O+'/cpu_gate_v2/'+name,str(target))
    finally:s.close();c.close()
if __name__=='__main__':main()
