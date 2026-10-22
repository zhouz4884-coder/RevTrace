# Stage2资格检查修订：唯一追加的跨batch压力档

首16源侦察已完整保留，原门槛NO-GO不撤销。它的峰值为14个活动源（单worker microbatch=16），且最佳固定Goodput距arrival上界仅1.4%。该负载无法满足用户要求的“同run在线调度确有必要”，不能将之解释为Elastic算法已失败。

为检验明确的**跨batch资源压力**，只追加一个32源档（不继续无限搜索负载）：同test-clean语料按新的冻结SHA顺序选32个不同speaker、每人一个完整16–28s utterance，排除与旧开发池/PhaseD完全相同的utterance，不声称speaker与此前全部实验都不重叠。未用任何新ASR输出/质量标签选样。若不足32合格speaker，停止资格检查，不拼接/复制凑数。

同32源比较固定rho1/2/3，sync、sid×2s uniform-stagger、low-high-low三到达；后者sid0/1在0s、sid2–29在10s、sid30/31在42s。双GPU、microbatch16、精度、预算、适配器、保护和全部SLO/质量约束不变。观察的是两个以上批次/排队与parent链的相互作用，不改保护机制来救结果。

仍为9个scout；门槛与SPACE_GATE_OPERATIONAL一致（低/高阶段按释放时钟10/42s划分）。首16与本32绝不混成独立重复或合并中位数。只在本档显示明确空间才写最小Elastic；若仍不触发，结束升级NO-GO。此修订是在新32源GPU输出出现之前冻结，不伪装成首轮预注册。
