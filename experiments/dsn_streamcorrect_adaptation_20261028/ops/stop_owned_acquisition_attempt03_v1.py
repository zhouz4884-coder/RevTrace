import pathlib,json,hashlib,os,signal,datetime
O=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028/assets_v1')
h=json.loads((O/'DETACHED_LAUNCH_HANDLE_attempt03.json').read_text());p=pathlib.Path('/proc')/str(h['pid'])
assert h['pid']==1626317 and h['start_ticks']==500037515
assert int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==h['start_ticks']
assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256']=='f976ccf4e0c03e952cb420e82c306dc843241922f6ab46ec6c927f3a6f67a530'
os.kill(h['pid'],signal.SIGINT)
record=dict(status='OWNED_EXACT_WRITER_SIGINT_REQUESTED',pid=h['pid'],start_ticks=h['start_ticks'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 reason='Exact public HF 64MiB memory probe sustained 2.864x contemporaneous ModelScope writer; retain same frozen asset bytes, SHA and partial')
(O/'TRANSPORT_SWITCH_attempt03_REQUEST.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
