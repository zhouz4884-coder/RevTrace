# 两GPU用于单chain提前执行还是多session并行：独立取舍

2026-11-11。仅讨论与读取root授权的**已完成本地PILOT24/OP bounded结果**及源码；不读取运行中的resource8 raw，不运行分析、模型或新策略，不修改NN3/CURRENT。resource8的部分口头状态只作为待核问题，最终以完整8格为准。

**判断：保留为有界调度诊断，暂不升为新的研究分支。** canonical-first RR可能压住单chain条件执行，但两GPU都在服务其它canonical chain时，并没有空闲的“spare GPU”；优先conditional是资源再分配，会延后别的合法需求。合法性条件可以保障“不错误使用”，不能免费给出容量或公平性。普通EDF/priority本身也不是新的RevTrace算法。当前最高ROI仍是确认Fullcall相对Ready-only的合法在飞效果，而不是立即换调度目标寻找赢家。

## 1. 现有完成证据实际支持什么

PILOT24使用NN `de0936b2e30179d63aeef6e235cd1af685578c58`；完成SUMMARY SHA `fdf635d499f4c32431f5632151582e219a6a7a542e12b16ff0fb62241598893a`。同一单session合同下：

| 对象（各4次、两speaker、两fresh repeat） | 已完成观察 |
|---|---|
| Fullcall | dual-credit32.340125/33.11625audio-s，即97.656%；whole-run2/4通过；56个实际model-active兼容确认事件 |
| Ready-only | credit12.5audio-s，37.746%；ready命中0；56次相同完整输入/target重派；累计worker wall约82.145s |
| Fullcall paid work | 累计worker wall约51.765s；与Ready-only差约30.38**worker-s**，不是独占GPU active time |
| Strong Vdag | credit与Fullcall相同；两speaker的ancestor-only分歧机会都是0，不是额外规则已获独占收益 |

当前四个Conservative完整run的worker−infer总差各约0.17–0.19秒；无infer缺测。这是每个**整个run**的restore+insert+export等直接混合开销上界，不是单次call，也不是完整因果wrapper税（allocator/间接效应未识别）。它不能支撑“restore额外花掉几十秒”的猜测；原作者continuous online控制仍有R1公平性价值，但目前直接开销不像Fullcall/Ready-only差距的主解释。不能搬用旧bank的worker成本替代这些新数。

resource8的2/4-session是不同source/到达时序配置，不能把两个独立single run的97.656%或credit相加，假装同时服务时的实测counterfactual。单chain高信用和多chain低信用提出容量分配问题，并不已经证明优先conditional会净改善。

## 2. 可用性与资源机会的门

NN3 `round_robin_dispatch.py:27–57`先选所有source的canonical候选，再选conditional；Owner保留相同AU/WAL/SUP守卫。要存在可测试的再分配，必须在**真实空闲worker的dispatch时刻**，同时出现另一source canonical backlog与一个已接受target的合法conditional候选。现有shared-dispatch日志已记录这两类eligible source集合；完整resource8结束后先检查它，不需要先写新scheduler。

若两类候选从未同时可派，新规则在不等待/造空转的前提下没有处理强度，EDF名称不会创造机会。即使两者同时存在，conditional只是允许推测计算；其完整输入还可能UNKNOWN并后来refute，不能把尚未获AU的预测称为已知“deadline-supported usefulness”。原输入/原task及最终实际parent检查不变，所有错预测/重算仍付款。

原deadline `origin+frontier/16000+D/C`可在线得知，未来model耗时、未来输入确认和最终view真值不可使用。普通EDF往往继续优先更早frontier的canonical，因此未必改变canonical-first行为；若跳过已过期canonical以追逐新信用，还受原反馈chain依赖约束，不能少算旧步骤或把它们移出offered分母。

## 3. 若值得试，只试一条已冻结、非oracle规则

