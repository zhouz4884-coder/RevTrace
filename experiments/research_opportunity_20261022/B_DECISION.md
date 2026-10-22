# B — Epoch-safe In-flight Authority Adoption

## 分层裁定

**机制可行性与净恢复机会：GO。完整算法/大规模GPU：本轮不执行，建议只申请下一步有限集成。作为独立DSN新算法贡献：尚未确立。**

已经证明的不是“多放宽一个epoch check”，而是：在可信Supervisor与FP32 Worker存活的故障域内，仍属于当前合法父状态的未安装任务可以保留计算来源，由新owner重建逻辑输入、重新发证，并通过原准入/WAL进入认证消费。6个实际收养单元均省去一次fresh Authority调用；另6个WAL已提交单元不需要且没有进行收养。

## CPU负控

34项CPU矩阵通过，含实际WAL和本地FIFO：当前合法旧任务、已提交、WAL提交未发布、parent前进、session/source/音频/χ/runtime/chunk/language失配、worker死亡、来源Supervisor/incarnation失配、派发/结果篡改、重复、新旧结果两顺序竞争、旧owner竞争及原WAL排他锁。

“当前合法输入”与“可信执行来源”分开校验。所有非法项不能新增安装；已提交项返回重放路径，不靠再次接受旧结果恢复。CPU fixture的假token/假renderer不叫GPU证明，真实GPU项另经独立Render/WAL审计。

## GPU有限实验及公平性

主矩阵18单元：3故障点×Cold/Strict/Adoption×2fresh repeat，按repeat反转方法顺序。故障前均为同一1张3090、1个预热FP32 Worker、同一6s音频目标、相同预算/χ。Cold故障后重启Worker；两Warm方法共享存活Worker与同资源，不增加standby卡。所有同输入的fresh生成/收养Z、P、text逐项一致。

另4单元先真实生成并持久化0–6s非空父状态，再计算6–12s；Warm Strict/Adoption各2重复。新纪元从实际ledger恢复的P与固定音频/manifest独立重建的全部逻辑字段一致。

下表RTO从真实SIGKILL前开始，到新本地FIFO消费者**完成认证view应用**；不是server emit、网络、浏览器或完整多会话服务RTO。每格n=2，中位数仅描述这两个观测，不外推P99。

| 故障点 | Cold(s) | Warm Strict(s) | Warm Adoption(s) | 收养的净解释 |
|---|---:|---:|---:|---|
| Authority运行中 | 16.914 | 1.946 | 1.014 | 保留剩余约0.95–1.03s旧GPU计算，避免Strict之后另做一次生成 |
| 已完成、未安装 | 16.837 | 1.238 | 0.272 | 旧结果来源可达且输入仍合法，避免一次约1s重新生成 |
| WAL持久、未发布 | 0.615 | 0.299 | 0.286 | 无需收养；三者直接恢复认证快照，Cold也不强制先载模型 |
| 非空父、已完成未安装 | 未追加冷组 | 1.430 | 0.284 | 真实P/版本非零仍可合法重新授权；不是只对genesis成立 |

Warm→Adoption的净差约0.932s（运行中）、0.966s（完成未提交）、1.146s（非空父完成）。Cold→Warm节省主要来自Worker驻留与模型不重载，不能算为收养的新算法收益。

主矩阵中ledger打开/重放/**追加新epoch并同步**约8–45ms；它不是纯内存重放时钟。恢复阶段新GPU派发：前两个故障点Strict需额外一次、Adoption不需；WAL点三者都为零。GPU峰值约9.4GB，原始逐cell显存和模型初始化时钟保留。冷组运行中被中止的旧GPU剩余量是删失未知，未拿其他运行补成实测。

22个成功故障单元共32个目标派发，其中30个目标调用完成、2个冷组运行中被中止；非空父另有4次实际seed生成。单独保留初版失败pilot，不计入成功中位数。每个campaign内相同目标的完整Z/P/text Oracle一致，原WAL无重复准入，认证文本来源重新Render相符。

## 成本与不能声称的收益

本原型真实payload约4,033 pickle bytes／5,271 JSON bytes，单pending记录样本5,726 JSON bytes（不是Python RSS上界）。Linux CPU真实payload Pipe基准3×2×1000次：relay RTT中位约0.150ms，加深复制/双摘要后的receipt约0.395ms，配对增量中位约0.246ms；单纯guard约12–14μs。它们不是生产服务overhead、CPU能耗或P99承诺。

GPU能耗来自最终原始采样的独立积分。实时字段因线程最终样本晚到而有9项修正，原值保留。短窗口样本覆盖最低约81%；使用`B_INDEPENDENT_CELLS.csv`中的覆盖率和sample-supported energy，不用原live字段作精确总能耗/节能倍数主张。没有用补跑挑更好能耗。

## 相关工作与新颖性风险

结果证明“这项工作可合法复用、并能改善本故障点关键路径”，没有证明普通任务服务/结果跟踪无法实现它。RIFL的结果去重/重试定位、Ray的任务/actor容错、RobustRL的角色存活/重连都必须正面处理。Warm Strict是保守安全政策，**不是所有最强常规系统的代表**。

后续若继续，应先把同Supervisor+规范请求ID+完整输入谓词的普通结果跟踪组合设为正控；不要为了拉开差距去掉它的合法缓存。若与Adoption等价，则贡献应界定为RevTrace特化的安全恢复策略、规格与实证，而不是独立算法突破。

## 允许申请的下一步，不自动执行

只建议有限集成：多会话当前父判定、持久可审计的来源收据、旧/新任务真实交错竞争、worker失败退回冷路径、ACK/GC/背压，以及Linux无故障正常路径回归。必须在保留强普通任务组合的前提下验证。没有理由直接展开大规模GPU或重写摘要/论文；新颖性差异仍不足时，应把B作为恢复工程增强，而非继续命名包装。
