# 外部资源账本的先行只读核验

2026-11-11。此文件先于新的ledger正式重计，依据已归档原始行和实际bdfa执行source；没有新GPU。本目录已完成的29格内容两个CPU门不受本项影响。曝光字符秒/稳定前缀v2仍保持未冻结、未启动。

## 已直接证实的两处关键错误

**24次abandoned不能叫“神经模型前拦截”或“纯神经0”。** 原 `FULLSPEC_LEDGER.abandoned` 明确写 `asr_prefix_executed=true`、`learned_C_executed=false`、`C_U_completed=false`。实际source `dsn_streamcorrect_stage_handoff_20261029/packages/SOURCE_v3.json` 指向bdfa；其 `source_snapshot_v3/candidate_bridge.py` 的before_corrector钩子在原ASR已经执行、即将调用学习式C时检查hint。worker收到该异常后还执行CUDA同步、清缓存、再次同步。abandoned没有完整 `record.model_seconds` 字段；外部 `build_ledger.py` 用缺省0补出来，不能把缺测ASR模型时间称为零。

完成调用的 `model_seconds` 也不是“纯GPU/纯神经阶段”：`native_bridge.step` 在restore和insert之后同步CUDA，包住完整 `engine.infer`，其中包含ASR、C/U和边界callback；结束同步后再导出状态。worker_job_wall还包含restore/insert/export等。故69.017与68.308即使数值重现，也应分别称完整调用worker区间和原infer墙钟区间，不能拿后者做独占GPU算时。

**两个j16晚丢不是已证实可用“更早发hint”修好的竞态。** 两次都是S0908、目标6秒、反证父状态frontier88000。原行如下：

| 实际perf_counter | r0 | r1 |
|---|---:|---:|
| child j16 ASR-early produced |5030168.342780603|5029960.404425853|
| parent j15 infer model_end |5030168.349519103|5029960.474955507|
| parent j15 terminal received |5030168.353311929|5029960.479305559|
| parent canonical_install receipt |5030168.375709036|5029960.490804591|
| j16 invalid hint observed |5030168.379537113|5029960.495942685|
| child j16 model_end |5030168.522841267|5029960.588499070|

源码先执行before_corrector检查，之后才发送ASR-early；但连父调用infer结束都分别比child ASR发送晚6.739ms/70.530ms。因此在合法before-C检查点，实际父选择结果尚未产生；即使把WAL、Owner处理和hint队列时延假设为0，也不能凭空提前得到反证。该观测支持研究“C中途的合法取消点”或“before-C等待父输入”及其代价，不支持把旧两例写成已定位的hint下发实现缺陷。

两个精确cell：

`SERVICE_RESULTS_v1/SC_FINAL_INDEPENDENT_V1_two_full_spec_early_BAC009S0908W0369_r{0,1}`，各自 `native_jobs.jsonl` 的j15/j16和 `events.jsonl` 的j16 ASR/hint、j15安装。两个计时观察属于同一声学模式，不能算两个独立source。

## 23.779秒需要改名并重新分账

外部定义 `(parent_install + child.model_seconds) − child.worker_job_end`。展开等于

`parent_install − child.model_start − (child.worker_job_end − child.model_end)`。

当父安装在该次infer区间内，它主要是已完成infer前缀减去实际post-infer导出时间，不是观察到的因果服务延迟节约。它还假定重启调用具有相同infer时长、立即获槽、忽略重启restore/排队等，且跨job求和不能当episode关键路径。92次都为正只说明该固定假设下存在时序重叠机会，不能代替三/四策略真实闭环重跑。

同理69.017是92个被采用调用的**全程**worker时长，不是截至父安装已经完成、可因取消而丢失的部分。新重计必须分别给：完整worker/infer区间；在父接收—安装receipt边界前的区间交集；安装后的剩余部分。promotion自身没有原始timestamp，不能把canonical_install日志戳冒充精确promotion瞬间。真正切换发生在parent receipt到安装日志之间，应给对应上下界。

## 新正式CPU重计的事前输入与估计量

后续新ID、完整source/config/env、8TB raw/summary/gate先冻结，再执行。只读旧四source16cell，两个repeat仍留在source内；归档Collection manifest逐文件核对原 `events/native_jobs/FULLSPEC_LEDGER/CONFIG/SUMMARY/DISPATCHES/CANONICAL_HISTORIES/RUN_RECORD/GATE`。逐job校验cell/source/arm/repeat、dispatch frozen-start与完整返回和实际父状态绑定。

全dispatch守恒以最终状态分类：installed、abandoned-before-C、completed-discarded、completed-ready-uninstalled、active-without-terminal、suppressed-before-execution、fault/other。每个状态有原事件或明确unknown，不能预设 `dispatch=install+abandon+discard`。ready数为0只能描述旧轨迹，不能推导ready-only在改调度后等价保守臂。

正式估计量：1)全调用资源构成；2)父receipt/安装边界前后的实际worker和infer交集及界；3)缺测ASR infer保持unknown；4)外部23.779公式以原名加proxy标记重现、并展示代数与假设；5)两晚丢的证据可用时间相对before-C检查点上界；6)每source两repeat完整差，不设置2%有效性阈值。身份、哈希和完整状态等价必须严格，计时漂移仅诊断，不负责决定运行是否有效。

这项先行核验已经足以否定“24次未触发神经模型”和“更早发同一proof即可省掉两次C”的表述；69.017/13.515、5.11和23.779的精确总量与完整守恒仍以新正式CPU门为准。
