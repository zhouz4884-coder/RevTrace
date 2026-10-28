# H3 独立结果阅读：机会、内容效用与选择性系统主张

分析 ID：`REVTRACE-H3-INDEPENDENT-READING-20261028`。这是对已完成记录的 CPU 阅读和重算，没有新增 GPU 调用、修改执行配置或撰写论文。先读了 `PRE_RESULT_PREDICTIONS_v3.json` 的 P1–P4，再从 `H3_RESULTS_v2/{aggregate,usefulness,opportunities}` 的逐 run、逐 source 表独立求和；未沿用旧报告的判断。

**最强结果是 Qwen、rho1、staggered 的有条件组合价值。** 在该冻结主层中，完整组合同时比两个单因素方案保留更多及时且与 Canonical 一致的首次可见音频，并消除已记录的音频进度回退。sync 低机会层趋于收敛，jitter 的一个重复没有复现对 R-only 的优势，Whisper 的质量和机会边界也不支持普遍优势。H3 支持选择性主张，不能据此写成所有模型、所有负载或所有分支均获益。

## 1. 身份、样本单位和指标

- 实际执行源：`f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`；冻结计划 SHA256：`8a62b6849842aee0baa432f83c260b11686e328746b3b7f5bc652b9ec`。
- 正式接受 110/110 cells；22 个完整 2×2 blocks、22 个 Standard 正控比较。主层 60 cells = 3 cohorts × 2 models × 2 arrivals × 5 arms；paired_jitter 20 cells 只重用 cohort A；coarse 30 cells 为 rho3、sync。
- 独立内容只有 **24 条 source、24 位 speaker、714.110 秒**。880 个逐 source/run 行是重复观测，不是 880 位 speaker；模型、arm、arrival、coarse 和 jitter 不增加独立内容量。主层每个 model/arrival/arm 有 3 个 cohort runs，不能把 24 source 当成 24 次独立 GPU 部署。
- `R0_S0` = no-retain + checked_snapshot；`R0_S1` = no-retain + two_lane；`R1_S0` = retain + checked_snapshot；`R1_S1` = retain + two_lane。`STANDARD_FULL` 是作者实现的完整组合正控。各 arm 使用相同 guard kernel；此组全部为 row_complete、关闭物理提前退出，不能用 H3 宣称物理撤销收益。
- 176/176 个 block/source 的 Canonical 历史组包含全部五个 arms；144/144 个更宽的 source/model/rho/arrival/runtime 分组内，完整 F/Z/P/text 历史也一致，包括 paired_jitter。因而本组最终质量的跨 arm 相等有真实历史证据。
- 110/110 run 的 recorded audit 中 unauthorized admission、stale publication、root-incompatible actual view、certified-only violation、rejected/unfinished source、cancelled row、controlled input substitution 均为 0；最终 certified 音频覆盖率均为 1。它们是记录内安全证据，不能替代确定性证明。

本文主用 `U_norm = first_certified_dual_timely_audio_seconds + first_ahead_normalized_equal_dual_timely_audio_seconds`，`U_raw` 把 normalized_equal 换成 raw_equal。音频权重按每个 offered frontier 的首次实际覆盖 view 分配一次；ahead 内容要与完整可见 F 处后续选中的 Canonical 比较。当前所有 ahead 的 already-selected 数为 0，因此此处 all-equal 与 future-selected-equal 相等。**不能遗漏 first_certified 项**：例如 Qwen 主层 staggered 的 R11 有 168 秒先已 certified，ahead-only 的 512.760 秒只是 U=680.760 秒的一个组成部分。

`U` 是离线回看所得的 Canonical 一致性效用，不是在线核验、语义正确率或 ground truth。normalized 规则为 NFKC、casefold、统一弯引号、保留 Unicode 字母数字词和内部撇号、忽略其他标点；raw 与 normalized 必须分开。原服务 dual credit 只检查原 2/8 秒期限；与文本一致性的交集才进入 U。无相同 F 的 Canonical 边界保持 unknown，不计为错误，也不能补计为一致。

## 2. 所有冻结层的首次可见内容效用

下表均为 U_norm 秒，列顺序固定；主层和 coarse 每格 offered=714.110 秒，jitter 每格 offered=240.520 秒。`I=Y11-Y10-Y01+Y00` 为严格 2×2 算术交互。表中秒数保留三位小数，其他比率按显示精度四舍五入。

