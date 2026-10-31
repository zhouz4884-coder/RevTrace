# R1 实机补强执行完成报告

完整机器记录与所有 gate/SHA 入口：`FINAL_R1_EXECUTION_RECORD_20261031.json`。本轮完成全部已授权 **40 个真实 NN trials、54 个请求实例、918 个原始选定 C/U 状态转移核对**；主任务音频只有四个固定来源，重复与策略格不增加独立声学样本数。没有启动后续 admission / dual-client probe，没有改正文或 push GitHub。

## 同来源、同条件版本配对：32/32 完成

旧 bdfa 与最终 4f 各两个完整 FP32 replica；同模型与 26 文件资产、同包版本、同显式 allocator、同原始神经 warmup、同 500 ms/EOS/原 D2-C8、同 source bytes，两个 fresh repeats 交换 GPU 与反转格顺序。a13 是真实外层 controller，bdfa/4f 始终是各自实际 NN source，不以 archive HEAD 替代。

| 真实实现 / 策略 | 整场原 D2/C8 | 双期限音频信用 / 全 offered 秒 | 每格 D99 的中位数 |
|---|---:|---:|---:|
| bdfa conservative | 0/8 | 33.5 / 66.33975 | 4.4495 s |
| bdfa Full-call | 8/8 | 66.33975 / 66.33975 | 1.6332 s |
| 4f conservative | 0/8 | 30 / 66.33975 | 4.7593 s |
| 4f Full-call | **6/8** | **65.821625 / 66.33975** | **1.6384 s** |

544 个完整 start/end state、selected C、returned IDs 与原合法参考全部一致，实际 Consumer/EOS 完整覆盖，未丢弃任何失败、EOS 或欠债。4f 的两次失败均是 S0908 EOS，配对 Full-call D99 为 bdfa 1.879996/1.962331 s、4f 2.042823/2.012688 s。不能把旧 8/8 赋给最终 4f。

完整八对 Full-call D99 差值有三对更快、五对更慢，平均 +0.076108 s；每格 D99 中位数接近不证明等价。输入/输出参考控制和 fresh repeated runs 已把所观察的 canonical C/U 不一致与这两次期限失败分开；结果不支持把它们叫作已确认语义 bug。调度、序列化/验证/持久化、运行时变化和边界敏感性是尚未逐项归因的解释，不能只凭这组数据选定某一个原因。

同最终 4f 的 conservative 比较仍有强端到端机会。共同 **origin→真实 Consumer certified EOS** 的双板积分，Full-call 32197.78 J、conservative 35869.89 J；共同 **origin→外部确认 model PID 退出且 CUDA owners 为空** 的窗口为 43951.89 J、47019.22 J。跨版本 Full-call 对比则分别为 final +0.8626% / +10.6135%，这些代价也保留。旧 source 原 energy 的终点不同，原值单列，没有混成同一个窗口。

本地有界结果：`PAIRED32_V2_RESULTS`，247 个索引文件、991837 B。全部 880 个 raw 文件、128297473 B 的 SHA 清单为其中 `RAW_INDEX.json`；大 raw 仍在指定 8 TB 盘。独立审计见 `PAIRED32_FINAL_INDEPENDENT_AUDIT_v2.json`。

## 纯编排常驻请求合同：4/4 trials 完成

a13 新外层只编排四个事前登记的独立 sid。下一请求只在前一个真实 Consumer certified EOS 后开始；各自 origin、500 ms 与不足整块的原 EOS 全量计分。4f 的 59 个核心文件逐字节不变；每个 trial 只有一次双 worker 模型加载，PID 跨四个请求连续驻留。

| 策略 | 请求原 D2/C8 | 双期限音频信用 / offered 秒 |
|---|---:|---:|
| conservative | 0/8 | 31 / 66.33975 |
| Full-call | **7/8** | **64.118875 / 66.33975** |

第一 fresh pair 的四个 Full-call 请求全部通过原门且有端到端机会，才按事前规则继续第二 pair。第二 fresh Full-call 的第三个请求 S0908 D99=2.228824 s，保留该失败，不把首 pair 的成功改写成最终 8/8。16 个请求、272 个原状态转移与完整原参考、时钟、输入义务核对全部通过。

