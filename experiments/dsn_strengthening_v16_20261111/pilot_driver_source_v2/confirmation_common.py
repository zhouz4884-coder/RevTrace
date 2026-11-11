"""Pure-stdlib source/receipt and per-speaker ABBA contracts."""
from __future__ import annotations
import hashlib,json,os,pathlib,random,subprocess,sys
RUNTIME='de0936b2e30179d63aeef6e235cd1af685578c58'
PARENT_RUNTIME='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
NN4F=RUNTIME  # Historical variable name; value is actual newly frozen runtime.
SUPPORT='a13fa0a335529dc188f7e738877a3acd027ce4a7'
MAIN_ARMS=('conservative','dependency_versioned','ready_only','fullcall','uir')
AUXILIARY_ARMS=('safe_versioned',)
REFERENCE_SUCCESS='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'
BOUND_REFERENCE_SUCCESS='PASS_PREDECLARED_SOURCE_SUBSET_OF_MEASURED_REFERENCE'
SPLIT_DIRECTORY='StreamCorrect/aishell1_testset'
SPLIT_NAMESPACE='AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96'
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
SEED=20261111
class GateError(RuntimeError):pass
def need(ok,text):
    if not ok:raise GateError(text)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def put(path,value,replace=False):
    with pathlib.Path(path).open('w' if replace else 'x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def disk(path):
    p=pathlib.Path(path);need(p.is_absolute() and p.resolve().is_relative_to(B.resolve()),'new output outside designated8TB');return p
def verify_source(root,manifest,expected=None):
    root=pathlib.Path(root).resolve(strict=True);manifest=pathlib.Path(manifest).resolve(strict=True);m=read(manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    commit=m.get('source_commit',m.get('code_commit'))
    need(isinstance(commit,str) and len(commit)==40 and (expected is None or commit==expected),'wrong full source commit')
    need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root and git('rev-parse','HEAD')==commit and git('cat-file','-t',commit)=='commit','source identity unresolved')
    need(git('config','--get','core.autocrlf')=='false' and not git('status','--porcelain','--untracked-files=all'),'source dirty or line conversion enabled')
    need(set(git('ls-files','-z').split('\0'))-{''}=={r['path'] for r in m['files']},'complete source manifest mismatch')
    for r in m['files']:
        p=root/r['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root) and p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'source bytes differ')
    return dict(source_commit=commit,source_root=str(root),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),complete_files=len(m['files']),clean=True)
def selected_sources(receipt,expected):
    need(receipt['status']=='PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE','strict test selection not complete')
    sources=receipt['sources'];need(len(sources)==expected and expected>0,'frozen source count differs')
    need(len({s['speaker_id'] for s in sources})==len({s['source_id'] for s in sources})==expected,'one independent utterance per distinct speaker required')
    for s in sources:
        need(s['original_split']==SPLIT_NAMESPACE and s['split_directory']==SPLIT_DIRECTORY,'mixed/unversioned/non-test split forbidden')
        need(s['archive_member']['path']==SPLIT_DIRECTORY+'/'+s['source_id']+'.wav','source archive membership differs')
        h=s['header'];need(h['sample_rate']==16000 and h['channels']==1 and h['sample_width']==2,'original PCM contract changed')
        need(96000<=s['frames']<=320000 and abs(s['duration']-s['frames']/16000)<1e-10,'original6–20s source duration/header changed')
    need(receipt['model_calls']==0,'selection receipt must precede neural outcomes')
    return sources
def phase_arms(include_auxiliary=True):
    return MAIN_ARMS+AUXILIARY_ARMS if include_auxiliary else MAIN_ARMS
def validate_phase_selection(receipt,phase,sources):
    if phase=='pilot_existing':
        need(len(sources)==2 and receipt.get('selection_use')=='existing_bank_pilot_reuse','pilot must reuse two metadata-frozen existing-bank sources')
    elif phase=='existing8':need(len(sources)==8,'existing bank must retain eight speakers')
    elif phase=='new_confirmatory':
        need(receipt.get('selection_use')=='new_speaker_confirmatory','reused bank cannot be relabelled as new independent speakers')
        evidence=receipt['historical_speaker_disjointness'];need(sha(evidence['path'])==evidence['sha256'],'historical speaker census changed')
        gate=read(evidence['path']);need(gate['all_selected_speakers_previously_unused'] is True and set(gate['selected_speaker_ids'])=={s['speaker_id'] for s in sources},'new-speaker historical census did not pass')
    else:raise GateError('unknown cohort phase')
def prespecified_reference_subset(parent_selection,subset_selection):
    parent_sources=selected_sources(parent_selection,4);sources=selected_sources(subset_selection,2)
    bank_ref=parent_selection['parent_bank_receipt']
    need(sha(bank_ref['path'])==bank_ref['sha256'],'existing metadata bank changed')
    bank=selected_sources(read(bank_ref['path']),8)
    need(parent_sources==sorted(bank,key=lambda s:(s['speaker_id'],s['source_id']))[:4],'measured reference scope is not metadata-first four')
    need(sources==parent_sources[:2] and subset_selection.get('selection_use')=='existing_bank_pilot_reuse','subset is not metadata-first two')
    need(subset_selection['parent_bank_receipt']['sha256']==bank_ref['sha256'],'pilot and reference parent banks differ')
    return parent_sources,sources
def abba_blocks(sources,include_auxiliary=True):
    rng=random.Random(SEED);ordered=sorted(sources,key=lambda s:(s['speaker_id'],s['source_id']));rng.shuffle(ordered);orders={}
    for s in ordered:
        order=list(phase_arms(include_auxiliary));rng.shuffle(order);orders[s['speaker_id']]=order
    blocks=[]
    for repeat in (0,1):
        for s in (ordered if repeat==0 else list(reversed(ordered))):
            order=orders[s['speaker_id']] if repeat==0 else orders[s['speaker_id']][::-1]
            blocks.append(dict(source=s,repeat=repeat,primary_gpu=repeat,strategies=list(order)))
    return blocks,orders
def validate_matrix(cells,sources,include_auxiliary=True):
    arms=phase_arms(include_auxiliary);n=len(arms)
    need(len(cells)==2*n*len(sources) and len({c['cell_id'] for c in cells})==len(cells),'complete phase-specific matrix required')
    for s in sources:
        own=[c for c in cells if c['source_id']==s['source_id']]
        r0=sorted((c for c in own if c['repeat']==0),key=lambda c:c['position']);r1=sorted((c for c in own if c['repeat']==1),key=lambda c:c['position'])
        need(len(r0)==len(r1)==n and {c['strategy'] for c in r0}==set(arms) and {c['strategy'] for c in r1}==set(arms),'speaker repeat policy matrix changed')
        need([c['strategy'] for c in r1]==[c['strategy'] for c in r0][::-1],'per-speaker ABBA did not reverse')
        need(all(c['primary_gpu']==0 for c in r0) and all(c['primary_gpu']==1 for c in r1),'same-repeat GPU role or repeat rotation changed')
    blocks,_=abba_blocks(sources,include_auxiliary)
    expected=[(b['source']['source_id'],a,b['repeat'],b['primary_gpu']) for b in blocks for a in b['strategies']]
    actual=[(c['source_id'],c['strategy'],c['repeat'],c['primary_gpu']) for c in sorted(cells,key=lambda c:c['position'])]
    need(actual==expected and [c['position'] for c in cells]==list(range(len(cells))),'metadata-only seeded plan order differs')
def reference_binding(path,selection_path,sources,generator_commit=None):
    ref=read(path);need(ref['status'] in (REFERENCE_SUCCESS,BOUND_REFERENCE_SUCCESS) and ref['actual_NN_source_commit']==NN4F,'original/restore reference incomplete or wrong source')
    if generator_commit is not None:need(ref['generator_source_commit']==generator_commit,'reference generator actual source differs')
    need(ref['selection_receipt']['sha256']==sha(selection_path),'reference selection changed')
    need(set(ref['source_ids'])=={s['source_id'] for s in sources} and set(ref['speaker_ids'])=={s['speaker_id'] for s in sources},'reference did not cover complete fixed selection')
    need(ref['sources']==sources,'reference complete frozen source objects changed')
    for key in ('reference_details','reference_gate','genesis'):
        r=ref[key];need(sha(r['path'])==r['sha256'],'terminal reference bytes differ: '+key)
        if 'bytes' in r:need(pathlib.Path(r['path']).stat().st_size==r['bytes'],'reference length differs')
    gate=read(ref['reference_gate']['path']);need(gate['status']==ref['status'] and gate['actual_NN_source_commit']==RUNTIME and gate['generator_source_commit']==ref['generator_source_commit'] and gate['all_original_full_state_C_IDs_equal'] is True,'reference gate failed or has wrong execution identity')
    expected=sum((s['frames']+7999)//8000 for s in sources)
    need(gate['expected_original_steps']==expected and gate['expected_sources']==gate['completed_sources']==len(sources),'reference terminal scope incomplete')
    need(ref['reference_only'] is True and ref['actual_serving_runs']==0 and ref['original_continuous_no_between_step_restore'] is True and ref['restored_repeats_per_edge']==2,'reference execution/serving scope changed')
    need(ref['reference_details']['expected_steps']==expected,'reference step scope incomplete')
    details=read(ref['reference_details']['path']);need(len(details)==expected and len({(x['source_id'],x['end']) for x in details})==expected,'reference DETAILS missing/duplicate')
    by={s['source_id']:s for s in sources}
    for row in details:
        need(row['source_id'] in by,'unknown reference source')
        for key in ('original_full_start_cut','original_full_cut'):
            state=row[key];need(state['contract']['stage_execution']['source_commit']==RUNTIME,'old states cannot be relabelled as new references')
            need(state['contract']['source_sha']==by[row['source_id']]['audio_sha256'],'reference audio identity changed')
    genesis=read(ref['genesis']['path'])
    for sid,s in by.items():
        rows=sorted((r for r in details if r['source_id']==sid),key=lambda r:r['end'])
        need([r['end'] for r in rows]==list(range(8000,s['frames'],8000))+[s['frames']],'reference cadence/EOS changed')
        previous=genesis[sid]
        need(previous['frontier']==0,'reference genesis frontier changed')
        for row in rows:
            need(canonical(row['original_full_start_cut'])==canonical(previous),'complete reference chain differs')
            need(row['original_full_cut']['frontier']==row['end'] and row['continuous_original_no_between_step_restore'] is True,'reference continuous path/end binding differs')
            previous=row['original_full_cut']
    if ref['status']==BOUND_REFERENCE_SUCCESS:
        need(ref.get('reference_origin')=='prespecified_exact_source_subset' and gate.get('new_neural_verification') is False and ref.get('new_neural_verification') is False and ref.get('new_model_calls')==gate.get('new_model_calls')==0,'derived reference mislabeled as new neural verification')
        parent=ref['measured_parent_reference'];parent_selection=ref['measured_parent_selection']
        need(gate['measured_parent_reference']==parent and ref['reference_cost_source']['parent_reference_receipt']==parent,'derived reference parent/cost provenance disagrees')
        need(sha(parent['path'])==parent['sha256'] and sha(parent_selection['path'])==parent_selection['sha256'],'measured parent reference binding changed')
        parent_receipt=read(parent['path']);need(parent_receipt['status']==REFERENCE_SUCCESS and parent_receipt.get('reference_origin','measured_continuous_and_restored')=='measured_continuous_and_restored','subset requires a directly measured full parent reference')
        parent_sources,checked_subset=prespecified_reference_subset(read(parent_selection['path']),read(selection_path))
        need(checked_subset==sources,'subset complete frozen source objects changed')
        parent_ref=reference_binding(parent['path'],parent_selection['path'],parent_sources,generator_commit)
        need(sources==parent_sources[:2],'reference subset is not the metadata-prespecified first two')
        parent_rows=read(parent_ref['reference_details']['path']);wanted={s['source_id'] for s in sources}
        need(canonical(details)==canonical([r for r in parent_rows if r['source_id'] in wanted]),'derived reference changed an original parent row')
        parent_genesis=read(parent_ref['genesis']['path']);need(canonical(genesis)==canonical({s['source_id']:parent_genesis[s['source_id']] for s in sources}),'derived reference changed parent genesis')
    return ref
def validate_prelaunch(pre,plan_path,driver,base):
    need(pre['plan_sha256']==sha(plan_path),'frozen plan differs')
    for key,identity in [('root_noarg_preflight',base),('driver_explicit_preflight',driver)]:
        need(sha(pre[key])==pre[key+'_sha256'],'source receipt bytes changed: '+key)
        gate=read(pre[key]);need(gate['gate']=='SOURCE_IDENTITY_PASS','source receipt failed: '+key)
        need(gate['code_commit']==identity['source_commit'] and gate['manifest_sha256']==identity['source_manifest_sha256'],'source receipt wrong identity: '+key)
        if key=='root_noarg_preflight':need(pathlib.Path(gate['setup_pointer'].replace('\\','/')).name=='CURRENT.json' and 'setup_pointer_sha256' in gate,'current no-argument receipt required')
    need(pre['exclusive_GPU_window_authorized_by_root'] is True,'Root owned exclusive window missing')
def child_env():
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
    env.pop('PYTORCH_ALLOC_CONF',None);env.pop('CUDA_VISIBLE_DEVICES',None);return env

