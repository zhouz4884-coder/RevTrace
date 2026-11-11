# 原加载构造路径的最小诊断与控制计划

状态：**仅计划，未启动 GPU、未改运行时。** 共同路径修改必须由 root 与 baseline runtime owner 统一加入另一个新冻结源，不能修改旧 NN4f 或并发开发副本。

## 已从真实源码核实

* `stage_worker.py:16` 原 `model_load_seconds` 围住整个 `CandidateBridge` 构造；`:19–25` 的固定原 C/U warmup另有耗时。当前 after-durable 约70–88秒主要在该 constructor，现有日志不能拆分内部原因。
* `NativeBridge.__init__:118–131` 调用原 `PaddedAlignAttWhisper`；原 `simul_whisper.py:60` 调用其 `load_model`。bridge已将 `_download` 仅路由到原 Chinese checkpoint，**不再发生原通用模型重复下载**，不应以此作为新修复点。
* 原 `simul_whisper/whisper/__init__.py:287–288,318` 默认 device为cuda并 `torch.load(fp,map_location=device)`；`:330–331` 创建 `Whisper(dims)` 后 `load_state_dict`；`:336` 再 `model.to(device)`。当前 worker没有设置默认 torch device，因此源级候选是：checkpoint tensors先进入CUDA、CPU模型装参再读回、最后整模型搬到CUDA。需要测量当时真实 tensor/parameter device与copy字节，不能仅由源码估算秒数。
* 原 key转换 `convert_finetuned_to_whisper_state_dict` 主要重新命名并引用原 tensor；不能未经计数就称它复制了全部权重。
* `NativeBridge:138–143` 还包括corrector配置/processor、Ultravox `AutoModel.from_pretrained`、Peft adapter；Ultravox `ultravox_model.py:430–521` 按 `_init_weights` / meta相位选择 nested audio/text `from_pretrained` 或 `from_config`。嵌套Llama backbone是该checkpoint结构需要的；出现第二个from_pretrained本身不证明重复。
* 源快照及SHA：`FORMAL_RECOVERY_WHISPER_LOADER_v1.json`（author loader SHA `f9ab895c30bb36218adaace260ec2519d1a5fc98c3fd3e2caa02a75d36003b4d`）；`FORMAL_RECOVERY_LOADER_SOURCE_v1.json`（Ultravox SHA `df618218561375da01bb53bd2764ea123e0cbf782f3326753f669f63ff6c6d3f`）。这些是只读源码证据，尚无新加载性能测量。

## 第一阶段：给两臂同样的观测，不改计算语义

优先将以下相同轻量标记放入 root 已计划的正常/故障执行器；避免为收集同类信息额外创建大量只load不服务的进程。每个标记带cell、Owner epoch、worker slot/PID/incarnation、original perf clock与完整源/资产hash。

| 边界 | 需要测量 |
|---|---|
| worker入口→torch/author import→constructor入口 | perf、process_time、`/proc/self/io` read_bytes/rchar、RSS、默认torchdevice；把import时间与constructor分开 |
| 原ASR loader：torch.load / key转换 / Whisper构造 / load_state_dict / model.to | 每段墙钟与CPU；checkpoint tensor devices/总bytes、model parameters devices/bytes；CUDA allocated/reserved前后；计数真正发生的GPU↔CPU copy，分别记录observed标记及有同步计时的诊断模式 |
| corrector interface / AutoModel / nested audio/text / Peft adapter | 同样phase时钟、weight-file读取次数/bytes、实际branch（meta/from_config/from_pretrained）、最终参数dtype/device；不打印权重或token |
| audio验证/读取→固定warmup→ready发送/接收→首次dispatch | 补ready接收时间；原warmup完整C/U、genesis/replica合同校验均保留 |
| fault→exit/CUDA释放→WAL scan/replay→e1阶段→首新模型/commit/Consumer | 每段同输入、同故障点RTO，原origin、accepted债务、old-fact与new-fact分开；两GPU board全服务能耗 |

常规服务只加宏观host时间，不在每个标记插入GPU同步。若诊断GPU copy异步时间，则单列启用显式同步的diagnostic arms；它们不与未同步服务数字混用。最终比较必须两臂使用同一测量模式。

## 第二阶段：只在诊断证实后做窄共享修复

首个候选是 **原ASR loader只将checkpoint映射到CPU，再按原代码load进CPU模块并一次迁移到原GPU**。它保留同一Chinese checkpoint、key转换、alignment heads、参数dtype、原C/U和固定warmup。不得同时改precision、attention backend、warmup或故障域。可以在独立审计adapter中狭窄包住原loader的checkpoint读取；不编辑author source，也不能影响后续服务中的torch.load。

先测原路径的copy与phase成本。若checkpoint实际已在CPU、或GPU→CPU搬运并非显著成本，则不实施这个候选。Ultravox/adapter的潜在重复materialization也必须先计数并证明，不先做合并权重/预转换资产。

## 同输入、重复和合法oracle的最小控制

1. **Same-input**：原loader与候选loader使用完全相同source/model资产、FP32、TF32设置、GPU映射、cache目录、warmup原state/audio。比较所有最终参数tensor（dtype/shape/bytes hash）、buffers、alignment heads、runtime contract/genesis；完整source manifest单独冻结。
2. **Repeated-run**：原/原重复与候选/候选重复都保留；按ABBA/BAAB顺序交叉，交换两卡，至少每个顺序2次。记录初始/恢复load、温度/功率/IO/cache状态；不执行系统drop_caches，不把先后缓存差归因为策略。
3. **Legal oracle**：原未改author loader+原完整C/U执行是合法实现对照；同一冻结输入分别记录完整state、原C/IDs和结果。不以独立GPU重跑逐位相等冒充唯一数学真值；若有输出差先看原/原重复，再区分参数差、数值执行或原程序非确定性。
4. **真实成效**：在相同owner-after-durable点对Conservative/RevTrace各自重跑原与候选，至少2个独立repeat；依旧杀原Owner整个故障域并确认exit/CUDA释放，不能用预热幸存worker缩小故障域。保留D2/C8全部offered义务、实际Consumer、完整原fact trace checker、全服务能耗。

保留修复的门：参数/合同与原程序合法性检查通过；复制/加载阶段真实下降；**故障后首新认证、原债务清除和全服务GPU能耗有净改善**；Conservative获得相同优化。若只改善加载微基准却无E2E净机会，冻结该候选负结果；这不预先终止其它共同恢复机会，也不称RevTrace独占算法收益。
