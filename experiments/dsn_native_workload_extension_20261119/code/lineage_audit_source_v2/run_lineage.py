"""Frozen CPU-only all-dispatch lineage recount; no rescheduling/model calls."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,array,ast,datetime,hashlib,importlib.abc,json,os,platform,subprocess,sys,traceback,unittest,wave
from lineage import NN,need,encoded,fingerprint,cut_key,same,classify_owner
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
def read(p):return json.loads(Path(p).read_bytes())
def lines(p):return[json.loads(x)for x in Path(p).read_bytes().splitlines()if x.strip()]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def put(p,x):
    with Path(p).open('x',encoding='utf8',newline='\n')as stream:json.dump(x,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
def verify_source(root,manifest,expected=None):
    root=Path(root).resolve();m=read(manifest);commit=m['code_commit']
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    need(expected is None or commit==expected,'wrong frozen source')
    need(git('rev-parse','--show-toplevel')==str(root)and git('rev-parse','HEAD')==commit,'source not a complete independent checkout')
    need(git('config','--get','core.autocrlf')=='false'and not git('status','--porcelain','--untracked-files=all'),'dirty/translated source')
    need(set(git('ls-files').splitlines())=={r['path']for r in m['files']},'incomplete source manifest')
    for r in m['files']:
        p=root/r['path'];need(p.is_file()and not p.is_symlink()and p.stat().st_size==r['bytes']and sha(p)==r['sha256'],'frozen source bytes differ')
    return dict(source_commit=commit,source_root=str(root),source_manifest=str(Path(manifest).resolve()),
        source_manifest_sha256=sha(manifest),complete_files=len(m['files']),clean=True)
class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0]in('torch','transformers','peft','librosa','whisper','simul_whisper'):
            raise ImportError('lineage recount forbids neural imports')
def inventory(paths):
    return{str(p):dict(bytes=Path(p).stat().st_size,sha256=sha(p))for p in sorted(set(map(str,paths)))}

def audit_cell(cell,runtime,scan):
    root=Path(cell['out']);cfg=read(root/'CONFIG.json')
    need(cfg==read(cell['config'])and sha(cell['config'])==cell['config_sha256'],'actual/frozen cell config differs')
    need(cfg['settings']['source_commit']==cfg['source_commit']==NN and cfg['fault']['kind']=='none','not normal declared NN1145 task')
    need(read(root/'GATE.json')['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK','incomplete original task')
    need(read(root/'JOB_ACCOUNTING.json')['status']=='PASS_DISJOINT_JOB_ACCOUNTING','job ledger failed')
    need(read(root/'INDEPENDENT_VIEW_AUDIT.json')['status']=='PASS_NATIVE_VIEW_APPLICATION_AUDIT','actual-policy Consumer audit failed')
    sources={s['source_id']:s for s in cfg['settings']['sources']};need(len(sources)==1,'declared one-source native cell required')
    source=next(iter(sources.values()));wavpath=Path(source['path'])
    need(sha(wavpath)==source['audio_sha256'],'original immutable WAV differs')
    with wave.open(str(wavpath),'rb')as wav:
        need(wav.getframerate()==16000 and wav.getnchannels()==1 and wav.getsampwidth()==2 and wav.getnframes()==source['frames'],'original PCM header changed')
        pcm=wav.readframes(wav.getnframes())
    if 'header'in source:need(hashlib.sha256(pcm).hexdigest()==source['header']['PCM_sha256'],'original full PCM differs')
    samples=array.array('h');samples.frombytes(pcm)
    if sys.byteorder!='little':samples.byteswap()
    floats=array.array('f',(v/32768 for v in samples))
    need(floats.itemsize==4,'not IEEE32 native float array')
    if sys.byteorder!='little':floats.byteswap()
    audio=floats.tobytes()
    def added(sid,a,b):
        need(sid==source['source_id']and 0<=a<b<=source['frames'],'changed input audio range')
        return hashlib.sha256(audio[a*4:b*4]).hexdigest()
    scanned=list(scan(root/'facts.wal',repair_tail=False));header=scanned[0][0]
    need(header['kind']=='genesis'and header['body']['metadata']['actual_source_commit']==NN and
        header['body']['metadata']['config_sha256']==fingerprint(cfg),'WAL genesis/source/config differs')
    initials=read(root/'GENESIS.json');need(initials==header['body']['initials'],'exported/full durable genesis differs')
    facts=[obj for obj,receipt in scanned if obj['kind']=='canonical'];state_by_F={sid:{s['frontier']:s}for sid,s in initials.items()}
    latest=dict(initials)
    for fact in facts:
        b=fact['body'];sid=b['source_id']
        need(same(latest[sid],b['parent_state'])and b['parent_state_sha256']==fingerprint(b['parent_state'])and
             b['next_state_sha256']==fingerprint(b['next_state']),'durable complete original prefix differs')
        latest[sid]=b['next_state'];state_by_F[sid][latest[sid]['frontier']]=latest[sid]
    owner_starts={0:initials}
    supervisor=lines(root/'supervisor.jsonl')
    for row in supervisor:
        event=row.get('event',{})
        if event.get('kind')=='owner_ready':owner_starts[event['owner_epoch']]={sid:state_by_F[sid][F]for sid,F in event['recovered_frontiers'].items()}
    paths=[root/name for name in('CONFIG.json','GENESIS.json','facts.wal','GATE.json','JOB_ACCOUNTING.json','INDEPENDENT_VIEW_AUDIT.json','supervisor.jsonl')]+[wavpath,Path(cell['config'])]
    rows=[];counts=Counter();witnesses=[];all_dispatch=0
    for folder in sorted(root.glob('owner_e*')):
        if not folder.is_dir():continue
        epoch=int(folder.name.removeprefix('owner_e'));need(epoch in owner_starts,'actual recovered Owner start missing')
        files={n:folder/(n+'.jsonl')for n in('dispatch','owner_events','worker_results','policy_audit')};paths.extend(files.values())
        dispatch=lines(files['dispatch']);jobs=[r['job']for r in dispatch];all_dispatch+=len(jobs)
        for row in dispatch:
            j=row['job'];need(row['owner_epoch']==epoch and j['job_id'].startswith('e'+str(epoch)+'-')and
                row['physical_incarnation']==j['worker_incarnation']and row['physical_slot']==j['worker'],'Owner/physical dispatch binding differs')
            need(j['dispatch_epoch']==0,'session-reset lifecycle requires separate evidence tier')
        events=lines(files['owner_events']);workers=lines(files['worker_results']);audits=lines(files['policy_audit'])
        installs=[e for e in events if e['kind']=='canonical_install'];receipts=[e for e in events if e['kind']=='validated_full_receipt']
        result=classify_owner(jobs=jobs,installs=installs,receipts=receipts,workers=workers,audits=audits,
            facts=facts,initials=owner_starts[epoch],source_frames={sid:s['frames']for sid,s in sources.items()},audio_float32_hash=added,
            policy_hints=[e for e in events if e['kind']in('known_invalid_C_skip_hint','policy_C_entry_skip_hint','input_or_coverage_reason_observed_without_C_entry_skip')])
        counts.update(result['counts'])
        for row in result['jobs']:
            row=dict(row,owner_epoch=epoch);rows.append(row)
            if row['actual_same_original_job_selected_after_reconfirmation']:
                jid=row['job_id'];byj={j['job_id']:j for j in jobs}
                own=next(e for e in installs if e['canonical_install_order']['sequence']==row['own_input_later_confirm_order'])
                selected=next(e for e in installs if e['job_id']==jid)
                fact_by={f['sequence']:f for f in facts}
                witnesses.append(dict(metadata=row,complete_original_frozen_job=byj[jid],
                    actual_ancestor_refutation_facts=[fact_by[w['journal_sequence']]for w in row['ancestor_refutations']],
                    actual_own_input_confirmation_fact=fact_by[own['receipt']['sequence']],
                    actual_same_original_job_selected_fact=fact_by[selected['receipt']['sequence']],
                    original_worker_messages=[w for w in workers if w.get('event',{}).get('job_id')==jid]))
    need(all_dispatch==read(root/'JOB_ACCOUNTING.json')['dispatches']==counts['all_dispatched_jobs'],'all dispatch accounting not conserved')
    return dict(cell_id=cell['cell_id'],source_id=source['source_id'],speaker_id=source['speaker_id'],condition=cell['condition'],repeat=cell['repeat'],
        status='PASS_COMPLETE_ALL_DISPATCH_LINEAGE_STATE_AND_ORDER_BINDINGS',counts=dict(counts),jobs=rows,
        raw_root=str(root),positive_witnesses=witnesses),paths

def main():
    parser=argparse.ArgumentParser()
    for name in('manifest','config','out'):parser.add_argument('--'+name,required=True)
    a=parser.parse_args();root=Path(__file__).resolve().parent;cfg=read(a.config)
    own=verify_source(root,a.manifest,cfg['source_commit']);runtime=verify_source(cfg['runtime']['source_root'],cfg['runtime']['source_manifest'],NN)
    need(runtime==cfg['runtime'],'wrong actual frozen NN parser')
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU-only CUDA visibility required')
    out=Path(a.out).resolve();need(out.is_relative_to(B)and str(out)==cfg['raw_result_location'],'unfrozen/wrong result disk')
    out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(executable=sys.executable,python=sys.version,platform=platform.platform(),
        hostname=platform.node(),CUDA_VISIBLE_DEVICES='',neural_imports='forbidden',source=own,runtime_parser=runtime,model_calls=0,GPU_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=own['source_commit'],frozen_config=str(out/'CONFIG.json'),
        frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),
        declared_old_bank_trials=80,new_bank_scope=cfg['new_bank_scope']))
    sys.meta_path.insert(0,NoNeural())
    try:
        for p in root.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
        with (out/'CONTROLS.log').open('x',encoding='utf8')as stream:
            controls=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_lineage'))
        need(controls.wasSuccessful()and not controls.skipped,'constructive controls failed')
        sys.path.insert(0,runtime['source_root']);from resilience_storage import scan
        results=[];paths=[Path(a.config),Path(a.manifest),Path(runtime['source_manifest'])];count=Counter();by_condition=defaultdict(Counter)
        for campaign in cfg['campaigns']:
            plan_path=Path(campaign['plan']['path']);summary_path=Path(campaign['summary']['path'])
            need(sha(plan_path)==campaign['plan']['sha256']and sha(summary_path)==campaign['summary']['sha256'],'complete campaign inputs changed')
            plan=read(plan_path);summary=read(summary_path);paths.extend((plan_path,summary_path))
            need(plan['actual_NN']['source_commit']==NN and plan['expected_trials']==campaign['expected_trials'],'wrong complete campaign/source')
            need(summary['completed_trials']==summary['planned_trials']==campaign['expected_trials']and not summary['failed_attempts'],'partial campaign cannot be recounted as complete')
            need(len(plan['cells'])==campaign['expected_trials'],'planned matrix incomplete')
            for cell in plan['cells']:
                value,used=audit_cell(cell,runtime,scan);paths.extend(used);count.update(value['counts']);by_condition[value['condition']].update(value['counts'])
                target=out/'cells';target.mkdir(exist_ok=True)
                put(target/(cell['cell_id']+'.json'),value);results.append({k:v for k,v in value.items()if k not in('jobs','positive_witnesses')})
        need(len(results)==cfg['expected_trials']and len({r['cell_id']for r in results})==len(results),'complete run denominator differs')
        manifest=inventory(paths);put(out/'INPUT_MANIFEST.json',manifest)
        need(inventory(paths)==manifest,'raw evidence changed during read-only recount')
        verify_source(root,a.manifest,own['source_commit']);verify_source(runtime['source_root'],runtime['source_manifest'],NN)
        loaded=[k for k in sys.modules if k.split('.')[0]in('torch','transformers','peft','librosa','whisper','simul_whisper')]
        need(not loaded,'neural module loaded')
        summary=dict(status='PASS_COMPLETE_OLD80_LINEAGE_RECOUNT_NEW_BANK_PENDING'if cfg['new_bank_scope']['status']=='PENDING_NOT_RUN'else'PASS_COMPLETE_DECLARED_LINEAGE_RECOUNT',
            source_commit=own['source_commit'],actual_NN_source_commit=NN,completed_trials=len(results),counts=dict(count),
            conditions={k:dict(v)for k,v in by_condition.items()},cells=results,new_bank_scope=cfg['new_bank_scope'],
            controls=controls.testsRun,model_calls=0,GPU_calls=0,neural_modules_loaded=[],
            input_manifest=dict(path=str(out/'INPUT_MANIFEST.json'),sha256=sha(out/'INPUT_MANIFEST.json')),
            interpretation='Whole recorded graph, actual installed same-frontier full cuts, and actual same-original-job survival/use. Independent forecast-change axis. No natural reconvergence asserted unless a temporal witness exists; no counterfactual service credit or saved GPU time.')
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json'),
            positive_cases_required=False,all_zero_results_retained=True,model_calls=0,GPU_calls=0))
        print(json.dumps({k:v for k,v in summary.items()if k not in('cells','conditions')},indent=2));return 0
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_LINEAGE_RECOUNT_PRESERVED',failure=traceback.format_exc(),model_calls=0,GPU_calls=0));raise

if __name__=='__main__':raise SystemExit(main())
