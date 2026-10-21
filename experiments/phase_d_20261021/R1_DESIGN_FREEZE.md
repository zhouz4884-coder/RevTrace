# R1 冻结设计

目的：固定rho、音频、worker与预算时，单独改变**authority结果交付**是否改变认证滞后和回撤。不能预设单调性或风暴。

正式矩阵：Fine/Coarse × authority post-completion delivery hold {0,0.75,1.5}s ×3fresh repeats，共18cells。固定12source/16slots开发池、sync、microbatch16、2s、FP16/FP32、256token、group_ready WAL、lazy A/B/C D0。源码从已发布runtime复制，仅新增authority delay CLI；所有实际model-call时钟保持原值，不把hold写成计算时间。

同rho完整normalized canonical Z/P/父/区间/身份历史必须匹配；若batch时序导致实际内容不同，降级为调度干预的联合效应，不称仅lag因果。固定次数和分段；同时报告private lead、到达lag、rollback/commit、depth/area、文本和队列。3repeats不是新声学来源。保留全18cell，无按结果选单元。

CPU publisher replay对同一真实发布流比较D0、two-lane-invalidated、canonical-only、LocalAgreement2/3和fixed wait；不改变canonical decisions，不当GPU性能。

R1 gate：只有在同内容、同rho下干预呈稳定的lag/覆盖关联才保留有条件机制叙述；否则为该adapter/工作负载下现象，不命名普遍retraction storm。R2可独立修补确证的text-binding gap，即使因果假设NO-GO。
