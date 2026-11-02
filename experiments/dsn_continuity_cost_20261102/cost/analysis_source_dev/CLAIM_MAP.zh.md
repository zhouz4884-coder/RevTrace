# 成本证据与论文主张：执行前边界

本表尚无校准或NN16聚合数值，不把CPU12单个格子的微短函数读数当业务费用。

| 证据账 | 能回答 | 可在正文使用的表述 | 不能推出 |
|---|---|---|---|
| 原3cf null-target calibration | 当前计时器clock bracketing及RAM观测的分辨率/成本量级 | 原meter的thread/process CPU外括号包含额外clock reads；所有实际footprint不扣校准floor | 精确测出某个2微秒guard的无偏业务CPU；CPU-wall是lock wait；统一减一个常数修复全部标签 |
| CPU12完整真实FactStore/Consumer replay | 原17步真实完整cut/C/IDs/fact、整view对象及实际fsync走当前路径支付多少观察到的host成本 | 原durable文件逐字节与Consumer语义重建成立，按来源/策略/三fresh分列coarse操作足迹 | 真实流式服务延迟、完整Owner调度成本、部署吞吐、冷文件系统、总协议净开销 |
| 独立完整输入/identity probes | 真实对象上的完整状态物化/比较与原owned-call binding当前函数行为 | 另列为真实对象component probes，接近floor只保留observed account | 把原job全集context当原时刻liveOwner占用；与完整FactStore/Consumer或NN费用相加 |
| 正常NN16 on-path spans | 未改原安全谓词的完整当前Owner/Consumer/WAL实际调用分布 | 主表选FactStore commit、whole Consumer apply及真实fsync，inclusive分开；同线程exclusive另列 | 将inclusive父子累加、跨进程wall当总服务wall、将exclusive当消除了meter后的真CPU |
| 同来源/策略/repeat共8off/on pairs | 打开计时/捕获后，原任务及真正服务端点有何变化 | 全部pairs给原D2/C8/EOS、信用、原完整selected任务、调用/消费数和共同drain能量；称total observation impact | 裸无安全检查是合法基线；off/on差即协议保护净开销；小样本未显著即无开销 |
| 原program digest与a13/c4 | 原选择、输入/输出/C/IDs与合法性分别有什么证据 | a13固定原任务/actual Consumer检查与另冻c4完整来源/依赖检查分别引用 | 用runtime或reference PASS扩大成零非法安装；将new cost trials自动加进旧3976分母 |
| 真实origin→confirmed physical model drain功率 | 同一原窗口内两张物理板的实测能量 | 复算总/每板J并保留原SERVICE_END及Ownerexport；drain是外部观测上界 | CPU/PSU总系统能耗，结束时刻是瞬时硬件时钟，把Ownerexport从真实端点偷偷减去 |

这批实验重用S0908/S0916两个已测来源。它不是新的独立泛化确认。Conservative/Fullcall在实际执行与调度上不同，二者差不能命名为纯guard税。若off/on完整selected任务或物理工作量变化，保留并先解释；不丢pair、不把CPU重放时延用于修正真实NN。

可填数后的英文句式：

> We replay complete recorded objects through the current FactStore and whole-view Consumer, with their original synchronization enabled. We report their observed, unsubtracted costs separately from standalone input/binding probes. A null-target calibration exposes the clock-bracketing floor for very short functions. Eight paired normal-service comparisons then quantify the total effect of enabling observation under the same selected task and original deadlines. These measurements characterize the current path and its measurement cost; they do not remove the protocol or estimate a counterfactual protection tax.

主文优先保留一个coarse足迹小表与off/on端点范围，完整family/raw/null曲线放artifact。不能在NN16与正式校准尚未齐全时填入“几微秒”“可忽略”“零开销”。
