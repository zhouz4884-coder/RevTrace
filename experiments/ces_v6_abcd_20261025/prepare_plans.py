from pathlib import Path
import argparse,hashlib,json,random
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025';C=P/'configs';assert not C.exists();C.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
base={'max_deferrals':2,'promise_quantile':.9,'max_successors_per_session':2,'max_scenario_combinations':16,'max_candidate_plans':8,'promise_tolerance_s':1e-6}
save(C/'closed_reference.json',base)
for mode in ['hard','soft','aging']:save(C/('closed_'+mode+'.json'),dict(base,cache_mode='memoized',guard_mode=mode))
save(C/'fine.json',{'policy':'fine'})
save(C/'anchor.json',{'policy':'anchor_cost','minimum_support':8,'risk_quantile':.9,'initial_plan_budget_s':.005,'dispatch_allowance_s':.002})
for tag,hold in [('0',0.),('075',.75),('15',1.5)]:save(C/('hold_'+tag+'.json'),{'policy':'fine','authority_hold_seconds':hold,'hold_at_window':5})
sources={'baseline_v5':'projects/revtrace_ces_v5_closed_loop_20261025/runtime',
 'runtime_A':'projects/revtrace_ces_v6_abcd_20261025/runtime_A','runtime':'projects/revtrace_ces_v6_abcd_20261025/runtime'}
manifest='results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
old_cal='projects/revtrace_ces_v5_closed_loop_20261025/CALIBRATION.json';new_cal='results/revtrace/ces_v6_abcd_20261025/training_v1/CALIBRATION.json'
def cell(label,arrival,traffic,repeat):
 method='fine' if label.startswith('fine') or label.startswith('hold') else 'cost' if label=='anchor_cost' else 'causal'
 source='baseline_v5' if label=='v5_reference' else 'runtime_A' if label in ['cached','guard_soft','guard_aging'] else 'runtime'
 closed='closed_reference.json' if source=='baseline_v5' else 'closed_soft.json' if label=='guard_soft' else 'closed_aging.json' if label=='guard_aging' else 'closed_hard.json'
 options='anchor.json' if label=='anchor_cost' else 'fine.json' if label=='fine' else None
 if label.startswith('hold_'):options=label+'.json'
 cal=new_cal if label=='anchor_cost' else old_cal
 return {'pool':'development','label':label,'source':source,'method':method,'arrival':arrival,'traffic':traffic,'repeat':repeat,'seed':20261025+repeat,
  'sessions':16,'manifest':manifest,'manifest_sha256':sha(B/manifest),'calibration':cal,'calibration_sha256':sha(B/cal),
  'closed':closed,'options':options,'fallback_layout':'selective'}
A=[]
for repeat in range(3):
 labels=['fine','v5_reference','cached','guard_soft','guard_aging','anchor_cost']
 random.Random(20261025+repeat).shuffle(labels)
 A.extend(cell(label,'staggered','mixed',repeat) for label in labels)
 labels=['fine','anchor_cost'];labels=labels if repeat%2==0 else labels[::-1]
 A.extend(cell(label,'sync','mixed',repeat) for label in labels)
save(P/'PLAN_A.json',{'experiment_id':'REVTRACE-CES-V6-ABCD-20261025','stage':'A','sources':sources,'cells':A,'expected_repeats':3,
 'scope':'Same-target safety gate; cache control uses original V5 vs isolated planner-only source. Anchor is a changed decision policy.',
 'no_auto_tuning':True})
Ccells=[]
for traffic in ['clean','mixed']:
 for repeat in range(3):
  holds=['hold_0','hold_075','hold_15'];random.Random(20261025+repeat+(0 if traffic=='clean' else 100)).shuffle(holds)
  Ccells.extend(cell(label,'sync',traffic,repeat) for label in holds)
save(P/'PLAN_C.json',{'experiment_id':'REVTRACE-CES-V6-ABCD-20261025','stage':'C','sources':sources,'cells':Ccells,'expected_repeats':3,
 'randomized_unit':'Fresh-process entire16-session run, blocked by input/seed/F2 condition; rows are not IID',
 'treatment':'Installation hold only at window5; current running GPU0 work cannot be canceled',
 'primary_future_outcome':'Paid GPU0 physical batches first issued after treatment receipt and covering windows>5, with original in-flight work separately counted'})
print(json.dumps({'A_cells':len(A),'C_cells':len(Ccells),'A_plan_sha256':sha(P/'PLAN_A.json'),'C_plan_sha256':sha(P/'PLAN_C.json')}))
