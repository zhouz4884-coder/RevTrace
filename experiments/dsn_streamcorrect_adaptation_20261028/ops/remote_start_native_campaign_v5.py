"""Launch only in the parent-coordinated GPU window, after both core campaigns."""
import pathlib,json,subprocess,hashlib,os,sys,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';cache=B/'cache/revtrace_streamcorrect_20261028'
assert json.loads((O/'assets_v1/GATE.json').read_text())['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
assert json.loads((O/'cpu_native_v5/GATE.json').read_text())['status']=='PASS_CPU_STATE_CONTRACT_TESTS_ONLY'
assert json.loads((O/'AUTHOR_DEPENDENCY_GATE_v5.json').read_text())['status']=='PASS_COMPLETE_PINNED_AUTHOR_SOURCE'
apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip()
assert not apps,'foreign/previous GPU workers present; no new launch'
handle=O/'NATIVE_v5_HANDLE.json';assert not handle.exists(),'existing launch handle; inspect exact PID before another run'
out=O/'native_campaign_v5_controller';assert not out.exists()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HOME=str(cache/'huggingface'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',
 TRITON_CACHE_DIR=str(cache/'triton'),TORCHINDUCTOR_CACHE_DIR=str(cache/'inductor'),TORCH_HOME=str(cache/'torch'),XDG_CACHE_HOME=str(cache/'xdg'),NUMBA_CACHE_DIR=str(cache/'numba'),CUDA_CACHE_PATH=str(cache/'cuda'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
command=[sys.executable,'-B',str(P/'runtime_source_v5/native_campaign.py'),'--plan',str(P/'NATIVE_CAMPAIGN_v5_FROZEN.json'),'--source-manifest',str(P/'SOURCE_v5.json'),'--out',str(out)]
log=O/'native_campaign_v5_controller.log'
with log.open('x') as f:child=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=env)
proc=pathlib.Path('/proc')/str(child.pid);ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]);cmdsha=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()
record=dict(pid=child.pid,start_ticks=ticks,cmdline_sha256=cmdsha,command=command,source_commit='a652f6097c2269232b332ad046e399f9968b16e2',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),log=str(log),controller_out=str(out))
handle.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
