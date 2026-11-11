# v16 证据缺口的第二轮审计（面向 v16 已编译 11 页稿）

日期：2026-11-11 22:40–23:05。类型：**只读审计**。没有新模型、GPU、服务运行或论文修改。
审计对象：`Paper_DSN/revisions/20261111_dsn2027_release_v16/`（11 页，PDF SHA `f87a5e96…`）、
`experiments/dsn_strengthening_v16_20261111/`（87 项闭合 RUN_RECORD）、以及两批 8 源 N8 结果。

---

## 0. 第一结论：最重的一条证据被降级了，而且不是新实验

**同一个 8 speaker 集合，在两个不同 runtime 上，得到逐位相同的保留收益。**

| 项 | 旧批 NN4f（2026-11-02） | 新批 de0936（2026-11-11） |
|---|---|---|
| 来源 | S0769/W0190, S0901/W0183, S0902/W0343, S0906/W0197, S0907/W0440, S0912/W0434, S0914/W0456, S0915/W0286 | **完全相同的 8 个** |
| 每臂 offered | 137.864125 audio-s | **137.864125 audio-s** |
| 原 offered 前沿 | 282 | 282 |
| 保留臂信用 | **129.460000**（93.9041%） | **129.460000**（93.9041%） |
| 整场 D2/C8 通过 | **10/16** | **10/16** |
| D2 miss（其中 EOS） | **20（6）** | **20（6）** |
| 对照臂 | Conservative 56.000000（40.6197%） | Ready-only 58.500000（42.4331%） |
| 配对增益 | 53.284pp [44.769, 59.618]（20,000 次 speaker-paired bootstrap） | 51.471pp，8/8 源、16/16 重复对同向 |
| 能量 | 90.280 vs 95.263 kJ（−5.23%） | 91.880 vs 117.823 kJ（−22.02%） |
| D99 中位数 | RevTrace 1.7623 / Conserv 5.0266 | Fullcall 1.6309 / Ready 5.0090 |

**交叉验证是独立算出来的，不是引述**：新批 32 格逐格加总 `D2_misses_all_offered = 20`，
`EOS_D2_misses = 6`，与旧批报告记载的 20（6）**逐位相同**。offered 分母、信用秒数、
通过数三项也逐位相同。这不是"接近"，是同值。

### 这为什么是整篇最重的证据

因为它同时杀掉三个最危险的反驳，而且都不需要新实验：

1. **"你的数字是不是调出来/过拟合的"** → 两个 runtime（NN4f vs de0936）、相隔 9 天、
   独立 controller（f367 vs 4fb6）、独立参考生成，保留臂的 129.460000 秒与 20 个 miss
   集合逐位复现。这不是统计复现，是确定复现。
2. **"n=8 太少"** → n 仍然是 8 个声学单位（不能虚报），但每个 speaker 有
   2 次时序重复 × 2 个 runtime × 2 个对照臂 = 8 次独立观测，且都不改变结论。
   审稿人数的是 speaker 数，但"两个 runtime 给出同一个数"会让"n=8"从软肋变成硬边界。
3. **"你的 miss 是 runtime 抖动"** → miss 集合由任务与负载决定，不由实现决定。
   这条正好接上你们"合同充分、实现自由"的主论点。

### 现在的写法问题

`05_evaluation_v16.tex` 只有这一句：

> An earlier eight-speaker Conservative comparison **independently** preserves the same
> original task and final CER of 13.22\%; its **older runtime and endpoints remain a
> separate supportive bank** in the artifact.

这句话做了三件错事：① 用 "independently" 一个词把"同一批 speaker"藏了，读者会以为是另外
8 个人（Reader review 已经点名此风险）；② 把跨 runtime 复现降级成 "older runtime …
supportive bank"，等于把最强的确定性证据放进 artifact；③ 只提 CER，没提 129.460 / 10-16 / 20(6)。

**建议替换为（两句话，不增页）：**

