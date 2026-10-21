# T3：有界交付延迟敏感性结项

Source `8916c3ccfdc2c1344316e51c145339f8120e2685`。状态：**GO：按冻结协议完成并通过独立审计**，不是启用 selector 的 GO。

在 T1/V0/V1 前置验证后，使用 unchanged independent canonical generation。9 个 scout 查合法性后冻结 45 个全新正式单元：三次重复 × 三策略 × 0/6s anchors、持续 1.5/3s、稀疏 6s。scout 不并入中位数。C3 readiness 技术 hold 在 formal progression 前解除；只停止 driver 发行，运行中的 scout 子进程未暂停。未因结果调整输入、参数或选择更好的重复。

hold 位于真实 model/worker computation 完成后的结果交付环节，原 GPU 时钟不回写。稀疏条件是 target window=4 mod6 选中整个 batch response；预先固定顺序种子 20261021，非生产随机故障率。本轮每个正式 sparse run 都恰有 3 个 held response batches、48 个 selected/held rows，collateral rows 为 0；总 proposal batch 数因策略为 12–22，不把“3 batches”说成所有策略同一比例。

## 三次配置中位数

| 条件 | 策略 | xRT | 合法 Display P99(s) | Commit P99(s) | GPU J/audio-s | 过时新发布 |
|---|---|---:|---:|---:|---:|---:|
| 0 | Legacy | 12.813 | 4.968 | 8.331 | 32.169 | 9 |
| 0 | Lazy | 12.840 | 5.024 | 8.306 | 31.793 | 0 |
| 0 | Barrier | 12.676 | 6.469 | 8.282 | 31.872 | 0 |
| 1.5s | Legacy | 8.148 | 8.220 | 8.220 | 41.089 | 231 |
| 1.5s | Lazy | 12.644 | 7.874 | 8.307 | 29.276 | 0 |
| 1.5s | Barrier | 8.134 | 25.017 | 27.251 | 42.316 | 0 |
| 3s | Legacy | 5.518 | 8.244 | 8.244 | 49.637 | 263 |
| 3s | Lazy | 12.622 | 7.770 | 8.271 | 28.012 | 0 |
| 3s | Barrier | 5.484 | 54.084 | 57.553 | 56.053 | 0 |
| sparse6 | Legacy | 9.780 | 8.287 | 8.287 | 37.344 | 215 |
| sparse6 | Lazy | 12.543 | 7.798 | 8.334 | 29.790 | 0 |
| sparse6 | Barrier | 9.764 | 19.164 | 20.794 | 37.376 | 0 |
| 6s | Legacy | 3.343 | 8.191 | 8.191 | 66.524 | 279 |
| 6s | Lazy | 11.511 | 8.228 | 8.228 | 28.945 | 0 |
| 6s | Barrier | 3.334 | 113.983 | 120.460 | 80.434 | 0 |

Legacy 是本实现的 unreconciled decoupling control，不是声称优于所有现有/native schedulers。上表不是 paired ratio；每次配对、所有范围和双 deadline grid 均保留在证据。

## 配对结果与边界

Lazy/Legacy 吞吐比的三次配对中位数：

- 0 hold：**1.0012×**，范围 0.99994–1.00212。
- 1.5s：**1.5526×**，1.53397–1.55438。
- 3s：**2.2888×**，2.27740–2.29399。
- sparse6：**1.2834×**，1.27706–1.28461。
- 6s：**3.4467×**，3.44156–3.45544。

6s 的 GPU energy 配对比为 0.4342，但它包含缩短 drain/设备驻留 idle 以及不同 private 已执行/退休/跳过工作，不解释为纯 kernel 能效提升。没有把 skipped windows 乘平均时长伪造“实测节省 GPU 秒”。真实已执行批的 model-call 区间、全部退休批与混合退休批分别记录。

Lazy 在正常点 throughput 基本持平，且 Display P99 5.024 大于 Legacy 4.968；6s 下也不是每个显示时延都优。没有宣称无条件速度支配或预设相变点。Barrier 在强阻塞下以等待维持合法性但 finalization 尾部很长；Lazy 在本测试中清除过时发布且维持较短完成周期。

## 保证与实际进展

全部 54 个 scout/formal 的规范化 canonical Z/P/音频/身份历史相同，各自 WAL 全字段重放与证书检查通过；相同源码下选择不同私有时序未改变被保护提交内容。ground-truth 分数与 Coarse baseline 相同。所有 q=2s 及精确末端都留在分母，不完成的点不得隐藏。

合法 first-publication 和 durable commit 同时达标的音频秒/Twall 是联合 Goodput；它不等于所有点 P99 通过，也不等于持续可见字幕稳定性。完整 display 2/5/8s × commit 4/8/12/16s 网格在原审计 records 中，未只挑有利 SLO。

CPU Z/parent→Phi/实际文本重建检查 **5292** 个转移全部通过。可见性重建另报当前 visible frontier、历史 ever-covered、回撤/字符擦除和 invalid-visible slot-seconds；不把曾显示过未来音频说成该音频从未被撤回。结果仅是固定 12 源/16 槽、指定注入政策下的恢复/进展测量，不是自然故障率或最大服务容量。

数据：`collected/t3_aggregates/T3_AGGREGATE.json`、`tables/T3_CELLS.csv`、`tables/T3_GROUPS.csv`、`tables/T3_PAIRED.csv`、`tables/VISIBILITY_AND_RETIRED_WORK.csv`。大型 trace/power/WAL 原件保留在 8TB 实验盘，哈希逐文件索引。
