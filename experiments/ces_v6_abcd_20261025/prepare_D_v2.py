"""Freeze eligible D comparisons after A/B/C, before new-source execution."""
from pathlib import Path
import argparse,hashlib,json,random,xml.etree.ElementTree as X
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
assert read(O/'ABC_SUMMARY.json')['GPU_queue_closed']
assert read(O/'B_SORTED_SUMMARY.json')['GPU_queue_closed']
assert read(O/'A_audit/SUMMARY.json')['failures']==[]
assert read(O/'C_audit/SUMMARY.json')['failures']==[]
suite=X.fromstring((O/'LINUX_CPU_D_FOCUSED.xml').read_text()).find('testsuite');assert suite.get('failures')=='0' and suite.get('errors')=='0' and suite.get('tests')=='377'
bgate=read(O/'B_independent_analysis/SUMMARY.json');cgate=read(O/'C_independent_analysis_v2/SUMMARY.json')
assert not cgate['causal_risk_integration_GO'],'A GO risk estimate requires a separate frozen supported observable model; do not invent one here'
source=P/'runtime_D';m=read(source/'SOURCE_MANIFEST.json')
for f in m['files']:assert sha(source/f['path'])==f['sha256']
cal=O/'training_v1/CALIBRATION.json';folder=P/'configs_D';folder.mkdir()
save(folder/'closed_hard.json',{'max_deferrals':2,'promise_quantile':.9,'max_successors_per_session':2,'max_scenario_combinations':16,'max_candidate_plans':8,'promise_tolerance_s':1e-6,'cache_mode':'memoized','guard_mode':'hard'})
save(folder/'fine.json',{'policy':'fine'})
save(folder/'anchor.json',{'policy':'anchor_cost','minimum_support':8,'risk_quantile':.9,'initial_plan_budget_s':.005,'dispatch_allowance_s':.002})
# run_matrix confines configuration names to configs; new immutable names avoid overwrites.
for f in folder.iterdir():
 target=P/'configs'/('D_'+f.name);assert not target.exists();target.write_bytes(f.read_bytes())
methods=['fine','standard','anchor_cost']
if bgate['integration_GO']:methods.append('fine_original_operator')
source_rel='projects/revtrace_ces_v6_abcd_20261025/runtime_D';sources={'runtime_D':source_rel}
manifests={'development':'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json','heldout':'results/revtrace/ces_v6_abcd_20261025/heldout_source_v1/MANIFEST.json'}
for pool,traffics in [('development',['mixed']),('heldout',['clean','mixed'])]:
 cells=[]
 for traffic in traffics:
  for arrival in ['sync','staggered']:
   for repeat in range(3):
    order=methods.copy();random.Random(20261025+repeat+int(arrival=='staggered')*17+int(traffic=='mixed')*101+int(pool=='heldout')*1009).shuffle(order)
    for method in order:
     manifest=manifests[pool]
     cells.append({'pool':pool,'label':method,'source':'runtime_D','method':'cost' if method=='anchor_cost' else 'fine' if method=='fine_original_operator' else method,
      'arrival':arrival,'traffic':traffic,'repeat':repeat,'seed':20261025+repeat,'sessions':16,
      'manifest':manifest,'manifest_sha256':sha(B/manifest),'calibration':str(cal.relative_to(B)),'calibration_sha256':sha(cal),
      'closed':'D_closed_hard.json','options':'D_anchor.json' if method=='anchor_cost' else 'D_fine.json',
      'fallback_layout':'selective_reprocess' if bgate['integration_GO'] and method!='fine_original_operator' else 'selective'})
 stage='D_development' if pool=='development' else 'D_heldout'
 save(P/('PLAN_'+stage+'.json'),{'experiment_id':'REVTRACE-CES-V6-ABCD-20261025','stage':stage,'sources':sources,'cells':cells,'source_commit':m['code_commit'],
  'source_manifest_sha256':sha(source/'SOURCE_MANIFEST.json'),'B_operator_gate':bgate,'C_risk_gate':cgate,
  'controllers':{n:sha(P/n) for n in ['run_matrix.py','audit_v6.py','audit_closed_helpers_v2.py','summarize_v6.py','audit_anchor_policy_v2.py','run_D_sequence_v2.py','prepare_D_v2.py']},
  'configuration_sha256':{f.name:sha(f) for f in folder.iterdir()},
  'expected_repeats':3,'rules':'D_DESIGN_FREEZE.md; no retuning after development or held-out; all mandatory strong controls kept','new_source_input_policy':'Source/speaker and audio SHA metadata selected before V6 GPU results'})
 print(json.dumps({'stage':stage,'cells':len(cells),'methods':methods,'plan_sha256':sha(P/('PLAN_'+stage+'.json')),'source_commit':m['code_commit']}))
save(O/'D_GATE_DECISIONS.json',{'A':'Focused CPU377 pass; actual-credit wiring repaired in D-only source','B_shared_operator':bgate['decision'],'C_causal_risk':cgate['reason'],'no_causal_algorithm_superiority_claim_without_risk_arm':True,'paper_not_modified':True})
