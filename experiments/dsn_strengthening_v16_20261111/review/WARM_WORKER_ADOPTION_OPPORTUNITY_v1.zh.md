# Owner-only故障下常驻worker与合法旧调用接纳：机会评估

2026-11-11。只读冻结`14ae77ee2f1f0c324be3f40b89fb6011972c35b9`及既有恢复证据；没有实施、启动实验、改CURRENT或干扰主pilot。本文是后续机会评估，不改变RR pilot与loader study的优先级。

**判断：同两worker常驻的Owner-only恢复有明显共享工程机会；旧调用合法adoption的增量尚不足以开启新研究实现分支。** 去掉约70–88秒重新构造权重的收益主要来自缩小故障域与worker常驻，两策略都应获得。真正有待证明的是在**同样warm containment**下，接纳旧调用相对丢弃旧调用还能减少多少真实新fact/债务恢复时间与双板能耗。当前数据只支持保留这个条件性候选，不支持把persistent workers换名为新算法或RevTrace独占加速。

## 1. 为什么不是改一个kill就可以

当前`resilience_owner.py:27–31`由Owner创建worker、命令/结果/hint Pipe和接收线程；`resilience_transport.py:39–46,70–75`端点跟Owner存亡相连。Owner消失后，worker在command/hint接收处可遇EOF，或向消失的结果端发送失败；简单不killpg不能保证它继续常驻和输出不丢。`resilience_trial.py:31–43,85–101`本来定义整个Owner+worker组退出/CUDA释放后冷恢复。

而`resilience_inbound.py:133–140`明确拒绝jobID中旧Owner epoch，且新Owner没有旧active/terminal registry。直接放宽这个比较会让未登记旧消息取得权限；重写旧jobID/epoch则破坏原调用身份。需要把通道/worker lease和issued registry移到幸存Supervisor或独立可信broker，Owner只持独占writer lease。保护模型和GPU数仍为原两份FP32副本。

## 2. 两种身份和一次新的使用授权

| 对象 | 必须保持的内容 |
|---|---|
| 计算身份/物理lease | Supervisor boot namespace、slot/incarnation、单调issue serial、原jobID及birth Owner epoch、原session epoch、source与完整冻结start/input key/target/EOS、原模型合同；跨Owner不改名、不重签结果 |
| writer authority | 独占新Owner writer epoch；原Owner实际失效且WAL writer已fence后才授予。writer epoch变化不自动取消仍存在的计算，也不自动认可其结果 |
| adopt capability | 可信registry已在派发前记录该调用；绑定原compute ID/完整result receipt SHA、当前session、恢复WAL tail的sequence/SHA与完整parent、当前writer epoch、一次性cap ID。每次append前重验证，parent变化后旧cap无效；UNKNOWN输入只挂起，REFUTED/covered不授予使用权 |

同输入比对仍不能代替原完整C/U结果。可信worker执行与通道完整性是前提，不是GPU算术attestation；这里不新增Byzantine模型或要求签名基础设施。

旧Owner的private/canonical publication始终按旧publication namespace拒绝。新Owner只能基于broker登记的原调用证据重新做AU/SUP并产生**自己的新publication**；它不是把旧Owner publication换epoch重发。可先把范围限于完整原结果adoption：在飞计算继续占原lease至完成，才可进入接纳；不把旧早期投影直接升级为事实。

## 3. 必须维持的归纳项与失败路径

1. **单writer。** 新Owner取得权限之前，旧writer确已停止；不能仅发新epoch就允许两个文件writer并行。Owner+workers全丢仍走原冷恢复，不把Owner-only结果套上去。
2. **compute→fact唯一消费。** 由原登记调用、原完整结果、恢复后的实际parent建立新合法边；新writer与原birth Owner可以不同，但原计算身份不变。若WAL已包含该compute ID，它只可replay，不得再次append。
3. **sync/install gap不消失。** crash可能发生在fsync成功、registry尚未收到selected ACK之间。恢复先读WAL并调和registry，不能因ACK丢失再授予第二次adopt cap；现有transition ID含writer epoch，单独按它去重不够，需跨writer的selected compute-ID约束。
4. **物理lease独立。** 至多两份实际执行；旧任务未terminal/未观察退出不能把slot再派给新Owner。晚帧不得释放另一incarnation的任务；新Owner不能同时adopt旧任务又在同slot发duplicate。
5. **视图与债务独立。** 幸存Consumer继续原SUP；replay旧fact不是新神经结果；原ingress/origin与accepted debt保持。授权失败/不确定则冻结writer或安全丢弃后重算，deadline不能放宽输入或cap守卫。

