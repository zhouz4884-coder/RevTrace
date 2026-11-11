# LA2适配器独立审查记录 v1

本记录汇总首次CPU运行前已发送的静态问题，以及执行后对修复源/有界控制日志的只读核对。**不是独立重跑，也不是新的模型、服务或原始银行分析。** 本次未编辑冻结源、执行测试/重放、读取音频或改变CURRENT。

审查身份：

* 初版 `external_rule_source_v1`，commit `a105e33d7dd8349a86d46cf427f9de0fadcc899d`：保持immutable，**未执行**。
* 修复版 `external_rule_source_v2`，commit `7e53cd6cc4089b8e9d7fd525679ed93f5f20c569`：本次核对`support.py`、`shadow_replay.py`、相关controls及已完成的`external_rule_ops/RESULTS_V2/{CONTROLS.log,SUMMARY.json,GATE.json}`。

## 两个前置问题与v2修复

**1. 同frontier完整状态被refute，不得当作普通covered继续证明LA前缀。** v1 `WholeView.rebase`先判断`end.frontier≤new.frontier`，导致same-F但完整cut不相同被归为covered；`prior_update`的covered分支又没有清除`la.previous`。旧ASR样本可在失去支撑后继续参与下一次共同前缀确认。

v2已在covered判断之前检查same-F完整end不等并返回refuted；covered prior也同步清除`prior_update`与`la.previous`；refuted触发canonical基准重置并清相应proof。控制`test_27_refuted_same_frontier_cannot_be_LA_sample_one`明确构造`AB@F8→实际A@F8→ABX@F16`，检查旧尾部不能作为有效样本一偷渡。静态修复与该有限见证对应，未通过重写旧job或epoch取得权限。

**2. 固定0.5s滞后不能暗中让每个canonical立即绕过。** v1的`pick`无条件加入当前canonical，故实际上只delay provisional，与原合同的非终局整view滞后不符。

v2对lag控制改为：已到达的immutable canonical history与当前受支持private候选都按received+0.5成熟，fallback为genesis；可保留更早已送达的committed视图。只有最终**实际C/U到达**才执行另行声明的terminal flush。`test_28_fixed_lag_delays_nonterminal_canonical_too`覆盖非终局canonical不提前显示及终局实际文本释放。其它规则保留自己的canonical行为，不把它们混写成通用wait-k。

**静态结论：上述两项有意义的must-fix已在v2解决；未发现新的必须阻止这一次限定离线实验的概念缺陷。** 新增的piecewise within-D覆盖积分与右删失上下界也明确按实际轨迹积分，没有将未观察尾部外推为覆盖。

## 因果与SUP边界核对

* 新音频agreement单位为严格递增的实际visible frontier，并检查该frontier对应ingress已接受。一次跨多个前沿只是一条实际假设；同F的ASR/full-C、重复或较旧F不构成第二次更新。即使不计更新，canonical仍立即触发完整状态SUP重验。
* 候选只在实际Consumer观察时加入pool；定时器不会早于candidate received，canonical时对pool/proof重定位。正文级文字相等不能替代full-cut boundary一致。旁路终局不读取未来C/U或worker已完成但Consumer尚未收到的结果。
* 自由Unicode共同前缀单独输出，不凭字符比例制造audio frontier。用于audio信用的对象必须是已到达、当前有完整支持路径的真实whole view；无法映射部分只保留文本指标。这里的保守映射是明确的适配选择，不是词时间戳版LA2输出等价。
* EOS只在实际最终原C/U到达后terminal release，单独计数，不算第二次agreement。原processed/certified G按实际canonical事件保持，各规则对照原C时刻；不是EOS修复，也不是原selected task变更。

## 完成证据与解释限度

只读控制日志记录28 tests、0 skip、OK，包含原作者HypothesisBuffer/finish的受限AST控件和新增27/28；SUMMARY/GATE记录24格、4规则、96行全部保留，actual-SUP行/信用恒等、原G不变、最终实际文本一致、`new_model_calls=0`与`neural_imports=[]`。这些是**已有正式CPU运行的记录**；本审查没有再次执行它们，也没有独立重算其性能数值。

适用对象仍是既有PILOT24固定计算/候选日程之上的离线阅读策略。所有观察器共同保留原任务、计算保留及必要SUP条件；LA2-CP使用Unicode code point并作whole-view保守映射。它提供已发表决策规则的适配参照，**不是整个WhisperStreaming、SSBD或Retire复现，不是替换原AlignAtt ASR，也不是在线吞吐/能耗/SLO因果实验**。

原Consumer ACK会影响Owner pin/GC，换线上阅读策略可能改变未来候选与物理成本。本轮不发ACK/Owner/GC命令，所以“固定日程无干预”成立于该离线估计量，不能提升为线上noninterference定理。低修改、覆盖、延迟或未映射文本均须共同报告；不得把agreement或相同终局文字当作人工正确性、体验收益或全局连续性保证。

publication可将本记录与v1未执行身份、v2完整source/controls/run/input/gate/资源闭合一并归档；不要用v1名字替换v2实际执行commit。当前已完成结果的解释范围无需再加新用户许可或追加测试数量。
