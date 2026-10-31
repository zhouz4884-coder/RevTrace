"""Create a new v7 audit driver without changing the verified v4 driver."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[3]
old=ROOT/'experiments/dsn_writing_closure_20261031/content_evidence_analysis/anonymous_cold_build_v4.py'
new=Path(__file__).with_name('anonymous_cold_build_v7.py')
assert not new.exists()
data=old.read_bytes();s=data.decode('utf8')
s=s.replace('experiments/dsn_writing_closure_20261031','experiments/dsn_story_revision_20261031')
s=s.replace('_v4','_v7').replace('==25','==27').replace('files=25','files=27')
s=s.replace("command=['uv','run','python'", "command=['uv','run','--no-project','--offline','python'")
s=s.replace("[ZIP,FINAL]+", "[ZIP,FINAL,ROOT/'experiments/repository_identity_20261027/CURRENT.json']+")
s=s.replace("assert parsed and not unparsed and all(x['embedded'] for x in parsed)",
            "assert len(parsed)==29 and not unparsed and all(x['embedded'] for x in parsed)")
s=s.replace("  assert len(original_pages)==len(new_pages)==12", """  assert len(original_pages)==len(new_pages)==12
  ref_headers=[i+1 for i,page in enumerate(new_pages) if any(re.sub(r'\\s+','',line).upper()=='REFERENCES' for line in page.splitlines())]
  assert ref_headers==[12], ref_headers
  assert re.sub(r'\\s+','',new_pages[11].lstrip().splitlines()[0]).upper()=='REFERENCES'""")
s=s.replace("  report['embedded_fonts']=font_checks", """  report['embedded_fonts']=font_checks
  report['font_lists_byte_identical']=font_output['release']==font_output['cold']
  report['review_driver_sha256']=sha(Path(__file__).read_bytes())""")
assert '==25' not in s and 'files=25' not in s and '_v4' not in s
compile(s,str(new),'exec')
with new.open('xb') as f:f.write(s.encode('utf8'))
assert old.read_bytes()==data
print(json.dumps(dict(driver=str(new),bytes=new.stat().st_size,
    sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
    original_v4_driver_unchanged_sha256=hashlib.sha256(data).hexdigest())))
