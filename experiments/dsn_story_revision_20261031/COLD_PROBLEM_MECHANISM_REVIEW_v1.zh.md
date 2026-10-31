# 首页与机制图独立冷读审阅

审阅日期：2026-10-31。范围仅为 `Paper_DSN/revisions/20261031_dsn_story_revision/main.pdf` 第 1 页、指定的 `FIGURES_v2/coordination_protocol_PDF_PAGE.png` 以及 PDF 的 Figure 2 图注。未读后续结果、项目历史或历史报告；未运行模型。本报告判断读者能否复述叙事及动作边界，不验证形式论证或数据真伪。

## 1. 具体可靠性问题，以及为何重要

可信反馈修订可以在没有否定当前进度的情况下，把 Consumer 已经显示且仍有支持的完整假设替换为更短快照，导致可用进度暂时消失。首次显示与首次认证都按时，并不足以防止这种“avoidable withdrawal”。首页给出的实例中，两秒音频区间在 ready 后 1.44 s 已显示，符合 D2；在 1.54 s 被更新撤下，相同文本在 3.72 s 返回，也符合 C8，却出现 2.176 s 的可见空档。

重要性是服务交付承诺的缺口：客户端既需要及时收到进度，也需要仍然有效的进度继续可用。只拒绝非法状态并不自动保证后者。只保留计算也不足够，因为合法的后续安装仍可能覆盖 Consumer 的有效 ahead view。首页把问题落到了实际 Consumer 和一次具体时间轨迹，足以让冷读者理解这不是单纯的文本准确率或首次延迟问题。

## 2. 一句话贡献

RevTrace 在保留原始结果的选择与有序安装语义的同时，分别确认完整调用输入、原始选择授权和完整显示视图的支持关系，从而跨可信反馈修订保留仍可用的计算与可见进度。

## 3. 三种判定分别控制什么动作

| 判定 | 冷读可复述的检查对象 | 直接控制的动作 | 不应误读成什么 |
|---|---|---|---|
| [EL] Input eligibility | 调用的完整冻结输入及其依赖路径，是否与实际选中的反馈状态一致；图中为 frozen P̂₂ 与 selected P₂ 的关系 | 确认后保留完整调用 j₃；反驳则拒绝该调用的适用性；未决则保持未决 | 不确认调用自己的下一步 ASR 预测 P̂₃ 正确，也不单独授予提交权 |
| [AU] Selection authority | 完整原始结果 P₃，以及原始 Correct/Update 和授权同步关系 | 保持原始结果的 durable selection 与有序 installation，防止以预测替代原始选择 | 不因旧输入已确认就采纳预测；不把 producer 存活位等同于所有已接受结果的资格 |
| [SUP] View support | P₂ 安装时，Consumer 实际显示的完整 ahead hypothesis h 是否仍受支持 | 支持则保留整个 h；不支持则撤回 h | 不仅检查未来调用输入；也不是只保留后台计算就会自动完成的显示策略 |

三者的动作区别能够复述：EL 管调用能否被保留和使用，AU 管哪一个完整原始结果有资格被选中并安装，SUP 管状态安装时 Consumer 的整个当前视图是否继续保留。

## 4. UNKNOWN 是否暂停调用，是否授权 commit

结合图注，答案明确：UNKNOWN 本身不要求暂停 owned call，调用可以继续运行或缓冲；它保持输入资格未决，不能因此授权 commit。等待的是资格确认或使用决定，不是必然停止模型执行。

仅看图内的 “Unknown: wait; no commit”，我会先对 “wait” 的对象犹豫；图注中的 “owned calls may run or buffer” 才消除了歧义。因此，包含图注时可准确回答，单独转发机制图时仍可能误读。

## 5. 相对“一律把旧工作判过期并丢弃”究竟新增什么

新增的是有条件的完整工作复用和独立的可见进度保留，而不是放宽提交授权。调用的出生版本较旧，并不直接证明完整输入已经失效；若冻结输入及依赖路径得到确认，可以继续保留完整 ASR → Correct/Update 调用。最终仍使用原始完整结果及其原有选择关系，不能把预测升级为权威状态。

