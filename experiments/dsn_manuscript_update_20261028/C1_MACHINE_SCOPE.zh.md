# C1 的机器检查范围与正文可用命题

结论：**可以把 C1 写成有代码见证、反例和条件性归纳的兼容充分条件；现有“1,154 状态 + 64 role 单元”不能直接称为它的完整机器证明，更不能称为最小必要条件。** 这不会削弱组合贡献：正文应把兼容关系、Consumer 保留性质和实际服务交互分别陈述，给每层放最贴近的证据。

## 可陈述的条件性命题

在单 Owner、同合同/epoch、不可变音频和声明 adapter 的调用合同下，P 必须涵盖下一次调用实际消费的全部跨调用反馈状态；完整结果及其实际输入由可信边界绑定，不能把正文文本、Caller 布尔值或不完整输出当作 P。

若在新 Canonical 前沿 F 处，存在完整 Private 节点，其反馈投影逐 token 等于所选 Canonical P；由此节点到分支末端的每条实际冻结输入边，均恰好消费真实前驱的完整输出投影且边界连续；末端确实可达；任何在途后继仍消费该末端的冻结输入并指向 F 之后，则该链可重根为新 Canonical 下的**合法临时计算**。归纳基是同边界的实际跨调用状态相同；归纳步是每条后继的真实输入不因重根改变。结论不提升 Private 写权限、不保证将来识别正确、不要求重复浮点执行逐位相同，也不迁移未声明 KV/工具状态。

另一条独立的 Consumer 性质是：当一次 Canonical 应用前的完整临时假设超前于 F 且满足实际 ancestry 检查，`two_lane` 保留该完整假设，同时推进认证 lane；不兼容则撤回。它不拼接未经证明的文本后缀，也不保证今后每次更新均单调。

## 实际实现与既有机器证据的对应

| 前提/性质 | 冻结源中的实际位置 | 已有证据能说明什么 |
|---|---|---|
| 同边界、输出 P 相等 | `continuity_proof.py:2–9` | `eligible_chain` 明确比较 SID、精确 audio_end、同代际和完整 result.state_tokens；完整性及输入真实性来自外层 row/render 合同，非该函数重新验证。 |
| 每条冻结边与可达末端 | 同文件 `12–18` | 按实际 chunk 边界和前驱 P 推进，检查末端 chunk/P；已有 CPU 测试拒绝中间输入、末端和缺节点错误。 |
| 唯一在途后继、未覆盖目标 | 同文件 `19–24` | 已有 CPU 测试覆盖错误 chunk/输入；原 1,154 状态产品没有表示这个保留谓词。 |
| Consumer 实际完整 ancestry | `certified_display.py:83–95,125–135`；`kernel_runtime.py:19–55` | 原生 Consumer 检查同边界输入/输出投影与唯一祖先，KernelView 在私有预演后先申请、再实际应用并记收据。已有 CPU 正反例和实际 GPU 受控交错证据。 |
| 合同/epoch/冻结身份、合法发布 | `certified_display.py:63–78`；`kernel_runtime.py:103–119` | 这些约束分布在外层，不能把 `eligible_chain` 的一个 True 当作独立证明全部外部前提。 |

