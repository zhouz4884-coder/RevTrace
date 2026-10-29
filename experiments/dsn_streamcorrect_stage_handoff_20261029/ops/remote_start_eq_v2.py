"""Root allocated four-source same-input neural prerequisite, no service grid."""
import pathlib,json,hashlib,subprocess,sys,os,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_stage_handoff_20261029';O=B/'results/revtrace/dsn_streamcorrect_stage_handoff_20261029'
assert json.loads((O/'PREREQUISITE_GATE_v2.json').read_text())['status']=='PASS_FROZEN_STAGE_SOURCE_DEPENDENCIES_AND_SAME_ENV_CPU_ONLY'
assert hashlib.sha256((P/'EQ_PLAN_v2_FROZEN.json').read_bytes()).hexdigest()=='a93e27fe5ffb9a7343077867a7386c020480699a2695aa6d9cc285a104f3b92a'
assert hashlib.sha256((P/'SOURCE_v2.json').read_bytes()).hexdigest()=='2dc1ca87c160e22649e3cf229e09d5840db2e77f6146b730deaea2e539d9638c'
assert json.loads((B/'results/revtrace/dsn_streamcorrect_stage_profile_20261029/campaign_v1/GATE.json').read_text())['status']=='PASS_BOUNDED_ORIGINAL_STAGE_PROFILE_AND_PACKET_CONTROLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
handle=O/'EQ_HANDLE_v2.json';assert not handle.exists() and not (O/'equivalence_v2').exists()
command=[sys.executable,'-B',str(P/'source_v2/run_neural_equivalence.py'),'--plan',str(P/'EQ_PLAN_v2_FROZEN.json'),'--manifest',str(P/'SOURCE_v2.json'),'--out',str(O/'equivalence_v2')];log=O/'equivalence_v2.log'
with log.open('x') as f:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,source_commit='99e83a466fee7f1d16830b640cc99e0040d2f147',plan_sha256=hashlib.sha256((P/'EQ_PLAN_v2_FROZEN.json').read_bytes()).hexdigest(),source_manifest_sha256=hashlib.sha256((P/'SOURCE_v2.json').read_bytes()).hexdigest(),log=str(log),out=str(O/'equivalence_v2'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
handle.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
