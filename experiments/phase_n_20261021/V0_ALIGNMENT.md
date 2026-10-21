# V0：实际输入、覆盖与及时就绪

## 协议与分母

全部 12 个正式 T1 单元用于 live 审计；c16 是 16 个负载槽，源音频为 12 个。Fine 每 run 279 个 authority 机会，Coarse 每 run 98 个。三次运行、不同 policy 与复用音频不被当作独立声学来源。

正式固定态 V1 的抽取规则在结果前固定：每个唯一源的前两个 native authority target，C1 为 2/4s，C2/C3 为 6/12s，各 24 个上下文。C3 新 Root Draft 要单独付费；初始 parent 是 trusted fixture，不宣称生产服务动态迁移契约。

## 记录实际条件，不只比较 prompt 字段

记录 source/end、真实 waveform digest、prompt tokens、chunk_id、最终 rollback prefix、processor IDs/mask、CPU processor features digest、dtype/batch/pad、生成预算、EOS 与时间。特征摘要是 dtype cast 前的 processor 输出；GPU 算术不由观察哈希证明。

`chunk_id>=2` 才启用 rollback-prefix 转换。因此 C2/C3 同时涉及父、private chain、chunk/rollback 和输出单位，不能写成“100% ancestry effect”。`verification_tokens=64` 是向上补齐候选宽度，不是截断至 64。

r0 的实际观察如下，完整重复见 CSV：

| 组/调度 | 机会 | 同 parent | 处理后 context 相同 | target waveform 相同 | enqueue 前有候选 |
|---|---:|---:|---:|---:|---:|
| C1 Fine-B | 279 | 279 | 279 | 279 | 0 |
| C1 Fine-D | 279 | 112 | 148 | 279 | 87 |
| C2 Coarse-B | 98 | 98 | 5 | 98 | 0 |
| C2 Coarse-D | 98 | 93 | 12 | 98 | 0 |

同 parent/处理后输入相同/及时三个条件的合取，在所测各单元都是零。**这不是说来自不同条件的字符串不能被重新验证**：可信 checker 可以在目标 context 下作新选择。另给出更宽松、事后使用已记录 FP32 Oracle 的“原生完整 Z 正确且及时”上界：Fine-D 为 20/279、20/279、22/279，其余所测接口为零。该上界不是实测在线验证器，也不覆盖尚未实现的新候选编码。

## C3 的实际准备检查

为避免把固定态 Draft 成本误当实时就绪，增加三个付费 C3 preparation-only runs：同一 proposer 进程/模型，FIFO 排队额外 root-aligned calls，每会话至多一个额外 Root outstanding；authority 始终独立执行，不等、不消费、不验证这些候选。没有新增 GPU worker、online selector 或 KV reuse。

| repeat | authority 机会 | 准备完成 | 原始输入严格相同 | enqueue 前且与目标 Z/P 一致 |
|---|---:|---:|---:|---:|
| 0 | 98 | 84 | 83 | 1 |
| 1 | 98 | 69 | 68 | 0 |
| 2 | 98 | 69 | 68 | 1 |

未准备到的机会仍保留在 98 的分母里。输入与输出分开统计：不把不相同的原始输入自动说成错误输出；也不把模型开始后才到的候选追认为 enqueue 前 ready。

准备本身使 xRT 分别为 baseline 的 0.9762/0.9785/0.9702，GPU energy 为 1.0212/1.0093/1.0352。它未安装任何候选，不能据此称为 V2 性能。三个重复的全部 canonical Z/P/音频/身份历史仍与 matched baseline 相同。

## 一个真实的处理链等价性边界

同一个 `chinese-05` 末端在三个 Root runs 中出现：parent、prompt、chunk、waveform、rollback prefix 都相同，但 singleton Root 的 processor 输入长 523，三行 authority batch 为 524；差的是一个 `<|audio_pad|>`。features 为 3464 对 3600 frames，valid feature mask sum 为 3464 对 3465。

不是直接猜因：两个实际 batch 布局各做两次 CPU 重放，三个 GPU runs 的原 IDs/features 全部精确复现。分类为**可复现的 batch-dependent preprocessing realization**，不是本次 coordinator 祖先链污染证据，也不是已证明的 GPU 算术故障。protected canonical 历史未变；不从这一个输入差异推断文本损害或自然发生率。

该负结果保留，未修改 padding/模型/历史以制造 alignment。C3 preparation gate 为 NO-GO；独立 authority 的 T3 不消费候选，故在 triage 解释后继续。技术队列 hold 只停止 T3 driver 的后续发行，当前 scout 子进程未被暂停，测量未被改写。

## 必须保留的替代解释

原生最后一步的增量 Z 不一定是目标 authority 调用的完整 continuation；P 相同也不表示原生 Z 相同。比如 r0 Coarse-D 有 90/98 的 P 相同，却只有 12/98 的 Z 相同。本文数据**不否定**先将 P/完整 tentative transcript 重新编码成目标 continuation、再可信验证的新适配器；它没有在本协议实现。

Fine-D 中事后 P 相同且及时的机会为 82/279、66/279、82/279，高于原生 Z 上界。这只是使用 Oracle 的线索，不能直接在线判断、更不能无认证写入。无损 P→目标 Z 的逆转换、token/stop 等价及完整成本均未证明。Coarse 当前完整末端候选 enqueue 前为零，任何依赖该已完成结果的转换不能追溯提前其可用时间。

结论：对**所测原生 token 接口与付费 Root 准备政策**，及时完整候选不足；不是所有未来验证方法不可能。实际数据、CPU 控制和未验证项见 `V0_LIVE_ALIGNMENT.json`、`C3_ROOT_READINESS_AUDIT.json`、`PROCESSOR_CPU_CONTROLS.json`、`tables/V0_*`。
