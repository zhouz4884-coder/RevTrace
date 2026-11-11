# v2：相同恢复输入、无故障对照与原生加载合同

日期：2026-11-11。**这是待 root 冻结实施的合同修订；未启动 GPU，未修改 baseline v1。** 对齐本次读取的 root `plans/GPU_EXPERIMENT_CONTRACT_v2.json`（SHA256 `93c7e2c96b54bbac0bf5998e12f3bb7b4a22d41ea8a397bcddd86103ea99ae98`）的五臂和至少5次配对诊断重复。本文替代 v1 计划里仅靠“自然恢复后恰好都是32k→40k”支持同输入的表述。历史原结果及 CPU 形式检查身份保持。

## 1. 三种实验对象分别冻结

| 层 | 操作与读者/时钟 | 可回答的问题 |
|---|---|---|
| 加载/原调用微诊断 | 独立 controlled fixture；两副本、相同模型/worker合同，强制同一完整start、wave切片、target与EOS；可开启逐copy同步及全tensorhash | 哪个加载/搬运阶段耗时；原/CPU-map是否保持参数和原完整调用语义。不是自然服务吞吐、UIR或D2结果 |
| 受控故障/无故障配对 | 原Supervisor、ingress、Consumer、两worker；原origin连续、原wave释放账本和power时钟；在实际factID处触发或不触发故障；首个恢复/对应后继call受同一输入门约束；记录fixture干预 | 在明确相同恢复计算负载下，故障/加载修复的真实RTO与资源成本。是受控服务试验，不冒充自然到达主结果 |
| 自然服务主矩阵 | 不插入强制恢复call/输入屏障，不改Reader、GPU数、到达时钟、accepted义务、原C/U与实际Consumer | 正常或自然策略进度的UIR、覆盖、编辑、SLO、全服务代价；故障诊断/host计数不得合并成这些收益 |

相同微诊断不能靠重置时钟、暂停Reader或预热幸存worker伪造相同负载。受控故障的整个Owner+worker组仍按原域失效，必须确认无执行成员且CUDA释放，才重启同样的两worker。

## 2. 完整相同输入的冻结字段

启动前生成 `FORCED_INPUT.json` 与完整 `START_STATE.json`，使用同一个新执行源承载 `original_loader` 和 `cpu_checkpoint_map` 分支。完整cut中包含execution source，因此**两分支若各用不同source commit，完整输入即不相同**。新源上的合法原loader bootstrap 必须先产生并冻结实际完整cut；不能把旧4f cut悄悄换source标记。

必填字段：

* 新执行 full commit、完整source manifest、环境/包/allocator变量、模型资产逐file hashes；原loader与candidate仅 `loader_mode` 工程分支不同，语义runtime contract和原程序配置相同。若loader_mode需进入语义contract，两臂须共同声明相同允许模式集合，不能每臂改start字节。
* `source_id`、WAV文件byte SHA、解码后完整mono `<f4` wave SHA、sample rate、frames；每次输入 `[start_frontier:target]` 的 `<f4` 字节SHA与bytes。不能只比较文件名/文字。
* 真实完整start state的规范JSON字节、SHA、全部跨调用字段；包括context/token IDs、tokens、audio segments及各段hash、cursor、language、initial IDs、decoder type、contract和transcript；不是只比较frontier或decoded text。
* `target=40000`、`start_frontier=32000`、`is_last=false`，exact original C/U、beam4、FP32、TF32/autocast关闭、500ms cadence、原corrector最大new tokens=8及do_sample=false；另外冻结实际tokenizer文件、vocab/special IDs、原prompt构造配置和start context IDs。完整EOS仅在自然完整服务自己的全部offered分母内处理，不把这个非EOS探针称EOS覆盖。
* `input_key_sha256`：由当前 `CandidateBridge.key` 的全部冻结输入产生；dispatch、worker收到后、完整完成receipt、durable body与实际Consumer绑定的input/start/end均复核。

**强制规则：** 受控重启完成且合同/genesis校验通过后，第一个指定worker上的原full call必须使用冻结start对象、target及wave；在该call完成前不在另一worker额外派生竞争任务。无故障配对使用相同规则。实际WAL restored root必须逐字节等于冻结start且target已由原ingress接受；不相等时记录 `CONTROL_INPUT_MISMATCH`，不得替换结果、伪造root或修改accepted时钟。所有失配/触发失败保留为控制失败分母，不能换样本或只发表成功的匹配格。

这条串行首call门是显式fixture干预，故只属于受控层。自然主矩阵继续原调度，不复制此门。

## 3. 实际 factID 故障点与无故障同构控制

故障点仍为 `after_durable_before_install_and_consume`。不以“运行N秒后”或仅“target=32000”定位：

