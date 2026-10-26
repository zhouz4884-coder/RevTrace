"""Create bounded research-only evidence after COMPLETE, without audio/weights.
Runs on the remote 8TB disk. No manuscript or authorization material included.
"""
from pathlib import Path
import json,hashlib,tarfile,sys
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()
def main():
    marker=O/('CAMPAIGN_COMPLETE_v3.json' if (O/'CAMPAIGN_COMPLETE_v3.json').exists() else 'CAMPAIGN_COMPLETE_v2.json')
    assert read(marker)['status'].startswith('COMPLETE_ALL_SIX')
    dest=O/'BOUNDED_EVIDENCE_v1.tar.gz';assert not dest.exists()
    full=[];small=[]
    for f in sorted(O.rglob('*')):
        if not f.is_file() or f.name.endswith('.partial'):continue
        if any(part.startswith('cpu_') for part in f.relative_to(O).parts):continue
        f.resolve().relative_to(O.resolve());rel=f.relative_to(O).as_posix()
        assert f.suffix not in ['.wav','.flac','.safetensors','.bin']
        full.append(dict(path=rel,bytes=f.stat().st_size,sha256=sha(f)))
        if len(f.relative_to(O).parts)==1 and f.suffix in ['.json','.csv','.log','.xml']:
            small.append(f)
        elif f.name in ['FREEZE.json','SUMMARY.json','STOP.json','KILL.json','POLICY.json','ARRIVAL.json','CONTEXT.json',
            'COMMAND_0.json','COMMAND_1.json','RUN_COMPLETE_PENDING_AUDIT.json','OWNER_HANDLE_0.json','OWNER_HANDLE_1.json']:
            small.append(f)
        elif f.name in ['config.json','provenance.json','initial_states.json','workers.json','OWNED_WORKER_HANDLES.json',
            'sessions.json','result.json','FACTS_AND_DEBT_RESTORED.json','EXECUTORS_READY.json','POST_SYNC_KILL_READY.json','BOUNDARY_PROBE.json']:
            small.append(f)
        elif f.name in ['canonical.wal','input.wal','canonical.wal.pre-recovery','input.wal.pre-recovery']:
            small.append(f)
    index=O/'RAW_INDEX_v1.json';index.write_text(json.dumps(dict(files=full,raw_root=str(O),
        scope='source-specific raw remains on8TB; CPU fixture temporary trees excluded; index is not additional execution evidence'),indent=2)+'\n')
    small.append(index)
    # Logs containing completed rows/tensors, power samples and event traces
    # remain indexed remotely, not silently omitted from the audit.
    with tarfile.open(dest,'w:gz') as t:
        for f in sorted(set(small)):t.add(f,arcname=f.relative_to(O).as_posix())
    meta=dict(status='BOUNDED_RESEARCH_EVIDENCE_CREATED',archive_bytes=dest.stat().st_size,
        archive_sha256=sha(dest),bounded_files=len(set(small)),raw_files=len(full),raw_bytes=sum(r['bytes'] for r in full),
        source_commit=read(P/'runtime/SOURCE_MANIFEST.json')['code_commit'],no_manuscript=True)
    (O/'BOUNDED_METADATA_v1.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
if __name__=='__main__':main()
