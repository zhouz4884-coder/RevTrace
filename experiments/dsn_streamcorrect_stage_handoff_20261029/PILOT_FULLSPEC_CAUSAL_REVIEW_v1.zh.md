# Full-spec pilot：实际在途保留、退出与 EOS 的只读复核

本地读取 frozen `bdfa3b1307d267a5a4caf6484e1ad465c39a592e` 的 source0 三臂实际服务证据；未修改 runtime、未 remote/GPU。补充的 8.7 KB `PILOT_FULLSPEC_CAUSAL_REVIEW_v1.json` 记录逐 job 检查与所读输入 SHA，不是新的实验或性能指标。更完整的选择建议见 `POST_PILOT_FULLCALL_DECISION_REVIEW_v1.zh.md`。

**结论：10 次 promotion 都保留了真实正在执行的原 model path；4 次退出都有实际完整 start 否定见证；EOS 失败是仍需报告的实际尾部边界。没有发现改变分母或给予 full-spec 额外显示/认证语义。支持下一轮 16 格确认；不为让 stage 追平它而立即加 join。**

## 1. 10 次保留是否只是队列或 CPU 遥测

将 ledger promotion 的 job ID 与 actual `native_jobs.jsonl`、dispatch、完整 Canon history 及父 `canonical_install` 时间交叉连接：

- 原 birth/job 保留：10/10。
- 冻结完整 start 等于后来实际 Canon 父 cut：10/10。
- `record.model_start < parent Canon install < record.model_end`：**10/10**；模型 end 在 bdfa bridge 的 GPU synchronize 后记录。不是只检查包含 restore/export 的 worker wall 区间。
- child 与 parent 两个原 model path 时间区间实际重叠：**10/10**，每次重叠 0.154–0.512 s。该计时仍包含模型路径中的 CPU/preprocessor，不声称每微秒 CUDA kernel 都同时忙。
- 更宽的 `worker_job_begin/end` 亦 10/10 跨过该安装事件；确认后剩余 model 路径为真实正值，worker 残余为 0.235–1.076 s。

三次尤其有区分力：`j000010`（72000→80000）、`j000014`（96000→104000）、`j000017`（112000→120000）均在上述 10 个实际在途保留中，且**该 job 自己的早期 identity end 不等于原 C/U 的实际 end**。输入被实际父状态确认即可继续当前计算；不需要它对未来输出的预测也正确。17 步完整 C/IDs/state fidelity 保证它们最终没有换任务。

实际 completed-full buffer reuse 为 0。已完成结果接续、future-start 收敛等机制有 CPU 控制，不把它们写成本点自然出现的服务收益。

## 2. 4 次 C-entry skip 是否强迫浪费或误取消

每次 abandoned 记录的 proof 都是 `actual_canonical_disagrees_with_complete_start`；独立验证：proof 的 expected hash 等于该 job 实际冻结 start 的 hash，actual hash 等于实际 Canon history 在其 **自身 start frontier** 的 hash，二者不等。

这不是“祖先预测失去支持，所以未来一定不可能收敛”的推断；仅祖先失配不会发此取消许可。它也不是未来 oracle、deadline 压力或任意超时取消。模型输入尚未被确认的 full job 可以继续，实际输入完全相等后会被 promote。

4 条记录均为 learned C 未执行、C/U 未完成、没有反馈 cut、没有 `end` 状态，原 cache/decoder 已清理。它们不进 Canon、不赚 certified 信用。实际 ASR prefix 和耗时仍留在服务窗口及两卡能耗里。因此这个强 full-call 控制具备合理退出机会，没有为了衬托 stage 强迫已知无用的 C 继续运行。

## 3. EOS 的实际失败链

source0 总长 129088 samples = 8.068 s。最后 offered 间隔为 1088 samples = **0.068 s**，原计划明确纳入 17 个 frontier 及 all-offered 线性 P99，未从任何臂删除。

以实际 service origin 为 0：

| 实际事件 | 时间 |
|---|---:|
| EOS offered | 8.068 s |
| EOS 原 D2 deadline | 10.068 s |
| 错预测 EOS `j000020` 开始 | 9.953 s |
| 正确 Canon 父 F=128000 安装 | 10.228 s |
| 合法 EOS `j000021` 派发 | 10.237 s |
| 合法 EOS 原 model path | 10.253–10.984 s |
| 错预测 EOS `j000020` 清理退出 | 10.463 s |
| Consumer 首见 EOS 视图 | 10.734 s |
| Consumer 首次 certified EOS | 11.019 s |

128000 父更新的真实 C 选择不同于其 identity 预测，故已有 EOS full job 的完整 start 被否定；它在 C 前退出。正确父输入直到 10.228 s 才确定，已晚于该点的 D2 deadline；随后用正确输入执行的 EOS 保留原结果，实际 D=2.666 s、C=2.951 s。

因此这是错误预测分支被隔离后需要正确尾部重算的边界，不能把两个不同 start 的 EOS 算在一起复用，也不能因其仅占 0.068 s 音频而消除失败。8.000/8.068 s dual-credit 与 D99=2.552 s 未通过并不矛盾：音频信用按间隔长度计权，all-offered quantile 按原 17 个 frontier 观察计数。全 C8 通过、全 D99 失败都应保留。

## 4. 消费语义和基线公平性

三臂有相同源输入、cadence、offered gate、D2/C8、EOS、两卡模型配置、真正 neural-ready、same `StageConsumer` 与完整反馈/显示权限。保守臂也有两份完整原模型和相同 ASR 早显；full-spec 的新增能力是允许在合法条件输入上提前算并按实际父状态保留，而不是多获一种认证/显示能力。

full-spec 的 50 条实际 Consumer 记录中有 16 条 typed ASR projection 与 34 条 Canon 视图；17 次 Canon 安装时 ahead view 留存实际为 0。因此本点支持 C1 在途计算保留在 same S 合同下的服务价值，不能单独宣称本来源又证明了消费保留发生或 R×S 必要交互。C2 必要性仍由核心实验支撑。

三个执行臂的17个完整 Canon/C/IDs均等于原任务；实际 Consumer 端点和内容记录未被成功样本分母替换。full-spec 相对保守臂有10个miss→hit、6个同hit、1个同miss，信用增加5.0 s，C50由3.192降至1.466 s，两卡能耗4802.8→4420.8 J。这是单来源单fresh的工程机会；随机配对、角色换卡和4来源×2fresh确认仍有必要。

full-spec 是本工作作者新组装的完整调用保留实现；保守臂是对原作者 ASR/C/U 的保守执行控制。不能把任一者不加说明地称为外部已部署的完整 published system，也不能因 strong control 胜过 stage 就否定我们自己的完整组合贡献。

## 5. 下一步

支持冻结16格 `{fullspec, conservative} × 4 old sources × 2 fresh repeats`，预设随机配对顺序、repeat交换primary GPU、保留所有未达标点与内容/质量/能耗。没有发现需要先修 runtime 才能做这轮确认的阻塞问题。

ready-only stage 的4次 matching-inflight fallback确实存在内部优化余量，但目前 full-call retention 已是更快、更省能且任务精确保持的我们自己的实现。先确认它，不增加 join 臂去追逐代码分支之间的排名。新增 speaker confirmation 只做本地工具准备，待这16格结果和root决策后再锁metadata清单、生成独立原始full参考、运行最终冻结方法。
