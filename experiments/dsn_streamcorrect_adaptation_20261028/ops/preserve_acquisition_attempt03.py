import pathlib,json,shutil,datetime,hashlib
O=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028/assets_v1')
h=json.loads((O/'DETACHED_LAUNCH_HANDLE_attempt03.json').read_text());p=pathlib.Path('/proc')/str(h['pid'])
if p.exists():
 stat=(p/'stat').read_text().rsplit(')',1)[1].split()
 assert int(stat[19])!=h['start_ticks'] or stat[0]=='Z','owned writer still alive'
out=O/'attempts/attempt03_modelscope_transport_switch';out.mkdir(parents=True,exist_ok=False)
for name in ['GATE.json','PROGRESS.json','PUBLIC_PLAN.json','ACTIVE_DOWNLOAD_HANDLE.json','DETACHED_LAUNCH_HANDLE_attempt03.json','TRANSPORT_SWITCH_attempt03_REQUEST.json']:
 q=O/name
 if q.exists():shutil.copyfile(q,out/name)
partial=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/models/revtrace_streamcorrect_20261028/llama32_1b_instruct_f8e6b/model.safetensors.partial')
r=dict(status='PRESERVED_INTENTIONAL_PUBLIC_TRANSPORT_SWITCH',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),partial_bytes=partial.stat().st_size,
 retained_partial=True,old_exact_writer_dead_or_zombie=True,old_log=str(O/'acquisition_attempt03_detached.log'),asset_plan_unchanged=True,
 actual_next_transport='public HF unsloth/Llama-3.2-1B-Instruct revision 5a8abab4a5d6f164389b1079fb721cfab8d7126c',
 expected_final_sha256='1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f')
(out/'PRESERVATION.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
