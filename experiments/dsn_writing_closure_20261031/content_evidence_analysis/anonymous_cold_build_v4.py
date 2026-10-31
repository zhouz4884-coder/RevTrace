"""Independent ZIP-only extraction and skill-only cold paper build audit."""
from pathlib import Path,PurePosixPath
import datetime,hashlib,json,os,re,stat,subprocess,traceback,zipfile

ROOT=Path(__file__).resolve().parents[3]
E=ROOT/'experiments/dsn_writing_closure_20261031'
RELEASE=ROOT/'Paper_DSN/revisions/20261031_dsn2027_release_v4'
ZIP=RELEASE/'RevTrace_DSN2027_anonymous_source_v4.zip'
FINAL=ROOT/'experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v4.json'
COLD=E/'ANONYMOUS_COLD_BUILD_v4'
LOGS=E/'ANONYMOUS_COLD_BUILD_LOGS_v4'
OUT=E/'ANONYMOUS_COLD_BUILD_REVIEW_v4.json'
SKILL=Path(r'C:\Users\LENOVO\.agents\skills\latex-paper-en\SKILL.md')
COMPILE=SKILL.parent/'scripts/compile.py'

def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):return dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
def dump(path,obj):
 with path.open('x',encoding='utf8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def run(argv,name,cwd=None):
 result=subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 assert len(result.stdout)+len(result.stderr)<=1024*1024,'tool logs exceeded 1MiB'
 (LOGS/(name+'.stdout')).write_bytes(result.stdout);(LOGS/(name+'.stderr')).write_bytes(result.stderr)
 return result

def main():
 report=dict(gate='IN_PROGRESS',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0,SSH_calls=0,CURRENT_modified=False,original_manuscript_modified=False,source_archive=str(ZIP),cold_directory=str(COLD),final_record=str(FINAL),skill=str(SKILL),compile_script=str(COMPILE))
 before={}
 try:
  assert not COLD.exists() and not LOGS.exists() and not OUT.exists(),'exclusive cold build target already exists'
  final=json.loads(FINAL.read_bytes());rows=final['source_package_files'];assert len(rows)==25
  expected={r['path']:r for r in rows};assert len(expected)==25
  assert record(ZIP)==dict(bytes=final['archive_bytes'],sha256=final['archive_sha256'])
  before={str(p):record(p) for p in [ZIP,FINAL]+[RELEASE/name for name in sorted(expected)]}
  assert before[str(RELEASE/'main.pdf')]['sha256']==final['pdf_sha256']
  for name,r in expected.items():assert record(RELEASE/name)==dict(bytes=r['bytes'],sha256=r['sha256'])
  with zipfile.ZipFile(ZIP) as z:
   infos=z.infolist();assert len(infos)==25
   names=[i.filename for i in infos]
   assert set(names)==set(expected) and len(set(x.casefold() for x in names))==25
   assert z.testzip() is None
   for info in infos:
    p=PurePosixPath(info.filename)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in info.filename
    assert not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16) and not(info.flag_bits&1)
    data=z.read(info);r=expected[info.filename];assert len(data)==r['bytes'] and sha(data)==r['sha256']
   provenance=json.loads(z.read('PACKAGING_PROVENANCE.json'))
   assert {r['target'] for r in provenance['files']}|{'main.pdf','PACKAGING_PROVENANCE.json'}==set(names)
   for r in provenance['files']:
    assert sha(z.read(r['target']))==r['target_sha256'] and len(z.read(r['target']))==r['bytes']
   COLD.mkdir();LOGS.mkdir()
   for info in infos:
    target=COLD/PurePosixPath(info.filename);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(z.read(info))
  report['source_whitelist']=dict(files=25,exact_final_record_bytes_and_SHA=True,exact_provenance_target_SHA=True,extra_files=[],unsafe_entries=[])
  dump(LOGS/'ORIGINAL_INPUT_HASHES_BEFORE.json',before)
  command=['uv','run','python','-B',str(COMPILE),'main.tex','--recipe','pdflatex-bibtex']
  report['compile']=dict(command=command,cwd=str(COLD),shell_escape=False,skill_sha256=sha(SKILL.read_bytes()),compile_script_sha256=sha(COMPILE.read_bytes()))
  compiled=run(command,'SKILL_COMPILE',COLD);report['compile']['returncode']=compiled.returncode
  assert compiled.returncode==0,'latex-paper-en compile.py failed; no direct TeX fallback permitted'
  cold_pdf=COLD/'main.pdf';assert cold_pdf.is_file()
  pdf_info={};font_output={};layout={}
  for label,path in [('release',RELEASE/'main.pdf'),('cold',cold_pdf)]:
   info=run(['pdfinfo',str(path)],label+'_pdfinfo');assert info.returncode==0
   fields={m[1].strip():m[2].strip() for line in info.stdout.decode('utf8','replace').splitlines() if (m:=re.match(r'([^:]+):(.*)',line))}
   pdf_info[label]=fields
   text=run(['pdftotext','-layout',str(path),'-'],label+'_layout');assert text.returncode==0;layout[label]=text.stdout
   fonts=run(['pdffonts',str(path)],label+'_fonts');assert fonts.returncode==0;font_output[label]=fonts.stdout.decode('utf8','replace')
  pages={label:int(fields['Pages']) for label,fields in pdf_info.items()}
  assert pages['cold']==pages['release']==final['total_pages']==12
  def page_texts(raw):
   parts=raw.decode('utf8').split('\f')
   if parts and not parts[-1].strip():parts.pop()
   return parts
  original_pages=page_texts(layout['release']);new_pages=page_texts(layout['cold'])
  assert len(original_pages)==len(new_pages)==12
  per_page=[dict(page=i+1,layout_text_byte_identical=a==b,release_text_sha256=sha(a.encode()),cold_text_sha256=sha(b.encode())) for i,(a,b) in enumerate(zip(original_pages,new_pages))]
  report['layout_comparison']=dict(pdftotext_layout_bytes_identical=layout['release']==layout['cold'],pages=pages,per_page=per_page,technical_pages=11,references_start_page=12,PDF_bytes_equality_required=False)
  assert layout['release']==layout['cold'],'cold/release pdftotext -layout differs'
  font_checks={}
  for label,text in font_output.items():
   parsed=[];unparsed=[]
   for line in text.splitlines()[2:]:
    if not line.strip():continue
    m=re.match(r'^(.*?)\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+(\d+)\s+(\d+)\s*$',line)
    if not m:unparsed.append(line);continue
    parsed.append(dict(description=m[1],embedded=m[2]=='yes',subset=m[3]=='yes',unicode=m[4]=='yes',type3=bool(re.search(r'\bType\s+3\b',m[1]))))
   font_checks[label]=dict(font_rows=len(parsed),all_embedded=all(x['embedded'] for x in parsed),Type3=sum(x['type3'] for x in parsed),unparsed=unparsed,fonts=parsed)
   assert parsed and not unparsed and all(x['embedded'] for x in parsed) and not any(x['type3'] for x in parsed)
  report['embedded_fonts']=font_checks
  log=(COLD/'main.log').read_text(encoding='utf8',errors='replace')
  patterns=dict(undefined_citations=r'Citation\s+.*?undefined',undefined_references=r'Reference\s+.*?undefined',undefined_control_sequences=r'Undefined control sequence',unresolved_summary=r'There were undefined (?:references|citations)',overfull=r'Overfull\s*\\[hv]box',rerun=r'Label\(s\) may have changed|Rerun to get')
  warnings={key:re.findall(pattern,log,re.I) for key,pattern in patterns.items()};report['final_log_checks']=warnings
  assert not any(warnings.values()),'cold final log has unresolved/overfull warnings'
  # Compilation is allowed to replace only the extracted main.pdf; every
  # originally packaged source, bibliography and figure byte remains unchanged.
  cold_sources_unchanged=all(record(COLD/name)==dict(bytes=r['bytes'],sha256=r['sha256']) for name,r in expected.items() if name!='main.pdf')
  assert cold_sources_unchanged
  after={str(p):record(p) for p in [ZIP,FINAL]+[RELEASE/name for name in sorted(expected)]};assert before==after
  dump(LOGS/'ORIGINAL_INPUT_HASHES_AFTER.json',after)
  report.update(gate='PASS_ANONYMOUS_ZIP_COLD_SKILL_COMPILE_AND_LAYOUT_PARITY',original_inputs_hash_before_after_unchanged=True,cold_packaged_source_bytes_unchanged=True,original_zip=record(ZIP),original_pdf=record(RELEASE/'main.pdf'),rebuilt_pdf=record(cold_pdf),rebuilt_pdf_metadata_may_differ=True,final_record_sha256=sha(FINAL.read_bytes()),bounded_logs_total_bytes=sum(p.stat().st_size for p in LOGS.iterdir() if p.is_file()),completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 except BaseException as exc:
  report.update(gate='FAIL_PRESERVED_ANONYMOUS_COLD_BUILD',error_type=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc())
  if before:
   report['original_inputs_hash_after_failure']={path:record(Path(path)) for path in before}
   report['original_inputs_unchanged_after_failure']=before==report['original_inputs_hash_after_failure']
  dump(OUT,report);raise
 dump(OUT,report)
 print(json.dumps({k:report[k] for k in ('gate','compile','layout_comparison','original_inputs_hash_before_after_unchanged','original_zip','original_pdf','rebuilt_pdf','bounded_logs_total_bytes')},indent=2))

if __name__=='__main__':main()
