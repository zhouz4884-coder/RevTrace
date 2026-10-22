# Space Gate的数值化规则（读取本轮scout结果前）

此文件把STAGE2_FREEZE的“明确空间”变为可执行判据，不调整已冻结样本、SLO或质量阈值。当前只观察controller完成计数，尚未读取本轮quality/latency结果。

独立审计9个scout后，对low→high→low的相同16源：

1. 首先剔除安全/未完成/触顶错误作为成功候选，但所有前沿仍计入结果与分母。质量合法基线需WER/CER均不高于同集合rho1 +0.5pp。合法不表示其SLO自动通过。
2. Primary空间：最佳合法固定的双SLO Goodput距`total_audio / last_audio_release`绝对上界至少还有5%，且实际高段Authority有服务需求/队列或parent等待压力。上界不用任何模型输出，不能超越到达约束。
3. Commit空间：固定rho1在low段Commit P99比rho3至少低1s，rho3在high段比rho1至少低1s，并且**只混合时间、不混合神经输出**的逐frontier最小提交时间乐观screen，比最佳合法固定Commit P99至少低10%。这个screen不是合法动态Oracle或可实现性能保证，只是值得真实检验的候选空间。
4. 能耗–质量空间：最低GPU能耗固定配置未通过冻结质量约束，而最佳质量合法固定至少贵10%。这只触发有界真实混合策略检验，不假定质量可线性拼接或能够成功。

满足任一候选空间且有可观察的阶段负载变化，才进入最小Elastic；否则判定本资产/门槛下升级NO-GO。没有触发不证明所有动态算法不可能，只表示不为未知的可能性继续堆GPU。若触发，后续formal才判断可重复、统计支持且超过强简单基线；scout乐观screen从不作为最终收益。
