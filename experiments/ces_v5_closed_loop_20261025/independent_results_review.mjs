// Independent read-only CSV arithmetic. No original result is edited.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const root=path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/,'$1'));
const input=path.join(root,'precollection');
const output=path.join(root,'INDEPENDENT_RESULTS_REVIEW.json');
if(fs.existsSync(output))throw new Error('Independent report exists; choose a separately versioned review');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const sources=Object.fromEntries(['SERVICE_CELLS.csv','PHYSICAL_COSTS.csv','SUMMARY.json'].map(n=>[n,{path:path.join(input,n),sha256:hash(path.join(input,n))}]));

function parseCSV(text){
  const records=[];let row=[],field='',quoted=false;
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){
      if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;
    }else if(c===','&&!quoted){row.push(field);field='';}
    else if(c==='\n'&&!quoted){row.push(field.replace(/\r$/,''));if(row.some(v=>v!==''))records.push(row);row=[];field='';}
    else field+=c;
  }
  if(quoted)throw new Error('Unclosed quoted CSV field');
  if(field||row.length){row.push(field.replace(/\r$/,''));records.push(row);}
  const headers=records.shift();
  if(new Set(headers).size!==headers.length)throw new Error('Duplicate CSV columns');
  return records.map(r=>{if(r.length!==headers.length)throw new Error('CSV row width mismatch');return Object.fromEntries(headers.map((k,i)=>[k,r[i]===''?null:r[i]==='True'?true:r[i]==='False'?false:/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(r[i])?Number(r[i]):r[i]]));});
}
const cells=parseCSV(fs.readFileSync(sources['SERVICE_CELLS.csv'].path,'utf8'));
const costs=parseCSV(fs.readFileSync(sources['PHYSICAL_COSTS.csv'].path,'utf8'));
const audit=JSON.parse(fs.readFileSync(sources['SUMMARY.json'].path,'utf8'));
if(cells.length!==72||audit.cells!==72||audit.expected_cells!==72||audit.failures.length||audit.status!=='PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT')throw new Error('Incomplete formal evidence');
if(new Set(cells.map(r=>r.cell)).size!==72)throw new Error('Duplicate service cell');
const allCalls=costs.reduce((s,r)=>s+r.physical_model_calls,0);
if(costs.length!==144||allCalls!==audit.actual_model_calls||allCalls!==2672)throw new Error('Physical-call denominator mismatch');
const groupMap=new Map();
for(const r of cells){
  const match=r.cell.match(/^validation-(sync|staggered)-mixed-(.+)-r([012])$/);
  if(!match||r.method!==match[2])throw new Error('Cell/label mismatch');
  r.arrival=match[1];r.repeat=Number(match[3]);
  if(r.audio_seconds!==250.18||r.commits!==135||r.delivery!=='row'||r.traffic!=='mixed')throw new Error('Changed input or evidence contract');
  const rs=costs.filter(c=>c.cell===r.cell);
  if(rs.length!==2||new Set(rs.map(x=>x.role)).size!==2)throw new Error('Missing physical role');
  r.actual_model_calls=rs.reduce((s,c)=>s+c.physical_model_calls,0);
  r.authority_model_calls=rs.find(c=>c.role==='authority').physical_model_calls;
  r.proposal_model_calls=rs.find(c=>c.role==='proposal').physical_model_calls;
  r.physical_batches=rs.reduce((s,c)=>s+c.physical_batches,0);
  r.authority_worker_service_s=rs.find(c=>c.role==='authority').worker_service_s;
  r.proposal_worker_service_s=rs.find(c=>c.role==='proposal').worker_service_s;
  const k=r.arrival+'/'+r.method;
  if(!groupMap.has(k))groupMap.set(k,[]);groupMap.get(k).push(r);
}
if(groupMap.size!==24)throw new Error('Expected twelve methods × two arrivals');
const quantile=(xs,q)=>{const x=xs.toSorted((a,b)=>a-b);const at=(x.length-1)*q,l=Math.floor(at),f=at-l;return x[l]+f*((x[l+1]??x[l])-x[l]);};
const median=x=>quantile(x,.5);
const metricNames=['Audio_Goodput_2_8','Audio_Goodput_certified_consumer_2_8','Audio_Goodput_stable_2_8',
 'display_P50','display_P95','display_P99','commit_P50','commit_P95','commit_P99','GPU_J_audio_s','WER','CER',
 'wall_seconds','verified_rows','accepted_rows','rejected_rows','fallback_rows','fallback_physical_calls',
 'planner_wall_s','feature_wall_s','decision_count','physical_fsyncs','obsolete_private_jobs',
 'withdrawn_before_certified_frontiers','visible_audio_rollback_samples','erased_characters','actual_model_calls',
 'authority_model_calls','proposal_model_calls','physical_batches','authority_worker_service_s','proposal_worker_service_s',
 'direct_consumed_F2_jobs','candidate_wait_before_eligibility_seconds'];
