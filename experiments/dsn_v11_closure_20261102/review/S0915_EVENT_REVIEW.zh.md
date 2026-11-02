# S0915 原事件人工只读审查

审查 ID：`S0915_EVENT_REVIEW_20261102`。范围为已完成的新 8-speaker 确认银行中 `BAC009S0915W0286` 的两个 RevTrace/fullcall repeat。只读取既有 summary、原盘 JSON/JSONL 和冻结实现；没有运行新模型、重放分析实验或改动 CURRENT、运行源、日志。本文件中的差值是人工核对既有时间戳，不能替代新的分项性能测量。

## 结论

两次 run 的 D2 失败都集中在最后 7 个 frontier（6.0 s 至 EOS），并非恢复、非法安装、丢消息或 Consumer 拒绝。晚段的原 corrector 连续改变选择，提前启动的下一任务因完整父状态不符不能成为实际主链，实际父状态安装后才重派发合法任务。选中任务完整模型调用约 0.53–0.83 s，而输入每 0.5 s 到达；跨多个修订累积的父依赖关键路径，使第一交付从略超 2 s 增至约 3.086 s。两个 fresh-process repeat 均出现同样的 frontier 位置和接近的时序。

首个 6.0 s frontier 是阈值边缘：r0 首次 publication 接收仍在截止前 9.458 ms，实际 Consumer 观察在截止后 22.780 ms；这条路径中存在同步审计日志写入及完整 Consumer 应用，不能将其全部解释为模型时间。r1 在 publication 接收时已晚 11.604 ms。其余六个 frontier 在 publication 接收时已晚至少 271 ms，几十毫秒的交付路径税不能解释其整体失败。

这支持论文保留“收益取决于合法依赖能否跨修订延续及原模型服务节拍”的边界；不支持将 S0915 的 D2 失败写成协调器异常，也不支持声称去掉某项税就能使整个 run 达标。

## 证据身份与定位

