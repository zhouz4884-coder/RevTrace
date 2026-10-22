# B：有界GPU可行性预冻结

只验证单个合法FP32 Authority操作和一次coordinator-only故障；不是完整服务或生产容量。原Phase D Worker、DGFT准入、WAL、Trusted Render、FIFO消费者原字节复用。Supervisor单独拥有mp.Queue/Worker与不可变任务注册，新的Coordinator只拿fresh Pipe，不能恢复旧Queue句柄。

每组故障前同样1张3090、1个预热FP32 worker、同一6秒完整音频前缀、相同χ/预算、同一个pending target。三组预算相同，不预留额外standby GPU。Cold在故障后重启worker；两种Warm共享相同worker存活策略，仅是否可收养旧结果不同。**Cold→Warm属于worker驻留收益，Warm Strict→Warm Adoption才是收养的净收益**。WAL持久后，Cold也必须先恢复并发布快照，不强迫等待无需使用的模型初始化。

三个故障点：model-started后真实SIGKILL coordinator；GPU完成但未安装；WAL成功且未发布。固定两个fresh repeat，每repeat逆转三方法次序，18个故障单元。相同原始输入/χ/target下所有fresh生成与收养输出逐token/stop/P/text比较作合法oracle；不因失败调样或改变预算。

Supervisor只保存原任务、来源worker incarnation和结果的不可变副本及摘要；不是GPU远程attestation。仅本机可信监督器/worker存活、存储完整/单owner、固定manifest/χ范围。来源registry消失、worker死亡、过期parent、已提交、错误音频/χ等全部fail-closed，不向strict模式偷偷提供收养。

恢复时钟从SIGKILL调用前perf_counter开始；分别报检测/启动、WAL重放、GPU剩余、模型初始化、首次认证view应用完成及全程序排空。cold被中止的剩余GPU工作是删失未知，不拿其他运行推测值冒充实测。GPU功率按原始采样插值积分，主机能耗未测。正常成本单独报告序列化/registry/IPC CPU测量，不将fixture均值称生产尾延迟。

CPU32项初始矩阵通过后才允许此有限原型。任一来源/准入/Oracle失败，停止矩阵并保存STOP；只有CPU/仪表缺陷可修复后留前后版本再跑。完成本矩阵不自动授权完整算法或大规模GPU实验。
