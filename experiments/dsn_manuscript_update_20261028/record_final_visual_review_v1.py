import datetime,hashlib,json
from pathlib import Path
T=Path(__file__).resolve().parent;R=T.parents[1]
D=R/'Paper_DSN/revisions/20261029_dsn2027_release_v1'
qa=json.loads((D/'QA_AUTOMATED_v2/QA.json').read_bytes())
assert qa['gate']=='PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA'
assert qa['total_pages']==11 and qa['checks']['pagination']['technical_pages']==10
assert hashlib.sha256((D/'main.pdf').read_bytes()).hexdigest()==qa['pdf_sha256']
record=dict(gate='PASS_ROOT_ALL_PAGE_VISUAL_QA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pdf=D.relative_to(R).as_posix()+'/main.pdf',pdf_sha256=qa['pdf_sha256'],actual_root_visual_review=True,reviewed_pages=list(range(1,12)),rendered_max_side_pixels=1800,technical_pages=10,references_only_pages=[11],abstract_words=139,checks={'all_pages_readable':True,'no_text_figure_table_overlap_or_clipping':True,'all_three_figures_and_two_tables_reviewed':True,'references_only_on_final_page':True,'no_obvious_author_identity_or_own_repository_link_in_prose':True,'known_metadata_identity_tokens_checked_by_automated_QA':True},notes='Root inspected all eleven rendered pages. IEEE column continuations and references-only column imbalance are normal. One nonblocking underfull vbox; no overfull, undefined citation or undefined reference. All23 fonts embedded; no Type3. Automated v1 pagination was indeterminate because layout extraction joined the left References heading with right-column reference17; flow extraction v2 and actual page11 inspection confirm a clean references-only page.',rendered_pages=[dict(path=p.relative_to(R).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted((D/'QA_RENDERED_v1').glob('page-*.png'))])
p=T/'FINAL_ALL_PAGE_VISUAL_QA_v1.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'gate':record['gate'],'pages':record['reviewed_pages'],'pdf_sha256':qa['pdf_sha256']}))

