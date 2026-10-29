# 有界原生阶段测量

这项实验只决定：原生 ASR 的完整候选能否成为值得继续研究的保留对象，以及其成本是否留下实际服务空间。它不实现交接，不将离线阶段时间当成服务收益。

固定原有四个来源，每个完整回放一次；另用原先已冻结 Canonical 的 1.5 秒输入状态推进至 2 秒，做六个预先指定短控制。全来源、空输出、所选反馈改变及未改变都保留。原 v8 全部所选 token 和完整闭合状态是合法 oracle；完整候选须在重复、跨卡及 capture 方式控制中比较，不能靠只看最终文本。

Wrapper 只在原 `_run_SpeechLM_error_corrector` 入口与原清理入口读状态。原有完整有序 beam、前缀长度、音频、配置、context token IDs、分支局部变量、可持续 feedback 状态及原 C 返回值保留；传给原方法的对象、方法的返回对象、原选择和原 cleanup 都不改。KV/attention 只保留形状元数据，并明确标记为尚未闭合的中间状态；它不是 v8 的 closed cut。原 tail 不消费这些缓存的数值，随后仍执行原 reset，未来 resume 实现必须另证等价。仅两个 encoder 前提前 return 视作 early/no-model；no-speech 的 decoder break 不预先视作没有 C。

候选的未来合法性依据完整开始 cut、音频、目标和原 ASR 合同相等。identity 预测的最终 cut 与原 C 选择后的 cut 不等，不自动使同次 ASR 候选无用；旧 384 个实际同输入对中的 73 个 end 不等须保留讨论。后续猜测链仍须与真实所选反馈相容。这里只由受保护的原 Authority 产生 packet，不给旧 Private 授予 Canonical 权限。

CUDA 同步分开计 A（原 C 前）、C（原方法）与 H（tail、同步和未分类残差）。捕获 tensor 的复制、同步和序列化成本单列，deferred 的最终物化在 model timer 后另列。H 不是 IPC/匹配/handoff 成本，任何列都不代表部署 transport 免费。每个新进程首个真实 C 在既定前端 warmup 中保留并单列，不据冷调用总均值直接推断容量。

GO 需要完整原始候选、原 selector、重复和合法 oracle 通过，以及实际 A/C/packet 成本留下强端到端机会。两完整副本的并行容量可能优于固定 A/C pipeline；单会话反馈因果关键路径才可能提供不同的重叠空间。若后续做服务比较，必须包括“两完整副本且同样可在 ASR 阶段早显”的强对照，固定原四来源分别全纳入。当前 FP32 合同不等于作者 FP16/BF16 优化部署；未来实现若只靠慢精度才有空间，先补同源优化精度强对照，而非主张部署优势。

冻结源码、实际环境、完整四来源 history oracle 和有界控制任一失败均留存原记录，分同输入/重复/合法 oracle 查因；不换来源、不调输出、不增加模型训练工程。开发测试不是正式证据；正式 CPU gate 在完整 clean commit 上重跑。
