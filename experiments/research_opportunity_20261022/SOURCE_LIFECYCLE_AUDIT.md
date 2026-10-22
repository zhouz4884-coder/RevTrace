# 源码级机会与生命周期审计

执行日2026-10-22。正式起点是GitHub `experiments/phase_d_20261021`，主分支实时核验为`87520c085f34797ac2f33b03354268b576ebc408`，268个manifest条目逐SHA匹配。测量runtime仍为`2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8`。原工作树已有大量修改，本轮未覆盖；800个TeX/Bib/PDF在开始时冻结哈希。

## 继承的正式决策

Phase N的A/B/C、全token/stop/Phi checker的有界正确性保留；C2 0/98及时、付费C3 0–1/98及时且一致、V2就绪/完整成本门槛失败仍为NO-GO。Phase D的固定历史时序效应、可信Render/消费规则有条件GO；安全字符串后缀拼接、传统组合不可表达/独占性能主张NO-GO。长Whisper完整性/历史内存、host/storage/network故障等边界没有被本轮解决。全部既有决策的文件哈希见INTAKE。

## B：逐模块实际边界

下列行号属于冻结Phase D runtime，不是工作树旧src，也不是永久API。完整源字节与方法范围以冻结源码SHA为准。

| 模块 | 实际行为 | coordinator单独崩溃后的缺口 |
|---|---|---|
| `live_qwen.py:77–201` | 构造时创建空jobs/inflight/sequence，再重放WAL。恢复F/P/已提交ID，不恢复在途源记录 | 无法由WAL得知哪个旧Worker真的执行了哪个未提交任务 |
| `_make_job:273–337` | 任务含sid、source、parent、P、chunk、音频范围/摘要、χ/runtime；ID由内存sequence生成 | 重启序号可重用；执行Job dict本身没有独立持久的dispatch epoch/worker incarnation |
| `_receive:420–512` | 先核对本地inflight的完整result ID集合，再查jobs、runtime/audio摘要和时间；Authority parent必须仍当前 | 仅去掉epoch拒绝没有意义：旧映射和来源已经丢失；字符串job_id不足以恢复可信关联 |
| `_commit_ready:514–608` | 从**当前状态epoch**构造CanonicalSegmentJob，新建证书，经原准入再WAL | 原DualAxis证书字段自身没有epoch；epoch由job/state检查。因此必须区分旧计算来源与新纪元重新授权，不能把证书当执行attestation |
| `tc_live_worker.py:22–323` | Worker验证静态资产/音频，独立加载模型；队列读取不可变任务并生成Z/P/text | 同可信Worker确实可能继续生成，但没有新Coordinator可按名称重新连接的服务接口 |
| `GPUExecutor:326–400` | Coordinator用spawn创建mp.Queue并把句柄传给Worker；自身poll/held_result/telemetry都是内存 | Queue没有公布的网络/本地地址；新Python进程不能只给旧队列取个名字重开。仅Worker存活不等于结果可达 |
| `run_tc_live_qwen.py` | CLI拥有Worker、CPU Renderer和消费线程；正常finally关闭Worker | 原CLI先初始化Worker再恢复scheduler；不能把该初始化顺序产生的31秒视为WAL性质的下界 |
| `durable_journal.py:163+` | 排他owner锁、完整frame/校验、parent/delta一致性、fsync成功后安装 | 它持久化准入史，不持久化未提交执行来源 |
| `_append_restart_epoch:581+` | 恢复时增加epoch并同步记录，F/P不因此改变 | 新owner可有相同合法输入，但仍须证明旧结果的来源、未被提交、parent/音频/χ一致 |
| `certified_display.py` | 独立Render、epoch/version/transaction绑定、本地FIFO实际view应用 | 不能以server emit代替消费；恢复已安装事实无需等待额外GPU推理 |

## 最小可行存活路径

本轮原型只有一个Supervisor、一个FP32 Authority Worker和按需重启的Coordinator，不是完整新服务。Supervisor创建并拥有两条原mp.Queue，保存不可变派发Job及其摘要、manifest/χ、worker incarnation、旧dispatch epoch和Result摘要。Coordinator通过由Supervisor新建的本地Pipe通信；新连接不是“重连旧Queue”。

Supervisor/Worker/OS存活且可信是前提。结果摘要只能证明记录未改，不是GPU硬件证明；来源依据受信监督器实际拥有的Worker队列和独立incarnation。没有绕过身份认证，没有给任意同名Job或自行声称runtime的结果写权限。

新owner持有排他WAL锁。逻辑重建为：从ledger取sid/F/P/checkpoint；由固定session manifest取source/language及原始wave；以fine/rho确定下一个end；重新计算prefix/interval摘要，绑定同χ/runtime。`reconstruction.py`对22个真实故障单元逐字段独立复算，与原Job的全部逻辑输入字段一致。原型在线用固定可信模板加恢复F/P重建；不是已完成多会话通用重连实现。

**可重建输入不等于来源证明。** 只有Supervisor仍能提供该任务的实际派发/Worker/Result关联、Worker仍存活、旧任务是当前合法下一步且尚未提交，才允许新owner选择旧计算结果。它使用新epoch的Job、原证书构造、原准入、可信Render和原WAL完成新的授权。已持久任务直接重放发布，不再次收养或安装。

## 不应混成一个优化的三件事

1. 保持CPU/GPU角色存活，避免重新加载模型：普通故障域拆分/驻留收益。
2. WAL已有提交时先重放发布、延后无关模型加载：恢复路径排序修复。
3. 尚未安装的合法在途/已完成结果被新owner重新授权：本轮净收养机会；必须只和同Worker存活策略的Strict比较。

B不声称一般RPC/任务重试/结果缓存不能实现它，也没有证明可恢复Supervisor或Worker故障。后续生产化还要有可持久审计的授权来源、ACK/回收、真实断连、长期内存和多会话压力；原型没有实现这些完整系统功能。
