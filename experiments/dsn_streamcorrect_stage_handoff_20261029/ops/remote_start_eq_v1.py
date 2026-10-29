"""Root allocated four-source same-input neural prerequisite, no service grid."""
import pathlib,json,hashlib,subprocess,sys,os,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_stage_handoff_20261029';O=B/'results/revtrace/dsn_streamcorrect_stage_handoff_20261029'
assert json.loads((O/'PREREQUISITE_GATE_v1.json').read_text())['status']=='PASS_FROZEN_STAGE_SOURCE_DEPENDENCIES_AND_SAME_ENV_CPU_ONLY'
assert hashlib.sha256((P/'EQ_PLAN_v1_FROZEN.json').read_bytes()).hexdigest()=='f640672518788c9fcb36de80bf424f6d7a3157c6e110fe3de27d8a8a9bdbcc2d'
assert hashlib.sha256((P/'SOURCE_v1.json').read_bytes()).hexdigest()=='9f1364c65c78f901e8a4af580e4b10e417a020d366954f8b48ba95f9d02aecfa'
assert json.loads((B/'results/revtrace/dsn_streamcorrect_stage_profile_20261029/campaign_v1/GATE.json').read_text())['status']=='PASS_BOUNDED_ORIGINAL_STAGE_PROFILE_AND_PACKET_CONTROLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
handle=O/'EQ_HANDLE_v1.json';assert not handle.exists() and not (O/'equivalence_v1').exists()
command=[sys.executable,'-B',str(P/'source_v1/run_neural_equivalence.py'),'--plan',str(P/'EQ_PLAN_v1_FROZEN.json'),'--manifest',str(P/'SOURCE_v1.json'),'--out',str(O/'equivalence_v1')];log=O/'equivalence_v1.log'
with log.open('x') as f:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,source_commit='c7e403b4313ed1283dfea2af043116643e01a0f7',plan_sha256=hashlib.sha256((P/'EQ_PLAN_v1_FROZEN.json').read_bytes()).hexdigest(),source_manifest_sha256=hashlib.sha256((P/'SOURCE_v1.json').read_bytes()).hexdigest(),log=str(log),out=str(O/'equivalence_v1'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
handle.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
