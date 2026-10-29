# 真实交接等价门结果

四个原来源的全部69个输入步骤已完成。执行源 `99e83a466fee7f1d16830b640cc99e0040d2f147`，冻结计划 `a93e27fe5ffb9a7343077867a7386c020480699a2695aa6d9cc285a104f3b92a`，Linux正式CPU控制75/75通过且无skip。

65个实际保护域ASR packet与相同完整输入下原full路径的语义候选相同；在Authority上真正恢复open状态并运行原C/U后，完整C选择、返回ID、全文和闭合feedback cut全部相同。其余4步是原encoder前的early路径，完整fallback保留。固定2秒输入的同输入tail重复也相同。open阶段早显投影和从packet解码得到的投影，都等于原private identity full-step的实际ID/全文/feedback结果；投影没有执行learned C，与完整调用完成是不同证据。

其中 **13个预测end与实际原C所选end不同的案例，当前ASR packet仍然合法可用**。这是已实际执行的阶段交接等价证据，说明“撤回预测输出”和“丢弃同次ASR计算”可以分开。它不是ready-only在线命中率，也不是服务加速或D2/C8成功。

主gate为 `PASS_FOUR_SOURCE_PROTECTED_PACKET_ORIGINAL_C_U_EQUIVALENCE`，B盘 `results/revtrace/dsn_streamcorrect_stage_handoff_20261029/equivalence_v2/GATE.json`，SHA256 `41221280007d94581a640ec329bf5634ccb6012efbc44ab60fca302c51c6849d`。本地EQ_RESULTS_v2收集8文件、1,701,805字节，逐项与远端SHA一致。完整wire packets保留B盘。

独立旧任务保真门另外比较所有69步，只明确移除新加入的 `contract.stage_execution` 绑定，其余开始/结束状态、C、返回ID、文字和音频缓冲严格相同。原始cut hash因此0/69相同，不能称原hash相等。该门由独立源码 `64ba03e56aaee752bd962f123a125750e34ad71e` 执行，gate SHA256 `79f9355a41f42660fb16c3f002b3052551a547dbe6dafd89cdb0a0205c8d1411`，详见OLD_FIDELITY_RESULTS_v1.zh.md。

首版wire仍显式携带缓冲音频及open snapshot：65个包中位885,131字节，均值851,110字节，范围198,173–1,515,401字节。实际序列化、队列完整接收、校验和恢复成本必须在服务中测量，不能用旧profiling的9ms snapshot直接替代IPC。保护域、完整输入和原C/U提供条件性授权；重复/跨卡等价是实测控制，不是任意GPU历史普遍唯一的证明。

c7首版失败被原样保留在EQ_FAILURE_v1。原因是Python3.12在完整module与裁剪class的编译上下文中对module全局调用采用不同bytecode编码，旧身份guard使用了错误的参考code。v2改为编译整个固定作者module、取code但不执行module，保留全部原hash/class/co_code/co_flags检查。没有改模型、候选、C/U、输出或数据来源。

当前服务实验数量仍为0。下一步只在独立source_v3开发ready-only controller，强基线为两full副本、相同ASR阶段早显、两个真实C模型都完成固定neural-ready warmup；正式服务范围需另审另冻。
