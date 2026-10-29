import json,pathlib,urllib.request,urllib.error
P=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_independent_20261029');s=json.loads((P/'METADATA_SELECTION_v1_FROZEN.json').read_text());entry=s['selected'][1]['technical_fallback_order'][0]
rows=[]
for suffix in ('','?download=true'):
 try:
  request=urllib.request.Request(s['archive_public_url']+suffix,headers={'Range':f"bytes={entry['local_offset']}-{entry['local_offset']+511}", 'Cache-Control':'no-cache'})
  with urllib.request.urlopen(request,timeout=20) as response:b=response.read(513);rows.append(dict(public_route_suffix=suffix,status=response.status,bytes=len(b),content_range=response.headers.get('Content-Range')))
 except Exception as exc:
  reason=getattr(exc,'reason',None);rows.append(dict(public_route_suffix=suffix,error_type=type(exc).__name__,http_status=getattr(exc,'code',None),reason_type=type(reason).__name__,reason_errno=getattr(reason,'errno',None),ssl_verify_code=getattr(reason,'verify_code',None),reason_text=str(reason)[:200] if not isinstance(reason,str) else reason[:200]))
print(json.dumps(dict(source_id=entry['source_id'],same_frozen_selected_member=True,rows=rows)))
