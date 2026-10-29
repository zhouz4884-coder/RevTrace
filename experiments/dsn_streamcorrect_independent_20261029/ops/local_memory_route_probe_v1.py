import json,pathlib,urllib.request,urllib.error
F=pathlib.Path(__file__).resolve().parents[1];s=json.loads((F/'METADATA_SELECTION_v1_FROZEN.json').read_text(encoding='utf-8'));e=s['selected'][1]['technical_fallback_order'][0]
try:
 req=urllib.request.Request(s['archive_public_url'],headers={'Range':'bytes=%d-%d'%(e['local_offset'],e['local_offset']+511)})
 with urllib.request.urlopen(req,timeout=20) as r:
  b=r.read(513);print(json.dumps(dict(status=r.status,bytes=len(b),content_range=r.headers.get('Content-Range'),local_WAV_written=False,source_id=e['source_id'])))
except Exception as exc:
 print(json.dumps(dict(error_type=type(exc).__name__,http_status=getattr(exc,'code',None),reason_type=type(getattr(exc,'reason',None)).__name__)))
