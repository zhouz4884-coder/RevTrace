# F1 / F2 / F6 概念图内容简报


## 论文内容速览（图的上下文）

一句话论点：流式修订生成系统（Whisper、Qwen 这类"输出会改写下一轮输入状态"的
serving）里，普通的瞬时输出差异本来只是显示层面的局部差异，但一旦经过反馈边
（本轮输出进入下一轮读取的状态），就会变成永久性的状态污染。

核心证据（因果干预）：21 个合法状态对中，8 对在反馈边存在时传播差异，
去掉反馈边后 0 对传播；持续传播的 6 对上尾部 RAF（轨迹放大因子）实测最高 153。

方法 DGFT（Dual-Granularity Feedback Transactions）：细粒度提案只负责显示，
粗粒度典范权威负责状态写入；任何状态投影只能作为带证书的事务进入状态。
ρ = g_a/g_p（权威粒度/提案粒度）≥ 1；SG 是 ρ=1 的退化情形。

系统 RevTrace：family adapter + 版本化 ledger + 分层认证，三组件事务运行时。

理论保证：Thm 3.1（未认证投影不能进入已提交状态的祖先链）、Thm 3.2（已提交
状态线性化，依赖原子提交）、Prop 3.7（权威成本分解，端到端
T_service ≈ max(T_p, T^a) + T_repair）。

---

## F1 — 问题对照图（Section 2 开头，label `fig:motivation`）

**内容**：同一场景两幅面板。
(a) 普通 batching：音频修订 → 批内提案出现局部差异 → 差异输出被显示 →
该输出进入反馈状态 → 下一轮修订读到被改变的父状态 → 轨迹分叉。画面本质是
两条轨迹：canonical trunk 与 contaminated branch。
(b) 同样的场景、同样的局部差异，但在 DGFT 下：差异在显示层保留，
状态写入被拒绝；之后粗粒度权威产出证书，frontier 才前进。

**必须出现**：
- 反馈边本身——本轮输出 Y_t 进入下一轮反馈子状态 H_{t+1} 的那条路径，
  这是全图的主角。反馈子状态的具体形态：Qwen 是 rollback prefix，
  Whisper 是 previous-text prompt（若画实例可用其一）。
- 面板 (b) 中状态入口处的判定语义："PROVISIONAL DISPLAY ok / STATE WRITE denied"。
- 角注证据行："8/21 legal pairs propagate with feedback; 0/21 without;
  tail RAF up to 153 measured on the 6 persistent pairs"。

**突出**：
- (a)(b) 的差异不在输出是否一致，而在"未认证的输出是否成为未来状态的父"。
  这是图的核心信息，也是 caption 的原句。
- 8/21（21 对因果干预实验）与 RAF 153（6 个持续对上实测）是两组不同的实验，
  角注里要让读者看得出这不是对 21 对统计出来的 153。

---

## F2 — 架构 + 提交时间线（Section 4 开头，label `fig:arch`）

**内容**：上下双面板。
上面是架构：细提案通道（fine proposal lane）、证据适配器（evidence adapter）、
粗典范权威（coarse canonical authority）、证书/账本（certificate/ledger）、
反馈状态（feedback state）、临时显示面（provisional display surface）。
下面是提交时间线：细修订 p1–p3 与其临时显示、粗权威覆盖同一段 frontier、
证书消费、父版本检查、提交或选择性重放（selective replay）、
陈旧后代失效（stale-descendant invalidation）。

**必须出现**：
- 四个协议性质标注在图上：R1 authority separation（显示权限≠状态写权限）、
  R2 parent ownership（只能提交到自己计算时所基于的父版本）、
  R3 frontier monotonicity（已提交音频 frontier 单调推进、无 gap 无 overlap）、
  R4 evidence non-authority（风险/证据只调度验证，不授权安装）。
- 证书的内容语义：cert_j = Bind(sid, e, p, v_j, [f_j, f_{j+1}), h(Φ_j^a))，
  即同时绑定父版本、frontier 区间、合同纪元/运行时摘要、典范投影摘要；
  一次性消费。图里证书与账本的关系要能读出"绑定"与"单次消费"。
- 提交是一次原子 compare-and-swap：Definition 3.3 的全部有效性检查
  （会话/纪元/策略 fence、父版本、frontier 连续、证书绑定与摘要重算、单次使用）
  与状态安装是一个不可分步骤。

**突出**：
- 显示与状态写入是两种独立权限——这是 R1，也是 DGFT 的第一性原理。
- 风险信号 / coverage witness 的箭头只指向验证调度器，**永远不指向 commit**
  （R4）。这条箭头的去向是审稿人会盯的细节。
- 原子性：检查与安装不要画成先后串联的流水线，它们是一次原子动作；
  这是 Thm 3.2（线性化、无 fork）成立的原因。
- 时间线上粗段覆盖 ρ 个细窗口的粒度关系（ρ = g_a/g_p）。

---

## F6 — 分层认证（Section 4.4，label `fig:cert`）

**内容**：四层阶梯或矩阵，每层是 RevTrace 认证层的一个 stratum：
(i) SG numerical risk：singleton 权威的随机化审计 + anytime-valid（UCB）界，
    作用域仅 SG 适配器路径；
(ii) authority implementation：合同范围内的 FP32 preflight 不变性检查
    （batch repeat、batch-vs-singleton），fail-closed；
(iii) transaction integrity：证书、版本、frontier 连续性的在线穷尽验证；
(iv) semantic quality：独立的、按 family 分开的语义质量参照。

**必须出现**：
- 每一层标注它产出的证据和它的有效范围（scope），一层一保证。
- 层与层之间的显式 "no-transfer" 分隔：任何一层的证据不得用于授权另一层
  范畴内的安装决定。

**突出**：
- 图的中心信息就是"每个保证都有明确边界、不可迁移"。分层之间不是强度递进，
  而是作用域互不相交。
- 与 Table 5（9 列保证分类表）呼应：图给结构直觉，表给逐 regime 的核对。

---

## 硬性交付约束（与画法无关的工程口径）

- 三张图都是 `figure*` 全宽插图（elsarticle review 版式，目标宽约 17–18 cm）。
- 矢量交付（PDF；可另附高分辨率 PNG 预览）。
- 图内文字字体需嵌入，PDF 不得含 Type 3 字体——正文已因该问题换 Latin Modern，
  图是最后一道防线。
- 图内文字最小字号建议不低于 7 pt（与 F3–F5 数据图口径一致）。
- 图内术语以正文为准：feedback sub-state H_t、certificate/Bind、committed state、
  frontier、authority、R1–R4。若需核实用词，直接看
  `Paper/sections/02_model.tex`、`03_dgft.tex`、`04_system.tex`。
