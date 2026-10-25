# N5 SIGKILL 开发恢复：已记录前缀审计，独立验证组尚待门槛

权威复算为 N5_RECOVERY_INDEPENDENT_AUDIT_v3.json（v2保留但时钟不同，不能
作为正常服务口径）。WAL独立谓词重放为N5_RECOVERY_CANONICAL_WAL_REPLAY_v1。
真实GPU源码408d756，控制器v2 SHA11fdc252...fa436，开发旧8来源，每方法1次。

两次均在原始episode14s之后首次观测Authority Batch派发时，对身份核验的
本任务进程组SIGKILL；两张卡Worker均冷重启，不是Coordinator-only存活收养。
派发边界不一定等于正在执行模型内部算子，不能升级为特定算子故障。
首次v1控制器因驱动释放记录短暂延迟而停止的失败另存，不删、不混入成功数。

|项目|Fine+公平限流|CDE完整反馈|
|---|---:|---:|
|崩溃前逻辑输入ACK数|49|53|
|记录中已确认音频丢失|0 samples|0 samples|
|最终认证覆盖/提供音频|100%|100%|
|唯一Canonical transitions（跨两纪元）|87|33|
|崩溃前已耐久transitions|45|14|
|已付出派发Batch / 有Drain记录Batch|43 / 41|29 / 27|
|无完成收据的已派发行|6|3|
|Canonical账本恢复|19.50 ms|17.27 ms|
|kill→全部旧认证前沿实际Consumer应用|31.053 s|30.886 s|
|重启进程launch→相同实际Consumer点|30.498 s|30.363 s|
|原始到达→实际Consumer/模型排空|55.238 s|52.856 s|
|提供音频全分母Goodput(2s/8s)|1.629|1.589|
|Display / Commit P99|32.940 / 33.025 s|34.986 / 38.192 s|
|整轮双P99达标|否|否|
|GPU J/提供音频秒，含废弃工作及冷加载|70.039|61.448|
|WER errors/reference words|10/413|11/413|

两次各87个提供音频前沿全部进入分母。输入账本完整前缀保留，原始origin、
音频、配置和原始期限保持不变；新纪元未将旧Private覆盖改标为新认证覆盖。
已记录视图无根不兼容/陈旧新鲜化/假CERTIFIED-ONLY，无未经授权Canonical
安装。独立核对了实际Worker完整Token/Stop/P、角色、输入、重启后Parent与
WAL唯一身份，及物理Batch-drained前不能再次复用Worker。

### 这些数字不意味着什么

没有网络客户端ACK测量。这里是服务器同步后输入逻辑ACK，以及真实本地
FIFO Consumer应用；不是外部浏览器、任意网络客户端或断电测试。受信Owner/
Authority与完好可用存储、不可变音频均为前提。崩溃后没有返回收据的GPU行
已由功耗窗口计费，但不臆造其未知最终Z。恢复审计以已写出的观测前缀为准；
本轮未发现诊断尾行被撕裂，也不把flush日志称为磁盘掉电耐久日志。

Fine与CDE认证粒度不同，WER相差1个词，单次能量差不能成为等质量优势或
统计结论。两次Cold RTO基本同量级，不能由17ms账本重放推断服务恢复17ms。
正确的传统输入/WAL/视图控制同样可实现这些语义，应作为强正控。

### 审计自身的修正（原始GPU结果未变）

1. 初稿检查器错误假设序列化DualAxis Certificate有contract_epoch字段。
   实际Epoch围栏来自冻结Job/Row注册和WAL restart chain，而非不存在的
   证书字段。已按实际字段核对选择证据、Parent、Z/P与执行合同。
2. v2把进程结束后的约5.4–5.5s富日志/清理计入primary服务结束，而正常组
   primary以实际Consumer/模型Drain为界。v3统一primary边界，仍保留完整
   原始资源生命周期和功耗采样，不把清理成本删掉或称其不存在。
3. 控制器Windows测试曾假设os.killpg存在；仅修改CPU测试替身，未改变Linux
   信号逻辑。3项Windows+3项Linux资源归属回归通过；Runtime238项亦通过。

### 下一道门槛

记录前缀与Canonical WAL门槛通过，但实际tokenizer/processor资产CPU重放
尚未执行（避免与105单元正式GPU服务争用CPU）。正式故障21组不能仅凭
当前报告自动启动，需资产门槛和完整独立GO_SAFETY_ONLY记录。正式正常组
的105单元已按冻结协议运行；任何异常停止而非悄悄重试。
