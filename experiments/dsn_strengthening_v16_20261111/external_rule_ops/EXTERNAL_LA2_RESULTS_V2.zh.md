# LA2 已发表规则：离线 CPU 结果 v2

**已完成：28 项控制通过，全部 24 格 × 4 规则 = 96 行通过，原始 C/U、selected G、actual-SUP 行和信用恒等，最终实际文本 SHA 全相同。没有新模型、GPU、训练或线上服务运行。** 当前 CPU 进程已退出，资源闭合见 CPU_RESOURCE_CLOSURE_V2.json；最后 no-argument CURRENT 门仍是 NN de0936，未改 CURRENT。

最直接的新发现：在 Fullcall 已记录的相同计算日程上，LA2-CP 阅读适配器将被修改字符从 **4 降为 0**，双期限音频信用从 **32.340125/33.11625 = 97.6564%** 降为 **31.340125/33.11625 = 94.6367%**，代价恰为 **1 音频秒（3.0197pp）**。这是可复现的发布延迟—修订交换；既不是“LA2 击败原系统”，也不能把这一组合结果解释为无需计算保留或无需 SUP。

## 角色和主来源

外部规则依据：[Macháček et al., 2023, Turning Whisper into Real-Time Transcription System](https://aclanthology.org/2023.ijcnlp-demo.3/)，图 1、第 2–3 节；作者 [whisper_online.py@6da90b44](https://github.com/ufal/whisper_streaming/blob/6da90b44b7e50d79695e68166d2a2c7609c75abb/whisper_online.py#L359) 的 HypothesisBuffer 与独立 finish()。前者取两个连续新增音频更新的未确认公共前缀；后者终局输出剩余部分。本实验没有把 finish 当成第二次 agreement。

原任务已经在 native_bridge.py:110–129 使用 PaddedAlignAttWhisper；本轮不替换它。完整角色是：

| 角色 | 本轮行为 |
|---|---|
| 原 ASR / C / U / selected G | NN de0936 原样保留 |
| 计算保留策略 | 每 cell 原策略/已记录日程原样保留 |
| 支撑义务 | 所有观察器共同验证真实完整状态路径；SUP 固定 |
| 发布规则 | actual-SUP、canonical-only、固定 0.5s 滞后、LA2-CP |
| LA2 适配 | Unicode code point；真实完整视图保守映射；无词时间戳 |
| 估计量 | 固定候选日程上的离线发布质量；无闭环资源/吞吐因果结论 |

这提供了 R1b 所缺的一种已发表决策规则参照，并展示阅读策略可与协议组合。LA2-CP 使用相同的计算保留结果和必要 SUP 适配，因此不是直接与“不保留计算”竞争的外部整系统。它的 94.6367% 也不能反推支撑义务无贡献。LA2 作者系统的 prompt、缓冲裁剪和未来推理并未复制；替换原 ASR 会改变任务和 G，另需新实验。

没有把固定滞后误称为 wait-k。[STACL](https://aclanthology.org/P19-1289/) 的 wait-k 涉及源/目标词推进及 prefix-to-prefix 模型；此处只是明确的通用阅读控制。

## 全部策略的信用结果

每行 4 个 cell：原定 2 speaker × 2 repeat；每列分母均为 33.11625 配置全 offered 音频秒。列间是同一个 cell 的同一份计算产物，不是重新运行服务。五 main 与一个 auxiliary 保持原角色。

| 原策略日程 | actual-SUP | canonical-only | fixed-lag 0.5s | LA2-CP |
|---|---:|---:|---:|---:|
| Conservative | 12.000000 | 10.500000 | 7.000000 | 10.500000 |
| Dependency-versioned | 32.340125 | 30.340125 | 26.840125 | 30.340125 |
| Fullcall | 32.340125 | 30.840125 | 26.840125 | 31.340125 |
| Ready-only | 12.500000 | 10.000000 | 7.000000 | 10.000000 |
| UIR | 30.840125 | 29.340125 | 25.840125 | 29.340125 |
| Strict-birth auxiliary | 12.000000 | 10.000000 | 7.000000 | 10.000000 |

全部 24 格的 LA2-CP 和 canonical-only 都为 0 个最小编辑 D/S 被修改字符；每个原策略下 actual-SUP 合计各为 4 个。本次两种冻结对齐的 D/S、暴露秒数一致；一般情况下对齐仍可能有歧义，不能把这一小样本结论泛化为对齐不重要。

Fullcall 的完整交换：

| 阅读规则 | 信用 / 33.11625s | D+S 字符 | 被修改字符暴露秒 | 已观察 D 窗口覆盖积分 |
|---|---:|---:|---:|---:|
| actual-SUP | 32.340125 (97.6564%) | 4 | 2.122732 | 32.740124 |
| canonical-only | 30.840125 (93.1269%) | 0 | 0 | 23.287151 |
| fixed-lag 0.5s | 26.840125 (81.0482%) | 9 | 0.153651 | 9.552980 |
| LA2-CP | 31.340125 (94.6367%) | 0 | 0 | 24.403430 |

覆盖积分单位为 audio-second × wall-second，是每个真实 offered 前沿在 [offer,min(offer+2s,最后实际同源观察)) 内的分段覆盖积分。Fullcall 四规则相同的未观察右删失上界为 1.340813 audio-second × wall-second；该尾部没有外推。LA2 的首次信用下降只有 3.0197pp，但观察窗口内覆盖积分也从 32.740124 降到 24.403430，须同时呈现。低修订不是免费收益。

固定滞后并不保证更少编辑：Fullcall 9 个字符退休、3 次前沿回退，虽然退休暴露总时长短。它延迟了可显示的私有/非终局 canonical，期间支持否证仍立即生效；更早的已送达 canonical 可继续显示。这一负结果完整保留，没有因控制表现差而改规则或调滞后参数。

## 逐来源、激活和 EOS

Fullcall 的 LA2−actual 信用差：

| 来源 | repeat 0 | repeat 1 |
|---|---:|---:|
| S0769 W0190 | 0s | 0s |
| S0901 W0183 | −0.5s | −0.5s |

各 cell 均减少 1 个被修改字符。LA2−canonical-only 的 +0.5s 仅出现在 S0901 repeat 1；其余三格信用相同。故不把总计 +0.5s 当作每个来源均获益。

Fullcall 四格共有 62 次严格新增音频候选更新、4 次普通 LA 前缀延长（均 S0901，两 repeat 各 2），以及 8 个与 canonical-only 相比确实超前的已送达整视图身份。部分超前只是新音频对应全文仍等于已确认文字，不产生新的字符延长；没有把它伪造为额外 agreement。LA2 所有 24 格的未映射前缀字符最大数都为 0；这是当前有限候选形态的结果。部分前缀无法映射时不准按字符比例给音频信用的情形由独立控制覆盖。

每个来源只计严格增大的、确实到达且 ingress 已接受的前沿一次。同前沿 ASR/full-C、重复发布、canonical 手递交不再贡献 agreement 样本；它们仍立即触发支撑否证。LA2 可保留的整视图必须具有当时合法的完整路径；同一前沿即使文字相同，完整反馈状态不同也会 refute。

所有 shadow 规则仅在实际最终 C/U 到达后执行独立 terminal release。Fullcall 的 S0901 EOS：repeat 0 的 shadow EOS D=2.738675s、repeat 1=2.588414s；原 actual-SUP 的 EOS D 分别为 2.602553s、2.407536s。原 selected G/C 时刻完全不变。因此本轮没有修好 EOS、没有借终局刷新发明早到的 C/U，也没有声称原系统单调或 LA2 一致性已经证明终局正确。

## 方法、门和可复现性

全部 PILOT24 输入范围在准备时继承并复核 OPV1 的完整冻结清单；未按来源、时刻、结果选点。重新核对实际事实/strict 原参考/实际 Consumer 和 ASR/full receipt 绑定，然后只读运行观察器。原 Consumer ACK 会回传 visible_job_ids，影响 Owner keepalive/GC；本轮不向 Owner/ACK/GC 发消息，故不能用离线发布时刻冒充替换线上 Consumer 后的闭环 SLO、GPU 秒或能耗收益。

- 正式 CPU ID：REVTRACE-V16-EXTERNAL-LA2-SHADOW-20261111-V2。
- 实际分析源：7e53cd6cc4089b8e9d7fd525679ed93f5f20c569，18 文件；完整 manifest 01687e6b1d653bdbcad369bdf0e7747ecf9c3323fabec8fac360cc442e6536ba。
- Bundle：49e1de95e71ca37509863d93b1ba9e45f09bf41313dcab7144b195e3f525f4df；根库 ref refs/revtrace/execution/v16-external-la2-shadow-v2 可解析，旧 dirty HEAD 保留。
- 原模型源 NN de0936b2e30179d63aeef6e235cd1af685578c58；原 driver f367c4e1068a9391a0e99d8537c94995a3388e13；绑定审计源 0d54630951dff6e1a423a1652704ee39eea0b8ce。
- Frozen config：887f94753e0fec3df04f859a4e9e8c3a51e0aa74827880fc358cafa0b6747b2b；实际环境：4a9190ccb247897ad09dc58cc70ce8212c9e5bab75843840f907395383f2a32c。
- 输入 525 项 / 164,208,654 bytes，全哈希复核；包含原始 522 项和本轮绑定记录。无新模型调用，禁止神经包导入，neural_imports=[]。
- Gate：PASS_COMPLETE_ALL24_OFFLINE_EXTERNAL_RULE_ADAPTER；28 控制 PASS，0 skip。控制包含从固定作者代码 AST 提取的 HypothesisBuffer/finish，无模型实例。
- 225 个原结果文件 / 6,082,561 bytes 镜像 SHA 全一致，外加 DOWNLOAD_VERIFICATION.json。原始模型日志仍在 8TB，未复制到普通论文树。
- Raw：/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/EXTERNAL_LA2_SHADOW_V2。
- 资源闭合：13:33:52 UTC，CPU PID2944198/start615397635 已退出、CUDA=[]，最终 default/analysis-source 门 PASS。没有继续运行的 CPU 测试/重放。

v1 源 a105e33 保留为**未执行**版本。独立静态审查发现同前沿 covered/refuted 混淆及 canonical 绕过滞后两个问题，均在 v2 全新冻结前修复并增加实际合成路径控制；未修改 v1 或任何已冻结结果。审查说明见 review/EXTERNAL_LA2_PRELAUNCH_REVIEW_v1.zh.md。

建议发布：把本结果作为“协议上可组合的外部发布策略对照”，与原实际 GPU 五 main/auxiliary 结果分栏。主呈现 Fullcall 的延迟—修订表和全部六日程信用矩阵；附全部 96 行、24 个来源/repeat 对照、持续覆盖/删失边界、完整源和控制。n 仍是这组原来的 2 speaker；不能把 96 行当成新增 96 个独立服务样本。

