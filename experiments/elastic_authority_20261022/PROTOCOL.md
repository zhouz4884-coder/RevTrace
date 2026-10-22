# DGFT Elastic Authority Granularity — 2026-10-22

正式用户请求：唯一主线 Display Permission Does Not Imply State-Write Permission；保留C1可信准入、C2因果双粒度协调、C3持久恢复，只研究能否实质增强C2。不修改论文/标题/摘要，不重跑C1 E1/R5、Audit A/V0/V1、C3恢复矩阵；不扩展推测解码、GPU恢复、新模型或KV fallback。

Stage1：读取原PDF Theorem1与冻结PhaseD live_qwen/dgft/adaptive_audio_plan、A/B/C/D与WAL Resume；核对最新GitHub PhaseN/D/Opportunity身份。动态rho_k∈{1,2,3}需逐项验证parent/chunk/generation/audio readiness/txn/χ/恢复/质量，不能说原代码直接支持。重算旧T1/R4服务需求、积累与排队，跨实验观察不得冒充同工作负载因果。

Stage2：同一独立完整音频、模型/精度/双3090/预算/资产，固定rho1/2/3，sync、uniform-stagger和同run low→high→low。冻结2s/8s Display/Commit主SLO及完整网格、WER/CER约束、GPU能耗与按相同2s/末端frontier的联合Audio Goodput；未完成不剔除。纯CPU代价仿真只找空间，不拼接不同rho的神经输出或Canonical History。

Stage3 gate：只有真实固定粒度显示明确可利用交叉空间，才实现最小Elastic。只用已释放音频、当前合法parent、实际backlog、历史标定成本、声明deadline；比较Backlog-only、Deadline-only、联合策略和最佳合法固定rho，不用复杂学习器。完整χ声明允许集合/规则/参数；每条动态历史独立Render/准入/WAL/质量/恢复审计。CPU协议先通过，再有界GPU。

成功：在真实非平稳负载下，较最佳固定和简单动态基线有可重复、统计支持的双SLO Goodput/Commit P99或能耗–质量Pareto收益，无新增准入违规。不预设Fine时延+Coarse能耗兼得。没有清晰空间或无强基线优势则算法升级NO-GO，不削弱原DGFT。

所有运行冻结代码/配置/环境/模型和数据身份，保留原始结果、失败和负结果。模型/音频/环境/大日志留8TB盘，只有有界证据归档。先查现有GPU进程不重复启动、不结束其他任务。最终交付机制必要性、算法、形式化义务、质量/成本权衡、强基线及C2升级GO/NO-GO。
