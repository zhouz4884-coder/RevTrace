"""T1 Crossref lookups for formally published substrate comparators only."""
from pathlib import Path
import hashlib,json,urllib.parse,urllib.request
W=Path(__file__).resolve().parent;O=W/'crossref_v2';O.mkdir(exist_ok=False)
queries=[('seda_conference','10.1145/502034.502057','SEDA'),
 ('seda_journal_duplicate','10.1145/502059.502057','SEDA'),
 ('rifl','10.1145/2815400.2815416','Implementing linearizability')]
out=[]
for key,doi,expected in queries:
 url='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'RevTrace-reference-verification/1.0'})
  with urllib.request.urlopen(req,timeout=20) as r:raw=r.read(2_000_000)
  data=json.loads(raw);m=data['message'];assert m['DOI'].lower()==doi.lower()
  assert expected.casefold() in m['title'][0].casefold()
  assert m['type'] in ['proceedings-article','journal-article']
  (O/(key+'.json')).write_bytes(raw)
  out.append(dict(key=key,doi=doi,status='VERIFIED_FORMALLY_PUBLISHED_METADATA',title=m['title'][0],
   container=m.get('container-title'),type=m['type'],published=m.get('published'),page=m.get('page'),
   authors=[dict(given=a.get('given'),family=a.get('family')) for a in m['author']],
   sha256=hashlib.sha256(raw).hexdigest(),source=url,
   selected=key!='seda_journal_duplicate',duplicate_note='same SEDA article, use conference manifestation only' if key.startswith('seda') else None))
 except Exception as e:out.append(dict(key=key,doi=doi,status='MANUAL_NEEDED',error_type=type(e).__name__))
(O/'VERIFICATION.json').write_text(json.dumps(dict(records=out,preprints_used=False,metadata_not_fulltext_review=True),indent=2)+'\n')
print(json.dumps(out))
