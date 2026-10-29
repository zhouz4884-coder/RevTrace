# 原四来源 16 格确认：独立 CPU 重计与后续决策

实际 gate：`PASS_COMPLETE_16_CELL_INDEPENDENT_PAIRED_RECOUNT`。这轮分析在读取新结果数量前冻结了独立 clean source `4088f34f1aac8f10c9676006f08b6b44401a5019`、完整 manifest/config/plain snapshot/bundle；11 项纯 CPU 控件通过，显式 source preflight 通过后再执行本地重计。没有 remote、模型或新数据调用。

**结论：当前 full-call retention 的服务机会经过四个旧来源、两次 fresh process、GPU 换卡的确认，值得做一次固定四个新 speaker 的独立确认。无需为 stage 追加 join 追逐排名。** 单次 encoder component probe 与新缓存设计应分开；它只需要短暂关闭当前条件机会判断，再确定最终方法，不能让选源与模型响应互相影响。

## 1. 完整范围与主要结果

原 runtime 始终为 `bdfa3b1307d267a5a4caf6484e1ad465c39a592e`。16 格 = 4 个原来源 × 2 次 fresh process × 2 臂，每组两个臂同一来源/重复/GPU角色且配置除执行臂外相同，配对顺序预冻结；同一来源 r0/r1 交换 primary GPU 0/1。四个旧来源不是 holdout，不能把8个进程配对或138个frontier当成独立来源。

| 指标 | 保守两 full + 相同早显 | RevTrace full-call retention |
|---|---:|---:|
| 完整服务格数 | 8 | 8 |
| offered 音频/observations | 66.42975 s / 138 | 相同 |
| 原 D2/C8 信用 | 37.50000 s | **66.29375 s** |
| 信用比例 | 56.45% | **99.80%** |
| 全 run 原 P99 同时达标 | 0/8 | **6/8** |
| D2 miss（其中 EOS） | 63（8） | **2（2）** |
| 非 EOS D2 miss | 55 | **0** |
| C8 miss | 0 | 0 |
| 两卡 service energy 合计 | 36941.6 J | **32049.8 J** |
| 原完整输入/输出/C/IDs fidelity | 138步 | 138步 |
| 最终字符错误 | 16/182 | 16/182 |

信用净增 **28.79375 s / +43.34pp**。共有61个 miss→hit、75个同hit、2个同miss、0个 hit→miss。两卡 service energy 降13.24%；它包括所有实际在途工作/退出，加载和固定 neural warmup 分列，不是只比较模型内核功耗。

八个配对全部信用更高、C50更低、能耗更低。C50改善0.733–1.907 s，配对能耗下降8.60–16.41%。这不是统计显著性声明；它是明确的跨旧来源、时序重复与换卡一致性。

| 来源 / repeat（primary GPU） | 信用：保守 → full-call | C50减少 | 两卡能耗减少 | full-call D99 |
|---|---:|---:|---:|---:|
| S0764W0209 / r0（0） | 3.0 → 8.0 s | 1.731 s | 8.60% | **2.520 s，失败** |
| S0764W0209 / r1（1） | 3.0 → 8.0 s | 1.907 s | 8.88% | **2.603 s，失败** |
| S0765W0203 / r0（0） | 5.0 → 8.334 s | 0.992 s | 16.41% | 1.017 s |
| S0765W0203 / r1（1） | 5.0 → 8.334 s | 1.027 s | 14.88% | 1.025 s |
| S0767W0329 / r0（0） | 5.0 → 8.66894 s | 0.781 s | 14.67% | 1.222 s |
| S0767W0329 / r1（1） | 5.0 → 8.66894 s | 0.733 s | 15.12% | 1.202 s |
| S0768W0136 / r0（0） | 6.0 → 8.14394 s | 0.737 s | 13.86% | 0.890 s |
| S0768W0136 / r1（1） | 5.5 → 8.14394 s | 0.793 s | 13.96% | 0.943 s |

所有全-run P99、EOS、未命中和较差重复都保留。source0两次EOS各0.068s未满足D2，信用缺口恰为0.136s；不能把它删掉后写“所有负载满足原服务目标”。全部non-EOS命中与6/8全run通过是两个不同事实。

## 2. 这轮证明的真实保留路径

独立连接 actual dispatch、job/model计时、父Canon安装、full history、ledger：

- **99次旧birth在途promotion**，完整输入均等于后来确认的实际父cut，出生身份保持。
- 99/99满足 `model_start < parentCanonInstall < model_end`，且与其父原model path区间重叠；不是把restore/export或未读队列冒充神经在途。
- 其中**12次自身identity预测end不同于真正C/U end**，仍按已确认完整输入保留并正确完成。这是当前计算合法性与未来预测正确性相分离的实际服务证据。
- **20次known-invalid C-entry退出**：逐项核对了实际自身start frontier的Canon见证、expected/actual完整状态hash不等、learned C未执行、C/U未完成、没有endcut。不是仅祖先失支持或未知未来输入就取消。
- 实际completed-full buffer reuse为0，discarded-full-completion为0；不把只在CPU里验证的完成结果缓冲或未来收敛写成自然服务发生率。

