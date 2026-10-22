"""Actual-payload Linux IPC/receipt cost; fixture, not production throughput."""
from pathlib import Path
import copy,json,multiprocessing as mp,pickle,statistics,sys,time
from adoption_core import digest
def relay(c,receipt):
 c.send('ready')
 while True:
  r=c.recv()
  if r is None:break
  if receipt:
   j,z=copy.deepcopy(r['job']),copy.deepcopy(r['result']);a,b=digest(j),digest(z)
  else:a,b=None,None
  c.send((a,b))
def q(xs,p):
 xs=sorted(xs);i=(len(xs)-1)*p;a=int(i);return xs[a]+(xs[min(a+1,len(xs)-1)]-xs[a])*(i-a)
def main():
 B=Path(sys.argv[1]);O=B/'results/revtrace/opportunity_20261022';p=O/'B_gpu_v2/completed-adopt-r0/SUPERVISOR_RECORDS.json';raw=json.loads(p.read_text());r=next(iter(raw['records'].values()));payload={'job':r['job'],'result':r['result']};rows=[]
 for repeat in range(3):
  for receipt in ([False,True] if repeat%2==0 else [True,False]):
   a,b=mp.get_context('spawn').Pipe();proc=mp.get_context('spawn').Process(target=relay,args=(b,receipt));proc.start();b.close();assert a.recv()=='ready'
   times=[]
   for i in range(1000):
    t=time.perf_counter();a.send(payload);a.recv();times.append(time.perf_counter()-t)
   a.send(None);proc.join(timeout=5);assert proc.exitcode==0;a.close();rows.append({'repeat':repeat,'receipt':receipt,'iterations':1000,'median_seconds':statistics.median(times),'p99_seconds':q(times,.99),'mean_seconds':statistics.mean(times)})
 out={'status':'COMPLETE_CPU_IPC_COST_FIXTURE','rows':rows,'actual_payload_pickle_bytes':len(pickle.dumps(payload)),'actual_payload_JSON_bytes':len(json.dumps(payload).encode()),'one_pending_record_JSON_bytes':len(json.dumps(r).encode()),'source_actual_GPU_record':str(p),'extra_full_receipt_median_seconds':statistics.median(next(x['median_seconds'] for x in rows if x['repeat']==i and x['receipt'])-next(x['median_seconds'] for x in rows if x['repeat']==i and not x['receipt']) for i in range(3)),'scope':'Linux host CPU loopback Pipe RTT with actual job/result metadata; not production GPU/streaming p99, not host energy, not full scheduler overhead','retention_warning':'records kept until durable decision; full-system ACK/GC and bounded memory not implemented'}
 (O/'NORMAL_COST_CPU.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
