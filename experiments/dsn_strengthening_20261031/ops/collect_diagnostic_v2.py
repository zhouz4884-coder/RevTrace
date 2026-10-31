"""Collect only the frozen <=5MiB diagnostic export, byte-for-byte."""
import hashlib,json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1];d=json.loads((E/'DIAG_STAGED_v2.json').read_bytes());target=E/'DIAGNOSTIC_RESULTS_v2'
assert not target.exists()
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
    s=c.open_sftp()
    with s.open(d['results']+'/GATE.json','rb') as f:gate=f.read()
    g=json.loads(gate);assert g['status']=='PASS_ALL36_ACTUAL_DISPATCH_PAIRING_AND_ALL8_LONG_BOUNDARY_DIAGNOSTICS' and g['cases']==36 and g['long_cases']==8 and g['selected_Canonical_steps']==3976 and g['CPU_controls']['tests']==67
    with s.open(d['results']+'/bounded/OUTPUT_MANIFEST.json','rb') as f:manifest=f.read()
    rows=json.loads(manifest);assert sum(r['bytes'] for r in rows.values())<=5*1024*1024
    target.mkdir();copied=[]
    for name,row in rows.items():
        assert pathlib.PurePosixPath(name).name==name
        with s.open(d['results']+'/bounded/'+name,'rb') as f:data=f.read()
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
        (target/name).write_bytes(data);copied.append(dict(path=name,**row))
    assert (target/'GATE.json').read_bytes()==gate
    (target/'OUTPUT_MANIFEST.json').write_bytes(manifest)
    record=dict(status='PASS_COMPLETE36_BOUNDED_EXPORT_REMOTE_SHA_AND_TOP_GATE_MATCH',remote_raw_results=d['results'],source_commit=g['analysis_code_commit'],actual_NN_source=g['actual_neural_source_commit'],new_model_calls=0,top_gate_sha256=hashlib.sha256(gate).hexdigest(),files=copied)
    (target/'COLLECTION_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(status=record['status'],files=len(copied),bytes=sum(r['bytes'] for r in copied),gate_sha256=record['top_gate_sha256'])))
    s.close()
finally:c.close()
