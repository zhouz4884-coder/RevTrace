"""Same actual protocol events, deep reference vs ordinary COW engineering."""
from pathlib import Path
import sys,pickle,copy,random
import pytest
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
import revtrace.composed_kernel as core
from cpu_full_counterexample import run

def test_all_actual_protocol_events_match_and_preserve_snapshots(tmp_path,monkeypatch):
    real=core.step;counts={};retained=[];denied=0
    def paired(s,kind,p,**kw):
        nonlocal denied
        before=pickle.dumps(s);a,ea=real(s,kind,p);b,eb=real(s,kind,p,incremental=True)
        assert a==b and ea==eb and pickle.dumps(s)==before
        # Invalid epoch, owner, contract and unknown event: rejection is pure.
        for badkind,badp in [(kind,dict(p,epoch=s.epoch+1)),(kind,dict(p,owner=s.owner+1)),
                             (kind,dict(p,contract='wrong')),('unknown',p)]:
            for inc in [False,True]:
                with pytest.raises(core.Denied):real(s,badkind,badp,incremental=inc)
                assert pickle.dumps(s)==before
                denied+=1
        for old,blob in retained:assert pickle.dumps(old)==blob
        retained.append((s,before));counts[kind]=counts.get(kind,0)+1
        return b,eb
    monkeypatch.setattr(core,'step',paired)
    root=tmp_path/'runs';root.mkdir()
    for mode in ['latest','two-register','scan','mv-index','mv-index-envelope','dominance']:run(root,mode)
    assert {'recover-fact','input-synced','dispatch','row-complete','batch-drained','admission-request',
            'canonical-synced','install','publish','apply-request','view-applied'}<=set(counts)
    assert denied>500

def test_partial_failure_does_not_mutate_shared_nested_objects():
    s=core.State('c',0,1.)
    s.C={0:dict(v=0,F=0,P='p')};s.D={0:{}};s.V={0:dict(v=0,F=0,visible=0)}
    s.I={0:dict(accepted=10,offered=10,reserved=10)}
    s.J={'j':dict(worker='w',result=None)}
    for kind,p in [('dispatch',dict(worker='w',jobs=[])),('row-complete',dict(id='j',worker='wrong')),
                   ('canonical-synced',dict(operation='missing')),('view-applied',dict(operation='missing'))]:
        blob=pickle.dumps(s)
        for inc in [False,True]:
            with pytest.raises((core.Denied,KeyError)):core.step(s,kind,p,incremental=inc)
            assert pickle.dumps(s)==blob
