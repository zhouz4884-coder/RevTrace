# RevTrace 统一组合的独立确认设计

本设计检验的能力是：可信反馈状态推进后，系统能否保留仍合法的计算分支，并让实际 Consumer 持续获得这些进展。物理退出另作研究；本确认的所有格子固定使用原 `row_complete`，无 F2 注入、无 CES、无等待、无 prefix 复用。即使新增退出没有服务收益，本确认也完整执行。

## 已完成的数据准备

原池在 `context_recovery_20261028/publication_update_v2/context_holdout_freeze_v1`：48 条 90 秒重构流，24 个 speaker/chapter 簇，318 个不重复 utterance，原冻结 manifest SHA256 为 `2be8fc874313393a7564272bed714e3a3cb5ab50751fe49dfe20280bf094b9b0`。这是实验未使用的确认池；是否进入过模型预训练未知。原冻结及后续 context 记录报告 0 次 ASR；本次准备确实没有导入或运行模型。没有把一次保留清单检查升级为对任意未归档私人代码的穷尽证明。

本次从原冻结 Parquet 的 `id/text/speaker_id/chapter_id` 列取回 318 条完整文本，按 utterance ID 重建 48/48 条原完整 reference，逐条完全相等。历史排除清单 SHA 为 `38e5ce1b52f153525bcc42158c3a9f9267d2f8e831ce1653632f3cabf5805f65`，含 11,229 个 source ID 和 151 个 speaker ID。原池及所选片段对该清单的 utterance/speaker 交集均为 0；与 V6 开发池、V6 确认池的 speaker/source 交集也为 0。

**规则在 ASR 前固定：** 按原 manifest 顺序，每个 speaker 只用其第一条 90 秒流；枚举所有连续完整 utterance 区间，只保留 25–35 秒，取最接近 30 秒者，同距离取最早起点、再取最早终点。所有 48 条原流都有合法区间，共 258 个候选；没有为某位说话人缺少候选而换来源。原来的 0.1 秒间隔保留，开头和末尾不加补齐静音，utterance 内不裁剪。reference 是所选完整 utterance 原文本的顺序连接，没有按时间或 token 比例切文本。

CPU 实际落盘已通过：**24 个说话人、24 条流、58 个完整 utterance、714.11 秒，单流 28.265–31.31 秒，45,704,960 字节音频**。所有新音频只在 8 TB 盘。检查包括两个 Parquet 的完整 SHA、原 FLAC 编码 SHA、90 秒父流文件/解码 float32 SHA、逐 utterance 解码样本与父流原区间完全相等、新裁剪 WAV 的 float32 往返相等。最终数据 manifest SHA 为 `1c603e5f90a281181973f3108bcbf3fe9c62e7b01ad35aef394434834c082571`。

CPU 准备源是独立、干净的提交 `ca7551a11e18d8800f216be8c0c6d7799fd5f730`，不改运行源 v1。其完整 manifest 与 Git bundle 已取回本目录，供根仓库导入实际对象。最初的 `git init -b` 在服务器旧 Git 上失败，发生在任何资产准备进程启动前；兼容命令修复与原失败记录保留。CPU 准备的 Gate 为 `PASS_CPU_EXACT_UTTERANCE_ASSET_FREEZE_NO_ASR`。

## 实验盘上的确定路径

数据根：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/datasets/revtrace/composition_confirmation_20261028/utterance_boundary_v1`

总清单与三个互不重叠的 8-speaker 区块：

| 清单 | 路径（均在下列 inputs 根） | SHA256 |
|---|---|---|
| 完整数据 | `MANIFEST.json` | `1c603e5f90a281181973f3108bcbf3fe9c62e7b01ad35aef394434834c082571` |
| A：240.52 秒 | `COHORT_A.json` | `db27422abbfc6c0e9df56e18f8087385dd683ff339ab2c241df25fe70a563bd2` |
| B：237.58 秒 | `COHORT_B.json` | `b0655e01e338ff96c548d2d63a08792bfe2f59d8ee2f2ed175fd25e93bfa659a` |
| C：236.01 秒 | `COHORT_C.json` | `fa74c3f4794a8ce40f7da7b4cef6729e18e1869906df6ee77fd08cebff5288c3` |

inputs 根的完整路径为：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/composition_confirmation_v1/inputs/`

