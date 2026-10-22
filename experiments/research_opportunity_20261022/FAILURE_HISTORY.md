# 失败、修正与证据边界

| 事件 | 保留记录与处理 | 科学影响 |
|---|---|---|
| 未认证GitHub API403限流 | INTAKE记录，改只读git ls-remote+原始manifest读取，未要求新认证 | 主分支和268文件已核验，不是仓库不存在 |
| A初版AutoProcessor未先注册Qwen | A_CONTROLLER.log；CPU导入修复，v2/v3独立脚本保留 | 无GPU调用，不改tokenizer/adapter，不把失败当机会0的证据 |
| B首个cold-running试验消费schema缺time | B_gpu/STOP.json及WAL/功率保留；增加fresh/recovered真实FIFO CPU回归，后续v2从全新目录完整重测18 | 属原型事件协议缺陷；失败试验不混入正式中位数，未修改原Worker/准入/WAL |
| 正常路径先验成本只计guard不含IPC | 单独Linux真实payload Pipe CPU基准3×2×1000补测 | 12–14微秒guard不冒充完整开销；增量receipt中位约0.246ms只是CPU fixture |
| 实时能耗积分早于采样线程最终join | 独立复算发现9个live字段与最终原始采样积分不同，差值逐cell保留 | 不改原result；最终CSV用原始样本重积分，报告覆盖率。短窗口最小约81%，不做精确总能耗/能效提升主张 |
| 独立审计v1要求live能耗相等而失败 | 保留本地operations输出；v2明确重算和边界，而非修改原结果去通过 | 准入/来源/消费时钟检查不因此跳过 |
| 附加逻辑重建审计v3变量sf遮蔽soundfile | v4只修审计变量，所有22个实际WAL+manifest输入逐字段重建通过 | CPU审计器缺陷，不重启GPU，也不把尚未通过的v3称成功 |
| 初始有界archive早于附加重建核验 | 最终BOUNDED_EVIDENCE_v2和RAW_EVIDENCE_INDEX_v2显式替代初版 | 初版保留、不当最终证明；全部原始测量不变 |
| 真实SIGKILL后mp资源追踪warning | 完整controller日志保留；最终无本任务GPU进程 | 未证明无POSIX semaphore泄漏；完整系统须做故障后资源清理与长期压力，不声称生产完成 |
| A未找到根等价/重算机会 | 148观测/12唯一对均不满足条件，Whisper截断路径未在资产中启用 | NO-GO，不实现DAG Grafting |
| WAL已提交点没有收养收益 | 三组均直接重放发布；Cold不强迫加载不需要的模型 | 保留零收益对照，不拿旧CLI31秒作刻意弱基线 |
| 条件收养的源记录仅Supervisor存活内存 | 坐实本轮fault model，只覆盖Coordinator丢失 | Supervisor/Worker/主机死亡、可信执行被破坏均不支持；CPU worker-dead负控fail-closed |

本轮未修改论文、既有基线或原始测量来获得漂亮数字；没有预设成功RTO。小样本2repeat不是尾延迟分布、自然故障率或生产可靠性证明。
