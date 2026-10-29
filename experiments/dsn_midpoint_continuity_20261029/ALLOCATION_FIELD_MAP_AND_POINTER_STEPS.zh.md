# 待根分配的字段映射与CURRENT安全切换

2026-10-29，此时native最后formal格/后分析仍在运行或待核对。本文件只准备步骤；未stage、未launch、未修改CURRENT。计划SHA和12格范围不变。

## ALLOCATION字段映射

前缀`B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9`。

| label | 真实远端记录 | 已知/待核对字段 |
|---|---|---|
| joint24_execution | `B/results/revtrace/physical_retirement_20261028/dsn_joint_controller_v1/GATE.json` | `gate=PASS_ALL_FROZEN_EXECUTION_CELLS`，`completed=24`；本地对应`../dsn_joint_retention_exit_20261028/RESULTS_v1/controller/GATE.json`，hash在实际allocation生成时与远端再次核对。 |
| joint24_analysis | `B/results/revtrace/physical_retirement_20261028/dsn_joint_analysis_v2/GATE.json` | `gate=PASS_OFFLINE_RECOUNT`；使用修复后的v2，不能指向保留的v1分析失败。另读v2 SUMMARY确认accepted24/6完整blocks，不把PASS当正交互。 |
| native_prescribed_scope_decision | `B/results/revtrace/dsn_streamcorrect_20261028/native_campaign_v8_continuation_auditfix_v1/GATE.json` | 精确status/SHA由native agent终态回执给出；同时确认原始2witness+12formal实际齐全。source仍v8 `61c9afac00561f7ff1351f3eba9fd95adb239e8c`，离线controller/auditor不同提交另记，不重标。 |
| native_analysis | `B/results/revtrace/dsn_streamcorrect_20261028/native_postanalyses_v8/SUMMARY.json` | 预期结构`status=COMPLETED_POSTANALYSES_ORIGINAL_NATIVE_GATES_PRESERVED`，但必须实读原始两项analysis coverage/gates和整个原生scope终态，不能只看进程rc或这个status。阴性科学结果不阻止本点按原计划执行。 |

`native_scope_executed`只有在真实核对后填写`two_witnesses_gate_passed_all12_formal_complete`。若预定witness门控实际关闭，则只能填写`two_witnesses_gate_closed_no_formal`，并绑定真实门控决定；不能把未执行formal称完成。当前已有17/36非空raw交错门控通过，因此预计走前一种，但在完整终态之前不填写为事实。

每个`prerequisite_evidence`都要实际路径+远端完整SHA256+必须匹配的JSON字段。`root_allocated`只由收到根任务资源分配后设true；本地模板的false/占位符保持拒绝启动。native agent还需确认无残留模型/CPU分析/重IO后台进程，GPU空闲。

## f0 CURRENT切换步骤（根分配后才执行）

1. 收到native完整scope+后分析+收集结束/资源释放回执，并收到根任务分配。在此之前不改CURRENT，当前v8运行的source identity必须继续指向v8。
2. 核对计划仍为`fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84`；分析源仍为`fb8a429d95ab682002bc39aedca8bcbec8942b67`。核对本地f0 source_v3 clean、242文件完整manifest、完整commit可解析；先用显式source/manifest preflight，不改老运行。
3. 逐字节备份当前CURRENT到本目录唯一`CURRENT_BEFORE_MIDPOINT_v1.json`，记录其SHA。只调整机器本地指针的source_worktree/commit/manifest/hash、analysis指针、research_state、队列说明、previous_pointer和更新时间；旧v8、旧f0运行记录与源均不动。
4. 用同目录临时文件+原子替换写新CURRENT，再运行no-argument preflight，必须得到f0 commit和完整manifest匹配。若失败，原子恢复原CURRENT字节并保存失败回执，拒绝stage/launch。此处是source identity检查，不等于环境验证/完成GPU实验。
5. 本次新no-argument preflight JSON写入本目录`LOCAL_PREFLIGHT_BEFORE_GPU_v1.json`，其字段进入allocation的`local_current_preflight`。再次确认实际资源空闲，之后才运行既有stage脚本和准备好的launcher。

不复用旧`CURRENT_BEFORE_NATIVE_v6`文件直接覆盖：虽然它曾指向f0，但其中队列/更新时间是历史状态。使用当前pointer副本更新本次目标，并保留精确前态，避免伪造历史。

## 不改计划的后续步骤

Stage只上传35KB冻结plan、source selection、完整analysis bundle/manifest；核对全部byte身份并留下staging receipt。launch再次检查allocation、前置scope字段和所有SHA、runtime/analysis clean-source manifest、GPU空闲以及所有输出从未使用。每个实际cell由f0 campaign记录环境/config/run record后调用模型。

12格全部结束后执行完整4项core+timely-continuity分析，保留所有negative gate与完整三重复。强条件不满足仍为完成STOP；不试10/11、不换source、不增repeat。原始日志和大结果留8TB盘，本地只取有界审计结果并核对远端SHA。
