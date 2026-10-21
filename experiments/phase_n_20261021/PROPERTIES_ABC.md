# A/B/C 定义与实现对应

## A：过时 proposal 不新发布

发布时满足 generation=current 且 target>durable F。旧 parent 单独不构成失败。
被拒的已执行结果记 `proposal-obsolete` 及 job execution duration；未派发覆盖窗口记 `proposal-skip`，二者不可合并为省下的 GPU 计算。

## B：有界 reconciliation

前提：单 owner、每会话至多一个 private in-flight、有限输入窗口、任务最终返回且 owner 公平推进。在接收/下次调度时，覆盖窗口在有限 scan 中退休/跳过，至多扫描本会话剩余 fine windows；下一真实派发沿合法 root 继续。不是无条件 wall-clock liveness，也不推广到多 in-flight。

## C：真实 canonical 快照覆盖

WAL 成功、安装后，每个版本无条件发布实际 transcript 文本及 transaction ID，即使已有更远 private display。恢复从 WAL 的 committed_text 重新发布最新确认快照。canonical_snapshot 独立保存，不被 tentative 内容写入。没有可靠词音对齐，采用版本化完整快照；允许并量化 visible audio frontier 回撤和字符擦除。

| 转移 | 前提/顺序 | 效果 |
|---|---|---|
| 收 private | 检查 generation、target 与 F | 发布 tentative 或显式退休；绝不写 canonical |
| 无 in-flight 调度 | 覆盖窗口存在 | skip 每窗口并前进；无剩余 private 时退出 |
| 准备 canonical | authority 结果 + 当前父/区间谓词 | certificate；仍未给显示端 ACK |
| WAL 成功 | 完整 frame 同步成功 | 安装 state；失败不安装/发布 |
| 安装后 | 不依赖 D_ever 是否已更远 | canonical snapshot + version/transaction；然后 install-ack |
| 相同请求重试/恢复 | 原 journal namespace/contract | 原收据/历史，不加第二次 transition；最新文本可重新公布 |

CPU 用例包括快/慢 proposer、快/慢 authority、Fine/Coarse、Barrier/Decoupled、旧 generation、终端 skip、更远 private display、WAL 失败、恢复与同输入重复。27 个新增 A/B/C/sequence 测试通过（其中 9 个是 token/stop tests）；完整整合为 353 tests，不按声学样本计数。

新旧差异用 legacy 对照直接暴露 obsolete publication；canonical snapshot 测试验证 commit→真实文本显示/事务映射及允许的回撤，不将“修了 if”表述为不可能性定理。正式 GPU 测量由独立 raw audit 再查 A/B/C，而非只相信生产代码计数。

## 最终验证范围

最终独立检查从 Z+parent 重算 Phi/显示文本并对照 WAL，T1 3393、C3-preparation 294、T3 5292、全 hooks calibration 2262 个转移全部通过。这些是重复负载的 transition 记录，不是独立故障、说话人或新恢复试验。

publication 是单 owner 有序 emit 流中的真实文本快照。`display_revision` 是每 owner incarnation 的计数；恢复流有 run-start/state-recovered 上下文并重发最新 canonical text。未实现/未证明跨连接乱序前端合并、网络 exactly-once 或浏览器绘制顺序。历史承认身份的 exactly-once 与显示消息去重不是一条保证。CPU fixture 的真实 host fsync 时钟与 Fake 调度时钟分开，不能混算成本。
