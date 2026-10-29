# 新来源服务中的完整自然事件链

冻结 CPU checker `dd2cb7e7816fcfd7d6be5194f8f883c98dba1f78` 已实跑 PASS；完整4文件manifest、bundle、snapshot、机械输入配置、环境、run record、逐输入hash及gate在同family。它遍历全部16格的Consumer和全部fullspec ledger，重建**所有2次frontier回撤、所有2个completed-full discard以及唯一一次Canon保持ahead-private-view**。无远端读取、无模型调用、不修改原分析源码/结果或D2/C8端点。

**唯一兼容保留自然见证：S0905/r1。** Consumer行24→25，认证前沿由4.0秒推进至4.5秒，完整可见前沿始终5.0秒，全文和private job `j000011` 均不变。其旧birth Root为4.0秒（`41941d…`），冻结完整start为4.5秒（`922681…`）；这个start逐字段等于新安装的真实Canon4.5秒，而非仅字符串相同。旧依赖链4.0→预测4.5→预测5.0完整成立，job/物理worker/epoch身份未改。实际新Canon安装发生在该job的model_start与model_end之间，故确是正在运行的工作及其已可见临时结果跨Root被保留。Consumer仍只认证4.5秒，没有将5.0秒预测越权认证；随后5.0秒原C/state/IDs亦与完整原参考相同。

**必要回撤自然见证：同一S0908声学修订模式，在r0/r1两次fresh执行出现。** 两次Consumer行30→31均由可见6.0秒回到5.5秒，认证前沿由5.0秒到5.5秒。父调用 `j000015` 的原学习纠错器在5.5秒选择了不同的尾部token，临时全文尾部“领捷”变为原C选定的“领接”。这里“选定”只描述原模型输出，不宣称该输出就是人工真值或更低CER。真实Canon5.5秒为 `13badc…`，依赖调用 `j000016` 的完整冻结start却为旧预测5.5秒 `87b7da…`；逐字段比较，`tokens`及`transcript`不同，其余完整cut字段相同。

因此旧5.0→预测5.5→预测6.0链已被实际同5.5秒Canon反证。原job/epoch/physical channel均未改；两个完成的j16结果分别被discard，proof精确绑定该job完整start与真实同F Canon，均从未出现于canonical_install，也没有其完整end进入Canon历史。随后真正安装的6.0秒调用使用新的真实5.5秒start，完整原C/state/IDs与原参考一致。这两次是**同一声学模式的两次计时观察**，不是两个独立声学样本。

这三次观察没有发现兼容视图误撤。它们提供真实反馈流程中“相容则保留，不相容则撤回且不安装错误分支”的自然见证，可以将native在途保留与实际整视图消费连接起来。它们不构成新R×S消融、不估计自然发生率，也不扩大为全局保证；R×S必要性及交互证据仍来自核心110格试验。原服务信用、内容支持、全部EOS与质量/能耗数字均保留。

可接入正文的桥接段：

> Natural execution also exercised the consumption boundary. In one S0905 run, Canonical progress advanced from 4.0 to 4.5 s while the Consumer retained its complete 5.0 s provisional view: the surviving call's frozen input equaled the new cut, without changing its job or birth identity. Conversely, one S0908 revision pattern, observed in both fresh runs, changed the 5.5 s cut; the dependent 6.0 s view was withdrawn and its completed result never installed. These are natural witnesses, not another factorial test.
