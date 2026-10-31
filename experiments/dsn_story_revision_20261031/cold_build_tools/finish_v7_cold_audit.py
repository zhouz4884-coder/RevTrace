"""Finish the same completed cold build after a reference-header detector fix.

No extraction, compilation, neural call, or original-source write occurs here.
The initial failed detector result is preserved with its original bytes.
"""
from pathlib import Path
import datetime,hashlib,importlib.util,json,re,subprocess

ROOT=Path(__file__).resolve().parents[3]
E=ROOT/'experiments/dsn_story_revision_20261031'
RELEASE=ROOT/'Paper_DSN/revisions/20261031_dsn2027_release_v7'
COLD=E/'ANONYMOUS_COLD_BUILD_v7';LOGS=E/'ANONYMOUS_COLD_BUILD_LOGS_v7'
OUT=E/'ANONYMOUS_COLD_BUILD_REVIEW_v7.json'
FAILED=E/'ANONYMOUS_COLD_BUILD_REVIEW_v7_failed_reference_detector.json'
FINAL=ROOT/'experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v7.json'
def sha(data):return hashlib.sha256(data).hexdigest()
def rec(p):return dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
def read(p):return json.loads(p.read_bytes())
def dump(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2);f.write('\n')
initial_bytes=OUT.read_bytes();initial=json.loads(initial_bytes)
assert initial['gate']=='FAIL_PRESERVED_ANONYMOUS_COLD_BUILD'
assert initial['compile']['returncode']==0 and initial['original_inputs_unchanged_after_failure']
assert 'ref_headers' in initial['traceback'] and initial['reason']=='[]'
assert COLD.is_dir() and LOGS.is_dir() and not FAILED.exists()
before=read(LOGS/'ORIGINAL_INPUT_HASHES_BEFORE.json');final=read(FINAL)
expected={r['path']:r for r in final['source_package_files']};assert len(expected)==27
assert {r['target'] for r in read(COLD/'PACKAGING_PROVENANCE.json')['files']}|{'main.pdf','PACKAGING_PROVENANCE.json'}==set(expected)

layout={label:(LOGS/(label+'_layout.stdout')).read_bytes() for label in ['release','cold']}
def split_pages(raw):
    a=raw.decode('utf8').split('\f')
    if a and not a[-1].strip():a.pop()
    return a
pages={k:split_pages(v) for k,v in layout.items()}
assert len(pages['release'])==len(pages['cold'])==12 and layout['release']==layout['cold']
per_page=[dict(page=i+1,layout_text_byte_identical=a==b,release_text_sha256=sha(a.encode()),
    cold_text_sha256=sha(b.encode())) for i,(a,b) in enumerate(zip(pages['release'],pages['cold']))]
assert all(r['layout_text_byte_identical'] for r in per_page)

# Flow extraction separates columns. Reuse the established pure pagination
# checker rather than assuming one physical layout line contains only a title.
qa_path=ROOT/'experiments/dsn_manuscript_update_20261028/qa_dsn_release.py'
spec=importlib.util.spec_from_file_location('v7_cold_pagination_qa',qa_path)
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
flow={};pagination={}
for label,pdf in [('release',RELEASE/'main.pdf'),('cold',COLD/'main.pdf')]:
    out=LOGS/(label+'_flow.stdout');err=LOGS/(label+'_flow.stderr')
    assert not out.exists() and not err.exists()
    r=subprocess.run(['pdftotext','-enc','UTF-8',str(pdf),'-'],capture_output=True,timeout=60)
    assert r.returncode==0 and len(r.stdout)+len(r.stderr)<=1024*1024
    out.write_bytes(r.stdout);err.write_bytes(r.stderr);flow[label]=r.stdout
    pagination[label]=qa.reference_pages(r.stdout.decode('utf8'),12,11)
    assert pagination[label]['status']=='PASS',pagination[label]
    assert pagination[label]['technical_pages']==11 and pagination[label]['references_start_page']==12
assert flow['release']==flow['cold']

