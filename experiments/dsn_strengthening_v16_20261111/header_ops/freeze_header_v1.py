"""Freeze explicit header-source identity independently of default CURRENT."""
import ast,datetime,hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];S=E/'magicdata_header_source';P=E/'header_packages_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def git(where,*args):return subprocess.check_output(['git','-C',str(where),*args],text=True).strip()
def main():
    P.mkdir(exist_ok=False)
    for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    default=json.loads(subprocess.check_output([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],text=True,cwd=R));put(P/'DEFAULT_PREFLIGHT_AT_FREEZE.json',default)
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    try:
        code="import json,platform,sys;print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node(),CUDA_VISIBLE_DEVICES='',model_calls=0,GPU_calls=0)))"
        i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=30);i.write(code);i.flush();i.channel.shutdown_write();raw,err=o.read(),e.read();assert o.channel.recv_exit_status()==0,err.decode();env=json.loads(raw)
    finally:c.close()
    put(P/'FROZEN_ENVIRONMENT.json',env)
    subprocess.run(['git','init','--initial-branch=codex/magicdata-test-header-v1'],cwd=S,check=True,capture_output=True)
    for k,v in [('core.autocrlf','false'),('user.name','RevTrace Research'),('user.email','source@revtrace.local')]:git(S,'config',k,v)
    git(S,'add','-A');git(S,'commit','-m','data: freeze official MAGICDATA test-only transport and RIFF header census')
    commit=git(S,'rev-parse','HEAD');assert not git(S,'status','--porcelain','--untracked-files=all')
    files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git(S,'ls-files').splitlines()]
    put(P/'SOURCE.json',dict(code_commit=commit,source_commit=commit,files=files,scope='CPU official test transport/header readiness only; no model/transcript interpretation or selection'))
    git(S,'bundle','create',str(P/'SOURCE.bundle'),'HEAD');ref='refs/research/magicdata-test-header-v1';git(R,'fetch',str(P/'SOURCE.bundle'),'HEAD:'+ref);assert git(R,'rev-parse',ref)==commit
    cfg=dict(experiment_ids=dict(controls='REVTRACE_MAGICDATA_TEST_HEADER_CONTROLS_20261111_V1',acquire_census='REVTRACE_MAGICDATA_TEST_HEADER_CENSUS_20261111_V1'),
        source_commit=commit,source_manifest_sha256=sha(P/'SOURCE.json'),experiment_disk=B,expected_environment=env,expected_controls=12,
        official_resource_page='https://www.openslr.org/68/',archive_url='https://openslr.magicdatatech.com/resources/68/test_set.tar.gz',
        allowed_archive_urls=['https://openslr.magicdatatech.com/resources/68/test_set.tar.gz'],archive_bytes=2201936013,
        expected_ETag='"833ee08d-58e45ba913852"',official_expected_sha256=None,official_expected_md5=None,
        official_checksum_scope='landing page links no digest; bounded3adjacent checksum probes404; computed archive hash is observed identity, not published-digest validation',
        checksum_lookup_record_sha256=sha(E/'review/MAGICDATA_CHECKSUM_LOOKUP_v1.json'),
        metadata_archive=B+'/results/revtrace/dsn_strengthening_v16_20261111/metadata_options_v1/magicdata_metadata.tar.gz',
        metadata_archive_sha256='1f71e2dfea4706e76177158a6d45f2be838042af5ecc442f447f8369d40764c9',
        test_scp_sha256='c1dc8d289fb8a245359428d0ad30624cc3eff620c3ada4b7b1359f532e6be600',
        speaker_info_sha256='b74de5e561d4e5b9e57248445413bb1ffe7415aca9ee72d7528799dc8d8f4d7f',
        expected_WAV_members=24279,expected_test_speakers=43,maximum_tar_members=100000,maximum_expanded_member_bytes=16*1024**3,
        maximum_single_WAV_bytes=128*1024**2,maximum_download_attempts=3,network_socket_timeout_seconds=45,maximum_download_wall_seconds=7200,
        candidate_format='original mono PCM16 16000Hz, consistentblockalign/byterate',duration_strata_seconds=[[6,12],[12,20]],stratum_bounds='[6,12),[12,20]',
        preprocessing='NONE: no decode/trim/resample/concat',history_census_status='REQUIRED_NOT_COMPLETED',speaker_selection='FORBIDDEN_UNTIL_FRESH_HISTORY_CENSUS',
        default_pointer_policy='observe default preflight identity before/after; never change/reset CURRENT; root may legitimately activate another execution source',
        prospective_contract_sha256=sha(E/'plans/MAGICDATA_TEST_HEADER_CONTRACT_v1.zh.md'))
    put(P/'CONFIG.json',cfg)
    put(P/'FREEZE_RECORD.json',dict(source_commit=commit,source_manifest_sha256=sha(P/'SOURCE.json'),source_bundle_sha256=sha(P/'SOURCE.bundle'),source_files=len(files),config_sha256=sha(P/'CONFIG.json'),frozen_environment_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),local_execution_ref=ref,default_execution_pointer_at_freeze=default,
        remote_project=B+'/projects/revtrace_dsn_strengthening_v16_20261111/magicdata_header_v1',remote_result_base=B+'/results/revtrace/dsn_strengthening_v16_20261111/magicdata_header_v1',archive_download_started=False,models_or_GPU_launched=False))
    print(json.dumps(json.loads((P/'FREEZE_RECORD.json').read_bytes()),indent=2))
if __name__=='__main__':main()
