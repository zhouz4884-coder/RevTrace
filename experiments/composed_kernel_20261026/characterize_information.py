"""Executable guard witnesses and insufficient-observation pairs. CPU only."""
from pathlib import Path
import json,sys,importlib.util
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
import revtrace.composed_kernel as m
spec=importlib.util.spec_from_file_location('fixture',W/'runtime/tests/test_composed_kernel.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
out=[]

def weakened(reason,k,kind,p):
    real=m.need
    def need(c,r):
        if r!=reason:real(c,r)
    m.need=need
    try:return m.step(k,kind,p)[0]
    finally:m.need=real

k=f.dispatched('proposal');k,_=m.step(k,'row-complete',dict(id='j',worker='a',identity='jobhash',P='P1',Z='Z',textsha='1'*64))
F=dict(v=1,F=1,P='P1',Z='Z',textsha='1'*64,txn='t')
k=weakened('private/unselected canonical write',k,'admission-request',dict(sid=0,job='j',operation='t',fact=F))
k,_=m.step(k,'canonical-synced',dict(operation='t'));k,_=m.step(k,'install',dict(sid=0,fact=F))
assert k.C[0]['v']==1 and k.J['j']['role']=='proposal'
out.append(dict(cut='trusted authority role at admission',result='UNAUTHORIZED_CANONICAL_WRITE',
    trace=['private dispatch','complete Render','weakened prepare','real abstract sync','install']))

k=f.seeded();k.I[0]['accepted']=1
j=dict(f.job(),end=2)
k=weakened('unaccepted audio dispatched',k,'dispatch',dict(worker='a',jobs=[j]))
assert k.J['j']['end']>k.I[0]['accepted']
out.append(dict(cut='accepted-input dispatch bound',result='EXECUTION_OUTSIDE_ACCEPTED_OBLIGATION',trace=['accepted 1','dispatch end 2']))

k=f.dispatched();j=dict(f.job(),id='j2')
k=weakened('physical worker still leased',k,'dispatch',dict(worker='a',jobs=[j]))
assert set(k.J)=={'j','j2'} and k.J['j']['result'] is None
out.append(dict(cut='physical lease exclusion',result='SECOND_SUBMIT_BEFORE_FIRST_DRAIN',trace=['submit j','submit j2 before row/drain']))

pairs=[
 dict(observation='self-described content/metadata/checksum only',same_observation={'Z':'Z','P':'P','text':'same'},
      hidden_difference='independent trusted authority selection vs coherent private output',
      required_actions=['allow after sync','deny canonical admission']),
 dict(observation='canonical WAL only',same_observation={'canonical_version':1,'canonical_P':'P1'},
      hidden_difference='actual private input chain roots at P1 vs unrelated P0',
      required_actions=['allow compatible provisional view','withdraw incompatible view']),
 dict(observation='canonical WAL only',same_observation={'canonical_version':0,'canonical_frontier':0},
      hidden_difference='accepted unsatisfied input with original deadline vs no accepted input',
      required_actions=['retain and drain accepted obligation','no accepted obligation to resume']),
 dict(observation='row completion only',same_observation={'j':'complete'},
      hidden_difference='another physical row executing vs batch actually drained',
      required_actions=['retain worker lease','allow worker reuse'])]
r=dict(status='PASS_CPU_EXECUTABLE_WITNESSES_AND_INFORMATION_PAIRS',witnesses=out,pairs=pairs,
    nontriviality='declared legal work must be allowed; rejecting everything is not an alternative',
    alternatives='equivalent trusted evidence/ordinary safe transactions/complete Standard can supply the same information',
    not_claimed='universal minimality, new cryptography, natural fault prevalence, GPU performance')
p=W/'INFORMATION_CHARACTERIZATION_v1.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
