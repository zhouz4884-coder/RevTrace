# 原生阶段交接：联合结果之后的独立判断

2026-10-29。仅本地读取已经取回的 native v8 主表、ready 机会结果、`NATIVE_STAGE_HANDOFF_FEASIBILITY.zh.md` 和冻结 bridge/service 源。没有远端读取、新推理、源码改动或论文正文改动。

**我的决定是 GO 到一个有明确停止条件的阶段 profiling / 等价性探针，暂不直接实现服务 handoff。** 当前有真实可用时序机会，值得查“重复 ASR 是否占了认证推进的关键路径”；但两完整副本已经是强容量基线，不能将少做一次 ASR 自动写成更高吞吐或 D2/C8 服务胜利。

## 已有真实结果使哪个机会更清楚

原 12 formal 中，sequential 的总信用为 18.5/66.42975 秒、joint 为 17.0/66.42975 秒；全部主 P99 目标失败。这个合计并非所有来源条件一致：

| cohort | joint−sequential，r0/r1，音频 s | 含义 |
|---|---|---|
| A | +3.5 / +1.5 | 早期 Private 进展能缓解某些首次可见延迟；尚未消除认证积压 |
| B | −4.0 / −2.5 | 两完整副本的并行认证明显强于单 Authority 的固定分工 |

joint 四次 D99 为 11.3–17.2 秒，C99 为 16.9–21.4 秒；其 Private 提前不能替代 C8。因此继续堆 Consumer/保留模块不会解决当前最明显的认证容量瓶颈。

同时，formal joint 的 130 个真实 Authority model calls 中，116 个已有**相同完整起始 cut**的 Private 结果在 dispatch 前被 controller 收到。这 116 个结果的 worker return 距 Authority dispatch 最小 42ms、中位 3.575s、最大 6.191s；其中 109 个至少提前 250ms、99 个至少提前 500ms。它证明当前 schedule 中存在实在的完整输入和时序窗口，不能用“都是版本不等、无法重用”草率否定。

但这些不是 116 个已可合法交接的候选 packet：日志没有完整有序 beam 矩阵和 ASR-stage 可变状态。很长的提前量也部分反映 Authority 已经积压，不能直接当成改进后仍存在的命中率或节约量。

116 个 ready pair 中只有 95 个 whole-end cut 相同，**不应该把 95 当成候选阶段交接的上限**。Private 的 first-beam identity 和原纠错器本来就可能选择不同后继；交接要复用的是同输入下 ASR 的完整候选阶段，并保留真实 corrector 的全部选择权，不是把 Private 完整后继直接承认为 Canonical。

## 最值得查的设计切面

现有 bridge 的 Private 完成原生 ASR 后走 identity-selection tail；Authority 则重新做 ASR，再调用原 corrector。这说明候选设计应是：

1. 一个**受保护的候选生产阶段**在完整冻结输入 cut 上做原始 ASR，产生不可变、带输入/模型/配置/音频边界绑定的完整候选 packet。
2. Private 可继续用真实 first-beam 路径生成临时后继。packet 保留下来，与它后来走出的完整 Private 后继分开。
3. 当前 Canonical 允许消费该 packet 的起始输入时，真实 corrector 使用原有全部候选、音频及顺序做原选择，再完成原尾部，产生完整闭合反馈 cut。
4. 输入不兼容、packet 缺字段、producer 不受保护、同目标/同输入不明确时，回退完整原调用。deadline 不能授权未验证交接。

这不是“把文本放进 exact-key cache”。完整 key 同效实现完全可以作为组合的简洁实现或完整组合正控；不会因此否定“跨可信修订保留候选计算，同时维持独立选择权”的应用/组合贡献。真正要证明的是哪些具体状态足以使这种阶段重用合法、它何时把计算转成合法服务，而不是宣称 hash lookup 本身新颖。

这里还不能借用 f0 的独立 FP32 Authority 保证：当前想法属于原生受控应用的阶段协议。未受保护的 Private 只能输出临时内容，不能因为起始 key 相同就让其 beam 获得可信写入权。若 producer 纳入保护域，这是明确的新保护/执行边界，需单独声明和测试。

## 为什么应先 profile，而不直接写 handoff

原始 corrector 入口有一个有价值的切面，但不是现有 `export_cut()` 支持的闭合边界。它前面已改动音频缓冲、context/tokens、alignment cursor；后面还有 None/fallback、追加/retokenize 和 cleanup。现有完整调用日志无法恢复完整 candidate packet。

因此先以固定原四源、原选择规则做一个有界探针，收集以下东西：

