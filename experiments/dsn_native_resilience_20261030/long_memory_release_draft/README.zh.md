# 未冻结的 long reference generation 生命周期窄修草稿

只在本新目录开发；没有修改source_v1、source_dev或已冻结diagnostic_v1，也没有远端/神经调用。

原作者infer在940行把首轮完整logits视图放到 `generation['logits_starting']=Logits(logits[:,:,:])`，952/959行又将Logits放入progress。已验证的旧stage_packet接口从这些generation_progress.Logits/Tokens/BeamTokens对象读取 `.tokens`；底层storage是否别名/clone必须由本次实际GPU诊断测量，不凭逻辑numel相加猜测。

冻结9492的continuous_transitions在yield时仍保留局部 `g`，下一次infer的右侧先执行，直到返回后才覆写g；因此下一次模型执行可与上一轮诊断Logits的storage重叠。原NativeBridge.step提取C/IDs/完整cut后返回cut/record，不把g返回给serving caller；该栈退出时g已释放。这里定位的是新连续参考wrapper的返回诊断生命周期，不应直接称原ASR算法或serving实现有同样缺陷。

草稿 `continuous_transitions_release_g` 保留相同原insert_audio/infer/export顺序和参数。提取全部选中C、返回IDs、累计text和完整closed cut后，先统计g中的去重CUDA storage：与显式engine/model/保留semantic result共享的storage另列，只返回标量元数据。随后在本generator局部真正 `del g`、sync、记allocated/reserved，再yield。不empty_cache、不缩上下文/beam/dtype、不改原C/U。

CPU控制证明generation weakref在yield暂停时已经释放，且下一原infer时不存活；验证storage别名只计一次、engine/semantic共有存储不算独有、结果report本身不持Tensor，以及 `.tokens` 接口。只有根任务下一次冻结diag并实际GPU运行才能证实allocated下降和95/96边是否越过，当前没有宣称修复成功。

`compare_rows(old,new)` 是纯比较器，完整start/end（含全部contract/source marker）、原C和IDs逐字段严格canonical bytes相等，允许old94对new96公共prefix或重复same-input95对new中同一edge。只排除这些语义对象之外的时间/诊断元数据，不对状态字段作投影。重复控制不是额外声学样本。
