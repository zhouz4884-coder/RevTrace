"""Check original nested backbone access using any existing HF login only.

No new login, gate acceptance, account creation, token output or stored token.
"""
import pathlib,json,urllib.request,urllib.error,hashlib,datetime
O=pathlib.Path(__file__).resolve().parents[1]/'backbone_access_v1';O.mkdir(exist_ok=False)
repo='meta-llama/Llama-3.2-1B-Instruct';rows=[]
try:
 from huggingface_hub import get_token
 token=get_token()
except ImportError:token=None
for label,headers in [('anonymous',{}),('existing_login',{'Authorization':'Bearer '+token} if token else None)]:
 if headers is None:rows.append(dict(route=label,status='NO_EXISTING_LOGIN'));continue
 row={'route':label,'public_repo':repo}
 try:
  with urllib.request.urlopen(urllib.request.Request(f'https://huggingface.co/{repo}/resolve/main/config.json',headers=headers),timeout=25) as r:
   b=r.read(100001);assert len(b)<100001
   row.update(status=r.status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 except urllib.error.HTTPError as e:row.update(status=e.code,error='HTTPError')
 except Exception as e:row.update(status='ERROR',error=type(e).__name__)
 rows.append(row)
token=None
summary=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpu_launched=False,gate_accepted=False,requests=rows)
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
