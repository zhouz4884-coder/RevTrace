import pathlib,json,urllib.request,datetime
O=pathlib.Path(__file__).resolve().parents[1]/'base_model_metadata_v1';O.mkdir(exist_ok=False)
url='https://huggingface.co/api/models/fixie-ai/ultravox-v0_5-llama-3_2-1b'
with urllib.request.urlopen(url,timeout=25) as r:b=r.read(1_000_001);assert len(b)<1_000_001
(O/'MODEL.json').write_bytes(b);x=json.loads(b)
print(json.dumps({k:x.get(k) for k in ('id','sha','private','gated','cardData','siblings')},indent=2))
