# Ready-only 阶段交接：有限在线试验与停止决策

2026-10-29，本地独立决策备忘录；没有启动模型、远端 CPU/IO 或 GPU，没有修改执行源。依据已完成的 stage profile、99e83a4 的全 69 神经等价、64ba03e 的旧任务保真，及当时正在开发的 source_v3 policy/controller。后者还需最终 clean freeze/CPU gate；实现存在不等于服务结果已存在。

Pilot 前解释补充：`two_full_spec_early` 是本工作作者新组装的完整输入保留+在途/完成 full 结果复用+same whole-state Consumer 实现，不是外部原作者基线。若它优于保守执行而 stage 未胜过它，可以选 full-call retention 作为 RevTrace 原生实现，不能因此宣布整个组合贡献结束。另见 `INFLIGHT_JOIN_AND_FULLCALL_INTERPRETATION_PREPILOT.zh.md`：只有实际 pilot 显示匹配在途 A 被 ready-only 重复 fallback 吞掉机会时，才评估一次有界 join；现在不加臂、不预设 stage 必赢。

## 1. 建议

**GO 一个固定 source0、三个执行臂、各一个 fresh-process 的配对随机顺序 pilot。** 先检验真实端到端机会，随后才决定是否做四个旧来源、两次 fresh-process 确认。不要因为代码写完而自动铺完整网格；不要用 GPU 再证明一次已经通过的 69 个同输入等价点。

三个臂共用输入时钟、owner、Consumer、早显语义、完整状态合同、neural-ready、指标与能耗记录：

1. `two_full_early`：两份完整原 ASR+C+U，均可在相同 ASR 边界早显，当前已确认反馈上顺序执行。保留它解释原先的保守串行代价。
2. `two_full_spec_early`：两份完整原 ASR+C+U，均可早显；空闲副本可从合法 identity projection 启动未来完整调用，只有 actual complete start cut 和 epoch 获确认后才安装。它是主要强基线。
3. `ready_handoff`：已完成的 protected A packet 仅在完整输入匹配且完整接收后命中；Authority 执行原 C/U，否则立即 full fallback。无等待、无预测 end 相等前提。

source0 固定为原 `BAC009S0764W0209`，不是从新结果挑出的最好来源。它有 17 个原调用、8.068 s offered 音频；已完成神经门中有 16 个 packet、5 个预测终点不同，作为开发 pilot 有明确的机制机会，但不叫 holdout。三臂顺序在最终 config 冻结前由固定 seed 生成一次，运行过程中不因结果修改。每臂全流程重新建进程并作同一固定 neural warmup；不让前一臂权重加载、CUDA/JIT 或 packet 缓存替下一臂预热服务状态。

## 2. 为什么值得这一个 pilot

真实 profile 的 64 次 neural C 调用平均 A=434.7 ms、C=268.7 ms，原整调用约 714.0 ms，capture 约 9.22 ms。原 cadence 每次 500 ms。若预测及 readiness 配合，A 与 C 分卡后可能把单反馈链临界路径从 A+C 推向两阶段重叠，量级足够影响 D2。**这些是实测组件值支持的假设，不是已测在线加速。** packet 编解码、queue、恢复、尾部、owner/Consumer、失配重算都必须计入 pilot。

神经门已给出更具体的合法组合证据：69 原输入中 65 个 packet 的 C 选择/IDs/完整闭合状态以及两条 identity 投影均通过，13 个预测终点不同而当前 packet 仍有效；旧任务的 69 个完整输入/输出、C/IDs/text 也在唯一 stage tag 投影后不变。这说明“当前 A 的合法复用”与“预测反馈是否猜对”可以分开，值得观察这种分离是否兑现成服务进展。它没有给出 readiness 命中率，也没有保证下一条预测链合法。

最可能的新增收益点不是泛泛的模型流水，而是：**及时保留当前合法 A；未来预测被否定时，只丢弃确实依赖错误输入的后继，且不额外占用 producer 的 learned C 阶段。** 是否实际发生、节省的时隙是否到达 Consumer，必须靠同输入事件链验证。

## 3. 强 full-spec 基线必须做到的事

单会话中若两 full 副本始终只允许一个 current-Canon 调用，第二 GPU 会闲置。赢过这个臂只能说明胜过保守顺序执行，不能直接声称优于两卡上的强并行系统。`two_full_spec_early` 必须有实际可用的第二卡机会：