const groups=[];
for(const [key,rows]of groupMap){
  rows.sort((a,b)=>a.repeat-b.repeat);
  if(rows.map(r=>r.repeat).join(',')!=='0,1,2')throw new Error('Incomplete paired repeats');
  const [arrival,method]=key.split('/');
  const medians=Object.fromEntries(metricNames.map(k=>[k,median(rows.map(r=>{if(typeof r[k]!=='number'||!Number.isFinite(r[k]))throw new Error('Missing/nonfinite metric '+k);return r[k];}))]));
  groups.push({arrival,method,runs:3,repeat_ids:[0,1,2],medians,
    whole_run_dual_P99_passes:rows.filter(r=>r.dual_P99_2_8_pass).length,
    capped_authority_admissions:rows.reduce((s,r)=>s+r.capped_authority_admissions,0),
    unfinished_sources:rows.reduce((s,r)=>s+r.unfinished_sources,0),
    per_repeat:rows});
}
groups.sort((a,b)=>a.arrival.localeCompare(b.arrival)||a.method.localeCompare(b.method));
const byGroup=Object.fromEntries(groups.map(g=>[g.arrival+'/'+g.method,g]));
function paired(baseName,newName,arrival){
  const a=byGroup[arrival+'/'+baseName],b=byGroup[arrival+'/'+newName];
  const metrics={};
  for(const key of metricNames){
    const quality=['WER','CER'].includes(key);
    const values=a.per_repeat.map((r,i)=>quality?(b.per_repeat[i][key]-r[key])*100:r[key]===0?(b.per_repeat[i][key]===0?0:null):(b.per_repeat[i][key]/r[key]-1)*100);
    if(values.some(v=>v===null)){metrics[key]={status:'ZERO_BASELINE_RATIO_UNAVAILABLE',paired_values:values};continue;}
    const bootstrap=[];
    for(let i=0;i<3;i++)for(let j=0;j<3;j++)for(let k=0;k<3;k++)bootstrap.push(median([values[i],values[j],values[k]]));
    metrics[key]={units:quality?'percentage_point_difference':'percent_relative_change',paired_values:values,
      median_paired_change:median(values),exact_27_resample_descriptive_95_interval:[quantile(bootstrap,.025),quantile(bootstrap,.975)],
      ratio_of_group_medians_change:quality?(b.medians[key]-a.medians[key])*100:a.medians[key]===0?null:(b.medians[key]/a.medians[key]-1)*100,
      positive_repeats:values.filter(x=>x>0).length,negative_repeats:values.filter(x=>x<0).length,
      note:'Three paired runs only. Exhaustive resampling of three observed effects is descriptive, not independent-source confirmation or multiplicity-corrected significance.'};
  }
  return {arrival,baseline:baseName,treatment:newName,metrics,
    baseline_dual_P99_passes:a.whole_run_dual_P99_passes,treatment_dual_P99_passes:b.whole_run_dual_P99_passes};
}
const pairs=[];
for(const arrival of ['sync','staggered']){
 for(const treatment of ['causal','causal_joint'])for(const baseline of ['fine','standard','cost','cost_joint','service_cost','reserved_progress','inherit'])pairs.push(paired(baseline,treatment,arrival));
 for(const [a,b]of [['fine','fine_shared_progress'],['standard','standard_shared_progress'],['cost','cost_joint'],['causal','causal_joint'],['service_cost','reserved_progress'],['reserved_progress','inherit']])pairs.push(paired(a,b,arrival));
}
const report={status:'COMPLETE_INDEPENDENT_READ_ONLY_CSV_ARITHMETIC_REVIEW',experiment_id:'REVTRACE-CES-V5-CLOSED-LOOP-20261025',
 evidence_tier:'Independent arithmetic on supplied audited CSV summaries only; not raw event/model re-execution',
 sources,review_script_sha256:hash(new URL(import.meta.url)),cells:72,groups:24,actual_model_calls:allCalls,
 requested_audio_per_run:250.18,commits_per_run:135,frontier_observations:cells.reduce((s,r)=>s+r.commits,0),
 whole_run_dual_P99_passes:cells.filter(r=>r.dual_P99_2_8_pass).length,
 unfinished_sources:cells.reduce((s,r)=>s+r.unfinished_sources,0),capped_authority_admissions:cells.reduce((s,r)=>s+r.capped_authority_admissions,0),
 WER_values:[...new Set(cells.map(r=>r.WER))],CER_values:[...new Set(cells.map(r=>r.CER))],
 independent_confirmation:false,pure_no_service_guard_GPU_ablation:false,group_results:groups,paired_comparisons:pairs,
 decisions:{overall_algorithm_upgrade:'NO-GO_AS_BROAD_C2_PERFORMANCE_UPGRADE_ON_THIS_DIAGNOSTIC',
   contribution_scope:'Final judgement must inspect strong references, both arrivals, actual quality and full physical costs; causal mechanism attribution additionally needs the separately collected event diagnosis.',
   not_a_rejection_of_original_C1_C2_C3:true}};
for(const [name,info]of Object.entries(sources))if(hash(info.path)!==info.sha256)throw new Error('Input changed during review: '+name);
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,groups:groups.map(g=>({arrival:g.arrival,method:g.method,g:g.medians.Audio_Goodput_2_8,D:g.medians.display_P99,C:g.medians.commit_P99,E:g.medians.GPU_J_audio_s,SLO:g.whole_run_dual_P99_passes})),WER:report.WER_values,CER:report.CER_values,caps:report.capped_authority_admissions,SLO:report.whole_run_dual_P99_passes},null,2));
