"""Re-use two recorded development histories as a legal audit oracle; no GPU."""
from pathlib import Path
import json
import audit_n5_fault_formal_v1 as checker
W=Path(__file__).resolve().parent
def test_formal_checker_preserves_recorded_recovery_metrics():
    R=W/'n5_recovery_development_collected_v1';manifest=json.loads((R/'DEVELOPMENT_MANIFEST.json').read_text())
    old=json.loads((W/'N5_RECOVERY_INDEPENDENT_AUDIT_v3.json').read_text())['episodes']
    for expected in old:
        actual=checker.episode(R/'recovery_development'/expected['episode'],manifest)
        for k,v in expected.items():
            if k!='scope':assert actual[k]==v,(expected['episode'],k)
