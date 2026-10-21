# 强基线及来源纪律

LocalAgreement正式出版来源：Macháček, Dabre, Bojar, *Turning Whisper into Real-Time Transcription System*, IJCNLP-AACL 2023 System Demonstrations, pp17–24, DOI10.18653/v1/2023.ijcnlp-demo.3，官方页 https://aclanthology.org/2023.ijcnlp-demo.3/ 。作者代码 https://github.com/ufal/whisper_streaming/blob/main/whisper_online.py 。已核对n次连续更新共同前缀原则；非arXiv-only依据。

本轮LocalAgreement2/3为**credited display-policy adaptation**：同一受保护canonical engine上比较连续临时hypothesis稳定前缀，canonical correction到来重置稳定缓存并保留真实修订；不改authority状态。原系统使用词时间戳/音频buffer trimming，本adapter没有该对齐，因此不能把稳定文字前缀映射到整个音频前沿，不称作作者native Whisper-Streaming复现或原论文性能对比。

Standard Safe Async为独立常规策略适配器：过时完成退休、有限schedule的bisect跳过、版本快照优先。共享GPU executor、commit/WAL和D1 renderer，非外部原生系统；与RevTrace相同规则时应被识别为等价，而不是藏掉正控。已有GPU工作不可物理取消，逻辑退休与省下GPU工作分开。

Naive FIFO/Latest-wins只作缺失保护的消融；不代表工业async。Sync Barrier为合法保守基线。所有同rho方法要求逐transitions检查canonical Z/P历史，若不等须标出batch/context差异并降级比较。
