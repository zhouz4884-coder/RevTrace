from types import SimpleNamespace as N
import pytest
from revtrace.continuity_proof import eligible_chain
def fixture():
 s=N(sid=0,segment_end=1,state=N(prompt_tokens=(1,),audio_frontier_window=32000),branch_generation=2,branch_chunk=2,branch_tokens=(1,2),fine_busy=True,fine_window=3)
 jobs={'a':dict(job_id='a',role='proposal',session_id=0,branch_generation=2,chunk_id=0,end_window=1,prompt_tokens=[],audio_start_sample=0,audio_end_sample=32000),'b':dict(job_id='b',role='proposal',session_id=0,branch_generation=2,chunk_id=1,end_window=2,prompt_tokens=[1],audio_start_sample=0,audio_end_sample=64000),'c':dict(job_id='c',role='proposal',session_id=0,branch_generation=2,chunk_id=2,end_window=3,prompt_tokens=[1,2],audio_start_sample=0,audio_end_sample=96000)}
 results={(0,1):dict(job_id='a',state_tokens=[1]),(0,2):dict(job_id='b',state_tokens=[1,2])}
 return s,jobs,results
def test_exact_boundary_completed_chain_and_frozen_pending_job():
 s,j,r=fixture();assert eligible_chain(s,j,r)==(True,('a','b'))
@pytest.mark.parametrize('attack',['boundary','generation','middle_input','inflight_input','tip','missing_boundary','wrong_chunk'])
def test_no_string_or_generation_shortcut(attack):
 s,j,r=fixture()
 if attack=='boundary':j['a']['audio_end_sample']=16000
 if attack=='generation':j['a']['branch_generation']=1
 if attack=='middle_input':j['b']['prompt_tokens']=[9]
 if attack=='inflight_input':j['c']['prompt_tokens']=[9]
 if attack=='tip':s.branch_tokens=(9,)
 if attack=='missing_boundary':del r[0,1]
 if attack=='wrong_chunk':j['c']['chunk_id']=1
 assert not eligible_chain(s,j,r)[0]
