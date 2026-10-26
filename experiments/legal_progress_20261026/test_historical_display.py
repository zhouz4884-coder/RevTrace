"""Native compatibility reference, duplicate ancestry and permission controls."""
import sys,json,copy,hashlib,random
from pathlib import Path
import pytest
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.historical_display import HistoricalEnvelopeView
from revtrace.historical_display import kernel_private_support
from revtrace.composed_kernel import Kernel
from revtrace.dgft import digest_tokens

def runstart():return dict(kind='run-start',t0_perf=1.,contract_digest='c')
def node(j,chunk,end,inp,out,rev=1,branch=0):
    return dict(kind='display',session_id=0,job_id=j,chunk_id=chunk,end_window=end,audio_end_sample=end*10,
        input_projection_sha256=inp,output_projection_sha256=out,text=j,text_sha256=hashlib.sha256(j.encode()).hexdigest(),
        branch_generation=branch,contract_epoch=0,contract_digest='c',display_revision=rev,canonical_version=0,time=rev,displayed=rev)
def mode(name,rev,**kw):return dict(kind='view-mode',mode=name,display_revision=rev,session_id=0,
    contract_epoch=0,contract_digest='c',time=rev,displayed=rev,**kw)

@pytest.mark.parametrize('strategy',['scan','mv-index','mv-index-envelope','dominance'])
def test_individual_revocation_genesis_and_mode_no_new_authority(strategy):
    v=HistoricalEnvelopeView(strategy=strategy,policy='two_lane',strict_bound=True,fine_samples=10)
    v.consume(runstart());v.consume(node('one',0,1,digest_tokens(()),'a'))
    assert v.records[-1]['valid_visible_frontier']==10
    r=v.consume(mode('NORMAL',2,revoked_job_ids=['one']));assert r['valid_visible_frontier']==0
    v.consume(node('two',0,2,digest_tokens(()),'b',3))
    assert v.records[-1]['valid_visible_frontier']==20
    assert v.consume(mode('CERTIFIED-ONLY',4))['valid_visible_frontier']==0
    assert v.consume(node('three',0,3,digest_tokens(()),'c',5)) is None
    assert v.consume(mode('NORMAL',6))['valid_visible_frontier']==0
    assert v.states[0]['version']==0

def test_duplicate_identity_and_late_ambiguity_are_not_hidden():
    v=HistoricalEnvelopeView(strategy='dominance',policy='two_lane',strict_bound=True,fine_samples=10)
    v.consume(runstart());a=node('a',0,1,digest_tokens(()),'x');v.consume(a)
    bad=dict(a,text='changed',display_revision=2)
    with pytest.raises(ValueError):v.consume(bad)
    v.consume(node('b',1,2,'x','y',2));v.consume(node('duplicate-proof',0,1,digest_tokens(()),'x',3))
    s=v.states[0];root=dict(s,F=10,Psha='x')
    assert v._compatible(root,s['nodes']['b'],'x') # direct parent is still valid
    root=dict(s,F=0,Psha=digest_tokens(()))
    assert not v._compatible(root,s['nodes']['b'],root['Psha'])
    assert 'a' in s['_history_tips'] # no deletion with unsealed/individual revocation

@pytest.mark.parametrize('seed',range(8))
def test_scan_index_and_safe_payload_deletion_future_root_equivalence(seed):
    rng=random.Random(seed);views={k:HistoricalEnvelopeView(strategy=k,policy='two_lane',fine_samples=10,
        sealed_branches=True,revocation_contract='owner-mode') for k in ['scan','mv-index','mv-index-envelope','dominance']}
    # Immutable monotone branch graph, including shared roots and branch forks.
    nodes=[];rev=1
    for b in range(4):
        prior=digest_tokens(())
        for end in range(1,8):
            out=f'p{end}' if end<3 else f'p{end}-b{b}'
            nodes.append(node(f'b{b}-{end}',end-1,end,prior,out,rev,b));rev+=1;prior=out
    roots=[(0,digest_tokens(()))]+[(n['audio_end_sample'],n['output_projection_sha256']) for n in nodes]
    roots=sorted(set(roots))
    for v in views.values():
        v.consume(runstart())
        for n in nodes:v.consume(n)
    for F in sorted({r[0] for r in roots}):
        # Each choice at this depth starts from its own same past permissions;
        # no querying an obsolete earlier root after advancing F.
        for root in [r for r in roots if r[0]==F]:
            ans={}
            for k,v in views.items():
                s=copy.deepcopy(v.states[0]);s.update(F=root[0],Psha=root[1])
                selected=v._select(s,'NORMAL');ans[k]=selected['audio_end_sample'] if selected else F
            assert len(set(ans.values()))==1,(seed,root,ans)

def test_sealed_contract_rejects_future_old_window_and_individual_revoke():
    v=HistoricalEnvelopeView(strategy='dominance',policy='two_lane',fine_samples=10,sealed_branches=True,revocation_contract='owner-mode')
    v.consume(runstart());v.consume(node('a',0,2,digest_tokens(()),'p'))
    with pytest.raises(ValueError):v.consume(node('late-old',0,1,digest_tokens(()),'p',2))
    with pytest.raises(ValueError):v.consume(mode('NORMAL',3,revoked_job_ids=['a']))
    v.consume(runstart());assert not v.states

def test_joint_selector_respects_stricter_core_cross_branch_multiplicity():
    k=Kernel('c',0,1.);empty=digest_tokens(())
    events=[node('a',0,1,empty,'x',1,0),node('b',1,2,'x','y',2,0),node('duplicate',0,1,empty,'x',3,1)]
    for e in events:
        k.state.J[e['job_id']]=dict(id=e['job_id'],sid=0,role='proposal',rootF=e['chunk_id']*10,
            inputP=e['input_projection_sha256'],end=e['audio_end_sample'],
            result=dict(P=e['output_projection_sha256'],textsha=e['text_sha256']))
    v=HistoricalEnvelopeView(strategy='scan',policy='two_lane',fine_samples=10,kernel_support=lambda s,n:kernel_private_support(k,s,n))
    v.consume(runstart())
    for e in events:v.consume(e)
    s=v.states[0];assert v._compatible(s,s['nodes']['b'],empty)
    assert not kernel_private_support(k,s,s['nodes']['b'])
    assert v._select(s,'NORMAL')['audio_end_sample']==10
