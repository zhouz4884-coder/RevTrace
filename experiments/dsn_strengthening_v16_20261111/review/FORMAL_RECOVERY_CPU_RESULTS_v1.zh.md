# v16 相位正确的动作不变量检查：实际 CPU 结果

实验 ID：`REVTRACE_V16_FORMAL_PHASE_ACTION_V1_20261111`。实际运行于指定 8TB 的原 Python 3.12.13 环境，`CUDA_VISIBLE_DEVICES=''`，0 模型调用、0 GPU 调用。开始前两次检查 GPU compute process 为空。没有修改 CURRENT、旧规格、旧 NN4f、v15 或论文。

**Gate：PASS_ADDITIONAL_PHASE_CORRECT_STATE_ACTION_CHECKS_OVER_UNCHANGED_V3_SPEC。** 原 27 个 controls 加新增 8 个全部通过，35/35、0 skip。原 `model.py` 与 `test_model.py` 字节精确不变；没有更改状态机动作或扩张原探索边界。

| profile | 状态 | 启用边/新动作检查 | 深度截断状态 | terminal |
|---|---:|---:|---:|---:|
| 正常：2 frontier、至多3 issued、depth12、0 fault | 6,231 | 11,142 | 2,144 | 16 |
| 故障：1 frontier、至多2 issued、depth12、至多1 fault | 14,074 | 25,799 | 2,828 | 2,196 |

所有计数与冻结旧 v3 精确相同。新增证据是对这 36,941 条有限启用边执行动作级检查，而不是声称又发现了 20,305 个独立新状态样本。没有触及 150,000 cap，深度截断仍然存在。

新增控制验证：成功 sync 后尚未 install 是合法状态；同一 gap 可以穿过 Crash；Recover 只安装/重放原 fact，不创造神经转移；可写 idle Owner 不得遗失 pending synced fact；Receive complete 不得偷偷 append；每个 job 都必须有不可变 dispatch evidence；Recover 不得修改原结果；Sync append 与 Install stutter 的作用分开。

在探索状态中，正常有636个 synced相位，故障有1,720个 synced与123个 crashed相位；这些是有限模型状态数，不是实际故障发生率。专门控制覆盖 sync 后 crash 的合法 gap。错误的“durable tail 恒等于 Owner installed parent”在合法 sync 前进状态即被反例否定。

本次检查的关键归纳项：只有 Sync 可以把 durable prefix 扩展一条原 C/U 边；Install 精确消费已同步 pending fact；其余动作不改 durable prefix；Recovery 将 installed position 移至原 durable tail，但保留原 job/结果并不增加事实。接受输入义务及原时钟跨动作保持。

这是**手写有限规格上的设计验证**。它不是原 Python/CUDA 程序的机械抽取证明，不解除忠实原 C/U、完整状态声明、存储同步、物理消息绑定前提，也不把旧规格清 provisional steps 的恢复模式改成真实幸存 Consumer 保留视图的全路径证明。

可复查身份与位置：

* 实际新源 commit：`aa9db5c2396b76d9b50f5281fa4a68b54aca844a`；6 文件 manifest SHA256：`6d4212882ad7a276849336239c5815d3160f8c91ea6ad85313b5741732c4a15f`。
* 完整 bundle SHA256：`0f8a8218528ef342d2512bc8ee34583287111460c25b31477ea3cff459246a9e`；root 可解析 ref：`refs/research/dsn-strengthening-v16-formal-phase-action-v1`。
* 原模型/controls source：`deb3260655e2f3312499a34597cc0be6fc15484b`；复制 SHA256：model `d65176b661665713b934761a2f64e012768f1bed0a27a22986f9e9bc6e18d814`，test `b3aca890e308735b97a7d8f7b1248166d1caff78d28c36f9802d3316c359916e`。
* 远端 primary raw：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/formal_action_v1/`。
* 本地逐文件 SHA 验证取回：`FORMAL_ACTION_RESULTS_v1/`；总12个原输出文件，含 prelaunch config/environment/run record、controller identity、原 controls log、profiles、summary、gate。`COLLECTION_MANIFEST.json` 记录全部 remote path、bytes、SHA 与已退出状态；远端源仍 clean。
* Gate/SUMMARY SHA256：`c3478886f2c7921d035d8a76e93c371297d54d487660fa4beddcf6931fbdff09`。
* 新源启动前显式 source+run-record preflight PASS；root 默认无参 preflight 前后仍为 NN4f `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，CURRENT SHA均为`ea4d2ebe65bfe325a003a4ab50fe25262d6ee67fcfd20a7a460508de797fd867`。

方法脚本在 `formal_ops/freeze_formal_v1.py` 与 `formal_ops/remote_formal_v1.py`。执行源、完整冻结输入和部署记录位于 `formal_packages_v1/`。初步 `FORMAL_RECOVERY_OPPORTUNITIES.*` 保留为运行前历史审计，不回写成新运行结果。