这是有限预登记、单 outstanding、closed-loop 客户端合同。它不证明开放到达负载容量、任意动态 session 注册、总内存常数或无界持续服务，也不覆盖旧无中途 EOS/reset 长流的实时与 CER 负结果。

本地有界结果：`RESIDENT4_V2_RESULTS`，35 个索引文件、505693 B；111 个 raw 文件、88986159 B 全 SHA 索引仍指向 8 TB。逐请求事实见 `RESIDENT4_FINAL_FACTS_v2.json`。

## 四个真实 NN 故障见证与独立 reader 修复

原执行 fixture source 为 **4eb**，共享运行 harness 为 **a13**，实际 C/U 为 **4f**。四个事前固定格全部运行：两正控各接原 S0905 后续请求，两负控仅目标请求，共六个请求、102 个原选定转移；四格完整任务/reference/clock gate 均 PASS。

但是原 posthoc reader 用 `(job_id, kind)` 建表，把两个不同 worker 的无 job READY 都归为 `(None, ready)`，触发错误的 receipt 冲突。因此四格原 CLI 均返回 1，原 buffer/watchdog gate 失败，整体 `NO_GO_COMPLETE_BUFFER4_NEGATIVES_PRESERVED`。**这些执行 compound 失败全部原样保留。**

修复使用新冻结纯 reader **b867**，serving/timing/controller/entry 等原执行文件字节保持 4eb。正式 Linux31 控制零 skip 通过，增加了物理 control namespace、双 READY、替换 READY、drained、真 job 矛盾等反例。新 analysis ID 对四个原 raw 与 watchdog 全树做前后 SHA 核对，**零新增 NN 调用**，四格全通过独立机制重审：

- 两个输入匹配正控：已接收完整 C/U 结果在 producer 实际退出后，保持原 child UID、birth 和 incarnation，待真实 parent 确认后合法安装/消费。
- 两个输入不同负控：producer 退出没有让错误输入取得资格，原 conditional result 被拒绝。
- 正控中的下一独立请求完成真实 C/U/EOS；replacement 仅证明已经启动，不能写成已经 neural-ready。实际导出的首正控只有两条初始 READY 和 survivor 的 DRAINED。

新 gate 为 `PASS_COMPLETE_ZERO_NN_BUFFER4_POSTHOC_REAUDIT`，旧执行 gate 仍是 FAIL。此结果支持受控真实 NN 交错中的机制证据，不提供自然出现率、故障下性能优势或原 CLI 全绿的结论。

原始故障有界结果：`BUFFER4_V1_RESULTS`，42 个索引文件、272742 B；155 个 raw 文件、30436654 B。新分析、31 CPU、失败 CPU 初次尝试和成功 R2 都在 `FINAL_CPU_AND_POSTHOC_RESULTS`，38 文件、184786 B。第一次 Linux25 因 launcher 漏设测试 scratch 变量而在所有 setUp 失败、0 模型调用；另起 R2 后 25/25 通过，未修改冻源或改贴失败。

## 前置与资源闭合

正式执行前，Linux28 控制、真实 POSIX dead-leader 孤儿组控制、36 个资产/输入文件共 15846603671 字节全 SHA、author commit/源码、环境/NN 双 manifest 与物理 GPU UUID 均通过。孤儿组控制的 CUDA 响应是 synthetic，不写成真实 CUDA 释放证据。实际 NN 每格的资源退出与共同窗口另由实际 NVML-backed 观察记录。

所有真实 NN queue 的原 PID generation 均已消失，GPU0/1 各 24 MiB、0% utilization，compute owners 为空。`CURRENT` 已恢复到原最终 **4f / 60ae… / 59 files**，无参数 preflight 通过：`FINAL_CURRENT4F_ROOT_NOARG_R1.json`，SHA `c48b0cb028543aae1a2dd773e1af3245a326f0755af8fe47e7c7277a5be2c7a1`。

CURRENT / GPU 窗口已归还 root。后续最多四格的新双客户端观察 probe 不属于本轮 40 个 trial，本代理没有启动。
