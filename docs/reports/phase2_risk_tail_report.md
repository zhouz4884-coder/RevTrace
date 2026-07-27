# RevTrace Phase 2：风险约束与终态尾延迟

## 决策

Phase 2 将 Phase 1 的 deployed mechanism 分成两条独立证据线：

1. S2 已通过：固定工作负载下，terminal canonical reservation 将两个模型
   的 2 秒 deadline miss 从 5.42% 降到 0/240，同时保留 5.99x/4.97x
   双卡墙钟加速和 3.00x/2.49x GPU-normalized 加速。
2. S1 的 time-uniform 数学构造与 2,500 条漂移/可选停止模拟已通过；真实
   randomized shadow audit 的最终判定由冻结结果文件给出。

deterministic intermediate certificate 仍未解决。本文档不把 margin、零观察
违规或固定 shape 重复性描述为确定性证明。

## S2：Terminal canonical reservation

### 最终机制

- GPU 0：FP16 batched proposer；
- risky intermediate：FP16 singleton canonical verification；
- terminal：在 GPU 1 上使用冻结的 FP16、batch-size-16 canonical path；
- terminal proposer 结果仍可并发计算，但没有状态写权限；
- 每次写状态前检查 parent revision version；
- service 结束后的 canonical audit 不计入在线墙钟时间。

### 真实双卡结果

| Model | Events | Verify | Wall speedup | GPU-normalized | SLO goodput | Miss | P99 | Output/state/stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 240 | 19 | 5.992x | 2.996x | 5.992x | 0/240 | 1.336 s | 0/0/0 |
| Qwen3-ASR-1.7B | 240 | 23 | 4.972x | 2.486x | 4.972x | 0/240 | 1.652 s | 0/0/0 |

相对 Phase 1：

- 0.6B 墙钟加速提高 8.3%，P99 降低 55.2%；
- 1.7B 墙钟加速提高 4.7%，P99 降低 36.1%；
- deadline miss 均由 13/240 降到 0/240。

### 被证据否定的替代方案

| Intervention | Result | 结论 |
|---|---|---|
| 两个 FP16 singleton verifier process | 3.33% miss | 同卡多进程没有消除 terminal burst |
| 上述方案加 MPS | 3.75% miss | MPS 对冻结 workload 没有收益 |
| 1.7B FP32 terminal batch | 6.67% miss，P99 2.701 s | 数值稳定但 SLO 失败 |
| generic FP16 batch-invariant mode | 两模型均有 1/240 cross-shape mismatch | 不能声明 MM end-to-end singleton equivalence |
| FP16 fixed shape | 0.6B 通过，1.7B replication 7 次、composition 1 次失败 | 稳定性依模型、位置与子图而异 |
| FP32 fixed shape | 两模型四类检查均为 0 mismatch | 稳定新 canonical 可行，但并非旧 FP16 singleton |

S2 的关键不是把 FP16 fixed shape 宣称为全局确定性，而是将其限定为
terminal position、batch size 16、冻结 runtime 的版本化 canonical contract。

## S1：Anytime randomized audit

### 数学对象

对每个 risk-eligible state entry，以固定概率 \(p\) 独立执行 canonical
shadow audit。若 \(M_t\) 是真实累计错误数、\(S_t\) 是被随机审计命中的
错误数，则对 \(\lambda<0\)：

\[
\mathcal E_t(\lambda)=
\frac{\exp(\lambda S_t)}
{\left(1-p+p\exp(\lambda)\right)^{M_t}}
\]

是 error-event clock 上的非负 martingale。固定 mixture 经 Ville inequality
反演得到 time-uniform upper confidence sequence，允许：

- error sequence 任意漂移和相关；
- optional stopping；
- 在任意时刻检查 bound。

只允许固定、独立的 base-audit coin 进入证书。额外自适应审计只用于诊断。

### 仿真

- 30,000 entries/trajectory；
- 500 repetitions/scenario；
- zero、rare、boundary、unsafe、sudden drift 五种场景；
- 总计 2,500 trajectories；
- overall observed coverage violation 2.0%；
- worst scenario 3.8%，低于 \(\alpha=5\%\)；
- zero-caught-error upper risk 0.48%，低于 \(\delta=0.5\%\)。

Monte Carlo 是回归验证，不是理论保证来源。Wilson upper 仅保留为诊断。

### 真实 shadow audit

最终数字由以下机器可读文件冻结：

- `results/phase2/risk_v1/natural-shadow-Qwen3-ASR-0.6B.json`
- `results/phase2/risk_v1/natural-shadow-Qwen3-ASR-1.7B.json`
- `results/phase2/risk_v1/risk_metrics.csv`

必须分别报告：

- risk-eligible execution events；
- fixed base audits；
- caught proposal/output errors；
- caught state-projection errors；
- time-uniform upper risk；
- selected-state violations；
- workload 与独立样本边界。

## 证据边界

- 30k 指 execution events，不是 30k 个独立 utterances。
- c64 calibration/stress 不能替代 deployed c16 population 的独立验证。
- shadow-audit runner 的串行等待时间不是服务性能。
- `0/n` 观察结果不是 deterministic certificate。
- terminal canonical 与 FP16 singleton equivalence 不成立也不主张成立。
- fixed-shape canonical 的适用范围不能外推到其他 chunk、batch size、模型或
  runtime。

## 下一步

只有在 S1 的真实 audit 风险预算闭合后，才进入 amplification-aware
certification 和第二 revision architecture。若 uniform 2.1% audit 捕获错误并
使 bound 超出 0.5%，应冻结失败、提高验证覆盖或在独立数据上验证预注册的
分层策略，不能回填阈值。
