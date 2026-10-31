# 实际派发重配对与长流边界：正式v2结果解释

结论先行：原36格的完整重配已经完成，真正的条件派发分母是1901；其中360个完整输入最终确认、1541个被同start-frontier实际Canonical反证、0个未决。360个也都有独立live promotion见证，但只有354个形成durable fact、352个有原Owner安装事件、354个实际被Consumer使用。差值全部可落到受控故障时序，不能把输入相同自动换成当时仍有authority或实际使用。

## 证据身份和核验边界

本报告只解释已完成的 `DIAGNOSTIC_RESULTS_v2`：分析source `ff95f04465d006f76a0e729d3fd5457c32769c1e`；原神经执行source `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`；36格、全部8长流、3976个选定Canonical转移；725个绑定输入（原始日志及source/config等元数据）的SHA在扫描前后核对，CPU控制67/67且无skip，新模型调用0。Top GATE SHA为 `09daf9313ef888d028414f4404d6de86b4f255d9ccb0e0f44490a5b301bb4843`；SUMMARY SHA为 `7cf116b63b8b04dd683b1a100dfb2cf1fa028d42732d6aed334ff99dd6fcf4f0`。本地已再次核对5个有界导出文件的长度与SHA，不能把CPU复核写成新GPU性能实验。

为解释生命周期差异，经配对执行agent明确确认0NN/空窗后，只读取了8个**已经生成的诊断**派发文件共642014 bytes，按既有输出manifest核SHA并再次核读后SHA，带回8个例外row共28620 bytes；未读取原NN日志、未重新扫描实验。其证据为 `DIAGNOSTIC_LIFECYCLE_EXCEPTIONS_v2.json`。随后已通知配对agent恢复timed NN，本报告不再访问远端。

## 分层后的实际分母

| 固定证据层 | 格数（Full-call） | 全部实际派发 | 条件派发 C / R / U | 确认率 | live提升 | durable / 原Owner安装 / Consumer使用 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 正常短流 | 8（4） | 153 | 40 / 17 / 0，N=57 | 70.18% | 40 | 40 / 40 / 40 |
| 受控故障短流 | 20（10） | 384 | 58 / 32 / 0，N=90 | 64.44% | 58 | 52 / 50 / 52 |
| S0770无reset长流 | 4（2） | 2660 | 96 / 828 / 0，N=924 | 10.39% | 96 | 96 / 96 / 96 |
| S0903无reset长流 | 4（2） | 2332 | 166 / 664 / 0，N=830 | 20.00% | 166 | 166 / 166 / 166 |

C/R/U分别为CONFIRMED/REFUTED/UNRESOLVED。格数和“全部实际派发”包含Conservative；条件派发列只统计实际发生的条件job，Conservative的该分母为0，而不是0%预测准确率。正常短流只有既有三来源、四个Full-call格；受控故障有重复/迟到、Owner前/后durable、Worker-after-ASR、partial-frame等预定时序。两个长来源各为同一24-utterance合成长流的两臂×两次重复，属于无reset状态压力测试。

全36格混合结果360/1901=18.94%只用于完整账本守恒，**不估计生产总体确认率或自然失效率**。S0770/S0903坏长流占了1754/1901个条件派发，直接池化会掩盖正常短流40/57=70.18%与长流96/924=10.39%、166/830=20.00%的证据层差别。受控故障58/90=64.44%也不是自然发生率。所有36格的144条source×clock×分母覆盖摘要都已检查N及C+R+U守恒，空bin保留；本地有界导出不含整条timebin曲线，不凭端点重建曲线。

## 6个确认但未用，与2个durable后恢复消费

以下8项均为source BAC009S0908W0369、Full-call、owner0的 `e0-j000000004`，输入区间24000→32000 samples（1.5→2.0秒）。UID必须连同cell_id/owner epoch使用，不能跨run把同名job合并。

