# 外部模型排空与runtime完成：V1分析失败的端点定义诊断

日期：2026-11-19。仅阅读已完成80格的有界JSON和冻结原实现，未运行神经推理、未修改GPU数据/driver/runtime/audit，未改CURRENT或Root HEAD。旧分析f29和失败运行记录保留。

## 判定

**这是派生分析中的时间窗假设错误，不是已发现的模型能量缺失。** f29把`external physical_drain.confirmed_perf >= SERVICE_END.service_end_perf`当成必须条件，但两个独立定义不具有这个偏序。主能量列在冻结实验开始前就定义为origin到外部首次确认实际READY模型worker退出/CUDA为空；原runtime能量则到Supervisor记录的SERVICE_END。

80格中75/80的外部确认比runtime marker更早。`runtime end - external drain`最小-0.109110682s、中位0.077674913s、最大0.529559793s；另外5格则是外部采样确认更晚。这正说明独立观察上界与CPU完成标记没有固定先后关系。

## 具体失败与极值

- 首个失败cell `RS18_PILOT20_V1_BAC009S0769W0190_r0s1_r1`：origin=18003.877178209；外部查询begin=18029.059983246；确认drain=18029.232222118；runtime SERVICE_END=18029.742076924，差0.509854806s。其最终实际Canonical/EOS消费早在18017.158280509，比外部确认早12.073941609s。
- 最大正差cell `RS18_CONFIRM60_V1_BAC009S0914W0456_conservative_s1_r0`：drain=23524.680643542，runtime end=23525.210203335，差0.529559793s。

逐格完整时间及差值：[ALL80表](DRAIN_SERVICE_ENDPOINT_ALL80.csv)；75个早确认：[75格表](DRAIN_BEFORE_RUNTIME75.csv)；原标量JSON：[逐格值](DRAIN_SERVICE_ENDPOINT_RECOUNT_ROWS.json)。这些表只诊断端点，不是80格最终性能汇总。

## 原执行机制

1. `production_support/external_power.py:35–44`持续采样。实际READY PID均absent/Z/X且两GPU无compute owner时，仅第一次设置`drain.confirmed_perf=observation_end_perf`。它是采样确认上界，不是精确硬件退出时刻。
2. `ExternalObserver.finish:58–64`要求最终采样覆盖调用者给出的not_before，但不把已经记录的第一次drain重新延后。因此结束观测流与能量积分的drain端点是两个对象。
3. `runtime_source/resilience_owner.py:182–203`先停止worker并确认CUDA释放，再处理封闭channel尾部、发送owner_finished，最后关闭store和日志。
4. `runtime_source/resilience_trial.py:146–159`收到owner_finished后还join Owner、完成循环及accepted义务检查，才记录SERVICE_END。这个CPU/监督完成标记可晚于外部对模型进程的首次空确认。源码说明顺序可能性，未把两个时点之间的时长精确归因于某个未单独计时的CPU子阶段。
5. `audit_results.audit_cell`原本就分别保存origin→useful EOS、origin→external model drain及original_source_energy。没有将外部窗定义为必须覆盖所有post-worker CPU记账。

## 数据是否缺失的独立核对

- 80/80外部能量begin等于原origin、end等于记录的外部drain；两板积分对象完整。
- 80/80最终实际Canonical和certified EOS均在drain之前；EOS提前范围4.489537797–12.073941609s。因此本批没有发现该主窗口漏掉尚未交付的有用选定结果。
- 80/80drain PID集合等于ownership actual_READY_pids；V2还绑定READY_gate的同一两模型PID。
- 80/80original_source_energy原对象与runtime SUMMARY.energy相等，原对象的origin和SERVICE_END分别绑定其自身窗口。不同采样器和不同端点的总J不能相减后命名为纯CPU尾部能量。

## 最小正确修复与新身份

保留旧失败，clone成analysis_source_v2，只替换错误的跨窗排序要求为实际定义绑定：origin<=drain、observation_begin<=drain、external energy begin/end/duration精确绑定、三份实际READY PID集合相同、最后Canonical/EOS已在窗口内；原runtime能量原子完整相等且绑定自己的SERVICE_END。主能量数值、credit、worker账和80个GPU观测未改变。

V2 clean commit：`720c6e27a805cf98d98a5ae8fd193ec664751857`，3文件manifest与bundle另存；旧f29目录及V1失败记录不动。每个cell的external physical-drain、runtime SERVICE_END及original_source_energy在V2输出中分开保留，不合并端点，不改为有利的新测量窗口。Root负责SOURCE_MAP、正式preflight与执行。
