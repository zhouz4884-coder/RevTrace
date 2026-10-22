"""Read-only complete-row observer; not a scheduler or admission authority."""
import hashlib,json,time

class RowFinalStream:
    def __init__(self,job_ids,*,eos,budget,events,render,phase,clock=time.perf_counter):
        if not job_ids or len(set(job_ids))!=len(job_ids):raise ValueError('unique physical row identities required')
        self.ids=list(job_ids);self.eos=set(eos);self.budget=budget;self.events=events
        self.render=render;self.phase=phase;self.clock=clock
        self.rows=[[] for _ in self.ids];self.done=[False]*len(self.ids);self.started=False
    def put(self,value):
        v=value.tolist()
        if not self.started:
            if not isinstance(v,list) or len(v)!=len(self.ids) or not all(isinstance(r,list) for r in v):raise ValueError('wrong initial physical input layout')
            self.started=True;return
        if not isinstance(v,list) or len(v)!=len(self.ids) or any(isinstance(x,list) for x in v):raise ValueError('wrong decode row layout')
        for i,t in enumerate(v):
            if self.done[i]:continue
            self.rows[i].append(int(t));stop=t in self.eos
            if stop or len(self.rows[i])==self.budget:
                ready=self.clock();Z=tuple(self.rows[i]);P,text=self.render(self.ids[i],Z)
                final=self.clock();self.done[i]=True
                self.events.append({'kind':'probe-row-final','job_id':self.ids[i],'phase':self.phase,
                    'row_index':i,'stop_kind':'EOS' if stop else 'budget',
                    'terminal_observed_perf':ready,'complete_render_perf':final,
                    'observer_render_s':final-ready,'Z':list(Z),'P':list(P),'text':text,
                    'worker_reusable':False,'diagnostic_not_online_installation':True})
    def end(self):
        if not self.started or not all(self.done):raise ValueError('generation stopped without a declared complete row')

def result_equal(a,b):
    return all(a.get(k)==b.get(k) for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit'])

def observer_lead(event,batch_end):
    return batch_end-event['complete_render_perf']
