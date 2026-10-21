# T1：修复后 factorial 与前置等待归因

正式实现：T1 v4，commit `e73115c66d42a15fc3a6907e7161e37ea5e07662`。
Qwen3-ASR-1.7B，双 RTX3090，一个 FP16 proposer worker、一个 FP32 authority worker；c16、fine=2s、rho=1/3、相同 12 源/16 槽、同步到达、256-token 预算、durable group-ready WAL。

## 决策与主结果

12 个正式单元及 6 个仪表开销控制均完成。独立证书/WAL/时钟/A/B/C 审计通过；每个 rho 内，9 个配置/重复的完整规范化 canonical 提交内容一致，不只是终态相同。这里的规范化比较含父版本、音频区间、事务 ID、Z 与 P；不同配置的 contract/runtime digest、跨会话交错及私有失效版本计数不要求字节相同。各自 WAL 的全字段重放另行通过。

下表是每配置三个运行中位数，P99 使用相同 q=2s 加实际末端的合法显示/持久提交前沿，不是只对完成的 display events 求分位数。

| Authority | Private | xRT | GPU J/audio-s | 合法 Display P99(s) | Commit P99(s) |
|---|---|---:|---:|---:|---:|
| Fine | Barrier | 10.089 | 44.273 | 15.035 | 16.015 |
| Fine | Decoupled-Lazy | 10.266 | 44.973 | 8.311 | 14.972 |
| Coarse | Barrier | 12.516 | 32.359 | 6.965 | 8.740 |
| Coarse | Decoupled-Lazy | 12.765 | 32.028 | 5.237 | 8.543 |

按同 repeat 配对后再取中位数：

- Coarse/Fine 吞吐比：Barrier **1.2405×**（1.2378–1.2451），Decoupled **1.2463×**（1.2294–1.2921）。
- Decoupled/Barrier 的 Display P99 降低：Fine **44.65%**（36.33–45.31%），Coarse **22.44%**（19.14–24.81%）。这不是上表中位数直接相除。
- Decoupling 吞吐比中位数 Fine 1.0175×、Coarse 1.0222×；Fine 单次有 0.9835×，不能写每次都更快。Fine 的配对 GPU 能量中位数增加 2.24%，不宣称全维度支配。
- Coarse 相对 Fine 的配对 GPU 能量降低约 26.97%（Barrier）和 28.93%（Decoupled）。当前点全部错过 2s display P99，不作为容量通过点。

质量按唯一源计，复制槽单独查一致性：Fine 英文 17/554，Coarse 18/554；两者中文 16/637。不同 rho 改变声学切分/条件输入，不作跨 rho 原始 token 相同要求。

## 完整时钟，而非把所有事情都叫 GPU 排队

实际链：audio release → parent/input eligibility → enqueue → worker started → preprocessing → synchronized model call started/completed → worker completed → owner received → certificate → WAL write/fsync → installed → canonical publication → install ACK。

GPU model-call 区间含自回归发射循环，不是逐 CUDA kernel busy time。模型预处理与解码不被冒充模型执行；同一批的 duration 只计一次，不能把 16 个 row span 相加当 GPU 秒。

以 r0 的 Decoupled 为例：

| 阶段中位数(s) | Fine | Coarse |
|---|---:|---:|
| common-frontier Ready→Enqueue | 0.570 | 0.025 |
| Enqueue→worker start（job 口径） | 0.0084 | 0.0106 |
| worker preprocessing（job 口径） | 0.2768 | 0.3414 |
| Enqueue→GPU model call | 0.2848 | 0.3597 |
| GPU model-call service | 2.0022 | 2.8519 |
| owner receive after worker completion | 0.0050 | 0.0059 |
| owner WAL call | 0.0243 | 0.0232 |

同批 row 量化会重复同一 service span；表中明确是 job 分布，不据此算设备利用率。去重实际 batch 后，r0 Fine 有 **21 个 authority batches、46.104s worker service、40.275s model-call service**；Coarse 为 **8 batches、22.814s、20.164s**。相同到达窗口 40.295s，Fine 的有限窗口服务需求已超过该窗口，Coarse 明显较低。它解释了占用/前序依赖的压力，不是“状态锁快了 18×”或稳态利用率估计。

完整 P50/P95/P99、每次运行的实际批大小、模型/worker 数及条件 run/source-cluster bootstrap 区间在 JSON/CSV。最大 batch=16，不代表每批都恰好 16；r0 authority 实际批大小 Fine 包含 16/11/6/2，Coarse 包含 16/13/3/2。

## 重叠占用与合法 CPU 反事实

