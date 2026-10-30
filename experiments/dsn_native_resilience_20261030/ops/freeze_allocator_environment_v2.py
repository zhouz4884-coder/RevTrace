"""Freeze the evidenced allocator condition for both formal arms and reference."""
import datetime,hashlib,json,pathlib,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];base=R/'experiments/dsn_streamcorrect_encoder_profile_20261029/references_v1/FROZEN_ENVIRONMENT.json';gate=F/'LONG_MEMORY_DIAGNOSTIC_RESULTS_v1/v3/release_g_expanded_r0/GATE.json';M=F/'packages/SOURCE_v2.json'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(base)=='96a0679d34741743de1a1b6d784c0e518cbdcf7b76a23cae3d95c12d20a6fae8';g=json.loads(gate.read_bytes());assert g['status']=='PASS_RELEASE_G96_AND_ALL_FIXED_ACTUAL_PREFIX_AND_INPUT_CONTROLS' and g['allocator_conf']=='expandable_segments:True'
d=json.loads(base.read_bytes());d['historical_base_environment_code_commit']=d.pop('code_commit');d.update(native_source_commit=json.loads(M.read_bytes())['source_commit'],base_environment_record=str(base.resolve()),base_environment_record_sha256=sha(base),source_manifest_sha256=sha(M),runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},allocator_alias='PYTORCH_ALLOC_CONF must be absent',control_gate_sha256=sha(gate),frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Same original packages/assets/FP32/C_U; source_v2 narrow reference lifecycle/persistence repair and actual allocator fields. This new environment record binds the one evidenced allocator control for both strategies, every worker/replacement, and independent long reference. Not a parameter grid or a serving result.')
p=F/'FROZEN_ENVIRONMENT_v2.json';assert not p.exists();p.write_bytes((json.dumps(d,indent=2)+'\n').encode());B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';target=B+'/projects/revtrace_dsn_native_resilience_20261030/FROZEN_ENVIRONMENT_v2.json'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 with s.open(target,'wx') as stream:stream.write(p.read_bytes());stream.flush()
 s.close();print(json.dumps(dict(path=str(p),remote=target,sha256=sha(p),native_source_commit=d['native_source_commit'],runtime_environment=d['runtime_environment'])))
finally:c.close()
