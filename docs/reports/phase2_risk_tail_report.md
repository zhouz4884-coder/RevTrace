# RevTrace Phase 2：风险约束与终态尾延迟

## 最终决策

`PHASE2_RISK_AND_TAIL_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`

Phase 2 的两个独立门均已通过：

1. S1：固定概率随机 shadow audit 的 anytime 风险上界，在两个 active
   policy 上均低于预注册的 0.5% 风险预算；
2. S2：真实双 RTX 3090 terminal-reserved revision transaction 在两个模型、
   每个模型五次运行中均通过 `<1%` deadline-miss、`>=4x` 墙钟加速、
   `>=2x` GPU-normalized 加速和零观察安全违规门。

确定性中间证书仍未解决。margin、随机审计、零观察错误和跨五次运行一致，
都不能表述为 bitwise 或数学上的 deterministic certificate。

## Active policy

- Qwen3-ASR-0.6B：FP16 proposer，intermediate margin threshold `tau=0.05`；
- Qwen3-ASR-1.7B：FP16 proposer，独立验证后的 threshold `tau=0.10`；
- risky intermediate：FP16 singleton canonical verification；
- terminal：冻结的 FP16、batch-size-16 canonical path；
- proposer terminal 输出可以并行产生，但无状态写权限；
- 所有状态写入必须通过 parent revision version 检查；
- 离线 canonical audit 不计入在线服务墙钟。

## S2：真实双卡系统结果

### 论文主运行

| Model / policy | Events | Verify | Wall | GPU-normalized | SLO goodput | Miss | P99 | Output/state/stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.6B / `tau=0.05` | 240 | 19 | 5.992x | 2.996x | 5.992x | 0/240 | 1.336 s | 0/0/0 |
| 1.7B / `tau=0.10` | 240 | 23 | 4.830x | 2.415x | 4.830x | 0/240 | 1.730 s | 0/0/0 |

### 五次真实复跑

| Model | Runs | Wall mean +/- 95% CI | Wall min | GPU min | P99 max | Miss/output/state/stale | Cross-run output/state mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.6B | 5 | 6.052 +/- 0.128x | 5.935x | 2.967x | 1.582 s | 0/0/0/0 | 0/0 |
| 1.7B | 5 | 4.949 +/- 0.102x | 4.830x | 2.415x | 1.730 s | 0/0/0/0 | 0/0 |

五次运行不是同一 JSON 的复制：每次都重新启动真实 proposer/verifier 服务并执行
240 个 live revision events。跨运行 full-trace 与 terminal-trace digest 各只有
一个唯一值，说明在冻结 workload、模型、runtime 和策略内观察到完全一致的输出
与状态轨迹。

## S1：Anytime randomized audit

### 数学对象

对每个 risk-eligible state entry，以固定概率 \(p\) 独立执行 canonical
shadow audit。若 \(M_t\) 为真实累计错误数、\(S_t\) 为随机审计命中的错误数，
对 \(\lambda<0\)：

\[
\mathcal E_t(\lambda)=
\frac{\exp(\lambda S_t)}
{\left(1-p+p\exp(\lambda)\right)^{M_t}}
\]

是 error-event clock 上的非负 martingale。固定 mixture 结合 Ville
inequality 反演得到 time-uniform upper confidence sequence，允许错误序列任意
漂移、相关和 optional stopping。只有固定、独立的 base-audit coin 进入证书；
自适应额外审计仅用于诊断。

### 2,500 条漂移仿真

- 30,000 entries/trajectory；
- 500 repetitions/scenario；
- zero、rare、boundary、unsafe、sudden drift 五种场景；
- overall coverage violation 2.0%；
- worst scenario 3.8%，低于 \(\alpha=5\%\)；
- zero-caught-error upper risk 0.48%，低于 \(\delta=0.5\%\)。

Monte Carlo 是实现回归，不是理论保证来源。

### Active natural shadow audit

| Model / policy | Eligible | Base audits | Unique jobs | Caught output/state errors | 95% anytime upper | Decision |
|---|---:|---:|---:|---:|---:|---|
| 0.6B / `tau=0.05` | 30,025 | 660 | 209 | 0/0 | 0.480% | PASS |
| 1.7B / `tau=0.10` | 30,155 | 597 | 204 | 0/0 | 0.478% | PASS |

