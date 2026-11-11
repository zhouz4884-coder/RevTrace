# C1技术备忘录：从动作守卫建立选择安全（对应Q6–Q9）

2026-11-11；两页量级方法备忘录，不改稿、不运行新检查、不改CURRENT。实现锚点 **R**=`baseline_source_v2`，完整冻结commit `14ae77ee2f1f0c324be3f40b89fb6011972c35b9`；规格锚点 **F**=`formal_source_dev`，冻结commit `aa9db5c2396b76d9b50f5281fa4a68b54aca844a`。二者目录均在本实验根下。后续v3预期只改共同scheduler；本文不假定尚未审完的diff自动继承此论证。

## 第一页：C1的逻辑对象与动作归纳（Q6）

**C1应表述为三个用途不同的逻辑判定，不能声称三套独立数据结构或全局最小完整条件。** 同一个完整cut witness可以共享、缓存或在引用结束后回收：

| 判定 | 对象与成立条件 | 允许什么；不能替代什么 |
|---|---|---|
| EL | job的完整冻结输入；同frontier实际完整cut尚未知为UNKNOWN，相等为CONFIRMED，不等为REFUTED | 保留/缓冲已发起工作，或基于真实反证早停；UNKNOWN不是false。确认输入不认可该job自己的预测输出，也不直接写selected state |
| AU | 原call真实完整结果，且其完整start等于串行选择时实际installed parent，原身份/权限仍有效 | 允许原C/U结果进入WAL；ASR投影、相同文字、worker存活或“EL曾成立”都不能单独代替原完整结果与append前parent检查 |
| SUP | Consumer当前整view在此次实际canonical应用下的完整支持路径 | 决定保留/必要撤销该view；部分节点或另一个job输入成立不足以支持整view，provisional publication不得取得认证前沿 |

safe UIR仍保留使用前完整输入检查和AU/SUP，只禁发cooperative early-stop hint；因此EL分类、是否早停、是否允许最终使用是不同决策。UIR同效不能推出AU/完整输入验证冗余。

**对象与显式前提。** 令原程序允许关系为 `P —A,X→ P′`，可非确定；X是已接受的不可变输入。每个job保存原完整start、target、job/Owner epoch/session epoch/physical incarnation及完整结果receipt。可信原worker忠实执行冻结输入和原C/U（含声明的buffer-only路径）；Owner独占串行接纳，绑定的通道/身份与完整状态声明可信；存储兑现成功同步，支持的故障域为Owner+workers fail-stop、幸存Supervisor/ingress/Consumer及完好文件系统。**这些不是GPU算术认证，也不抵御Byzantine/被攻破worker或掉电/持久损坏。**

令 `D=(d1…dn)` 为已经完整验证的可恢复fact前缀，`P0`是genesis、`Pi=di.end`；成功同步是正常append的接纳点。未返回的IO结果不硬判成功/失败：live writer冻结，由恢复逐帧校验实际完整prefix。令Owner安装位置为k，Consumer已应用位置为c。归纳项：

1. **I_edge**：每个`di`绑定一个未重命名、已拥有的完整原call；`di.start=P(i−1)`，`di.end`为该call真实原结果；distinct新fact不得重复消费同一原job。这里是要由动作建立的结论，不当作“每个新fact本来合法”的前提。
2. **I_prefix**：Owner installed cut=`Pk`且`0≤k≤n`；Consumer canonical应用也只能是D的无缺口前缀`Pc`，二者不必同时等于tail。成功sync→install之间允许`k=n−1`；crash可保持此gap。恢复重建既有D，replay不构造新C/U。buffer-only fact不自动增加neural覆盖信用。
3. **I_binding/support**：冻结输入/原身份、物理lease及接受输入原时钟保持；provisional与certified通道分开；每次Consumer应用分别检验SUP。

**由守卫到归纳结论，而非由结论重述结论：**

| 动作 | 建立/保持项及实际代码守卫 |
|---|---|
| Dispatch / ASR / Receive | 不扩D。`R/fullspec_policy.py:111–124,172–185`固定输入/target并校验完整start/end/原C路径；`resilience_policy.py:134–148,221–260`绑定Owner serial、物理通道/incarnation及terminal。投影与完整结果分开；UNKNOWN未来结果只buffer。由可信执行前提得到“该receipt是这一冻结调用的原结果”，尚未得到selected资格 |
| Prepare / Sync | **关键步。** `resilience_policy.py:150–179`在append前比较完整start与当前真实parent/session epoch；同一串行调用内`resilience_storage.py:71–81`再与WAL roots比较并验原record/C/IDs。由旧I_edge的tail和这两个当前parent守卫，推出新record.start=`Pn`；由原receipt绑定推出其end是`A`允许后继。因此本步建立一条新合法边。`:82–99`完整写循环+flush/fsync后才返回绑定receipt；hook异常/不确定性冻结新写入，不因deadline继续 |
| Install / Publish | `resilience_policy.py:175–185`回调后再验parent未变，才调用原install；失败冻结。`fullspec_policy.py:146–166`每次提交保留自己的root/view snapshot。它将k推进到已同步fact，**不再增加一条D边** |
| Consumer Apply | `resilience_consumer.py:26–42`独立验WAL frame/sequence/source/parent/原record后才install；`:48–76`验Owner namespace、FIFO、整条view路径；`feedback_contract.py:55–65`实际reconcile suffix。由旧I_prefix和无gap receipt建立新Consumer前缀；compatible-and-ahead分支保存整view，非兼容可以必要撤销；private分支不改processed认证信用 |
| Reject / Crash / Recover | 已知重复/旧域局部拒绝为stuttering；`resilience_policy.py:274–332`仅在匹配terminal/实际exit后复用lease。`resilience_trial.py:85–101`先确认原组exit/CUDA释放，再校验并replay原WAL；`resilience_storage.py:51–70`逐frame恢复。D只保留已验证原边，Owner从原tail重建，重放既有ID不增加神经转移 |

