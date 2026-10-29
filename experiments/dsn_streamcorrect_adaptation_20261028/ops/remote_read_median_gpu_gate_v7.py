import pathlib,json
O=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028');out=O/'median_gpu_gate_v7';r={}
for name in ['GATE.json','SUMMARY.json']:
 p=out/name
 if p.exists():r[name]=json.loads(p.read_text())
p=out/'ACTUAL_NATIVE_MEDIAN_INPUT.pt';r['actual_tensor_exists']=p.exists()
if p.exists():r['actual_tensor_serialized_bytes']=p.stat().st_size
log=O/'median_gpu_gate_v7.log'
if log.exists():
 with log.open('rb') as f:f.seek(max(0,log.stat().st_size-5000));r['log_tail']=f.read().decode(errors='replace')
print(json.dumps(r,indent=2))