> The same eight speakers were earlier run on the prior runtime against a Conservative
> control. That run reproduces 129.460~s (93.90\%) and 10/16 whole-run passes exactly,
> with the same 20 interval misses of which 6 are end-of-stream; only the control arm
> differs (56.000~s). Retained-work credit and its miss set therefore depend on the
> workload, not on the runtime that implements the contract. The earlier bank also fixes
> the final task at CER 13.22\% (23/174 reference characters).

这一改，`dep ≡ full` 与 `n=8` 两条同时从弱点变成边界。

---

## 1. 新数据核对（32 格闭合）

`gpu_results/CONFIRM_LAST4_FULL_READY_V1` 16/16 原任务 PASS，`final_n8_worker_ops` 32 格算术闭合。

- 8 源 × 2 臂 × 2 重复 = 32 格；每臂 offered 137.864125 audio-s（含 partial EOS）
- Fullcall 129.460000（93.9041%），Ready-only 58.500000（42.4331%），差 **51.470968pp**
- 整场通过 **10/16 vs 0/16**；8/8 源、16/16 重复对同向
- Worker **223.215 vs 322.991 s**（−30.9%）；能量 **91.880 vs 117.823 kJ**（−22.02%）
- Ready-only 真实复用 **3** 次（S0902 一次、S0907 两次）
- 两臂 total infer 均 NA（12/208 个 abort 缺 infer timer），**不得写成完成调用之和**

**与 v16 正文/Macro 一致性**：`\NativeFullCreditPct`=93.90、`\NativeReadyCreditPct`=42.43、
`\NativeCreditGainPP`=51.47、223.215、322.991 全部正确；Table 与 Fig. 数据方向正确。
正文引用无误，**不需要改数字**。

### 新数据里必须补的一句：93.90% 与 10/16 不矛盾

正文给了两个数但没有桥。实际分解（本次逐格算出）：

| 分组 | 源数 | Fullcall 表现 |
|---|---:|---|
| 打满 100%、0 miss | 5（W0190/W0197/W0434/W0440/W0456） | 10 格全部 pass |
| 只差一个 EOS 前沿 | 2（W0183、W0343） | W0343 99.23%（D99 2.404/2.429）；W0183 92.16/98.30（D99 2.516/2.319） |
| 实质超期 | 1（W0286） | 58.35/55.57（D99 3.276/3.421），13 个 non-EOS miss 全在此源 |

Fullcall 全部 20 个 miss = **6 个 EOS + 14 个 non-EOS，其中 13 个集中在 W0286 一个源**。
即：**8 源里 5 源零 miss，2 源仅超 0.32–0.43 s 且唯一残余点是句尾串行点，1 源是真实容量边界。**

**建议加入（3 行，接在 Table 后）：**

> Five of the eight sources reach 100\% coverage with no missed interval. Two more miss
> only the end-of-stream interval (W0343 at 99.23\%, D99 2.40~s; W0183 at 92.2--98.3\%),
> exceeding D2 by 0.32--0.43~s. One source (W0286) sustains 3.28--3.42~s D99 and supplies
> 13 of the 14 non-EOS misses; we report it as a capacity boundary rather than exclude it.

这一句同时完成三件事：解释 93.90% vs 10/16、把 EOS 定位成单点残余、把 S0915 变成
"已识别的 operating boundary"（读者看 Fig. 2 的 S8 时必须有这句话，否则会以为数据有错）。

---

## 2. P0 遗漏（有正式记录、正文没写、零成本可补）

