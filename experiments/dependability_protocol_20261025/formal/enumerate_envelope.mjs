// Separate DFS implementation of the finite obligation specification.
// No imports from Python or live policy/Consumer code.
import fs from 'node:fs';import crypto from 'node:crypto';
const [O,A,C,R,J,DA,DR,DJ,ACK,E,M,U,V,Q,READY,BAD]=Array.from({length:16},(_,i)=>i);
const props=['accepted_input_lost','reservation_recovery_unavailable','certified_only_false_view',
 'old_observation_relabelled_fresh','untrusted_canonical_admission','credit_bound_exceeded','terminal_rejection_forgotten'];
const serialize=s=>JSON.stringify(s);
const replace=(a,i,value)=>a.map((x,k)=>k===i?value:x);
function init(n){const z=()=>Array(n).fill(0),b=()=>Array(n).fill(false);return [z(),z(),z(),z(),b(),z(),z(),b(),z(),0,0,z(),z(),null,true,0];}
function successors(state,c){
 if(state[BAD])return [];
 const out=[],n=c.sessions,max=c.frontiers,B=c.budget,q=2,missing=c.omit,mode=state[M];
 const add=(label,changes,durable=false)=>{
   const s=state.slice();for(const [k,x] of Object.entries(changes))s[Number(k)]=x;
   if(durable){s[DA]=s[A];s[DR]=s[R];s[DJ]=s[J];}
   if(s[R].reduce((v,r,i)=>v+r-s[C][i],0)>B)s[BAD]|=32;
   out.push([label,s]);
 };
 for(let i=0;i<n;i++){
   if(state[O][i]<max)add(`offer-${i}`,{[O]:replace(state[O],i,state[O][i]+1)});
   if(mode!==4&&!state[J][i]&&state[O][i]>state[R][i]){
     let to=state[R][i]+q;if(state[O][i]===max)to=Math.min(to,max);
     const cost=to-state[R][i],used=state[R].reduce((v,r,j)=>v+r-state[C][j],0);
     if(cost>0&&(used+cost<=B||missing==='credit_limit'))add(`reserve-complete-interval-${i}`,{[R]:replace(state[R],i,to)},true);
   }
   const to=Math.min(state[O][i],state[R][i]);
   if(!state[J][i]&&state[A][i]<to)add(`accept-sync-ack-${i}`,{[A]:replace(state[A],i,to),[ACK]:replace(state[ACK],i,to)},missing!=='input_sync');
   const target=Math.min(state[C][i]+q,max);
   if(mode!==4&&target>state[C][i]&&target<=state[A][i]&&!state[J][i]){
     add(`trusted-canonical-admission-${i}`,{[C]:replace(state[C],i,target)});
     if(missing==='admission_trust')add(`negative-deadline-bypass-${i}`,{[C]:replace(state[C],i,target),[BAD]:state[BAD]|16});
   }
   if(state[U][i]<state[C][i])add(`actual-certified-consume-${i}`,{[U]:replace(state[U],i,state[C][i]),[V]:replace(state[V],i,state[C][i])});
   if(![2,4].includes(mode)&&state[A][i]>state[V][i]&&!state[J][i])add(`actual-legal-private-consume-${i}`,{[V]:replace(state[V],i,state[A][i])});
   if(!state[J][i]&&state[A][i]===0&&state[O][i]>0)add(`explicit-reject-unaccepted-${i}`,{[J]:replace(state[J],i,true),[R]:replace(state[R],i,0)},true);
   if(state[Q]===null&&state[V][i]>0)add(`stage-actual-observation-${i}`,{[Q]:[i,state[V][i],state[E],state[C][i]]});
 }
 if(state[Q]!==null){
   const [i,F,e,context]=state[Q];let bad=state[BAD];
   if(e!==state[E]&&missing==='epoch_fence')bad|=8;
   add('deliver-or-fence-observation',{[Q]:null,[BAD]:bad});
 }
 if(state[READY]){
   for(let m=0;m<4;m++){
     if(m===mode)continue;
     let visible=state[V],bad=state[BAD];
     if(m===2&&missing!=='mode_purge')visible=state[U];
     if(m===2&&visible.some((x,i)=>x!==state[U][i]))bad|=4;
     add(`apply-view-mode-${m}`,{[M]:m,[V]:visible,[BAD]:bad});
   }
 }else add('actual-new-stream-application',{[READY]:true});
 if(state[E]===0){
   const accepted=state[DA];let reserved=state[DR],rejected=state[DJ],bad=state[BAD];
   if(missing==='zero_reservation_restore')reserved=state[C];
   if(missing==='derive_reservation_positive')reserved=accepted.map(a=>Math.min(max,Math.ceil(a/q)*q));
   if(missing==='forget_rejection')rejected=Array(n).fill(false);
   if(state[ACK].some((a,i)=>a>accepted[i])||state[C].some((cc,i)=>cc>accepted[i]))bad|=1;
   if(accepted.some((a,i)=>a>reserved[i]))bad|=2;
   if(state[J].some((old,i)=>old&&!rejected[i]))bad|=64;
   add('crash-restore-input-and-canonical-new-epoch',{[A]:accepted,[R]:reserved,[J]:rejected,[E]:1,[M]:4,
     [U]:Array(n).fill(0),[V]:Array(n).fill(0),[READY]:false,[BAD]:bad});
 }
 return out;
}
function explore(config){
 const root=init(config.sessions),seen=new Map([[serialize(root),root]]),work=[root];let edges=0,bad=0;
 while(work.length){
   const s=work.pop();for(const [label,t] of successors(s,config)){
     edges++;const k=serialize(t);if(seen.has(k))continue;
     seen.set(k,t);work.push(t);bad|=t[BAD];if(seen.size>600000)throw new Error('state cutoff, incomplete');
   }
 }
 const h=crypto.createHash('sha256');for(const k of [...seen.keys()].sort())h.update(k+'\n');
 return {config,complete:true,states:seen.size,transitions:edges,reachable_sha256:h.digest('hex'),violations:props.filter((_,i)=>(bad&(1<<i))!==0).sort()};
}
const args=process.argv.slice(2),file=args[args.indexOf('--output')+1];if(!file||fs.existsSync(file))throw new Error('unique output required');
const results=[];
for(const [sessions,frontiers,budget] of [[1,3,2],[2,2,2]]){
 for(const omit of ['none','input_sync','zero_reservation_restore','derive_reservation_positive','mode_purge','epoch_fence','admission_trust','credit_limit','forget_rejection']){
   const r=explore({sessions,frontiers,budget,omit});results.push(r);
   process.stdout.write(JSON.stringify({config:r.config,states:r.states,violations:r.violations})+'\n');
 }
}
if(results.some(r=>['none','derive_reservation_positive'].includes(r.config.omit)&&r.violations.length))throw new Error('protected obligation violation');
fs.writeFileSync(file,JSON.stringify({status:'JS_FINITE_CDE_SEARCH_PENDING_COMPARISON',results},null,2)+'\n');
