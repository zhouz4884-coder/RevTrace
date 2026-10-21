# D-Recovery：补足实际consumer链的最小GPU故障控制

预注册3次coarse/c2/D1/two-lane/group_ready，在真实WAL同步、安装后、canonical publication前SIGKILL自建进程组。标记虽沿用旧CLI名ACK_FOR_KILL，实际不是显示ACK或consumer已观察；必须明示这个故障边界。

恢复保持相同输入/contract/源码/WAL，允许新output路径；新的FIFO消费流先重发已恢复认证快照，再继续剩余输入。独立检查此前WAL字节前缀存活、每个恢复快照被实际consumer观察、text与Render和WAL选择匹配、无第二次安装身份。恢复账本时间、model init、整个进程重启墙钟分开。

仅process crash；不覆盖主机/存储失效、浏览器、网络exactly-once或跨连接消息合并。该补充与已冻结容量矩阵不混算SLO或吞吐；它回答的是新增D1/消费端恢复，不把旧21次kills冒充新D1证据。