| 层 / 模型 / arrival | R00 | R01 | R10 | R11 | Standard | I |
|---|---:|---:|---:|---:|---:|---:|
| primary / Qwen / sync | 708.465 | 705.110 | 712.230 | 711.440 | 711.440 | +2.565 |
| primary / Qwen / staggered | 654.115 | 628.435 | 664.150 | 680.760 | 667.530 | +42.290 |
| primary / Whisper / sync | 412.000 | 414.000 | 412.000 | 412.000 | 419.320 | -2.000 |
| primary / Whisper / staggered | 422.000 | 424.000 | 422.000 | 422.000 | 448.790 | -2.000 |
| jitter / Qwen / sync | 239.355 | 239.355 | 238.565 | 238.565 | 238.565 | 0 |
| jitter / Qwen / staggered | 216.000 | 214.000 | 230.565 | 226.320 | 227.300 | -2.245 |
| jitter / Whisper / sync | 156.000 | 156.000 | 156.000 | 156.000 | 157.320 | 0 |
| jitter / Whisper / staggered | 168.000 | 168.000 | 166.000 | 166.000 | 164.000 | 0 |
| coarse / Qwen / sync | 227.570 | 227.790 | 231.450 | 231.450 | 231.450 | -0.220 |
| coarse / Whisper / sync | 92.010 | 92.010 | 92.010 | 92.010 | 92.010 | 0 |

Qwen primary staggered 的 U_raw=U_norm；R11 为 95.32985%，比 base 增加 26.645 秒 / 3.73122 个百分点，比 S-only 增加 52.325 秒，比 R-only 增加 16.610 秒，比 Standard 增加 13.230 秒。三个 cohort 的 U_norm 交互分别为 A +18.530、B +6.205、C +17.555 秒；不是只由一个正 cohort 形成。逐 source 的 R11 相对参考方案“改善/相同/变差”分别为：base 11/10/3，S-only 17/4/3，R-only 10/10/4，Standard 8/13/3。对 base、R-only、Standard 的逐 source 中位差均为 0；因此不能写成每条 source 都改善。

Qwen primary sync 的 R11 仅比 base 多 2.975 秒，22/24 sources 相同，且比 R-only **少 0.790 秒**。paired_jitter 的 Qwen staggered R11 比 base 多 10.320 秒，却比 R-only 少 4.245 秒、比 Standard 少 0.980 秒；其交互为 -2.245 秒。这是主层收益的重复稳定性边界，不能丢弃或把两次运行当作更多独立 speaker。

## 3. 实际安装时的组合机会

下表为 owner_install 时钟的 `compatible_opportunities/canonical_updates`；括号中是该 arm 对这些机会实际 retained/cleared 的次数。consumer_apply 的对应机会、兼容和 retained/cleared 等计数全部一致；owner_install 另有 inflight/unpublished job 字段，不能把两种时钟行当成两倍样本。

| 层 / 模型 / arrival | R00 | R01 | R10 | R11 | Standard |
|---|---:|---:|---:|---:|---:|
| primary / Qwen / sync | 2/368 (0/2) | 2/368 (2/0) | 3/368 (0/3) | 3/368 (3/0) | 2/368 (2/0) |
| primary / Qwen / staggered | 6/368 (0/6) | 4/368 (4/0) | 17/368 (0/17) | 18/368 (18/0) | 15/368 (15/0) |
| primary / Whisper / sync | 0/368 | 0/368 | 6/368 (0/6) | 14/368 (14/0) | 0/368 |
| primary / Whisper / staggered | 0/368 | 0/368 | 2/368 (0/2) | 19/368 (19/0) | 8/368 (8/0) |
| jitter / Qwen / sync | 0/125 | 0/125 | 0/125 | 0/125 | 0/125 |
| jitter / Qwen / staggered | 1/125 (0/1) | 2/125 (2/0) | 6/125 (0/6) | 5/125 (5/0) | 6/125 (6/0) |
| jitter / Whisper / sync | 0/125 | 0/125 | 5/125 (0/5) | 1/125 (1/0) | 0/125 |
| jitter / Whisper / staggered | 0/125 | 0/125 | 0/125 | 1/125 (1/0) | 0/125 |
| coarse / Qwen / sync | 8/128 (0/8) | 8/128 (8/0) | 8/128 (0/8) | 8/128 (8/0) | 8/128 (8/0) |
| coarse / Whisper / sync | 0/128 | 0/128 | 0/128 | 0/128 | 0/128 |