- 原盘共同根：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_confirmation_20261102/service_confirmation_v1/cells/`。
- case：`SC_NEWTEST_BAC009S0915W0286_fullcall_r0` 与 `SC_NEWTEST_BAC009S0915W0286_fullcall_r1`。下文 `r0/`、`r1/` 均指这两个原目录。
- 既有执行 NN4f 源：`4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`；既有确认 driver：`d865af11e9a8d6c451146942d1708a8caed8d1d9`。本审查沿用已闭合运行身份，不另造实验源。
- 本地终结统计：`experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/SUMMARY.json:189–201`：两次 offered 共 17.996125 audio-s；Conservative 信用 6.0 s，RevTrace 11.0 s，配对增益 5.0 s / 27.783759 pp；两策略此 speaker 的全 run gate 均 0/2。RevTrace 的 model-to-drain board 能量也较高（12837.116 J 对 11991.150 J），不应隐藏这一成本。

## 时钟及起点

`ORIGIN.json` 的 `origin_perf` 分别为 r0 `5361984.144473837`、r1 `5363091.297502208`。下表全部是该 run 原 `perf_counter` 减本 run origin 的秒数；offer 为音频 frontier/16000，不使用 `author_start_time_wall`，也不使用本次审查的墙钟。

`worker_results.jsonl:1–2` 中两个 READY 均早于 origin：r0 full0 −1.000529 s、full1 −0.047284 s；r1 full0 −4.618699 s、full1 −0.039811 s。`stage_worker.py:19–25` 在真实 warmup 后发送 READY，`resilience_trial.py:125–129` 在 Owner ready 后建立服务 origin。约 46–57 s 的模型加载以及约 49–59 s 的加载加 warmup 不在这些 D2 延迟内。

## 七个首次实际交付的关键链

`Dispatch` 是 `dispatch.jsonl.job.dispatched_perf`；`Begin` 是 completed record 的 `worker_job_begin_perf`；`ASR` 是 `asr_early.produced_perf`；`Pub recv` 是 `publications.jsonl.received_perf`；`D` 是实际 `consumer.jsonl.observed`；`Result` 是 completed `sent_perf`；`Install` 是 `owner_events.jsonl.canonical_install.observed`。D 均来自 `kind=private`，发生于完整 C/U 结果和其 Canonical 安装之前。

### Repeat 0

| F/offer (s) | job | Dispatch | Begin | ASR | Pub recv | D | Result | Install |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6.000000 | 015 | 7.590534 | 7.593459 | 7.976400 | 7.990542 | 8.022780 | 8.243838 | 8.273002 |
| 6.500000 | 017 | 8.277850 | 8.282248 | 8.763316 | 8.771387 | 8.819514 | 9.027442 | 9.051436 |
| 7.000000 | 019 | 9.056292 | 9.061565 | 9.356205 | 9.369395 | 9.402830 | 9.616880 | 9.645574 |
| 7.500000 | 021 | 9.650327 | 9.654548 | 10.144655 | 10.160523 | 10.219864 | 10.401075 | 10.432430 |
| 8.000000 | 023 | 10.437705 | 10.442622 | 10.734321 | 10.741684 | 10.773764 | 11.016753 | 11.045380 |
| 8.500000 | 025 | 11.050231 | 11.054728 | 11.453883 | 11.468862 | 11.502190 | 11.718582 | 11.753722 |
| 8.998063 | 026 | 11.473361 | 11.477365 | 12.051914 | 12.064869 | 12.083728 | 12.303689 | 12.350765 |

逐行原定位：dispatch 第 15/17/19/21/23/25/26 行；worker ASR 第 27/30/33/36/39/42/44 行，completed 第 28/31/34/37/40/43/45 行；owner install 第 26/28/30/32/34/36/38 行；Consumer 第 33/36/39/42/45/48/51 行，publication_id 同该行号。

### Repeat 1

| F/offer (s) | job | Dispatch | Begin | ASR | Pub recv | D | Result | Install |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6.000000 | 015 | 7.607358 | 7.610896 | 7.998608 | 8.011604 | 8.048483 | 8.265180 | 8.288637 |
| 6.500000 | 017 | 8.293149 | 8.297980 | 8.774343 | 8.780045 | 8.839379 | 9.046125 | 9.078726 |
| 7.000000 | 019 | 9.082859 | 9.088723 | 9.379622 | 9.388332 | 9.419717 | 9.639336 | 9.669770 |
| 7.500000 | 021 | 9.672810 | 9.679056 | 10.144696 | 10.155041 | 10.196823 | 10.402169 | 10.437644 |
| 8.000000 | 023 | 10.439829 | 10.442705 | 10.726312 | 10.732899 | 10.768878 | 10.981802 | 11.037149 |
| 8.500000 | 025 | 11.040046 | 11.042944 | 11.425966 | 11.438477 | 11.521866 | 11.695774 | 11.730784 |
| 8.998063 | 026 | 11.445397 | 11.449369 | 12.029409 | 12.040660 | 12.082267 | 12.284050 | 12.362167 |

原定位：dispatch 第 15/17/19/21/23/25/26 行；worker ASR 第 27/30/34/37/40/42/45 行，completed 第 28/31/35/38/41/44/46 行；owner install 第 26/28/30/32/34/36/38 行；Consumer 第 33/36/39/42/45/48/51 行。两 run 的 `consumer_rejections.jsonl` 均 0 行。

## 为什么提前计算未能继续变成合法主链

两个 run 均派发 26 个 full job、实际选择 18 个 frontier。r0 的 8 个非选中 job 为 004/008/014/016/018/020/022/024，全部是 ASR-prefix 后退出；r1 相同 8 个 job 中 018 完整跑完后 discarded，其余 7 个退出。不能把 26 次派发当作 26 个有效原生结果。

晚段已选 job 013/015/017/019/021/023 的 completed record 均 `selection_changed=true`、`native_model_evaluated=true`、`stage_execution=original_full_infer`。它们之后提前启动的 job 014/016/018/020/022/024 都冻结了与后来实际 Canonical 不同的完整起点。job 025 的选择未改，随后 job 026 得以从提前分支晋升并安装；这也是反证，不能说本 speaker 的全部提前工作一律无效。

最小原证据（r0 `worker_results.jsonl:26`，job014）为：

```json
{"kind":"abandoned","job_id":"e0-j000000014","target_end":96000,
 "proof":{"kind":"actual_canonical_disagrees_with_complete_start","witness_frontier":88000,
  "expected_cut_sha":"acb6ea68323362e00b01ed91e602eb8636e9b47e486dee9ce4be877d2d0f4108",
  "actual_cut_sha":"45c26582835c577e756637a35d842926e4170caa5ab975342f49c214484f7f3f"},
 "asr_prefix_executed":true,"learned_C_executed":false,"C_U_completed":false}
