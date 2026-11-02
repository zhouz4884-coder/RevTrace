# 当前完整协议成本：冻结前执行方案

日期2026-11-02。只写本cost目录；原NN4f/source_v2、旧raw、论文及CURRENT未修改。本文件是计划，不是完成结果；实际source/manifest/config/environment/raw/summary/gate须由Root冻结并登记后启动。

## 要回答的问题

当前完整输入资格、原程序结果选择绑定、身份准入/安装、Consumer整视图验证与WAL同步各支付了什么host资源；这些费用是否可能解释可靠性扩展及EOS边界？同时确认观测本身对真实服务有多大影响。

不能把off/on计时差叫协议净开销。二者都完整执行相同安全、原C/U、持久化、Consumer与日志。Conservative/Fullcall包含不同提前调用/调度，差值也不是纯guard税。原神经C/U计算与绑定其真实结果的AU CPU必须分开。

## 源与三种证据

1. 原实际NN源为4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47，原59文件manifest60ae…不变。cost/source_dev的vendor_nn4f是逐字节归档副本，不是新执行身份。正式程序始终从原独立clean4f checkout导入，验证所有59文件和完整Git identity。
2. CPU trace replay使用既有最终matched两来源×两策略的r0全raw，每case三新CPU进程，共12；CUDA_VISIBLE_DEVICES为空。按原fact/publication顺序调用原FactStore与SurvivorConsumer，原full cut/C/IDs/job全部保留，实际fsync启用。重建facts.wal必须逐字节等于原file，Consumer除实际observed新时钟外逐语义字段相同。真实完整输入比较/owned-call binding probe另列，不伪造Owner调度，不模拟服务时延。这一层叫**真实完整对象的协议CPU/IO足迹**。
3. 新真实NN正常服务：固定S0908W0369、S0916W0463（原metadata选择记录前两条），两策略×off/on计时×两fresh；共16格。repeat交换GPU并反转off/on顺序；原500ms/EOS/all-offered/D2/C8/完整输出/模型/精度/warmup/allocator/两完整workers不改。先4格验证身份、实际NN、source-preserved C/U/reference/Consumer/观察器可用；只有技术/语义/资源失败才停，不以正负性能裁剪后12格。

## 计时与账本

span同时含perf_counter_ns、thread_time_ns、process_time_ns、PID/thread、parent span和异常。Owner child通过spawn-safe cost_runtime.observed_owner在自己进程安装probe；Supervisor/Consumer独立安装。Worker原神经不patch。测EL调度/依赖/actual-input反证与提升扫描；原owned binding、消息分类；完整原结果选择、durable selected commit与安装；FactStore验证/编码/写/flush/fsync；Consumer durable frame与完整依赖应用；原Journal写。

没有改原return/exception/result，也没有关闭任何谓词。热路径只RAM记录，最多100万span；overflow保留原工作但使成本研究FAIL。**Inclusive families不可相加。** 同线程子span只从parent扣出exclusive threadCPU/wall；跨线程/process wall不相加当端到端，processCPU可能含后台reader线程，因此不作为当前线程的独占成本。wall−threadCPU只叫阻塞/调度等未归因部分，不叫lock wait。当前串行Owner的这些协议函数没有单独显式锁；队列/IPC内部锁等待未被独立测量，不能从残差推算。

span文件批量导出：Owner在原owner_main返回、模型/CUDA已排空后导出，但原Supervisor会join它，所以**Owner导出仍早于原SERVICE_END，观测总影响包含这段**；记录export begin/end/bytes。Supervisor导出在原trial返回后。最终两板能耗以Root外部共同origin→confirmed physical model drain为主，同时保留原SERVICE_END/source energy，不能隐藏导出税或手工从deadline扣除。per-span摘要只选完整落在原窗口内的span，边界span另计，不按时长比例编造CPU。

CPU新输出文件并不意味cold filesystem；cache状态未控制，不调用drop_caches。fsync保留实际设备/FS记录；新文件/WAL与真实trace读cache行为分开。

## 验收与负例

Root统一commit+完整manifest+preflight+环境与assets/author gate，原模型/dataset/raw在8TB；逐cell运行record先于启动。CPU完整objects/byte-equivalent journal/Consumer语义快照是硬门。NN原任务、reference、全部input/EOS/Consumer、完整state/C/IDs、两workerREADY和physicaldrain是硬门；off/on的调度/调用/publication数量若变化，按真实总观测影响报告，不能假设纯host tax。真实输出差异先按same-input、repeat、legal original oracle诊断，不能删失败格。

最终产物应包括每层原端点与两板共同窗口能量、原NN model-host intervals（不是kernel时间）、嵌套span足迹、off/on成对差和全失败/未知。最有价值的结果也可能是“协议CPU足迹小但IO/重叠不能从简单相加归因”；不预设百分比开销必须很小。

Root启动CLI：

`python build_plan.py --paired-plan <原paired32计划> --observer-commit <新完整commit> --observer-manifest <新manifest> --out <新configs> --raw-root <8TB新raw>`

`CUDA_VISIBLE_DEVICES='' python trace_cost.py --base-source <clean4f> --base-manifest <原SOURCE_v2.json> --observer-manifest <新costmanifest> --raw <既有matched normal cell> --out <新CPU cell>`

`python observed_trial.py --base-source <clean4f> --base-manifest <原SOURCE_v2.json> --observer-manifest <新costmanifest> --config <新冻结cell> --out <8TB新NN cell>`

外部watchdog、实际GPU lease/共同power与原actual-trace checker复核由Root复用已冻结a13/c4工具，不由此agent自行启动GPU。
