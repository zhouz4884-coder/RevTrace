"""After root actually viewed all12 final images, bind and package this release."""
import json,pathlib,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1]
T=R/'experiments/dsn_manuscript_update_20261028';P=R/'Paper_DSN/revisions/20261031_dsn2027_release_v2'
qa=P/'QA_AUTOMATED_v1/QA.json';visual=T/'FINAL_ALL_PAGE_VISUAL_QA_20261031_v2.json';record=T/'FINAL_RELEASE_RECORD_20261031_v2.json'
assert not visual.exists() and not record.exists()
notes=('Root actually viewed all12 final1800px page images. Three scientific figures and three tables are legible, including the4-row matched version table and8.5pt full-width fault table. No clipping, overlap or visible author/repository identity. Pages1-11 contain technical material and disclosed AI usage; page12 is references only. All23 fonts embedded, noType3, nooverfull/undefined citation or reference. Source/normal/resident/controlled-timing/stress scopes, original failed audit gates and final admission NO_GO are explicit. Standard IEEE final/reference column imbalance does not obscure content.')
subprocess.run([sys.executable,'-B',str(T/'record_final_visual_review.py'),'--release',str(P),'--automated-qa',str(qa),'--rendered-directory',str(P/'QA_RENDERED_v1'),'--output',str(visual),'--reviewed-pages',','.join(map(str,range(1,13))),'--root-reviewed-all-pages','--notes',notes],check=True)
archive=P/'RevTrace_DSN2027_anonymous_source_v2.zip'
subprocess.run([sys.executable,'-B',str(T/'package_dsn_release.py'),'--release',str(P),'--automated-qa',str(qa),'--visual-review',str(visual),'--archive',str(archive),'--final-record',str(record)],check=True)
data=json.loads(record.read_bytes());print(json.dumps(dict(gate=data['gate'],pdf_sha256=data['pdf_sha256'],archive_sha256=data['archive_sha256'],archive_bytes=data['archive_bytes']),indent=2))
