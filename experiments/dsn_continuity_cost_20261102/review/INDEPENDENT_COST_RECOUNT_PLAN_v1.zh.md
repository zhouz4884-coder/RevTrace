# 当前成本的独立汇总方案（待原NN16结束后再实施）

日期2026-11-02。此为方案，不是新脚本或运行结果。独占NN窗口内不访问B盘，不运行reader/hash/CPU。冻结observer为`3cf7cd10a3ba76958b4173aa20eb6116ac779a39`，driver身份以root当前冻结manifest为准；原实际NN4f身份保持独立。CPU12的正式gate已完成；NN16未在本方案中预写结果。

## 输入与独立性

由root在NN独占窗口结束、资源闭合后提供有界副本/原盘受控路径：campaign plan、PRELAUNCH/HANDLE/DRIVER_AUDIT、各cell原GATE/SUMMARY、原offered/reference/Consumer端点、cost_spans JSONL与元数据、外部共同origin→确认model drain窗口及两板能量。先验全部source/config/environment、raw成员SHA和计数，再读取；缺失留失败/UNKNOWN，不通过补零完成矩阵。

新独立summarizer不得调用observer的`summarize_spans.py`或driver的`span_audit`来证明自身。可以读取它们的报告作最终对照，但必须直接从span JSONL构建森林和计量。与主分析一样，独立summarizer也需新commit/完整manifest/controls/ENV/run record/gate，不在冻结source_dev/source_v2上改动。

## 一、span森林重建

1. 以`cell_id,role,pid,thread_id,span_id`为完整key，不能把跨进程同号span合并。每span数值有限、end≥start、wall=end−start、threadCPU≥0；原processCPU只作inclusive观测。
2. parent必须存在且同PID/线程，时间包含child；同线程直接siblings不能发生重叠。父child关系必须无环。线程root span按时间做union，不把不同并行线程的wall相加为一个run关键路径。
3. 从直接children重算exclusive wall与threadCPU，核对原字段/负残差计数；不信任主summary中的clamped结果。inclusive family只能单列，不能相加得到全协议时间；processCPU与threadCPU也不能相加。
4. RAM记录及wrapper bookkeeping在inner span之外的部分不是免费，但不能从span残差直接剥离成纯协议或lock成本。off/on端点承接其总影响；wall−threadCPU继续标未归因等待/调度。

建议导出`INDEPENDENT_SPANS.csv`（校验字段与树关系）、`THREAD_ROOT_UNIONS.csv`、`EXCLUSIVE_FAMILIES.csv`、`COUNT_RECONCILIATION.json`，分别保留CPU replay与actualNN，不合并两种证据层。

## 二、对象数与窗口

- WAL.complete_fact_commit次数应对应实际新durable canonical事实；genesis/恢复旧fact另列，不把replay加成新C/U边。
- Consumer apply次数对应actual publication处理，replay、duplicate/late/reject另列。正常NN矩阵无故障/拒绝不代表异常路径成本已被实测。
- CPU完整FactStore/Consumer与EL/full-input、ownedbind probe分别汇总；后者不重建原Owner动态队列/history占用。
- 只完整落在原服务窗口内的span进入该window成本，跨边界span列明；不能按wall比例虚构threadCPU切片。另报告Owner export相对真实model drain、SERVICE_END的位置和bytes。
- 新文件/进程不称冷filesystem。实际fsync的CPU/wall与模型调用host intervals分开，不能把模型interval误当GPU kernel work。

## 三、NN16配对与命名

固定配对key为`source_id,arm,repeat`，off/on应各唯一一格，共8个pair；两个独立声学source，不是16个独立样本。完整task/reference、EOS/all-offered、实际Consumer、physical drain、allocator/worker/设备轮换均先验；任何身份/语义异常保留并停止强效果主张。

每pair给on−off的：D2/C8信用、whole-run pass、display/certified P99、EOS tail delay、原C/U/实际调用/publication数、共同window两板energy与whole elapsed。若observer改变组批/dispatch/输入，其差值仍是**观测器总系统影响**；不能叫固定host指令的纯timer开销。两个repeat给原值/范围，不以小N制造总体显著性。

Conservative vsFull-call比较是策略端到端tradeoff，两者都付协议；不改称纯guard税。旧bdfa→4f只可称total reliability-extension change。CPU12单独回答全对象各操作支付多少资源，不能被当成正常神经服务的净开销。

## 四、最低独立控制

冻结后至少验证：跨PID同span号不合并、嵌套exclusive、重叠siblings失败、丢parent失败、负残差失败、跨window span单列、off/on重复/缺失pair失败、genesis/replay不计新fact、同毫秒值不同实际window不可拼接、zero-observation off有完整安全/task对象而非缺数据。

## 五、预先接受的结果解释

- spanCPU低且端点off/on接近：可写当前协议路径成本与可控观测影响，不写“全部协议零开销”。
- CPU小但WAL/Consumer阻塞wall明显：说明同步/IO是实测支点，不能用CPU微秒掩盖wall。
- 小EOS margin被observer推过D2：报告真实观测配置和失败，不把off最佳性能与on最全证据拼成一个run。
- 发现某个重复完整state序列化/验证开销高：它是可检验优化机会；只有同安全谓词、同完整输出/时钟、强对照验证后才称修复。不能依据相关span就断言它是旧EOS失败唯一根因。
- 新source与NN身份、c4实际whole-view/原调用检查未闭合时：最终cost结论保持pending，不因primary driver PASS宣布完整论文验收。