- 在真实 corrector 入口，捕获完整有序 beam、真实 token 长度、完整音频/状态依赖及 `is_last`/fallback 所需字段，而不只捕获 top1 文本。
- 设备同步的 ASR-stage A、corrector/完成尾部 C、stage snapshot/复制/传输/匹配 H；它们必须来自同一原调用。现有 Authority 总时长约 0.77s、Private 总时长约 0.48s，不能直接相减称为 C。
- 同实际输入、重复调用及原完整调用对照：候选矩阵/顺序、corrector 真实输入、选择 token/text、完整闭合输出 cut；覆盖 empty、corrected、unchanged、None/fallback 和 terminal，而不只选全量成功路径。
- 在原 missed frontiers 的关键路径上定位 A、C、排队与收发。只报告平均 A/C 不足以说明 D2/C8 会改善；当前存在 4.79s 的完整 Authority 调用，应知道长尾究竟属于哪一段。

若没有新的合法阶段类型、完整 tail 消费依赖和实际等价对照，不要把中间状态伪装成现有 closed cut。可以明确地做受控 author-function split，但必须保留原整函数基准和等价证据，不能声称整函数仍原样执行。

## 两完整副本造成的容量约束，需要正面解决

在理想均匀任务下，两完整副本容量为 `2/(A+C)`，固定一张卡做 A、一张做 C 的容量为 `1/max(A,C)`；后者不大于前者。未命中、传输和验证只会增加成本。所以**固定分卡阶段流水线不能以“少做重复 ASR”为理由，承诺在多会话饱和负载下普遍胜过两完整副本**。

但这个容量关系不否定两类有限机会：

- **单个热点反馈链/低复用并发的延迟窗口。** 同一会话下一步依赖 corrector 反馈，两完整副本也不能无条件并行其完整下一步；合法推测候选可能把串行关键路径从 A+C 向 max(A,C) 推进。500ms 更新时，单会话稳定推进至少需要有效 A、C 各自加必要开销低于 500ms。当前数据尚未实测这些阶段，所以这是 profile 的可检验条件，不能宣布可部署。
- **保留两完整执行能力的机会式交接。** 不把两 GPU 永久锁死成 A/C；有完整合法 packet 就消费阶段结果，无 packet/高压力时保留完整调用。这样才可能同时争取单链重叠和多会话容量，但实现复杂度、额外推测及调度干扰必须真实计入，不能称为免费不回退。

若 profile 显示只有更复杂的动态平衡、多进程 mutable-state 复制或模型训练才能产生收益，当前应停止这个扩展，将 native 作为真实反馈机制确认和明确容量边界，避免把整篇论文绑到尚未完成的新执行系统。

## 必须有的强对照，以及实现 GO 的条件

当前 sequential 在完整 corrector 返回后才交付认证内容。对 handoff 的服务价值，除现有两完整副本外，还应考虑**两完整副本在 ASR 阶段完成时就交付合法临时 top1、再沿原 call 做 corrector**的轻量强对照。它不做未来 chunk 推测，但能分离“提早公开本来已算出的内容”与“跨反馈保存未来候选并免去重算”。不能仅因为原 sequential 不早显，就把所有提前显示收益归给 handoff。

真正值得实现的条件应同时成立：

1. 固定来源上的完整阶段数据可以构造成保护域内合法 packet，并在原 corrector 选择与完整闭合输出上通过严格同输入/重复/原调用对照。
2. 有相当数量**在原服务关键路径上**的可消费 packet；测得可免除的 A 大于 H/匹配/队列扰动/回退成本。现有 116 ready 只是找这些候选的起点。
3. 同等资源下，至少有一个事前说明的真实服务区间有望改善 D2/C8/认证推进，而不是仅降低总调用次数。需同时保留单热点链与原双流容量边界，不能按结果只报告前者。
4. 保留原纠错选择、全部 offered、质量、能耗与同输入完整结果检查。纯完整 key 的完整组合若同效，使用它作正控；独立选择与跨修订保留的组合解释仍成立。

我的当前建议是：**有意义地补一轮小 profiling 和阶段接口等价检查，结果好再实现；不立即启动新 serving 网格，不为追 seq 总信用排序而改来源、质量或取消规则。**

## 本地证据入口

- `final_native_v8_evidence/native_postanalyses_v8/primary_quantiles/SUMMARY.json`，SHA256 `600749f68a19d403a7e1419c55ed791155929b2d856f37d2e53dee72096f4254`。
- `final_native_v8_evidence/ready_opportunity_v1/SUMMARY.json`，SHA256 `2fdb160fbfabd4552dd96354d23c4dc5df878169b69d98377a305408d24cef8b`。
- `final_native_v8_evidence/native_campaign_v8_continuation_auditfix_v1/SUMMARY.json`，SHA256 `84b04f0e16dcf8ff7cc42aba66c8f86b8d41e6e1b56e9e3f048edbb0c332709b`。

上述三件均已用本地 `IMMEDIATE_COLLECTION_MANIFEST.json` 与当前字节核实；没有为本备忘录重新读远端。数字按 formal-only 重算，未把两 witness 的 285/384 全局数量当作 formal 数量。
