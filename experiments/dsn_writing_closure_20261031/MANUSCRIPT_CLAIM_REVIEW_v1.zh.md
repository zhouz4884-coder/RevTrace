# 新 DSN 故事稿：跨节主张、合同与可读性复核

审查日期：2026-10-31。只读对象为 `Paper_DSN/revisions/20261031_dsn_story_progress/main.tex` 及其全部实际可达章节；PDF 为本次已编译的 12 页。数据对照为 `FINAL4F_CONTENT_RECOUNT_REPORT.zh.md`、既有 final4f 原源和本轮近邻定位记录。未运行模型、未访问远端、未修改正文；本文件是审查交付，不替代 Root 的逐页视觉 QA。

**结论：跨节主张目前一致，可以进入最终排版收束。** 没有发现需要重开实验的证据缺口，亦没有发现最终/早期实现的数字串用。建议补两处短算法动作，并消除一处计数歧义。下列均为文字可实现性或准确表达问题，不是新发现运行时缺陷。

## 三处具体风险

1. **中：短算法漏写产生临时链的 ASR projection 分支。** `sections/03_coordination_algorithm.tex:22–25` 的 Receive 只描述完整原始结果与 unknown buffer；表内 Dispatch 随后又依赖 conditional tail，Consume 依赖整视图 h。`03_native_extension.tex:13–19` 已解释 typed first-beam projection，表后 `03_coordination_algorithm.tex:43–44` 也解释完整结果替换投影，但读者只按 Table I 实现时，尚看不到什么事件可以合法生成/延长这条临时链。建议在 Receive 补一句：**“Typed ASR projections extend only a checked provisional path; they do not select.”** 必须继续保留当前的完整结果/投影类型区分，不能将未知完整结果直接当作已选中转移。

2. **中低：Consume 的失败分支应明说安装后的默认显示对象。** `sections/03_coordination_algorithm.tex:30–32` 目前为 “keep h whole iff S(C,h) ... Otherwise withdraw h”。主性质 `03_continuation.tex:78–86` 明确保护的是 **ahead 且仍支持** 的旧整视图；实际 `feedback_contract.py::Reconciler.install/visible` 在不保留临时链时退到新 Canonical cut。建议压缩成 **“retain a supported ahead h; otherwise render the installed cut.”** 这既与性质的作用域对齐，也避免把 withdraw 误读为空白显示或把已被新根覆盖的 h 继续固定。它只是补全算法动作，不扩大性质、不更改端点。

3. **低：必要撤回的计数最好明确为每个 bank 两次。** `sections/05_native_retention.tex:97–98` 的 “Both Full-call banks also contain two necessary incompatible withdrawals” 可被快速读成两批合计两次。正式 CPU 表是 matched Full-call=2、resident Full-call=2，共4。建议写 **“Each Full-call bank also contains two necessary incompatible withdrawals.”** 同段 `:84–85` 的斜线数值可加 “matched/resident, respectively”，但其现有数值本身正确。

没有把细小语言偏好、已有且诚实披露的负结果或版面取舍列为重大风险。Table I 是机制摘要，不必塞入所有 RPC、WAL、重放和物理检查细节；补足临时链输入与回退动作后，正文已有足够上下文。

## 重点通过项

