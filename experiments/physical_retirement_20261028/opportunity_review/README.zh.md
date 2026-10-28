# 物理退出机会的独立复核（2026-10-28）

实验 ID：`REVTRACE-PHYSICAL-RETIREMENT-OPPORTUNITY-REVIEW-20261028`。这是对已有真实 GPU 原始记录的独立分析，新增 GPU 调用为 0。没有把固定轨迹估计写成实际取消收益，也没有修改任何已有结果。分析脚本及其 SHA256、Python/平台、原始输入 SHA256、汇总与 gate 分别保存在本目录。

## 结论和判定

**GO：先做有边界的物理退出探针。服务试验优先采用有实际后续批次的 37-token 工作；256-token 长尾用于执行器可行性和异常资源隔离。** 现有证据不支持普遍吞吐提升，也不支持复杂因果取消已优于简单可信覆盖取消。

逐批独立复算得到 **98 次运行、1,603 个 Proposer 批次**，与原 `TAIL_OPPORTUNITY_BATCHES.csv` 的全部尾部数值及取消行集合完全一致，最大数值误差为 0。

13 个超过 5 秒的批尾全部同时满足：

- 是该次运行的最后一个 Proposer 批次；
- 包含来源 `1993-147149-0020` 的一个 256-token 触顶行；
- 这 13 行的实际模型音频 SHA、实际 conditioning token 序列和目标前沿完全相同，只有 **1 个执行输入上下文**；
- 都在声明的 Mixed-F2/Authority 安装时序实验条件下出现，不能解释为自然发生率或 13 个独立异常来源。

新来源 D_heldout 的 36 次运行中没有触顶行。它们的理想批尾合计 5.608806 秒，相应 Proposer 模型阶段合计 570.919301 秒，比例 **0.9824%**。单批最大 0.270054 秒；单次运行的多个批次累计最大 0.743404 秒。开发池与该确认池的 source ID、音频 SHA 和 speaker 均无交集。重复种子/进程并不能增加来源独立性。

## 取消能否在完成前因果可知

可以，限于这里检查的确定条件：某个已经安装的可信前沿覆盖该行的固定目标 `job.audio_end_sample`。该条件只需当前 Owner 的状态、job 身份和目标，无需预测该行未来 token 或完整结果。

当前最终执行源 `.execution/lp1_runtime/runtime/src/revtrace/live_qwen.py` 中：

- `_finish_commit` 先把 `install.state` 赋给 `s.state`，再记 `installed` 与 `commit` 事件；
- Proposer 完整结果接收路径已将 `audio_end_sample <= s.state.audio_frontier_window` 判为 `proposal-obsolete`；
- 覆盖重整只跳过已可信覆盖的窗口，保持 offered 输入的既有会计。

因此提前退出只是把现有“接收完整结果后会丢弃”的确定判据前移到 Worker 的 decode 安全点。它不产生可信写权限，不需要改变 Authority 选择，不以旧 parent 编号本身推断失效。

把取消控制的最早可见时间保守地换成 `commit` 日志记录时刻，所有批次中理想空间下降的最大值仅为 **66.18 微秒**。这说明原结果不是依赖一个在 Owner 尚不可见的未来覆盖事件。但真实 IPC、轮询、GPU 同步和安全点延迟尚未测量，不能由此推断实际反应很快。

完整完成、取消接受、取消终态和 BatchDrained 必须各自记账。现有 `CompleteRowStream.end()` 要求所有行完整终止，`RowDeliveryTap.finish()` 会补发并核对完整输出；新执行路径必须显式支持取消行，不能把未完成序列塞进原完成路径。仅请求取消不能释放 lease。固定布局中把一个已失效行标记停止，也不等于已经减少其他仍活跃行的 FLOPs；最小机制可先只实现“所有行完成或取消后提前结束整批”。

## 理想批尾估计的有效范围

独立脚本采用按时间排序的事件扫描：初始将物理批的行置为活跃；遇到观测完整终止事件就移除对应行；遇到已安装可信覆盖事件就移除被覆盖的活跃行；首个活跃集为空的时刻是理想 drain。它没有调用原扫描脚本，也没有直接复制原 max/min 实现。

