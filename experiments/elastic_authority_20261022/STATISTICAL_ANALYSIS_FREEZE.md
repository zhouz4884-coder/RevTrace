# Formal统计判定细化（未读取formal结果表前）

主点估计为4个完整run的指标算术均值，另报中位数及全部重复。按相同repeat和speaker/source配对；seed20261022、10,000次两层条件bootstrap（4run及32source分别有放回，保留方法间配对）。Goodput用抽样source的合法双期限音频秒/该已观测run的真实全局wall，不能模拟重排后的新延迟。此为条件于现有contended traces的区间，不是新workload性能复现。

质量用逐源真实错误/参考单位的micro WER/CER。Joint相对fixed1的95%上界须≤+0.5pp，触顶或未完成不能掩盖。固定和简单比较者用点质量约束筛选；不借其区间不确定性排除强对手。比较“最佳固定”和“最佳简单”分别在每次bootstrap内重新取max Goodput，避免只选弱对手。全部历史独立验证，不要求同终态。

Primary：Joint均值Goodput较两类最强合法基线均≥5%，两类配对95%下界均>0，并且相对各类点最强者的4个repeat差值全正。

Secondary Commit：Joint均值Commit P99较两类最小时延基线均≤0.90，配对95%改善下界>0；Goodput相对各类最强Goodput的95%下界≥−2%。不能通过降低显示进展换Commit而不计代价。

Secondary Energy：严格共同窗口GPU J/audio-s较两类最低能耗合法者均≤0.90，run-only bootstrap改善下界>0；Goodput非劣2%，相应Display/Commit P99均不恶化2%，质量通过。能耗不分摊到source，不能捏造逐源GPU能耗CI；功率窗口覆盖率须≥99.5%。

三项按primary→commit→energy顺序判定并全部披露，不把任何scout混入formal重复，不调整已冻结门槛。若全部失败，C2 Elastic算法升级NO-GO，保留原DGFT以及ρ=2新权衡证据。该细化不是新增成功标准选择自由度，也不把有限源池区间当普适最优性证明。
