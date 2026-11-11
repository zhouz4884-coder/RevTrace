"""Prepare/stage final bounded public evidence; never commit, push or copy paper.

Rerunnable after Root appends its final writing/release receipt. Existing target
bytes must match its current manifest before updates. The old current-facing
statuses and delivery manifest are preserved once as historical checkpoints.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,sys
E=Path(__file__).resolve().parents[1]
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
T=W/'experiments'/E.name;PREFIX='experiments/'+E.name+'/'
BLOCK_SUFFIX={'.tex','.bib','.pdf','.png','.jpg','.jpeg','.svg','.tif','.tiff','.docx','.pptx','.wav','.mp3','.mp4','.safetensors','.pt','.pth','.bin','.ckpt','.zip','.pkl','.pickle','.npy','.npz','.parquet','.pyc','.pyo'}
BLOCK_COMPONENTS={'.git','__pycache__','.pytest_cache','models','datasets','cache','raw','raw_results'}
BLOCK_NAMES={'DELIVERY_MANIFEST.json','FINAL_PUBLICATION_INDEX_VERIFICATION.json','PAPER_SKELETON_v16.zh.md','publish_manuscript_v16.py','consumer.jsonl','worker_results.jsonl','dispatch.jsonl','publications.jsonl','power.jsonl','facts.wal','ingress.jsonl'}
SECRET_PATTERNS=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'hf_[A-Za-z0-9]{25,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']
def git(*args):return subprocess.check_output(['git','-C',str(W),*args])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def allowed(p):
    rel=p.relative_to(E);parts=rel.parts
    if any(c in BLOCK_COMPONENTS for c in parts) or p.suffix.lower() in BLOCK_SUFFIX or p.name in BLOCK_NAMES:return False
    if parts[:2]==('review','V16_FINAL_READER_FILES'):return False
    if parts[0]=='ops' and any(s in p.name.lower() for s in ('manuscript','private','writing')):return False
    return True
def preserve_unexecuted_LA_v1():
    source=E/'external_rule_source_v1';package=E/'external_rule_packages_v1_preserved'
    def sg(*args):return subprocess.check_output(['git','-C',str(source),*args],stderr=subprocess.PIPE).decode().strip()
    commit=sg('rev-parse','HEAD');assert commit=='a105e33d7dd8349a86d46cf427f9de0fadcc899d' and not sg('status','--porcelain','--untracked-files=all')
    paths=sorted(p for p in sg('ls-files','-z').split('\0') if p);rows=[dict(path=p,bytes=(source/p).stat().st_size,sha256=sha(source/p)) for p in paths]
    package.mkdir(exist_ok=True);plain=package/'plain_source';plain.mkdir(exist_ok=True)
    for row in rows:
        target=plain/row['path'];target.parent.mkdir(parents=True,exist_ok=True);raw=(source/row['path']).read_bytes()
        if target.exists():assert target.read_bytes()==raw
        else:target.write_bytes(raw)
    manifest=package/'SOURCE.json'
    if manifest.exists():assert read(manifest)['files']==rows and read(manifest)['source_commit']==commit
    else:write(manifest,dict(source_commit=commit,code_commit=commit,execution_status='UNEXECUTED_HISTORICAL_PROTOTYPE_NOT_RESULT',files=rows))
    bundle=package/'source.bundle'
    if not bundle.exists():sg('bundle','create',str(bundle),'--all')
    sg('bundle','verify',str(bundle))
    write(package/'PRESERVATION_INDEX.json',dict(record_type='ARCHIVE_ONLY_UNEXECUTED_V1_PRESERVATION',source_commit=commit,source_files=len(rows),source_manifest_sha256=sha(manifest),bundle_sha256=sha(bundle),old_one_byte_placeholders_preserved_at='external_rule_packages_v1',CPU_runs=0,model_calls=0,GPU_runs=0,scope='Archival packaging only; v2 is the executed LA2 source'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch-verify',action='store_true');args=parser.parse_args()
    # Staging is required by the existing index verifier, but stays in this tree.
    for command in [('diff','--name-only','-z'),('diff','--cached','--name-only','-z'),('ls-files','--others','--exclude-standard','-z')]:
        paths=[p.decode() for p in git(*command).split(b'\0') if p]
        assert all(p.startswith(PREFIX) for p in paths),('unrelated worktree edits',paths)
    old=read(T/'DELIVERY_MANIFEST.json');known={r['path']:r for r in old['files']}
    for rel,row in known.items():
        assert (T/rel).is_file() and (T/rel).stat().st_size==row['bytes'] and sha(T/rel)==row['sha256'],'prior published bytes drift: '+rel
    history=E/'historical_checkpoints';history.mkdir(exist_ok=True)
    for name in ('WORKING_STATE.json','LIVE_GPU_STATUS.json','README.md'):
        checkpoint=history/(Path(name).stem+'_BEFORE_FINAL_DELIVERY_20261111'+Path(name).suffix)
        if not checkpoint.exists():checkpoint.write_bytes((E/name).read_bytes())
    checkpoint=history/'DELIVERY_MANIFEST_BEFORE_FINAL_20261111.json'
    if not checkpoint.exists():checkpoint.write_bytes((T/'DELIVERY_MANIFEST.json').read_bytes())
    for name in ('EXPR_REGISTRY.json','EXPR_REGISTRY.zh.md'):
        checkpoint=history/(Path(name).stem+'_BEFORE_FINAL_STATUS_REFRESH_20261111'+Path(name).suffix)
        if not checkpoint.exists():checkpoint.write_bytes((E/name).read_bytes())
    preserve_unexecuted_LA_v1()
    registry=read(E/'EXPR_REGISTRY.json');final=read(E/'FINAL_N8_SUMMARY.json')
    assert registry['counts']['active_root_campaigns']==0 and registry['counts']['actual_GPU_serving_child_cells_locally_closed']==56
    assert final['status']=='COMPLETE_FINAL_N8_ARITHMETIC'
    campaigns={}
    for tag,count in [('PILOT24_V2',24),('RESOURCE8_V1',8),('CONFIRM_NEW2_FULL_READY_V1',8),('CONFIRM_LAST4_FULL_READY_V1',16)]:
        summary=read(E/'gpu_results'/tag/'SUMMARY.json');assert summary['completed_trials']==count
        closure=E/'launch_ops'/tag/'RESOURCE_CLOSURE.json';c=read(closure)
        assert c.get('active_owned_process') is False and c.get('compute_owners','')=='',tag
        campaigns[tag]=dict(trials=count,summary='gpu_results/'+tag+'/SUMMARY.json',gate='gpu_results/'+tag+'/GATE.json',resource_closure='launch_ops/'+tag+'/RESOURCE_CLOSURE.json',resource_closure_sha256=sha(closure))
    refs={}
    for tag in ('REFERENCE_FULL4_V2','REFERENCE_LAST4_V1'):
        s=read(E/'gpu_results'/tag/'SUMMARY.json');g=read(E/'gpu_results'/tag/'GATE.json');assert g['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'
        closure=E/'launch_ops'/tag/'RESOURCE_CLOSURE.json'
        refs[tag]=dict(continuous_steps=g['original_continuous_steps'],exact_start_restored_steps=s['ledger']['restored_original_input_full_step_completed'],fixed_warmup_calls=s['ledger']['declared_fixed_warmup_full_step_calls'],summary='gpu_results/'+tag+'/SUMMARY.json',resource_closure='launch_ops/'+tag+'/RESOURCE_CLOSURE.json',resource_closure_sha256=sha(closure),reference_only=True)
    write(E/'WORKING_STATE.json',dict(record_type='FINAL_CLOSED_RESEARCH_EXECUTION_STATE',date='2026-11-11',research_phase='NEW_RESEARCH_EXPERIMENTS_CLOSED_BY_USER',research_execution_complete=True,
        GPU_status='ALL56_SERVING_AND_TWO_PAID_REFERENCE_CAMPAIGNS_CLOSED',active_root_campaigns=0,frozen_runtime='de0936b2e30179d63aeef6e235cd1af685578c58',frozen_runtime_files=66,original_NN4f_ancestor='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',
        pilot_reference_driver='f367c4e1068a9391a0e99d8537c94995a3388e13',focused_confirmation_driver='4fb6d05f1cf4ad80e73bae9934afaed04c60edeb',resource_driver='7b83b2151040512776b5bdaa7f7680e7a8f59047',
        formal_CPU_protocol_controls_passed=225,formal_CPU_action_controls_passed=35,pilot_reference_CPU_controls_passed=56,focused_CPU_controls_passed=10,resource_CPU_controls_passed=5,external_LA2_CPU_controls_passed=28,
        completed_serving_trials=56,closed_campaigns=campaigns,paid_reference_campaigns=refs,primary_full_ready_cells=32,primary_speaker_clusters=8,primary_scope='first2 pilot plus next2 and last4 confirmation; all existing-bank speakers, no repeat pseudoreplication',
        final_N8='FINAL_N8_SUMMARY.json',complete_registry='EXPR_REGISTRY.json',failed_CPU_records_preserved=registry['counts']['CPU_failed_records'],new_research_experiments_closed_by_user=True,
        writing_status='V16_REWRITE_FINAL_QA_PASS_AND_PRIVATE_GITHUB_BYTE_VERIFIED',original_research_task_unfinished=False,writing_and_private_manuscript_delivery='Root-owned separate release, excluded from this public evidence tree',v15_unchanged=True,
        writing_release_receipts=['V16_WRITING_AND_RESEARCH_CLOSURE.zh.md','V16_MANUSCRIPT_GITHUB_RECEIPT.json','V16_SOURCE_COLD_BUILD_CHECK.json'],
        publication_state='BOUNDED_EVIDENCE_PREPARED_STAGED_NOT_COMMITTED_OR_PUSHED',historical_checkpoints='historical_checkpoints',publication_commit_is_not_execution_commit=True))
    latest=max(read(E/r['resource_closure'])['utc'] for r in campaigns.values())
    write(E/'LIVE_GPU_STATUS.json',dict(record_type='FINAL_CLOSED_GPU_EXECUTION_STATUS',last_authoritative_serving_closure_utc=latest,active_root_campaigns=0,current_active=False,current_campaign=None,completed_serving_trials=56,primary_full_ready_cells=32,primary_speaker_clusters=8,paid_reference_campaigns=2,closed_campaigns=campaigns,reference_closures=refs,
        status_basis='Collected closed controller gates and PID-generation/physical-release receipts; not a new remote polling observation',scope='P24+R8+focused8+focused16; resource mixtures reuse existing voices; these are not56 independent speakers. Research closed by user; no further GPU matrix pending.'))
    # Refresh only current metadata identities, never scientific experiment rows.
    archived_registry=read(history/'EXPR_REGISTRY_BEFORE_FINAL_STATUS_REFRESH_20261111.json')
    registry['historical_snapshot_identities_at_registry_creation']=[dict(original_path_at_capture=r['path'],bytes=r['bytes'],sha256=r['sha256'],scope='historical identity recorded before final status refresh, not a current path binding') for r in archived_registry.get('snapshots',[])]
    registry['snapshots']=[dict(path=n,bytes=(E/n).stat().st_size,sha256=sha(E/n),role='CURRENT_FINAL_STATUS' if n=='WORKING_STATE.json' else 'PRESERVED_EXECUTION_CHECKPOINT') for n in ('WORKING_STATE.json','EXECUTION_CHECKPOINT.zh.md')]
    registry['final_status_refresh']=dict(scope='Metadata identities only;87 scientific/container records and56 serving children unchanged',writing_status='V16_REWRITE_FINAL_QA_PASS_AND_PRIVATE_GITHUB_BYTE_VERIFIED',historical_status_checkpoint='historical_checkpoints/WORKING_STATE_BEFORE_FINAL_DELIVERY_20261111.json')
    assert registry['counts']==archived_registry['counts'];write(E/'EXPR_REGISTRY.json',registry)
    text=(E/'EXPR_REGISTRY.zh.md').read_text(encoding='utf8');text=text.replace('旧WORKING_STATE仍含next2-running等过时字段，完成门与Root最新闭合状态优先。','当前WORKING_STATE与LIVE_GPU_STATUS已刷新为最终闭合状态；原始状态字节与先前snapshot身份保留在historical_checkpoints。registry snapshots逐项绑定当前最终文件，原创建时身份另列为historical_snapshot_identities_at_registry_creation。')
    (E/'EXPR_REGISTRY.zh.md').write_text(text,encoding='utf8')
    (E/'README.md').write_text('''# RevTrace v16: closed research evidence

The research execution phase is closed: **56 actual serving trials and two paid
reference campaigns**, with no active Root experiment process in the collected
closure receipts. Start with [the complete master record](RESEARCH_STRENGTHENING_AND_WRITING_MASTER.zh.md),
[the full experiment registry](EXPR_REGISTRY.zh.md), and [final N8 results](FINAL_N8_SUMMARY.zh.md).

The primary comparison comprises32 Full/Ready cells across eight existing-bank
speaker clusters: first2 pilot, next2 confirmation, and last4 confirmation.
The other pilot policies and eight nested multi-session resource cells remain
separate comparisons. Reference work uses newly measured original NN3 full
states/C/U/IDs; derived bank slices preserve exact measured parent objects.
Reference cost, actual serving, fixed-schedule offline analyses, finite protocol
controls, failed CPU records, and unexecuted prototypes have distinct identities.

[Current closed status](LIVE_GPU_STATUS.json) replaces the earlier running
snapshot, whose bytes remain in [historical checkpoints](historical_checkpoints/).
The external LA2 v2 analysis preserves all24 fixed pilot schedules and96 rule
rows, with28 controls; its v1 unexecuted source remains archived. Final timer
derivation preserves missing abandoned-call infer timers as NA and reports
occupied-worker time separately from CUDA activity and both-board energy.

Every actual execution source has a complete manifest and Git bundle. This
delivery commit is an evidence archive, not a neural or analysis execution
commit. The designated8TB disk retains models, datasets, caches and bulk raw
event/Consumer/character ledgers. Only bounded outputs, reference witnesses,
complete source snapshots/bundles, review/decision records and audited indexes
are included here. No manuscript, paper figures, PDF, credentials or nested Git
repository is copied. v15 and the separate v16 writing/private release remain
outside this evidence delivery. `DELIVERY_MANIFEST.json` binds every included file.
''',encoding='utf8')
    selected=[];excluded=[]
    for p in sorted(E.rglob('*')):
        if not p.is_file():continue
        if not allowed(p):
            if '.git' not in p.relative_to(E).parts and '__pycache__' not in p.parts:excluded.append(p.relative_to(E).as_posix())
            continue
        assert not p.is_symlink() and p.resolve().is_relative_to(E.resolve())
        rel=p.relative_to(E).as_posix();raw=p.read_bytes();assert len(raw)<8_000_000,rel
        for pat in SECRET_PATTERNS:assert not re.search(pat,raw.decode('utf8',errors='ignore')),'possible secret: '+rel
        selected.append((rel,raw))
    # Old indexed files remain archived, but none may be forbidden by this policy.
    removed=[]
    for rel in list(known):
        if allowed(E/rel):continue
        target=(T/rel).resolve();assert target.is_relative_to(T.resolve()) and target.is_file()
        target.unlink();known.pop(rel);removed.append(rel)
    for rel,raw in selected:
        target=T/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        known[rel]=dict(path=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    rows=sorted(known.values(),key=lambda r:r['path']);total=sum(r['bytes'] for r in rows);assert total<64_000_000,total
    for row in rows:assert (T/row['path']).stat().st_size==row['bytes'] and sha(T/row['path'])==row['sha256'],row['path']
    manifest=dict(record_type='FINAL_BOUNDED_CLOSED_V16_RESEARCH_EVIDENCE_DELIVERY',files=rows,file_count=len(rows),bytes=total,closed_serving_trials=56,closed_primary_full_ready_cells=32,primary_speaker_clusters=8,paid_reference_GPU_campaigns=2,reference_continuous_steps=sum(r['continuous_steps'] for r in refs.values()),reference_exact_start_restores=sum(r['exact_start_restored_steps'] for r in refs.values()),reference_fixed_warmup_calls=sum(r['fixed_warmup_calls'] for r in refs.values()),
        registry_records=registry['counts']['closed_local_RUN_RECORD_records'],active_root_campaigns=0,research_closed_by_user=True,failed_CPU_records_preserved=True,external_LA2_v2_fixed_cells=24,external_LA2_v2_rule_rows=96,external_LA2_v2_controls=28,external_LA2_v1_unexecuted_preserved=True,
        source_bundles_and_complete_snapshots_included=True,models_datasets_caches_bulk_raw_excluded=True,manuscripts_and_paper_figures_excluded=True,no_nested_git=True,publication_commit_not_execution_commit=True,archive_parent_commit=git('rev-parse','HEAD').decode().strip(),excluded_current_source_files=excluded,
        bounded_reference_witness_scope='JSON original full-state/C/U/ID witnesses included as in earlier deliveries; bulk actual event/Consumer ledgers remain8TB',stage_only_no_commit_no_push=True,removed_non_evidence_paths=removed)
    write(T/'DELIVERY_MANIFEST.json',manifest)
    git('add','--',PREFIX)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','excluded_current_source_files')},indent=2))
    if args.batch_verify:verify_index_batch(manifest)
    else:subprocess.run([sys.executable,'-B',str(E/'ops/verify_publication_index.py')],check=True)
def verify_index_batch(manifest):
    """Equivalent indexed-blob checks without a separate Git process per file."""
    staged={p.decode() for p in git('diff','--cached','--name-only','-z').split(b'\0') if p}
    expected={PREFIX+r['path'] for r in manifest['files']}|{PREFIX+'DELIVERY_MANIFEST.json'}
    assert staged<=expected and PREFIX+'DELIVERY_MANIFEST.json' in staged
    indexed={}
    for record in git('ls-files','--stage','-z',PREFIX).split(b'\0'):
        if not record:continue
        meta,path=record.split(b'\t',1);mode,oid,stage=meta.split();assert mode!=b'160000' and stage==b'0';indexed[path.decode()]=oid.decode()
    requests=[(PREFIX+r['path'],r) for r in manifest['files']]+[(PREFIX+'DELIVERY_MANIFEST.json',None)]
    payload=('\n'.join(indexed[path] for path,row in requests)+'\n').encode()
    proc=subprocess.run(['git','-C',str(W),'cat-file','--batch'],input=payload,capture_output=True,check=True);data=proc.stdout;cursor=0
    for path,row in requests:
        end=data.index(b'\n',cursor);oid,kind,size=data[cursor:end].split();size=int(size);cursor=end+1;raw=data[cursor:cursor+size];cursor+=size+1
        assert oid.decode()==indexed[path] and kind==b'blob'
        if row is None:assert raw==(T/'DELIVERY_MANIFEST.json').read_bytes()
        else:assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],path
    assert cursor==len(data)
    assert sha(W/'Paper_DSN/revisions/20261105_dsn2027_release_v15/main.pdf')=='b5c410b6c6fd08cec08535398910b49398dc0dc78cde497638eb537b661db750'
    (E/'DELIVERY_MANIFEST.json').write_bytes((T/'DELIVERY_MANIFEST.json').read_bytes())
    receipt=dict(status='PASS_ALL_INDEX_BLOBS_MATCH_FINAL_BOUNDED_MANIFEST_BATCH',staged_files=len(staged),complete_snapshot_files=len(expected),bytes=manifest['bytes'],no_gitlinks=True,v15_PDF_unchanged=True,verification='git ls-files --stage -z +one git cat-file --batch, all blob lengths/SHA256 includingmanifest')
    write(E/'FINAL_PUBLICATION_INDEX_VERIFICATION.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