这个扫描与原公式一致：在固定模型阶段内，`max(e_j) - max(min(e_j,c_j))`（按阶段起点截断），其中 `e_j` 是观测完整行终止，`c_j` 是可信首次覆盖目标的安装时刻。

这是固定轨迹、固定活跃行终止时钟、零控制成本下的理想**整批尾部**空间。它不包含未同步的 GPU kernel 抢占，不给 interior compaction/refill 估价，不包含保留后处理，不允许把并行 GPU 时间相加后从服务墙钟中减去。取消可能改变后续组批、模型时钟与可信安装顺序，所以它也不是一切新执行器端到端收益的普适上界。

## 最小探针清单

完整冻结身份、原 COMMAND、原配置、实际模型路径、音频路径/清单 SHA、原 Worker/Runtime 指纹、job 顺序和原 worker_records 行号都在 `PROBE_SHORTLIST.json`。其中 `selected_exact_targets` 保存所选行的完整 job、实际执行上下文、实际 model-input audit 和原始输出比较证据；原始输出只能用于核对，不能作为新模型结果注入。

供最小执行器探针直接消费的 `OPERATOR_PROBES.json` 还保存了三个完整物理 batch 的全部 peer job 定义与顺序：`cap256-standard-staggered-r0`、`medium37-standard-sync-r0`、`clean14-fine-sync-r0`。前两者将原覆盖时刻换算为相对原 neural phase 的取消请求时间（触顶行 1.614819 秒，37-token 行 1.547185 秒），第三个没有取消请求。该文件明确是固定时序的算子重放输入；新执行必须使用新源身份并测量新时钟，不能称为在线可信覆盖策略或真实服务收益。

| 优先级 | 原始单元 | 用途与固定轨迹机会 |
|---|---|---|
| 首个真实服务探针 | D_development `development-sync-mixed-standard-r0/r1/r2`，各批 `:5`，`proposal-8-137`，source `1993-147149-0020`，window 5 | 三次实际生成相同 37 tokens；理想尾部 0.949522 / 0.916105 / 0.925324 秒；各有 9 个实际后续 Proposer 批次。在理想退出时有 5 个会话仍有已释放而未提交的窗口。 |
| 强 Fine 对照 | D_development `development-sync-mixed-fine-r0/r1/r2`，各批 `:5`，同一 job/逻辑目标 | 相同 37-token 输出；理想尾部 0.818364 / 0.969749 / 0.887105 秒；各有 8 个实际后续 Proposer 批次。 |
| 大尾部执行器探针 | D_development `development-staggered-mixed-standard-r0`，`proposal-0:8c7ef881451a4b68a633ab631eacdb7c:15`，`proposal-8-169`，window 6 | 14 行，原模型阶段 13.631025 秒，理想尾部 12.002657 秒。14 行的原始顺序需保持。该批为最终批，只能先证明物理释放；服务改善需由实际未满足输入和 Consumer 结果证实。 |
| 重复异常上下文 | C `development-sync-mixed-hold_15-r0/r1/r2`，各批 `:6`，window 6 | 16 行、相同触顶上下文；理想尾部 11.523868 / 11.412345 / 11.463840 秒。含 1.5 秒 Authority 安装干预，属于机制/压力证据。 |
| 独立来源小机会 | D_heldout `heldout-staggered-clean-anchor_cost-r0`，`proposal-0:f4942a0d3fa04fdeba8ef2fa70afda1e:7` | 6 行、0.270054 秒理想尾部；主要用来界定正常开销和小窗口反应，不建议据此开大矩阵。 |
| 短批不触发控制 | D_heldout `heldout-sync-clean-fine-r0` 与 `heldout-sync-clean-standard-r0`，各批 `:1` | 16 行，约 0.81–0.83 秒模型阶段，理想尾部 0；测无取消情况下检查/IPC 的新增成本。 |

