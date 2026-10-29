# Ready-only 原生候选交接：首版合同

先完成四个原来源的实际同输入等价门，再审核和冻结小型服务实验。本 family 不改原 native14 或 profiling 结果。

Candidate producer 是与原完整 native ASR 相同信任级别的 **protected ASR stage**，使用同一发布模型、FP32 路径、原 beam decoding 和原状态输入。它可以复用 v8 identity tail 预测下一步反馈，但不是 f0 的不可信 FP16 proposer。只允许从本次拥有的受保护 worker/私有进程队列接收 packet；body 中的标签和校验和本身不是对任意不可信发送者的认证。

CandidatePacket 是明确未闭合的独立类型：完整开始反馈 cut、不可变来源、实际新增音频 bytes 的摘要、目标、is_last、原模型/配置/执行身份构成 key；已完成的有序四 beam、前缀长度、C 音频、post-ASR 持续状态和原 tail 全部七个语义局部输入形成不可变 wire snapshot。预测的最终 end 不参与 key。根没有匹配、包未完整接收、缺字段、篡改或未获得合法输入时，不等待候选，立即保留原 full ASR+C+U 路径。

Authority 只从完整已接收缓存中匹配。实际 queue.get 返回后立即以 fresh perf_counter 记录完整接收，校验完毕另记可用时间；不复用旧 loop-now。命中才恢复 open 状态并执行固定作者 blob `02a2202ae6f559c70014eca789796cbc948dd340` 的原 C+U AST 后缀；原 C 的候选选择、prompt、generate、所选追加 ID、retokenize、append 和 cleanup/reset 不改。原完整 ASR fallback 始终可用。

原源码读集合证明：C 不接收 generation；tail 对其 payload 的读取只有 `error_corrector` 所选 ID，其他 diagnostic key 原样返回或被写入。保留 generation 所有原键、starting/ordered beam、Tokens、primitive 进度；只把不被 C/U 读取的 Logits 数值显式标为 type/shape/dtype elision。不能用 marker 冒充 beam、音频、flags 等真正依赖字段；CPU fault controls 会拒绝。未清 KV/attention 数值也不被 C/U 消费，原 cleanup 仍执行；不把 open packet 称为闭合反馈 cut。

两臂都可在相同 ASR 阶段早显。早显使用隔离副本上的同一原 identity AST tail 得到 whole-text/反馈投影，并明确是 typed ASR projection，没有执行 learned C，也不是原完整 C 调用已结束。四来源既定神经门同时核对：从实际 open state 和从 packet 得到的投影，均等于相同完整输入下原 private identity full-infer 的返回 ID/全文/闭合反馈结果。受保护 producer 随后仍完成自己的实际 identity full-step；这两种节点证据分开记录。

真正的 neural-ready 统一用固定旧开发 case：source0 的 1.5 秒 Canonical 输入推进至 2.0 秒。每个实际 C 模型（包括两 full 副本的两个 C）都必须由原 C 返回非 None，否则保留失败，不换 warmup case。输出丢弃、warmup packet 不进缓存，清 cache 并将所有服务反馈和 telemetry 重置 genesis。载入/预热成本单列。ASR-only producer 明确没有 C 模型，不伪称 C 已预热。

默认精度与公开 VAC 推理代码一致，为 FP32；不因为论文条件性 FP16/BF16 内存段而开无意义精度网格。可配置 C dtype 属于新的完整执行合同能力，本轮不启用其他值。详见 PRECISION_SOURCE_CORRECTION.zh.md。

第一项实际 GPU 门固定原四来源、全部 69 个完整输入步骤。每步比较保护域 ASR packet 与原完整调用的语义输入，再比较原 C 完整选择、返回 ID 和闭合反馈 cut/全文；保留 None、空输出、early/fallback 与预测 end 不同的全部案例。固定 source0 的 2 秒输入再做一次同输入 tail 重复。这个门不是服务结果，也不证明任意 GPU 历史普遍 bitwise 唯一。

后续服务首版只做 ready-only、无等待。强基线必须是两完整副本、同样 ASR 早显、同样真正 neural-ready；四个原来源分别完整纳入单会话，并保留原双会话容量边界。原 D2/C8 的 all-offered 分母、实际 Consumer 端点、内容进度/版本 churn、质量与两卡能耗都保留。旧 readiness 不充当新命中率；处理的音频 frontier 不等于新增文字。服务配置待上述实际门后另审、另冻结，不因实现完成就直接启动服务网格。
