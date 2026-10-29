"""Update living pointers; preserve frozen experiment records and historical runs."""
import json
from datetime import datetime, timezone
from pathlib import Path

T = Path(__file__).resolve().parent
R = T.parents[1]
now = datetime.now(timezone.utc).isoformat()
state_path = T / 'ACTIVE_STATE.json'
state = json.loads(state_path.read_text(encoding='utf8'))
state.update(
    status='CORE_SCOPES_COMPLETE_STAGE_PROFILE_AND_NEURAL_EQ_COMPLETE_ONLINE_HANDOFF_IN_DEVELOPMENT',
    phase='BOUNDED_STAGE_SERVICE_PREPARATION_AND_FULL_MANUSCRIPT_INTEGRATION',
    updated_utc=now,
    current_runtime='99e83a466fee7f1d16830b640cc99e0040d2f147',
    current_runtime_manifest='experiments/dsn_streamcorrect_stage_handoff_20261029/packages/SOURCE_v2.json',
    gpu_current=None,
    gpu_next='Review and freeze source_v3 ready-only stage-handoff paired service development scope. No online handoff service cells exist yet.',
    paper_status='All eight core sections drafted in core_draft.tex; preliminary compiled PDF has9 technical pages plus references. main.tex/main.pdf/CURRENT remain protected old baseline pending final research decision and full release QA.',
    agents={
        'streamcorrect_adapter':'source_v3 service controller and Consumer integration; no GPU launch before root plan/source gate',
        'joint_result_analysis':'independent online pilot and stop/go design review',
        'service_stability':'independent full core draft argument review',
    },
    next_design_decision='Ready-only protected ASR candidate reuse with original C/U, compared with two complete native replicas having identical early ASR visibility and genuine neural warmup. Measure actual receipt/restore cost, hit/fallback, all offered deadlines, content and energy. Stop or independent final-implementation confirmation according to actual headroom.',
)
state['completed_stage_profile'] = {
    'source_commit':'41dea9bb6666e2c7397b394fb1c7a4a58b27888f',
    'gate_sha256':'c6e3a55fda5edcc6f138922d6e78e1f6f80f3794f0ea2a405ef7ae0d28556090',
    'scope':'4 original complete flows plus6 fixed controls;69 full steps,64 non-None neural C calls',
    'mean_A_ms':434.70,'mean_C_ms':268.72,
    'performance_tier':'instrumented sequential stage profile, not online handoff service',
}
state['completed_stage_neural_equivalence'] = {
    'source_commit':'99e83a466fee7f1d16830b640cc99e0040d2f147',
    'gate_sha256':'41221280007d94581a640ec329bf5634ccb6012efbc44ab60fca302c51c6849d',
    'full_steps':69,'candidate_C_U_comparisons':65,
    'predicted_end_different_but_candidate_valid':13,
    'old_native69_fidelity_gate_sha256':'79f9355a41f42660fb16c3f002b3052551a547dbe6dafd89cdb0a0205c8d1411',
    'raw_old_new_hashes_equal':0,
    'explicit_projection':'only added stage_execution contract binding is removed for old-v8 comparison; all old task state/selected C/IDs/text remain exact',
    'actual_online_service_cells':0,
}
state['new_content_endpoint'] = {
    'gate_sha256':'65e763b6b7871a8b92c66d825b3362db6b0ef3f4fa812034f8078895a677aa49',
    'scope':'all14 native cells, CPU-only retrospective, unchanged original first credit',
    'finding':'Joint17.0s frontier credit all first-covered by strict text append; sequential18.5s includes1.5s unchanged text. Joint erases57 introduced LCP character occurrences vs drop22; no audio-to-character alignment claim.',
}
state['new_full_interval_case'] = {
    'scope':'one post-hoc c16 R-only full2s interval, not a paired counterfactual',
    'first_display_s':1.443905769,'compatible_withdrawal_s':1.543663285,
    'return_s':3.719605122,'new_raw_characters':37,
    'finding':'Actually new text is delivered beforeD2 but absent at theD2 read point; the identical whole text later returns.',
}
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
latest_path=R/'experiments/LATEST_RESEARCH.json'
latest=json.loads(latest_path.read_text(encoding='utf8'))
latest.update(date='2026-10-29',status=state['status'],scope='Core36+joint24+midpoint12 and original native14 complete. New stage profile, all69 neural equivalence, independent old-task fidelity, native content endpoints and full2s text case complete. Online ready-only handoff is source_v3 development, with0 serving cells; full core draft exists and final integration/QA remain pending.',updated_utc=now)
latest_path.write_text(json.dumps(latest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
draft=R/'Paper_DSN/revisions/20261028_dsn2027_progress/DRAFT_STATE.json'
d=json.loads(draft.read_text(encoding='utf8'))
d.update(status='FULL_CORE_DRAFT_COMPILED_FINAL_RESEARCH_DECISION_AND_RELEASE_QA_PENDING',entrypoint='core_draft.tex',preliminary_pdf='core_draft.pdf',preliminary_pages=10,preliminary_technical_pages=9,main_and_current='protected old baseline',pending='Final stage service decision; integrate selected actual results; complete all-page PDF/source/citation/font/anonymity QA; make clean release package and update CURRENT.',updated_utc=now)
d['drafts']=[str(p.relative_to(draft.parent)).replace('\\','/') for p in sorted((draft.parent/'sections').glob('*.tex')) if p.name in {'01_progress_introduction.tex','02_contract.tex','03_continuation.tex','04_protocol.tex','05_evaluation_core.tex','05_execution_application.tex','06_progress_related.tex','07_progress_discussion.tex','08_progress_conclusion.tex'}]
draft.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':state['status'],'online_handoff_cells':0,'updated_utc':now}))