1. 原完整C/U真实完成，append前确认该call完整parent与预先冻结的触发parent/end；原jobID、Owner epoch和物理incarnation保持。
2. `FactStore.commit` 完成flush/fsync并返回真实 `transition_id`、sequence、frame SHA、offset/end_offset。Owner发送这些原receipt及parent/end SHA；Supervisor独立核验原WAL frame，把本次**实际factID**绑定到唯一控制命令/trigger ledger，再向原已注册Owner组执行指定故障。
3. 同一个factID不得触发两次；未完成同步、receipt/frame不一致、预定完整end不一致、事实身份未知都不得当成预定after-durable样本。实际ID由真实原job和record产生，各策略ID可以不同；绝不把一个策略的jobID改成另一策略的ID。新源bootstrap若能冻结每格精确ID，则配置写入expected ID；否则冻结ID推导/内容谓词，保留 realized ID是在真实receipt后绑定的事实，不能伪称其字符串在运行前已知。
4. 恢复只重放原factID，不新增神经边；新forcedcall使用同一个冻结start32k、wave32k→40k、EOS=false。其原jobID是新Owner实际发起的ID，不能复用故障前ID。

**无故障同构控制是必选格。** 每个policy×loader_mode×repeat都有 `fault=none`，与其after-durable格使用相同source/settings、source wave、start/target/EOS、GPU映射、两worker、warmup、Reader、Consumer、arrival/origin策略及观察计划。到同一个完整fact内容/实际ID对应点只写 `would_fault_here`，正常返回并安装/消费；随后执行同一首call门。不暂停Reader、不reload、不延时模仿故障。记录predicate→首后继认证时延，而不是把不存在的restart叫RTO。

旧原设置可核查：`dsn_native_resilience_20261030/FORMAL_SHORT28_V1_RESULTS_v1/cells/SC_FORMAL_SHORT28_v1_BAC009S0908W0369_{none,owner_after_durable}_{conservative,fullcall}_r{0,1}/CONFIG.json`；新无故障格必须从当前新源真实normal配置派生并逐字段差异审计，允许差异仅cell ID、fault配置和预先冻结的repeat/order字段。历史normal不是新故障格的同期无故障结果。

## 4. 历史真实输入参照已经逐字节核实

本次只读验证四格原after-durable WAL的完整32k end state完全相同，保存为 `LOADER_CONTROL_HISTORICAL_INPUT_REFERENCE_v2.json`：

* 原执行source `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`。
* 完整32k cut规范字节SHA：`951d27d89c334b8d15689a4ecb0f033a589feaee6a7a2352054cd6ef8b778827`。
* WAV文件SHA：`1626b08c1f9b59794a4e3b3f2be926da1c570e20188efca5c835ebe26810a272`。
* 32k→40k `<f4` slice SHA：`4e5975533231077a11520cecf4da8014374f4b2f40c587dcd87293172e866da2`，32,000 bytes；16kHz，整source132,145frames，EOS=false。
* 每格真实transitionID、jobID、WAL sequence/frame SHA、parent/end SHA与整个WAL SHA均已记录；不是把同frontier当成同输入。

它支持“历史四格确实相同输入”的事实核查，**不替代新源bootstrap、强制门或新的同构对照**。

## 5. 后端配置与显存字段的适用性

本后端是原作者PyTorch Whisper + Hugging Face/Peft原C/U；不是vLLM。`max_model_len`、`gpu_memory_utilization`、vLLM KV block数、vLLM CUDA graph capture sizes须记录 `{value:null,status:not_applicable,reason:not_a_vLLM_engine}`，不得填写推测数值。原native KV是dictionary cache，closed cut要求已清空；不能把它换算为vLLM blocks。

| 新运行实际记录 | 来源和边界 |
|---|---|
| ASR context limits | loaded `engine.model.dims.n_text_ctx/n_audio_ctx/n_vocab`；这些是native容量，不冒名vLLM max_model_len |
| corrector容量与generation | loaded `config.max_position_embeddings`、原generation max_new_tokens/max_length/use_cache、tokenizer model_max_length；与实际原调用参数并列，不只看库default |
| dtype/device | ASR/corrector逐dtype×device参数elements/bytes，buffer同类摘要；实际 `hf_device_map`（没有就null+absent），requested corrector device_map='cuda'；物理GPU index/UUID与CUDA_VISIBLE_DEVICES映射 |
| allocator | `memory_allocated/reserved`、`max_memory_allocated/reserved`（明确worker-start累计peak，不调用reset）、allocator active/inactive split、allocation retries/OOM；`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`、alias必须absence；不是memory-utilization配置 |
| CUDA graphs | 应用无显式CUDAGraph/torch.cuda.graph/torch.compile启用路径；原日志未记录capture，历史count记unknown。新执行器冻结graph功能不启用，并记录可追踪capture API事件/count；未安装计数器就unknown，不能写observed0。`is_current_stream_capturing`只是瞬时观察，不证明此前没capture |
| 图/编译缓存 | 冻结TRITON/CUDA/TORCHINDUCTOR cache路径及原是否已有目录/文件的有界metadata；不把Triton kernel编译等同CUDA graph capture，不删缓存来制造cold |