| case（均r0、r1各一项） | 条件job数 | 完整回执 | durable / 原Owner安装 / Consumer使用 | 已记录的解释 |
| --- | ---: | --- | --- | --- |
| owner_before_durable | 2 | 有 | 0 / 0 / 0 | 输入已确认并提升，完整结果已到，但注入点在原C之后、durable之前；旧Owner namespace随后被替代。没有旧fact可重放，恢复另行完成原义务。 |
| worker_after_asr | 2 | 无 | 0 / 0 / 0 | 输入已确认并提升，physical-loss记录明确retire原full1/incarnation0活job；ASR阶段结果不是完整C/U回执，不能据此安装。未返回的model work保持UNKNOWN。 |
| worker_partial_frame | 2 | 无 | 0 / 0 / 0 | 同样有输入确认，但完整逻辑回执未成立，原full1/incarnation0被physical loss retire；不把partial frame补成结果或把未知计算记0。 |
| owner_after_durable | 2 | 有 | 2 / 0 / 2 | 原Owner在durable后、安装/消费前被终止；journal sequence 5已存在，owner1以 `recovery_replay=true` 实际消费原fact，保留原job birth。 |

因此，前3行解释360−354=6个**条件job**未被选择；最后一行解释354−352=2个缺少**原Owner**安装事件，却仍被恢复Consumer使用的durable事实。它们不是两个额外非法安装，也不是输入确认判错。若使用全部派发分母，3988个CONFIRMED减3976个selected共有12个未选job，其中还含另外6个current-root job；不要把“6个条件job”误写为全部job的差值。

“旧354/366”不再使用：366不是本轮完整actual-dispatch账本支持的分母。派发输入确认应写360/1901；durable/Consumer使用应写354/1901，原Owner安装352/1901。如确实讨论**已live提升者转为durable**的生命周期转换，才是354/360，不能将其重新命名为预测准确率。各分源分母优先于混合比例。

409/457、333/416也保留正确主语：每个相应长流run中，已选定调用自己的early predicted-end与其最终选定end不同，且各有1个缺失early prediction。新结果对实际后继输入逐job重配后，S0770每个Full-call格为48/462确认、414/462反证；S0903为83/415确认、332/415反证。数字接近不构成分母可互换的理由。

## 全8格首次边界

表中“位置”均为选定执行目标frontier/16000的**音频秒数**，不是服务wall时钟；D/C后一数为相对原offered时钟的实际Consumer延迟秒数。相邻重复为至少8 codepoints的reference-free文字信号；448列是选定job的trim后输入条件，**没有直接decoder guard分支探针**。LB列明确为OFFLINE ORACLE。两种策略的首次内容边界相同，wall完成时间不同，不能把audio位置当作发生wall时刻。

| source / arm / r | 首D>2：位置 / D | 首C>8：位置 / C | 相邻重复信号 | trim后≥448条件 | OFFLINE LB：>0 / ≥16 / ≥64 | 首20条件job低窗 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| S0770 / Cons / 0 | 4.5 / 2.081 | 18 / 8.219 | 36 | 59.5 | 27.5 / 33 / 41 | N/A：无条件派发 |
| S0770 / Cons / 1 | 4 / 2.047 | 16.5 / 8.003 | 36 | 59.5 | 27.5 / 33 / 41 | N/A：无条件派发 |
| S0770 / Full / 0 | 21 / 2.448 | 32 / 8.444 | 36 | 59.5 | 27.5 / 33 / 41 | j23–j52: 9/20 |
| S0770 / Full / 1 | 20 / 2.156 | 31.5 / 8.065 | 36 | 59.5 | 27.5 / 33 / 41 | j23–j52: 9/20 |
| S0903 / Cons / 0 | 4 / 2.223 | 14.5 / 8.311 | 39.5 | 128.5 | 16 / 32 / 49 | N/A：无条件派发 |
| S0903 / Cons / 1 | 4.5 / 2.081 | 15 / 8.338 | 39.5 | 128.5 | 16 / 32 / 49 | N/A：无条件派发 |
| S0903 / Full / 0 | 11.5 / 2.172 | 23 / 8.068 | 39.5 | 128.5 | 16 / 32 / 49 | j10–j40: 9/20 |
| S0903 / Full / 1 | 11 / 2.163 | 21.5 / 8.440 | 39.5 | 128.5 | 16 / 32 / 49 | j10–j40: 9/20 |