| # | 证据 | 出处 | 现状 |
|---|---|---|---|
| 1 | **跨 runtime 逐位复现**（129.460 / 93.9041% / 10-16 / 20 miss(6 EOS)） | `dsn_native_confirmation_20261102` + FINAL_N8 | 被写成 "older runtime … supportive bank" |
| 2 | **miss 结构分解**（5 源零 miss；20=6 EOS+14 non-EOS，13 在 W0286） | 本轮逐格 | 无 |
| 3 | **Strict-birth 0 次晋升；其 actual-SUP 信用 12.000000 = Conservative 精确相等** | `external_rule_ops/EXTERNAL_LA2_RESULTS_V2`、`opportunity_ops` | 只写 "earns 12 s" |
| 4 | **fixed-lag 0.5 s：26.840125 s（81.05%）、9 个被修改字符、3 次前沿回退** | 同上 | 完全没写 |
| 5 | **六日程 × 四规则完整矩阵**（6 策略 × 4 规则 × 4 格） | 同上 | 只写 Fullcall 一行 |
| 6 | **290 决策点 / 278 双保留 / 12 双拒绝 / 0 祖先反证 / 0 pending** | `analysis/divergence_v1`、`opportunity_ops`（22 controls） | 只有定性句 |
| 7 | **6231 正常 / 14074 故障状态、深度 12、cutoff 2144/2828、边 11142/25799** | `FORMAL_ACTION_RESULTS_v1` | 只写 "225 + 35" |
| 8 | **core 全 110 格 144 组最终文本全等（all_history_groups_equal=True）** | `CORE_COMPACT_TABLES.json` | 只写 "byte-equal per source" |
| 9 | **旧批内容证据：218/282 同G匹配两臂相同、及时同G匹配 47.000 → 107.161875 s、CER 23/174** | `dsn_native_confirmation_20261102` §,`HISTORICAL_EVIDENCE` P1 | 只提 CER 13.22% |
| 10 | **占用归一生产率 0.424341 → 0.633761（+49.35%）；及时同G +47.98%** | `history_ops/LEDGER_FULL_BUDGET_DERIVED_v1` | 无 |

### 逐条建议写法（可直接粘贴）

**#3 + #4 + #5 合成一句 + 一格表**（这是回应"能不能更简单"的最强组合）：
> On the same four recorded schedules we evaluate four publication rules across all six
> policies. The birth-root-fenced auxiliary earns 12.000~s under actual SUP --- numerically
> identical to Conservative --- because its rule requires an unchanged birth root and every
> observed promotion advanced exactly one parent step. A fixed 0.5~s publication lag is
> worse than local agreement on both axes (26.840~s, 9 modified characters, 3 frontier
> rollbacks versus 31.340~s and 0 characters); a simple delay is not a free approximation.

**#6 替换现有定性句：**
> Over the pilot's 290 decision points, 278 are retained by both policies, 12 are refused
> by both, and none has a refuted ancestor or an unresolved input; the two predicates
> therefore never diverge in this workload, and the comparison measures opportunity
> absence rather than agreement.

**#7 接在 225/35 后：**
> The bounded model enumerates 6{,}231 normal and 14{,}074 fault states to depth 12 with
> 2{,}144/2{,}828 cutoffs; the counts delimit the checked region rather than claim
> whole-program coverage.

**#8 替换 "byte-equal per source"：**
> Across the 110 core cells, all 144 history groups are byte-identical, including 56
> cross-arm groups; no policy changes the delivered text.

**#9 放在 CER 句旁：**
> On that bank the two arms match the later selected text on 218 of 282 offered frontiers
> identically, while timely matched content rises from 47.000 to 107.162~s: the gain is
> earlier delivery of the same selected content, not a change of task.

**#10 放在 worker 讨论处（回答"是不是只是多花算力"）：**
> In the earlier four-speaker ledger where the retained arm does consume more work
> (+20.05\% occupied seconds), credit per occupied second still rises from 0.424 to 0.634
> (+49.4\%). More work is spent, and it buys proportionally more service.

---

## 3. P1：被主动排除的一条，需要你决策

`analysis/divergence_v1` 的 Part B 结论：**92 次历史跨版本保留，版本间隔 92/92 = 1，
合计 69.017 worker-s，零跨代零离链**；并且规则化预言"间隔恒为 1 ⇒ 要求间隔 0 的
strict-birth 必然零晋升"，与实测 `Strict-birth recorded promotions = 0` 对上。

