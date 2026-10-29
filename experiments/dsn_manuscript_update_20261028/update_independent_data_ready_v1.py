"""Index the byte-verified new-source acquisition without claiming neural results."""
import datetime, hashlib, json
from pathlib import Path
T=Path(__file__).resolve().parent; R=T.parents[1]
I=R/'experiments/dsn_streamcorrect_independent_20261029'
receipt=I/'SOURCE_RECEIPT_v1.json'
assert hashlib.sha256(receipt.read_bytes()).hexdigest()=='2040995aa06a5c7958479fe42397d65e299c8a4505de18b35f44099edd9e3b9e'
assert (I/'DATA_READY_AND_IO_RELEASE_v1.json').is_file()
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
p=T/'ACTIVE_STATE.json'; x=json.loads(p.read_text(encoding='utf8'))
x['status']='FINAL_METHOD_FROZEN_FOUR_NEW_SPEAKER_AUDIO_VERIFIED_REFERENCE_PREPARING'
x['updated_utc']=stamp
x['gpu_next']='Original-full new4 sequential reference, then unchanged-bdfa final16 paired service only.'
x['final_independent_sources'].update(status='ALL_FOUR_FIXED_INITIAL_CANDIDATES_BYTE_VERIFIED_DATA_IO_RELEASED',receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),unique_offered_audio_seconds=33.169875,unique_frontiers=68,planned_service_cells=16,timed_service_results_exist=False)
p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
p=R/'experiments/LATEST_RESEARCH.json'; y=json.loads(p.read_text(encoding='utf8'));y.update(status=x['status'],updated_utc=stamp,scope='All prior scopes plus native19 and encoder13 complete; eager encoder route STOP by measured cost. Final full-call method frozen before new4speaker metadata; all4initial WAVs verified and dataIO released. Original-full reference and final16 controlled service pending; full paper argument updated, final release pending.')
p.write_text(json.dumps(y,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(x['status'])
