"""Derive the separately versioned formal serial operator from audited pilot code."""
import pathlib
F=pathlib.Path(__file__).resolve().parents[1];old=F/'operator_source_v2';new=F/'formal_operator_source_v1';new.mkdir()
def replace(text,before,after):
 assert before in text,before
 return text.replace(before,after)
code=(old/'run_campaign.py').read_text(encoding='utf8')
code=replace(code,'Serial frozen six-cell operator.','Serial frozen formal28/8-cell operator.')
code=replace(code,'EXPECTED_CELLS=6','EXPECTED_CELLS=None')
code=replace(code,'need(plan["expected_cells"]==len(plan["cells"])==expected_cells,"frozen complete scope changed")','''if expected_cells is None:
  kind=plan.get("campaign_kind");need(kind in ("formal_short28","formal_sustained8"),"unknown formal campaign scope")
  expected_cells={"formal_short28":28,"formal_sustained8":8}[kind]
 need(plan["expected_cells"]==len(plan["cells"])==expected_cells,"frozen complete scope changed")''')
code=replace(code,'need(prerequisite["source_commit"]==expected_nn and prerequisite["plan_sha256"]==sha(plan_path),"prerequisite source/plan differs")','need(prerequisite["source_commit"]==expected_nn,"complete prior source prerequisite differs")')
code=replace(code,'need(prerequisite["environment_record_sha256"]==plan["environment_sha256"] and prerequisite["reference_details_sha256"]==plan["reference_details_sha256"],"prerequisite environment/reference differs")','''need(prerequisite["environment_record_sha256"]==plan["environment_sha256"],"prerequisite environment differs")
 need(sha(plan["reference_gate"])==plan["reference_gate_sha256"],"actual complete reference gate bytes differ")
 reference=read(plan["reference_gate"])
 need(reference.get("status") in ("PASS_PRIOR_ACTUAL_BDFA_SHORT85_REFERENCE_EXPORT","PASS_CONTINUOUS_ORIGINAL_AND_ALL_RESTORED_NATIVE_EDGES"),"actual complete reference failed")
 need(reference.get("reference_details_sha256")==plan["reference_details_sha256"],"actual reference gate does not bind complete details")
 if plan.get("campaign_kind")=="formal_sustained8":
  need(reference.get("source_commit")==expected_nn and reference.get("original_continuous_no_between_step_restore") is True and reference.get("reference_full_calls")==reference.get("restored_full_calls")==875 and reference.get("all_original_full_state_C_IDs_equal") is True,"sustained original-reference scope differs")
 if plan.get("campaign_kind")=="formal_short28":
  need(reference.get("combined_calls")==85 and reference.get("all_reference_tags_remain_actual_BDFA") is True,"short85 original-reference scope differs")''')
code=replace(code,'need([(c["arm"],c["fault_kind"]) for c in plan["cells"][:2]]==[("conservative","none"),("fullcall","none")],"normal controls must precede fault development")','''# All order/source/arm/fault choices are made in the frozen plan. This
 # operator never substitutes a source or retries a completed/failed trial.''')
code=replace(code,'out=pathlib.Path(out).resolve()\n need(out==pathlib.Path(plan["raw_result_location"]).resolve()', 'expected_cells=plan["expected_cells"]\n out=pathlib.Path(out).resolve()\n need(out==pathlib.Path(plan["raw_result_location"]).resolve()')
code=replace(code,'PASS_ALL_FROZEN_SIX_DEVELOPMENT_TRIALS_AND_COMPLETE_TASK_REFERENCE','PASS_ALL_FROZEN_FORMAL_TRIALS_AND_COMPLETE_TASK_REFERENCE')
code=replace(code,'scope="Six development trials, not formal24 or sustained validation. Separate trace-refinement audit remains required."','scope="All frozen formal child trials. Child actual timings and deadline failures retained. Independent trace audit remains separate."')
(new/'run_campaign.py').write_bytes(code.encode('utf8'))
tests=(old/'test_campaign.py').read_text(encoding='utf8')
tests=replace(tests,'self.reference=self.root/"REFERENCE.json";self.reference.write_text(\'{"scope":"CPU fixture, not neural output"}\')','''self.reference=self.root/"REFERENCE.json";self.reference.write_text('{"scope":"CPU fixture, not neural output"}')
  self.refgate=self.root/"REFERENCE_GATE.json";put(self.refgate,dict(status="PASS_PRIOR_ACTUAL_BDFA_SHORT85_REFERENCE_EXPORT",reference_details_sha256=op.sha(self.reference),combined_calls=85,all_reference_tags_remain_actual_BDFA=True))''')
