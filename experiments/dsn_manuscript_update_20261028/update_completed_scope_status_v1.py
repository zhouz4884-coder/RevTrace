from pathlib import Path
import json,datetime
R=Path(__file__).resolve().parents[2];F=Path(__file__).resolve().parent
p=F/'ACTIVE_STATE.json';v=json.loads(p.read_text());v.update(
 updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 phase='CORE36_JOINT24_NATIVE14_MIDPOINT12_COMPLETE_STAGE_PROFILE_LOCAL_PREPARATION',
 paper_status='Protected old revision retained. Three new technical-section drafts exist but main/PDF remain old baseline until full rewrite and final research decision.',
 midpoint12=dict(status='COMPLETE_EXECUTION_AND_RECOUNT_STRONG_WITNESS_NOT_ESTABLISHED_STOP',execution_cells=12,all_D2_failed=True,all_C8_passed=True,same_task_attribution=True,
 analysis_gate_sha256='016e4d4342e9b37217dc4e4503440758bbab97213e6a7974f456e1d5a1fc415c',joint_D99=[2.196642,2.298685,2.227745],joint_compatible_timely_losses=[0,0,0],stop='No10/11 or further repetitions'),
 native_application_status='COMPLETE14 original native cells and primary/feedback/ready/energy. Every formal arm has CER16/182 and equivalent full Canonical history. Strong two-replica seq18.5s credit, drop12.5s, joint17s per66.42975s offered/arm; no formal D2/C8 whole-run pass. Stage profile is a new conditional study, not an unfinished original scope.',
 next_design_decision='New bounded native-stage profiling in local preparation only. Candidate input validity can hold even if predicted final feedback is withdrawn. Check full ordered beam, open-stage state, same-call A/C/H and same-input controls before any handoff implementation. Strong baseline includes ASR early display; fixed two-stage throughput not presumed superior.')
p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
q=R/'experiments/LATEST_RESEARCH.json';w=json.loads(q.read_text());w.update(status=v['phase'],scope='All72 new GPU cells (36 service +24 joint +12 midpoint) plus14 native cells complete with bounded source/analysis/evidence. Midpoint strong-witness negative STOP. New stage-profile preparation responds to actual exact-input readiness, has no new GPU/results yet. Full manuscript rewrite/compile pending final bounded design decision; original110+16 remain unchanged.')
q.write_text(json.dumps(w,indent=2)+'\n',encoding='utf8')