Qwen 主层 R11 的机会密度从 sync 3/368=0.81522% 上升到 staggered 18/368=4.89130%；有机会的 source 从 3/24 上升到 15/24，staggered 的单 source 最多 2 次。因此收益存在明确时序条件。R10 的 17 个兼容机会全部清除，R11 的 18 个全部保留，为“Owner 保留的工作还需要 Consumer 的对应发布规则”提供实际机制证据；但这两组事件不应被强制当成同一批一一配对机会。

机会计数是 arm 执行后产生的中介变量：改变调度或保留本身会改变可见 ahead 是否存在。不能把 `U/机会数` 当作随机化的每机会处理效果，不能用事后高机会 source 子集代替所有 offered 输入。

P1/P2 得到条件性支持：有完整合法链的机会确实被保留；低机会 Qwen sync 收敛。P3 只在 Whisper 上符合“改变粒度可改善质量同时减少兼容机会”的方向：R11 从 rho1 sync 14/368 到 rho3 0/128；Qwen 则从 3/368 到 8/128，不能宣称更粗粒度普遍降低机会。rho1/rho3 还是不同更新契约，绝不混池。

## 4. 进展连续性、期限、Standard 与质量边界

Qwen primary staggered 的服务统计如下。goodput 是 `sum(原期限内 dual credited audio)/sum(episode wall)`，不是 run goodput 的平均值。

| arm | 音频回退事件 / 秒 | 回退面积(音频秒×墙钟秒) | 擦除可见字符 | pooled goodput | GPU J/音频秒 |
|---|---:|---:|---:|---:|---:|
| R00 | 12 / 10.505 | 15.458 | 633 | 6.175532 | 59.475 |
| R01 | 1 / 0.560 | 0.258 | 524 | 5.958819 | 59.398 |
| R10 | 17 / 18.570 | 30.258 | 808 | 6.260896 | 59.466 |
| R11 | 0 / 0 | 0 | 569 | 6.453639 | 59.359 |
| Standard | 0 / 0 | 0 | 569 | 6.302505 | 59.467 |

R11 相对 base 的 pooled goodput 为约 +4.50%，是一个真实但有条件的端到端机会。能耗相差很小，不主张能源突破。音频回退为零并不等于文本没有修订：R11 仍擦除 569 个可见字符，比 S-only 的 524 多；它与 Standard 在此文本终点完全相同。逐 source 最长实际可见进展间隙的 R11-base 中位差为 -0.04975 秒，15/24 改善；但 R11-R-only 中位差为 +0.04959 秒，15/24 变差。因此“避免进度撤回”和“所有停顿都缩短”不是同一结果。

`aggregate/SPEAKER_BOOTSTRAP.json` 的样本输入来自 SOURCE_FACTORIAL_EFFECTS，给的是**严格交互**，不是 R11-base 对比。Qwen primary staggered 的逐 speaker 平均 dual_fraction 交互为 +5.8987 个百分点，描述性 95% cluster-bootstrap 区间 [1.1294,10.2795]；这是 source 等权的交互，和上文音频加权 +42.290/714.110=+5.92206 个百分点不同。各 source 共享 cohort/run 服务，此区间不是独立部署的总体优越性保证。

Whisper primary 的 R11 两种 arrival 的 U_norm 都与 base 和 R-only 相同，均比 S-only 少 2 秒。Standard 则有较高的原期限覆盖和 U：sync U=419.320 vs R11 412.000，staggered U=448.790 vs 422.000；代价是音频回退分别 27 次/73.320 秒和 32 次/85.500 秒，而 R11 两种均为 0。这是明确的期限/连续性权衡，不能把 Standard 宣称为失败正控，也不能把 R11 写成全面优于它。

最终质量按一次 source 集的 word-error 总数计算；这是英语 corpus，不能外推为中文质量。所有 arms、两种 arrival 完全相同：Qwen rho1 为 26/1908=**1.36268% WER**；Whisper rho1 为 1586/1908=**83.12369% WER**。Whisper 各 cohort 为 22.31013%、29.95392%、200.00000%；其 24 source 的中位 WER 为 21.05655%，两条 source 分别为 `composition-307-127535-0002-0003` 的 228/76=300% 和 `composition-1088-129236-0001-0002` 的 925/80=1156.25%。均值 84.08801% 是 cohort 宏平均，不应当作 pooled WER。异常跨 arm 保持相同，不支持把 fine Whisper 的任务质量失效归因于显示策略，P4 的适配器/反馈契约边界仍须保留。

