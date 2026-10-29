"""Update living research pointers, never frozen execution records."""
from pathlib import Path
import json,datetime
R=Path(__file__).resolve().parents[2];F=Path(__file__).resolve().parent
p=F/'ACTIVE_STATE.json';v=json.loads(p.read_text())
v.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         phase='NATIVE14_AND_RXK_QUALITY_COMPLETE_MIDPOINT12_RUNNING_STAGE_PROFILE_LOCAL_PREPARATION',
         native_application_status='14 actual native cells complete; all formal Canonical histories equal; original primary all-offered metrics recounted. Current500ms two-session point failsD2 in all12, strong two-full-replica sequential credit18.5s > joint17s > drop12.5s per66.42975s offered/arm. Native adaptation validates retention, not deployed SLO.',
         midpoint12=dict(status='ACTUALLY_RUNNING_FROZEN12',pid=1723962,start_ticks='501206749',actual_source_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',plan_sha256='fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84',result_pending=True),
         next_design_decision='Only locally preparing a bounded native-stage profiling study:244 nonempty controller-ready exact-input pairs observed. No handoff implementation or performance benefit claimed; original selector and full state stay binding.',
         RxK_quality='Completed all24/96 exact-F content support. All96 causal following rows raw/norm match later same-F full Canonical and have real unaltered inputs; first-credit untouched; general24 has real content disagreements, unknown0.')
p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
q=R/'experiments/LATEST_RESEARCH.json';w=json.loads(q.read_text());w.update(status=v['phase'],scope='Core36+joint24+native14 and all respective primary/quality analyses complete. Unique12point actually running on unchanged frozen f0. Local native-stage profile preparation is conditional and has no new GPU/results yet. Full revised body pending final bounded research decisions. Earlier110+16 remain unchanged.')
q.write_text(json.dumps(w,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':v['phase']}))
