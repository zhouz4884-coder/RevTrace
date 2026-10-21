# 失败、修复与未解决边界

本文件记录科学结果与执行缺陷，不能因最终审计通过而删除早期失败。全量操作日志留本地operations和8TB原日志；公开归档只含有界证据及哈希索引。

| 项目 | 发现 / 处理 | 证据层级及最终地位 |
|---|---|---|
| 旧worker.text无独立绑定 | 只改text而Z/P不变，CPU4/4接受；owner独立Render并比较、WAL绑定及恢复重算 | 确实工程缺口；CPU负控与后续真实GPU逐转移审计，不作自然漏洞prevalence |
| 字符串后缀不具可靠对齐 | LCP/latest-frontier/append无法证明新parent兼容 | 安全拼接NO-GO，不实现；whole hypothesis另有严格兼容前提 |
| 只保留分支或只改view不足 | Factorial中单chain仍回撤，单view等待更长 | 真实GPU负结果，和联合收益并列，不隐藏 |
| 早期LocalAgreement适配错误 | 等待agreement期间会清空已确认文本；CPU最小反例保留 | 旧12个LA GPUcells无效比较；修复全词协议和canonical precedence，同载体54矩阵全部fresh重测 |
| 测试录音warmup隔离 | 旧carrier warmup用首测试片段但输出不进服务状态 | 旧72保留诊断/选负载；最终carrier仅合成零音频warmup，实际workers记录核验 |
| 消费时钟边界 | preliminary用dequeue，最终用view application完成并保留dequeue | 不混合中位数；最终v6与旧载体分别标记 |
| v1–v5 continuity源码 | 多次CPU规范修正后才得到最终v6 | 这些版本没有GPU执行；归档不作GPU证据 |
| probe旧ed9工具冻结 | 后续增加initial/target/future全部重复、实际消费hook及完整输入摘要 | ed9未运行；实际4f工具在首次probe前部署，路径别名final_tools_v4不等于源码版本，真实身份单独核验 |
| tokenizer诊断路径假设错误 | 初次假定tokenizer.json存在失败；实际为vocab.json+merges.txt | 保留诊断失败；读实际库warning规则和资产，不启用fix_mistral_regex或静默改变Φ |
| Safe Async强正控等价 | 完整安全组合得到相同canonical历史及相近性能 | 真实GPU反证，独占/不可组合主张NO-GO，不能降配对手“救”创新 |
| c16未达2s/8s | 匹配机制实验改善回撤及display等待，但仍超SLO | 合法高负载边界，和新池c8/c4通过点分开，不调历史阈值 |
| 新池并非处处零回撤 | 联合连续性sync c8为1/1/1，开发池Fine为0/0/0 | 零回撤不是无条件保证，也不等于无字符修订 |
| R6处理输入差异未改变输出 | 523/524稳定复现，但Z/P各布局全部相同 | 有界负结果，不包装成GPU SDC或质量损害 |
| R5受控F2 | 16有效中2例目标不变；14变者中5例未来未变 | 所有结果保留；不能只选9个传播正例或称自然发生率 |
| 恢复时钟差距 | ledger23–64ms，restart→首次认证消费约31s | 真实服务恢复不是毫秒级；不隐藏模型初始化和输入排空 |
| CPU收尾审计脚本未部署到旧路径 | postflight_v5尝试不存在的PhaseN/audit_phase_n.py，退出前6项新审计已运行 | 执行路径缺陷，不是GPU/机制失败；原log0保留，原审计器原字节部署到PhaseD独立路径，再以v6复算，不改原始结果 |
| 原V0/V1及长时边界 | C2 0/98、C3 0–1/98及时；Whisper截断和历史内存增长 | 原结论保留，没有重启V2/KV fallback或用新语义掩盖 |

任何进一步审计失败必须追加本表；不得将尚未完成的独立审计写成PASS。最终状态由POSTFLIGHT_SUMMARY、FINAL_LOCAL_QA及远端Git核验共同限定，而非此表单独认证。