这里的 30k 是 repeated natural execution events，不是 30k 个独立 utterances；
unique job hash 只有 209/204。证书允许事件相关，但数字不能被写成独立语音样本量。

## 失败、定位与合法修复

### c64 calibration 只暴露边界，不替代部署验证

| Model | Eligible | Base audits | Caught state errors | Upper risk | Decision |
|---|---:|---:|---:|---:|---|
| 0.6B | 30,864 | 661 | 1 | 1.630% | FAIL |
| 1.7B | 30,068 | 651 | 0 | 0.479% | PASS |

0.6B 捕获错误 margin 为 0.078125，位于冻结的 `(0.05,0.10]` 层。这证明
`tau=0.05` 不是跨并发度的确定性安全边界。c64 结果只用于 calibration/stress，
不能替代 c16 deployed population 的独立审计。

### 1.7B c16 v1 真实失败

旧 `tau=0.05` 策略在 seed `20260729`、30,163 个 eligible events 和 594
个 base audits 中捕获 1 个 output/state disagreement：

- ticket：`e0116-c11-p007-t2980`；
- margin：0.0625；
- anytime upper risk：1.668%，超过 0.5% 预算；
- decision：`S1_NATURAL_SHADOW_AUDIT_FAIL`。

该策略及结果完整保留，没有删除失败事件，也没有在同一数据上调整阈值后回填成功。

### v2 独立修复

预注册修复将 1.7B threshold 提高到 `tau=0.10`，使用新 seed `20260730`：

- 30,155 eligible events；
- 597 base audits；
- 204 unique audited job hashes；
- 0 caught output/state disagreement；
- anytime 95% upper risk 0.4775%；
- decision：`S1_NATURAL_SHADOW_AUDIT_PASS`。

代价是主运行墙钟从旧策略的 4.972x 降到 4.830x，GPU-normalized 从
2.486x 降到 2.415x；五次均值仍为 4.949x，所有预注册系统门仍通过。

## 被证据否定的替代方案

| Intervention | Result | 结论 |
|---|---|---|
| 两个 FP16 singleton verifier process | 3.33% miss | 同卡多进程没有消除 terminal burst |
| 上述方案加 MPS | 3.75% miss | MPS 对冻结 workload 没有收益 |
| 1.7B FP32 terminal batch | 6.67% miss，P99 2.701 s | 数值稳定但 SLO 失败 |
| generic FP16 batch-invariant mode | 两模型均有 1/240 cross-shape mismatch | 不能声称 MM end-to-end singleton equivalence |
| FP16 fixed shape | 0.6B 通过；1.7B replication/composition 失败 | 稳定性依模型、位置和子图而异 |
| FP32 fixed shape | 两模型四类检查均为 0 mismatch | 新 canonical 可行，但不是旧 FP16 singleton |

## 证据边界

- `selected_*_violations` 原始字段只统计 mandatory/audited、最终使用
  canonical 结果的分支，不能当作全部 unaudited fast-path 的真实错误数；
  后者由 randomized audit 的 anytime bound 约束。
- shadow-audit runner 的串行等待时间不是在线服务性能。
- terminal fixed-shape canonical 只对冻结模型、chunk、batch size、runtime
  和版本成立；不外推到其他配置。
- 冻结 tokenizer 发出 `fix_mistral_regex=True` 警告。proposer、verifier 与
  baseline 使用相同 tokenizer，因此相对状态一致性有效；修复 tokenizer 会定义
  新 canonical，必须重新跑全部证据。
- 运行结束后的 NCCL process-group cleanup warning 发生在结果已落盘之后，
  属于资源回收卫生问题，不计为性能或安全失败；后续 runtime 版本应显式销毁
  process group。
- 本阶段证明的是与冻结 canonical execution 的风险约束，不是 transcript
  ground-truth correctness，也不是生产错误发生率。

## 下一阶段

Phase 2 结束，不再继续调 threshold。后续研究按冻结路线推进：

1. S3：Revision Impulse Response 与状态放大因子；
2. S4：第二个 feedback/revision architecture；
3. S5：最小 deterministic operator slice 或兼容 Qwen3-ASR 的 preventive
   batch-invariant baseline。
