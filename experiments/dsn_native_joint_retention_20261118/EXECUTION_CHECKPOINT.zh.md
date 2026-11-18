# 2026-11-18原生R×S实验执行检查点

## 用户目标与边界

认真核查三份AI审稿意见，选择能增强DSN竞争力的实验，完成后报告结果；不修改论文。本轮已对当前v18目录全部230份文件做只读SHA快照。用户后来询问进度，已答预计剩余约2–3小时，需坚持完成全80格和独立核验，不能以pilot结束当任务完成。

## 已冻结身份

- Runtime：`11453433c154aeffbff703c4c8dc9697421430e1`，67文件；actualConsumer外层`consumer_retain_views`控制视图保留，保留所有输入/选择/路径校验及Owner计算依赖。正式315项CPU测试通过。
- Controller/reference generator：`1bd3b01265a57d844c192e88573dc2a13860f64f`，22文件，正式72项CPU测试通过。
- Independent actual-view auditor：`0571d51d85542e1eaf000be8082585a66e5978be`，20文件，正式53项CPU测试通过。
- Post-campaign recount：`f29c2706e365df86ea18eecbb048a8f635976d36`，`analysis_source`3文件；尚未执行，必须完整80格镜像后运行。
- Readiness复用已冻结3文件source `3fb1951ba58b74110403c72d885efa8077e3140c`，31模型资产＋9WAV、15,848,006,117bytes全SHA核验通过，已暖文件缓存。
- Production support依赖：`a13fa0a335529dc188f7e738877a3acd027ce4a7`，18文件。远端源/manifest在旧v16计划中，本地`baseline/support_inspection`有3个已核代码文件，最终需完整manifest＋bundle/已有已发布地址。

`CURRENT.json`已合法激活新runtime1145，旧指针在`baseline/CURRENT_BEFORE.json`。Root legacy HEAD7372133保持不动；完整runtime/controller/auditor bundle已fetch到Root refs供preflight解析。

## 远端路径与连接

使用`experiments/dsn_v11_closure_20261102/ops/remote.py`的`Remote`，通过现有Windows Credential Manager凭据；不打印凭据。

B=`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9`
P=`B/projects/revtrace_dsn_native_joint_retention_20261118`
O=`B/results/revtrace/dsn_native_joint_retention_20261118`
Python=`B/envs/revtrace-streamcorrect-20261028/bin/python`
GPU0=`GPU-ef01d441-985f-50b3-6e64-5d4c3e2def3a`，GPU1=`GPU-a696ce9a-7137-cf6f-b4d3-deb992a72f28`，双3090，各24GB。

## 实验与当前进展

参照`REFERENCE8_V3`完成PASS：8来源、141连续original steps＋282 exact-input-restored steps，声明1warmup；133＋266＋1=400条实际神经评估，loader内部call未单独计数。只有这个参照发生模型执行。V1/V2是加载前的operator回执字段/来源顺序绑定失败，模型调用0，失败Root_closeout保留。不能重标为GPU负结果或抹掉。

全80格协议与顺序事前固定在`plans/SCIENTIFIC_PROTOCOL.json`。每source两次fresh-process，repeat1反转本source的五条件顺序、交换primary GPU。来源为既有八source，不是新独立语料。500ms、D2/C8、全部offered含EOS不变。

四因子臂：r0s0=Ready-only＋Consumer snapshot；r0s1=Ready-only＋retain；r1s0=Fullcall＋snapshot；r1s1=Fullcall＋retain。第五臂conservative_s1是同runtime零投机资源锚点。

