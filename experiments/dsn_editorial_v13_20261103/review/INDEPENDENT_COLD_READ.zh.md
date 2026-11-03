# v13 独立冷读结论

当前稿的技术叙述与图表通过本轮独立冷读，未发现必须修改的实质问题。复现材料的交付声明仍以最终匿名包审计为条件；本结论不替代原始结果重算或发布包验证。

- 审阅对象：`Paper_DSN/revisions/20261103_dsn2027_release_v13/main.pdf`。
- 实际 PDF SHA256：`1413182663224acb507c2c68080f4dc8d340b2d7dab47a678e2aea39aa941928`。
- 范围：完整 12 页 PDF（11 页技术正文与披露、1 页参考文献），`main.tex` 递归可达的全部 20 个 TeX 文件，3 个 BibTeX 文件及本稿 README。未用旧稿代替当前稿阅读。
- 方法：逐页提取并完整阅读 PDF 文本；对照全部可达 TeX；检查全部 12 页的 108-dpi 灰度渲染及图所在页的彩色渲染，并读取最终 PDF 中的实际图中文字字号。独立渲染与逐页文本位于 `review/independent_render/`。

## 关键判断

| 审查项 | 独立读者的实际理解与依据 |
|---|---|
| 首次交付与持续可用性 | Fig. 1 并未把两者混为同一胜负：computation-only 在 1.444 s 首次显示，随后丢失 2.176 s；RevTrace 在 2.027 s 首次显示，明确晚于 D2 27.4 ms，之后保持覆盖。图注明确是两个各用自身 ready clock 的执行，不能当作事件匹配的反事实。第 1 页引言、第 2 页 Fig. 1；`01_progress_introduction.tex:1–30`。Eq. (5) 的首次覆盖指标与后续兼容丢失分析分开定义，读者能理解连续性改善可与 D2 失败并存。第 6、9 页；`05_evaluation_core.tex:44–74`、`05_operating_boundaries.tex:43–53`。 |
| core 四臂与 native 两臂 | core 的 R/S 四臂在共同执行、验证、持久化与 Consumer 上隔离计算/视图保留，支持“只保留计算不足以保留服务”；Alternative joint 是作者构建的正控制，也得到零撤回。native 固定两个完整 worker 和早期视图 Consumer，对比等待父反馈与条件完整调用，支持完整调用重叠及其合法性；不能把 native 增益全部归给 S。正文已经这样表述，也明确不对外部系统作普遍排名。第 6–8、11 页；`05_evaluation_core.tex:1–42,76–117`、`05_native_retention.tex:12–20`、`07_progress_discussion.tex:1–5`。 |
| [EL] / [AU] / [SUP] | 输入确认不等于自身预测正确，原始 Correct/Update 仍决定完整结果；已有银行的 92 个提前调用中 20 个自身预测终态错误是独立佐证。unknown 不授权提交，也不构成基于反驳的取消证据。Fig. 2 中完整结果与 [EL] 的证据分别进入 [AU]，“either may arrive first”准确表达异步汇合；unknown→run/buffer 有独立分支；[SUP] 独立从父事实与实际整视图接收证据。图注还说明子事实 P3 应有自己的后续 [SUP]。第 3–5、8 页；`02_contract.tex:59–72`、`03_coordination_overview.tex:1–23`、`03_native_extension.tex:13–32`、`03_coordination_algorithm.tex:1–43`、`05_native_retention.tex:115–130`。 |
| 生产者死亡与已取得结果 | fencing 撤销后续消息权，不擦除已经合法接收的完整结果；该结果仍需与实际同 frontier 父状态匹配。正文明确接收/封闭通道验证在 fencing 前完成，匹配与不匹配各两例，控制性 interleaving 不声称故障 SLO。第 6、9–10 页；`04_native_resilience_working.tex:3–30`、`05_same_source_validation.tex:45–58`。 |
| 样本与统计单位 | 独立声学单位是 8 位说话人、每人一个 8–9 s utterance；2 策略×2 fresh repeats 得到 32 个计时 run，每策略 16 个。564 是审计过的 selected transitions，不能当作独立样本数。bootstrap 以说话人配对并把其两次计时保留在同一簇，20,000 次重采样得到 53.3 pp、95% CI [44.8,59.6]，8 个源的配对方向均为正。0/16→10/16 是整 run 通过数，非说话人数。稿件已充分交代这些分母。第 7、11 页；`05_native_retention.tex:1–11,24–49`、`07_progress_discussion.tex:1–5`。 |
| 能量与协议成本 | 能量从共同 trial origin 到确认物理模型 drain，计入未使用的已派发工作，并在同 runtime/工作负载内比较；不能直接比较 native 与 batched-core 数值。Table II 的 5.23% 降幅是该服务窗口的观察值。Table III 明确是 8 个 timing-enabled run 的每 run 平均值范围，commit 包含嵌套 fsync，Consumer application 包含检查和同步日志，因此没有把这些数误称为纯额外开销。Table V 的范围明确为两次试验最小/最大值，且故障时限失败保留。第 6–10 页；`05_evaluation_core.tex:59–66`、`05_native_retention.tex:52–55`、`05_protocol_cost.tex:1–30`、`05_same_source_validation.tex:24–43`。 |

## 论点强度与版面

论文目前清晰提出了三个有边界但有力度的结果：兼容更新仍会造成已交付进度丢失；完整调用可以在输入随后被确认时提前完成原始任务；结果的可用性与生产者能否继续发消息是不同判断。摘要、Finding 1–4 与结论都直接陈述这些结果。条件性 selected-trace refinement 与手写有界检查明确分开，没有扩大成完整 Python/CUDA 证明（第 5 页，`03_native_refinement_working.tex:21–59`）。长期不重置压力测试全部错过 D2/C8、出现原任务插入错误及更高能耗也明确保留，未冒充持续服务成果（第 10 页，`05_same_source_validation.tex:60–76`）。无需再添加泛化的防御性限制清单。

全部 12 页的正文、图注、表格、引用及跨页续文均可读；未发现裁切、遮挡、浮动体重叠、缺字或空白技术页。四幅图在灰度下仍由实线/虚线、圆/方标记、阴影斜线区分。最终 PDF 的图中文字主体最小约 8.02 pt；Fig. 2 小于 8 pt 的片段是数学下标，并非整句说明缩小。Fig. 4 虽为单栏图，三个覆盖分区及 40.6%/93.9% 等边界标签仍清楚。

必须修正的问题：无。最小修改建议：无。无需为本轮编辑冷读追加 GPU 实验。

## 最终材料的条件

第 11 页复现段（`07_progress_discussion.tex:17–22`）使用现在时称匿名材料提供 source snapshots、fixed configs、per-run identities、endpoint checkers 与 hash-bound figure inputs。只有在最终材料确实含有并验证这些内容时，该段才成立。包终审应把该声明与最终真实内容对齐；这是本轮唯一保留的交付条件，本报告未将其标记为已经完成。

本轮只写独立审阅报告、结构化审阅记录及自行生成的阅读渲染；未修改稿件、图、旧稿或冻结实验材料，未运行新 GPU 实验，未推送。
