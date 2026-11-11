"""Preserve failed v1; prepare one-line canonical interpreter path repair."""
from pathlib import Path
import hashlib,json
E=Path(__file__).resolve().parents[1]
s=E/'readiness_source';t=E/'readiness_source_v2';t.mkdir(exist_ok=False)
m=json.loads((E/'readiness_ops/SOURCE.json').read_bytes())
for r in m['files']:
    raw=(s/r['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256']
    (t/r['path']).write_bytes(raw)
p=t/'readiness.py';v=p.read_text(encoding='utf8')
a="str(Path(sys.executable).resolve())==c['executable']"
b="Path(sys.executable).resolve(strict=True)==Path(c['executable']).resolve(strict=True)"
assert v.count(a)==1;p.write_text(v.replace(a,b),encoding='utf8')
v=(E/'ops/freeze_launch_readiness.py').read_text(encoding='utf8')
v=v.replace("S=E/'readiness_source';D=E/'readiness_ops'","S=E/'readiness_source_v2';D=E/'readiness_ops_v2'")
v=v.replace('readiness_v1','readiness_v2').replace('readiness-v1','readiness-v2').replace('READINESS_20261111_V1','READINESS_20261111_V2')
(E/'ops/freeze_launch_readiness_v2.py').write_text(v,encoding='utf8')
(E/'readiness_ops/FAILURE_TRIAGE.zh.md').write_text('v1保留FAIL：检查器把实际解释器resolve后的路径与未resolve的期望路径比较，误拒绝同一个Python符号链接。包版本和原始解释器路径完全相同。故障在CPU检查器，不是模型/环境变化；GPU与模型调用为0、权重哈希尚未开始。v2只把两边都resolve(strict=True)，重新冻结实际源、配置与新结果路径；不覆盖v1。\n',encoding='utf8')
print('Prepared new source; preserved v1 failure')
