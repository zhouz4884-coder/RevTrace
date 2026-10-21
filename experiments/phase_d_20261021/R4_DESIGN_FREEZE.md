# R3/R4 正式前冻结

真实双3090/FP16+FP32/group_ready、fine2s/rho1或3、256预算、完整音频按时间释放。新16独立LibriSpeech test-clean说话人，每人一个完整16–28s utterance；固定seed哈希序，无识别结果选择。独立于原12源开发池；重复、相同嵌套并发集不作新说话人计数。

先R2两个机制pilot及c4 D1 off/on×3成本控制。正式目标D1不是本地Fake测试；任何pipeline失败留原记录，停止新矩阵。

scout为Coarse-D/D1/snapshot、c2/c4/c8/c12/c16×sync与uniform-stagger，共10cells。stagger固定sid×0.25s均匀间隔，不称Poisson。主SLO2s显示+8s持久提交；显示2/5/8、commit4/8/12/16网格全报。依据真实consumer观测、相同2s和精确末端frontier，所有未完成计入；不只采样事件延迟。

每到达模式选最高双P99通过且未cap的scout负载；若全部未通过取c2。此规则只选靠近临界点的fresh正式工作点，不调阈值，不从scout声称三重复容量通过。正式9策略×两arrival×3repeat=54cells：Fine/Coarse×Barrier/Decoupled-D1 snapshot四组、Coarse Two-lane、Standard Safe Async Two-lane、LocalAgreement2/3、Naive legacy消融。每次repeat逆序平衡policy顺序。canonical engine相同；全history Z/P/父/区间/身份逐同rho核对，不相同则触发条件/批输入归因，不能伪称pure display因果。

WAL/显示/CPU/IO/GPU成本、WER/CER、短录音切分代价、认证修订、temporary invalidation与认证后缀保留分列。LocalAgreement没有可靠audio对齐的稳定prefix不凭空算完整音频覆盖；同时报告字符稳定/延迟，标注相应保守frontier边界。

当前容量结论仅为该完整录音集合、模型/硬件、到达和声明指标下的**所测工作点**。不会声称全天稳定流、所有长度、真实互联网体验或topic极限。
