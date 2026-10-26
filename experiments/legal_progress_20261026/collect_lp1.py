"""Explicit bounded evidence export; never traverse model/audio/cache trees."""
from pathlib import Path
import json,hashlib,tarfile,csv,sys,platform,importlib.metadata,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def read(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for v in iter(lambda:f.read(2**22),b''):h.update(v)
    return h.hexdigest()
def main():
    assert read(O/'m_gpu_v2/SUMMARY.json')['episodes']==320
    assert read(O/'X_SERVICE_AUDIT.json')['runs']==16
    oracle=read(O/'x_service_oracle_v1/SUMMARY.json');assert oracle['targets']==16
    assert read(O/'M_INDEPENDENT_AUDIT.json')['status'].startswith('PASS_')
    D=O/'export_v1';D.mkdir();files=set()
    def add(p):
        assert p.resolve().is_relative_to(O) and p.is_file();files.add(p)
    for stage in ['x_gpu_v1','m_gpu_v1','m_gpu_v2','m_old_truth_controls_v1','x_service_oracle_v1']:
        for p in (O/stage).glob('*.json'):add(p)
        for p in (O/stage).glob('*.jsonl'):add(p)
    for p in (O/'m_gpu_v2').glob('*/RESULT.json'):add(p)
    for p in (O/'m_gpu_v2').glob('*/project.sqlite'):add(p)
    for stage in ['scan_ck5_v1','scan_ck5_v2','scan_n5_v2','s_independent_v1','s_independent_v2']:
        add(O/stage/'SUMMARY.json')
    for p in (O/'s_independent_v2').glob('*.jsonl'):add(p)
    X=O/'x_service_v2'
    for p in X.glob('*.json'):add(p)
    allowed=['config.json','sessions.json','initial_states.json','events.jsonl','worker_records.jsonl','consumer.jsonl',
        'worker_batch_accounting.jsonl','kernel_trace.json','provenance.json','result.json','power_samples.json','OWNED_WORKER_HANDLES.json','FACTS_AND_DEBT_RESTORED.json']
    for cell in X.iterdir():
        if not cell.is_dir():continue
        for name in allowed:
            p=cell/'attempt0'/name
            if p.exists():add(p)
        for name in ['envelope.json','arrivals.json','episode.json','input.wal','canonical.wal','POWER_MEASURED.json','episode_power.jsonl','runner.log']:
            add(cell/name)
    for p in O.glob('*owner.log'):add(p)
    for p in O.glob('*OWNER*.json'):add(p)
    for name in ['M_INDEPENDENT_AUDIT.json','M_EPISODES.csv','X_SERVICE_AUDIT.json','X_SERVICE_RUNS.csv','X_SERVICE_FRONTIERS.csv',
                 'SOURCE_AND_ENV.json','X_PROFILES_v1.json','CHAIN_COMPLETE.json','CHAIN_V1_CANCELLED_BEFORE_GPU.json']:add(O/name)
    rows=[dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(files)]
    assert sum(r['bytes'] for r in rows)<120*2**20,'bounded export exceeds declared size'
    (D/'RAW_INDEX.json').write_text(json.dumps(dict(files=rows,total_bytes=sum(r['bytes'] for r in rows),raw_root=str(O),
        scope='original raw files preserved; bounded complete selected sources/output/receipt/DB/WAL evidence, no audio/model/env/credentials',
        oracle_status=oracle['status']),indent=2)+'\n')
    with tarfile.open(D/'RAW_EVIDENCE.tar.gz','w:gz') as arc:
        for r in rows:arc.add(O/r['path'],arcname=r['path'])
    assert (D/'RAW_EVIDENCE.tar.gz').stat().st_size<40*2**20
    models=[]
    for name in ['Qwen3-ASR-1.7B','Qwen2.5-1.5B-Instruct','Qwen2.5-0.5B-Instruct']:
        for p in sorted((B/'models'/name).iterdir()):
            if p.is_file() and p.suffix in ['.safetensors','.json','.txt','.model']:
                models.append(dict(model=name,file=p.name,bytes=p.stat().st_size,sha256=sha(p)))
    (D/'MODEL_INVENTORY.json').write_text(json.dumps(dict(models=models,observation='post-execution read-only inventory; not a new model download or proof of arbitrary historical immutability'),indent=2)+'\n')
    record=dict(status='EXPORTED_BOUNDED_EVIDENCE',files=len(rows),uncompressed_bytes=sum(r['bytes'] for r in rows),
        archive_bytes=(D/'RAW_EVIDENCE.tar.gz').stat().st_size,archive_sha256=sha(D/'RAW_EVIDENCE.tar.gz'),index_sha256=sha(D/'RAW_INDEX.json'),
        inventory_sha256=sha(D/'MODEL_INVENTORY.json'),python=sys.version,platform=platform.platform(),
        packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers']},
        GPUs=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True),
        active_compute_apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True))
    (D/'SUMMARY.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
if __name__=='__main__':main()