保守与full-call都完成了相同的130次原ASR模型调用和128个non-None C选择；full-call另承担了20个被正确退出的ASR prefix。这里并不是原计算总数更少。实际收益来自合法流水/保留，减少了等待与服务尾部；完成更早后，两卡service窗口能耗仍下降。不能将能耗结论改写为FLOPs减少或C调用被大量省略。

## 3. 精确任务保持与 same S

本次独立对276个实际Canon步骤重新检查完整原始输入、完整输出、原C对象（含prompt/候选/选择）、returned IDs、actual job/WAL/history相符；只允许精确的新增 `stage_execution` 标签投影。实际原任务最终质量也相同，不能用仅CER相同替代该全链检查。

所有臂共用相同S/whole-state Consumer、typed ASR早显、完整parent/branch链检查、Canon/Provisional权限和fsync发布路径。**但全部16格的“Canon安装时保留ahead privateview”实际仍为0。** 因此原生应用这轮是C1在途执行保留在相同消费合同下兑现服务进展，不能独立宣称它再次证明消费保留的必要性。C2的交互证据继续由原核心实验提供。native的99次实际模型保留/12次end预测不同/20次错误start退出已经足够具体，不需把每个结果强行套成所有贡献同时发生。

full-call与保守执行都是本工作组装的原生执行方式；full-call是当前最佳RevTrace实现，不是外部已发表方法用来否定我们的组合。原作者ASR/C/U源码与模型保持不变，不等于完全复现了原作者整个在线VAD/服务部署。论文应透明称其为真实反馈流程的受控原生适配。

## 4. 推荐的独立四speaker确认

GO一个固定小scope：**4个未用于开发/本16格的speaker × 2次fresh process × {保守两full、冻结full-call实现} = 16个timed cells**。保留相同换卡、随机配对、原cadence、D2/C8/all-offered含EOS、内容/最终质量与两卡能耗。旧来源确认已很稳定，独立来源的目标是检验效应能否离开这4个开发speaker，而不是再开模型、精度或时间相位网格。

先让既定单次E component probe形成明确门，确定最终method source；若仍用bdfa，就保持bdfa不变。然后冻结metadata选源规则/seed/候选顺序，按原固定公开ZIP索引从speaker-disjoint候选中选4个8–15s WAV，检查实际header、16kHz单声道、CRC/SHA与官方文本。所有候选替补仅因metadata/header不满足预先规则，不因模型响应、兼容率、质量或性能更换。

来源清单与实际bytes先锁定，再用独立 `66abab7` 工具按原full、无早显/无推测生成逐步参考；模型runtime实际commit与generator commit分列。参考gate完整通过后，机械锁DETAILS SHA，再冻结最终timed计划。offline参考不作为服务数据，不能按参考的输出选择“容易兼容”的新speaker。final方法若改变，必须先重新冻结source/manifest和相应generator组件身份，不能继续套用bdfa标记。

建议冻结独立后验内容检查：及时首见的完整文本与其实际visible frontier的完整Canon对应，raw/固定normalizer分开，未知保持未知，不截长文本。它与现有原D2/C8指标平行，不取代主指标；最终质量相同不自动意味着首次Provisional文字全受未来Canon支持。

确认结束后，以新4speaker作为独立确认单列；旧4speaker×2repeats是开发后的稳定性确认。不要将EOS observation、同speaker的repeat或所有frontier当成独立样本抬高统计强度。若新4仍稳定收益，当前native证据已足够转入正文，不为新增点而继续横向扩source/model；若结果分化，就报告与输入/预测失配/容量的实际边界。

## 5. 可核查交付

- `confirmation_analysis_source_v1`：实际clean commit `4088f34f1aac8f10c9676006f08b6b44401a5019`；`confirmation_analysis_snapshot_v1`、完整bundle与manifest均已冻结并导入证据repo refs。
- manifest SHA：`e6fe388840696558306a4bd3f0d00ade0ce14d1ad5eca044ca619e91a1cb4d9f`；config SHA：`832d1c7559064ebbd1f2296ebdd2aa292e63b3eedb41d4c2d40705b7d2b171ea`。
- `CONFIRMATION_ANALYSIS_RESULTS_v1`：config/env/run、正式CPU日志、222个实际输入hash、完整16cell结果、8个pair结果、summary/gate；gate SHA `c7b4b26b383703e53733f987bf5b59f9ea31949dbc768f2b6d37545b47b94e01`。
- 原有界服务证据431文件/29,733,082B均按collection receipt逐文件核对；原raw继续留在8TB。独立重计没有改原runtime或原结果，也没有新增任何推理。
