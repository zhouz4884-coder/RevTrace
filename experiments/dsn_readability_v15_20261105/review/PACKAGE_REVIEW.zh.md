# RevTrace v15 打包提示关闭检查

结论：**PASS_PACKAGE_NOTE_RESOLVED**。此前冷读报告中的 README 版本提示已关闭；`FINAL_COLD_READ.zh.md/.json` 保留为当时的审阅记录，无需改写。现行稿件仍为 12 页、SHA-256 `b5c410b6c6fd08cec08535398910b49398dc0dc78cde497638eb537b661db750`，没有新增阅读问题。

本轮直接读取实际 ZIP 及当前文件，并独立比较 PDF 渲染像素，未仅采信已有 QA 状态：

- 源码 ZIP 的实际 SHA-256 为 `6f2332f979b48561c3d2682d02b21ad3c9e36809563e16a27ef6ebafb659af48`。包含 38 个文件，无重复或越界路径：37 个清单输入加 `PACKAGING_PROVENANCE.json`，成员集合精确相等。逐个输入的长度和 SHA-256 与清单相符，ZIP 字节同时与当前 revision 文件和冷编译目录文件相符。
- ZIP 内 `README.md` 现已明确写 source v15，说明新增的 Fig. 1 独立 renderer、配置和原始输入，并将它们与保持原身份、独立供应的 frozen v13 科学证据 companion 区分。五个 `figures/figure1_source/` 文件均在包内。旧的版本提示不再成立。
- 实际冷编译 PDF 的 SHA-256 为 `88a3c24f2e8dd065d99f3f2a070b651b3800bc6283f866cc82a1e45623f39351`。独立使用 PyMuPDF、RGB、matrix 1.5 将它与交付 PDF 的全部 12 页逐页渲染，尺寸与完整像素字节 **12/12 完全相同**。因此先前对实际十二页的冷读和色彩/灰度判断覆盖此冷编译结果。
- 将 `paper_qa/FINAL_v1/figure1_reproduction/timely_full_interval_case.pdf` 与实际稿件 Fig. 1 分别用 PyMuPDF、RGB、matrix 3 渲染，完整像素字节完全相同。实际文本保留 2.176-s 缺口、D2 +27.4 ms、两套各自 ready clocks，以及对应的 snapshot replacement/retained 16-s view 操作标注；与冷读时判断一致。
- 原始 v13 证据 companion 的实际 SHA-256 为 `09e3ae7be37b56fdc8ce4993f0a13fd767a7d62ec3f8d4adbb66afad610f7d5f`，与声明的冻结身份相同。

未解决事项：**0**。本轮没有启动模型、GPU 实验、统计重算或新的宽范围审稿，也没有修改稿件。没有重新执行 LaTeX 编译；本轮独立核查的是已提供的实际冷编译 PDF 与其完整像素、归档成员和字节清单。可逐项审计的数据见 `PACKAGE_REVIEW.json`。