- 接到真实 ASR identity projection、目标音频已 offered 且有空闲卡后，可从 projection tail 发起下一完整 full 调用；不只等当前 learned C 完成后再派发。lookahead 不大于 handoff 的相同冻结上限。
- 每个 speculative full job 保留其真实 worker/job、birth Canon/epoch、完整 start cut 及依赖链。完成可缓存，但只有实际父输入相等才安装；预测 end 不同不能直接使它在其真实输入上的原 full 计算非法。
- 当已有在途 full job 的完整 start 被新 Canon 确认，它应可提升为当前 Authority 的在途工作，等待它真实完成；不能故意重复跑另一份 full 调用以削弱基线。已完成且输入确认的 full 结果应尽早 WAL/install/Consumer，而不是再付一次 C。
- **A-ready 时已被真实证据确认无用的 C 可以省。** 原 full worker 在原 C 入口可读非等待的 owner cancellation/invalidity 标记：若任务自身完整 start 的同 frontier cut 已被 Canon 明确否定、任务已覆盖或 epoch 已失效，可返回明确的 abandoned job，清理后转向 fallback。更早祖先失配只剪失去支持的可见链，future complete start 尚可能收敛时继续计算，不把它当成普遍不可能。该 abandon 分支没有 C/U 输出或 certified cut；成本仍计入实际服务/能耗。
- “未来父输入尚未被确认”不等于“已经错误”。尚可成为合法根的 spec job 不能被人为提前放弃；同样不能明知起点已经不可能成立还强迫它做无用 C。invalid 标记必须有实际 Canon/epoch 见证及读取时间，不能由未来 oracle 决定。

上面这些只改变共享调度/退出判断，两个 full worker 的有效 A/C/U 仍是原方法，不需新模型或额外 GPU。初版即可限制最多两个在途 full 调用、固定原 lookahead；不要求复杂的预测器、最优调度 oracle 或学习调度。

一个重要边界是：若所有预测都正确，两 full 的理想算力上限约为 `2/(A+C)`，可能高于单 ASR producer 的 `1/A`。因此不能先验承诺 stage 胜出。只有错分支造成的不可避免占用、原执行阶段的及时复用、实际内存/能耗或时序差异提供了额外优势时，服务收益才成立。A-ready 的合法取消会进一步缩小机会，这正是值得测量的强对照。

## 4. pilot 的必要记录与 gate

原 D2/C8、所有 offered frontier/audio 分母不变，不能用成功请求的条件 P99 或只含 hit 的指标代替。每臂至少记录：

- 实际 Consumer 的 first D/first C、dual-credit、全 offered P99 与缺失数；两个卡的 service energy，原加载/预热成本另列。
- 同一冻结 `content_endpoints` 定义下的全文、空/未变化显示、strict append/replacement/erase、LCP code-point occurrence churn；处理音频 frontier 不当成新增文字。
- 每个 candidate/full-spec job 的 dispatch/start/cut、完整接收及校验完成时间、原 birth、匹配或失配见证、在途 promote、C-entry cancel/continue、C/U 完成、WAL 与 Consumer publication 身份。packet 网络/编码/恢复开销不能只留 C 内核计时。
- 原完整 Canonical histories、selected C、IDs、最终 CER；三臂及旧原任务的合同投影后全状态检查，发生不等就保存失败，不以 final CER 相同掩盖。
- 每次新 deadline 命中的同-F 首次实际 Consumer 全文及其后验完整 Canon 支持，raw/冻结 whitespace normalization 分开；unknown 不改成支持，不把后验支持写成在线认证。

实现 gate 必须覆盖 physical queue 到 worker/job 的绑定、complete input/epoch、ready-only、原 birth、wrong future successor、pending full promotion、known-invalid C-entry abandon 及“尚未确认”继续。冻结 neural core 文件若与 99e83a4 相同，应记录逐字节关联；新的共享调度 source/配置/环境、全部 CPU controls 和实际 source manifest 另冻。69 结果不能被重标成新服务 source，也不要求把已证明的原神经算法再铺一遍无意义网格。

服务结束前所有 in-flight 成本计入服务窗口，不能在 Canon 最终完成时截断仍运行的错误分支成本。Canon 发布前须完成 WAL/fsync；policy 的内存 install 单独不代表持久授权。加载/固定 warmup 所有角色分别列出，两 full 的两个实际 C 都需 real neural-ready。

## 5. 有限停止/继续规则

