# 最终完整调用语义保持：对象、转换与证明义务

此文件是新模型的设计/来源映射，尚未报告模型状态数或实际运行通过。它不继承旧1154状态模型的证明身份。独立source_v1将单独冻结；原bdfa源码只读保留。

## 需要区分的对象

* 完整Cut是(F,P)，P为适配器声明的全部跨调用可变状态。符号模型用一个bit代表整个不透明P；相同F的两种P故意具有相同显示文字，因此文本相等不能替代完整状态。
* owned job包含原job、worker、物理incarnation、Owner epoch、birth root、冻结start、target及冻结依赖链。它们在确认、缓冲和重根时不改名、不重签。
* typed ASR identity projection是已执行完整A后的临时状态，不能被标成原C/U已经执行。原C/U完成结果是另一对象，既可能与自己的投影相同，也可能不同。
* 输入资格三态：actual同F完整cut未知为UNKNOWN；已知且相同为CONFIRMED；已知且不同为REFUTED。祖先失配不推出未来完整start已被反证。
* 输入真值、用途和物理权限不同。已确认完整start也可能已被覆盖而没有用途；未终结worker需要真实exit/sync证明才能释放物理槽。
* durable record绑定transition id、原job、原完整start/end、接纳时epoch及其原物理incarnation。已拥有的closed buffer可在worker-only重启后保留原incarnation；新的late消息不能借此取得新权限。

## 与实际代码的直接对应

| 规格动作/检查 | bdfa实际挂点 | 新resilience层需要保持/新增 |
|---|---|---|
| complete input、same F与job binding | FullSpecCoordinator.register/_dependencies；StageCoordinator.bind | 保留冻结对象；单物理worker/incarnation拥有一个未终结任务 |
| UNKNOWN/CONFIRMED/REFUTED | _reason、dependency_support_losses、_canonical_witnesses | 加typed local rejection；不能将祖先失配当C-entry取消原因 |
| ASR投影与原C/U结果分开 | admit_asr；_replace_conditional_node；complete | 原pipeline不变，完成receipt含完整start/end、原C与IDs |
| exact current parent安装 | _commit；pop_ready_commits | durable-before-commit回调在r.install前fsync；每次record唯一引用原call |
| 逐安装view快照 | _commit返回view_event_snapshot | 保留每次自身root的快照，不能批量安装后把最终root套给所有publication |
| 实际Consumer整视图 | StageConsumer.run；Reconciler.install | Supervisor日志保留publication payload及实际application receipt；预测视图不推进认证通道 |
| 旧消息局部拒绝 | bdfa对此多为ValueError | 已知旧epoch/incarnation/重复job局部拒绝，合法工作继续；真正状态破坏停止新写入并恢复 |
| worker-only失效 | bdfa不支持继续服务 | 保留session epoch与已拥有的完整buffer；observe-exit后新incarnation |
| Owner组失效与恢复 | bdfa只有普通日志，无该保证 | Supervisor/ingress/Consumer在故障域外；只重放真实durable prefix，旧epoch未持久化结果不得新安装 |
| 原输入义务/时钟 | fixed offered boundaries/original ORIGIN | Supervisor保持原ORIGIN与持续接受账本；恢复视图不能清除新音频义务 |

模型并非从Python/CUDA机械抽取。它对上述守卫提供可检查的有限交错规格；实际同源实现及日志仍须独立核验。这种来源区分是贡献的一部分，不应把规格模型PASS写成所有实现路径已验证。

## 语义保持命题

前提：完整声明状态足以决定后继输入；保护执行器忠实消费冻结输入并执行原C/U；Owner独占且串行接纳；持久存储兑现fsync；消息来源及incarnation绑定正确；Supervisor保持接受输入及原时钟。原神经程序允许的转移关系可以非确定。

把一条实际协议轨迹中的推测、投影、等待、取消、丢弃、局部旧消息拒绝和既有事实重放作为stuttering删除。每一次新Canonical事实的durable接纳/安装，对应原保护反馈程序允许的一次转移：

1. 引用某个实际原C/U完成调用，非typed预测；
2. 该调用完整冻结输入等于前一实际Canonical cut；
3. 接纳时仍有原job/epoch权限；closed receipt保留原worker身份，不因重启重签；
4. record先完整持久化，再允许安装与认证发布；
5. 以后恢复只重放同一record，不构造新的神经结果。

归纳证明：初始cut为原程序初态。普通推测/取消动作不改变可信前缀。新record的守卫给出输入等于前一事实及真实原C/U输出，因此扩展一条允许的原程序执行边。恢复保留相同durable前缀，重放只造成既有事实重复可见，不增加原程序边。由此每个新事实序列均是原程序允许的执行，不需要假设两个独立GPU重跑逐位相同。

Consumer推论：实际认证前沿只能来自该durable事实前缀。一次没有独立fault-withdrawal的兼容Canonical应用保留现有完整ahead视图；不兼容输入或明确epoch fence可以撤销临时视图。它不保证全会话文字单调，也不证明临时文本是人工正确转录。

继续服务命题仅是条件性进展：预期旧消息拒绝是无状态stuttering；accepted义务与原时钟不变。在最终无新故障、物理exit最终可确认、可用worker最终完成原C/U、Owner与Consumer公平调度时，可从当前真实cut重算下一步并推进。有限模型与命名测试演示这些路径，不提供故障RTO/D2上界或任意无限调度的活性证明。

## 历史回收与证明边界

规格中的dispatch evidence和durable prefix是ghost/归档证据，不声称生产live-RAM常数空间。实际GC需要保留current cut以及active/buffer/Consumer publication引用闭包，不能让seen-job记录被删除后重用旧身份。epoch+单调issue序号+worker incarnation可以用高水位代替永久保存每个job对象。回收是否使峰值状态有界由持续输入实验测量，不新增一个GC算法主张。

## 有限模型与反例控制计划

模型有两个worker、完整状态两值、原C/U两种允许选择。正常profile覆盖两前沿、至多三次发起、12个事件；故障profile覆盖一前沿、至多两次发起、一次Owner或worker故障、12个事件。三前沿/四调用的祖先失配后再次收敛由命名控制显式构造。所有bounds在正式运行前冻结，达到state cap即失败，不把截断状态数冒充穷尽。

命名控制包含：完成先于/晚于确认、未来buffer按真实父顺序、原C改变自身预测、same-text不同完整状态、UNKNOWN误取消反例、投影越权认证反例、快照Consumer反例、publication最终root别名反例、未fsync安装反例、旧epoch重新授权反例、提前复用物理槽反例、原时钟重置反例；另检查局部拒绝后继续、worker-only保留closed buffer及Owner组恢复后新任务继续。

