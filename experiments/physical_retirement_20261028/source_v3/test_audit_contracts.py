"""Auditor controls, not new GPU experiments."""
from pathlib import Path
import ast,sys,math
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W))
import x_service_metrics as m
def test_auditor_does_not_shadow_its_global_helper_functions():
    tree=ast.parse((W/'x_service_metrics.py').read_text());helpers={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    for fn in [n for n in tree.body if isinstance(n,ast.FunctionDef)]:
        local={n.id for n in ast.walk(fn) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store)}
        assert not local&helpers,(fn.name,local&helpers)
def test_unfulfilled_frontiers_cannot_be_removed_by_percentile():
    assert math.isinf(m.quantile([1.,2.,math.inf],.99));assert m.export_float(math.inf) is None
    assert m.quantile([0.,2.],.5)==1.
def test_original_deadline_survives_owner_start_offset():
    origin,owner,offset,F=100.,103.,.25,64000
    relative_ready=origin-owner+offset+F/16000
    assert owner+relative_ready==origin+offset+F/16000
    assert relative_ready!=offset+F/16000
