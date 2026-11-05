from pathlib import Path
import difflib,hashlib,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261105_dsn2027_release_v15';O=R/'Paper_DSN/revisions/20261104_dsn2027_release_v14'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes())
q=read(E/'paper_qa/FINAL_v1/SUMMARY.json');assert q['status'].startswith('PASS_') and q['pdf_sha256']==sha(P/'main.pdf')
checks={n:read(E/'review'/n) for n in ['SEMANTIC_DIFF_REVIEW.json','FINAL_COLD_READ.json','PACKAGE_REVIEW.json','FIGURE_DESIGN_FINAL_QA_v1.json']}
for name,j in checks.items():assert 'PASS' in json.dumps(j),name
assert checks['SEMANTIC_DIFF_REVIEW.json']['open_material_findings']==0
assert checks['FINAL_COLD_READ.json']['pdf']['sha256']==q['pdf_sha256']
assert q['source_zip_sha256']==sha(P/'RevTrace_DSN2027_anonymous_source_v15.zip')
patch=[]
for p in sorted(P.rglob('*.tex')):patch.extend(difflib.unified_diff((O/p.relative_to(P)).read_text(encoding='utf-8').splitlines(True),p.read_text(encoding='utf-8').splitlines(True),fromfile='v14/'+p.relative_to(P).as_posix(),tofile='v15/'+p.relative_to(P).as_posix()))
(E/'MANUSCRIPT_DIFF.patch').write_bytes(''.join(patch).encode())
source=E/'figure_source';manifest=E/'review/FIGURE_DESIGN_SOURCE_v1.json'
assert sha(manifest)=='3983d7b8ce4f71843899abd7b7597c36547b16b8f84c404302d870899aae1044'
bundle=E/'packages/FIGURE_SOURCE_v1.bundle';assert not bundle.exists()
subprocess.run(['git','-C',str(source),'bundle','create',str(bundle),'HEAD'],capture_output=True,check=True)
assert subprocess.check_output(['git','-C',str(R),'cat-file','-t','fd8fe368e7327d36221fd1860767ec60cfd0ceeb'],text=True).strip()=='commit'
gate=dict(status='PASS_COMPLETE_V15_ACADEMIC_READABILITY_AND_VISUAL_REFINEMENT',base_commit='3bcbb7638e6d9106965e4274a6c388a0186ab7ee',pdf_sha256=q['pdf_sha256'],source_zip_sha256=q['source_zip_sha256'],source_zip_files=38,frozen_scientific_companion_identity='v13',frozen_companion_sha256=q['frozen_companion_sha256'],technical_pages=11,reference_pages=1,cited_works=31,abstract_words=143,three_propositions_three_proofs_five_equations_unchanged=True,numerical_measurements_frozen=True,display_rounding_only=True,figure1_only_action_annotations=True,figure1_reproduced_from_source=True,other_three_figures_unchanged=True,method_changed=False,new_model_calls=0,new_GPU_runs=0,new_service_trials=0,independent_sources=8,frozen_trials=32,selected_transitions=564,v14_files_preserved=37,v11_files_preserved=616,full_12_page_cold_build_pixel_identical=True,independent_readability_and_semantic_reviews_pass=True,source_pointer_unchanged=True,conference_submission_performed=False,remaining_required_work=[],GitHub_delivery='Verified separately after publication')
(E/'FINAL_RELEASE_GATE.json').write_bytes((json.dumps(gate,indent=2)+'\n').encode())
report='''# RevTrace v15：学术可读性精修完成

本轮目标是让审稿人更自然地理解同一项协调能力。调整了反直觉结果的出现顺序、逻辑角色与worker部署的解释顺序、生命周期段落、若干指代/内部短语、右删失说明和结论术语回声。Discussion先给设计教训。三个命题、三个证明、五个公式及31条书目均保持。

图1新增两个实际事件的动作标注，直接解释12-s快照替换14-s视图，以及14-s状态安装时16-s视图仍保留。D2晚27.4ms、2.176s缺口和两种真实交错完整保留；其余三图原字节未变。

正文只做明确的显示舍入，原始精度、数据、D2/C8、offered/EOS、统计单位、质量和能量窗口未变。新8来源/32服务运行/564选定转移及40.6%→93.9%、53.3pp [44.8,59.6]、0/16→10/16均沿用原冻结结果，没有新方法或GPU运行。

DSN风格依据复读了三篇正式收录论文，提炼能力主线、对象先后及证据衔接，不据此承诺录用。独立语言审阅与语义差异核查、陌生读者全文冷读和12页实际彩色/灰度检查均完成。修正了初稿的一处主设置能耗范围与RevTrace主体歧义。

最终11页正文+1页参考文献，143词摘要计数，31篇参考文献。新的38文件匿名源码包同时包含Fig1独立编辑源、配置和原始数值输入。从空目录冷编译得到12页逐像素一致PDF；包内源重画Fig1也逐像素一致。科学证据包按原v13身份和字节复用，模型权重、录音和完整大日志仍为外部资源。

正文与源包位于Paper_DSN/revisions/20261105_dsn2027_release_v15/。详细取舍见EDITORIAL_DELTA.zh.md；语义、DSN依据、图形设计与最终冷读在review/；数值舍入清单和冷编译在paper_qa/FINAL_v1/。归档/发布回读见REMOTE_ARCHIVE_RECEIPT.json和DELIVERY_RECEIPT.json。

v14的37份发布对象、v11/独立确认的616份冻结对象及原默认NN4f源保持。本轮到交付收束，未向会议提交。
'''
(E/'FINAL_REPORT.zh.md').write_bytes(report.encode())
current='''# Current RevTrace manuscript — readability v15, 2026-11-05

- [Manuscript PDF](revisions/20261105_dsn2027_release_v15/main.pdf)
- [Main LaTeX](revisions/20261105_dsn2027_release_v15/main.tex)
- [Anonymous source + editable Fig1](revisions/20261105_dsn2027_release_v15/RevTrace_DSN2027_anonymous_source_v15.zip)
- [Frozen scientific evidence companion](revisions/20261105_dsn2027_release_v15/RevTrace_DSN2027_anonymous_evidence_v13.zip)
- [Revision report](../experiments/dsn_readability_v15_20261105/FINAL_REPORT.zh.md)
- [Detailed dispositions](../experiments/dsn_readability_v15_20261105/EDITORIAL_DELTA.zh.md)
- [Final gate](../experiments/dsn_readability_v15_20261105/FINAL_RELEASE_GATE.json)
- [Frozen v14](revisions/20261104_dsn2027_release_v14/main.pdf)

v15 improves logical flow, terminology and paragraph references. Fig1 adds
two actual-action labels; the other three figure PDFs/SVGs are unchanged.
Three propositions, three proofs, five equations and31bibliographic items
remain unchanged. The original method and experiments remain frozen.

Eight independent sources/32trials still give40.6%→93.9% coverage,
53.3pp paired gain (95% CI[44.8,59.6]), and0/16→10/16 passes. No new
GPU, model or serving run is added. The paper has11technical pages plus
one reference page. The38-file source ZIP cold-builds to12pixel-identical
pages and reproduces the annotated Fig1 from standalone source. Independent
semantic/readability and actual color/grayscale review are complete.
No conference submission has been performed.
'''
(R/'Paper_DSN/CURRENT.md').write_bytes(current.encode())
latest=dict(date='2026-11-05',status='COMPLETE_V15_ACADEMIC_READABILITY_REFINEMENT',report='dsn_readability_v15_20261105/FINAL_REPORT.zh.md',final_gate='dsn_readability_v15_20261105/FINAL_RELEASE_GATE.json',paper=P.relative_to(R).as_posix()+'/main.pdf',new_actual_NN_trials=0,reused_frozen_independent_trials=32,reused_frozen_independent_speakers=8,method_changed=False,new_GPU_matrix=False,cited_references=31,technical_pages=11,reference_pages=1,mathematical_statements_and_proofs_unchanged=True,figure1_annotations_only=True,frozen_evidence_companion_identity='v13',independent_review_complete=True,conference_submission_performed=False)
(R/'experiments/LATEST_RESEARCH.json').write_bytes((json.dumps(latest,indent=2)+'\n').encode());print(json.dumps(gate))
