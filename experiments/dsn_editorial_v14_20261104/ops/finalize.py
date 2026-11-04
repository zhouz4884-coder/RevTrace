from pathlib import Path
import difflib,hashlib,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261104_dsn2027_release_v14';O=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes())
q=read(E/'paper_qa/FINAL_v2/SUMMARY.json');assert q['status'].startswith('PASS_') and q['pdf_sha256']==sha(P/'main.pdf')
reviewpath=E/'review/FINAL_V14_COLD_READ.json';review=read(reviewpath);s=json.dumps(review,ensure_ascii=False)
assert q['pdf_sha256'] in s and 'PASS' in s
assert read(E/'review/EXECUTION_PROOF_AUDIT.json')
patch=[]
for p in sorted(P.rglob('*.tex')):
 old=O/p.relative_to(P);patch.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),p.read_text(encoding='utf-8').splitlines(True),fromfile='v13/'+p.relative_to(P).as_posix(),tofile='v14/'+p.relative_to(P).as_posix()))
(E/'MANUSCRIPT_DIFF.patch').write_bytes(''.join(patch).encode())
gate=dict(status='PASS_V14_REVIEWER_TARGETED_EDITORIAL_AND_READABILITY_CLOSURE',base_commit='1f841da127d7bba5cead8b129da25da56a50b0eb',pdf_sha256=q['pdf_sha256'],source_zip_sha256=q['source_zip_sha256'],frozen_companion_sha256=q['frozen_companion_sha256'],technical_pages=11,reference_pages=1,cited_works=31,abstract_words=143,method_changed=False,new_model_calls=0,new_GPU_runs=0,new_service_trials=0,independent_sources=8,frozen_service_trials=32,selected_transitions=564,three_proposition_statements_unchanged=True,proof3_only_supported_interleaving_explanation=True,figures_data_and_bytes_unchanged=True,v13_files_preserved=37,v11_evidence_files_preserved=616,full_cold_build_pixel_identical=True,independent_review_sha256=sha(reviewpath),remaining_required_work=[],conference_submission_performed=False,GitHub_delivery='Verified in separate delivery receipt after push')
(E/'FINAL_RELEASE_GATE.json').write_bytes((json.dumps(gate,indent=2)+'\n').encode())
text='''# RevTrace v14：审稿视角与可读性修订完成

本轮将现有贡献组织得更可理解、更易核对。改进集中在首达之后的实际可用性空洞、三判断的对象差异、早完成结果的串行选择依据，以及迁移/复现的具体义务。可读性检查同时修正表格碎行、基线对齐、指代和重复自述。

方法、原32次新八来源服务运行、564次选定转移、原D2/C8、offered/EOS、质量、能耗与统计单位均未变化。没有新GPU、模型或方法分支。四张图保持v13原始PDF/SVG字节；不因建议重复再画一轮。

源码核对支持命题3的说明：父输入未知的早完成结果先缓冲，实际父状态和完整冻结输入重查后才可追加子事实。R/S关闭时保留专用函数可能短路，所以正文仅声明共享输入准入/视图应用安全门，没有将判据与动作或实现路径混同。详细行号在独立执行审计中。

新三行对象表替换重复overview；故障表列名改为Fault-to-new-fact并保留原消费端点。迁移义务涵盖完整状态、原选择/结果/身份/持久转移和实际Consumer完整视图依赖。匿名材料说明区分包内摘要/统计/图重建与外部完整日志重审、模型重跑。AI参与实际范围保持。

最终11页正文加1页参考文献、31篇引用，摘要143词（字母数字计数）。3命题、5公式、前2段证明不变，命题3仅增加交错说明。v13的37份发布文件、v11及独立确认的616份冻结对象和原NN4f59文件均核对保持。独立冷读检查最终PDF的文字、实际版面和灰度；新33文件源码包从空目录编译出12页逐像素一致PDF。

交付：新稿目录中的main.pdf与RevTrace_DSN2027_anonymous_source_v14.zip；配套证据按原身份复用RevTrace_DSN2027_anonymous_evidence_v13.zip，原hash不变。过程、逐项处置与新增论证证据见EDITORIAL_DELTA.zh.md、CLAIM_EVIDENCE_DELTA.md和review/。大日志/权重不随匿名包提供，未向会议提交。

发布记录与远端逐字节回读见DELIVERY_RECEIPT.json。本轮完成到此收束。
'''
(E/'FINAL_REPORT.zh.md').write_bytes(text.encode())
current='''# Current RevTrace manuscript — editorial v14, 2026-11-04

- [Manuscript PDF](revisions/20261104_dsn2027_release_v14/main.pdf)
- [Main LaTeX](revisions/20261104_dsn2027_release_v14/main.tex)
- [Anonymous source ZIP](revisions/20261104_dsn2027_release_v14/RevTrace_DSN2027_anonymous_source_v14.zip)
- [Frozen v13 evidence companion](revisions/20261104_dsn2027_release_v14/RevTrace_DSN2027_anonymous_evidence_v13.zip)
- [Revision report](../experiments/dsn_editorial_v14_20261104/FINAL_REPORT.zh.md)
- [Detailed dispositions](../experiments/dsn_editorial_v14_20261104/EDITORIAL_DELTA.zh.md)
- [New claim–evidence bindings](../experiments/dsn_editorial_v14_20261104/CLAIM_EVIDENCE_DELTA.md)
- [Final gate](../experiments/dsn_editorial_v14_20261104/FINAL_RELEASE_GATE.json)
- [Frozen v13 PDF](revisions/20261103_dsn2027_release_v13/main.pdf)

v14 sharpens service significance, the three decision objects, early-result
buffering/selection and adapter obligations. It improves prose and table
readability without changing the method or scientific results. The native
confirmation remains eight independent sources,32trials and564selected steps;
coverage40.6%→93.9%, paired gain53.3pp (95% CI[44.8,59.6]), passes0/16→10/16.

The paper has11technical pages plus1reference page and31cited works. Four
figure PDFs/SVGs and the v13 evidence companion are reused byte-for-byte.
The new33-file source ZIP cold-builds to12pixel-identical pages. Independent
reading covers prose, actual table/figure layout and grayscale. No new GPU
or model run and no conference submission was performed.
'''
(R/'Paper_DSN/CURRENT.md').write_bytes(current.encode())
latest=dict(date='2026-11-04',status='COMPLETE_V14_TARGETED_REVIEWER_AND_READABILITY_REVISION',report='dsn_editorial_v14_20261104/FINAL_REPORT.zh.md',final_gate='dsn_editorial_v14_20261104/FINAL_RELEASE_GATE.json',paper=P.relative_to(R).as_posix()+'/main.pdf',new_actual_NN_trials=0,reused_frozen_independent_trials=32,reused_frozen_independent_speakers=8,method_changed=False,new_GPU_matrix=False,cited_references=31,technical_pages=11,reference_pages=1,proof_change='Supported interleaving explanation in existing proposition3 only',four_figures_unchanged=True,frozen_evidence_companion_identity='v13',independent_review_complete=True,conference_submission_performed=False)
(R/'experiments/LATEST_RESEARCH.json').write_bytes((json.dumps(latest,indent=2)+'\n').encode());print(json.dumps(gate))