tests=replace(tests,'reference_details_sha256=op.sha(self.reference),expected_cells=6,','reference_details_sha256=op.sha(self.reference),reference_gate=str(self.refgate),reference_gate_sha256=op.sha(self.refgate),expected_cells=6,')
tests=replace(tests,'expected_nn=self.nn_commit)','expected_nn=self.nn_commit,expected_cells=6)')
tests=replace(tests,'expected_nn=self.nn_commit,artifact_root=','expected_nn=self.nn_commit,expected_cells=6,artifact_root=')
insert='''
 def test_failed_reference_gate_cannot_launch(self):
  put(self.refgate,dict(status="FAIL_RESTORE_EQUIVALENCE_WITH_DIAGNOSTIC_CONTROLS_PRESERVED",reference_details_sha256=op.sha(self.reference)));self.plan["reference_gate_sha256"]=op.sha(self.refgate);put(self.plan_path,self.plan)
  with self.assertRaises(op.CampaignError):self.validate()
 def test_gate_must_bind_the_actual_complete_reference_bytes(self):
  x=op.read(self.refgate);x["reference_details_sha256"]="0"*64;put(self.refgate,x);self.plan["reference_gate_sha256"]=op.sha(self.refgate);put(self.plan_path,self.plan)
  with self.assertRaises(op.CampaignError):self.validate()
 def test_production_campaign_cannot_be_a_partial_matrix(self):
  self.plan["campaign_kind"]="formal_short28";put(self.plan_path,self.plan)
  with self.assertRaises(op.CampaignError):op.validate_inputs(self.plan_path,self.pre,op.sha(self.pre),expected_nn=self.nn_commit)
 def test_complete_prior_source_prerequisite_is_not_relabelled_as_new_plan(self):
  self.prerequisite["plan_sha256"]="0"*64;put(self.pre,self.prerequisite)
  _,_,_,pre=self.validate();self.assertEqual(pre["plan_sha256"],"0"*64)
 def test_frozen_arm_order_can_be_reversed_without_a_policy_rewrite(self):
  self.cells[0],self.cells[1]=self.cells[1],self.cells[0];put(self.plan_path,self.plan)
  plan,_,_,_=self.validate();self.assertEqual(plan["cells"][0]["arm"],"fullcall")
'''
tests=replace(tests,'if __name__=="__main__":unittest.main()',insert+'\nif __name__=="__main__":unittest.main()')
(new/'test_campaign.py').write_bytes(tests.encode('utf8'))
for leaf in ('.gitattributes','.gitignore'):(new/leaf).write_bytes((old/leaf).read_bytes())
(new/'README.md').write_text('''# Frozen formal serial operator

Runs exactly a frozen short28 or sustained8 plan, using the unchanged native
runtime in its separately verified clean execution source. Requires the actual
short85 reference or independent continuous-original875/restore875 gate. Prior
runtime/assets/environment/zero-skip CPU prerequisite stays linked to its real
pilot plan; it is never relabelled as execution of this formal plan. Every child
retains actual source, config, full original task, all offered/EOS, and original
deadline failures. Failed or partial children stop with the executed prefix
preserved; no retries, source substitution, metric replay, or clock reset.

Operator CPU fixtures create tiny actual processes and no neural models. They
are separate from production GPU ownership probes and serving measurements.
''',encoding='utf8')
print(str(new))
