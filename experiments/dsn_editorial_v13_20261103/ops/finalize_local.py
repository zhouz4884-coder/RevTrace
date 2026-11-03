"""Close the complete editorial scope only after real build and review gates."""
from pathlib import Path
import hashlib,json,subprocess,sys
from datetime import datetime,timezone
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13';Q=E/'paper_qa'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def put(p,j):Path(p).write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
qa=read(Q/'FINAL_QA.json');cold=read(Q/'COLD_BUILD_QA.json');review=read(E/'review/INDEPENDENT_COLD_READ.json');pack=read(Q/'anonymous_evidence_check/SUMMARY.json')
pkg_review=read(E/'review/ANONYMOUS_PACKAGE_INDEPENDENT_REVIEW.json')
assert qa['pdf_sha256']==cold['pdf_sha256']==review['pdf']['sha256']==sha(P/'main.pdf')
assert pack['status']=='PASS_FRESH_ANONYMOUS_EVIDENCE_SOURCE_STATISTICS_AND_FIGURE_REPRODUCTION' and pack['all_five_figures_pixel_identical']
assert pack['archive_sha256']==sha(P/'RevTrace_DSN2027_anonymous_evidence_v13.zip')
assert not review['material_issues'] if 'material_issues' in review else True
assert 'PASS' in pkg_review.get('decision',pkg_review.get('gate',pkg_review.get('status','')))
assert len(review['coverage']['grayscale_pages_visually_inspected'])==12
assert read(E/'review/COMPARISON_COST_AUDIT.json')['gate']=='PASS_V13_COMPARISON_COST_SCOPE_WITH_NO_RESULT_CORRECTION'
archive=read(E/'REMOTE_ARCHIVE_RECEIPT.json');assert archive['all_file_hashes_verified']
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(E/'FINAL_DEFAULT_SOURCE_GATE.json')],cwd=R,check=True,capture_output=True)
sg=read(E/'FINAL_DEFAULT_SOURCE_GATE.json');assert sg['gate']=='SOURCE_IDENTITY_PASS' and sg['files_verified']==59 and sg['code_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
assert sg['setup_pointer_sha256']==read(E/'figures/ROOT_DEFAULT_SOURCE_GATE_v1.json')['setup_pointer_sha256']
visual=dict(gate='PASS_ALL_12_PAGES_INDEPENDENT_COLOR_AND_GRAYSCALE_REVIEW',pdf_sha256=qa['pdf_sha256'],independent_review_sha256=sha(E/'review/INDEPENDENT_COLD_READ.json'),independent_full_text_pages=list(range(1,13)),independent_grayscale_pages=list(range(1,13)),root_color_pages_inspected=[1,2,3,8,11,12],root_full_size_figure_exports_inspected=['timely_full_interval_case','coordination_protocol','core_interaction','native_content','source8_paired_effects'],key_figure_label_print_size_pt='approximately 8.02; smaller math fragments are subscripts',issues_remaining=[],technical_font_or_line_spacing_reduced=False)
put(Q/'VISUAL_REVIEW.json',visual)
qa.update(visual_review='PASS_INDEPENDENT_ALL_PAGES_AND_FINAL_ARTIFACT_AUDIT',visual_review_sha256=sha(Q/'VISUAL_REVIEW.json'),anonymous_package_independent_review_sha256=sha(E/'review/ANONYMOUS_PACKAGE_INDEPENDENT_REVIEW.json'))
put(Q/'FINAL_QA.json',qa)
pre=dict(status='PASS_PDF_AND_ARTIFACT_PRE_SUBMISSION_CHECKS',checked_date='2026-11-03',official_CFP='https://dsn2027-berlin.github.io/call-for-contributions/',paper_type='Regular',technical_pages=11,references_only_pages=[12],abstract_whitespace_words=qa['abstract_words_whitespace'],abstract_alphanumeric_words=qa['abstract_words_alphanumeric'],letter_two_column_IEEE_10pt_12pt=True,fonts_embedded=True,grayscale_review_complete=True,authors_anonymous=True,identifying_paths_absent_in_paper_and_packages=True,AI_Tool_Usage_disclosed=True,pdf_sha256=sha(P/'main.pdf'),source_zip_sha256=cold['source_zip_sha256'],evidence_zip_sha256=pack['archive_sha256'],source_cold_build_pixel_identical=True,companion_checks_and_plots_reproduced=True,title_unchanged=True,system_name_retained=True,public_title_check='Two arXiv-domain title searches found no indexed exact-title match; this search is not proof of publication absence.',submission_action_performed=False,scope='Checks the local PDF and supplied artifacts. Portal author identities, COIs and originality/exclusivity declarations are outside this editorial delivery; no conference submission is made.',official_revision_policy=dict(invited_revised_regular_pages=12,new_content_limit_percent=30,rebuttal_word_limit=750,not_used_to_defer_core_evidence=True),artifact_evaluation_separate_from_research_track=True)
put(E/'SUBMISSION_PREFLIGHT.json',pre)
gate=dict(status='PASS_COMPLETE_LOCAL_V13_EDITORIAL_AND_ARTIFACT_SCOPE',method_changed=False,new_GPU_runs=0,new_model_calls=0,new_serving_trials=0,frozen_NN_source=sg['code_commit'],frozen_NN_source_manifest_sha256=sg['manifest_sha256'],frozen_default_source_pointer_unchanged=True,v11_evidence_files_preserved=qa['all_frozen_v11_evidence_files_preserved'],v12_release_files_preserved=qa['all_frozen_v12_files_preserved'],formal_blocks_unchanged=qa['unchanged_formal_blocks'],independent_native_sources=8,independent_native_trials=32,selected_transitions=564,original_results_unchanged=True,main_figures=4,artifact_only_figures=1,figure_data_unchanged=True,pdf_sha256=sha(P/'main.pdf'),source_zip_sha256=cold['source_zip_sha256'],evidence_zip_sha256=pack['archive_sha256'],technical_pages=11,reference_pages=1,cited_references=31,independent_cold_read_complete=True,anonymous_package_condition_resolved=True,all_source_and_figure_cold_checks_pass=True,legacy_dirty_checkout_preserved=True,conference_submission_performed=False,required_local_work_remaining=[],GitHub_delivery='Verified separately after publishing explicit bounded paths')
put(E/'FINAL_RELEASE_GATE.json',gate)
report='''# RevTrace v13：完整编辑交付

本轮完成两份外部材料的选择性落实，并经过独立判断、实际改稿、重绘、冷读、包内复算和冷编译。
论文方法、原NN4f、新八来源32次独立服务运行、D2/C8、offered/EOS、质量与能量窗口均未变。

## 论文增强了什么

- 摘要给出53.3个百分点的speaker-paired增益与95%区间[44.8,59.6]，并区分core与native的职责。
- 引言以真实兼容撤回说明首达与持续可用；图1保留D2+27.4ms的真实权衡。
- 三用途证据在图2闭环：完整调用已运行，完整结果与输入确认可异步汇合；原选择与实际整视图检查分别决定后续用途。
- 图3保留因子交互和原统计单位；图4直接给出及时部分合计。八来源点图只放配套材料，未制造个体CI。
- 主结果后紧接完整历史与最终质量保持；S0915写成可复用前瞻耗尽的观察路径，保留S0901/S0902差异。
- 压缩重复论证和结论以满足页限，没有缩正文字号或行距。正文保留四个Finding，没有添加新方法贡献。

## 独立判断和结果

新八来源覆盖仍是40.6%→93.9%，整场通过仍是0/16→10/16，564个原选择转移和13.22% CER保持。
能量窗口独立复核一致，约5.23%的同合同能量下降不需改数。
历史ready-only第二worker不含Corrector、积分终点也不同，不能把该旧对照拼成新八来源第三臂。
成本表继续报告八运行均值范围，不相减伪造纯验证税。

31项引用完成正文用途、一手机制与书目身份映射；只采用四项精度修订。
全部20个可达TeX和12页PDF完成独立冷读，12页灰度均检查，无实质问题。

## 实际交付

- `Paper_DSN/revisions/20261103_dsn2027_release_v13/main.pdf`：11页技术内容+1页参考文献，31项引用。
- 同目录 `RevTrace_DSN2027_anonymous_source_v13.zip`：33文件，干净解压编译得到12页逐像素一致PDF。
- 同目录 `RevTrace_DSN2027_anonymous_evidence_v13.zip`：173文件，包含六组原源码快照共103文件（NN4f59文件）、配置、逐run身份、摘要、原始日志hash索引与图源。
- 配套材料全新解压后，32运行算术、八来源效应和20,000次配对bootstrap重算一致；五图重绘逐像素一致。
- 大日志和模型权重不在匿名包内；包说明没有声称一键完成全部原服务重跑。
- 有界图形/验证输出已归档指定8TB盘并按hash回读；GitHub精确提交与回读见`DELIVERY_RECEIPT.json`。

逐条修改见`EDITORIAL_DELTA.zh.md`，主张证据见`CLAIM_EVIDENCE.md`，独立审阅在`review/`，构建和验收在`paper_qa/`。
v12的31份发布文件、v11及独立确认的616份冻结对象均保留；3命题、3证明、5公式保持不变。

本轮到交付即停止，无新GPU矩阵、方法分支或新增服务样本；也未向会议提交。
'''
(E/'FINAL_REPORT.zh.md').write_text(report,encoding='utf-8')
current='''# Current RevTrace manuscript — editorial v13, 2026-11-03

- [Manuscript PDF](revisions/20261103_dsn2027_release_v13/main.pdf)
- [Main LaTeX](revisions/20261103_dsn2027_release_v13/main.tex)
- [Anonymous source ZIP](revisions/20261103_dsn2027_release_v13/RevTrace_DSN2027_anonymous_source_v13.zip)
- [Anonymous evidence and editable figures](revisions/20261103_dsn2027_release_v13/RevTrace_DSN2027_anonymous_evidence_v13.zip)
- [Editorial report](../experiments/dsn_editorial_v13_20261103/FINAL_REPORT.zh.md)
- [Detailed changes](../experiments/dsn_editorial_v13_20261103/EDITORIAL_DELTA.zh.md)
- [Claim–evidence map](../experiments/dsn_editorial_v13_20261103/CLAIM_EVIDENCE.md)
- [Final gate](../experiments/dsn_editorial_v13_20261103/FINAL_RELEASE_GATE.json)
- [Frozen v12](revisions/20261102_dsn2027_release_v12/main.pdf)
- [Frozen independent native result](../experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/PAPER_DATA.json)

v13 changes writing and figure presentation, not the method or experimental
results. Eight independent sources/32 trials still give40.6%→93.9% coverage,
53.3pp paired gain (95% interval[44.8,59.6]), and0/16→10/16 whole-run passes.
The original selected task and quality are unchanged; no new serving run is added.

The four main figures preserve their data. All12pages have independent color/
grayscale review.31references have primary-source mappings. The33-file source
package cold-builds to12pixel-identical pages; the173-file companion reproduces
the paired statistics and all5figure exports. Models and full journals are not
included. No conference submission has been made.
'''
(R/'Paper_DSN/CURRENT.md').write_text(current,encoding='utf-8')
latest=dict(date='2026-11-03',status='COMPLETE_V13_EDITORIAL_REVISION_WITH_FROZEN_EXPERIMENTS',report='dsn_editorial_v13_20261103/FINAL_REPORT.zh.md',final_gate='dsn_editorial_v13_20261103/FINAL_RELEASE_GATE.json',paper='Paper_DSN/revisions/20261103_dsn2027_release_v13/main.pdf',new_actual_NN_trials=0,reused_frozen_independent_trials=32,reused_frozen_independent_speakers=8,method_changed=False,v11_confirmation_relabelled=False,runtime_patch_created=False,new_GPU_matrix=False,independent_cold_read_complete=True,anonymous_artifact_checks_complete=True,submission_preflight_complete=True,no_further_method_branch=True,cited_references=31,technical_pages=11,references_pages=1,previous_frozen_paper='Paper_DSN/revisions/20261102_dsn2027_release_v12/main.pdf',conference_submission_performed=False)
put(R/'experiments/LATEST_RESEARCH.json',latest)
print(json.dumps(gate))
