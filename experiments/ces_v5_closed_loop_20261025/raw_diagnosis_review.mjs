// Independent read-only arithmetic on the frozen 72-cell event diagnostic extracts.
// No GPU replay, unchosen-action counterfactual, or modification of original evidence.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const input=path.join(root,'precollection');
const output=path.join(root,'RAW_DIAGNOSIS_REVIEW.json');
if(fs.existsSync(output))throw Error('Refuse to overwrite completed independent review');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function csv(text){
  const records=[];let row=[],field='',quoted=false;
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}
    else if(c===','&&!quoted){row.push(field);field='';}
    else if(c==='\n'&&!quoted){row.push(field.replace(/\r$/,''));if(row.some(v=>v!==''))records.push(row);row=[];field='';}
    else field+=c;
  }
  if(quoted)throw Error('Unclosed CSV quote');
  if(field||row.length){row.push(field.replace(/\r$/,''));records.push(row);}
  const headers=records.shift();
  if(new Set(headers).size!==headers.length)throw Error('Duplicate CSV columns');
  return records.map(r=>{if(r.length!==headers.length)throw Error('CSV width');return Object.fromEntries(headers.map((k,i)=>[k,r[i]===''?null:r[i]==='True'?true:r[i]==='False'?false:/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(r[i])?Number(r[i]):r[i]]));});
}
const sourceNames=['DIAG_GROUPS.csv','DECISION_ACTIVATION.csv','SERVICE_PROMISES.csv','OPERATION_CALIBRATION.csv','SNAPSHOT_REPLAY.csv','HOTSPOTS.csv','PROPOSAL_TAIL_CELLS.csv','PROPOSAL_TAIL_SUMMARY.json','SERVICE_CELLS.csv','PHYSICAL_COSTS.csv','SUMMARY.json'];
const sources=Object.fromEntries(sourceNames.map(n=>[n,{path:path.join(input,n),sha256:hash(path.join(input,n))}]));
const read=n=>csv(fs.readFileSync(path.join(input,n),'utf8'));
const diag=read('DIAG_GROUPS.csv'),decisions=read('DECISION_ACTIVATION.csv'),promises=read('SERVICE_PROMISES.csv'),calibration=read('OPERATION_CALIBRATION.csv'),snapshots=read('SNAPSHOT_REPLAY.csv'),hotspots=read('HOTSPOTS.csv'),tails=read('PROPOSAL_TAIL_CELLS.csv'),service=read('SERVICE_CELLS.csv');
const tailSummary=JSON.parse(fs.readFileSync(sources['PROPOSAL_TAIL_SUMMARY.json'].path,'utf8'));
const summary=JSON.parse(fs.readFileSync(sources['SUMMARY.json'].path,'utf8'));
if(service.length!==72||tails.length!==72||diag.length!==24||summary.failures.length||summary.actual_model_calls!==2672)throw Error('Formal denominator changed');
const quantile=(xs,q)=>{if(!xs.length)return null;const x=xs.toSorted((a,b)=>a-b),a=(x.length-1)*q,l=Math.floor(a);return x[l]+(a-l)*((x[l+1]??x[l])-x[l]);};
const median=xs=>quantile(xs,.5),sum=(xs,key)=>xs.reduce((s,x)=>s+(key?x[key]:x),0);
function identity(cell){const m=cell.match(/^validation-(sync|staggered)-mixed-(.+)-r([012])$/);if(!m)throw Error('Unexpected formal cell '+cell);return {arrival:m[1],label:m[2],repeat:Number(m[3])};}
const group=(rows,key)=>{const m=new Map;for(const r of rows){const k=key(r);if(!m.has(k))m.set(k,[]);m.get(k).push(r);}return m;};
const stats=xs=>({n:xs.length,min:xs.length?Math.min(...xs):null,median:median(xs),mean:xs.length?sum(xs)/xs.length:null,P90:quantile(xs,.9),P95:quantile(xs,.95),P99:quantile(xs,.99),max:xs.length?Math.max(...xs):null});
const activationCells=[];
for(const [cell,rs]of group(decisions,r=>r.cell)){
  const id=identity(cell);if(rs.some(r=>r.label!==id.label))throw Error('Decision label mismatch');
  const physical=rs.filter(r=>['verify','generate'].includes(r.operation));
  const waits=rs.filter(r=>r.operation===null);
  if(waits.length+physical.length!==rs.length)throw Error('Unknown operation');
  activationCells.push({cell,...id,decisions:rs.length,physical_selection_decisions:physical.length,wait_decisions:waits.length,
    successor_active_decisions:physical.filter(r=>r.successor_reward_used&&r.released_successor_observations>0).length,
    inherited_deadline_decisions:physical.filter(r=>r.inherited_deadline_targets>0).length,
    selected_inherited_deadline_decisions:physical.filter(r=>r.selected_targets_with_inherited_deadline>0).length,
    selected_inherited_target_observations:sum(physical,'selected_targets_with_inherited_deadline'),
    released_successor_observations:sum(physical,'released_successor_observations'),
    positive_successor_forecast_decisions:physical.filter(r=>r.positive_successor_credit_forecast).length,
    positive_successor_reward_used_decisions:physical.filter(r=>r.successor_reward_used&&r.positive_successor_credit_forecast).length,
    positive_private_forecast_decisions:physical.filter(r=>r.positive_private_additional_credit_forecast).length,
    service_guard_active_decisions:physical.filter(r=>r.service_guard_active).length,
    forced_target_observations:sum(physical,'forced_targets'),
    forced_not_selected:sum(physical,'forced_not_selected'),
    planner_wall_s:sum(rs,'authority_planner_wall_s'),feature_wall_s:sum(rs,'base_feature_wall_s'),
    snapshot_to_enqueue_s:sum(physical,'actual_snapshot_to_first_enqueue_s'),
    residual_snapshot_to_enqueue_s:sum(physical,'snapshot_to_first_enqueue_minus_feature_and_planner_s'),
    physical_planner_wall_distribution_s:stats(physical.map(r=>r.authority_planner_wall_s)),
    plans_evaluated_distribution:stats(physical.map(r=>r.plans_evaluated).filter(Number.isFinite))});
}
const activationGroups=[];
const countKeys=['decisions','physical_selection_decisions','wait_decisions','successor_active_decisions','inherited_deadline_decisions','selected_inherited_deadline_decisions','selected_inherited_target_observations','released_successor_observations','positive_successor_forecast_decisions','positive_successor_reward_used_decisions','positive_private_forecast_decisions','service_guard_active_decisions','forced_target_observations','forced_not_selected'];
for(const [key,rs]of group(activationCells,r=>r.arrival+'/'+r.label)){
  if(rs.length!==3)throw Error('Missing activation repetition');
  const [arrival,label]=key.split('/');
  const d=diag.find(r=>r.arrival===arrival&&r.label===label);if(!d)throw Error('Missing DIAG group');
  activationGroups.push({arrival,label,runs:3,sums:Object.fromEntries(countKeys.map(k=>[k,sum(rs,k)])),run_medians:Object.fromEntries([...countKeys,'planner_wall_s','feature_wall_s','snapshot_to_enqueue_s','residual_snapshot_to_enqueue_s'].map(k=>[k,median(rs.map(r=>r[k]))])),diagnostic_summary:d,per_repeat:rs.toSorted((a,b)=>a.repeat-b.repeat)});
}
const promiseGroups=[];
for(const [key,rs]of group(promises,r=>{const i=identity(r.cell);if(i.label!==r.label)throw Error('Promise label mismatch');return i.arrival+'/'+i.label;})){
  const [arrival,label]=key.split('/');const named=rs.filter(r=>r.promised_finish!==null);const late=named.filter(r=>r.actual_promise_late);
  promiseGroups.push({arrival,label,identity_retirements:rs.length,with_frozen_promise:named.length,actual_late:late.length,
    late_fraction_of_promised:named.length?late.length/named.length:null,positive_lateness_s:stats(late.map(r=>r.promise_lateness_s)),
    recorded_breach_events:sum(rs,'recorded_promise_breach_events'),retirement_deferral_values:[...new Set(rs.map(r=>r.deferrals_at_retirement))],
    per_repeat:[0,1,2].map(repeat=>{const a=rs.filter(r=>identity(r.cell).repeat===repeat),b=a.filter(r=>r.promised_finish!==null);return {repeat,identities:a.length,promised:b.length,late:b.filter(r=>r.actual_promise_late).length};})});
}
const calibrationGroups=[];
for(const [key,rs]of group(calibration,r=>r.arrival+'/'+r.label+'/'+r.operation)){
  const [arrival,label,operation]=key.split('/'),n=sum(rs,'actual_selected_batches');
  const weighted=k=>sum(rs.map(r=>r[k]*r.actual_selected_batches))/n;
  calibrationGroups.push({arrival,label,operation,runs:rs.length,batches:n,predicted_mean_lease_s:weighted('predicted_first_lease_mean_s'),
    actual_mean_lease_s:weighted('actual_full_lease_mean_s'),actual_minus_predicted_mean_s:weighted('actual_minus_predicted_mean_s'),
    actual_over_predicted_ratio:weighted('actual_full_lease_mean_s')/weighted('predicted_first_lease_mean_s'),P90_coverage:weighted('observed_lease_P90_coverage'),
    actual_fallback_rows:sum(rs,'actual_fallback_rows'),predicted_fallback_rows:sum(rs,'predicted_fallback_rows'),
    scope:'Selected physical batches only, weighted by batch count; not same-batch Verify/Generate counterfactual'});
}
const tailGroups=[];let runtimeLabelDifferences=0;
for(const r of tails){Object.assign(r,identity(r.cell));if(r.method!==r.label)runtimeLabelDifferences++;}
for(const [key,rs]of group(tails,r=>r.arrival+'/'+r.label)){
  const [arrival,label]=key.split('/');const total=sum(rs,'total_lease_s'),associated=sum(rs,'cap_associated_batch_lease_s');
  tailGroups.push({arrival,label,runs:rs.length,proposal_rows:sum(rs,'proposal_rows'),capped_rows:sum(rs,'proposal_caps'),
    proposal_batches:sum(rs,'proposal_batches'),total_paid_lease_s:total,cap_associated_batches:sum(rs,'cap_associated_batch_count'),cap_associated_paid_lease_s:associated,
    associated_fraction_of_paid_lease:total?associated/total:0,median_total_paid_lease_s:median(rs.map(r=>r.total_lease_s)),
    median_batches:median(rs.map(r=>r.proposal_batches)),max_batch_lease_s:Math.max(...rs.map(r=>r.max_batch_lease_s)),
    runtime_method_values:[...new Set(rs.map(r=>r.method))],scope:'Entire batch with at least one capped row; association is not exclusive causal cap overhead',per_repeat:rs.toSorted((a,b)=>a.repeat-b.repeat)});
}
if(sum(tails,'proposal_rows')!==8892||sum(tails,'proposal_caps')!==22||sum(tails,'proposal_batches')!==1146||tailSummary.cells!==72)throw Error('Proposer accounting mismatch');
const snapshotGroups=[];
for(const [mode,rs]of group(snapshots,r=>r.mode))snapshotGroups.push({mode,n:rs.length,all_fields_exact:rs.every(r=>r.exact_all_planner_fields===true),context_build_excluded:rs.every(r=>r.original_owner_context_build_not_in_replay===true),
  recorded_owner_wall_s:stats(rs.map(r=>r.recorded_owner_planner_wall_s)),ordinary_exact_choose_wall_s:stats(rs.map(r=>r.ordinary_exact_choose_wall_s)),
  instrumented_choose_wall_s:stats(rs.map(r=>r.instrumented_choose_wall_s)),plans_evaluated:stats(rs.map(r=>r.plans_evaluated))});