rho3 的 Qwen WER 为 27/1908=1.41509%，Whisper 为 220/1908=11.53040%，Whisper source 最大 WER 降为 50.52632%。但 coarse 层不能包装成效用胜利：R11 Qwen 原期限 dual credited=701.450 秒，U_norm=231.450，U_raw=217.450，另有 **464.000 秒**及时 ahead 视图没有同 F 的 Canonical 对照；Whisper 则 U_norm=92.010、U_raw=34.815，及时不同 normalized 内容=144.100 秒，及时无同 F 对照=422.000 秒。这些 unmatched 是观测空缺，不是错误；不能用最终 WER 改善或 deadline credit 把它们补成已证实有用的早期内容。

全 110 cells 中原双 P99 gate 仅通过 7 个，全部为 Qwen。即使音频加权 timely coverage 达到 95% 或 99%，也不等于 whole-run 双 P99 通过。

## 5. 能保留和必须放弃的主张

**可以保留的最强主张：** 在相同 guard、相同 Canonical 完整历史和原 deadline 下，合法私有链保留与对应 Consumer 发布可以组合为一条有条件的连续进展路径。H3 的 Qwen rho1 staggered 三个 cohort 给出同向的 U 交互、零音频撤回及 modest 的服务 goodput 改善；同一设计的低机会和质量失效层给出可解释边界。

**应弱化或放弃：** 通用模型加速、每 source 获益、每负载强交互、全面优于 Standard、零文本修订、能耗显著下降、物理退休收益、普遍双 P99 达标、自然流量高覆盖或由 110 runs 推出大样本总体结论。尤其 jitter 是实测重复反例，Whisper fine 是任务质量边界，coarse 是同 F 对照不足的测量边界，三者不能合并为一个“失败率”。

判断：**H3 对选择性组合机制为有条件 GO；对普遍性能优势为 NO-GO。** 若下一步需要扩大主张，优先的可证伪问题是独立 cohort/service 重复能否保持 Qwen staggered 的 U 与期限收益，以及自然流量中这种兼容机会的真实密度；当前数据不允许直接宣称答案为正。

## 可核查输入

数据根：`D:\VLA_QWEN\RevTrace\experiments\physical_retirement_20261028\H3_RESULTS_v2`；原始执行记录根：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/confirmation_v3/`。Linux 分析环境记录为 Python 3.12.13、Linux 5.15.0-139-generic。各 cell 的源、冻结配置、环境和 raw 位置由 `aggregate/COVERAGE.json`、`aggregate/ANALYSIS_RECORD.json` 与原 run record 链接；此阅读没有把历史计划的 stale out alias 作为执行 argv/实际 output。aggregate 接受 110 个实测 cell，并单独记载 110 个历史 out-alias disagreement。

| 文件 | SHA256 |
|---|---|
| aggregate/RUNS.json | `21826f7ef2bdb344d50f292efd8904c28aa5d22b4d342fc58ef59a2981a0626e` |
| aggregate/SOURCE_METRICS.json | `06748c7a58f0dbb2e168ee7a7d1a5867f0809aef9a564d06088dd6a0b2751f9c` |
| aggregate/SPEAKER_BOOTSTRAP.json | `9b2c515d3d58a7d73a7de4710ddc9fffa0283a202b70b3aa821850912227e608` |
| usefulness/RUNS.json | `6f076dd7d63bc25e679dd2572ecb2958f02e05d6a895b37de30696ad98b95652` |
| usefulness/SOURCE_METRICS.json | `b44c13fac4cc6f9a0a14568869784ce734caa4305b3f621d188470f15816afdd` |
| opportunities/STRATIFIED_RATES.json | `db4faffb80eea6b7ed76cdf2d8fb2407cba1554909363ad4d43ff46ba4f3cb50` |
| opportunities/SOURCE_OPPORTUNITIES.json | `ffecde5a1f05530146e4ce2b92be768ca69f3924259dff3dbdb4bf5200459f36` |
