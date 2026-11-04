# v13 独立定点审阅

审查对象为 `Paper_DSN/revisions/20261103_dsn2027_release_v13/main.pdf`，12 页，SHA256 `1413182663224acb507c2c68080f4dc8d340b2d7dab47a678e2aea39aa941928`。已逐页读取 PDF 文本、全部可达 TeX（含表格），并查看与此哈希绑定的第 1、2、3、5、8、11 页实际渲染。另已读取用户的两份文本附件及 `E:/Downloads/RevTrace_v13_Reviewer_Audit_and_Revision_1f841da.md`。审阅只提出增量编辑；未修改论文、runtime，未运行模型或 GPU。

判断：v13 的核心证据和边界已经可辨认。下一轮最有价值的是下面四项，均可用现有冻结证据完成。没有发现需要重开 GPU 的真实性或计量问题。本审阅不作录用预测，也不把附件中关于会议审美的判断当作硬性规则。

## 1. 用真实可用性缺口解释服务意义，并修复图1指代

**处置：采用，最高优先级。** 第 1 页仍写 `Both first deliveries` 和 `slightly late`；图1第 2 页已经正确标明面板(b)晚 27.4 ms。问题是引言的指代和解释不够直接，并非图或原指标算错。

- 源码：`sections/01_progress_introduction.tex:5-10,27-30`。
- PDF：第 1 页左栏前两段；第 2 页图1及图注。
- 已有实测支撑：`sections/05_operating_boundaries.tex:43-50`，PDF 第 9 页左栏末至右栏首，给出及时交付后缺失窗口、面积和读点交集。

将第二段替换成一小段说明“首次交付是过去事件，而 Consumer 后续读的是当前视图”，同时明确 `Figure 1(a)` 的两项首达期限满足，`Figure 1(b)` 晚 27.4 ms 却保留所示覆盖。不要重复增加背景或数字。可保留的核心句为：

> First-delivery compliance concerns a past delivery event, whereas a consumer reads the current view. An avoidable withdrawal removes progress that the new selected state still supports, creating a service gap without a corresponding refutation.

不采用附件中的不可逆 Agent/翻译损害、既有 SLO 被虚报等主张：当前证据只测到了实际视图缺失；首达指标对其定义没有计算错误。也不把图1两次运行改写为逐事件反事实。

## 2. 一次说明 EL/AU/SUP 的对象，并把它们与 R/S 动作分开

**处置：采用，以替换重复解释为主。** 第 3 页 overview 已有正确案例，但读者仍要到第 4-6 页才把三个判断与动作开关对应起来。可用三行紧凑对象表或等长文字替换重复段落，无须新增第五张图。

- 源码：`sections/03_coordination_overview.tex:11-23`；`sections/03_continuation.tex:43-71`；`sections/05_evaluation_core.tex:32-42`。
- PDF：第 3 页 §III-A；第 4 页 §III-C/D；第 6 页 §V-A(b)。

建议对象映射：EL 判断完整冻结输入，产生 confirmed/unknown/refuted 的资格结论；AU 判断完整原结果与当前父状态能否组成一次选中转移；SUP 判断实际完整视图在本次选中更新后是否仍有支持。紧接一句明确：

> R and S enable retention actions; the four arms share input-admission and actual view-application safety checks.

不要写成“关闭 R/S 后每个 retention predicate 仍完全相同地执行”。主审的实现核对指出，关闭保留时可跳过专用于保留的 `eligible_chain` 或 compatibility 分支。当前 `retaining the same dependency checks` 应收窄成上述共同安全门措辞。此处是表述精度问题，不是已发现的 runtime 缺陷。尤其不能把 EL=R、SUP=S，或把 UNKNOWN 写成反证。

## 3. 在命题3证明中补上早完成结果如何等待父状态

**处置：采用，两句以内，不扩展定理。** 第 5 页证明已经正确采用条件性投影，但 `regardless of dispatch time` 跳过了读者最关心的具体交错。表 I 说明了缓冲；证明宜直接连接缓冲、当前父状态校验与 durable append。