独立区间重建不调用生产 `_ready()` 来猜原因。原始位图保留 self-inflight、commit-pending、真实 barrier gate、worker capacity、其他会话工作、owner WAL call、physical fsync 和 UNKNOWN。完成通知已观察到至首 row 接收间的容量释放边界有不确定区间，不补零。

以“尚未派发 authority target 的等待秒”归一化，三个重复的中位数：

| 配置 | Self in-flight | Worker capacity occupied | 自身 model-call 与 capacity 同时占用 |
|---|---:|---:|---:|
| Fine-D | 97.51% | 97.24% | 86.09% |
| Coarse-D | 74.29% | 93.05% | 68.99% |

分母是**target-wait seconds**，不是 GPU wall。不同标志重叠，不能相加，也不能把优先级 partition 当因果份额。

新增六配置、各两重复的合法 CPU 调度反事实全部通过：

1. 一个会话增加空闲 authority worker，不会缩短它的父状态依赖链等待。
2. 两会话、microbatch=1 的首转移，增加 worker 能消除等别的会话释放设备的等待。
3. 快 authority/慢 private 的 Barrier 可以在 GPU 结果已返回、worker 已空闲后继续等私有终端结果；Decoupled 无此 gate。

这些是 Fake Clock/Fake Executor 控制，不是 GPU 加速数字。它们证明多类原因可独立存在；当前 GPU 中多数等待同时具备前序依赖和资源占用，不能量化成一个“纯状态 HoL 百分比”。

## 仪表修复前后

v2 的富输入 JSON 在 owner 循环内同步写盘；v3 将不可变记录移至 serving/power 区间之后；v4 再把 worker 预处理、同步 model-call、后处理和 owner 接收分开。三版全部原始数据保留，最终表不拼接旧版本。

v4 matched rich-observer on/off 吞吐比中位数 Fine 0.9954×、Coarse 1.0065×。两臂仍共享生命周期 CUDA/IPC hooks，因此这组只校准富输入/等待观察器，不能单独宣称全部时钟零开销。Fine 单次 Commit P99 可相差 +8.37%、Display P99 可到 +16.88%。完整 hooks-off 成本另做 12-cell 校准，A/B/C 在两臂保持启用；最终数据见追加校准结果与 `INDEPENDENT_CALIBRATION_AUDIT.json`。所有控制值和下降尝试保留，主要归因在相同仪表 carrier 内比较。

证据：`T1_V4_INDEPENDENT_AUDIT.json`、`T1_FULL_HISTORY_EQUIVALENCE.json`、`T1_BLOCKING_SUMMARY.json`、`CPU_BLOCKING_COUNTERFACTUALS.json`、`tables/T1_*`。服务器 publication 时间不等于网络投递/浏览器绘制时间。

## 全 hooks 成本结项

补充 12 个完全开/关诊断 hooks 的同输入配对单元，保留 A/B/C。off 同时去掉新生命周期 CUDA 同步标记、IPC status、富 enqueue/WAL 诊断、等待观察器和输入捕获；不是拿旧的有缺陷机制当“零开销”基线。全部规范化提交历史一致、独立证书/WAL/显示审计通过。

on/off 吞吐比的配对中位数 Fine **0.9870×**、Coarse **0.9994×**，通过预注册 5% 吞吐开销门槛。Display P99 比为 1.0051/1.0157，Commit P99 比为 1.0487/1.0063；Fine 单次 Commit 比最高 1.0541。完整时钟有可测开销，不把它称为严格无扰动。最终 factor 表保留仪表 carrier 条件；不从百分比中机械减去校准开销。

## 当前可见与历史覆盖

独立可见性重建保留了真实 correction 的代价：Fine-D 三次有 77/61/77 次音频前沿回撤、canonical correction 擦除字符 2069/1732/2135；Coarse-D 为 2/2/15 次及 529/529/730 字符。Barrier 没有音频回撤，但依然可有文本修订。故 `D_ever` 不能代替当前可见版本，first-display P99 不能表示连续可见或“零闪烁”。字符/前沿量是 server event 代理，不是人类感知评价。

`audit_text_projection.py` 从选定 Z 和冻结 parent 独立重建 Phi 与实际文本，并同时对照 canonical publication/WAL text。T1 3393 个转移全部通过；此 CPU 复算不算新增 GPU 运行或神经执行 attestation。完整生命周期、可见性和退休 model-call 工作见 `tables/T1_STAGE_QUANTILES.csv` 与 `tables/VISIBILITY_AND_RETIRED_WORK.csv`。
