import datetime,hashlib,json,pathlib
F=pathlib.Path(__file__).resolve().parents[1];ROOT=F.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_20261029';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
m=read(F/'packages/SOURCE_v1.json');selection=read(F/'METADATA_SELECTION_v1_FROZEN.json');assert not selection['WAV_bytes_read'] and not selection['reference_read']
assets=read(ROOT/'experiments/dsn_streamcorrect_adaptation_20261028/ready_cpu_evidence_v6/assets_v1/ASSET_MANIFEST.json')
ref=next(x for x in assets['files'] if x['path'].endswith('/reference.json'))
cfg=dict(experiment_id='SC_INDEPENDENT4_EXACT_PUBLIC_RANGE_ACQUISITION_V1',source_commit=m['source_commit'],source_files=m['files'],
 selection=P+'/METADATA_SELECTION_v1_FROZEN.json',selection_sha256=sha(F/'METADATA_SELECTION_v1_FROZEN.json'),
 designated_disk=B,out=O+'/acquisition_v1',dataset_root=B+'/datasets/revtrace/streamcorrect_independent_20261029',
 reference_metadata=ref['path'],reference_metadata_sha256=ref['sha256'],
 environment_python=B+'/envs/revtrace-streamcorrect-20261028/bin/python',
 created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 scope='Four preselected sources only; exact public ZIP Range/memberCRC/nativeWAV16mono16k checks; no NN/models/resampling/output filtering',
 summary=O+'/acquisition_v1/SUMMARY.json',gate=O+'/acquisition_v1/GATE.json',source_receipt=O+'/acquisition_v1/SOURCE_RECEIPT.json')
p=F/'ACQUISITION_v1_FROZEN.json';assert not p.exists();p.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
(F/'CURRENT_STATUS.json').write_text(json.dumps(dict(status='METADATA_LOCKED_BEFORE_CONTENT_ACQUISITION',experiment_id=cfg['experiment_id'],source_commit=cfg['source_commit'],method_source_commit=selection['method_source_commit'],selection_sha256=cfg['selection_sha256'],selection_created_utc=selection['selection_created_utc'],WAV_members_downloaded=0,model_calls=0,gpu_calls=0,source_count=4,selection_order=[x['initial_source_id'] for x in selection['selected']],next_action='Stage frozen6-file CPU source and lock, run13 CPU controls onnativePython, then detached exact publicRange extraction only'),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(config_sha256=sha(p),selection_sha256=cfg['selection_sha256'],reference_metadata_sha256=ref['sha256'])))