font_checks={};font_raw={}
for label in ['release','cold']:
    text=(LOGS/(label+'_fonts.stdout')).read_text(encoding='utf8');font_raw[label]=text
    parsed=[];unparsed=[]
    for line in text.splitlines()[2:]:
        if not line.strip():continue
        m=re.match(r'^(.*?)\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+(\d+)\s+(\d+)\s*$',line)
        if not m:unparsed.append(line);continue
        parsed.append(dict(description=m[1],embedded=m[2]=='yes',subset=m[3]=='yes',unicode=m[4]=='yes',
            type3=bool(re.search(r'\bType\s+3\b',m[1]))))
    assert len(parsed)==29 and not unparsed and all(x['embedded'] for x in parsed) and not any(x['type3'] for x in parsed)
    font_checks[label]=dict(font_rows=len(parsed),all_embedded=True,Type3=0,unparsed=unparsed,fonts=parsed)
log=(COLD/'main.log').read_text(encoding='utf8',errors='replace')
patterns=dict(undefined_citations=r'Citation\s+.*?undefined',undefined_references=r'Reference\s+.*?undefined',
    undefined_control_sequences=r'Undefined control sequence',unresolved_summary=r'There were undefined (?:references|citations)',
    overfull=r'Overfull\s*\\[hv]box',rerun=r'Label\(s\) may have changed|Rerun to get')
warnings={k:re.findall(p,log,re.I) for k,p in patterns.items()};assert not any(warnings.values())
assert all(rec(COLD/name)==dict(bytes=r['bytes'],sha256=r['sha256']) for name,r in expected.items() if name!='main.pdf')
after={p:rec(Path(p)) for p in before};assert before==after
dump(LOGS/'ORIGINAL_INPUT_HASHES_AFTER.json',after)

report={k:initial[k] for k in ['created_utc','new_model_calls','SSH_calls','CURRENT_modified',
    'original_manuscript_modified','source_archive','cold_directory','final_record','skill','compile_script','source_whitelist','compile']}
report.update(gate='PASS_ANONYMOUS_ZIP_COLD_SKILL_COMPILE_AND_LAYOUT_PARITY',
    layout_comparison=dict(pdftotext_layout_bytes_identical=True,pages=dict(release=12,cold=12),per_page=per_page,
        technical_pages=11,references_start_page=12,PDF_bytes_equality_required=False),
    flow_text_bytes_identical=True,independent_pagination_checks=pagination,pagination_checker_sha256=sha(qa_path.read_bytes()),
    embedded_fonts=font_checks,font_lists_byte_identical=font_raw['release']==font_raw['cold'],final_log_checks=warnings,
    original_inputs_hash_before_after_unchanged=True,cold_packaged_source_bytes_unchanged=True,
    original_zip=rec(Path(initial['source_archive'])),original_pdf=rec(RELEASE/'main.pdf'),rebuilt_pdf=rec(COLD/'main.pdf'),
    rebuilt_pdf_metadata_may_differ=True,final_record_sha256=sha(FINAL.read_bytes()),
    bounded_logs_total_bytes=sum(p.stat().st_size for p in LOGS.iterdir() if p.is_file()),
    completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    review_driver_sha256=sha((Path(__file__).with_name('anonymous_cold_build_v7.py')).read_bytes()),
    completion_reader_sha256=sha(Path(__file__).read_bytes()),same_single_extraction_and_compile=True,
    initial_detector_failure=dict(path=FAILED.name,bytes=len(initial_bytes),sha256=sha(initial_bytes),
        cause='Strict whole physical layout line matching missed REFERENCES joined with right-column bibliography; flow pagination fixes the detector only.',
        compile_returncode=0,original_inputs_unchanged=True,recompiled=False,reextracted=False))
assert OUT.resolve().parent==FAILED.resolve().parent==E.resolve()
OUT.rename(FAILED);assert FAILED.read_bytes()==initial_bytes
dump(OUT,report)
print(json.dumps(dict(gate=report['gate'],source_files=27,compile_exit=report['compile']['returncode'],
    layout_pages_identical=12,font_rows=29,all_embedded=True,Type3=0,source_hashes_unchanged=True,
    reference_pages=pagination['cold'],initial_failure_preserved=FAILED.name,
    extraction_count=1,compilation_count=1,report_sha256=sha(OUT.read_bytes())),indent=2))
