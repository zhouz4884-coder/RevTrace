# RevTrace 2026-10-31：面向服务证据的补强（完整范围与论文v2已完成）

## 最终入口

[最终研究与贡献判断](FINAL_RESEARCH_AND_PAPER_REPORT_20261031.zh.md) · [全范围与论文QA总门](FINAL_ROUND_AND_PAPER_GATE_v2.json) · [新正文PDF](../../Paper_DSN/revisions/20261031_dsn2027_release_v2/main.pdf)

本轮44个真实NN trials、70请求实例、1190原程序状态转换已独立重算。matched32最终Full6/8对Cons0/8；常驻请求Full7/8对0/8。受控buffer2match合法原身份使用/2mismatch拒绝，由新零NNreader验证，原执行审计FAIL不改。额外两client观察probe为NO-GO，不开发新调度器、不扫参。GPU已释放，CURRENT恢复4f。新稿11技术页+1参考文献页、全部12页实际视觉检查完成；旧稿/SHA链保留。会议投稿未执行。

以下为本轮事前选择及已执行的停止规则，不能当作所有项均成功的声明。

承接已完整交付的20261030稿及归档 `f73cecac0178e30387a6e9a9ed86b08f8da8e985`。旧稿、旧run、旧SHA链保持不变。本轮是在新证据驱动下继续研究，不把上轮的完整范围结束冒称全部研究机会穷尽。

## 当前选择

1. **实际后继输入重配对与边界定位**：离线重读已有36格原始dispatch/WAL/worker/Consumer；eventual same-frontier完整输入相同、实际在线确认、物理权限、完成、选中和实际消费分别列出。409/457、333/416只是所选调用自己的预测end与选择不同，不能充当实际派发输入失配率；354/366也暂不采信。原无reset长流阴性不覆盖。
2. **版本配对**：冻结原四来源×bdfa/4f×两策略×两fresh的32格。先执行既定S0908八格阻断smoke，其他来源不按结果替换。FP32、模型、输入、神经warmup、共同allocator/环境/GPU轮换保持一致。除原source指标外，另采共同明确的useful-EOS和physical-drain能量窗口，不把不同终点原数字硬拼。结果分支先写：未见回归如实报告；若有实际开销/回归先定位，只有保持强端到端机会的局部工程修复才考虑。
3. **完成结果跨producer死亡的受控正负控**：使用已知开发来源和固定父边界，真实ASR/full消息完整发送后的timing barrier；Owner已登记完整条件结果后再真实kill其producer。通过原退出/CUDA释放/通道封存/fence后释放父。正控允许原身份结果在输入被确认后安装；负控父输入不同时不得安装。两正两负fresh，不改神经输出、C/U或资格，不将其当自然率。fixture源码和NN4f源码分别冻结/记录。
4. **常驻有端点请求的小型闭环**：四个独立预注册语音请求，每个有真实文件EOS；模型/worker驻留，上一请求实际认证EOS后客户端才发下一请求。每请求原始时钟与输入义务单独记录，不将文件边界称在线VAD，不重置旧未完成义务。核心4f59文件全字节不变；新外层harness与时钟检查独立冻结。先两策略各一次smoke；语义、时钟、切换或端到端机会不成立即NO-GO，不横向改合同凑成功。通过后两fresh共4run。

上述顺序依据问题与证据，不采用“19条引文必须凑到30+”等数量目标。只补支撑实际差异的原始文献。资源准入与资格的区分先进入讨论；是否值得成为新机制取决于有用服务合同与实际干扰证据，不把单会话结果冒称多会话公平性。核心旧Qwen研究已有多会话；当前native36格才是单会话。

## 已取得的免费诊断

原8个Owner恢复格的两个worker `ready.sent_perf`差仅0.389–39.560ms。它不是Owner首次/第二次接收ready的精确时刻，但当前不支持为解除第二个ready屏障改恢复实现。保留现有故障域，不能让旧worker存活来偷换成更弱的Owner-only失效。

## 执行纪律

NN和正式分析均要求冻结config、真实source commit、完整manifest、环境、8TB原结果路径、summary与gate。保留legacy dirty checkout；新开发/冻结源独立。CURRENT由root统一协调，各代码版本与依赖分别核验，不以GitHub归档HEAD替代执行源。真实神经窗口不并行无关大IO/CPU。模型、语音、缓存、大raw只放既有8TB；这里只放代码、计划和有界证据。

本轮最终新release将在实测和独立核验结束后编译/逐页检查/同步GitHub。会议投稿未授权执行。
