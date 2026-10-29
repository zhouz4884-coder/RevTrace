import pathlib,json,subprocess,sys,os,hashlib,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';cache=B/'cache/revtrace_streamcorrect_20261028'
assert json.loads((O/'witness_recount_auditfix_v1/GATE.json').read_text())['status']=='PASS_CORRECTIVE_OFFLINE_WITNESS_RECOUNT'
assert json.loads((O/'witness_recount_auditfix_v1/WITNESS_GATE.json').read_text())['status']=='PASS_NATURAL_NONEMPTY_CORRECTED_AND_UNCHANGED_INTERLEAVINGS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
sys.path.insert(0,str(P/'runtime_source_v8'));from native_service import verify_source
source=verify_source(P/'SOURCE_v8.json');assert source['source_commit']=='61c9afac00561f7ff1351f3eba9fd95adb239e8c'
plan=P/'NATIVE_CAMPAIGN_v8_FROZEN.json';assert hashlib.sha256(plan.read_bytes()).hexdigest()=='b3b8d5612ae3adc9faee5332514184d6fc2471eebcc4a5154db8acff07e35e47'
out=O/'native_campaign_v8_continuation_auditfix_v1';handle=O/'NATIVE_v8_CONTINUATION_AUDITFIX_v1_HANDLE.json';log=O/'native_campaign_v8_continuation_auditfix_v1.log';assert not out.exists() and not handle.exists() and not log.exists()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HOME=str(cache/'huggingface'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',TRITON_CACHE_DIR=str(cache/'triton'),TORCHINDUCTOR_CACHE_DIR=str(cache/'inductor'),TORCH_HOME=str(cache/'torch'),XDG_CACHE_HOME=str(cache/'xdg'),NUMBA_CACHE_DIR=str(cache/'numba'),CUDA_CACHE_PATH=str(cache/'cuda'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
command=[sys.executable,'-B',str(P/'auditfix_source_v1/auditfix_recount_and_continue.py'),'--mode','continue','--plan',str(plan),'--manifest',str(P/'AUDITFIX_SOURCE_v1.json'),'--witness-recount',str(O/'witness_recount_auditfix_v1'),'--out',str(out)]
with log.open('x') as f:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=env)
proc=pathlib.Path('/proc')/str(child.pid);r=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=command,
 native_execution_source_commit=source['source_commit'],corrective_audit_controller_commit='a0652a81a205483ba2091dfd345b85be72ee8b19',frozen_native_plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),native_environment_sha256='96a0679d34741743de1a1b6d784c0e518cbdcf7b76a23cae3d95c12d20a6fae8',out=str(out),log=str(log),formal_cells=12,original_witness_raw_reused_without_neural_replay=True)
handle.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
