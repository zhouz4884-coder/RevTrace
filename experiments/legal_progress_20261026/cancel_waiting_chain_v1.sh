set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
import pathlib,json,os,signal,time,hashlib,sys
b=pathlib.Path(sys.argv[1]);o=b/'results/revtrace/dependability_20261025/lp1_20261026'
assert not (o/'CHAIN_PROGRESS.json').exists(),'queue already entered next stage: do not cancel'
owner=json.loads((o/'CHAIN_OWNER.json').read_text());pid=owner['pid'];p=pathlib.Path('/proc')/str(pid)
raw=p.joinpath('cmdline').read_bytes();assert b'lp1_20261026/after_m_chain_v1.py' in raw
assert not list(p.joinpath('task',str(pid),'children').read_text().split()),'own queue has children; do not cancel'
identity=dict(pid=pid,command_sha256=hashlib.sha256(raw).hexdigest(),stat=p.joinpath('stat').read_text())
os.kill(pid,signal.SIGTERM);time.sleep(.3)
(o/'CHAIN_V1_CANCELLED_BEFORE_GPU.json').write_text(json.dumps(dict(status='OWN_WAIT_ONLY_CANCELLED',identity=identity,
 reason='prelaunch audit found missing external service power sampler; no GPU experiment interrupted; M owner untouched'),indent=2)+'\n')
print('own wait-only chain cancelled; M left running')
PY