原代码已有可复用挂点：`resilience_transport.py:11–14` completed/abandoned的RSS、CUDA allocated/reserved/worker-start peaks；`stage_worker.py:25` dtype、包、TF32/autocast/allocator环境；`native_bridge.py:141` requested device_map。旧记录没捕获的字段不补写为已知。

## 6. OS页缓存、权重驻留与IO

每次e0/e1加载前后、相同nofault predicate处，按冻结低频计划记录：`/proc/meminfo` 的Cached/Buffers/SReclaimable/MemAvailable/Dirty/Writeback/Shmem；`/proc/vmstat`的pgfault/pgmajfault/pgpgin/pgpgout/pswpin/pswpout；本worker `/proc/self/io`的rchar/read_bytes、RSS/RssAnon/RssFile、major/minor faults、CPU及墙钟。系统计数是整个host的并发观察，本进程IO也不直接等于weights磁盘读取，二者不能作算法因果收益。

**Cached总量不能替代每个weight文件的resident pages。** 可选只读mincore，或先检查vmtouch是否可用；每个文件记录path、inode/device、size/mtime、page/resident-page数、probe时刻及耗时。禁止drop_caches、全局cache设置、vmtouch touch/evict、madvise eviction、干扰别的任务。mincore只观察瞬时文件页驻留，不读取/touch页；它也不证明模型tensor或GPU权重常驻。probe无权限/不支持记unknown，不虚构0。

本次只读host能力核查已确认：libc暴露mincore，PATH无vmtouch；上述8个meminfo字段、6个vmstat字段和本进程IO可读取。记录在`LOADER_CONTROL_HOST_CAPABILITY_v2.json`。这只是当前host的能力/瞬时值，不是旧故障格的缓存状态；尚未扫描权重resident pages，也未验证mincore实际文件调用权限。

全权重SHA验证会真实读取并预热文件页：必须记录验证发生在计时哪一侧；若随后页已resident，称“fresh-process、观测到的page-cache状态”，不称“物理磁盘cold”。源/资产身份验证不能为了cold说法省略；预热和probe耗时也不能从真实故障RTO中抹掉。完整tensor字节hash会造成GPU→CPU读取，只在独立正确性gate执行，不塞进正常计时窗口。

每次probe自身耗时记录，故障/no-fault同频同阶段；逐copy同步、全文件resident扫描等重观察放微诊断层。若将宏观host采样集成真实E2E，成本留在原时钟内，两策略相同，并单列observer模式。host指标只用于加载归因，不放入UIR主比较的收益列。

## 7. CPU-map修复前的关卡

原ASR loader的CUDA checkpoint→CPU module→CUDA roundtrip目前只是源级候选。必须先实际记录torch.load tensor device/bytes、Whisper构造parameter device、load_state_dict真实copy和model.to阶段。

之后在同一新源、相同forced input做：原/原重复、候选/候选重复、原/候选配对；全部参数/buffers/alignment heads、完整cut/原C与IDs、token/config合同比较；原未修改author loader+完整C/U是合法oracle。若独立GPU输出不同，先用原/原分布区分代码/参数错误与原模型数值非确定性，不能认定候选一定错，也不能忽略差异。

仅在该关通过后进入两policy（Conservative/RevTrace）×两loader×fault/no-fault的同期受控服务配对，固定ABBA/BAAB、GPU交换及每个冻结诊断比较至少5次独立fresh-process配对repeat；这部分不替代五臂自然主矩阵。比较fault→首新认证/债务清除/全服务能耗，同时保留输入失配、触发失败、SLO失败。若微诊断有收益而E2E无净收益，保留负结果，不称恢复成功或RevTrace独占优化。

## 8. 交接文件

`LOADER_CONTROL_REVISION_v2.json` 是机器可读条件；新source/bootstrap/hash等未知项明确是启动阻断项。`loader_profiler_dev/loader_observer.py` 是隔离候选模块：host/proc、可选只读mincore、已初始化torch allocator与native后端元数据；尚未集成、冻结或执行，不编辑baseline v1。root负责集成到新的共同source_v2、验证observer与fixture，然后决定GPU启动。
