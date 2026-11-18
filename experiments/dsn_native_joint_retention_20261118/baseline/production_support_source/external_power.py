"""External NVML-backed nvidia-smi observer; no service instrumentation."""
from __future__ import annotations
import json, pathlib, subprocess, threading, time
from common import GateError, need, read, lines

def nvml_snapshot():
    begin=time.perf_counter()
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,power.draw,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=10)
    boards={}
    for line in raw.splitlines():
        index,uuid,power,memory,util=[v.strip() for v in line.split(',')]
        boards[int(index)]=dict(uuid=uuid,watts=float(power),memory_MiB=float(memory),utilization_percent=float(util))
    processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'],text=True,timeout=10)
    owners=[]
    for line in processes.splitlines():
        if not line.strip():continue
        pid,uuid=[v.strip() for v in line.split(',')];owners.append(dict(pid=int(pid),gpu_uuid=uuid))
    end=time.perf_counter();need({0,1}.issubset(boards),'both physical boards absent')
    return dict(time=(begin+end)/2,observation_begin_perf=begin,observation_end_perf=end,boards=boards,compute_processes=owners,backend='nvidia-smi via NVIDIA NVML; actual board samples')

def process_state(pid):
    path=pathlib.Path('/proc')/str(pid)/'stat'
    if not path.exists():return 'absent'
    try:return path.read_text().rsplit(')',1)[1].split()[0]
    except FileNotFoundError:return 'absent'

class ExternalObserver:
    def __init__(self,path,*,snapshot=nvml_snapshot,interval=.1):
        self.path=pathlib.Path(path);self.snapshot=snapshot;self.interval=interval;self.stop=threading.Event();self.started=threading.Event();self.error=None;self.first=None;self.last=None;self.worker_pids=set();self.drain=None;self.thread=None
    def start(self):
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
        need(self.started.wait(20),'external NVML observer first sample timeout');self.check()
    def _run(self):
        try:
            with self.path.open('x',encoding='utf8',newline='\n') as stream:
                while not self.stop.is_set():
                    pids=tuple(self.worker_pids);row=self.snapshot();row['worker_process_states']={str(pid):process_state(pid) for pid in pids}
                    if len(pids)>=2 and all(s in ('absent','Z','X') for s in row['worker_process_states'].values()) and not row['compute_processes'] and self.drain is None:
                        self.drain=dict(confirmed_perf=row['observation_end_perf'],observation_begin_perf=row['observation_begin_perf'],worker_pids=sorted(pids),definition='first external sample confirming all actual READY model-worker PIDs exited/zombie and zero CUDA compute owners on allocated boards; upper observation bound, not an instantaneous hardware timestamp')
                    stream.write(json.dumps(row,separators=(',',':'))+'\n');stream.flush();self.first=self.first or row;self.last=row;self.started.set();self.stop.wait(self.interval)
        except BaseException as exc:self.error=repr(exc);self.started.set()
    def check(self):need(self.error is None,'external observer failed: '+str(self.error))
    def discover_workers(self,out):
        out=pathlib.Path(out)
        path=out/'READY.json'
        if path.exists():
            try:self.worker_pids.update(r['pid'] for r in read(path).values())
            except (json.JSONDecodeError,KeyError):pass
        # READY events are the first bounded lines of each owner incarnation.
        for path in out.glob('owner_e*/worker_results.jsonl'):
            with path.open('r',encoding='utf8') as stream:
                for i,line in enumerate(stream):
                    if i>=8:break
                    try:
                        event=json.loads(line)['event']
                        if event.get('kind')=='ready':self.worker_pids.add(event['pid'])
                    except (json.JSONDecodeError,KeyError):pass
    def finish(self,*,not_before,timeout=30):
        deadline=time.perf_counter()+timeout
        while self.last is None or self.drain is None or self.last['time']<max(not_before,self.drain['confirmed_perf']):
            self.check();need(time.perf_counter()<deadline,'missing actual final boundary/drain observation');time.sleep(.05)
        self.stop.set();self.thread.join(20);self.check();need(not self.thread.is_alive(),'external observer did not stop')
    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(20)

def energy(path,start,end):
    need(end>=start,'negative observation interval');rows=lines(path);by={}
    for gpu in (0,1):
        points=sorted((r['time'],r['boards'][str(gpu)]['watts']) for r in rows)
        need(len(points)>=2 and points[0][0]<=start and points[-1][0]>=end,'external power lacks actual interval boundary samples')
        total=0.
        for (a,x),(b,y) in zip(points,points[1:]):
            left=max(a,start);right=min(b,end)
            if right<=left:continue
            low=x+(y-x)*(left-a)/(b-a);high=x+(y-x)*(right-a)/(b-a);total+=(low+high)*(right-left)/2
        by[str(gpu)]=total
    return dict(begin_perf=start,end_perf=end,seconds=end-start,board_joules=by,total_joules=sum(by.values()),method='linear interpolation/trapezoids on external NVML-backed both-board power; no CPU/PSU energy claim')