```

r0 另 5 个晚段退出的 witness_frontier 分别 96000/104000/112000/120000/128000（worker 行 29/32/35/38/41）。r1 的对应行 29/36/39/43 提供四个退出见证；其 job018 完整结果在 worker 行33，`policy_audit.jsonl:48` 为 `discarded_full`，不能误写成提前退出。

实现依据：`fullspec_policy.py:34–43` 对完整起点相同允许保留，只在该任务实际起点 frontier 的真实 Canonical 见证不同时否定资格；`stage_worker.py:48–58` 在 `before_corrector` 检查已知失效后发 abandoned。这些原记录说明取消没有免除已支付的 ASR prefix，也说明不能为节省时间把未匹配的 complete start 当合法。

## 归因候选、反证及论文意义

1. **父依赖加原模型服务节拍是主要候选，有直接时序支持。** r0 job013 install=7.588372，合法 job015 dispatch=7.590534；之后合法重派发在前一父 install 后约 2–5 ms。r1 对应差值也为数毫秒。late job015/017/019/021/023 的 dispatch 已比其 offer 晚约 1.59–2.94 s。它们原完整模型时间分别为 r0 0.642888/0.732651/0.542188/0.733221/0.563673 s，r1 0.643239/0.740867/0.538196/0.715418/0.530870 s。由于多个预测父被实际选择反驳，0.5 s 负载节拍下的并行流水不能持续隐藏这些调用。
2. **不是已知的长期空闲派发缺口。** 上述选中 job 的 dispatch→worker begin 约 3–6 ms；r0 job014 还在另一槽运行到7.854931时，job015已在7.593459开始。无用分支 wall 不能直接当作合法主链被阻塞的同长度延误。没有反事实同输入移除试验，因此也不能排除两 GPU/CPU/磁盘资源竞争的次要影响。
3. **首个 miss 可能受交付与审计路径税影响，不能直接叫 guard cost。** `resilience_trial.py:52` 的 `publications=Journal(...,True)`、`:132–133` 的“写原 publication 日志再 Consumer.apply”，以及 `native_service.py:24–28` 的 flush/fsync 说明这段包含同步日志成本；还包含接收后队列、验证、状态应用等未分项计时。r0 F6 的 Pub recv→D 为32.238 ms，足以跨越其剩余9.458 ms；r1为36.879 ms，但接收时已过deadline。现有记录不提供这段每项实际起止，不能把整体差值宣称为 fsync 单项测量或获胜反事实。
4. **不是启动加载、丢失终点或 Consumer 拒绝。** READY在origin前，D/C终点均存在，Consumer rejection日志为空；两个 run 的 C99约3.39–3.40 s，全部C8满足。原 full-run D2 gate 仍失败，应保留而不靠“全部C8满足”遮盖。

建议正文只用一句边界解释：连续的真实选择改写可反复否定提前任务的完整父状态，使服务受合法父依赖和原模型节拍限制；安全保留不能承诺所有来源均满足 D2。可将本事件表留在有界附加证据，不增新 GPU 矩阵。

若后续确需修复首个阈值边缘 miss，最小可证伪目标应先是同合同下分离已有 publication 审计写入/接收队列/Consumer.apply 的计时，并保留真实原时钟和全 offered 分母；不能仅把 received_perf 替换成实际 D，也不能由离线减去日志时间宣称部署获益。本轮未实施该测量或修复。

## 追加：publication 审计的协议角色及六个失败 run 的 EOS

`publications.jsonl` 在当前在线路径中是审计输出，而非 Consumer 安装资格的证据源：

- `resilience_trial.py:52,132–134` 创建/写入该日志，之后调用 Consumer，再发送 ACK；在线路径没有读取该日志的调用。
- `resilience_consumer.py:26–43,48–76` 的 Canonical 验证读取 `facts.wal` 的实际 frame/receipt；private 验证读取当前 Consumer root 及消息中的完整 steps。两者均不读 publication 审计文件。
- Owner/worker 故障恢复位于 `resilience_trial.py:85–99`：扫描 `facts.wal`，`consumer.replay_fact`，再对内存保存的 `old_publication` 执行 retired-Owner fence；不从 publication 日志恢复。
- `resilience_owner.py:88–89` 在 ACK 时释放 `pending[publication_id]` 并更新 `consumer_pins`；`:155–157` 将尚待消费及实际显示的引用保护到历史回收。ACK 位于原 Consumer.apply 成功之后。

因此，若只将 `publications.write` 移到 `Consumer.apply` 后、ACK 前，在当前“Supervisor、Consumer、存储存活；Owner+workers 可故障”的模型内，没有发现它会改变 EL/AU/SUP 的资格、完整应用内容或 ACK 在应用之后的关系。但是它会改变审计的“原 publication 持久化先于实际应用”次序：publication 日志写入失败时，原实现尚未应用，新顺序可能已应用；若把 Supervisor/存储故障扩大进模型，还会出现 Consumer 记录已有而原 publication 审计未落盘的窗口。它不是未经控制即可宣称语义完全相同的改动。并且同步写入仍会阻塞本次 ACK 与后续 supervisor 消费，并未消除累计成本。此处未写补丁。

六个 fullcall 未通过原完整服务 gate 的 run，EOS 首次实际可见对应的原 publication 收包已经全部晚于 D2：

| Speaker/repeat | EOS frames | Pub/Consumer 行及 ID | 首次 Pub recv − offer (s) | 实际 D − offer (s) | Pub recv→D (ms) |
|---|---:|---:|---:|---:|---:|
| S0902/r0 | 137055 | 52 | 2.282539 | 2.314063 | 31.524 |
| S0902/r1 | 137055 | 52 | 2.784568 | 2.825579 | 41.011 |
| S0901/r0 | 130209 | 48 | 2.319424 | 2.497232 | 177.808 |
| S0901/r1 | 130209 | 48 | 2.448315 | 2.635833 | 187.518 |
| S0915/r0 | 143969 | 51 | 3.066806 | 3.085665 | 18.859 |
| S0915/r1 | 143969 | 51 | 3.042598 | 3.084205 | 41.607 |

原 case 均为共同 raw 根下 `SC_NEWTEST_BAC009<Speaker>W<utterance>_fullcall_r<repeat>/`，其中 S0902=`W0343`、S0901=`W0183`、S0915=`W0286`。每行由该 case `CONFIG.json.settings.sources[0].frames`、`ORIGIN.json.origin_perf`、首次 `consumer.jsonl.visible_frontier>=EOS且text非空` 的记录，及同 publication_id 的 `publications.jsonl.event` 定位。六个首次 EOS D 均为 private；对应 job 分别为 S0902 job024、S0901 job018、S0915 job026。

**机会判断：不为局部日志重排启动新的 GPU 修补矩阵（NO-GO）。** 当前时间戳显示的单次前置审计/应用路径税不能单独解释任何失败 run 的 EOS；至多说明 S0915/r0 的第一个 0.5 audio-s credit 是边缘候选。不能据这些差值简单相减，推断移除全部累计日志会产生怎样的新程序时间轴。可继续保留这一实现候选和测量缺口；若今后有独立证据显示显著端到端机会，再单独冻结补丁、CPU 协议控制和同输入实测。模型父依赖本身不列作代码错误。
