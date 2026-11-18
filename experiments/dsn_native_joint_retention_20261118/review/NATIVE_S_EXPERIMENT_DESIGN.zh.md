# 原生S消融：最小可证伪设计

2026-11-18，只读设计审阅。已读三份用户提供的审稿意见、当前v22响应记录及冻结NNde0936源。本文没有改论文或旧源，也没有运行GPU。Root负责新源实现、冻结、环境、实际运行和结果门。

## 1. 值得做，但建议中的两个名字必须分清

当前原生R对照已经共用完整输入、原C/U选择、持久化、物理身份和实际Consumer路径检查。新的S消融应关闭**在canonical应用时保留兼容已显示整视图的策略**，不能关闭检查输入/完整依赖路径的安全机制。

`baseline_source_v3/resilience_consumer.py:10`把实际Consumer的每个`Reconciler`固定为`retain=True`；配置的`arm=ready_only/fullcall`只选择计算保留策略。修改ready-only那一组开关并不能变成R1S0。

最小实现是在`SurvivorConsumer`新增布尔`retain_supported_view=True`参数，由`resilience_trial.py`的初始owner-ready路径从冻结config传入。S1保持True，S0为False。现有`feedback_contract.Reconciler.install`已经在同一完整输入/contract检查下支持两种行为：先计算same-F完整cut相容性，再根据retain决定保留未覆盖suffix或清空。

不要把Owner内部`policy.owners[sid].retain`也设为False：其steps同时驱动条件调用起点、冻结依赖和原调用保留，这样会把R也改掉。新S参数应作用于实际Consumer，Owner仍维护同一工作/依赖状态。

## 2. 有一个需要预先接受的真实边界

`resilience_owner.py:53–55`在canonical publication之后紧接着发布该次安装自己的`view_event_snapshot`。所以实际Consumer S0可在canonical应用时清除ahead，然后很快由下一条合法private publication恢复。这不是S0失效，也不该人为延迟后续消息来制造秒级gap。它可能使S0产生稳定但短的fsync/消息间隙，第一期限信用近似不变。

记录真实撤回次数、被撤音频和缺失积分，才能知道其可靠性代价；不能预定原生消融一定复现core的2.176秒案例。

## 3. 建议四臂及顺序

| 臂 | 原调用保留策略 | 实际Consumer视图保留 |
|---|---|---|
| R0S0 | Ready-only | snapshot，兼容ahead也在canonical应用时清除 |
| R0S1 | Ready-only | compatible-whole-view retain |
| R1S0 | Fullcall | snapshot |
| R1S1 | Fullcall | compatible-whole-view retain |

保持相同完整原程序、准入/选择/路径检查、2个完整FP32 worker、canonical-first RR、500ms前沿、ahead限制、D2/C8、EOS和全部offered分母。四臂用新冻结源和同一环境同期运行；不能把旧S1结果与新S0直接拼成因果2×2。

只跑R1S0增加一个S消融，不会使原有两臂自动成为完整2×2。R0S0同样需要实际执行。

已有完整24格OP审计给出良好的预先机会线索：Fullcall四次非空compatible-ahead实际应用全来自S0901，两repeat各2次；S0769为0。Ready-only合计5次。可先冻结这两源×四臂×两fresh=16格，用S0901作已知机会源、S0769作零机会对照；若运行/语义/计量门通过，继续预先冻结的全部8源，共64格（pilot计入总数）。不要因为某臂没赢删格、选择重跑或更改输入。

一个高价值附加锚点是同期Conservative(S1)×8源×2fresh的16格；这样总80格同时处理“只有Ready-only对照”的质疑。无需Conservative的S0重复，因为旧pilot没有compatible-ahead机会。最终规模由Root根据第一格包含两worker加载的实际壁钟决定，不能只用服务的约20秒估计。

## 4. 三类门与指标

**任务安全门**保持完整原输入、原状态/C/IDs参考比对、事实持久化/序列、actualConsumer权限与完整依赖路径、epoch/incarnation、终态守恒和物理释放。S0的有意兼容撤回是结果，不应被硬编码“必须0撤回”的旧检查器当作非法安装。若独立actual-trace checker重建Consumer，应明确声明S0/S1模式。

**激活计量**在实际Consumer canonical应用前捕获当前完整路径与非空tip，保留`install`返回的compatible/ahead、前后visible frontier/text身份。区分相容、同边界完整反证、不完整/未知和无ahead；缺边界证据不自动叫necessary。原Owner model-active确认/派发与Consumer兼容ahead是不同机会，分别报。

**主结果**报告原A2,8、offered P99、whole-run通过、avoidable/necessary/unknown withdrawal、removed audio-s、total gap和avoidable gap、文字I/D/S/字符暴露、worker时间、两板origin→真实drain能量。保持startup/reference另账，缺infer timer为NA；每格`dispatch=install+abandoned+discarded`闭合。Gap按实际撤回至部分/完整恢复分段积分，尾部缺观察报删失。

所有fresh repeats为运行重复，不增加独立speaker数。先看机会与机制是否实际被激活，再解释效应；没有显著第一信用差不等于连续性消融没有作用。

## 5. 三种可接受结果与结论

- S0有相容ahead清除、S1保留：得到同一原生系统里S的直接连续性证据；收益大小由实际缺失积分说明，不借core秒级gap。
- S0/S1信用接近但S0有短gap：S作用于持续可用性，R作用于在飞计算收益，两者分工闭合；不宣传S贡献额外53pp。
- 两源/八源均无S机会：记录未激活与实际机会数，不能用空结果证明S冗余；保留core直接作用与native运行条件，停止盲增同类重复。

当前用户的“所有native数字都是R贡献”可更精确理解为：R对照是在共同S1安全/消费路径下估计的条件性策略差，不能独立估出S。新的完整四臂正好回答这个缺口。

## 6. 对旧数据与审稿建议的取舍

旧NN4f Conservative56.000/137.864125与新NNde Ready58.500/137.864125同源同分母，但改变了runtime/controller；2.500s不是已识别的缓存增益。旧Conservative95.26kJ对同批Full90.28kJ是有效的旧配对锚点，足以说明该实现不只是相对Ready节能；仍不能据此给当前三臂建立同期性能天花板。

三份审稿的基线中间策略（保留ASR阶段）值得在既有stage-handoff材料里查证，不能把旧ASR-only producer或不同模型预算的prototype直接升级同预算强基线。本轮最清楚的新因果证据仍是原生R×S，避免在同一轮同时改ASR内部执行边界。

没有采纳“冷恢复完全由PCIe带宽决定”“四会话自动零开销”等没有隔离测量支撑的判断。它们不是本轮GPU实验应当靠措辞维护的主张。
