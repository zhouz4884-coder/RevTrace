# 原生阶段实验结果与决策

后续精读公开推理加载器后，已[更正关于作者推荐 dtype 的推断](../dsn_streamcorrect_stage_handoff_20261029/PRECISION_SOURCE_CORRECTION.zh.md)：作者的公开 Ultravox 推理路径明确使用 FP32，因此不把补 dtype 网格视为继续交接研究的强制门。旧冻结 plan 和实际结果保持原样。

既定四个完整来源和六个短控制全部完成。执行源为 `41dea9bb6666e2c7397b394fb1c7a4a58b27888f`，独立 CPU 汇总源为 `f6612d34183fdeff23fa677494f9a4b8279bd24c`。四条完整流的全部 69 个输出 token/完整反馈 cut 都等于原 v8 真实 Canonical 历史；固定同输入、fresh process、跨卡、full/deferred capture 控制的完整候选签名相同。没有改原 C 的候选、选择、对象传递或反馈更新。

主 gate 为 `PASS_BOUNDED_ORIGINAL_STAGE_PROFILE_AND_PACKET_CONTROLS`，SHA256 `c6e3a55fda5edcc6f138922d6e78e1f6f80f3794f0ea2a405ef7ae0d28556090`；离线 gate 为 `PASS_BOUNDED_STAGE_COMPONENT_EVIDENCE`，SHA256 `ef04f56a9bdfbea07f8e76d8df4dc028e6d6edbc470a1437efdb222ba53f3a46`。两者位于指定 B 盘 `results/revtrace/dsn_streamcorrect_stage_profile_20261029/` 的 `campaign_v1/` 与 `analysis_v1/`。本地 `RESULTS_v1/COLLECTION_MANIFEST.json` 核对了 80 个文件、2,367,252 字节；音频、全部 tensor blobs 和原始大日志只留 B 盘。

69 个完整流调用中保留了 65 个原 C 入口完整有序 beam packet，其中 64 个 C 返回非 None；另外四个是原生前端尚不执行模型的步骤。下面只列 64 个非 None C 步骤的实际分阶段值，单位毫秒。

| 项目 | 均值 | 中位数 | 范围 |
|---|---:|---:|---:|
| A：到原 C 入口 | 434.70 | 443.99 | 268.72–783.54 |
| C：原方法 | 268.72 | 229.60 | 158.40–761.19 |
| H：tail/同步/未分类残差 | 1.31 | 1.31 | 1.09–1.61 |
| full snapshot 捕获 | 9.22 | 9.03 | 4.64–12.61 |
| instrumented 原 model 总时长 | 713.95 | 686.78 | 436.55–1276.20 |

H 不是 IPC、匹配或部署 handoff 成本。完整捕获包含复制、同步和落盘。full capture 的最终物化基本已经在捕获时间内；固定 deferred 控制的单个目标步骤仍需在 model timer 后物化 183.13ms，不能把这部分删掉后主张传输免费。短控制同时具有 fresh 首个真实 C 的差异，不能由单次 full/deferred 总时间差推断部署开销。

原 native READY 的 1 秒前端 warmup 并非各来源都使神经 C ready。A 组 warmup 的 C 返回 None；完整 source0 首个非 None C 在 1.5 秒，761.19ms，source1 首个在 1.0 秒，675.44ms。B 组的 warmup 已真实执行 C，分别 764.39、761.89ms。只为区分冷调用，去掉完整流中这两个首个非 None C 后，其余 62 步 C 均值 254.22ms、中位数 229.28ms；所有原数据仍保留。以后服务比较须统一完整模型 ready 的定义，并公平计入或单列其成本，不能由某臂跳过神经 warmup 获益。

按完整开始 cut、source、目标和 is_last 精确匹配，旧实验的 384 个同输入对全部对应本次回放，包含 73 个最终 cut 不等的对、285 个 Controller 已先收到候选的对。最终 end 不等没有用作过滤条件。这支持继续研究“预测反馈必须撤回，但同次已完成 ASR 候选仍可由原 C 使用”的对象边界；它还不是一次实际 packet 交接，不能写成部署收益。

我的决策是有界 GO，目标限定为单会话因果关键路径。A≈435ms、C≈269ms 各自可能跟上固定 500ms 输入，而原完整调用≈714ms 不能；若足够多的合法候选在请求派发时已经完成，省掉 A 才可能改变稳定性。忽略额外部署成本的必要粗略条件 `C+(1-h)A<500ms` 给出 `h>0.47`；旧 285/384 readiness 不能代替新 scheduler 的实际命中率。A 大于 C 也意味着刚到下一次调用时常常还没有候选，必须保持 ready-only、无等待、失败立即原完整调用，并测出 fallback 周期和实际排队。

两个会话每秒四次请求仍会使单个 A producer 容量不足，所以本结果不支持该负载下胜过两完整副本。后续若实现，只固定原四来源分别完整运行，并保留“两完整副本且同样可在 ASR 阶段早显”的强对照。原 D2/C8、完整 Canonical history、内容端点和能耗都应保留；processed frontier 的进展不等于这一步新增文字的价值。

实际原 native READY 和新测量的 ASR、corrector 均为 FP32，不使用 autocast/TF32。原论文讨论 FP16/BF16 模型内存和 H20 部署。当前机会不能写成优于作者优化精度部署；进入性能结论前，应由实际实现结果判断是否需同源优化精度强对照。当前没有增加精度、模型、训练、来源或负载网格。

保留候选的条件性合法性应来自受保护的生产域、完整输入合同、完整候选与原 C/原 feedback 更新；同输入不构成任意 GPU 历史普遍 bitwise 唯一的证明。本次完整 history 和跨卡/重复检查是强实测控制，与确定性保证分开陈述。未清理 KV/attention 只记录了元数据，尚未实现恢复/交接；下一实现若进入这一切面，仍须证明原 tail 和 cleanup 的等价行为。
