"""CPU protocol fixtures and real tiny child processes; never serving evidence."""
import hashlib,json,pathlib,subprocess,sys,tempfile,unittest
import run_campaign as op

FAKE_TRIAL = r'''
import argparse,hashlib,json,pathlib,sys
p=argparse.ArgumentParser();p.add_argument("--config");p.add_argument("--manifest");p.add_argument("--out");a=p.parse_args()
c=json.loads(pathlib.Path(a.config).read_bytes());out=pathlib.Path(a.out);out.mkdir()
def put(n,x):(out/n).write_text(json.dumps(x,indent=2),encoding="utf8")
put("CONFIG.json",c)
put("RUN_RECORD.json",dict(experiment_id=c["cell_id"],code_commit=c["source_commit"],frozen_config_sha256=hashlib.sha256((out/"CONFIG.json").read_bytes()).hexdigest()))
behavior=c.get("fixture_behavior","pass")
put("GATE.json",dict(status="PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK" if behavior!="bad_gate" else "FAIL_FIXTURE",source_commit=c["source_commit"],cell_id=c["cell_id"],scope="SYNTHETIC_CPU_PROTOCOL_FIXTURE_NOT_SERVING"))
put("SUMMARY.json",dict(gate="PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT",source_commit=c["source_commit"],cell_id=c["cell_id"],primary=dict(original_quantile_test_pass=False),integrity=dict(original_reference=dict(status="PASS_COMPLETE_ORIGINAL_REFERENCE" if behavior!="bad_reference" else "FAIL_REFERENCE"),all_original_obligations_eventually_processed=True,durable_canonical_steps=1,expected_canonical_steps=1,local_reject_canonical_mutations=0,unexpected_owner_error_records=0,pending_accepted_uncertified_samples={"s":0},unprocessed_all_offered_samples={"s":0}),scope="SYNTHETIC_CPU_PROTOCOL_FIXTURE; zero neural models/calls"))
raise SystemExit(7 if behavior=="exit7" else 0)
'''

def manifest(source):
 commit=op.git(source,"rev-parse","HEAD")
 names=set(subprocess.check_output(["git","-C",str(source),"ls-files","-z"]).decode().split("\0"))-{""}
 return dict(source_commit=commit,files=[dict(path=n,bytes=(source/n).stat().st_size,sha256=op.sha(source/n)) for n in sorted(names)])
def put(path,value):path.write_text(json.dumps(value,indent=2),encoding="utf8")

class CampaignControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source_tmp=tempfile.TemporaryDirectory();cls.nn=pathlib.Path(cls.source_tmp.name)/"source";cls.nn.mkdir()
  (cls.nn/".gitattributes").write_text("* -text\n")
  (cls.nn/".gitignore").write_text("__pycache__/\n*.pyc\n")
  (cls.nn/"resilience_trial.py").write_text(FAKE_TRIAL,encoding="utf8")
  for i in range(56):(cls.nn/f"fixture_{i:02}.txt").write_text("Synthetic CPU source fixture\n")
  subprocess.run(["git","init","-q",str(cls.nn)],check=True)
  op.git(cls.nn,"checkout","-b","codex/cpu-fixture")
  for key,value in (("user.name","CPU Fixture"),("user.email","fixture@invalid"),("core.autocrlf","false")):op.git(cls.nn,"config",key,value)
  op.git(cls.nn,"add",".");op.git(cls.nn,"commit","-qm","Synthetic CPU operator fixture")
  cls.nn_manifest=manifest(cls.nn);cls.nn_commit=cls.nn_manifest["source_commit"]
 @classmethod
 def tearDownClass(cls):cls.source_tmp.cleanup()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  self.nn_manifest_path=self.root/"NN_MANIFEST.json";put(self.nn_manifest_path,self.nn_manifest)
  self.operator_manifest=self.root/"OP_MANIFEST.json";put(self.operator_manifest,manifest(pathlib.Path(op.__file__).parent))
  self.out=self.root/"results"/"campaign";self.cfgdir=self.root/"configs";self.cfgdir.mkdir()
  self.env=self.root/"ENV.json";self.env.write_text('{"scope":"CPU fixture, no models"}')
  self.reference=self.root/"REFERENCE.json";self.reference.write_text('{"scope":"CPU fixture, not neural output"}')
  order=[("conservative","none"),("fullcall","none"),("fullcall","owner_before_durable"),("fullcall","worker_after_asr"),("fullcall","owner_after_durable"),("fullcall","worker_partial_frame")]
  self.cells=[];self.configs={}
  for i,(arm,fault) in enumerate(order):
   cid="CPU_FIXTURE_"+str(i);path=self.cfgdir/(cid+".json")
   cfg=dict(cell_id=cid,arm=arm,source_commit=self.nn_commit,fault=dict(kind=fault),require_reference=True,settings=dict(source_commit=self.nn_commit,sources=[dict(source_id="s",frames=8000)]))
   put(path,cfg);self.configs[cid]=cfg
   self.cells.append(dict(cell_id=cid,arm=arm,fault_kind=fault,config=str(path),config_sha256=op.sha(path),out=str(self.out/"cells"/cid),log=str(self.out/"logs"/(cid+".log"))))
  self.plan=dict(experiment_id="SYNTHETIC_CPU_CAMPAIGN_NOT_SERVING",source_commit=self.nn_commit,source_root=str(self.nn),source_manifest=str(self.nn_manifest_path),source_manifest_sha256=op.sha(self.nn_manifest_path),environment_python=sys.executable,environment_record=str(self.env),environment_sha256=op.sha(self.env),reference_details=str(self.reference),reference_details_sha256=op.sha(self.reference),expected_cells=6,cells=self.cells,raw_result_location=str(self.out),aggregate_summary_location=str(self.out/"SUMMARY.json"),gate_decision_location=str(self.out/"GATE.json"))
  self.plan_path=self.root/"PLAN.json";put(self.plan_path,self.plan)
  self.cpu=self.root/"CPU_GATE.json";put(self.cpu,dict(status="PASS_ALL_FROZEN_SOURCE_CPU_ZERO_SKIP",source_commit=self.nn_commit,tests=249,expected_discovered_tests=249,skipped=0,scope="SYNTHETIC_PREREQUISITE_FIXTURE_NOT249REAL_TESTS"))
  self.pre=self.root/"PREREQUISITE.json"
  self.prerequisite=dict(status=op.PREREQUISITE_STATUS,source_commit=self.nn_commit,source_manifest_sha256=op.sha(self.nn_manifest_path),plan_sha256=op.sha(self.plan_path),tests=249,skipped=0,CPU_gate=str(self.cpu),CPU_gate_sha256=op.sha(self.cpu),environment_record_sha256=op.sha(self.env),reference_details_sha256=op.sha(self.reference),scope="Synthetic CPU schema fixture, not model readiness")
  put(self.pre,self.prerequisite)
 def validate(self):
  return op.validate_inputs(self.plan_path,self.pre,op.sha(self.pre),expected_nn=self.nn_commit)
 def execute(self,probe=lambda:dict(GPU_empty=True,scope="CPU mock, no GPU query")):
  return op.execute(self.plan_path,self.operator_manifest,self.pre,op.sha(self.pre),self.out,probe=probe,expected_nn=self.nn_commit,artifact_root=self.root/"results")
 def prefix(self,index=0):
  c=self.cells[index];self.out.joinpath("cells").mkdir(parents=True,exist_ok=True);self.out.joinpath("logs").mkdir(exist_ok=True)
  with pathlib.Path(c["log"]).open("x") as log:subprocess.run([sys.executable,"-B",str(self.nn/"resilience_trial.py"),"--config",c["config"],"--manifest",str(self.nn_manifest_path),"--out",c["out"]],check=True,stdout=log)
 def behavior(self,index,value):
  cid=self.cells[index]["cell_id"];self.configs[cid]["fixture_behavior"]=value
  put(pathlib.Path(self.cells[index]["config"]),self.configs[cid]);self.cells[index]["config_sha256"]=op.sha(self.cells[index]["config"])
  put(self.plan_path,self.plan);self.prerequisite["plan_sha256"]=op.sha(self.plan_path);put(self.pre,self.prerequisite)
 def test_complete_source_and_prerequisite_are_checked(self):
  _,_,identity,_=self.validate();self.assertEqual(identity["files_verified"],59)
 def test_production_policy_rejects_a_fixture_commit(self):
  with self.assertRaises(op.CampaignError):op.validate_inputs(self.plan_path,self.pre,op.sha(self.pre))
 def test_partial_manifest_is_not_source_identity(self):
  changed=dict(self.nn_manifest);changed["files"]=changed["files"][:-1];put(self.nn_manifest_path,changed)
  with self.assertRaises(op.CampaignError):self.validate()
 def test_skipped_prerequisite_cannot_launch(self):
  self.prerequisite["skipped"]=1;put(self.pre,self.prerequisite)
  with self.assertRaises(op.CampaignError):self.validate()
 def test_changed_frozen_config_cannot_launch(self):
  path=pathlib.Path(self.cells[0]["config"]);path.write_bytes(path.read_bytes()+b"\n")
  with self.assertRaises(op.CampaignError):self.validate()
 def test_all_six_real_tiny_children_count_only_complete_task_reference(self):
  result=self.execute()
  self.assertEqual(result["completed_cells"],6)
  self.assertTrue(all(c["launched_by_this_operator"] for c in result["cells"]))
  self.assertFalse(result["cells"][0]["primary"]["original_quantile_test_pass"])
 def test_valid_prefix_adopted_without_rerun_or_source_attribution(self):
  self.prefix();before=pathlib.Path(self.cells[0]["out"])/"RUN_RECORD.json";stamp=before.stat().st_mtime_ns
  result=self.execute()
  self.assertEqual(result["verified_preexisting_prefix"],1)
  self.assertFalse(result["cells"][0]["launched_by_this_operator"])
  self.assertEqual(before.stat().st_mtime_ns,stamp)
  self.assertEqual(sum(c["launched_by_this_operator"] for c in result["cells"]),5)
 def test_nonprefix_existing_trial_is_never_skipped(self):
  self.prefix(1)
  with self.assertRaises(op.CampaignError):self.execute()
  self.assertFalse(pathlib.Path(self.cells[0]["out"]).exists())
 def test_incomplete_or_running_prefix_is_not_adopted(self):
  self.prefix();(pathlib.Path(self.cells[0]["out"])/"GATE.json").unlink()
  with self.assertRaises(op.CampaignError):self.execute()
  self.assertFalse(pathlib.Path(self.cells[1]["out"]).exists())
 def test_first_child_nonzero_stops_scope_without_retry(self):
  self.behavior(0,"exit7")
  with self.assertRaises(op.CampaignError):self.execute()
  gate=op.read(self.out/"GATE.json");self.assertEqual(gate["completed_cells"],0);self.assertEqual(gate["child_returncode"],7)
  self.assertFalse(pathlib.Path(self.cells[1]["out"]).exists())
 def test_exit_zero_but_bad_reference_is_not_completion(self):
  self.behavior(0,"bad_reference")
  with self.assertRaises(op.CampaignError):self.execute()
  self.assertEqual(op.read(self.out/"GATE.json")["completed_cells"],0)
  self.assertFalse(pathlib.Path(self.cells[1]["out"]).exists())
 def test_exit_zero_but_failure_gate_is_not_completion(self):
  self.behavior(0,"bad_gate")
  with self.assertRaises(op.CampaignError):self.execute()
  self.assertEqual(op.read(self.out/"GATE.json")["completed_cells"],0)
 def test_GPU_ownership_must_be_released_after_each_child(self):
  calls=[]
  def probe():
   calls.append(1)
   if len(calls)==3:raise op.CampaignError("CPU mock occupied GPU after child")
   return dict(GPU_empty=True,scope="CPU mock")
  with self.assertRaises(op.CampaignError):self.execute(probe)
  self.assertEqual(op.read(self.out/"GATE.json")["completed_cells"],0)
  self.assertFalse(pathlib.Path(self.cells[1]["out"]).exists())
 def test_prior_campaign_cannot_be_restarted(self):
  self.execute()
  with self.assertRaises(op.CampaignError):self.execute()
 def test_runtime_echo_not_equal_to_frozen_input_is_rejected(self):
  self.prefix();path=pathlib.Path(self.cells[0]["out"])/"CONFIG.json";data=op.read(path);data["arm"]="changed";put(path,data)
  with self.assertRaises(op.CampaignError):op.validate_child(self.cells[0],self.configs[self.cells[0]["cell_id"]],self.nn_commit)
 def test_empty_input_debt_dictionary_cannot_hide_a_source(self):
  self.prefix();path=pathlib.Path(self.cells[0]["out"])/"SUMMARY.json";data=op.read(path);data["integrity"]["pending_accepted_uncertified_samples"]={};put(path,data)
  with self.assertRaises(op.CampaignError):op.validate_child(self.cells[0],self.configs[self.cells[0]["cell_id"]],self.nn_commit)

if __name__=="__main__":unittest.main()
