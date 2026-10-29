"""Record the root's resource allocation from completed scope receipts."""
from pathlib import Path
import json, datetime
F=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/'
a=json.loads((F/'ALLOCATION_TEMPLATE.json').read_text())
a.update(root_allocated=True,native_scope_executed='two_witnesses_gate_passed_all12_formal_complete',
         allocated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         local_current_preflight=json.loads((F/'LOCAL_PREFLIGHT_BEFORE_GPU_v1.json').read_text()),
         resource_release='Native original14, primary/feedback/ready CPU and bounded IO complete; RxK same-F24/96 CPU/IO complete. Only this timed GPU scope allocated.')
rows=[('joint24_execution',B+'physical_retirement_20261028/dsn_joint_controller_v1/GATE.json','d9bbb546e513a841d6ca20acce9a5bf6c80ab711c479f6a0a6cee1028341464c',{'gate':'PASS_ALL_FROZEN_EXECUTION_CELLS','completed':24}),
      ('joint24_analysis',B+'physical_retirement_20261028/dsn_joint_analysis_v2/GATE.json','4f85f52643d3ecb4d98245c360458544f1879632493e903776f37b99f704ba89',{'gate':'PASS_OFFLINE_RECOUNT'}),
      ('native_prescribed_scope_decision',B+'dsn_streamcorrect_20261028/native_campaign_v8_continuation_auditfix_v1/GATE.json','ecbeeaffd7d1abb894570d26bb41646aec836d5eac5d454f01da9630c31fedfa',{'status':'PASS_TWELVE_ACTUAL_NATIVE_CELLS_AND_FULL_HISTORY_EQUIVALENCE'}),
      ('native_analysis',B+'dsn_streamcorrect_20261028/native_postanalyses_v8/SUMMARY.json','772179553156df83f1b2ffb40409c50717fc97129d8e853d04f3c5f9203c805f',{'status':'COMPLETED_POSTANALYSES_ORIGINAL_NATIVE_GATES_PRESERVED'})]
a['prerequisite_evidence']=[dict(label=l,path=p,sha256=h,required_json_fields=v) for l,p,h,v in rows]
a['additional_finished_quality_scope']=dict(path=B+'physical_retirement_20261028/dsn_joint_same_F_support_v1/GATE.json',sha256='30f7f4eca2bbbfba512f1f055b3d3e53e06a0446c338fa095918711b1b0b3bcb',gate='PASS_ALL24_SAME_F_SUPPORT_RECOUNT')
with (F/'ALLOCATION_v1.json').open('x',encoding='utf8',newline='\n') as f:json.dump(a,f,indent=2);f.write('\n')
print(json.dumps({'root_allocated':True,'frozen_plan_changed':False,'new_neural_calls':0}))