另一个新增动作在 Consumer：安装相同的 selected update 时，不必机械地用较短快照替换已经受支持的整个 ahead view。SUP 单独决定是否保留该视图。首页关于 producer exit 的表述还允许区分“新消息授权终止”和“之前已接受结果仍有资格”，但仅凭首页无法复述其持久化细节。

这足以解释相对粗粒度过期丢弃和计算单独保留的机制增量；不足以单凭首页宣称，相对所有既有增量计算、撤销或流式系统具有普遍的新颖性优势。

## 6. 首页能准确复述的最强比较与范围

1. **机制分解最强证据：**在预先声明的 24-speaker stratum 中，计算保留虽然改善 timely audio coverage，却使显示音频 frontier 的后退次数由 12 增至 17；联合保留为 0。它支撑“保留计算与保留交付视图是两项独立义务”。首页没有给出该分层之外的发生率，不能外推为自然流量的普遍发生率或确定性保证。
2. **服务收益最强比较：**matched four-speaker native correction study 中，同时满足 D2 和 C8 的 offered-audio coverage 从 45.2% 增至 99.2%，selected histories 不变；whole-run passes 从 0 增至 6/8。可以复述“在这组匹配原生任务实验中，服务交付覆盖明显提高且没有改变所选历史”。首页没有明确命名 45.2% 对照的具体策略，也没有展开 whole-run pass 的全部判据，所以不能进一步替作者补齐该比较的配置或含义。
3. **审计范围：**fault 与 sustained-state tests 的 3,976 个 audited transitions 中未见 illegal installation。这是有限审计结果，不是所有故障下永不非法安装的经验或形式保证。首页同时限定了 cold recovery 和 no-reset quality failures；不能复述为无条件端到端成功、文本准确率提升、恢复延迟优势或已部署负载保证。

首页的单条时间轨迹、24-speaker factorial 现象、four-speaker native 比较与 fault-transition 审计必须保持分开。它们解释不同问题，不能拼成同一个实验的全栈胜利。

## 7. 最多三个实质混淆点与短修改建议

1. **图中的 “Unknown: wait” 容易被理解成暂停调用，与后续 keep-running 框的关系不够直接。** 图注已经给出正确边界，但图内仍可能误读。建议直接替换为 “Unknown: may run/buffer; no commit”，或把 “wait” 写成 “wait for eligibility confirmation; no commit”。
2. **最强 45.2% → 99.2% 比较没有在首页明确命名两端策略，whole-run pass 也缺少一句最短解释。** 冷读者可背出数字，但不能确信是在与一律丢弃、只保留计算还是其他策略比较。建议在首次报数处补 “策略 A vs RevTrace”，并以短括号说明 pass 汇总什么条件；保留 four-speaker、8 runs 与 unchanged selected histories 的范围。
3. **AU 图框压缩了 complete、authorized sync、select/install，读者可能把它看成 EL 确认后的自动提交许可。** 首页和图注能排除“输入确认等于预测授权”，但授权来源的主语仍较抽象。建议在框中或图注用一句因果说明：“Only the original complete Correct/Update result, through its original authorized selection, may be installed.” 同时保留 EL 与 AU 不是同一判断的视觉间隔。

## 8. 是否无需口头补充即可复述“问题 → 障碍 → 方案 → 证据”

**总体可以，最强比较的对照名称仍需文字补齐。** 冷读能够形成连贯复述：可信修订会撤回尚受支持的及时进度；出生版本、预测正确性、producer 存活以及单独的计算保留都不足以统一决定工作与视图的去留；RevTrace 把完整输入资格、原始选择授权和完整视图支持分开协调；分解实验说明计算保留可能恶化 frontier 后退，匹配原生实验报告服务覆盖提升，有限故障审计与已声明失败限定结论范围。

问题与障碍已经具体，方案的三种动作也基本可区分。图内 UNKNOWN 文案与首页比较命名做上述短改后，可更稳妥地要求读者在没有作者口头解释的情况下准确复述动作边界和证据范围。
