# 同任务强基线设计与实现

本目录是隔离开发材料，不是已冻结执行源码，不是 GPU 结果。所有新臂必须由同一份重新提交、冻结并通过完整 manifest 核验的源码执行。父源码为 NN4f `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，59 个文件逐字节与 `SOURCE_v2.json` 核对后复制；修改后的实际执行提交不得再写成父提交。

## 主要判断

原对话指定的“出生版本一变便取消”可以执行，但不是最强的版本策略。每次真实父状态前进都会改变 birth root，因此这种规则会系统性拒绝所有跨 birth root 的条件调用。它适合称作 **strict birth-root control**；即便明显落败，也不能推出 Retire、所有版本化调度或所有简单工程方法不够。

最有信息量的同任务版本控制是 **dependency_versioned**：允许预计的直接父节点正常转正；一旦任一冻结祖先实际失配，则永久撤销其后代版本。它在单次兼容交接上与完整输入确认一致，只有“祖先失配后，未来完整输入重新汇合”时才与 RevTrace 分歧。因此，可能出现同效结果，应如实保留；92 次跨 birth 有效工作本身不能证明这个更强基线会错误拒绝它们。

额外实现 **ready_only**，用于区分在途保留与普通完整结果 memoization。它保留安装前已被 Owner 完整接收、验证并进入 ready bank 的原始调用结果；安装时仍缺少完整接收的调用被 fence。此处 ready 是控制器可用的完整接收边界，不是模型物理结束时间：即便 worker 已完成、完整终结 frame 排在队列中尚未接收，也不是当前可用的 memoized result，不能称它仍在计算。旧四来源汇总的 completed_full_buffer_reuse=0，提示此臂在该银行可能与 strict birth-root 很接近，不能预设它是最强主要对手。

## 可执行策略表

| config arm | 派发 | 真实父状态安装后的完整调用处置 | SUP/Consumer |
|---|---|---|---|
| conservative | 只派发实际 canonical 输入 | 原始完整结果正常 AU 选择 | 共享合法整视图保留 |
| fullcall | canonical 优先，否则合法 conditional tail | 完整输入确认；未知继续；同 frontier 真失配或已覆盖可停止 | 共享 |
| safe_versioned | 与 fullcall 相同 | 旧 birth-install-generation 一律拒绝，包括已经完成结果 | 共享，拒绝计算不能删除仍支持的视图 |
| ready_only | 与 fullcall 相同 | 安装时没有 Owner 完整接收的调用永久拒绝；已在 ready bank 的结果继续等待实际父状态 | 共享 |
| dependency_versioned | 与 fullcall 相同 | 兼容的预期父交接继续；任一冻结祖先真失配永久撤销后代版本 | 共享 |

三个额外基线均为作者构建的同任务控制，不能标为 Retire/SSBD/PredGen 官方复现。

## 共同合同与日志

所有臂保留两张 3090 上的两个完整 FP32 ASR/Correct/Update worker、500 ms 原始输入、同一 actual all-worker READY 后 origin、原 D2/C8、同步 durable-before-install、真实 Consumer、同一物理退出与 terminal 绑定、两 GPU 实际功耗采样。不新增精度、批处理、网络、更改模型或重算机会。

策略 fence 使用新字段与新 reason：`birth_root_policy_fence`、`inflight_at_install_policy_fence`、`dependency_version_policy_fence`。它们与 `actual_canonical_disagrees_with_complete_start` 严格分开。发给 worker 的停止提示日志为 `policy_C_entry_skip_hint`；提示仍只在原安全 before-C 检查点生效，没有中途抢占 CUDA kernel 的能力。提示太晚则实际完成后拒绝完整结果，实际物理占用全部计入。

策略 version 不能修改 owner epoch、session epoch、worker incarnation、job id、frozen start、dispatch epoch。过时的终结结果只能释放其真实自有 worker lease；不能释放新的 job。已经被 SUP 接受的视图在调用停止或结果丢弃后仍独立存在。当前父输入的原始完整调用必须先按同步 durability 合同正常选择，随后才能推进策略 token，防止把该次选择本身错误取消而造成停滞。

## 已落实文件

- `baseline_source_dev/versioned_policy.py`：上述三种额外控制。
- `baseline_source_dev/resilience_owner.py`：原实际 Owner 的五臂选择、相同派发器、理由分类日志。
- `baseline_source_dev/test_versioned_policy.py`：当前父选择、在途与已完成的分界、身份保持、重复终结、伪造提示、durability 失败、SUP 独立、强依赖版本的兼容交接与失配后汇合控制。
- `baseline_source_dev/test_resilience_owner_integration.py`：实际 Owner→FactStore→SurvivorConsumer 的新臂完整任务 CPU fixture，分别覆盖 ready-before-parent 与 parent-before-live-result。
- `baseline_source_dev/RUNTIME_POLICY_CONTRACT.json`：父源码身份、共同合同与 arm 映射。

开发过程中曾在用户“先报告既有证据”追加要求到达前运行 61 项 CPU 单测，全部通过；其中 15 项是新增 strict/ready-only 策略控制。随后新增的强依赖策略及 Owner 集成控制尚未执行，暂停等根代理先展示既有证据报告。该开发检查不具有新实验 ID/冻结源码身份，不能当作正式实验或 GPU 证据。

**后续正式 CPU 验收已完成。** 既有证据专报展示后，冻结完整 62 文件源码为实际提交 `23538150798378c6629c8f75ec87426bb05574b4`；完整 manifest hash 为 `525db820cbe5ea8b74e7315b3dd3cc527df452c6e21c838b9229049b6131c095`。正式实验 `DSN_V16_BASELINE_NATIVE_PROTOCOL_CPU_V1` 在指定 8TB 盘的原 Python 3.12.13 环境执行203项协议/真实CPU IPC/Owner–FactStore–Consumer控制，203通过，0错误、失败、跳过，耗时9.007秒。`CUDA_VISIBLE_DEVICES=''`，`PYTHONPATH` 为冻结源码目录，导入守卫禁止 torch/transformers/peft 等神经框架，实际无此类导入，0模型调用、0 GPU执行。此结果只验收这些 CPU 协议接口，不是神经等价或服务性能结果；依赖 Torch 的原CPU张量测试不在本次无Torch导入合同内。原59文件默认源码的无参数 preflight 在验收前后均通过，CURRENT及脏根HEAD未改。正式记录、原始日志、摘要、gate与身份核验见 `baseline_ops/CPU_BASELINE_V1/`，远程原始结果位于8TB `results/revtrace/dsn_strengthening_v16_20261111/CPU_BASELINE_V1`。

## 最小高信息启动与后续

先完成已承诺的既有证据专报，再启动新实验。正式 source freeze 后，先以实际冻结 source/manifest 运行完整 CPU 守卫、同任务历史比较与负控。最低 GPU 调试块应由两位元数据预选、不同长度层说话人组成，五臂、两次 balanced fresh-process，共 20 个 cell；它用于验证完整执行、实际版本分歧与 ready-only 机会，不用于按结果挑选说话人或仅保留胜出的臂。

如果不希望给 strict birth 单独增加 GPU，最低四臂采用 conservative、dependency_versioned、ready_only、fullcall（两说话人×四臂×两重复=16）；strict birth 保留为 CPU/历史控制。若 ready-only 的实际完成前置机会仍为零，报告其与在途失效臂的同效事实，而不是重新解释成 EL 的普遍必要性。

正式确认最低保留原八来源的同期三臂 conservative/dependency_versioned/fullcall（8×3×2=48），再加16位真正未使用来源（16×3×2=96），总144。若要同时独立估计在途保留与 ready memoization，正式应预先固定四臂并相应增至192，而不是把开发选择伪称原144方案。GPU角色、策略执行顺序应平衡；不能把144/192个 cell 当作独立声学样本，speaker 是主要配对统计单位。

不采用离线 <=5pp/8pp 信用扣除作为停止门槛。预注册全部效果方向，保留失败、EOS、期限未达标、能耗与推迟完成。运行时应记录每次策略 fence 对应输入是否后来确认、所在完整调用时间及实际 Consumer credit；这些是解释数据，不能把冻结轨迹删除信用解释成重新调度后的因果收益。

## 资源归一化与外部方法边界

旧 `stage_service.py` 的 ready_handoff 是一个完整 Authority 加一个 protected-ASR-only producer；two_full_* 是两个完整 Authority。它改变了模型常驻与能力分工，不可代替相同两完整 worker 的主基线。可以在单独准备阶段消融中运行，并明确资源和合同差异。

增加同一条串行依赖链的完整副本，仍需要确定下一调用的真实父输入；但多会话可填补空闲卡，因此资源成本不能由单链机制论证自动关闭。无需第三物理卡即可首先做共同两卡资源预算下的两会话并发 Conservative/RevTrace 对照，完整计入单卡功率、内存、队列等待、总 makespan、每会话期限与任务结果。若改变逻辑 worker 数量或将多个模型放在同一 GPU，需独立精度/内存/公平分配门槛，不能把虚拟 worker 当额外 GPU。

经只读核对原论文与作者项目，外部边界如下；这是合同分析，不是移植实测：

- **Retire** 明确将执行版本的发布权限与资源所有权分开，并按执行合同认证可继承的已完成前缀；因此，把它概括成“版本一变丢弃一切”是不准确的。它在 vLLM 上处理版本替代、KV handoff、异步回收，原文实验对象为 Qwen3-32B/GPT-OSS-20B 等，不是本项目的原始递归 ASR/Correct/Update。推论：strict birth-root 不构成 Retire 复现；完整 Retire 适配需要另设合同与任务保持门槛。[Retire 原文](https://arxiv.org/html/2610.01160v1)
- **SSBD** 的更新输入是逐渐增长的翻译源文本，验证上一版翻译 draft；其 biased verification 显式修改 token 分布，并有 display-only mask-k。推论：直接把其输出当本项目原始 Correct/Update 结果会改变选择任务；可借鉴显示层消融，但不能冒称原任务原样保持。[SSBD v2 原文](https://arxiv.org/html/2509.21740v2)
- **PredGen** 作者仓库提供预测响应与多种 verification/generation 模式；其 README 的模拟输入是带时间戳的 TTS 转写或从最终文本逐词释放，输出关注 LLM 响应与首句/TTS。推论：官方代码确实可取得，但直接运行得到的是另一个任务，不能拿其延迟当相同 ASR 服务的强基线。[PredGen 原文](https://arxiv.org/html/2506.15556v2)，[作者 README](https://github.com/jacklishufan/PredGen/blob/main/readme.MD)，[作者执行代码](https://github.com/jacklishufan/PredGen/blob/main/prompt_speculation_v2.py)

文献核验使用 nature-academic-search 的 citation-verification 流程；专用 academic-search MCP 未挂载，采用官方 arXiv 与作者 GitHub 源。GitHub 首次不支持的 /readme endpoint 及大小写错误 README.md 均未作为“代码不可取得”证据，正确的 readme.MD 与执行文件随后已成功读取。没有声称外部实现不可能移植、已经充分排除，或已经实测。
