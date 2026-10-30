"""Add controls for final source/environment/reference/actual Consumer binding."""
import pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];S=F/'formal_operator_source_v2';p=S/'test_campaign.py';x=p.read_text(encoding='utf8')
def change(before,after):
 global x
 assert x.count(before)==1,before
 x=x.replace(before,after)
x=x.replace('249','253')
change('import argparse,hashlib,json,pathlib,sys','import argparse,hashlib,json,pathlib,sys,os')
change('put("CONFIG.json",c)','put("CONFIG.json",c)\nput("ENVIRONMENT.json",dict(PYTORCH_CUDA_ALLOC_CONF=os.environ.get("PYTORCH_CUDA_ALLOC_CONF"),PYTORCH_ALLOC_CONF=os.environ.get("PYTORCH_ALLOC_CONF")))')
change('unexpected_owner_error_records=0,pending_accepted_uncertified_samples','unexpected_owner_error_records=0,consumer_binding=dict(applied_durable_facts=1,durable_facts_not_yet_consumed=0,duplicate_actual_durable_applications=0),pending_accepted_uncertified_samples')
change('   put(path,cfg);self.configs[cid]=cfg','   cfg.update(reference_details=str(self.reference),reference_details_sha256=op.sha(self.reference),reference_gate=str(self.refgate),reference_gate_sha256=op.sha(self.refgate),reference_kind="short_bdfa_static_source_mapping",runtime_environment={})\n   put(path,cfg);self.configs[cid]=cfg')
change('reference_gate_sha256=op.sha(self.refgate),expected_cells=6,','reference_gate_sha256=op.sha(self.refgate),reference_kind="short_bdfa_static_source_mapping",runtime_environment={},expected_cells=6,')
extra='''
 def test_cell_cannot_select_a_different_reference_than_the_actual_campaign_gate(self):
  cid=self.cells[0]["cell_id"];self.configs[cid]["reference_details_sha256"]="0"*64;path=pathlib.Path(self.cells[0]["config"]);put(path,self.configs[cid]);self.cells[0]["config_sha256"]=op.sha(path);put(self.plan_path,self.plan)
  with self.assertRaises(op.CampaignError):self.validate()
 def test_durable_completion_cannot_hide_unapplied_actual_Consumer_fact(self):
  self.prefix();path=pathlib.Path(self.cells[0]["out"])/"SUMMARY.json";data=op.read(path);data["integrity"]["consumer_binding"]["durable_facts_not_yet_consumed"]=1;put(path,data)
  with self.assertRaises(op.CampaignError):op.validate_child(self.cells[0],self.configs[self.cells[0]["cell_id"]],self.nn_commit)
 def ready_rows(self,bad=False):
  folder=self.root/"ready"/"owner_e0";folder.mkdir(parents=True);rows=[]
  for i,(slot,inc) in enumerate((("full0",1),("full1",1),("full0",2))):rows.append(dict(physical_slot=slot,physical_incarnation=inc,event=dict(kind="ready",pid=9000+i,gpu=i%2,environment=dict(PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True",PYTORCH_ALLOC_CONF=None))))
  if bad:rows[-1]["event"]["environment"]["PYTORCH_ALLOC_CONF"]="unfrozen_alias"
  (folder/"worker_results.jsonl").write_bytes(b"".join(json.dumps(row,separators=(",",":")).encode()+b"\\n" for row in rows));return self.root/"ready"
 def test_actual_ready_receipts_cover_initial_workers_and_replacement(self):
  rows=op.ready_environment_audit(self.ready_rows(),{"PYTORCH_CUDA_ALLOC_CONF":"expandable_segments:True"},True);self.assertEqual(len(rows),3);self.assertEqual(rows[-1]["incarnation"],2)
 def test_replacement_cannot_inherit_an_unfrozen_allocator_alias(self):
  with self.assertRaises(op.CampaignError):op.ready_environment_audit(self.ready_rows(True),{"PYTORCH_CUDA_ALLOC_CONF":"expandable_segments:True"},True)
 def test_actual_tiny_children_inherit_the_same_frozen_allocator_condition(self):
  runtime={"PYTORCH_CUDA_ALLOC_CONF":"expandable_segments:True"};put(self.env,dict(scope="Synthetic CPU child, no CUDA/model",runtime_environment=runtime));self.plan.update(runtime_environment=runtime,environment_sha256=op.sha(self.env));self.prerequisite["environment_record_sha256"]=op.sha(self.env);put(self.pre,self.prerequisite)
  for cell in self.cells:
   cfg=self.configs[cell["cell_id"]];cfg["runtime_environment"]=runtime;put(pathlib.Path(cell["config"]),cfg);cell["config_sha256"]=op.sha(cell["config"])
  put(self.plan_path,self.plan);result=self.execute();self.assertEqual(result["completed_cells"],6)
  for cell in self.cells:
   actual=op.read(pathlib.Path(cell["out"])/"ENVIRONMENT.json");self.assertEqual(actual["PYTORCH_CUDA_ALLOC_CONF"],"expandable_segments:True");self.assertIsNone(actual["PYTORCH_ALLOC_CONF"])
'''
change('if __name__=="__main__":unittest.main()',extra+'\nif __name__=="__main__":unittest.main()');p.write_bytes(x.encode())
subprocess.run(['git','-C',str(S),'add','.'],check=True);subprocess.run(['git','-C',str(S),'commit','-qm','Freeze final-source formal26 CPU operator with exact reference, Consumer and per-incarnation allocator bindings'],check=True)
freeze=(F/'ops/freeze_formal_operator_v1.py').read_text(encoding='utf8').replace('v1','v2').replace('9492d3f9cb35e2b2849ec020817750a221248f0e','4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47').replace('LOCAL_CPU_FORMAL_OPERATOR21','LOCAL_CPU_FORMAL_OPERATOR26')
target=F/'ops/freeze_formal_operator_v2.py';assert not target.exists();target.write_bytes(freeze.encode())
cpu=(F/'ops/run_formal_operator_cpu_v1.py').read_text(encoding='utf8').replace('v1','v2').replace('V1','V2').replace('21','26');target=F/'ops/run_formal_operator_cpu_v2.py';assert not target.exists();target.write_bytes(cpu.encode())