这会改变现有形式模型`Record.authorized_epoch==job.epoch`与actual-trace checker中job namespace=writer epoch的映射，必须显式增加compute/writer/cap关系。不能简单删除原epoch断言却继续引用aa9db5的35控件为新协议证明。

## 4. registry必须真有界

仅“两worker”不界定全部registry：active最多2个，但已有完整ready bank、conditional后继、inbox帧和Consumer引用仍可能存在。现有32k lookahead/8k步长允许多级后继；不能把它们假定成最多一条旧调用。

必须预先冻结 active/ready/inbox entry cap、总字节cap、单message/cut上限、活跃session上限、adoption等待/用途界，并保留dispatch高水位与已selected compute-ID的压缩去重证据。Supervisor记录不能按累计历史无限增长。当前64项recent-history、32MiB wire、16MiB WAL frame只是局部上限，不自动给新registry完整RAM界。容量到限时拒绝新登记/安全回退并计入服务结果，不通过删身份或重用serial保住进度。

## 5. 公平比较与真实增量的大小

正确比较是`warm-worker/drop-old-jobs`与`warm-worker/adopt-eligible-old-jobs`，两者同Supervisor/broker、同两块GPU、同常驻权重、同Owner-only故障点、同输入时钟与recovery检查。drop臂应立即利用已经空闲的worker从恢复parent重算；不能人为等两个旧任务都drain才派发，也不能只给adopt臂预热。旧任务丢弃/安全早停规则需预先一致定义，不能藏掉其残余占用。原Owner+workers冷故障另列。

旧after-durable格在ready后首新认证仅0.678–0.740秒，首原infer0.582–0.632秒；约100秒主要是共同加载。若仅剩一条直接可用旧调用且另一worker可立即重算，adoption通常只领先不超过一次此类原调用及host调度差，**不能预写十几/几十秒增益**。0.6秒仍可能跨过D2边界，但须实际落在原offered/Consumer关键路径，不能把前缀工作秒求和作延迟收益。

这不是全局“≤1 call”定理：多条完整ready链、长原C、恢复期间的积压或原root未定时的后续收敛可放大机会。旧92个晋升正常job、22–24个累计确认前job-seconds并不证明Owner故障时存在这些候选；旧ready reuse=0也不等于新warm布局永远为0。需要在后续同输入故障ledger中实际数清：故障时两lease状态、未入WAL完整bank、可接纳同parent候选、仍UNKNOWN/REFUTED、空闲worker最早重算完成点及真实first-new/debt关键路径。

## 6. 工程与研究取舍

原完整cut/receipt、实际parent检查、WAL replay和dead-worker closed-buffer经验可复用，所以**可做，但非窄loader修补**。主要工作是broker生命周期/完整帧归属、writer fencing、adopt cap与ACK丢失恢复、跨writer去重、byte-bounded registry，以及新trace/形式映射。粗略为2–4个工程日的最小实现，再加2–3日控制/独立审查与测量；不是交付承诺，失败域扩大时更长。

**当前不启动该分支。** 先完成既定baseline与loader study。若loader修复后Owner-only冷初始化仍明显主导，可将两worker常驻作为两臂共同的恢复工程改进；若进一步的相同warm对照显示重复出现、可实际使用的多结果/长调用窗口，并带来值得保留的原债务/截止/能耗净改善，才进入cap-adoption实现。若仅偶发小于一调用且被broker/Owner开销吞没，保留安全设计与负机会结论即可，不升为新的算法贡献。