- LB定义：M(F)允许所有已开始parts的**完整**GT字符数，甚至包括当前part尚未到达的未来文字；LB(F)=max(0,累计render字符数−M(F))。本8格的parts/reference完整性及累计render前提均通过；同时冻结报告首次>0、≥16、≥64，不挑阈值。它只给宽松的离线长度下界，不给首次真实语义错误时刻、不作为VAD/reset信号。
- 20-job低窗是首次20个实际conditional dispatch的回溯窗口中C/(C+R)<0.5，最少10个resolved；四格均为9/20=45%，U=0。表中保留原Owner epoch0的immutable job序列范围。两端准确audio/wall坐标不在本有界导出，故标UNKNOWN，不凭job序号换算秒数。S0770首次REFUTED dispatch的start位置为11.0秒，S0903为6.0秒；这也不等同于统计学change point。Conservative无条件派发，rolling为N/A，不填0或伪造unknown率。
- 全8格实际D2与C8超限均发生在trim后≥448条件之前；离线LB首次为正也先于该条件。因此，448不能凭这组时间先后被当成全部灾难性插入的唯一解释。该事实不能进一步区分拼接无端点、context演化、纠错递归和长度机制的因果份额。
- 最终CER仍为S0770 638.48%、S0903 251.53%，两臂及重复保持同一原选定结果。没有把失败覆盖为成功，也不把新安全检查称为已修复ASR。
- `model_seconds`只是原host call interval，可能重叠、含等待。累计call-elapsed/audio约在2.5–3秒首次>1，只是辅助诊断；它不是双GPU容量越界、总paid work或模型forward计数。实测服务边界以上表实际D/C为准。
- 缺少字符级时间对齐，且part边界通常不在8000-sample调用网格，故逐500ms **online prefixCER不可识别**。EOS与恰好相等的part/sample边界才有完整参考检查；文字重复、长度oracle、448输入条件和Consumer期限分别属于不同观测层。

## 可用于正文的英文段落（147 words）

An independent read-only audit matched all 5,529 actual dispatches in 36 fixed traces against the selected complete cut at each dispatched start frontier, retaining Owner and session identity. Of 1,901 conditional dispatches, 360 had confirmed inputs, 1,541 were refuted, and none were unresolved. Confirmation was 40/57 on normal short traces, 58/90 under controlled faults, and 96/924 and 166/830 on the two synthetic no-reset sources. Confirmation and use remained distinct: 354 conditional results became durable facts, 352 had an original Owner installation, and 354 were consumed, including two facts replayed after Owner failure. Six confirmed conditional jobs were not selected after injected failures. On both long sources, observed D2/C8 failures preceded the after-trim 448-token condition. An offline length oracle became positive at 27.5 and 16.0 seconds; neither it nor textual repetition estimates online prefix CER. These stress results characterize bounded failure conditions and do not estimate production prevalence.

建议正文只加一张分层小表；354/352/354的恢复差值和8格细边界放补充材料，避免把failure stress与正常服务效果合成一个比例。下表中Input-confirmed是最终完整输入相等，Durable/Consumer-used是实际使用层；两者不可合成单一“success rate”。

| Workload stratum | Conditional dispatches | Input-confirmed | Durable / Consumer-used |
| --- | ---: | ---: | ---: |
| Normal short | 57 | 40 | 40 / 40 |
| Controlled faults | 90 | 58 | 52 / 52 |
| No-reset S0770 stress | 924 | 96 | 96 / 96 |
| No-reset S0903 stress | 830 | 166 | 166 / 166 |

## 精确索引

机器可读索引为 `ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.index.json`，保留每个分组的case IDs、完整8格边界标量、滚动UID窗口、例外row定位、5文件SHA和725输入数。直接字段为：`SUMMARY.cells[*].eventual_input_pairing.conditional_dispatches`、各`conditional_*`计数、`long_boundary_diagnostics[*].actual_service_boundary`、`boundary_first.selected_Canonical_jobs`、`offline_oracle_started_part_length_bound`、`input_confirmation_markers`。本报告和索引属于对既有正式结果的本地解释，不改frozen source/CURRENT，不产生新的NN或serving结论。