pilot 是机会筛选，不是论文的统计确认。按以下分叉决定，禁止看到某一臂好看后追加任意相位、seed 或删掉 source。

**实现或语义失败：** 立即保留失败，先分辨 job/恢复/状态合同、调度时钟或数值原因；做原同输入和合法 oracle 控制。不重跑同一个失败 GPU scope 直到定位，也不削弱强基线来“恢复收益”。

**只有阶段粒度没有增益：** 如果 full-spec 已经消除差距，而 handoff 对它没有可解释的端到端收益，则不自动启动 stage-vs-fullspec 的 4×2 确认。冻结“本边界下阶段交接无额外服务优势”；但 full-spec 自身是本工作完整组合的一个实现，若其对保守执行有有意义收益，可优先确认它、作为 RevTrace 原生实现。正文透明说明两个作者构建的设计，不能把它误称既有外部方法，也不能称 stage 赢过 strongest full-call control。

**可能有真实优势或合理不确定性：** handoff 对 full-spec 至少新增一个完整 0.5 s offered 间隔的合法 deadline 进展，并能逐行连接 ready packet→更早 C/U→实际 Consumer；或者 dual-credit 同处天花板，但完整同-F Consumer 延迟/内容或能耗出现明显、可解释且超出普通排队/启动噪声的改善。这些只是工程筛选条件，不宣称统计显著。此时才做四个旧来源、两次 fresh-process 的 `two_full_spec_early` vs `ready_handoff` 预冻结确认；`two_full_early` 留作 pilot 的解释控制即可。

若 source0 只是运行顺序噪声或余量太接近门限，可先重复完整三臂一轮；最多这个预先限定的 repeat，再决定。若几乎没有 ready 命中，应先用事件解释“候选太晚/预测依赖失配/传输与调度吃掉余量”，不把组件加速当收益，也不直接开更大来源网格。source0 原本已有较多 end-different 点，不能无证据地靠换更有利来源续命。

确认轮以全部四个旧来源报告配对差、逐来源方向、时序重复和失败边界，不把它们包装成新独立来源。若后续真实增益足够值得独立确认，**在最终执行 source/算法冻结之后**才依音频 metadata、固定 seed、speaker-disjoint 条件选少量新来源，预先锁定清单。不读取纠错一致率或性能结果来挑来源，不训练新模型；若旧四来源确认已经否定机制机会，则新增来源数为零。

## 6. 双会话容量与论文中的创新位置

单 ASR producer 平均约 2.3 步/s；两条原 0.5 s 会话合计约 4 步/s。双会话会形成明显容量压力，而两 full 有不同资源上限。若单热链有收益，原 cohort A/B 的双会话可各做一个固定配对容量边界控制，足以验证“何时收敛/何时 stage 瓶颈显现”，不把全负载 P99 达标设为必须修复目标。不能因双会话不占优又改变 offered rate、deadline、质量或只报告一条源。

对现有“先算输入、后反馈纠错/预测验证”的先例，本文应肯定具体组合：完整真实输入的跨 Root 阶段准入，post-ASR open 状态与依赖的完整交接，真实 C/U 的原样授权尾部，以及独立且不会冒充 certified 的早显消费。其有价值之处是把当前 A 的合法性与预测终点正确性分开，并把执行保留、用户可见保留和无用分支退出连起来。65 个完整神经对照及 13 个 end-different 点支持该设计可行，旧 69 保真排除了换任务解释。

但“有保护的阶段组合合法”和“强 full-spec 面前仍有服务优势”是两个命题。若后者成立，这个外部真实反馈应用会成为有竞争力的完整证据链；若后者不成立，它仍是正面的适配与边界证据，主论文创新重心继续放在已经成立的 C1/C2 协调问题与交互必要性。既不因 primitive 有先例否定组合创新，也不因组合是作者提出的就预设其性能优越。

## 附：本地 policy 审阅

当时的 `stage_policy.py` 主路径已检查 physical worker-channel、job/source/dispatch epoch、完整 key、真实 receipt/ready 时间；Authority completion 重新核对当前 Canon 与 epoch，保留原 birth，不要求预测 end 相同。已直接向 SC 报告两个 lifecycle 收口：producer completion 同样需要当前 epoch 检查（旧 early-return job 无 projection 时不能跨 reset append），reset 后需释放旧 active-authority 占位以允许新 session 派发。若本 pilot 不使用 reset，该问题不是当前收益解释，但应在 freeze 前通过窄 CPU 控件修完。没有改 source。
