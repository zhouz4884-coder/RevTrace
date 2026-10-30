"""Package only the compiled closure after automated and actual visual review."""
import argparse,base64,datetime,hashlib,json,subprocess,zipfile
from pathlib import Path
from release_delivery_checks import new_output_path

T=Path(__file__).resolve().parent;R=T.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_bytes())
parser=argparse.ArgumentParser()
parser.add_argument('--release',type=Path,required=True)
parser.add_argument('--automated-qa',type=Path,required=True)
parser.add_argument('--visual-review',type=Path,required=True)
parser.add_argument('--archive',type=Path,required=True)
parser.add_argument('--final-record',type=Path,default=T/'FINAL_RELEASE_RECORD_v1.json',help='NEW final record; existing records are never overwritten')
args=parser.parse_args()
release=args.release.resolve();archive=args.archive.resolve()
assert release.is_relative_to(R/'Paper_DSN/revisions') and release.is_dir()
# Validate every output before creating the ZIP, including the legacy default
# final-record name. A stale record must not leave a new, unrecorded archive.
archive=new_output_path(archive,R/'Paper_DSN','.zip')
target=new_output_path(args.final_record,T,'.json')
manifest=read(release/'PACKAGING_PROVENANCE.json')
pdf=(release/'main.pdf').read_bytes();qa=read(args.automated_qa);visual=read(args.visual_review)
assert qa['gate']=='PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA'
assert visual['gate']=='PASS_ROOT_ALL_PAGE_VISUAL_QA'
assert qa['pdf_sha256']==visual['pdf_sha256']==sha(pdf)
assert visual['reviewed_pages']==list(range(1,qa['total_pages']+1))
assert visual['actual_root_visual_review'] is True
payload={}
for row in manifest['files']:
 path=(release/row['target']).resolve()
 assert path.is_relative_to(release) and path.is_file() and not path.is_symlink()
 assert row['target'] not in payload
 data=path.read_bytes();assert sha(data)==row['target_sha256'] and len(data)==row['bytes']
 payload[row['target']]=data
payload['PACKAGING_PROVENANCE.json']=(release/'PACKAGING_PROVENANCE.json').read_bytes()
payload['main.pdf']=pdf
for name,data in payload.items():
 assert Path(name).suffix in {'.tex','.bib','.pdf','.json'} and len(data)<20_000_000
scannable=[data.decode('utf8') for name,data in payload.items() if Path(name).suffix in {'.tex','.bib','.json'}]
scannable += [base64.b64decode(e['original_entry_bytes_base64']).decode('utf8') for e in manifest['bibliography_entries']]
scannable += [subprocess.check_output(['pdftotext','-layout','-enc','UTF-8',str(release/'main.pdf'),'-'],encoding='utf8'),subprocess.check_output(['pdfinfo',str(release/'main.pdf')],encoding='utf8',errors='replace')]
for text in scannable:
 for token in ['LENOVO','zhouz4884-coder','C:\\Users\\','D:\\VLA_QWEN','/media/user/5bc0dc8d']:
  assert token.casefold() not in text.casefold(),'Identity/local-path token in clean package: '+token
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as package:
 for name,data in sorted(payload.items()):package.writestr(name,data)
with zipfile.ZipFile(archive) as package:
 assert len(package.namelist())==len(payload) and set(package.namelist())==set(payload)
 for name,data in payload.items():assert package.read(name)==data
record=dict(gate='PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),release=release.relative_to(R).as_posix(),pdf_sha256=sha(pdf),total_pages=qa['total_pages'],technical_pagination=qa['checks']['pagination'],automated_QA_sha256=sha(args.automated_qa.read_bytes()),visual_review_sha256=sha(args.visual_review.read_bytes()),archive=archive.relative_to(R).as_posix(),archive_sha256=sha(archive.read_bytes()),archive_bytes=archive.stat().st_size,source_package_files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(payload.items())],anonymity_scope='Known identity/local-path tokens checked in compiled text/metadata, selected TeX/Bib, provenance and decoded original Bib entries; actual all-page visual review recorded separately.',submission_performed=False)
with target.open('x',encoding='utf8') as output:output.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='source_package_files'},ensure_ascii=False,indent=2))
