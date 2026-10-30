"""Mechanical actual-trace input binding; never selects by performance or text."""
import argparse,hashlib,json,pathlib,re,datetime
F=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--case-root',type=pathlib.Path,required=True)
p.add_argument('--runtime-source-commit',required=True);p.add_argument('--output-config',type=pathlib.Path,required=True)
p.add_argument('--experiment-id',required=True);p.add_argument('--original-raw-root');p.add_argument('--collection-manifest',type=pathlib.Path)
p.add_argument('--checker-version',type=int,default=1)
a=p.parse_args();root=a.case_root.resolve()
need_commit=a.runtime_source_commit
assert re.fullmatch('[0-9a-f]{40}',need_commit)
manifest=F/f'packages/TRACE_SOURCE_v{a.checker_version}.json';m=json.loads(manifest.read_bytes())
config=root/'CONFIG.json';run=json.loads(config.read_bytes());assert run['settings']['source_commit']==need_commit
owners=sorted(root.glob('owner_e*'),key=lambda p:int(p.name.removeprefix('owner_e')))
assert owners and all(p.is_dir() and re.fullmatch('owner_e[0-9]+',p.name) for p in owners)
paths=[config,root/'facts.wal',root/'publications.jsonl',root/'consumer.jsonl',root/'ingress.jsonl',root/'ORIGIN.json']
for directory in owners:
    paths.extend(directory/name for name in ('dispatch.jsonl','worker_results.jsonl','owner_events.jsonl','policy_audit.jsonl'))
inputs={}
for path in paths:
    assert path.is_file() and not path.is_symlink()
    inputs[str(path.resolve())]=dict(bytes=path.stat().st_size,sha256=sha(path))
out=dict(experiment_id=a.experiment_id,mode='actual_complete_trace',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    checker_source_commit=m['source_commit'],checker_manifest_sha256=sha(manifest),
    actual_runtime_source_commit=need_commit,case_root=str(root),runtime_config=str(config),
    fact_journal=str(root/'facts.wal'),publication_journal=str(root/'publications.jsonl'),
    consumer_journal=str(root/'consumer.jsonl'),ingress_journal=str(root/'ingress.jsonl'),origin_record=str(root/'ORIGIN.json'),
    owner_directories=[str(d.resolve()) for d in owners],inputs=inputs,allow_incomplete_uncommitted_tail=False,
    fixed_data_rule='All actual Owner attempts, durable facts, dispatch/worker receipts, publication and actual Consumer rows; no metric/outcome based selection.',
    scope='Independent structural implementation trace refinement under declared execution-integrity/state-sufficiency premises. Not fixed GPU replay equality, human correctness or unbounded liveness.')
if a.original_raw_root:
    assert a.original_raw_root.startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/')
    out['original_raw_result_location']=a.original_raw_root
if a.collection_manifest:
    out['source_collection_manifest_sha256']=sha(a.collection_manifest)
assert not a.output_config.exists();a.output_config.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(config=str(a.output_config),config_sha256=sha(a.output_config),checker_source_commit=m['source_commit'],input_files=len(inputs),actual_trace_analyzed=False),indent=2))