初态genesis满足不变量；上述动作逐步保持，故删除投影、等待、拒绝、取消和重复delivery后的distinct selected facts构成A允许执行。这是条件性的一般归纳论证；忠实执行/状态声明等前提仍然显式，不能由host receipt推出GPU算术正确。

## 第二页：可执行反例、有限检查与实现对应（Q7–Q9）

**已有最小构造/单点变异见证**（不是全局最小充分条件证明；外围守卫仍可能拦住最终坏提交）：

| 被错误替代/遗漏的检查 | 已有可执行named control与所示后果 |
|---|---|
| 完整cut被文字替代；UNKNOWN被祖先失配当false | `F/test_model.py:52 test_same_frontier_mismatch_refutes_not_text_equality`；`:58 test_unknown_future_input_survives_ancestor_loss_then_converges`：后者的误取消损害合法进展，不是自动造成非法selected fact |
| typed投影冒充原C/U；尚未确认parent先prepare | `:85 test_original_projection_cannot_be_promoted_as_C_U`；`:92 test_mutation_unconfirmed_prepare_has_counterexample`。分别缺原完整执行和prepared阶段不变量；后续Sync仍有独立防线 |
| 未sync便install；旧epoch重授予权限 | `:180 test_illegal_install_before_sync_has_counterexample`；`:185 test_old_epoch_complete_cannot_be_reauthorized_under_identical_root` |
| compatible整view被snapshot清掉；多提交复用最终root | `:103 test_snapshot_consumer_mutation_is_observably_false`；`:125 test_final_root_alias_mutation_breaks_first_commit_snapshot`：违反SUP/逐应用绑定，不等同于原C/U被改算 |
| lease提前复用；恢复偷偷生成/改变fact | `:143 test_worker_exit_must_be_observed_before_slot_reuse`；`F/test_invariants.py:41 test_non_append_completion_cannot_create_a_fact`、`:52 test_recovery_cannot_add_an_extra_existing_job_result` |
| hook异常仍继续；直接绕AU使用结果 | `R/test_resilience_policy.py:109 test_hook_failure_freezes_writes_without_advancing_Canon`；`R/test_uir_policy.py:78 test_safe_uir_direct_AU_rejects_wrong_actual_parent_even_without_C_skip`，`:86 unsafe_UseAll…`仅是绕过正常AU/WAL路径的CPU fault model，不是safe UIR在线行为 |

**Q7：实际规格与分母。** F是手写Python frozen dataclass+显式动作，`deque` BFS对完整状态去重，无显式对称约简；bit抽象的是完整不透明状态的相等/不等，原C/U为两种允许选择，不是固定GPU replay oracle。状态/动作不变量检查不同于LTL或无限活性证明。既有35个unittest是原27个合法场景/故意变异控制加8个phase/action控制，既非35个独立故障类，也非35个定理。本memo没有执行新formal check。

既有同边界结果：正常2frontier/3issued/depth12/无fault为6,231 states、11,142 edges；故障1frontier/2issued/depth12/≤1fault为14,074 states、25,799 edges。两profile各有2,144/2,828个depth截断状态，未触150,000cap；只能说生成的界内可达状态/启用边全部检查，未知无限可达总数，不能给无限全状态覆盖率。35控件/36,941边不能升级为whole Python/CUDA证明。

**Q8：三种关键交错逐项回答。**

* 成功append后、Owner install前crash：**明确有**。`F/model.py:231–252,301–317`分离Sync/Install/Crash/Recover；`F/test_model.py:163 test_post_sync_preinstall_recovery_replays_old_fact_not_new_work`及既有`F/test_invariants.py:15–26`合法gap控制覆盖。错误式`installed=durable tail`在正常sync相位就为假，正确是verified durable **prefix**。
* SUP通过后、真实渲染前Consumer自身crash：**当前故障模型排除**；实际Consumer在Owner故障域外，模型没有render transaction或物理像素ack。不能以Owner恢复或逻辑Consumer receipt代替这个保证。
* 同批EL确认而SUP失败：逻辑上不矛盾——某job.start可恰等于新C，而Consumer旧whole view仍来自另一条不兼容链；或已确认输入的job其预测后继被原C/U改写。两判定应独立处理。已有`:33 test_confirmed_input_does_not_require_own_prediction_correct`与`:108 test_incompatible_application_withdraws_needed_view`展示分离；**没有把它们冒称一个新执行的同批原子交错控制**。模型以顺序动作交错表达，不以“batch”这个词抹掉接收/安装/应用顺序。

**Q9：人工映射存在，精化缺口仍在。** 上述动作→R守卫→F不变量/变异表就是可审计人工对应；另有独立actual-trace checker按原dispatch/completion/WAL/publication/Consumer receipt重建绑定，它验证结构与来源，仍不认证神经算术。F的`recover`显式清provisional steps，R的`SurvivorConsumer.begin_owner:13–15`保留既有read view：**当前有限模型并未机械覆盖幸存Consumer保留视图的全部恢复SUP路径**。`R/test_resilience_consumer.py:158,167`已有保留read view与未消费fact重放CPU controls，属于不同证据层；不能据此消除该refinement gap。

因此可保留C1作为用途分解、守卫建立与有界反例支持的合同；不称三套证据必须物理独立、不称全局最小协议、不把safe UIR对照当删除AU的实验，也不让“never”越过声明故障域与条件证明。
