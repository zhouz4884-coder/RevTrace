"""Bounded metadata audit and official metadata-only archive discovery.

Never opens/downloads WAV, transcript members, model weights or model outputs.
The sole new download is OpenSLR68's official metadata.tar.gz, kept on8TB.
"""
import hashlib,json,shlex,sys
from pathlib import Path

E=Path(__file__).resolve().parents[1];R=E.parents[1]
PY='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old=R/'experiments/dsn_native_confirmation_20261102/selection/METADATA_SELECTION_v2/HISTORICAL_EXCLUSION_INPUTS.json'
    selected=R/'experiments/dsn_native_confirmation_20261102/selection/METADATA_SELECTION_v2/METADATA_SELECTION.json'
    exclusions=json.loads(old.read_bytes());selection=json.loads(selected.read_bytes())
    prior=sorted(exclusions['excluded_speakers']);added=sorted(s['speaker_id'] for s in selection['selected_sources'])
    assert len(prior)==43 and len(set(added))==8
    params=dict(prior=prior,added=added,old_exclusions_sha256=sha(old),old_selection_sha256=sha(selected))
    code='PARAMS='+repr(params)+'\n'+r'''
import collections,datetime,hashlib,io,json,pathlib,re,tarfile,urllib.request
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
catalog=B/'projects/revtrace_dsn_native_confirmation_20261102/ARCHIVE_ENTRIES_0.json'
raw=catalog.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest=='efd03c4e9ef086548d353ead2efacb826afcc6440e1c5b866faf79d8e176ccc4'
entries=json.loads(raw);speakers=collections.defaultdict(list)
for row in entries:
 p=row.get('path','')
 if not p.startswith('StreamCorrect/aishell1_testset/') or not p.lower().endswith('.wav'):continue
 match=re.search(r'BAC009(S\d{4})W\d{4}',p)
 if not match:continue
 speakers[match.group(1)].append(dict(path=p,bytes=row['bytes'],estimated_seconds=(row['bytes']-44)/32000))
excluded=set(PARAMS['prior'])|set(PARAMS['added']);remaining=sorted(set(speakers)-excluded)
summary=[]
for speaker,rows in sorted(speakers.items()):
 durations=[r['estimated_seconds'] for r in rows];low=[r for r in rows if 6<=r['estimated_seconds']<12];high=[r for r in rows if 12<=r['estimated_seconds']<=20]
 summary.append(dict(speaker_id=speaker,catalog_utterances=len(rows),excluded_by_prior43=speaker in PARAMS['prior'],excluded_by_new8=speaker in PARAMS['added'],min_estimated_seconds=min(durations),max_estimated_seconds=max(durations),natural_6to12_estimated_count=len(low),natural_12to20_estimated_count=len(high),eligible_metadata_rows=low+high if speaker in remaining else []))
O=B/'results/revtrace/dsn_strengthening_v16_20261111/metadata_options_v1';O.mkdir(parents=True,exist_ok=False)
urls=['https://openslr.magicdatatech.com/resources/68/metadata.tar.gz','https://openslr.elda.org/resources/68/metadata.tar.gz','https://openslr.trmal.net/resources/68/metadata.tar.gz']
attempts=[];download=None;index=[]
for url in urls:
 try:
  request=urllib.request.Request(url,headers={'User-Agent':'RevTrace-metadata-audit/1.0'})
  with urllib.request.urlopen(request,timeout=30) as response:
   payload=response.read(8*1024*1024+1);assert len(payload)<=8*1024*1024
   headers={k:response.headers.get(k) for k in ('Content-Type','Content-Length','Last-Modified','ETag','Accept-Ranges')}
   final=response.url
  with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as tar:
   index=[dict(path=m.name,bytes=m.size,is_file=m.isfile()) for m in tar.getmembers()]
  target=O/'magicdata_metadata.tar.gz';target.write_bytes(payload)
  download=dict(requested_url=url,final_url=final,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),path=str(target),headers=headers,members=index,content_extracted=False)
  attempts.append(dict(url=url,status='success'));break
 except Exception as exc:attempts.append(dict(url=url,status='failed',error=type(exc).__name__+':'+str(exc)))
result=dict(status='BOUNDED_METADATA_AVAILABILITY_NOT_FRESH_HISTORY_CENSUS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),catalog_path=str(catalog),catalog_bytes=len(raw),catalog_sha256=digest,raw_catalog_entries=len(entries),same_split_catalog_speakers=sorted(speakers),catalog_speaker_count=len(speakers),prior43=PARAMS['prior'],new8=PARAMS['added'],prior_exclusions_sha256=PARAMS['old_exclusions_sha256'],selection_sha256=PARAMS['old_selection_sha256'],remaining_speakers=remaining,per_speaker=summary,scope='old catalog plus old43/new8 exclusions only; no fresh complete history census, no audio/header/reference/model read, no GPU',official_metadata_archive=download,download_attempts=attempts)
(O/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
'''
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    try:
        i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=120);i.write(code);i.flush();i.channel.shutdown_write();raw,err=o.read(),e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode('utf8',errors='replace')
        result=json.loads(raw);result['local_reader_sha256']=sha(Path(__file__))
        p=E/'review/METADATA_OPTIONS_BOUND_AUDIT_v1.json';assert not p.exists();p.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
        print(json.dumps({k:result[k] for k in ('status','catalog_speaker_count','remaining_speakers','official_metadata_archive','download_attempts')},indent=2))
    finally:c.close()

if __name__=='__main__':main()
