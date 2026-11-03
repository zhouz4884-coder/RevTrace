# v13 比较组、能量与成本口径独立审计

审计 ID：`REVTRACE_DSN_V13_COMPARISON_COST_STATIC_AUDIT_20261103_V1`。结论：**现有新八来源两臂主结果无需数值修正；没有发现可直接补入该研究的第三个同合同 native 比较臂。** 本次仅核对既有有界结果、实际 READY 记录、冻结源码及事件表，没有远端访问、新模型/GPU/服务运行或论文编辑。输入 SHA、逐格算术及判定记录在同名 JSON。

**比较组应保留明确的职责。** 当前 NN4f `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47` 新八来源研究确实比较同原始 ASR/Correct/Update 任务、双完整 FP32 worker、同固定 learned-C warmup、同早显与实际 Consumer、同 D2/C8/all-offered/EOS 及相同完整服务能量口径。它隔离的是条件完整输入上的提前执行/保留相对等待原选定父反馈的收益，不是对全部外部推测系统的排名。

| 已有控制 | 能否补作新八来源 native 第三臂 | 直接理由 |
|---|---|---|
| source0 ready-only handoff 三臂 pilot | 否；保留为 developmental service pilot | 仅旧开发来源 S0764 的一次 fresh trial，实际 bdfa 源；第二进程只有 ASR，没有 learned Corrector；能量只到 Consumer drain |
| 旧四来源 matched / resident | 否；能作各自合同的重复与驻留证据 | 仍只有 conservative / fullcall 两策略，不增加第三种比较策略，也不增加新八来源样本 |
| 最早双会话 native sequential / drop / joint | 否；保留原负结果 | 双源并发与执行角色不同，sequential 是每源一完整副本；旧 origin→Consumer-drain 窗口，非最终单反馈链 NN4f 对照 |
| core 的 checked snapshot + recomputation、R-only 与作者完整正控 | 否；继续承担因子分解 | Qwen/Whisper 批处理、FP16 Private + FP32 Authority 与 native 原任务/资源合同不同 |
| stage/encoder component、same-input oracle、CPU replay | 否；继续承担保真或对象取舍 | 不是完整 native serving 比较，不能用组件余量填主性能表 |

ready-only 的资源差异可由实际记录直接核实：`dsn_streamcorrect_stage_handoff_20261029/SERVICE_PILOT_RESULTS_v1/SC_STAGE_SERVICE_PILOT_V1_ready_handoff_source0_r0/READY.json` 中 authority 的 Corrector 为 1,934,137,344 个 FP32 参数、`neural_C_confirmed=true`；producer 的 `corrector_parameter_dtypes={}`、`ASR_only_producer=true`、`neural_C_confirmed=null`。这不是双完整 worker。实际 `ENERGY.json` 明写 `origin through Consumer drain`；冻结 `source_v3/stage_service.py:142–149` 在 ended 之后才等待 worker drained，却仍只积分到 ended。因此不能沿用旧叙述中笼统的“三臂相同模型/warmup/完整成本”来主张最终公平第三臂。pilot 的 5 次真实 ready hit 与端到端数据仍有效于其自身合同，不需删除或改写。

**新八来源能量窗口没有发现加载污染。** 对原 `confirmation/SERVICE_RESULTS_v1/SUMMARY.json` 中全部 32 格逐项核对：common window 的起点等于同格 origin，终点等于 `physical_drain_observation.confirmed_perf`；两板 J 相加等于总 J；J 与秒数分别精确对上 `FINAL_REPORT/ALL32_CELLS.csv`，原源记录均为 `initial_cold_load_excluded=true`。冻结 `resilience_owner.py:103–114` 先收齐两 worker READY，再发 owner_ready；`resilience_trial.py:125–129` 随后设置 origin。服务 driver 的 READY gate 核查两张板的模型参数精度/数量、包版本、真实 learned-C warmup 完成及 genesis reset。加载与固定 warmup 在服务起点前。