本目录 `materialized/` 只是上述有界 JSON 记录的字节一致副本，没有音频。原样本起止、utterance ID、完整 reference、父资产 SHA 均在清单内。第二条 90 秒流/说话人仍保留，未为本次方案消耗。

## 五臂与统一合法性要求

| 臂 | 分支保留 | Consumer | 目的 |
|---|---|---|---|
| R0_S0 | 关 | checked_snapshot | 保守且完整合法的参照 |
| R0_S1 | 关 | two_lane | 只保留显示协调能力 |
| R1_S0 | 开 | checked_snapshot | 保留计算、仍在 Canonical 更新时清掉旧 tentative 显示 |
| R1_S1 | 开 | two_lane | 完整组合 |
| STANDARD_FULL | 开 | two_lane | 完整 Standard 的替代实现正控 |

四个因子臂均用 `dgft_original` 载体；完整 Standard 用 `standard_fair`。同一小区块使用相同的 8 条完整音频、到达时刻、模型精度、GPU、MB16、256-token 原预算、Authority 频率、WAL、实际 Consumer 和原 D2/C8 期限。所有臂都走 full kernel、event-COW、D1、输入债务账本、完整 FP32 Authority 生成；不以较弱写入验证换性能。

`checked_snapshot` 必须同时满足：新到达的 provisional 若不兼容就拒绝；每次应用 Canonical 都清空旧 tentative，不跨该更新保留。它与 two_lane 共用核查入口与合法性合同。旧未经完整合法性检查的 snapshot 不能直接拿来占这个安全基线的位置。

source v2 的 Consumer 扩展完成并通过 CPU/旧开发输入检查后，才使用确认池。执行源固定路径是 `P/source_v2`，完整源码清单是 `P/SOURCE_v2.json`，其中 `P=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_physical_retirement_20261028`。最终计划已绑定 commit `1d8c30804a945570429d85d934b3bfcba6171a43` 与源码清单 SHA `5b1527bdcb20e165bc69f5002e3092a38b8ec773606828936c211ed595781f63`；每格仍须在 ASR 前核验干净源码、环境及输入身份。

## 110 个预先声明的单元

- rho1：两个适配器 × sync/staggered 两种到达 × 三个独立说话人区块 × 五臂 = **60 格**。
- rho3：两个适配器 × sync × 三个区块 × 五臂 = **30 格**。
- 测量抖动控制：区块 A、rho1、两个适配器、两种到达、五臂，再完整重复一次 = **20 格**。

模型为 Qwen3-ASR-1.7B 与 Whisper-base.en。Whisper 固定 `reserve-generation-tail-v1`，其条件视图合同与质量结果单独记录，完整 Canonical 历史不能被截断。

三个独立来源区块按原 speaker 顺序 round-robin 分配，每块 8 位说话人。固定 c8，sync 的 offset 全为 0，staggered 的 offset 为 `sid*0.25s`。旧最终载体的 c16 错峰点整 run 双 P99 未通过，因此不直接把已知过载点当唯一确认；c8 位于历史 c4 小规模点和 c16 点之间，保留中等争用。这里没有声称旧来源容量已证明新 30 秒流必定满足 SLO。必要的载体容量检查只用旧开发输入；不根据确认结果挑 c8/c4、改到达间隔或删除失败来源。

每个五臂配对区块完整连续运行；五臂顺序使用固定 Latin 循环，第二循环反向；模型先后按来源/到达小区块交替，来源区块间反转到达顺序。每个适配器共 11 个五臂区块，任一臂处于任一顺序位置 2 或 3 次。顺序不读取音频识别结果、时钟结果或 gate 表现。