- 论文源码：`sections/03_native_refinement_working.tex:23-39`；`sections/03_coordination_algorithm.tex:23-27`。
- PDF：第 5 页左栏 Proposition 3、证明及表 I。
- 已直接检查 v13 evidence ZIP 内的冻结 NN4f 源码，执行源提交为 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`：`source_snapshots/native_runtime_NN4f/fullspec_policy.py:151-179` 将未确认完整结果缓冲，仅在输入等于当前父状态时取出提交；`resilience_policy.py:150-181` 在 durable hook 前核对父状态/epoch，hook 后复核；`resilience_storage.py:71-100` 校验 durable parent、完整结果与 job 绑定，写入并 fsync 后推进 durable root。

因此可准确补入：

> A result completed before its parent is installed remains buffered. Under exclusive serial selection, the current parent and complete frozen input are checked before appending the child's fact, so completion order cannot introduce a parentless projected edge.

这解释当前实现如何兑现原前提，未声称新的原子操作、所有 GPU 重跑确定性或全程序证明。保留充分状态、忠实执行、串行选择、身份与存储语义等前提。第 5 页有限状态检查应继续与条件证明、独立 trace checker 分开，不将两个不同有界模型的状态数相加来暗示更强证明。

## 4. 让迁移与复现说明各自给出可核对的义务

**处置：采用，限于第 11 页两个现有段落。** 适配段当前只直接列出“暴露 mutable fields”，而真正可迁移的合同还要求完整原选择和实际消费路径。建议替换为三项平行义务：捕获/恢复/比较影响后继行为的完整状态与输入；保留并绑定完整原选择、更新和持久选中身份；实际 Consumer 记录整视图来源和依赖并执行保留/撤回。保留 Qwen 与 native 的不同充分实现，不承诺仅有输入 hash 就能迁移。

- 源码：`sections/07_progress_discussion.tex:7-15`；具体适配实例见 `sections/02_contract.tex:50-57`、`sections/03_native_extension.tex:21-39`。
- PDF：第 11 页 §VII(b)；第 2 页 §II-B；第 4 页 §III-E。

复现段已有材料清单，应再用一句明确核对层次：包内从已归档摘要重算配对统计和从 frozen inputs 重绘图；完整端点重审/服务重跑仍需要独立提供的原始 journals、模型/录音、依赖及对应源身份。当前 companion README 已准确区分这些层次，可直接压缩移入正文，不能把 hash index 写成 full raw log。

- 源码：`sections/07_progress_discussion.tex:17-22`，PDF 第 11 页 §VII(c)。
- v13 evidence ZIP：`README.md:21-44`。其中明确统计重算不重新计量原始 endpoints。

这是对现有材料如何复核的说明，不增加新验证层或新工作流；提交前也不能提前写成材料已随会议提交。

## 已完成而应保留的内容

- 摘要已区分 core/native，已有 speaker-paired CI、全部八来源均正及 0/16→10/16；不再改写一轮摘要。
- 图1两臂标注、图2异步 parent/child 汇合和 pending input、图4及时合计已经存在。实际页图支持保留，不按旧截图重画。
- Alternative joint implementation 在 `05_evaluation_core.tex:39-42,109-114`（PDF 第 6-7 页）已准确称为作者构建、共享执行/提交底座的正控。不能称 clean-room independent reference，不把与主臂的覆盖点差升成新优势；可选空心标记不是本轮门槛。
- `main.tex:61-66`（PDF 第 11 页）AI 使用披露包含实际论证、runtime、编排和分析帮助，保留范围；不缩成仅润色。
- 命题1仍是充分条件，命题2仍是单次兼容应用；右删失、原始能耗窗口、全部 offered/EOS 与负结果均保留。
- 故障表 `New result (s)` 可顺手改成 `Fault-to-new-fact (s)`（`tables/native_reliability.tex:3`，PDF 第 10 页），图注现有实际 Consumer 消费定义保持。这是低成本标签修正，不是新增恢复保证。

验收只需核对上述文字、原数字/定理前提未变，以及新编译 PDF 的 11 页技术正文加参考文献布局。若四项完成，则应冻结此次编辑，不因建议数量继续扩张论文。