| 同合同服务账 | Conservative | RevTrace fullcall |
|---|---:|---:|
| 每臂 offered audio-s | 137.864125 | 137.864125 |
| origin→外部确认 physical drain 的两板 J | 95,262.639975 | 90,279.609834 |
| J / offered audio-s | 690.989334 | 654.844832 |
| 逐 run 窗口范围 / s | 18.500436–20.780967 | 14.563064–17.685758 |

合计能量下降约 5.23%，与正文一致。全部格 actual certified EOS 到外部 drain 的剩余窗口为 4.645–5.697 s，确实被计入；不能离线删去。外部终点是首次样本确认实际 READY worker PID 已退出/僵尸且 CUDA compute owners 为空的观测上界，不是瞬时硬件事件。外部采样的该次查询区间为 0.127–0.403 s。以上使用已归档的逐格能量账和冻结积分器核验口径与守恒，未重新取回 32 份完整功率流再积分。没有足以要求远端重计的冲突。单凭 native 的 J/audio-s 高于 batched core，不能推出真实窗口错误；正文只在同 runtime、同 workload 内比较即可。

**成本表的三个范围均为逐 run 均值的 min–max。** 从 `dsn_continuity_cost_20261102/cost/FINAL_AGGREGATE/UNSUBTRACTED_FAMILY_FOOTPRINTS.csv` 筛选八个 timing-on native trial：完整 commit 为 20.350719–27.251959 ms/call，Owner fsync 为 15.776612–22.182155，Consumer apply 为 18.583767–23.914390。分别舍入为正文 20.35–27.25、15.78–22.18、18.58–23.91，且全部 `floor_subtracted=false`。commit 上界来自 S0908 fullcall on r0，fsync 上界来自 S0908 conservative on r1，连上界都不是同一 run。不得相减声称纯 validation 费用；即使同 span 扣除 nested fsync，剩余仍含编码/复制/写入/Python 等。当前表 caption 的逐 run 范围和正文“同步持久化占主要部分，端到端比较已支付全部路径”可保留，不增加旧微基准或净协议税。

**三条失败短解释均有冻结事件支持。** `EVENT_CLAIMS.json` 绑定的四份分析输入 SHA 全部匹配；另独立从 610 条 job、564 个 endpoint 和 190 条 miss 表核对以下范围：

- S0915 的两次重复各有六个 late non-EOS replacement（j15/17/19/21/23/25，6.0–8.5 s），完整输入匹配实际父状态且选中。父安装日志至派发为 2.162–5.275 ms；原 infer host 区间 0.530870–0.740867 s。EOS j26 是重新匹配并提前运行的调用，其 0.813146/0.825711 s 不在该六次范围内。r0 首个 miss 的 dispatch 7.590534、ASR 7.976400、Consumer 8.022780 相对原 origin，D2 为 8.000000；这确有交付敏感边缘，不能把全部失败只归模型或只归 Consumer。
- S0901 EOS j18 在父确认之前派发，完整输入后来匹配且 promotion 保留；两次 ASR 本身已比 EOS D2 晚约 0.311/0.422 s。r0 仅 EOS miss，r1 包含最后完整前沿及 EOS。用 `input-matching in-flight EOS call` 比 `early EOS` 更不易被读成及时 EOS。
- S0902 尾部 j19/21/23 两次均有完整输入反证；合法 j20/22/24 在实际父安装后约 3–5 ms 派发。r1 EOS 派发已比 deadline 晚约 0.367 s。不能统一套用 S0901 的匹配 EOS 路径。

S0915 占 6.996125 / 8.404125 = 83.2463% 的 RevTrace 未及时音频，不能扩为全部 offered 的比例。上述是当前原时钟上的执行路径解释，不是任意合法优化的最优性下界。

**最小编辑建议只有四项：** native 设置明确“input-confirmed overlap 相对等待 selected parent feedback”；ready-only 继续标 developmental control，不拼入新八来源主表；成本与能量保留当前正确范围/窗口；失败段保留 `each repeat's six late non-EOS replacements`，并在需要时用一句 observed execution boundary 排除 lower-bound 误读。无需新增通用限制清单、修改数值或打开新 GPU 实验。

Gate：`PASS_V13_COMPARISON_COST_SCOPE_WITH_NO_RESULT_CORRECTION`。该 gate 是编辑证据审计判定，不是新 native 实验通过数。
