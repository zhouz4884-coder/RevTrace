"""Tiny read-only actual native-boundary observation; never a serving gate."""
import json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/'LONG_REFERENCE_HANDLE_v2.json').read_bytes())
code=r'''import pathlib,json,collections
h=HANDLE;root=pathlib.Path(h['out']);out={}
for folder in sorted((root/'sources').iterdir()):
 p=folder/'STATE_BOUNDARIES.jsonl';phases=collections.defaultdict(collections.Counter)
 if p.exists():
  with p.open('rb') as stream:
   for raw in stream:
    try:r=json.loads(raw)
    except json.JSONDecodeError:continue
    phase='continuous_original' if r.get('job_id','').startswith('continuous_') else 'serialized_restore' if r.get('job_id','').startswith('restore_') else 'unclassified';c=phases[phase];c[r['boundary']]+=1
    if r.get('buffer_shift'):c['actual_buffer_shifts']+=1
    if r.get('context_changed'):c['actual_context_trim_changes']+=1
    if r.get('bound_still_exceeded'):c['context_bound_still_exceeded']+=1
 out[folder.name]={phase:dict(c) for phase,c in phases.items()}
print(json.dumps(dict(source_commit=h['source_commit'],boundaries=out,scope='Read-only counts of complete emitted records while the reference runs. Not a full gate, performance prefix, natural prevalence or constant-total-memory claim.')))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=15);i.write(code);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();print(b.decode())
finally:c.close()