上述行号均指实际冻结源码 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf` 的 `experiments/physical_retirement_20261028/source_v3/runtime/src/revtrace/`，不是 legacy dirty HEAD。

**1,154 状态的准确范围。** `experiments/composed_kernel_20261026/FORMAL_PRODUCT_v6_exact.json` 的 3,429 边、216 拒绝和 40 合法进展状态来自 `formal_explore.py`，源 kernel SHA256 为 `3006b628348a3bcf0979157ee3a60a89aba018ece4646a9c47e8384f2c4ecbb2`。生成器只有一个 session、一个 Authority 目标 F=1、一个 Private 目标 F=2 且 rootF=0、两个抽象投影、两 Worker、一次重启和最多两次视图修订。它检查 durable-root / 实际应用 / 物理 lease 等接口交错；没有生成 F=1 的 Private 边界节点、多个 Private 后继、`eligible_chain` 的在途重根检查，或保留超前假设的 Canonical 应用。故不能因 kernel 的 `apply-request` 含 ancestry guard，就声称这个有限产品已穷举了 C1 所有前提。BFS/DFS 同状态集是遍历交叉核对，仍共享同一转换规范。另一个 308 状态产品只有两 session 的 Authority 部分提交/恢复，不补上 Private 链。

**64 role 单元的准确范围。** `experiments/dependability_protocol_20261025/ROLE_FORMAL_REPORT.zh.md` 中的“C1”是旧贡献命名：4 段开发音频 ×4 方法 × clean/coherent Proposer ×2 fresh processes。它说明 Renderer 自洽不等于受保护 Canonical 选择，及错误状态实际进入未来反馈的损害；64 格不是跨根兼容模型检查，也不是64个独立声学来源。应把它作为可信选择边界的动机/支撑，不能充当新 C1 的主证明。

**最贴近新 C1 的旧证据。** `test_continuity_proof.py` 有 1 个完整链正例与 7 个拒绝变体；`test_certified_display.py::test_whole_provisional_compatibility_requires_exact_boundary_state` 覆盖实际 Consumer 完整保留/拒绝。`experiments/composed_kernel_20261026/test_composed_recovery_external.py:60` 另有真实 pure kernel 的显式 p1→p2 正例：Canonical F1/P1 先应用，再允许迟到 p2 成为超前临时视图，同时拒绝 p2 的 Canonical 写入；它弥补一种正向可达路径，但不是1154产品的穷举结论。CK5 的16个 late-private 正式运行给出64个源/条件/重复观察：56兼容保留、8不兼容撤回，属于受控交错；其中 coherent P6 是合成载荷，后续 P8 才是真实反馈模型调用，不能宣称64次自然交错。新的110格确认及新增服务时序矩阵回答机制出现与服务价值，不能替代充分条件证明。

## 不把充分性写成最小性或联合必要性

- “缺少见证，保守拒绝”不等于“缺少该字段，一定不合法”。例如一个完整子调用的实际冻结输入已经在同一 F 处等于新 P，可直接证明该调用的依赖合法性；某个保留实现仍可要求额外完整边界节点。这说明该实现的充分条件可以保守，未建立全局最小性。
- 若仅凭相同版本、相同可见文本或相同 P 字符串忽略 F/依赖边，确实可能把不同音频边界或不同真实输入混为一谈。反例支持“这些粗观察不足以普遍决定保留”，不能证明每个实现必须使用同一 guard。
- R 与 S 联合不是安全性的必要条件：拒绝所有旧 Private、只显示认证快照也可以安全。可主张的是**给定交错下保住某类已见合法进展的条件性非退化性质**，以及四臂测得的服务互补。若某些低机会点四臂收敛，或 R×K 收益可分离，均不推翻上述性质。

建议正文用语：*We give an executable sufficient condition for rebasing provisional computation under a declared feedback-state contract, and preserve compatible whole provisional views when applying a new certified root. Bounded kernel exploration, targeted source-level witnesses, and actual service interleavings validate distinct parts of this argument.* 不使用“minimal sufficient / universally necessary / full-stack machine proof”。

## 本轮最小 CPU 补充

本地实际运行12个针对性见证，12/12通过：同边界完整链、同P错F、错投影、断边、末端不可达、在途错输入/不唯一/已覆盖、缺边界；另比较“计算保留的保守拒绝”和 Consumer 的直接冻结输入证明，展示充分性不等于普遍必要性；同一个完整兼容假设在 two_lane 下保留64000、在 checked_snapshot 下安全退至认证32000。后者有进展损失，但不是非法。

所有例子明确是合成 CPU 条件，不当作自然调度轨迹、模型执行或新增服务收益。三个实际函数模块从 f0 冻结源逐字节复制，使用独立 import namespace；不是整套 native runtime 的集成测试。独立干净源码提交 `79f1f0997687450aca464356c59bc46d346f3be8`，完整 manifest/bundle 为 `C1_WITNESS_SOURCE_v1.json/.bundle`，配置为 `C1_WITNESS_CONFIG_v1.json`，结果 `C1_WITNESSES_v1/` 含逐例原始结果、环境、冻结配置、RUN_RECORD、SUMMARY 和 gate。无需追加 GPU 或扩展有限状态产品。
