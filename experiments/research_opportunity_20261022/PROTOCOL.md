# RevTrace Research Opportunity Audit — 2026-10-22

用户请求的本轮边界：只确定值得实施的新增算法机制，不改论文，不改变强基线以获得好看结果，不预先搭建完整新系统。

正式起点：GitHub `experiments/phase_d_20261021/`（归档87520c085f34797ac2f33b03354268b576ebc408，测量runtime2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8）；核对最新远端、AGENTS、源码字节与N/D全部GO/NO-GO。不启动V2/KV fallback。

## A — Realization-equivalent Recovery

只读实际Exact-P失败的private branch，区分同边界根输入等价、确定性adapter重解释与须真实模型重执行的一步收敛。Qwen rollback5并非删除所有差异；包含decode/encode规范化、Unicode回退、实际batch realization。Whisper历史截断须读实际实现和实际消费记录。旧Z在CPU新父下重解释不是新父生成。

统计真实机会、现存后代深度、现有机制真正会重算的工作、非重复计数的GPU批次和关键路径上界。没有实际收益空间则NO-GO，不实现DAG Grafting。

## B — Epoch-safe In-flight Authority Adoption（优先）

逐源码审计coordinator/executor/worker队列/WAL/epoch/job/certificate。原mp.Queue无独立重连入口；先证明可实现的最小Supervisor/IPC存活路径。监督器拥有worker队列、immutable dispatch registry和result来源；仅coordinator进程故障，不外推主机/监督器/worker故障恢复。

新纪元从已持久ledger+固定manifest+音频/χ重建下一合法job，来源可信性另查，不能仅放宽epoch。所有收养由新owner重新发证，通过原准入/WAL/可信Render。CPU负控含当前合法父、已提交、旧父、音频/χ/session失配、worker死亡、重复、竞争。非法fail-closed后才运行有界真实GPU原型。

GPU仅可行性：Cold Restart、Warm+Strict Epoch Fencing、Warm+Conditional Adoption；公平共享warm生命周期/资源预算，cold额外初始化单列而非冒充adoption收益。故障点运行中、完成未提交、WAL持久未发布。记录剩余实际GPU工作、ledger恢复、首次合法认证消费、重复计算、显存、功率积分及正常路径额外操作成本。结果不预设RTO/加速。

每run冻结源码/config/环境/ID/原始索引、同输入重复和合法oracle；先CPU、后有界GPU，不做大矩阵。真实GPU启动前查身份/资源/模型资产，无重复启动，不动他人GPU进程。8TB盘存环境/模型/音频/大日志。只归档有界已审计证据。

最终交付源码级可行性、反例矩阵、真实机会计数、正常成本、同契约公平基线、正式发表相关工作差异、两路线GO/NO-GO。只有新增合法复用且恢复关键路径实测改善才建议进入完整实现/大规模实验；本轮不自动越过该门槛。
