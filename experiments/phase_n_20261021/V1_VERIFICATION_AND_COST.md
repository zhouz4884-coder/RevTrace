# V1：完整 FP32 Token/终止/Phi 认证及成本

Source commit：`6f25cf818341f6e1c27991ee4208b4d40f99a51e`。状态：有界严格参考控制通过；V2 不启动。

## 检查对象与合法 Oracle

对每个真实候选的所有 1..m token，检查目标 FP32 条件 argmax；验证 prompt 偏移、candidate mask、padding、首次 EOS/合法 stop 位置或恰好达到声明预算的 cap。缺 EOS 且短于预算的匹配前缀不通过，EOS 后仍有 token 不通过。现行 64-window 为宽度补齐，未发现所谓“只验前 64 个 token”的 bug。

新 verifier 不安装 untrusted offered P。完整 Z/终止校验后，从可信目标 parent/context 重新构建 Phi；原始 offered pair 是否一致另报。最终被选择的 Z 与重建 P 都必须精确匹配独立 FP32 greedy Oracle。不是通过候选的一致性自签发选择。

三种真实 batch 布局 16/4/1 均各有独立 Oracle 及同输入 repeat；FP32 Oracle 自身也作为候选复验两次。最后一个 16-row batch 的 dummy rows 完整计费，不计作新来源。F1/E1 历史控制与本轮操作器记录不合并成新 GPU 故障数。

## 结果

| 候选来源 | 每种 batch 的候选数 | 接受 | 与相应 FP32 Oracle 不同却被接受 |
|---|---:|---:|---:|
| C1：Fine 原生候选，固定前两个 target | 24 | 24 | 0 |
| C2：Coarse target 的最后原生 private 增量 | 24 | 0 | 0 |
| C3：另付费的 H0-root-aligned draft | 24 | 24 | 0 |
| F2：错误 prompt intervention | 24 | 12 | 0 |

F2 的 12 个初始 chunk 尚不消费该 prompt，实际 prefix 没变，合法接受不算漏检；另 12 个确实改变 conditioning 的候选被拒。不能报告“24 个有效 context faults”。

合计 288 比较记录、180 接受，全部接受记录与目标 Oracle 完整 token/Phi 相同；它们共享 12 个源、多个前沿与 batch 重复，不是 288 独立声学样本。288 条 Oracle-as-candidate positive controls 全部通过，重复预测一致。24 个 GPU 生成的真实候选被显式截去终止 token 后，构造的协议负控均拒绝；这不是自然 EOS 故障发生率。

另有四个实际 4-token-budget 控制：无 EOS、长度为 4，但完整匹配其同预算 FP32 Oracle，均合法接受且 repeat 相同。**终止按声明预算等价，不等于识别内容完整。** 本轮真实候选长度 1–34；131-token 超 64 索引控制是 CPU 测试，不冒称长序列 GPU 证据，也不声称已覆盖所有 256-token 长度的数值/性能行为。

## 实际成本，不能替换成线上加速

下表是 batch=16、各 24 固定态上下文的 warm 操作 wall 秒。完整 fallback 实际执行；拒绝批保留原布局，不能删除失败成本。C3 的额外 Draft 单独计费。native Draft 是两臂已有共同工作，只在条件增量账本中抵消，不是全系统免费。

| 组 | 独立 FP32生成 | Verify | 实际完整 Fallback | 额外 Root Draft | 付费顺序操作和 |
|---|---:|---:|---:|---:|---:|
| C1 | 3.042 | 1.273 | 0 | 0 | 1.273 |
| C2 | 5.563 | 2.338 | 5.553 | 0 | 7.891 |
| C3 | 5.544 | 2.393 | 0 | 4.852 | 7.245 |

C1 条件工作量降低 58.14%；C2 增加 41.85%，C3 增加 30.69%。这是**固定态操作/顺序依赖成本账本**，不是部署吞吐、两 GPU 墙钟下界、或 Commit P99 比例。跨设备工作可有流水重叠，准备还可能抢占原生 private 工作；只有 live 流程才能验证净收益。

实际 C3 preparation-only 对照另测过就绪、完整 wall、GPU energy、display/commit 和全提交历史（见 V0）。它不含在线验证替换，因此不把其 Commit P99 当 V2 风险保证。`use_cache=False` 的 verification 没有可直接复用的 prefix KV；未实现新 KV-reuse fallback。

## 原始字段的时钟说明

固定态 jobs 源自 T1 trusted fixtures：其中原始 enqueue 字段是来源 provenance，不可拿它减本轮 worker start 算验证排队。真实本轮成本取 phase started/completed、实际 batches 和 worker/model-call stamps。执行角色由 phase、actual worker config/dtype 和新 runtime digest 记录；来源 job 的 role 不能当新 probe 的安装权限。此流程没有 state admission/在线服务迁移。

## V2 决策

预注册门槛包括 ≥25% 合法及时覆盖、≥10% 包含所有工作后的实质优势和 ≤5% 受支持 Commit P99 风险。所测 native 原始 Z 的及时正确上界最多 7.89%，付费 Root 为 0–1.02%；全线上 selector 的尾部风险没有执行证据。故 **NO_GO_ONLINE_SELECTOR**。这不否定完整 FP32 验证可行，也不否定未实现的候选归一化/其他工作负载。

证据：`V1_INDEPENDENT_AUDIT.json`、`V2_STAGE_DECISION.json`、`tables/V1_*`，以及 8TB 实验盘上的冻结 cases、每阶段原始 job/result/power 记录。没有用旧 1.347s/7.801s 推算部署收益。
