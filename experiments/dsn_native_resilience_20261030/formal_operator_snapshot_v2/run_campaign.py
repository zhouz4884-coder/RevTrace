"""Serial frozen formal28/8-cell operator. This file contains no neural implementation."""
from __future__ import annotations
import argparse,datetime,hashlib,json,os,pathlib,platform,re,subprocess,sys,traceback

NN_COMMIT="4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47"
NN_FILES=59
EXPECTED_CELLS=None
MIN_CPU_TESTS=253
RESULTS_ROOT=pathlib.Path("/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace")
PREREQUISITE_STATUS="PASS_COMPLETE_RUNTIME_SOURCE_26_ASSETS_AUTHOR_ENV_AND_ALL_CPU_NO_NEURAL"
TRIAL_STATUS="PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK"
METRICS_STATUS="PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT"
REFERENCE_STATUS="PASS_COMPLETE_ORIGINAL_REFERENCE"

class CampaignError(RuntimeError): pass

def need(ok,message):
 if not ok:raise CampaignError(message)

def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open("rb") as stream:
  for part in iter(lambda:stream.read(1024*1024),b""):h.update(part)
 return h.hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def put(path,value,exclusive=False):
 path=pathlib.Path(path);data=(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode()
 if exclusive:
  with path.open("xb") as stream:stream.write(data)
 else:
  temporary=path.with_name("."+path.name+"."+str(os.getpid())+".tmp")
  with temporary.open("xb") as stream:stream.write(data)
  os.replace(temporary,path)

def git(root,*args):
 return subprocess.check_output(["git","-C",str(root),*args],text=True,encoding="utf8").strip()

def verify_checkout(root,manifest_path,expected_commit=None,expected_files=None):
 root=pathlib.Path(root).resolve();manifest_path=pathlib.Path(manifest_path)
 manifest=read(manifest_path);commit=manifest["source_commit"]
 need(re.fullmatch("[0-9a-f]{40}",commit) is not None,"full actual source commit required")
 if expected_commit is not None:need(commit==expected_commit,"source commit changed")
 need(os.path.normcase(str(pathlib.Path(git(root,"rev-parse","--show-toplevel")).resolve()))==os.path.normcase(str(root)),"source is not its own clean checkout")
 need(git(root,"rev-parse","HEAD")==commit,"actual source HEAD differs")
 need(git(root,"rev-parse","--verify",commit+"^{commit}")==commit,"full source commit does not resolve")
 need(not git(root,"status","--porcelain","--untracked-files=all"),"source checkout is dirty")
 tracked=set(subprocess.check_output(["git","-C",str(root),"ls-files","-z"]).decode().split("\0"))-{""}
 rows=manifest["files"];need(len({r["path"] for r in rows})==len(rows),"duplicate manifest path")
 need(tracked=={r["path"] for r in rows},"incomplete source manifest")
 if expected_files is not None:need(len(rows)==expected_files,"wrong complete source file count")
 for row in rows:
  raw_path=root/row["path"];path=raw_path.resolve()
  need(path.is_relative_to(root) and path.is_file() and not raw_path.is_symlink(),"unsafe source manifest path")
  need(path.stat().st_size==row["bytes"] and sha(path)==row["sha256"],"source bytes differ: "+row["path"])
 return dict(source_commit=commit,source_manifest_sha256=sha(manifest_path),files_verified=len(rows),source_clean=True)

def gpu_empty():
 processes=subprocess.check_output(["nvidia-smi","--query-compute-apps=pid","--format=csv,noheader"],text=True,timeout=15).strip()
 need(not processes,"GPU is occupied; do not launch or continue")
 devices=subprocess.check_output(["nvidia-smi","--query-gpu=index,name,memory.used","--format=csv,noheader,nounits"],text=True,timeout=15).strip().splitlines()
 need(len(devices)==2 and all("RTX 3090" in r for r in devices),"expected two dedicated RTX3090 boards")
 need(all(float(r.rsplit(",",1)[1].strip())<128 for r in devices),"CUDA memory not physically released")
 return dict(observed_utc=now(),compute_processes=[],device_rows=devices,GPU_empty=True)

def validate_inputs(plan_path,prerequisite_path,prerequisite_sha256,*,expected_nn=NN_COMMIT,
                    expected_files=NN_FILES,expected_cells=EXPECTED_CELLS,min_cpu=MIN_CPU_TESTS):
 plan_path=pathlib.Path(plan_path);plan=read(plan_path)
 need(plan["source_commit"]==expected_nn,"frozen neural source changed")
 if expected_cells is None:
  kind=plan.get("campaign_kind");need(kind in ("formal_short28","formal_sustained8"),"unknown formal campaign scope")
  expected_cells={"formal_short28":28,"formal_sustained8":8}[kind]
 need(plan["expected_cells"]==len(plan["cells"])==expected_cells,"frozen complete scope changed")
 need(len({c["cell_id"] for c in plan["cells"]})==expected_cells,"cell IDs reused")
 need(sha(plan["source_manifest"])==plan["source_manifest_sha256"],"neural manifest hash changed")
 identity=verify_checkout(plan["source_root"],plan["source_manifest"],expected_nn,expected_files)
 need(sha(prerequisite_path)==prerequisite_sha256,"prerequisite bytes differ")
 prerequisite=read(prerequisite_path)
 need(prerequisite["status"]==PREREQUISITE_STATUS,"complete prerequisite did not pass")
 need(prerequisite["source_commit"]==expected_nn,"complete prior source prerequisite differs")
 need(prerequisite["source_manifest_sha256"]==identity["source_manifest_sha256"],"prerequisite manifest differs")
 need(prerequisite["skipped"]==0 and prerequisite["tests"]>=min_cpu,"complete zero-skip CPU prerequisite absent")
 need(sha(prerequisite["CPU_gate"])==prerequisite["CPU_gate_sha256"],"CPU gate hash changed")
 cpu=read(prerequisite["CPU_gate"])
 need(cpu["status"]=="PASS_ALL_FROZEN_SOURCE_CPU_ZERO_SKIP" and cpu["source_commit"]==expected_nn,"wrong CPU gate source/status")
 need(cpu["tests"]==cpu["expected_discovered_tests"]==prerequisite["tests"] and cpu["skipped"]==0,"CPU discovery incomplete or skipped")
 for key in ("environment_record","reference_details"):
  expected=plan["environment_sha256"] if key=="environment_record" else plan["reference_details_sha256"]
  need(sha(plan[key])==expected,"frozen "+key+" differs")
 need(prerequisite["environment_record_sha256"]==plan["environment_sha256"],"prerequisite environment differs")
 runtime_env=plan.get("runtime_environment",{})
 need(runtime_env in ({},{"PYTORCH_CUDA_ALLOC_CONF":"expandable_segments:True"}),"unknown frozen allocator condition")
 need(read(plan["environment_record"]).get("runtime_environment",{})==runtime_env,"frozen environment and plan allocator differ")
 if expected_nn==NN_COMMIT:need(runtime_env=={"PYTORCH_CUDA_ALLOC_CONF":"expandable_segments:True"},"final production allocator condition missing")
 need(sha(plan["reference_gate"])==plan["reference_gate_sha256"],"actual complete reference gate bytes differ")
 reference=read(plan["reference_gate"])
 need(reference.get("status") in ("PASS_PRIOR_ACTUAL_BDFA_SHORT85_REFERENCE_EXPORT","PASS_CONTINUOUS_ORIGINAL_AND_ALL_RESTORED_NATIVE_EDGES"),"actual complete reference failed")
 need(reference.get("reference_details_sha256")==plan["reference_details_sha256"],"actual reference gate does not bind complete details")
 if plan.get("campaign_kind")=="formal_sustained8":
  need(reference.get("source_commit")==expected_nn and reference.get("original_continuous_no_between_step_restore") is True and reference.get("reference_full_calls")==reference.get("restored_full_calls")==875 and reference.get("all_original_full_state_C_IDs_equal") is True,"sustained original-reference scope differs")
 if plan.get("campaign_kind")=="formal_short28":
  need(reference.get("combined_calls")==85 and reference.get("all_reference_tags_remain_actual_BDFA") is True,"short85 original-reference scope differs")
 configs={}
 for cell in plan["cells"]:
  need(sha(cell["config"])==cell["config_sha256"],"frozen cell config differs")
  cfg=read(cell["config"])
  need(cfg["cell_id"]==cell["cell_id"] and cfg["arm"]==cell["arm"],"cell identity/arm differs")
  need(cfg["source_commit"]==cfg["settings"]["source_commit"]==expected_nn,"cell actual execution source differs")
  need(cfg.get("require_reference",True) is True,"complete original reference cannot be disabled")
  need(cfg.get("fault",{}).get("kind","none")==cell["fault_kind"],"frozen fault site changed")
  for key in ("reference_details","reference_details_sha256","reference_gate","reference_gate_sha256","reference_kind"):
   need(cfg.get(key)==plan.get(key),"cell reference differs from the actual frozen campaign reference: "+key)
  need(cfg.get("runtime_environment",{})==runtime_env,"cell and campaign allocator conditions differ")
  configs[cell["cell_id"]]=cfg
 # All order/source/arm/fault choices are made in the frozen plan. This
 # operator never substitutes a source or retries a completed/failed trial.
 return plan,configs,identity,prerequisite

def ready_environment_audit(out,expected,require_ready):
 checked=[];slots=set()
 for path in sorted(pathlib.Path(out).glob("owner_e*/worker_results.jsonl")):
  with path.open("rb") as stream:
   for raw in stream:
    if b'"kind":"ready"' not in raw:continue
    row=json.loads(raw);event=row.get("event",{})
    if event.get("kind")!="ready":continue
    environment=event["environment"]
    need(environment.get("PYTORCH_CUDA_ALLOC_CONF")==expected.get("PYTORCH_CUDA_ALLOC_CONF"),"initial/replacement worker allocator differs")
    need(environment.get("PYTORCH_ALLOC_CONF") is None,"unfrozen allocator alias reached a model worker")
    slots.add(row["physical_slot"]);checked.append(dict(owner=path.parent.name,slot=row["physical_slot"],incarnation=row["physical_incarnation"],pid=event["pid"],gpu=event["gpu"],allocator=environment.get("PYTORCH_CUDA_ALLOC_CONF")))
 if require_ready:need(len(checked)>=2 and slots=={"full0","full1"},"both actual initial NN workers need readable frozen allocator receipts")
 return checked

def validate_child(cell,cfg,nn_commit):
 out=pathlib.Path(cell["out"])
 for name in ("CONFIG.json","RUN_RECORD.json","SUMMARY.json","GATE.json"):
  need((out/name).is_file(),"trial incomplete; missing "+name)
 runtime=read(out/"CONFIG.json");record=read(out/"RUN_RECORD.json")
 # The frozen input and runtime echo use separate byte encodings.  Compare
 # all values, and bind each byte hash to its own actual file.
 need(runtime==cfg,"runtime config differs from frozen input")
 need(record["code_commit"]==nn_commit and record["experiment_id"]==cell["cell_id"],"trial execution provenance differs")
 need(record["frozen_config_sha256"]==sha(out/"CONFIG.json"),"runtime config echo hash differs")
 gate=read(out/"GATE.json");summary=read(out/"SUMMARY.json")
 need(gate["status"]==TRIAL_STATUS and gate["source_commit"]==nn_commit and gate["cell_id"]==cell["cell_id"],"trial execution gate failed")
 need(summary["gate"]==METRICS_STATUS and summary["source_commit"]==nn_commit and summary["cell_id"]==cell["cell_id"],"complete task recount failed")
 integrity=summary["integrity"]
 need(integrity["original_reference"]["status"]==REFERENCE_STATUS,"complete original-task reference did not pass")
 need(integrity["all_original_obligations_eventually_processed"] is True,"accepted input obligations incomplete")
 expected_steps=sum((s["frames"]+7999)//8000 for s in cfg["settings"]["sources"])
 need(integrity["durable_canonical_steps"]==integrity["expected_canonical_steps"]==expected_steps>0,"complete Canonical scope differs")
 need(integrity["local_reject_canonical_mutations"]==0 and integrity["unexpected_owner_error_records"]==0,"trial integrity gate failed")
 consumer=integrity["consumer_binding"]
 need(consumer["applied_durable_facts"]==expected_steps and consumer["durable_facts_not_yet_consumed"]==0 and consumer["duplicate_actual_durable_applications"]==0,"actual Consumer did not apply every durable input fact exactly once")
 runtime_env=cfg.get("runtime_environment",{})
 if runtime_env:
  environment=read(out/"ENVIRONMENT.json")
  need(environment.get("PYTORCH_CUDA_ALLOC_CONF")==runtime_env["PYTORCH_CUDA_ALLOC_CONF"] and environment.get("PYTORCH_ALLOC_CONF") is None,"trial Supervisor allocator differs")
 worker_environments=ready_environment_audit(out,runtime_env,nn_commit==NN_COMMIT)
 for field in ("pending_accepted_uncertified_samples","unprocessed_all_offered_samples"):
  need(set(integrity[field])=={s["source_id"] for s in cfg["settings"]["sources"]} and all(v==0 for v in integrity[field].values()),"trial has remaining or missing input debt")
 return dict(cell_id=cell["cell_id"],arm=cell["arm"],fault_kind=cell["fault_kind"],
             neural_source_commit=nn_commit,original_reference_status=REFERENCE_STATUS,
             gate_sha256=sha(out/"GATE.json"),summary_sha256=sha(out/"SUMMARY.json"),
             frozen_input_sha256=cell["config_sha256"],runtime_config_echo_sha256=sha(out/"CONFIG.json"),
             checked_canonical_steps=integrity["durable_canonical_steps"],worker_environment_receipts=worker_environments,
             primary=summary.get("primary"),scope="Actual child measurements; no operator proxy or P99 success requirement")

def verified_prefix(plan,configs,*,probe):
 prefix=[];gap=False;allowed_out={pathlib.Path(c["out"]).name for c in plan["cells"]};allowed_logs={pathlib.Path(c["log"]).name for c in plan["cells"]}
 base=pathlib.Path(plan["raw_result_location"])
 for folder,allowed in ((base/"cells",allowed_out),(base/"logs",allowed_logs)):
  if folder.exists():need(all(p.name in allowed for p in folder.iterdir()),"unplanned artifact in trial directories")
 for cell in plan["cells"]:
  out,log=pathlib.Path(cell["out"]),pathlib.Path(cell["log"])
  exists=out.exists() or log.exists()
  if not exists:gap=True;continue
  need(not gap,"existing trials are not a contiguous frozen prefix")
  need(out.is_dir() and log.is_file(),"partial/running prefix cannot be adopted")
  result=validate_child(cell,configs[cell["cell_id"]],plan["source_commit"]);probe()
  result.update(launched_by_this_operator=False,execution_origin="verified_preexisting_frozen_prefix")
  prefix.append(result)
 return prefix

def execute(plan_path,manifest_path,prerequisite_path,prerequisite_sha256,out,*,
            probe=gpu_empty,expected_nn=NN_COMMIT,expected_files=NN_FILES,
            expected_cells=EXPECTED_CELLS,min_cpu=MIN_CPU_TESTS,artifact_root=RESULTS_ROOT):
 operator=verify_checkout(pathlib.Path(__file__).resolve().parent,manifest_path)
 plan,configs,nn,prerequisite=validate_inputs(plan_path,prerequisite_path,prerequisite_sha256,
                                            expected_nn=expected_nn,expected_files=expected_files,
                                            expected_cells=expected_cells,min_cpu=min_cpu)
 expected_cells=plan["expected_cells"]
 out=pathlib.Path(out).resolve()
 need(out==pathlib.Path(plan["raw_result_location"]).resolve(),"operator output must equal frozen campaign result location")
 need(out.is_relative_to(pathlib.Path(artifact_root).resolve()),"campaign results must stay on the designated experiment disk")
 need(pathlib.Path(plan["aggregate_summary_location"]).resolve()==out/"SUMMARY.json" and pathlib.Path(plan["gate_decision_location"]).resolve()==out/"GATE.json","summary/gate paths differ from plan")
 for cell in plan["cells"]:
  need(pathlib.Path(cell["out"]).resolve().parent==out/"cells" and pathlib.Path(cell["log"]).resolve().parent==out/"logs","child output/log escaped campaign")
 for name in ("CONFIG.json","RUN_RECORD.json","PROGRESS.json","SUMMARY.json","GATE.json"):
  need(not (out/name).exists(),"prior campaign operator cannot be restarted or overwritten")
 probe()
 prefix=verified_prefix(plan,configs,probe=probe)
 out.mkdir(parents=True,exist_ok=True)
 (out/"cells").mkdir(exist_ok=True);(out/"logs").mkdir(exist_ok=True)
 put(out/"CONFIG.json",plan,True)
 env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),runtime_environment=plan.get("runtime_environment",{}),
          operator_source=operator,neural_source=nn,scope="Serial process operator only; child NN code remains separately frozen.")
 put(out/"ENVIRONMENT.json",env,True)
 run=dict(experiment_id=plan["experiment_id"]+"_SERIAL_OPERATOR",
          operator_source_commit=operator["source_commit"],neural_source_commit=expected_nn,
          frozen_plan=str(plan_path),frozen_plan_sha256=sha(plan_path),
          operator_manifest_sha256=sha(manifest_path),prerequisite=str(prerequisite_path),
          prerequisite_sha256=prerequisite_sha256,environment_record=str(out/"ENVIRONMENT.json"),
          environment_sha256=sha(out/"ENVIRONMENT.json"),raw_result_location=str(out),
          aggregate_summary_location=str(out/"SUMMARY.json"),gate_decision_location=str(out/"GATE.json"),
          started_utc=now(),adopted_verified_prefix=len(prefix),
          scope="Prefix entries were executed by their original launcher, not retroactively attributed to this operator.")
 put(out/"RUN_RECORD.json",run,True)
 completed=list(prefix);current=None;child_returncode=None
 def progress(stage,**extra):
  put(out/"PROGRESS.json",dict(stage=stage,completed=len(completed),planned=expected_cells,
                             current=current["cell_id"] if current else None,
                             operator_source_commit=operator["source_commit"],
                             neural_source_commit=expected_nn,updated_utc=now(),**extra))
 try:
  progress("validated_prefix")
  for cell in plan["cells"][len(completed):]:
   current=cell;child_returncode=None
   verify_checkout(plan["source_root"],plan["source_manifest"],expected_nn,expected_files)
   need(sha(cell["config"])==cell["config_sha256"],"config changed before child launch")
   probe();need(not pathlib.Path(cell["out"]).exists() and not pathlib.Path(cell["log"]).exists(),"refuse to rerun any trial")
   command=[plan["environment_python"],"-B",str(pathlib.Path(plan["source_root"])/"resilience_trial.py"),
            "--config",cell["config"],"--manifest",plan["source_manifest"],"--out",cell["out"]]
   with pathlib.Path(cell["log"]).open("x",encoding="utf8") as log:
    child_environment=dict(os.environ,PYTHONDONTWRITEBYTECODE="1");child_environment.pop("PYTORCH_ALLOC_CONF",None);child_environment.update(plan.get("runtime_environment",{}))
    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                           close_fds=True,env=child_environment)
    progress("actual_child_running",child_pid=child.pid,command=command)
    child_returncode=child.wait()
   need(child_returncode==0,"actual trial subprocess failed")
   result=validate_child(cell,configs[cell["cell_id"]],expected_nn)
   result["GPU_release"]=probe()
   result.update(launched_by_this_operator=True,execution_origin="this_frozen_operator",
                 child_returncode=child_returncode)
   completed.append(result);progress("cell_complete")
  verify_checkout(plan["source_root"],plan["source_manifest"],expected_nn,expected_files)
  verify_checkout(pathlib.Path(__file__).resolve().parent,manifest_path,operator["source_commit"])
  final=dict(status="PASS_ALL_FROZEN_FORMAL_TRIALS_AND_COMPLETE_TASK_REFERENCE",
             experiment_id=plan["experiment_id"],operator_source_commit=operator["source_commit"],
             neural_source_commit=expected_nn,completed_cells=len(completed),planned_cells=expected_cells,
             verified_preexisting_prefix=len(prefix),cells=completed,completed_utc=now(),
             actual_serving_status="Child evidence only; P99 misses are retained and do not invalidate safe-recovery completion.",
             scope="All frozen formal child trials. Child actual timings and deadline failures retained. Independent trace audit remains separate.")
  put(out/"SUMMARY.json",final,True);put(out/"GATE.json",final,True);progress("complete")
  return final
 except BaseException as exc:
  failure=dict(status="FAIL_FROZEN_CAMPAIGN_PREFIX_PRESERVED_NO_RESTART",
               experiment_id=plan["experiment_id"],operator_source_commit=operator["source_commit"],
               neural_source_commit=expected_nn,completed_cells=len(completed),planned_cells=expected_cells,
               cells=completed,failed_cell=current["cell_id"] if current else None,
               child_returncode=child_returncode,error_type=type(exc).__name__,reason=str(exc),
               scope="No retry, replacement, source/config change, or skip of a failed child.")
  put(out/"failure.txt.json",dict(traceback=traceback.format_exc()),True)
  put(out/"SUMMARY.json",failure,True);put(out/"GATE.json",failure,True);progress("failed")
  raise

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--plan",type=pathlib.Path,required=True);p.add_argument("--manifest",type=pathlib.Path,required=True)
 p.add_argument("--prerequisite",type=pathlib.Path,required=True);p.add_argument("--prerequisite-sha256",required=True)
 p.add_argument("--out",type=pathlib.Path,required=True);a=p.parse_args()
 result=execute(a.plan,a.manifest,a.prerequisite,a.prerequisite_sha256,a.out)
 print(json.dumps({k:v for k,v in result.items() if k!="cells"},indent=2))
if __name__=="__main__":main()
