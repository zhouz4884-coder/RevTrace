"""Metadata-only, outcome-blind composition confirmation plan and crop selection."""
from pathlib import Path
import hashlib,json,math,platform,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PARENT=ROOT/'experiments/context_recovery_20261028/publication_update_v2/context_holdout_freeze_v1/MANIFEST.json'
REFERENCE=HERE/'REFERENCE_METADATA.json'
DISK='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
DATA=DISK+'/datasets/revtrace/composition_confirmation_20261028/utterance_boundary_v1'
RESULT=DISK+'/results/revtrace/physical_retirement_20261028/composition_confirmation_v1'
FINAL=DISK+'/results/revtrace/physical_retirement_20261028/confirmation_v2'
SOURCE=DISK+'/projects/revtrace_physical_retirement_20261028/source_v2'
SOURCE_MANIFEST=DISK+'/projects/revtrace_physical_retirement_20261028/SOURCE_v2.json'
CODE_COMMIT='1d8c30804a945570429d85d934b3bfcba6171a43'
SOURCE_MANIFEST_SHA256='5b1527bdcb20e165bc69f5002e3092a38b8ec773606828936c211ed595781f63'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(name,value):(HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def candidates(session):
    result=[];utterances=session['utterances']
    for start,u in enumerate(utterances):
        for end,v in enumerate(utterances[start:],start):
            length=v['end']-u['start']
            if 25*16000<=length<=35*16000:
                result.append(dict(first=start,last=end,start_sample=u['start'],end_sample=v['end'],duration=length/16000))
    return result

def main():
    parent=read(PARENT);reference=read(REFERENCE)
    if sha(PARENT)!=reference['parent_manifest_sha256']:raise ValueError('parent manifest identity')
    if reference['history_registry_sha256']!=parent['history_registry_sha256']:raise ValueError('history registry identity')
    texts={r['id']:r for r in reference['utterances']};all_ids=set();all_hashes=set();speakers=[];chosen=[];candidate_counts=[]
    for session in parent['sessions']:
        if ' '.join(texts[u['id']]['text'] for u in session['utterances'])!=session['reference']:raise ValueError('exact full reference reconstruction')
        for u in session['utterances']:
            if u['id'] in all_ids:raise ValueError('reused parent utterance')
            all_ids.add(u['id']);all_hashes.add(u['source_sha256'])
        pool=candidates(session);candidate_counts.append(dict(parent=session['source_id'],candidates=len(pool)))
        if session['speaker'] in speakers:continue
        if not pool:raise ValueError('no legal duration route for first parent of speaker; do not choose a different speaker after outcomes')
        speakers.append(session['speaker'])
        best=min(pool,key=lambda c:(abs(c['duration']-30.),c['first'],c['last']))
        units=session['utterances'][best['first']:best['last']+1]
        sid='composition-'+session['speaker']+'-'+session['chapter']+'-'+units[0]['id'].rsplit('-',1)[1]+'-'+units[-1]['id'].rsplit('-',1)[1]
        chosen.append(dict(source_id=sid,speaker=session['speaker'],chapter=session['chapter'],language='English',
          intended_path=DATA+'/'+sid+'.wav',duration=best['duration'],sample_rate=16000,
          parent_source_id=session['source_id'],parent_path=session['path'],parent_file_sha256=session['file_sha256'],
          parent_audio_sha256=session['audio_sha256'],parent_start_sample=best['start_sample'],parent_end_sample=best['end_sample'],
          reference=' '.join(texts[u['id']]['text'] for u in units),
          utterances=[{**u,'relative_start':u['start']-best['start_sample'],'relative_end':u['end']-best['start_sample'],
             'text':texts[u['id']]['text'],'original_encoded_path':texts[u['id']]['path'],
             'parquet_path':texts[u['id']]['parquet_path'],'declared_parquet_sha256':texts[u['id']]['declared_parquet_sha256']} for u in units],
          grouping='complete contiguous utterances from the first frozen session per speaker; original 0.1s separators; no leading/trailing padding',
          ASR_evaluated=False,materialization_status='PENDING_CPU_BYTE_VERIFICATION'))
    historical_ids=set(map(str,reference['historical_source_ids']));historical_speakers=set(map(str,reference['historical_speaker_ids']))
    selected_ids={u['id'] for s in chosen for u in s['utterances']}
    provenance=dict(parent_manifest=str(PARENT.relative_to(ROOT)),parent_manifest_sha256=sha(PARENT),
      parent_sessions=len(parent['sessions']),parent_speakers=parent['unique_speakers'],parent_unique_utterances=len(all_ids),
      parent_reported_ASR_model_calls=parent['ASR_model_calls'],
      zero_usage_claim_boundary='parent freeze and retained context records report zero ASR; bounded retrieval performs zero ASR; not an exhaustive attestation of unpublished external work',
      reference_metadata_sha256=sha(REFERENCE),exact_utterance_references=len(texts),
      reference_whole_parent_reconstruction='48/48 exact equality',
      history_registry_sha256=reference['history_registry_sha256'],historical_source_ids=len(historical_ids),historical_speaker_ids=len(historical_speakers),
      selected_utterance_overlap=sorted(selected_ids&historical_ids),selected_speaker_overlap=sorted(set(speakers)&historical_speakers),
      parent_utterance_overlap=sorted(all_ids&historical_ids),parent_speaker_overlap=sorted({s['speaker'] for s in parent['sessions']}&historical_speakers),
      candidate_segments=sum(row['candidates'] for row in candidate_counts),all_parent_sessions_have_route=all(row['candidates'] for row in candidate_counts),
      selected_sources=len(chosen),selected_speakers=len(speakers),selected_utterances=len(selected_ids),
      selected_unique_audio_seconds=sum(s['duration'] for s in chosen),selected_duration_range=[min(s['duration'] for s in chosen),max(s['duration'] for s in chosen)],
      candidate_counts=candidate_counts,new_ASR_calls=0,model_pretraining_exposure='UNKNOWN_NOT_CLAIMED')
    overlaps=[]
    for pool in ['development','heldout']:
        path=ROOT/f'experiments/ces_v6_abcd_20261025/evidence/inputs/{pool}_manifest.json'
        rows=read(path)['sessions'];ids={r['source_id'] for r in rows};sp={str(r.get('speaker',r.get('speaker_id',r['source_id'].split('-')[0]))) for r in rows}
        overlaps.append(dict(pool=pool,manifest=str(path.relative_to(ROOT)),sha256=sha(path),
          parent_utterance_ID_overlap=sorted(all_ids&ids),speaker_overlap=sorted(set(speakers)&sp)))
    provenance['V6_current_local_pool_overlap']=overlaps
    if any(provenance[key] for key in ['selected_utterance_overlap','selected_speaker_overlap','parent_utterance_overlap','parent_speaker_overlap']):raise ValueError('historical overlap')
    if any(row['speaker_overlap'] for row in overlaps):raise ValueError('current V6 speaker overlap')
    cohorts=[]
    for index in range(3):
        sessions=[s for i,s in enumerate(chosen) if i%3==index]
        cohorts.append(dict(cohort='ABC'[index],source_ids=[s['source_id'] for s in sessions],
          speakers=[s['speaker'] for s in sessions],audio_seconds=sum(s['duration'] for s in sessions),
          duration_range=[min(s['duration'] for s in sessions),max(s['duration'] for s in sessions)],
          sessions=8,selection='round-robin first-parent speaker order; independent source clusters across cohorts'))
    arms=[dict(arm='R0_S0',method='dgft_original',retain='no',confirmation_consumer='checked_snapshot'),
          dict(arm='R0_S1',method='dgft_original',retain='no',confirmation_consumer='two_lane'),
          dict(arm='R1_S0',method='dgft_original',retain='yes',confirmation_consumer='checked_snapshot'),
          dict(arm='R1_S1',method='dgft_original',retain='yes',confirmation_consumer='two_lane'),
          dict(arm='STANDARD_FULL',method='standard_fair',retain='yes',confirmation_consumer='two_lane',role='alternative implementation positive control')]
    models=[dict(adapter='qwen',model=DISK+'/models/Qwen3-ASR-1.7B'),
            dict(adapter='whisper',model=DISK+'/models/whisper-base.en',whisper_context_policy='reserve-generation-tail-v1')]
    cells=[]
    # Independent source replication is three disjoint speaker cohorts. Extra
    # A repeats are predeclared measurement-noise controls, not new sources.
    for phase,rho,arrivals,groups,repeats in [('primary',1,['sync','staggered'],cohorts,[0]),
      ('paired_jitter',1,['sync','staggered'],cohorts[:1],[1]),
      ('coarse',3,['sync'],cohorts,[0])]:
        for model_index,model in enumerate(models):
            for arrival in arrivals:
                for cohort_index,cohort in enumerate(groups):
                    for repeat in repeats:
                        rotation=(model_index+cohort_index+repeat+(arrival=='staggered'))%len(arms)
                        order=arms[rotation:]+arms[:rotation]
                        if (cohort_index+model_index+repeat)%2:order=list(reversed(order))
                        for arm in order:
                            cell_id=f'{phase}-{model["adapter"]}-rho{rho}-{arrival}-C{cohort["cohort"]}-{arm["arm"]}-r{repeat}'
                            cells.append(dict(cell_id=cell_id,phase=phase,**model,**arm,rho=rho,arrival=arrival,
                              stagger_step_seconds=.25,sessions=8,cohort=cohort['cohort'],repeat=repeat,
                              manifest=RESULT+'/inputs/COHORT_'+cohort['cohort']+'.json',
                              out=FINAL+'/'+cell_id,policy='row_complete',fixture=None,
                              source=SOURCE,source_manifest=SOURCE_MANIFEST,
                              display_slo_seconds=2.,commit_slo_seconds=8.,microbatch=16,max_new_tokens=256,
                              proposal_dtype='float16',authority_dtype='float32',proposal_GPU=0,authority_GPU=1,
                              service_timeout_seconds=240.,wall_timeout_seconds=420.,status='NOT_STARTED'))
    # Keep every matched five-arm block intact, alternate the two model blocks,
    # and reverse arrival order across source cohorts. No outcome is an input.
    blocked={}
    for cell in cells:
        key=(cell['phase'],cell['rho'],cell['cohort'],cell['arrival'],cell['repeat'])
        blocked.setdefault(key,{}).setdefault(cell['adapter'],[]).append(cell)
    phase_order={'primary':0,'paired_jitter':1,'coarse':2}
    keys=sorted(blocked,key=lambda k:(phase_order[k[0]],k[2],
      (k[3]=='staggered') if ('ABC'.index(k[2])+k[4])%2==0 else (k[3]=='sync'),k[4]))
    cells=[]
    for index,key in enumerate(keys):
        adapters=['qwen','whisper'] if index%2==0 else ['whisper','qwen']
        for adapter in adapters:
            group={c['arm']:c for c in blocked[key][adapter]}
            # Repeated five-block Latin cycles put every arm at every position.
            # Reversing an entire second cycle also balances order direction.
            ordered=[arm['arm'] for arm in arms]
            rotation=index%len(arms)
            ordered=ordered[rotation:]+ordered[:rotation]
            if (index//len(arms))%2:ordered=list(reversed(ordered))
            cells.extend(group[arm] for arm in ordered)
    for index,cell in enumerate(cells):
        cell['run_order_index']=index
        cell['output']=cell['out']
        cell['paired_block']=f'{cell["phase"]}-rho{cell["rho"]}-{cell["arrival"]}-C{cell["cohort"]}-r{cell["repeat"]}-{cell["adapter"]}'
        cell['manifest_sha256']=sha(HERE/'materialized'/('COHORT_'+cell['cohort']+'.json'))
        cell['argv']=[DISK+'/envs/revbatch-cu128/bin/python','-B',SOURCE+'/retirement_service.py',
          '--out',cell['out'],'--source-manifest',SOURCE_MANIFEST,'--manifest',cell['manifest'],
          '--model',cell['model'],'--adapter',cell['adapter'],'--policy','row_complete','--method',cell['method'],
          '--rho',str(cell['rho']),'--sessions','8','--arrival',cell['arrival'],'--repeat',str(cell['repeat']),
          '--retain',cell['retain'],'--confirmation-consumer',cell['confirmation_consumer'],
          '--watchdog-seconds','2.0','--service-timeout','240.0','--wall-timeout','420.0']
    costs=dict(cells=len(cells),cells_by_phase={phase:sum(c['phase']==phase for c in cells) for phase in ['primary','paired_jitter','coarse']},
      one_cell_GPU_boards=2,maximum_serial_cell_wall_seconds=sum(c['wall_timeout_seconds'] for c in cells),
      maximum_reserved_GPU_seconds=2*sum(c['wall_timeout_seconds'] for c in cells),
      offered_audio_seconds_all_cells=sum(next(co['audio_seconds'] for co in cohorts if co['cohort']==c['cohort']) for c in cells),
      expected_canonical_complete_rows=sum(sum(math.ceil(s['duration']/(2*c['rho'])) for s in chosen if s['source_id'] in next(co['source_ids'] for co in cohorts if co['cohort']==c['cohort'])) for c in cells),
      maximum_private_fine_rows=sum(sum(math.ceil(s['duration']/2) for s in chosen if s['source_id'] in next(co['source_ids'] for co in cohorts if co['cohort']==c['cohort'])) for c in cells),
      expected_wall_time='not predicted from a new holdout run; bounded upper budget only, includes failure timeouts',
      new_ASR_calls_already_run=0)
    plan=dict(experiment_id='REVTRACE-UNIFIED-COMPOSITION-CONFIRMATION-20261028',status='FROZEN_FULL_RUNTIME_V2_AND_CPU_ASSETS_NO_ASR_YET',
      code_commit=CODE_COMMIT,source_manifest_sha256=SOURCE_MANIFEST_SHA256,
      parent_manifest_sha256=sha(PARENT),selection_rule='first source per speaker in frozen parent order; contiguous complete-utterance interval 25..35s minimizing abs(duration-30), ties earliest start then end',
      cohorts=cohorts,arms=arms,models=models,cells=cells,costs=costs,
      execution_source=SOURCE,execution_source_manifest=SOURCE_MANIFEST,
      required_execution_commit=CODE_COMMIT,
      run_order='outcome-independent complete five-arm Latin cycles; opposite second-cycle direction; alternate model order by source/arrival block; reverse arrival order across cohorts; predefined same-input jitter blocks are retained',
      all_cell_output_root=FINAL,
      required_before_ASR=['CPU materialize exact audio/reference and hash all assets','freeze source implementing checked_snapshot with full kernel legal-view audit',
        'old-development inputs confirm finalcarrier and fixed c8 load capacity; never choose loads on confirmation outcomes',
        'freeze complete source commit, environment, commands and input manifests; verify no existing GPU processes'],
      fixed_load_rationale='c16 prior finalcarrier whole-run dual P99 failed; c8 lies between prior c4 bounded pilots and c16 overloaded point, keeps all24 independent speakers in3 matched cohorts. sync vs0.25s stagger isolates arrival geometry; not claimed capacity-guaranteed before development check.',
      continuation_rules='All mandatory design cells run regardless of performance; code/safety blocker stops paired queue with raw failures. Fix gets new source and repeated complete affected blocks. No winner-based source/load trimming.',
      statistics='paired arm contrasts by source and cohort/run; speaker bootstrap with repeat and deadline windows kept inside cluster; N=24 speakers, not cells/windows. Report each cohort and jitter repeat separately.',
      success_scope='observed legal progress retention/withdrawal, actual Consumer stalls, unchanged certified selection requirements, all offered deadlines/debt, energy and task quality; no arbitrary-load zero-rollback guarantee',
      standard_control='full Standard same-effect is a positive alternative implementation; do not demand failure')
    put('SELECTED_STREAMS_PENDING_MATERIALIZATION.json',dict(schema='composition-boundary-crop-selection-v1',
      parent_manifest_sha256=sha(PARENT),sample_rate=16000,selection_rule=plan['selection_rule'],
      dataset_output_root=DATA,manifest_output_root=RESULT+'/inputs',sessions=chosen,ASR_model_calls=0))
    put('DATA_PROVENANCE.json',provenance)
    put('PLAN.json',plan)
    put('EXPECTED_COSTS.json',costs)
    put('CONFIG_TEMPLATES.json',dict(arms=arms,common=dict(policy='row_complete',sessions=8,microbatch=16,max_new_tokens=256,
      result_delivery='row',protocol_kernel=True,kernel_copy_mode='event-cow',capture_model_inputs=True,
      trusted_text_binding=True,display_slo_seconds=2.,commit_slo_seconds=8.,input_WAL=True,canonical_WAL=True,
      selected_Authority='full FP32 canonical generation',physical_exit='disabled for composition isolation'),
      required_new_CLI='retirement_service.py --confirmation-consumer {checked_snapshot,two_lane}; all other declared flags already exist',
      checked_snapshot_contract='reject incompatible newly received tentative views; canonical application clears old tentative state rather than retaining it; same full kernel and legal-view verification'))
    put('BUILD_RECORD.json',dict(experiment_id='REVTRACE-COMPOSITION-METADATA-DESIGN-20261028',
      analysis_script_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(PARENT),reference_metadata_sha256=sha(REFERENCE),
      python=sys.version,platform=platform.platform(),new_model_calls=0,new_audio_assets_written=0,
      outputs=['SELECTED_STREAMS_PENDING_MATERIALIZATION.json','DATA_PROVENANCE.json','PLAN.json','EXPECTED_COSTS.json','CONFIG_TEMPLATES.json'],
      gate='VALID_BOUNDARY_AND_REFERENCE_ROUTE; MATERIALIZATION_AND_EXECUTION_PENDING'))
    print(json.dumps(dict(selected=len(chosen),speakers=len(speakers),duration_range=provenance['selected_duration_range'],
      audio_seconds=provenance['selected_unique_audio_seconds'],cells=len(cells),costs=costs),indent=2))

if __name__=='__main__':main()
