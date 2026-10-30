# 返回generation的生命周期：已知事实、假设与待实测

本说明不修改草稿两份实现文件，不修改9492/runtime/source_dev/diagnostic_v1，不访问远端或调用模型。执行agent正在管理实际诊断窗口。

## 本地源码已经支持的事实

固定原作者 `simul_whisper.py` 940行把完整首轮logits视图交给 `Logits(logits[:,:,:])`；952/959行将Logits加入逐token progress，1138行返回 `new_hypothesis,generation`。旧stage_packet经过65个真实候选的接口只读 `.tokens`；这里不凭未读的Logits构造器宣称它一定clone或一定留在GPU。草稿在实际tensor.device和untyped_storage层面测量，而非按逻辑shape推断显存。

9492 `continuous_transitions` 的 `ids,g=engine.infer(...)` 后提取原C/IDs/cut，再直接yield。Python generator在yield暂停时保留所有局部变量；下次恢复后进入下一轮，新的infer右侧执行完成后才会覆写g。因此“前一次返回的generation仍在下一次原调用期间可达”是具体wrapper生命周期事实。当前CPU weakref控件能够复现这一点并验证del-before-yield确实避免它。

NativeBridge.step是普通函数：它提取selected_correction等语义字段，返回cut/record而不返回整个g。只要C为原接口的普通CPU字典，其余generation诊断对象在函数栈退出时就可释放。完整调用serving路径不应因为新的continuous-reference generator失败，就被未经验证地归为同类显存问题。

## 收到的实际诊断进展，不在本文重跑

execution_continuation报告：默认allocator连续前缀两次都在第95边OOM，两个失败完整输入cut字节相同；同一失败输入通过原NativeBridge路径独立两次执行都成功且结束hash相同。它们区分“这一固定输入必然无法合法执行”与“某条持续caller/allocator历史产生失败”。这还不能单凭相关性断言g就是全部原因。

## release-g96应当检验的最小因果链

1. 原input/precision/beam/cadence/C/U/原模型保持；沿用默认allocator，不empty_cache。
2. 提取所有C/IDs/完整closed cut以后，返回的g没有语义用途再被本generator持有。
3. 统计g中实际CUDA storages，按底层storage去重；同engine/model或保留C共享者扣除。统计器返回值不能保留Tensor引用。
4. del g前后分别同步并记allocated/reserved。caching allocator的reserved不一定下降；不能把reserved不变误判成对象仍存活。
5. 必须实际完成到96边，并严格比较两份旧94公共前缀与两个独立same-input95结果的全部start/end/C/IDs（含source marker），不靠忽略状态字段越过。

若独有CUDA storage很小、allocated没有对应变化或96仍失败，则应保留该阴性，不把CPU weakref通过当成显存原因已证。下一步需针对实际peak/fragmentation/original内部日志再定界，不能改音频、减beam或缩context来维持原任务声明。
