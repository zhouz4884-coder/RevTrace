"""Bounded public metadata capture, not a manuscript or a baseline implementation."""
from pathlib import Path
import argparse,datetime,hashlib,json,platform,sys,urllib.request
from common import put,file_sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    m=json.loads(a.source_manifest.read_text());root=Path(__file__).parent
    for r in m['files']:assert file_sha(root/r['path'])==r['sha256']
    a.out.mkdir();put(a.out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),GPU_calls=0))
    urls={k:'https://api.crossref.org/works/'+d for k,d in [('aries','10.1145/128765.128770'),('ragcache','10.1145/3768628'),('flink','10.14778/3137765.3137777'),('whisper_streaming','10.18653/v1/2023.ijcnlp-demo.3')]}
    urls['dsp_public_note']='https://api2.openreview.net/notes?id=YZ5k2dVj6O'
    put(a.out/'FREEZE.json',dict(experiment_id='REVTRACE-RELATED-PUBLIC-METADATA-20261028',code_commit=m['code_commit'],source_manifest_sha256=file_sha(a.source_manifest),environment_sha256=file_sha(a.out/'ENVIRONMENT.json'),urls=urls,raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'RESULT.json'),gate_decision_location=str(a.out/'GATE.json'),scope='read-only public endpoints; no authentication or challenge bypass; failures retained'))
    rows=[]
    for key,url in urls.items():
        r=dict(key=key,url=url,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'RevTrace-CitationVerification/1.0'})
            with urllib.request.urlopen(req,timeout=18) as resp:b=resp.read(1024*1024+1);assert len(b)<=1024*1024
            obj=json.loads(b);(a.out/(key+'.json')).write_bytes(b)
            r.update(status='PUBLIC_METADATA_RETRIEVED',bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
            if key=='dsp_public_note':
                n=obj['notes'][0];r['title']=n['content']['title'];r['venue']=n['content'].get('venue');r['venueid']=n['content'].get('venueid')
            else:
                n=obj['message'];r.update(title=n['title'],type=n['type'],container=n.get('container-title'),published=n.get('published'),published_online=n.get('published-online'),published_print=n.get('published-print'),doi=n['DOI'])
        except Exception as e:r.update(status='SOURCE_FAILED_NOT_INFERRED',error=type(e).__name__+': '+str(e))
        rows.append(r)
    put(a.out/'RESULT.json',dict(rows=rows,GPU_calls=0))
    put(a.out/'GATE.json',dict(gate='PARTIAL_METADATA_CAPTURE' if any(r['status']!='PUBLIC_METADATA_RETRIEVED' for r in rows) else 'PASS_PUBLIC_METADATA_CAPTURE',manual_primary_source_verification_separate=True,GPU_calls=0))
    print(json.dumps(rows,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
