# 原作者连续执行基线：是否存在不必要的restore税

2026-11-11。只读当前NN3 `de0936b2e30179d63aeef6e235cd1af685578c58`、reference driver和固定author源码；没有读取pilot结果、计算新性能统计、改源码/配置/CURRENT或启动CPU/GPU。PILOT24与resource8优先级不变。

**判断：这是比立刻扩N16更高的方法学ROI控制，当前Conservative并非已实现的连续状态fast path。** 源码确实让每个原调用先完整restore；单source且同worker顺序推进时，其中许多restore原则上可以避免。是否足以改变端到端排序尚无实测，不能先写显著提速。优先考虑**给所有臂相同的“实际resident cut已等于start就跳过restore，否则原样恢复”**，在独立NN4上形成真实online continuous-original/Conservative对照；不只优惠某一个臂，也不重标签NN3结果。

## 1. 已从代码核实的差异

`NN3/native_bridge.py:151–162`的`step`无条件调用`restore_cut`，之后insert这次8000samples/真实EOS，再调用原`engine.infer`。`restore_cut:63–86`会清cache、从不可变wave重建/复制全部保留audio segments并核SHA、重新建立GPU token/initial-token tensor、回写cursor/context，再export一遍完整cut验证roundtrip。当前Conservative只限制从canonical派发，没有绕过该路径。

相反，`long_reference.py:25–42`的`continuous_transitions`在一次genesis初始化后，直接`insert_audio→engine.infer→export_cut`，步间没有restore。`pilot_driver_source_v2/run_reference.py:175–203`先执行该独立连续轨迹，再对每个exact start做两次恢复调用。已有full4因此支持**有限来源上原任务/完整state/C/IDs的一致性**，但它明确`reference_only`，没有真实ingress等待、Owner/WAL/实际Consumer和全服务计费，不能冒充已跑过的原作者online serving baseline。

固定author `simul_whisper.py:309–318,1136`在每次原infer结束本来就`_clean_cache`并reset beam decoder；当前cut要求native KV/attention/beam已清。**跳过restore不是保住跨调用KV的加速**，不能宣称恢复了原作者被wrapper剥夺的持久KV。可省的是真实已驻留状态的重复重建/复制/校验/分配及其同步效应。author源SHA仍为`9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7`；本次只读片段保存为`ORIGINAL_CONTINUOUS_AUTHOR_CODE_v1.json`。

## 2. 为什么它可能是实质公平性问题，又为什么不能先夸大

单source Conservative每次只允许一个current-parent full call；首个worker通常可连续完成该chain，第二个仍按共同预算加载/保留/计费。因此下一call的selected parent常是该worker刚返回的完整end。无条件重建可能给这个自然连续控制施加封装成本。Fullcall两worker轮换或跨source时，resident state可能不是下一job的start，那些restore仍然必要；共同fast path允许真实需要不同，而非强迫两策略支付相同不必要操作。

另一方面，原infer仍是主要神经工作，原native KV本就清空；restore不是另一遍ASR/C/U。不能由代码推断它足以解释整个Conservative差距。现有`worker_job_begin_perf→model_start`最多给restore+insert+同步的混合上界，`model_seconds`本身排除了restore，却含callback；没有独立restore段计时，不能拿worker−infer差直接叫restore成本。新增来源扩张前先消除/量化这个可辩护的税，比用更多speaker精确重复一个受质疑控制更有价值。

## 3. 优先的小改动：共同exact-resident fast path

worker在完成原完整调用并export关闭cut后保留`resident_descriptor`：source/contract、完整cut、实际worker incarnation及mutation generation。下一命令仅当**实际当前完整cut**与冻结start逐字节相同、clean native boundary成立且未有未跟踪mutation时，才跳过restore；不相同/unknown一律走原restore。初版可重新export实际entry cut核验，不能只凭“上次jobID相邻”或frontier/文字相同就命中；其验证开销须留在计时内。

成功full结果后更新descriptor；warmup/reset、source/session切换、restore异常、abandon、开放candidate/consume/projection或其它可能改变engine的路径必须明确更新或invalidate。尤其before-C abandon后的cache清理**不等于完整反馈状态回滚**，不得把它当作仍处于旧start。descriptor不是Owner selected authority；即使worker resident相等，原AU、WAL与SUP仍逐次执行，deadline不放宽。

