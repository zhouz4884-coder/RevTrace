"""Bounded CPU source-function witnesses; not a model checker or GPU evidence."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as N
import argparse,hashlib,json,platform,subprocess,sys

from upstream.continuity_proof import eligible_chain
from upstream.certified_display import ContinuityView,text_sha
from upstream.dgft import digest_tokens

W=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    with Path(p).open('x',encoding='utf8') as stream:json.dump(v,stream,indent=2);stream.write('\n')

def verified(manifest):
    m=read(manifest);git=lambda *a:subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
    assert git('rev-parse','HEAD')==m['code_commit'] and len(m['code_commit'])==40
    assert not git('status','--porcelain','--untracked-files=all')
    assert git('rev-parse','--show-toplevel').replace('\\','/').lower()==W.as_posix().lower()
    assert (set(git('ls-files','-z').split('\0'))-{''})=={r['path'] for r in m['files']}
    for row in m['files']:
        p=W/row['path'];assert p.stat().st_size==row['bytes'] and fsha(p)==row['sha256']
    return m['code_commit']

def fixture():
    s=N(sid=0,segment_end=1,state=N(prompt_tokens=(1,),audio_frontier_window=32000),branch_generation=2,
        branch_chunk=2,branch_tokens=(1,2),fine_busy=True,fine_window=3)
    jobs={'a':dict(job_id='a',role='proposal',session_id=0,branch_generation=2,chunk_id=0,end_window=1,prompt_tokens=[],audio_start_sample=0,audio_end_sample=32000),
          'b':dict(job_id='b',role='proposal',session_id=0,branch_generation=2,chunk_id=1,end_window=2,prompt_tokens=[1],audio_start_sample=0,audio_end_sample=64000),
          'c':dict(job_id='c',role='proposal',session_id=0,branch_generation=2,chunk_id=2,end_window=3,prompt_tokens=[1,2],audio_start_sample=0,audio_end_sample=96000)}
    results={(0,1):dict(job_id='a',state_tokens=[1]),(0,2):dict(job_id='b',state_tokens=[1,2])}
    return s,jobs,results

def view_case(policy):
    v=ContinuityView(policy);P=digest_tokens([1]);v.consume(dict(kind='run-start',t0_perf=1.))
    first=dict(kind='display',session_id=0,time=0.,displayed=0.,version=0,canonical_version=0,display_revision=1,
        job_id='a',text='one',audio_end_sample=32000,end_window=1,chunk_id=0,
        input_projection_sha256=digest_tokens([]),output_projection_sha256=P,branch_generation=0)
    v.consume(first)
    v.consume(dict(first,job_id='b',display_revision=2,text='one two',audio_end_sample=64000,end_window=2,
        chunk_id=1,input_projection_sha256=P,output_projection_sha256=digest_tokens([1,2])))
    v.consume(dict(kind='commit',session_id=0,version=1,segment_id='t',audio_end_sample=32000,next_prompt_tokens=[1]))
    return v.consume(dict(kind='canonical-display',session_id=0,time=1.,displayed=1.,version=1,display_revision=3,
        transaction_id='t',audio_end_sample=32000,text='one',canonical_projection_sha256=P,text_sha256=text_sha('one')))

def cases():
    rows=[]
    for attack in ['none','sameP_wrongF','different_projection','broken_frozen_edge','unreachable_tip',
                   'wrong_inflight_input','duplicate_inflight','covered_inflight','missing_boundary']:
        s,j,r=fixture()
        if attack=='sameP_wrongF':j['a']['audio_end_sample']=16000
        if attack=='different_projection':r[0,1]['state_tokens']=[9]
        if attack=='broken_frozen_edge':j['b']['prompt_tokens']=[9]
        if attack=='unreachable_tip':s.branch_tokens=(9,)
        if attack=='wrong_inflight_input':j['c']['prompt_tokens']=[9]
        if attack=='duplicate_inflight':j['d']=dict(j['c'],job_id='d')
        if attack=='covered_inflight':j['c']['audio_end_sample']=32000
        if attack=='missing_boundary':del r[0,1]
        ok,reason=eligible_chain(s,j,r);expected=attack=='none'
        rows.append(dict(case=attack,eligible=ok,reason=reason,expected=expected,pass_check=ok==expected,
            evidence_tier='CPU actual frozen predicate fixture; no neural execution or guard-minimality proof'))
    s,j,r=fixture();del r[0,1]
    node=dict(job_id='direct',chunk_id=1,input_projection_sha256=digest_tokens([1]),audio_end_sample=64000)
    alternate=ContinuityView('two_lane')._compatible(dict(F=32000,nodes={}),node,digest_tokens([1]))
    conservative=eligible_chain(s,j,r)[0]
    rows.append(dict(case='sufficient_is_not_universally_necessary',owner_eligibility=conservative,
        consumer_direct_frozen_input_proof=alternate,pass_check=not conservative and alternate,
        scope='Comparison of two actual predicates on declared fixtures; no claim this synthetic state is a native service trace.'))
    a=view_case('two_lane');b=view_case('checked_snapshot')
    rows.append(dict(case='two_lane_retains_compatible_whole_hypothesis',view=a,
        pass_check=a['valid_visible_frontier']==64000 and a['certified_frontier']==32000 and not a['joined_suffix']))
    rows.append(dict(case='snapshot_withdrawal_is_safe_but_loses_progress',view=b,
        pass_check=b['valid_visible_frontier']==b['certified_frontier']==32000 and b['tentative_invalidated']))
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-manifest',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    commit=verified(a.source_manifest);config=read(a.config);assert config['analysis_code_commit']==commit
    a.out.mkdir(parents=True,exist_ok=False)
    put(a.out/'CONFIG.json',config)
    put(a.out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        execution_scope='local CPU only; actual source-function fixtures, no GPU/model or service measurements'))
    put(a.out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],analysis_code_commit=commit,
        upstream_neural_source_commit=config['upstream_source_commit'],frozen_config=str(a.config),
        frozen_config_sha256=fsha(a.config),environment_record=str(a.out/'ENVIRONMENT.json'),
        environment_record_sha256=fsha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out/'CASES.json'),
        aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),
        source_manifest_sha256=fsha(a.source_manifest)))
    rows=cases();put(a.out/'CASES.json',rows)
    passed=all(r['pass_check'] for r in rows) and len(rows)==config['expected_cases']
    assert verified(a.source_manifest)==commit
    put(a.out/'SUMMARY.json',dict(cases=len(rows),passed=sum(r['pass_check'] for r in rows),
        limitations='Targeted CPU fixtures only; not exhaustive refinement, universal minimality, semantic ASR correctness or a service-effect estimate.'))
    put(a.out/'GATE.json',dict(gate='PASS_TARGETED_C1_CPU_WITNESSES' if passed else 'FAIL_PRESERVED'))
    print(json.dumps(dict(cases=len(rows),passed=sum(r['pass_check'] for r in rows))))
    assert passed

if __name__=='__main__':main()
