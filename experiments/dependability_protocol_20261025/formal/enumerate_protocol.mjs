// Independently implemented DFS checker of the declared finite transition cut.
// Same state encoding/spec; no imports from the Python transition generator.
import fs from 'node:fs';
import crypto from 'node:crypto';
const prop=['authorized_ancestry','gap_free_commit','fresh_provisional_publication','exact_chain_private_continuity','durable_certified_view'];
const B=Array.from({length:19},(_,i)=>2**i);
const [r1,r2,pIssue,pReady,pDrain,pReceive,aIssue,aReady,aDrain,aReceive,append,sync,install,publish,crash,replay,retry,retire,ack]=B;
const initial=()=>[0,0,0,0,0,0,false,false,false,-1,-1,[],0,0,false,0];
const stateKey=x=>JSON.stringify(x);
function next(state,config){
  const [bits,frontier,version,projection,epoch,generation,accepted,complete,durable,pEpoch,aEpoch,queue,consumerF,consumerP,provisional,monitor]=state;
  const scenario=config.case, missing=config.omit;
  const pEnd=scenario==='covered'?1:2;
  const pBoundary=scenario==='covered'?0:scenario==='ahead_equal'?1:3;
  const parent=scenario==='stale_parent'?1:0;
  const input=scenario==='stale_parent'?9:0;
  const start=scenario==='gap'?1:0,end=scenario==='gap'?2:1;
  const wrongSource=scenario==='wrong_receipt',wrongText=scenario==='bad_render';
  const has=flag=>(bits&flag)!==0;
  const freshEpoch=missing==='epoch'||aEpoch===epoch;
  const legal=(missing==='parent'||(parent===version&&input===projection))&&
              (missing==='frontier'||(start===frontier&&end>frontier))&&freshEpoch;
  const out=[];
  const make=(label,flag,changes={})=>{
    const s=state.slice(); s[0]=bits|flag;
    for(const [k,v] of Object.entries(changes))s[Number(k)]=v;
    out.push([label,s]);
  };
  if(!has(r1))make('release-1',r1);
  if(has(r1)&&!has(r2))make('release-2',r2);
  if(epoch===0&&has(pEnd===1?r1:r2)&&!has(pIssue))make('dispatch-private-frozen',pIssue,{9:epoch});
  if(has(pIssue)&&!has(pReady))make('row-complete-private',pReady);
  if(has(pReady)&&!has(pDrain))make('batch-drained-private',pDrain);
  if(has(pReady)&&!has(pReceive)){
    const stale=pEnd<=frontier||generation!==0||pEpoch!==epoch;
    const pass=missing==='freshness'||!stale;
    make(pass?'receive-private-and-publish':'retire-private',pReceive,
      {11:pass?queue.concat([['P',epoch,version,pEnd,pBoundary,false]]):queue,15:monitor|(pass&&stale?4:0)});
  }
  if(epoch===0&&has(end===2?r2:r1)&&!has(aIssue))make('dispatch-authority-frozen',aIssue,{10:epoch});
  if(has(aIssue)&&!has(aReady))make('row-complete-authority',aReady);
  if(has(aReady)&&!has(aDrain))make('batch-drained-authority',aDrain);
  if(has(aReady)&&!has(aReceive)){
    const pass=(!wrongSource||missing==='row_identity')&&(!wrongText||missing==='render')&&freshEpoch;
    make(pass?'receive-authority':'reject-authority',aReceive,{6:pass});
  }
  if(accepted&&!has(append)&&legal)make('append-WAL-incomplete',append,{7:false});
  if(has(append)&&!has(sync)&&accepted&&legal)make('complete-frame-and-fsync',sync,{7:true,8:true});
  if(accepted&&!has(install)&&legal&&(durable||missing==='persist')){
    const bad=monitor|((parent!==version||input!==projection||wrongSource||aEpoch!==epoch)?1:0)|((start!==frontier||end<=frontier)?2:0);
    make('install-canonical',install,{1:end,2:version+1,3:1,15:bad});
  }
  if(has(install)&&!has(publish)&&frontier)make('publish-certified',publish,{11:queue.concat([['A',epoch,version,frontier,projection,wrongText]])});
  if(has(install)&&!has(ack)&&frontier)make('return-install-receipt',ack,{15:monitor|(!durable?16:0)});
  if(has(pIssue)&&!has(pReceive)&&!has(retire)&&has(install))make('retire-private-generation',retire,{5:1});
  if(queue.length){
    const [type,e,v,to,p,badText]=queue[0];
    let cf=consumerF,cp=consumerP,vis=provisional,bad=monitor;
    if(e===epoch){
      if(type==='A'){
        cf=to;cp=p;
        if(!durable||badText)bad|=16;
        if(vis)vis=pEnd>cf&&(missing==='chain'||pBoundary===cp);
        if(vis&&pBoundary!==cp)bad|=8;
      }else if(to>cf){
        const match=cf===0||(cf===1&&pBoundary===cp);
        vis=match||missing==='chain';
        if(vis&&!match)bad|=8;
      }
    }
    make('consume-FIFO',0,{11:queue.slice(1),12:cf,13:cp,14:vis,15:bad});
  }
  if(!has(crash))make('crash-restart-new-stream',crash,{4:1,1:durable?end:0,2:durable?1:0,3:durable?1:0,
    6:false,7:durable,11:[],12:0,13:0,14:false,5:1});
  if(has(crash)&&durable&&!has(replay))make('replay-render-and-republish',replay,{11:queue.concat([['A',epoch,1,end,1,wrongText]])});
  if(durable&&!has(retry))make('retry-returns-prior-receipt',retry);
  return out;
}
function run(config){
  const root=initial(),seen=new Map([[stateKey(root),root]]),stack=[root];
  let transitions=0,violationMask=0;
  while(stack.length){
    const state=stack.pop();
    for(const [label,s] of next(state,config)){
      transitions++; const key=stateKey(s);
      if(seen.has(key))continue;
      seen.set(key,s);stack.push(s);violationMask|=s[15];
      if(seen.size>800000)throw new Error('state bound cutoff; not complete');
    }
  }
  const h=crypto.createHash('sha256');
  for(const key of [...seen.keys()].sort())h.update(key+'\n');
  return {config,complete:true,states:seen.size,transitions,reachable_state_sha256:h.digest('hex'),violations:prop.filter((_,i)=>(violationMask&(1<<i))!==0)};
}
const args=process.argv.slice(2);const output=args[args.indexOf('--output')+1];
if(!output||fs.existsSync(output))throw new Error('unique output required');
const results=[];
for(const c of ['covered','ahead_equal','ahead_diff','bad_render','wrong_receipt','stale_parent','gap']){
  for(const omit of ['none','freshness','chain','render','persist','epoch','row_identity','parent','frontier']){
    const r=run({case:c,omit});results.push(r);
    process.stdout.write(JSON.stringify({config:r.config,states:r.states,violations:r.violations})+'\n');
  }
}
if(results.some(r=>r.config.omit==='none'&&r.violations.length))throw new Error('full guard invariant violated');
fs.writeFileSync(output,JSON.stringify({status:'JS_COMPLETE_PENDING_PYTHON_COMPARISON',results},null,2)+'\n');