- **主信息和贡献边界。** `01_progress_introduction.tex:37–57` 把完整输入、原选择和整视图支持分开，并用 own prediction 错、future input 未定、producer 已死三个具体不同情形解释。`:59–73` 的三贡献映射到合同/机制、执行与证据；没有声称首次依赖复用或首次计算/显示联合。核心“R 单开更差”也没有被写成 R/S 对所有安全系统普遍必要。
- **Fig.2 与 native 源一致。** `04_protocol.tex:4–12` 明示完整冻结输入、自己的下一预测可错、原 C/U 输出、accepted buffer 原身份、producer exit/fencing、durable sync 和实际 use；也明确是因果 schematic 而非测量时间线。没有把 CK5 BatchDrained 等同于 native 单进程生命周期；`:17–23` 分开了这两条执行路径。
- **未知不等于反驳。** `03_native_extension.tex:27–32` 与 `03_coordination_algorithm.tex:41–48` 保留了 view withdrawal 与 unknown call 的不同动作。其 actual same-frontier witness 逻辑与 final4f `fullspec_policy.py::_reason`、`dependency_support_losses` 一致。`03_continuation.tex:47–57` 仍清楚限定 core Qwen 的 boundary-node/unique-successor 保守实现，没有将 native 条件反写到旧 core。
- **原任务与证明没有过度升级。** `03_native_refinement_working.tex:19–26` 将充分状态、冻结输入忠实执行、独占选择、消息身份和同步存储列为前提；`:44–51` 分开有限规格、实际 checker 和 GPU 精确对照。全稿未将其叫全 Python/CUDA 验证，也没有假定任意独立浮点重跑必然逐位相等。
- **近邻承认足够直接。** `06_progress_related.tex:29–38` 正面承认 SSBD 的 draft/display 协调与无偏配置，以及 PredGen 变化输入上的预执行先例；`:48–54` 明确 Retire 已联合 revocation、valid inheritance 和 physical reclamation。差别落到固定反馈任务中的完整调用资格与整视图动作；没有用未评测推导外部系统“不可能做到”。`:56–63` 将 OCC/WAL 等定位为基础支撑。
- **对照身份公平。** `05_evaluation_core.tex:37–52` 明说四臂共享验证、持久化、输入和执行；Full composition 是作者完整组合的正控，不是外部原生 SOTA。`05_native_retention.tex:3–11` 将两完整副本、同 Consumer、同 warmup 与自建调度方案放在结果前，避免用单副本弱对照解释收益。
- **新内容数字核对通过。** `05_native_retention.tex:80–90` 与正式 CPU 报告一致：matched supported credit 22.5→51.0s；resident 24.0→50.259s；Full-call 未支持信用分别14.822/13.860s，unknown=0；四个 cohort/arm 行均180 introduced、14 retracted、166 last-visible occurrences；两个 bank 内全部 offered 各136，Conservative 106 次、Full-call 104 次全文匹配。没有将信用增加写成字数、总体匹配率或人工正确率增加。建议仅做上述“每批两次”措辞修正。
- **连续性的小分母没有被包装。** `05_native_retention.tex:92–99` 明说 matched compatible 分母零、resident 唯一非空机会，0.817s 为跨该更新的逻辑保持区间，不是避免宕机；右删失端点为最后同源实际观察。没有把1/1变成总体保留率。旧36轨迹90/90与1118次必要撤回仍在 `05_same_source_validation.tex:79–81` 单列，没有与新批相加。
- **早期与最终数据没有串用。** native 独立确认仍为 earlier bdfa 的8/8；最终匹配表为6/8，resident为7/8。6.52%是最终 Full-call 对最终 Conservative 的共同 drain 窗口，10.61%为最终对早期 Full-call 的成本增加。`05_native_retention.tex:49–71` 保留 EOS 失败与不同清理端点。全稿未沿用早期29→51.518125的内容信用。
- **显著失败没有被挪走。** core headline 全15次 D2 失败、fresh repeat负交互、c12阴性、无reset长流严重CER/期限失败、Owner冷恢复慢、双客户端没有稳定准入收益均仍可见。已披露完整 buffer 结论来自修复 READY reader 后的不变 raw 重构，并保存原失败门；没有写成原 CLI 全部通过。
- **技术页边界。** 只读 PDF 文本检查共12页；Table I 在第4页、native表/新内容在第8–9页、故障表在第10页；第12页从 REFERENCES 开始，技术内容与 AI Tool Usage 在前11页。这不是字形/溢出视觉验收，最终仍按 Root 的全页 render QA。

## 最终写作判断

这一版已经从“结果目录”转向了同一个科学推理：及时交付为何仍会丢失 → 为什么需要分别判断三个对象 → 哪些动作保留/撤回/安装 → 同任务因子实验与完整原调用证明了什么 → 哪些边界仍失败。建议保持这个焦点，完成上述小修和全页视觉检查后交付，不为本轮近邻复核再扩充神经实验矩阵。
