# Auxiliary audit implementation log

N1 pilot runtime f0e5864 and both actual GPU runs were not changed or rerun.
CPU asset-audit v1 allocated a SimpleNamespace for the Qwen prompt helper;
the helper invokes `_build_messages`, which was absent on that namespace.
It failed before any input reconstruction and wrote no success result.
v2 uses `object.__new__(Qwen3ASRModel)` with only the CPU processor assigned,
so actual class methods are available without model initialization or weights.
The frozen tokenizer warning is retained; no regex/assets are silently changed.
This is an audit-code defect, not a GPU model or protocol failure.