`PLAN.json` 的 `cells` 是唯一待执行列表；每格都含 `cell_id/cohort/adapter/rho/arrival/repeat/retain/confirmation_consumer/method/manifest/sessions/policy`、输入清单 SHA、完整 argv 和唯一 `output` 路径。实验盘上的不可变计划为 `P/CONFIRMATION_PLAN_v2_FROZEN.json`，SHA 为 `a13745268829a99a4df2eb4192967587ad0ad506b7edfb9d70821e4322599d83`。输出根是：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/confirmation_v2/<cell_id>`

CPU 资产准备时保存了较早的计划快照（`PLAN_ASSET_PREP_v1.json`）；音频选择、区块、模型与格子集合不变。最终 v2 计划补全实际 Consumer 参数、确定执行路径、严格 Latin 顺序平衡及最终运行源身份；在第一次确认 ASR 前冻结。保留较早未绑定运行源的计划 `PLAN_PRE_RUNTIME_v2.json` 和原实验盘 `P/CONFIRMATION_PLAN_v2.json`，不回写 CPU 资产准备身份。

## 测量和判定

主结果同时报告合法可见音频覆盖/其回撤、已完成但未能保留的合法工作、连续可见停顿、所有 offered 前沿的 D2/C8 Goodput 与完整 run P99、可信覆盖、最终 WER/CER、未完成/已接受债务和双 GPU 能耗。只看第一次显示会遗漏后续撤回；只看“从未回退”又会让延迟到 Canonical 才显示的保守实现占便宜。因此连续进展和原期限必须一起呈现。

额外记录真实 Canonical 更新中有多少次已经存在领先的、因果兼容的 Private 进展。这是机会密度分母。若新来源的机会少，就报告少；不能事后只展示受益的窗口。兼容/不兼容分开：合法兼容进展的保留与应撤销的不兼容进展是不同结果，不能追求无条件零回撤。

对每个来源计算因子主效应与交互，再按说话人聚类统计；重复、窗口和配对五臂留在同一聚类。三个区块与 A 的额外重复分列，独立样本是 24 位说话人，不是 110 个单元或几千个窗口。小样本区块级不确定性、每个适配器与负载失败都保留。完整 Standard 同效是正控成功，不要求它失败。

代码/合法性失败会停止后续配对格并保留全部 raw；修复得到新 source/freeze，完整重跑受影响的配对区块。性能差或机制无收益不会触发换数据、换阈值、删失败来源；按原计划记录。这不是预注册“必须出现某个百分比收益”的承诺。

## 预算是工作量，尚无确认结果

110 格合计 offered 音频 **26,233.7 秒**。在全部完整完成的合同下，固定 Authority 网格对应 **11,140 个完整行**；Private fine 网格最多 **13,540 行**，覆盖跳过可能减少实际 dispatch。两者都不等于物理 GPU 调用次数，实际组批和取消均以 raw 计量。

每格外层 timeout 420 秒，合计串行故障上界 **46,200 秒（12 小时 50 分钟）**，双板预留上界 **25 小时 40 分钟 GPU-hours**。这是把所有格都运行到 timeout 的上界，不能当预期实际耗时或能耗。所有确认 ASR 目前仍为 0；已完成的是独立数据和元数据/执行设计。

## 相关有界文件

`DATA_PROVENANCE.json`、`EXPECTED_COSTS.json`、`CONFIG_TEMPLATES.json`、`PLAN.json`、`materialized/` 为当前交付。`build_confirmation_plan.py` 可复算选择、交集和格子；`materialize_streams.py` 与 `ASSET_SOURCE_v1.json/ASSET_BUILDER_v1.bundle` 保留实际 CPU 构造来源。新增机会与论文判断另见 `INDEPENDENT_OPPORTUNITIES.md`。