const hotspotGroups=[];
for(const [fn,rs]of group(hotspots,r=>r.function))hotspotGroups.push({function:fn,exclusive_cpu_profile_s:sum(rs,'exclusive_cpu_profile_s'),primitive_calls:sum(rs,'primitive_calls'),total_calls:sum(rs,'total_calls'),sampled_rows:rs.length,
  scope:'Exclusive CPU seconds in 20 instrumented replays; top-truncated profile, not measured live Owner or GPU time'});
hotspotGroups.sort((a,b)=>b.exclusive_cpu_profile_s-a.exclusive_cpu_profile_s);
const report={status:'COMPLETE_INDEPENDENT_RAW_EXTRACT_DIAGNOSIS_REVIEW',experiment_id:'REVTRACE-CES-V5-CLOSED-LOOP-20261025',
  evidence_tier:'Independent read-only arithmetic of extracts made from the same 72 formal raw GPU traces, plus twenty same-snapshot CPU exact replays. No new GPU or unchosen-action counterfactual.',
  sources,review_script_sha256:hash(fileURLToPath(import.meta.url)),formal_cells:72,formal_actual_model_calls:2672,decisions:decisions.length,promise_retirements:promises.length,
  activation_groups:activationGroups,promise_groups:promiseGroups,operation_calibration_groups:calibrationGroups,
  proposer_tail_totals:{rows:sum(tails,'proposal_rows'),capped_rows:sum(tails,'proposal_caps'),physical_batches:sum(tails,'proposal_batches'),paid_lease_s:sum(tails,'total_lease_s'),
    cap_associated_batches:sum(tails,'cap_associated_batch_count'),cap_associated_paid_lease_s:sum(tails,'cap_associated_batch_lease_s'),
    metadata_runtime_method_differs_from_experimental_label_cells:runtimeLabelDifferences,observed_cap_discordant_declared_logical_input_classes:tailSummary.cap_discordant_logical_input_classes},
  proposer_tail_groups:tailGroups,snapshot_groups:snapshotGroups,top_replay_cpu_hotspots:hotspotGroups.slice(0,20),
  scope_limits:[
    'Activation establishes execution of a feature, not its causal benefit; repeated feature observations are not unique successors or IID samples.',
    'maximum_observed_target_deferrals in DIAG_GROUPS counts non-selected ces-decision observations and can include operation=None candidate-wait polling in Cost; not a physical-batch deferral count for cross-mode comparisons.',
    'deferrals_at_retirement resets after dispatch; zero at retirement is not evidence of no prior waiting.',
    'Marginal P99 release-to-Parent, queue and service clocks cannot be summed into a critical-path decomposition.',
    'Paid Proposer lease uses batch_drained-worker_started; prior PHYSICAL_COSTS worker_service_s uses batch_result_complete-worker_started.',
    'Cap-associated batch lease is not cap-exclusive cost and no matched un-capped GPU alternative is executed.',
    'Declared logical input equality does not fix complete realized physical batch padding/layout or provide an unobserved counterfactual.',
    'Twenty CPU snapshot exact replays confirm planner-field reproducibility, not GPU output equality, a faster deployed policy, or re-executed Owner context build.'
  ],decision:{broad_C2_upgrade:'NO_GO_ON_THIS_DIAGNOSTIC',original_C1_C2_C3_rejected:false,
    measured_main_bottlenecks:['Charged online Owner planning and snapshot-to-enqueue cost','Authority release-to-Parent and eligible-queue delay under staggered load','Real paid Proposer long-tail batches, concentrated in conditional cap cases'],
    unproven_hypothesis:'Authority scheduling changes when later Private work starts and its actual generation/lease distribution; the frozen forecast prices GPU1 current/released-successor work and already-pending GPU0 CDF, not future not-yet-dispatched GPU0 work. This is a model mismatch hypothesis, not a measured counterfactual cause.'}};
for(const [name,s]of Object.entries(sources))if(hash(s.path)!==s.sha256)throw Error('Input mutated '+name);
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,activation:activationGroups.map(g=>({arrival:g.arrival,label:g.label,...g.sums,planner_median:g.run_medians.planner_wall_s})),promises:promiseGroups,calibration:calibrationGroups,tails:tailGroups.map(({per_repeat,...r})=>r),totals:report.proposer_tail_totals,snapshots:snapshotGroups,hotspots:hotspotGroups.slice(0,10)},null,2));
