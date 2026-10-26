"""Derive final metrics and verify BOTH raw archives, without model execution."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,statistics,collections,xml.etree.ElementTree as ET
W=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def archive_check(archive,index,expected):
    assert sha(archive)==expected
    records={r['path']:r for r in index['files']}
    with tarfile.open(archive) as arc:
        members=arc.getmembers();assert len(members)==len(records)
        for m in members:
            name=PurePosixPath(m.name);assert not name.is_absolute() and '..' not in name.parts and m.isfile()
            assert m.name in records and m.size==records[m.name]['bytes']
            assert hashlib.sha256(arc.extractfile(m).read()).hexdigest()==records[m.name]['sha256']
    return len(records)
def main():
    exp=read(W/'RAW_EXPORT_SUMMARY.json');count=archive_check(W/'RAW_EVIDENCE.tar.gz',read(W/'RAW_INDEX.json'),exp['archive_sha256'])
    idx=read(W/'M_FORMAT_RAW_INDEX.json');count2=archive_check(W/'M_FORMAT_RAW.tar.gz',idx,idx['archive_sha256'])
    src=read(W/'X_SERVICE_AUDIT.json');assert src['status']=='PASS_FULL_SERVICE_INDEPENDENT_RECOUNT' and len(src['rows'])==16
    oracle=read(W/'X_SERVICE_ORACLE.json');assert oracle['status']=='PASS_ALL_ACTUAL_PARENT_CONTROLS' and oracle['targets']==16
    assert all(r['input']==r['original']['model_input_audit']['batch_tensors'] for r in oracle['rows'])
    groups=[]
    for rho in [1,3]:
        for mode in ['fresh','strict-full','prefix','revtrace-prefix']:
            rs=[r for r in src['rows'] if r['mode']==mode and r['rho']==rho];assert len(rs)==2
            groups.append(dict(rho=rho,mode=mode,runs=2,independent_audio_sources=2,
                Goodput=statistics.median(r['all_offered_audio_goodput_2_8'] for r in rs),
                Display_P99=statistics.median(r['display_P99'] for r in rs),Commit_P99=statistics.median(r['commit_view_P99'] for r in rs),
                J_per_audio_s=statistics.median(r['GPU_J_per_offered_audio_second'] for r in rs),
                WER_percent=statistics.median(r['all_offered_WER_percent'] for r in rs),
                CER_percent=statistics.median(r['all_offered_character_error_percent'] for r in rs),
                dual_P99_passes=sum(r['whole_run_dual_P99_pass'] for r in rs)))
    ratios=[]
    for rho in [1,3]:
        lookup={r['mode']:r for r in groups if r['rho']==rho};a,b,c=lookup['fresh'],lookup['revtrace-prefix'],lookup['prefix']
        ratios.append(dict(rho=rho,RevTrace_over_Fresh_Goodput=b['Goodput']/a['Goodput'],
            RevTrace_over_Fresh_Commit_P99=b['Commit_P99']/a['Commit_P99'],RevTrace_over_Fresh_GPU_energy=b['J_per_audio_s']/a['J_per_audio_s'],
            RevTrace_over_Standard_prefix_Goodput=b['Goodput']/c['Goodput'],
            interpretation='two-source DEVELOPMENT point,2 timing repeats; shared decoding optimization, no independent exclusive scheduling/capacity inference'))
    xml=ET.parse(W/'CPU_FROZEN_FINAL_v2.xml').getroot().find('testsuite');assert xml.attrib['tests']=='32' and xml.attrib['failures']==xml.attrib['errors']=='0'
    M=read(W/'M_INDEPENDENT_AUDIT.json');F=read(W/'M_FORMAT_AUDIT.json');assert M['episodes']==320 and F['episodes']==64
    out=dict(status='PASS_FINAL_OFFLINE_RECOUNT_AND_RAW_BYTE_AUDIT',raw_primary_files=count,raw_content_control_files=count2,
        primary_archive_sha256=exp['archive_sha256'],content_control_archive_sha256=idx['archive_sha256'],
        X_service=dict(runs=16,source_count=2,timing_repeats=2,mode_groups=groups,ratios=ratios,whole_run_dual_P99_passes=sum(r['whole_run_dual_P99_pass'] for r in src['rows']),
            exact_actual_parent_GPU_controls=16,exact_processed_tensor_identity_controls=16,logical_extra_target_calls=48),
        M_main=dict(episodes=320,development=64,validation=256,GPU_operations=M['actual_GPU_model_operations'],CPU_encode_messages=M['CPU_only_token_encode_messages']),
        M_content_only=dict(episodes=64,GPU_operations=F['actual_GPU_operations'],CPU_encode_messages=F['CPU_encode_messages'],groups=F['groups']),
        CPU_frozen=dict(code_commit=read(W/'final_source_v2_SOURCE.json')['code_commit'],tests=32,failures=0,errors=0),
        no_paper_edit=True,no_new_GPU_queued=True)
    (W/'FINAL_METRICS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(groups=groups,ratios=ratios,raw_files=count+count2,CPU_tests=32)))
if __name__=='__main__':main()