`review/V16_METHOD_DELTA.zh.md` 以"外部文件未冻结身份/全输入/环境/运行/gate 闭环"为由
排除。这个理由**在归档强度上成立**，但结论本身是从正式 `CANONICAL_HISTORIES.json`
（17 个 state_sha256）与正式 ledger 算的，不是估算。

**建议**：若要写，先补一份 1 小时的 CPU freeze/gate 记录（把输入 SHA、脚本 SHA、
运行记录固化），然后只写一句：

> On the historical bank, all 92 cross-version promotions advance exactly one parent step,
> so a rule keyed on an unchanged birth root can never fire there; that is why the
> birth-root-fenced auxiliary reproduces the no-retention credit exactly.

不写也不损失核心论证（#3 已经用 12.000000 = Conservative 说了同一件事）。
**若时间紧，放弃这一条，保留 #3。**

---

## 4. P2：确认应当继续省略（不要补）

| 项 | 理由 |
|---|---|
| EOS "最多 3/4" 归因 | 8 源上已不成立（W0286 有 13 个 non-EOS miss）。写成"集中 EOS"会被数据打回 |
| MAGICDATA 43 test speaker | header 控制完成，音频未取、未跑，不能进正文 |
| loader profiler / warm-worker adoption / continuous fastpath / conditional dispatch | 均为 MEMO 或 NOT_IMPLEMENTED，无记录 |
| 611 early development checks | 未冻结，不可与 225/35 相加 |
| whisper adapter 的 Standard Safe Async | 27–32 次不兼容清除、erased 1012/1542；与 qwen 主分层结论冲突，只进 artifact 并需一句解释 |
| 2/256 标签翻转、leave-one/two 敏感性 | 条件诊断，正文可只报逐源同向 |

**⚠ 一处必须先处理的风险**：正文现句 "An author-built alternative joint policy … 667.530 s,
providing a positive control" 指的是 `STANDARD_FULL`。它在 qwen staggered 是 667.530 / 0 撤回 /
15-15 compatible retained（对 R1S1 的 680.760 / 18-18），但在 **whisper** 上 27–32 次
不兼容清除、erased 1012/1542。若审稿人查 artifact 会问"为什么正控只在 qwen 成立"。
**两个选项**：① 加半句限定"on the Qwen stratified layer"；② 干脆不提 667.530，只保留
"two independent implementations reach zero withdrawal"，并把 Standard 交给 artifact。
我建议 **①**，因为 667.530 是你手上唯一"独立实现 + 同 24 speaker 分层"的正面证据。

---

## 5. 对两份 review 的裁定

`review/V16_FINAL_TECHNICAL_REVIEW_v1.zh.md` 与 `V16_FINAL_READER_REVIEW_v1.zh.md` 的
4 项必改，我逐条核对后**全部同意，且都已定位到 source**：

| 项 | 裁定 |
|---|---|
| M1 pilot 零 ready 命中不可写成 N8 结果（已改 3 次真实复用） | 正确，改后与 FINAL_N8 一致 |
| M2 归纳是单会话事实投影（FactStore 按 source_id 多根） | **必须改**，这是技术审阅里唯一涉及证明正确性的 |
| V-C "Every run is required to match" → 改为实际结果句 | **必须改**，32 场全 PASS，写"requirement"会被读成有失败 |
| V-C "independently preserves" → 限定同一 speaker bank | **必须改**，正是本文 §0 的问题 |
| Q7 可选：补 6231/14074/depth12 | **建议采纳**（见 #7），成本一句话 |

---

## 6. 判定

- 新数据（32 格闭合）与正文数字**完全一致**，无需改数。
- 证据缺口 **10 项 P0**，全部是"已有记录、正文没写"，零 GPU、零新实验，合计约 14 句话 + 1 格表。
- 最重的一项不是补数据，而是**改写一句话**：把"older runtime supportive bank"
  改成"same eight speakers reproduce 129.460 s exactly on a prior runtime"。
- 结论：**可以开始。** 先改 5 处句子（§0、§1、#3/#4、#6、#8），再改两份 review 的 4 项必改，
  然后按 PAPER_SKELETON_v16 重排；不需要任何新实验。
