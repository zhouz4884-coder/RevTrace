# R2′：对真实祖先链缺口的有界验证

CPU回放发现Fine two-lane降低回撤却0次保留兼容超前假设，P99反而恶化。原始Fine r0的77次回撤中75次存在同边界private P与canonical P相同，但当前tip往往已经rebase到另一generation，不能据字符串/状态边界相等直接拼接。

仓库**已有**`retain_verified_private_prefix`开关，不能当作新发明。新版本补上完整已完成节点和在途不可变输入的因果链核验，再允许保留whole provisional分支的root。仍不认证未来内容、不拼接字符串、不改Z/P或GPU KV策略。边界P不等、generation不等、链断、inflight输入不匹配时退回原rebase。Canonical engine不变。

在已公开开发池的同c16/sync上：Fine/Coarse×retention off/on×snapshot/two-lane×3repeat=24cells。全新v2代码两臂相同，分别归因于调度分支保留和消费策略，不与旧表拼接。另在R4已选工作点两arrivals×3repeat=6个independent-pool Coarse迁移单元；与原D1矩阵比较注明代码/clock变化，只作迁移而非完全同代码因果。

每个eligible witness独立重建state-edge和冻结pending job；同rho完整canonical历史须一致。保留次数、回撤深度/面积、连续覆盖、时限/质量/成本全报。即使结果差也不扩参数网格。Standard Safe Async可承载同等规则，不能据此声称传统机制无法组合或独占该收益。

若无实质连续覆盖收益，机制性能主张NO-GO；仍交付可信文本绑定和正确消费边界。该补充在查看R4正式结果前冻结，只因真实CPU/trace反例触发。