原大尾部期间确有其他合法服务义务，但它们不能被解释为已经排队的 Worker job：原 Owner 只在 Worker 空闲时创建并 enqueue 下一批。13 个大尾部期间，其他会话仍有 11–15 个会话的待提交窗口；其实际 Consumer 仍收到 37–51 次 Canonical 进展，Proposer 进展通常停止。最大的 anchor_cost-r2 在理想退出时有其他 11 个会话、19 个已释放未提交窗口、14 个尚不可见窗口；尾部期间它们仍接收 39 次 Canonical 显示。因而评估应测合法可见进展的停顿及后续期限，而不能声称 GPU0 长尾使整个双 GPU 服务完全冻结。

## 37-token 输入 fixture 和清洁对照

`F2_INPUT_FIXTURE.json` 提取了原 donor 文件身份、全部 12 个 donor、精确映射 `{0:5 -> 0, 2:5 -> 2, ..., 14:5 -> 14}`。原规则只在实际 Proposer job 的 `chunk_id >= 2` 且逻辑目标精确命中时替换**模型输入的 conditioning tokens**。source 1993 对应 session 8，使用 donor 8：`authority-clean-17` / `english-02`，65 个 token。原音频来自 8 TB 盘上的 LibriSpeech 资产，路径与完整音频 SHA 均在 shortlist 中；实际 window-5 prefix 音频 SHA 为 `5b629f56f04b09264b328625d8261acbb812dfc9d43c1b2a1cf65b691f86c628`。

当前最新 CLI 的 `online-study` 路径同时会切换选择/rho，且其 F2 规则是每会话首次 `end>=5`，不是原精确 mixed map。因此应只将上述输入 fixture 提取成共享、冻结的 fault-harness hook，接在共同 `_make_job` 路径上；不要为注入输入复活整个 CES 或 online-study 载体。实际新模型输出需重测，不能承诺新布局仍是 37 tokens。

`LOGICAL_TARGET_COMPARISON.json` 覆盖同来源 window 5/6 的 30 条有/无实际调度记录。C `clean/hold_0` 的三个重复在相同音频与相同声明 parent 下实际使用正常 31-token conditioning，各生成相同 14-token 输出，并在 Canonical 覆盖前已对真实 Consumer 可见。D sync Mixed 的 Fine 和 Standard 六次都使用相同 65-token donor conditioning，并生成同样的 37-token 输出。D_development 本身没有同池 clean Standard 单元，所以不能用历史数据假装已经做完该强对照；最新统一执行器需补 Fine/完整 Standard × clean/Mixed。

## 独立判断和下一步判据

简单可信覆盖取消就是目前最清楚、可在线判定的最小机制，必须作为强对照。若复杂因果规则只触发同一批 covered rows，则二者同效是预期结果，不能把时序噪声写成新算法胜利。父版本取消需要单独测它是否杀掉仍兼容且有服务价值的工作；watchdog 应在共享执行器上运行并计入合法长输出损失。任何额外价值需要真实数据证实。

先完成固定 batch 的相同输入、原 row-complete、取消但不物理退出、物理退出三类操作对照，核对保留行的完整输出、实际 drain 和下一批真正开算。随后在上述 sync 负载上跑原 row-complete、watchdog、父版本、简单覆盖、因果规则，并给 Fine/Standard 共享同一执行能力、可信选择、Consumer 和输入期限。只有无故障会话的真实停顿/期限得到重复改善，且正常开销与质量可接受，才值得扩大异常来源或负载。单个触顶输入即使回收 12 秒，也只是一条机制证据。

复算命令（先回到仓库根目录；不运行模型）：

```powershell
python experiments/physical_retirement_20261028/opportunity_review/independent_recount.py
python experiments/physical_retirement_20261028/opportunity_review/enrich_shortlist.py
```

主结果：`SUMMARY.json`、`BATCH_CHECK.csv`、`RUN_CHECK.csv`；独立性明细：`CAP_SOURCE_CONTEXTS.json`；探针：`PROBE_SHORTLIST.json`、`F2_INPUT_FIXTURE.json`、`LOGICAL_TARGET_COMPARISON.json`；逐输入审计：`INPUT_MANIFEST.json`、`ENRICH_INPUT_MANIFEST.json`。旧执行源 commit 与当前新执行源 commit 均应保留其原身份，新试验需按 repository_identity preflight 重新冻结。