建议实现顺序是共同`if_needed`模式和可审计`always_restore`控制，而非先加一套旁路server。每job记录命中/未命中原因、实际entry/start/end SHA、验证/restore/insert/infer/export各段host时钟、原执行结果和资源。初始单source online Conservative在命中时就是“原连续神经pipeline+相同服务合同wrapper”；多session时必要的context切换restore保留，不能暗增常驻模型或第三GPU来维持每chain独占worker。

## 4. 原作者online基线应保留什么

保留原500ms immutable admission、真实partial EOS、原C/U、同两FP32 resident workers预算（单chain用一个，另一个unused也照计资源）、原warmup、实际SUP Consumer、WAL同步和原服务clock。shared before-C early-ASR publication/cancellation hook也须保持。

这里有一个现有reference不能自动消除的风险：reference的直接`engine.infer`没有服务路径每次的early-view projection callback；service的`CandidateBridge.full_step`会做该wrapper逻辑。若online“原作者臂”顺便删掉early view/projection或WAL，输出时机与可观察服务合同就变了，既不能当同合同restore税控制，也不能据其display表现直接归因restore。可以另列纯原作者final-only服务点，但必须承认输出/可靠性合同不同，不能替代主要配对。

所以该臂可准确命名**“original continuous neural pipeline under the shared service contract”**。它比只有offline原作者reference更能回应R1的原任务在线/作者封装成本疑问；它仍是带本文admission/Consumer/WAL的适配wrapper，不是已发表StreamCorrect整套原server逐项复现，更不是SSBD/Retire完整复现。资源扩容与其它外部系统差距也不因此全部关闭。

## 5. hidden state、RNG与精确任务门

可行性来自已有连续/restore一致性与clean-cut合同，不能把它当普遍充分性证明。须在**新NN4同一执行源**验证：

* 原direct continuous、always-restore、if-needed且带真实服务callback三条路径，在相同wave/start/target/EOS和加载模型下，对完整state、原C选择、IDs、token/config合同逐边比较。相同visible text不够。
* 保存/比较CPU/CUDA/NumPy/Python RNG状态和实际native cache/decoder边界；不为通过gate而把服务改成每call重seed。torch.tensor/清cache通常不应消耗模型随机draw，但必须由同输入原/原重复和合法原连续oracle区分隐藏状态、数值执行与代码差异。
* 覆盖首call、连续命中、实际miss、source切换、session/worker incarnation变化、early projection与before-C abandon后下一call；actor独占mutation规则必须可审计。只维护一个“上次完整cut”标记而没有invalidations不够。
* 失败保留首次边界与同输入重复/原连续prefix控制，不替换结果或降低完整state/原任务门。所有参考/模型调用是另外的paid work，不写入serving成功数。

## 6. 取舍与后续边界

最小共同fast path主要涉及`NativeBridge.step`的entry判断、worker状态描述符与失效路径、时钟字段；比新warm-worker跨Owner adoption小得多。粗估1–2工程日实现和针对性CPU控制，另1–2日原任务gate/配对与独立审查，取决于隐藏状态是否出现；不是交付承诺。无需先做新N16或新scheduler。

建议在当前pilot/resource8闭合后，把它作为**优先的窄控制候选**：另冻结NN4、生成NN4原连续/exact-start references，在相同旧来源上同期配对online Conservative和Fullcall；若需要识别wrapper收益，NN4内部预先冻结always-restore/if-needed两模式。source变更必须完整新commit/manifest/env/config和8TB raw，NN3完整保留，不能改标签或用旧reference冒充新source任务门。

如果fast path命中多但净收益小，报告wrapper税已被控制且不足以解释差距，R1就更可评估；若Conservative显著追近，应接受并以新公平控制收缩旧增益，不称新算法失败或偷偷偏袒。若Fullcall也同样获益，这是共同服务工程改进。**目前不自动开工程分支或启动运行；先完成既定阶段，再由root据该公平性与潜在端到端机会冻结具体控制。**
