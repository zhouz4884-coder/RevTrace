"""Same CPU Owner fixture against real pre/post-fix modules, no model call."""
from pathlib import Path
from types import SimpleNamespace
from collections import deque
import argparse,json,sys
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--expect',choices=['old','fixed'],required=True);a=p.parse_args()
sys.path.insert(0,str(a.source/'src'))
import revtrace.ces_v6_owner as module
seen=[];refreshed=[]
def choose(rows,**kw):
 seen.append(kw['observed_rate']);return {'operation':'generate','sids':[0],'chosen_index':0}
module.choose_anchor=choose
owner=SimpleNamespace(v6={'policy':'anchor_cost'},sessions={0:SimpleNamespace(state=SimpleNamespace(contract_epoch=1,checkpoint_id=2))},_v6_ages={},_v6_times=deque(),_v6_profile=None,contract_digest='fixed',cal={},t0=10.,clock=lambda:12.001,_closed_credit={},_closed_observed_credit=lambda:(refreshed.append(True) or 3.))
row=SimpleNamespace(sid=0,ready=10.,window=1)
out=module.V6OwnerMixin._v6_choose(owner,[row],12.,16)
assert seen==([0.] if a.expect=='old' else [1.5])
assert len(refreshed)==(0 if a.expect=='old' else 1)
print(json.dumps({'source':str(a.source),'expected':a.expect,'same_fixture_actual_observed_rate':seen[0],'credit_refresh_calls':len(refreshed),'CPU_fixture_not_GPU':True,'decision':out}))
