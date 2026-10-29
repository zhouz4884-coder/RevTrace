"""Small exact original processor dependency, public metadata only."""
import pathlib,json,urllib.request,hashlib,datetime,sys,shlex,base64
T=pathlib.Path(__file__).resolve().parents[1]
def get(url):
 with urllib.request.urlopen(url,timeout=45) as r:return r.read()
api=get('https://huggingface.co/api/models/openai/whisper-large-v3-turbo');meta=json.loads(api);revision=meta['sha']
url=f'https://huggingface.co/openai/whisper-large-v3-turbo/resolve/{revision}/preprocessor_config.json'
b=get(url);cfg=json.loads(b);assert cfg['feature_size']==128 and cfg['sampling_rate']==16000
folder=T/'native_processor_dependency_v6';folder.mkdir(exist_ok=False);(folder/'HF_MODEL_METADATA.json').write_bytes(api);(folder/'preprocessor_config.json').write_bytes(b)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';remote=B+'/models/revtrace_streamcorrect_20261028/whisper_large_v3_turbo_feature_extractor_'+revision[:8]
record=dict(experiment_id='SC_NATIVE_PROCESSOR_DEPENDENCY_ACQUISITION_V6',status='PASS_PUBLIC_ORIGINAL_NATIVE_FEATURE_EXTRACTOR_METADATA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),public_model='openai/whisper-large-v3-turbo',revision=revision,public_url=url,path=remote+'/preprocessor_config.json',bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),feature_size=128,sampling_rate=16000,native_neural_calls=0,
 reason='Original UltravoxProcessor.from_pretrained explicitly loads cfg.audio_config._name_or_path openai/whisper-large-v3-turbo; bundled Ultravox preprocessor metadata has80bins and is not an equivalent substitute')
(folder/'MANIFEST.json').write_text(json.dumps(record,indent=2))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 code='import pathlib,json,base64,sys,hashlib\nr=json.load(sys.stdin);p=pathlib.Path(r["record"]["path"]);p.parent.mkdir(exist_ok=False);b=base64.b64decode(r["data"]);assert hashlib.sha256(b).hexdigest()==r["record"]["sha256"];p.write_bytes(b);p.chmod(0o444);m=p.parent/"MANIFEST.json";m.write_text(json.dumps(r["record"],indent=2));m.chmod(0o444);print(json.dumps(r["record"]))'
 i,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(code),timeout=45);i.write(json.dumps(dict(record=record,data=base64.b64encode(b).decode())));i.flush();i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();assert rc==0,err;print(out)
finally:c.close()
