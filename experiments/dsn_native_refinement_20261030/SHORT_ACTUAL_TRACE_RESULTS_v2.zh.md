# 六个开发NN trial：实际轨迹精化硬验结果

**固定全6 trial已经实际读取并硬验PASS，不是模型理论或synthetic控制替代真实数据。** 检查器source `c4dde9ea9c7abf80fae084bc2293e193262c71e6`，6文件manifest SHA `0741878971dcdfad577624945ff3bb249860225f1281cf6d833814829f0a3948`；root切CURRENT并无参preflight后运行。实际NN source是`9492d3f9cb35e2b2849ec020817750a221248f0e`，operator是`dd4d16a51320eca0899ad6cccc1d61a0f3fbdc1a`，不是checker或GitHub归档HEAD。

原NN bank为指定8TB盘的`results/revtrace/dsn_native_resilience_20261030/short_pilot_v1`。本地输入`../dsn_native_resilience_20261030/SHORT_PILOT_RESULTS_v1`的154文件/35,494,736字节已由root逐remote SHA核验、controller退出且GPU释放；本检查又逐文件核对相同collection manifest，没有少选trial或更换输入。两种normal和四种controlled fault均是同一S0908语音上的**开发覆盖试验**，不能当正式28格或6个独立声学样本。

## 实际通过的链

* **102/102新durable Canonical转移**唯一绑定实际已登记job、原完整start/end、真实原C/U完成记录、原纠错选择及token IDs。原job/birth/Owner namespace/session epoch/worker incarnation不重签。这里检查原程序允许的真实调用来源，不依赖任意GPU重跑固定逐位相同；固定原参考一致性由独立metrics/oracle另验。
* **305条实际Consumer应用**和**107条完整Private路径链接**逐项重建，publication的原physical Owner namespace、pubID、每条完整start/end与实际ASR或full结果对应。认证仅来自durable事实，不能把ASR预测升级为认证，也不能将原事实重复算成新处理。
* 六trial的原ORIGIN、immutable音频、全部ingress和最终132145个samples（8.2590625秒）义务完整保留；全部dispatch晚于原target offer。故障恢复未重置原输入时钟。
* **2次worker-only故障**均有实际PID/start_ticks对应、退出确认、CUDA context释放后才启新incarnation，分别为ASR已实际消费后kill和partial IPC frame中kill。两个故障均完成后续原任务；没有用逻辑cancel代替物理释放。
* **Owner在durable前/后终止各1次**分别出现2个Owner attempt。post-sync/pre-install case有且仅有**1个旧durable事实首次实际消费重放**；pre-durable case为0，未把未持久化的预测或完成结果当事实恢复。重放不是新NN工作；新结果的恢复时钟仍需独立metrics区分。

| trial | 原durable转移 | 实际Consumer行 | Private链接 | worker-only重启 | 旧事实实际replay | 必要ahead撤回 |
|---|---:|---:|---:|---:|---:|---:|
| none/conservative | 17 | 50 | 16 | 0 | 0 | 0 |
| none/fullcall | 17 | 51 | 18 | 0 | 0 | 1 |
| Owner before durable/fullcall | 17 | 52 | 19 | 0 | 0 | 1 |
| worker after ASR/fullcall | 17 | 52 | 20 | 1 | 0 | 1 |
| Owner after durable/fullcall | 17 | 50 | 18 | 0 | 1 | 1 |
| worker partial frame/fullcall | 17 | 50 | 16 | 1 | 0 | 0 |

## 必须同场保留的覆盖边界

这6个trial中**policy-local rejection观测为0**。检查器所报`legal_progress_wrong_rejections=0`的分母也是0，不能据此宣布迟到/重复消息隔离已在这6个NN trial里被充分实测。真正`duplicate_late`/旧消息进入当前收件路径的正式试验仍需另列，不能用35个synthetic CPU控件填充自然事件数量。

两次Owner故障的原`consumer_rejections.jsonl`各有一条`retired_owner_namespace`旧publication拒绝，source epoch0/current epoch1，均pubID9。c4检查器尚未独立重算这两条拒绝的snapshot hash；机器facts明确把它们列为**raw观察，不属于c4已通过的拒绝快照硬验范围**，不只相信`state_unchanged=true`。后续补独立绑定时应保留这个来源区分。

**相容且ahead的Canonical应用为0**，因此不能把六个trial说成新same-source C2相容保留自然见证；实际4次ahead撤回均由完整状态不相容导出。`started_on_canonical=false && promoted_to_canonical=false`的已安装完成buffer也为0，不能据此宣称fault NN已经实测closed-buffer重启后复用；该能力目前有当前代码的独立CPU控制及规格支持。此前bdfa自然保持事件与这些开发覆盖分开。

每trial重新执行35个checker控制，均零skip；这是35个distinct synthetic控件的6次执行，不是210种真实故障。规格模型、合成反例、真实失效覆盖、自然发生率仍是不同证据层。worker-only物理释放已逐条核验，Supervisor整组终止的物理证明仍属于其独立进程收据，不能混为一类。

## 结果路径与完整哈希

* 全六batch：`SHORT_ACTUAL_TRACE_RESULTS_v2/GATE.json`，SHA `def68b6a4d5eb4fc23ba6d7c4133259af51c9d2fb244f7c993bdbcb201c0be8d`。
* 每trial完整结果在上述目录的原cell_id子目录，配置和prelaunch记录在`SHORT_ACTUAL_TRACE_CONFIGS_v2`；运行环境在`SHORT_TRACE_ENVIRONMENT_v2.json`。每条均登记原8TB raw与本地bounded copy。
* 机器表：`SHORT_ACTUAL_TRACE_FACTS_v2.json`，SHA `0c242ecbf5e68dff3c8f6592417eab792b0f637f9f6216cc3c568d167b04ca07`，含各trial gate SHA、实际计数与上述缺口。
* 原30309的六份schema失败保留在`SHORT_ACTUAL_TRACE_RESULTS_v1`；唯一窄修为真实`accepted_input/frontier`字段及原raw/副本provenance，未放宽时钟、输入、C/U、状态、fence或消费守卫，未改变神经source或任何endpoint。

可用于正文的精确英文短段：

> In six development failure-coverage trials, independent trace checks bound all 102 new durable transitions to their actual full original C/U calls, including complete frozen inputs, selected corrections and returned IDs. They reconstructed 305 Consumer applications and 107 whole-view dependency links while preserving every original input clock. Two worker failures, including a partial IPC frame, terminated their actual owners and released CUDA before replacement. After post-sync Owner termination, one pre-existing durable fact was replayed without new inference. These trials completed the remaining original task; they do not constitute the formal paired confirmation or establish duplicate-message coverage by themselves.
