# R1：固定选择历史下的交付时序干预

18 个正式真实 GPU 单元全部完成。Fine/Coarse × authority完成后交付hold0/0.75/1.5s ×3重复，保持同一source、rho、worker/预算。12个同repeat的hold-versus-zero对照，完整canonical Z/P/父/音频/身份内容历史均相同，且全部增加回撤率。

| rho | hold(s) | 三次回撤数 | 回撤/发布 中位数 | withdrawn area 中位数(s²) |
|---|---:|---|---:|---:|
| 1 | 0 | 77/72/77 | 27.599% | 278.152 |
| 1 | 0.75 | 158/142/145 | 51.971% | 1237.433 |
| 1 | 1.5 | 173/173/173 | 62.007% | 2493.835 |
| 3 | 0 | 1/2/2 | 2.041% | 1.952 |
| 3 | 0.75 | 34/34/50 | 34.694% | 171.896 |
| 3 | 1.5 | 66/66/66 | 67.347% | 243.823 |

**GO（有条件的因果发现）**：在固定rho和选择内容历史的本D0完整快照策略下，认证结果交付变晚可以通过增加相对private领先与版本覆盖而增加可见音频回撤。

**不支持**：不能把rho之间的差异归为单独认证频率；不能称普遍retraction storm、自然故障率、稳态利用率或纯状态锁瓶颈；不能把full snapshot本身判为错误。hold也改变未来排队/批机会，数据识别的是该时序干预的系统总效应，不是对每个中介因子的独立因果份额。

回撤深度、逐source/session/语言、累计音频秒、恢复删失及时间积分来自R0/R1逐事件CSV。Fine每run279、Coarse98次canonical机会；16slots来自12源，非16独立说话人。3repeat不是新声学样本。字符擦除代理与语义错误不同。

源：R1_SOURCE_IDENTITY.json；远端R1_gpu全量trace/WAL/model-clock；R1_audit/R1_CELLS.csv、R1_PAIRS.csv。原GPU计算时间未重写，hold是人工post-completion干预。最终完整审计还将复核物理frame/power和早先冻结数据。
