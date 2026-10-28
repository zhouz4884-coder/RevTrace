"""Complete terminal rows only; never marks a physical executor reusable."""
import time

class CompleteRowStream:
    def __init__(self,indices,*,eos,budget,on_complete):
        self.indices=list(indices);self.eos=set(eos);self.budget=budget
        if len(set(self.indices))!=len(self.indices) or not self.indices:raise ValueError('unique physical row indices required')
        if type(budget) is not int or budget<=0:raise ValueError('positive token budget required')
        self.on_complete=on_complete;self.started=False
        self.rows=[[] for _ in self.indices];self.done=[False]*len(self.indices)
        self.cancelled=[False]*len(self.indices)
    @property
    def all_terminal(self):return all(a or b for a,b in zip(self.done,self.cancelled))
    def cancel(self,indices):
        """Called at a decode safe point. Count discarded tokens, never emit them."""
        indices=list(indices)
        if len(set(indices))!=len(indices) or not set(indices)<=set(self.indices):
            raise ValueError('unknown or repeated cancellation row index')
        counts={}
        for i in indices:
            pos=self.indices.index(i)
            if self.done[pos] or self.cancelled[pos]:continue
            self.cancelled[pos]=True;counts[i]=len(self.rows[pos])
        return counts
    def put(self,value):
        rows=value.tolist()
        if not self.started:
            if len(rows)!=len(self.indices) or not all(isinstance(r,list) for r in rows):raise ValueError('wrong initial physical layout')
            self.started=True;return
        if len(rows)!=len(self.indices) or any(isinstance(x,list) for x in rows):raise ValueError('wrong token row layout')
        for pos,t in enumerate(rows):
            if self.done[pos] or self.cancelled[pos]:continue
            self.rows[pos].append(int(t))
            if t in self.eos or len(self.rows[pos])==self.budget:
                self.done[pos]=True
                self.on_complete(self.indices[pos],tuple(self.rows[pos]),time.perf_counter())
    def end(self):
        if not self.started or not self.all_terminal:raise ValueError('undeclared incomplete row terminal')