- `PILOT20_V1`已经20/20完成，资源闭合PASS；Gate与完整campaign SUMMARY已镜像`gpu_results/PILOT20_V1`，但per-cell有界镜像尚未做。原PID109431/start1792506已退出，CUDA为空。
- Pilot：r0s0信用12.0、4avoid、gap0.157145；r0s1信用12.5、0avoid；r1s0信用32.840125、4avoid、累计removed2audio-s、gap0.147403；r1s1同信用32.840125、0avoid；Conservative同runtime信用12.5。每臂offered33.11625。以上仅n2pilot，不能当n8最终结果。S0 gap短，Owner会紧接合法重发Private snapshot，不可人为延迟。
- `CONFIRM60_V1`已启动：PID **162667**，start_ticks **1955549**，启动UTC **2026-11-18T15:22:09.383916+00:00**。本地`launch_ops/CONFIRM60_V1/HANDLE.json`为权威。下一步持续轮询这一PID，不新起重复进程。

轮询命令：

```text
python -B experiments/dsn_native_joint_retention_20261118/ops/poll.py CONFIRM60_V1
```

SSH超时不等于进程死亡；同PID/starttick重新确认。不要杀foreign进程。全体SLO失败、零op、负效应继续；只有身份/实际原任务/独立audit/物理释放技术失败停止并保留。

## 剩余完整任务

1. 等待60格确认完成，检查同PID退出与CUDA无owner，保存Root closure。
2. GPU释放后批量收集两个campaign完整有界文件及raw文件SHA索引。`COLLECTION_REQUESTS.json`已有1626个显式路径、每文件8MB限额；`ops/prepare_collection_requests.py`与`ops/build_publication_candidate.py`由agent准备。Bulk原power/WAL/events/log、模型WAV留8TB，仅hashindex入Git。注意原source config与child rawCONFIG序列化不同，只能语义比较并分别保留byteSHA。
3. 运行已冻结`analysis_source/final_recount.py --out ABS_E/review/FINAL_RECOUNT_V1`。硬要求80=8×5×2、每cond16、offered137.864125、frontiers282，各technical/task/audit门PASS；独立重算逐frontiercredit/P99、worker/能量、S/R与交互。若recount脚本自身bug，保留失败后冻结新analysis修复，不重跑或筛选GPU结果。
4. 缺失job infer timer保留NA，不称GPU-active；worker是elapsed occupied-worker。
5. 两类gap分开：全部高水位deficit面积（含必要/未知）和同root、支持分类、可能被canonical/epoch截断的窗口面积。Driver aggregate的censor alias少两字段，最终从per-cell rawkeys`gap_right_censored_windows/gap_boundary_truncated_windows`独立恢复；不用改冻结driver。
6. 根据完整数据写结果报告，明确pilot/confirmation、同runtimeConservative、实际S能力和原任务一致性。不要给录用概率或把计数当发生率；230份论文SHA应保持不变。
7. bounded审计源码/计划/结果/失败/全过程同步publicGitHub。新论文/现有private稿件不动。公开checkout`C:/Users/LENOVO/.codex/worktrees/revtrace-dsn-evidence/RevTrace`，HEAD需先查远端新进展再普通ff推送，不能改dirtyRoot。source/pack complete，无nested.git、模型大数据。

## 已发现的v22解释问题（只记录，未改论文）

见`review/REVIEW_EVIDENCE_AUDIT.zh.md`：旧Conservative56.0与新Ready58.5跨runtime不能证明缓存净增2.5s；H3Gap是全部高水位面积非全avoidable；12/368是total事件比，avoidable6/368，非自然流量发生率；Fig1来自另一开发银行。新同期五条件实验直接解决首项归因，其他留给用户后续文字修订。


## 最终闭合（取代上文执行中状态）

20＋60格全部完成、完整有界结果和raw SHA索引收齐；315/72/53 CPU套件通过。原f29分析V1时间窗断言错误已保留，720c6e2分析V2正式完整重算PASS；全部1,410原选定边一致。分析V2、readiness和production support完整源码、manifest与bundle均已补齐。论文230文件全部不变。最终科学结论以FINAL_REPORT.zh.md、SCIENTIFIC_DECISION.json与review/FINAL_RECOUNT_V2为准。
