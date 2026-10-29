"""Exercise the real main loop's config/provenance namespace, with I/O fixture.

This is a CPU-only structural control, not a synthetic scientific observation.
Unrelated source/collection/ref gates are explicit fixture stubs. The actual
configuration/provenance load and source-object comparison run before the
fidelity sentinel. The earlier Path/dict shadow bug fails this control.
"""
import hashlib,json,pathlib,tempfile,types,unittest
from unittest.mock import patch
import analyze_confirmation as m

class ReachedFidelity(Exception):pass
class DriverNamespaceControl(unittest.TestCase):
 def test_real_main_preserves_provenance_dictionary_while_loading_config_path(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=pathlib.Path(temporary);bank=root/'bank';(bank/'campaign').mkdir(parents=True);(bank/'one').mkdir();frozen=root/'configs';frozen.mkdir()
   def put(path,value):path.write_text(json.dumps(value),encoding='utf-8');return str(path)
   def h(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
   sources=[dict(source_id=str(i),speaker_id='S'+str(i),technical_fallback_index=0,frames=8000,reference='A') for i in range(4)]
   provenance=dict(source_receipt=dict(sources=sources,method_source_commit=m.RUNTIME,metadata_only_before_neural=True),
      metadata_selection=dict(selected=[dict(initial_source_id=s['source_id'],speaker_id=s['speaker_id']) for s in sources],excluded_speakers=['old'],selection_created_utc='2026-10-29T02:00Z',metadata_only_before_neural=True),
      appraisal=dict(source_ids=[s['source_id'] for s in sources],speaker_ids=[s['speaker_id'] for s in sources],method_source_commit=m.RUNTIME),
      method_freeze=dict(method_source_commit=m.RUNTIME,created_utc='2026-10-29T01:00Z'))
   cfg=dict(analysis_source_commit='fixture',collection_root=str(bank),frozen_config_dir=str(frozen),expected_reference_calls=68,experiment_id='CPU_NAMESPACE_FIXTURE')
   for key,value in provenance.items():cfg[key]=put(root/(key+'.json'),value);cfg[key+'_sha256']=h(cfg[key])
   actual=dict(arm=m.ARMS[0],settings=dict(source_commit=m.RUNTIME,sources=[sources[0]]));put(frozen/'one.json',actual);put(bank/'one/CONFIG.json',actual)
   reference=put(root/'reference.json',[{}]*68);cfg['reference_details']=reference
   cfg['reference_gate']=put(root/'reference_gate.json',dict(status='PASS_ALL_LOCKED_NEW_SPEAKER_ORIGINAL_FULL_REFERENCE_CALLS',reference_details_sha256=h(reference),imported_model_runtime_commit=m.RUNTIME));cfg['reference_gate_sha256']=h(cfg['reference_gate'])
   cell=dict(cell_id='one',config='/remote/one.json',config_sha256=h(frozen/'one.json'))
   plan=dict(source_commit=m.RUNTIME,cells=[cell],reference_details_sha256=h(reference));cfg['campaign_plan']=put(root/'plan.json',plan);cfg['campaign_plan_sha256']=h(cfg['campaign_plan'])
   put(bank/'campaign/CONFIG.json',plan);put(bank/'campaign/GATE.json',dict(completed_cells=16,planned_cells=16,all_full_task_fidelity_pass=True))
   put(bank/'COLLECTION_MANIFEST.json',dict(all_bytes_equal=True,source_commit=m.RUNTIME,files=[]));cfg['collection_manifest_sha256']=h(bank/'COLLECTION_MANIFEST.json')
   for name,value in [('ORIGIN.json',dict(origin_perf=0)),('CANONICAL_HISTORIES.json',{'0':[]})]:put(bank/'one'/name,value)
   for name in ('consumer.jsonl','native_jobs.jsonl','events.jsonl','canonical_wal.jsonl'):(bank/'one'/name).write_bytes(b'')
   put(root/'manifest.json',dict(source_commit='fixture',files=[]));put(root/'config.json',cfg)
   def git(*args,**kwargs):
    command=args[0]
    return 'fixture\n' if 'rev-parse' in command else ''
   argv=['analyze_confirmation.py','--config',str(root/'config.json'),'--manifest',str(root/'manifest.json'),'--out',str(root/'out')]
   with patch.object(m.subprocess,'check_output',side_effect=git),patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='',stderr='CPU fixture')),patch.object(m,'fidelity',side_effect=ReachedFidelity),patch.object(m.sys,'argv',argv):
    with self.assertRaises(ReachedFidelity):m.main()

if __name__=='__main__':unittest.main()
