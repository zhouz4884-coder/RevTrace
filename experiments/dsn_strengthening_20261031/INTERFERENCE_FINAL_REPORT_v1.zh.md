# 原 4f 双客户端观察 probe：固定四格 NO-GO

最终判定为 **`NO_GO_FIXED_TWO_CLIENT_ADMISSION_OPPORTUNITY`**。首重复满足预写机会门，第二重复没有复现足够大的 B 服务损害；按两重复合取收束，没有只选择 r0，也没有扫来源/相位/阈值、重试、Canonical-first 或预算机制实验。

完整机器入口：`INTERFERENCE_FINAL_EXECUTION_RECORD_v1.json`。实验 source 为 `2198b8d517e068cb8a08e0bc022104b4fed4c8c7`（38 文件），实际 NN 仍是原 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`（59 文件）。四个原声源、A-first 顺序、B 首请求固定晚 2 s、两客户端各自 closed-loop/EOS、原 FP32/C/U/资格与 D2/C8 全部不变；观察器原样返回原协调器 proposal。

## 事前门与实测结果

| 重复 | Conservative 四请求 C8 零 miss | Full 实际 B-ready inversion | B worst-request C99：Conservative→Full | 差值 | 重复门 |
|---|---|---:|---:|---:|---|
| r0 | 是 | 7 个 distinct actual UID | 5.670810→7.470688 s | +1.799878 s | GO |
| r1 | 是 | 3 个 distinct actual UID | 5.942914→6.075753 s | +0.132839 s | NO-GO |

两个重复的 B 额外 C8 frontier misses 都是 0。r1 未满足 `max(1 s, 20% Conservative C99)`，也未满足至少 4 个额外 C8 misses，因此总体 NO-GO。真实 conditional-before-ready-Canonical 交错在两重复均存在；足够大的服务伤害没有稳定复现。它不证明新策略收益、不证明全部延迟的因果来源，也不代表核心 R1 的否定。

## A/B 全量指标

D99/C99 为该客户端两个请求中较差的 per-request 值；credit 为两个请求的原双期限音频秒。每个客户端每 trial 34 个 offered frontiers，含两个真实 EOS。

| 策略/重复 | A D99/C99 (s) | A D2 misses / credit | B D99/C99 (s) | B D2 misses / credit |
|---|---:|---:|---:|---:|
| Conservative r0 | 4.260582 / 4.539770 | 17 / 8.5 s | 5.341530 / 5.670810 | 21 / 6.5 s |
| Full r0 | 4.147919 / 4.416467 | 15 / 9.5 s | 7.182722 / 7.470688 | 26 / 4.0 s |
| Full r1 | 4.093549 / 4.374744 | 15 / 9.5 s | 5.652557 / 6.075753 | 22 / 6.0 s |
| Conservative r1 | 4.689750 / 5.008334 | 17 / 8.5 s | 5.623884 / 5.942914 | 21 / 6.5 s |

全部客户端、全部重复 C8 misses 均为 0；每个 A/B 单元各有 2 个 EOS D2 misses，其余 D2 misses 为 non-EOS。**16 个 probe 请求的原 D2/C8 联合门全部失败**，不能把语义执行完成称为服务期限全部成功。详尽 per-request、EOS/non-EOS、held views 与 durable authority 保留在 `INTERFERENCE_FINAL_FACTS_v1.json`，平表见 `INTERFERENCE_ALL_A_B_METRICS_v1.csv`。

## 两板实测能量与真实必要工作队列

| 策略/重复 | origin→真实 certified EOS | origin→外部确认 model/CUDA drain |
|---|---:|---:|
| Conservative r0 | 12802.10 J | 14566.78 J |
| Full r0 | 13164.17 J | 14487.28 J |
| Full r1 | 12849.62 J | 14408.52 J |
| Conservative r1 | 13110.64 J | 14583.63 J |

这是共享双板的整个 trial 能量，没有按客户端拆分或归因。原 source energy 另存，未假设与外部共同窗口相同。

7/3 个 inversion 是实际原调度器的 register/dispatch UID，均绑定 source/完整 start/end、slot/incarnation/PID、原派发时钟和真实 worker begin/end/terminal；B 的 Canonical SHA、frontier、已接受输入以及缺少同输入 live/completed 工作也有快照与原始队列证据。不是 proposal-only 计数。完整原行、行号、原行/全文件 SHA 入口为 `INTERFERENCE_ACTUAL_INVERSION_QUEUE_EVIDENCE_v1.json`。Conservative 每 trial 68 个实际 dispatch，Full 每 trial 72 个，合计 280。

## 独立复核与范围

正式 Linux98 零 skip、真实原协调器差分、原 OS control（CUDA 响应 synthetic）、使用的 26 模型＋5 音频共 10100369066 字节全 SHA、author/env/GPU 与 R1 真实 prior receipts 均在 NN 前通过。b867 posthoc wrappers、原 task/reference PASS、全部当前 raw/watchdog SHA 和旧 4eb compound/CLI/watchdog FAIL 被硬绑定；没有洗白旧执行门。

四 trial 之后，使用新 CPU 进程和冻结 2198 checker，对 probe 的完整 state/C/IDs、每请求时钟、原始派发/物理租约/worker、durable install/Consumer authority 重算，四份 summary 与运行输出逐对象完全一致。又从 R1 的全部原 raw 重算 918 个原选定转移及其 endpoint；probe 为 272，**合计 1190**。这不是 kernel-forward 调用数。

四组 NN 原 raw 共 1262 文件、348155321 字节，在独立只读重算前后逐文件全 SHA 相同；新增 NN 调用为 0。独立复核 gate：`PASS_INDEPENDENT_ALL1190_STATE_C_IDS_CLOCK_DISPATCH_RAW_RECOUNT`。本地第三方 QA 另完成 416 项包/算术断言且无错误，明确其元数据层级，不冒充再次远端 raw 重跑。

服务损害不稳定的解释仍是待检验假设：非抢占残余工作、相邻神经调用耗时、闭环后续请求相位以及 GPU 轮换可能改变某次 inversion 的实际关键路径权重。当前结果不能把某一个解释确定为原因。依据预写门，不以新相位/来源补试来挽救，也不开发新调度器。

## 资源闭合

实际新 NN trials 恰为 4，原 probe PID generation 已消失；两个 3090 各 24 MiB、0% utilization，compute owners 空。`CURRENT` 已恢复原 4f/60ae/59 文件，无参 preflight PASS，窗口归还 Root。

机会 gate SHA：`5a715324d5b67765cf2ad16aace5e63661666db9b497cb4272480fae0a6dd525`；独立 1190 raw gate SHA：`7b6d84572a8914954a1cc477a824c1a4402d20b1b71aa081ff5d5ba01f6bda88`；恢复 4f 无参门 SHA：`56eb4726d42743d2001f1f47864caa81b2ce665bd4e40ea9db103761ce55b387`。