在当前阶段闭合且门成立后，可考虑**一个**development point：按resource计划的既定顺序取第一个2-session group，保留其source、500ms到达、原EOS与G；不按哪组credit差来挑group。不用4-session/不同voice/不同threshold反复搜索。

候选共同规则为“带一个continuation token的轮转”：某source的canonical call实际派发后，可给该source一次有限conditional continuation优先权；另一worker空闲、该tail与target已可派时，最多使用一次；其它backlogged source获得canonical turn之前不得重复授token。没有eligible conditional立即回落其它canonical，Conservative也使用同一算法并因无conditional候选回落，**不人为闲置它的第二worker**。所有已接受工作最终必须原样完成；dispatch-count公平上限不冒充未知model时长下的墙钟公平保证。

这一点只检验受限per-chain弹性，不声称该简单token规则为新最优scheduler。相同NN4上比较两个dispatch模式（原RR/该规则）×两策略（Conservative/Fullcall），原state/模型/Consumer/WAL/取消点和restore模式相同。若NN4同时引入resident fast path，各模式都开启相同实现；不能把NN3 RR直接与NN4新规则相比后全归因调度。

预先冻结4个小counterbalance块（两种source初始turn×两种GPU映射），各块运行上述四格，共16个grouped运行；source和执行顺序按固定seed平衡，不使用未来runtime、模型输出或事后最优priority。它比“一个repeat选先给较快voice两卡”的8格更能分开source/GPU偏置，但仍是两声学来源的开发点，不能伪装独立确认。若这份预算不如T1，则不运行它，而非削掉公平对照。

## 4. 一个能被否证的判断，而不是只看总credit

预先判断：同G、同两GPU和原offered下，受限continuation是否产生真实model-active合法保留，并改善**同一个实际grouped run**的总audio-second credit，而且不以某source严重退化换来。描述性交互可列为 `(Full_new−Full_RR)−(Cons_new−Cons_RR)`，不称每条合法性检查的独立加成。

必须同时报告每source credit/fraction、最差source、最长无进展/覆盖缺口、原D2/C8及whole-run失败、final task完成、已过期债务清空、真实paid work/取消/重派和双板能耗。所有失败与原offered保持，不能只报成功source或条件于获两卡的片段。whole-run仍失败时，总credit变好不能写“服务容量/SLO通过”。

为paper主线保留“更好分配”结论至少应有：总credit可重复增加，同时每source的配对counterbalance汇总credit不下降；这只是预定小开发门，不是统计等效或普遍Pareto保证。如果总量升而一位speaker掉到近零，应报告**QoS集中/公平性trade-off**，不能包装成无代价保留收益。若两个策略同样改善，这是共享调度工程效应。若真实可派机会充足而无净改善，接受null，停止该点，不继续调token/EDF权重或换voice直到赢。

## 5. 当前建议的ROI顺序

1. **完成pilot/resource8的既定闭合与独立审计**，资源结果作为操作边界保留；不在运行中调参数。
2. **优先T1：Fullcall vs Ready-only在剩余6个对该新假设未测试的既有speaker上确认**。已有56次model-active机会、0ready复用、56重派与大worker成本差，问题明确且执行器已就绪；两臂×两repeat=24次，优于不活跃的Vdag再跑全5×8或自动160次新corpus。既有历史声音仍须明确不是新未见corpus。
3. **原作者continuous online/共同resident fast path控制**保留为R1公平性补强，先利用已完成直接开销边界判断实现投入；不能先许诺其改变排序。
4. **受限资源再分配点**仅在完整resource机会门成立且值得16格预算时研究；否则把canonical saturation/优势缩小作为诚实边界。当前不以此增添“新调度算法”paper主张。

新应用中的“何时用额外计算推进同一反馈chain，何时服务其它session”确实是系统组合问题；但合法性证明已由共同输入/AU/SUP条件承担，调度选择仍受已知overload、deadline与公平目标约束。要提升为进一步贡献，需要同资源下可重复的端到端改善及明确的新机制，而不是仅给传统priority规则换一个合法性名字。
