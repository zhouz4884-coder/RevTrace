# Ledger时钟术语补正：保留低成本新检查机会

2026-11-11，依据独立审阅 `../review/LEDGER_v2_INDEPENDENT_REVIEW.zh.md`。此为报告勘误，不修改817ebbb冻结source、config、原始数据或PASS结果。

实际bdfa boundary的顺序是：原 `before_corrector()` → capture/project/serialize → `produced_perf` → on_asr/emit → sent_perf → Queue.put → 原学习C调用。因而 produced_perf不是“发送完成”，也不是精确C入场。旧record没有Queue.put返回或真正C函数入口时钟。

两个j16的父infer结束晚于child produced_perf，仅能严格排除：**不移动原有检查点，只加快相同proof/hint传递**便能赶上原检查点。它不排除在publication之后、真正C调用之前增加新的非阻塞重检。这个位置的可用窗口和实际proof是否已到达，需要单独测量，不能从旧trace保证成功或宣告失败。

该候选比C中途取消或主动等待更小，可以先加精确时间/控制验证；仍需新的source版本与真实原任务/服务对照，未测不能宣称已修复两条discard。

24条abandon的原infer timer仍为NA（缺测），不是0：ASR前缀确已执行，只有学习C未执行。69.017全调用构成、22.429–24.487确认前worker区间界及23.779固定时长重启proxy均不受本术语补正影响；最后一项仍不是因果延迟节省。
