"""Spawn-safe observer entry; calls the untouched original Owner verbatim."""
from __future__ import annotations
import pathlib
from cost_probe import CostProbe

def observed_owner(config, manifest, out, *args):
    from resilience_owner import owner_main
    mode = config['cost_observer']['enabled']
    probe = CostProbe(pathlib.Path(out)/'cost_spans', 'owner', mode).install()
    try:
        return owner_main(config, manifest, out, *args)
    finally:
        probe.close()

