# operator_v1 原始 GPU 证据的独立复算

日期：2026-10-28。范围：固定输入、模型驻留的真实 Qwen 执行器实验。**没有开展新推理，也没有将它解释为线上服务结果。**

## 方法与来源

通过已批准的 SSH/SFTP helper 只读取 8 TB 盘上的完整 `operator_v1` 目录，取回 46 个文件，共 **9,690,945 字节**。每个文件下载后再次读取远端原始字节，核对 SHA256，并确认大小和修改时间没有变化。索引见 [RAW_INDEX.json](RAW_INDEX.json)。

独立脚本 [recount_operator.py](recount_operator.py) 仅使用 Python 标准库，不导入原实验 gate、worker 或调度策略。它直接读取逐次 RESULT、逐次事件、worker 原始封条、预提交 job 快照、冻结输入和 power 样本。冻结 config/environment 哈希一致；实际执行 commit 为 `c9c2469ba2ca38db5b7d9a3f1a7ea35052e57d68`，本地对应的 **238 个源文件全部字节匹配**。

## 独立得到的实际结果

每项有两次配对重复；模型阶段是实际 worker 的同步前后时钟差。

| 固定输入 | no_cancel 模型阶段，秒 | covered 模型阶段，秒 | 配对减少，秒 | 每次真实取消行数 |
|---|---:|---:|---:|---:|
| cap256-standard-staggered-r0 | 16.544827 / 16.470024 | 1.630027 / 1.676745 | **14.914801 / 14.793279** | 2 / 2 |
| medium37-standard-sync-r0 | 3.157831 / 3.127069 | 1.728585 / 1.940549 | **1.429246 / 1.186520** | 1 / 1 |
| clean14-fine-sync-r0 | 1.813027 / 1.784680 | 1.800677 / 1.805998 | +0.012350 / −0.021318 | 0 / 0 |

完整数字见 [RECOUNT.json](RECOUNT.json)、[PAIRED_EFFECTS.csv](PAIRED_EFFECTS.csv) 和 [TRIALS.csv](TRIALS.csv)。双板功耗按原始采样独立做分段线性积分，与每次实验记录一致；它包含另一块板的空闲功耗，不是逐行推理能耗或 FLOPs。

## 证明了什么

- **12 次正式 generation 批次、184 个物理行、178 个完整 worker 封条、6 个取消封条、12 个真实 BatchDrained。** 终态互斥且覆盖全部实际提交行；完整／取消清单、worker incarnation、batch、job、输入身份与 drain 全部相符。
- **184 个行输入记录**均与同次对照、跨重复对照及历史 processed tensor 身份一致，包括取消行保留下来的实际输入审计。
- **178 个完整行**的 chosen tokens、feedback state、文本、EOS／长度终止结果，全部与同次 no_cancel、另一重复及历史期望一致。存活的 F2 原始执行输出也与同次对照一致。
- 检查的是输入张量哈希和离散输出的重复性；没有保留全部 logits／激活，不能声称所有浮点中间值逐位相等，也不能外推到任意批布局。

## 必须继续收费的取消尾部

取消请求与取消确认都没有释放 worker。6 个实际取消的 request→ack 为 **0.013955–0.737471 秒**；取消终态 emitted→同步模型返回为 **0.000738–0.951919 秒**；emitted→worker BatchDrained 为 **0.024489–0.975674 秒**。这些时间全部保留在整批模型阶段／lease 账本中，未按行相加制造节约。

cap 批最早的零延迟请求仍分别等待 **0.737471 / 0.722817 秒**才确认，因为取消需要到实际 decode 安全点。这里没有 CUDA kernel 任意时刻可抢占、独立行立即释放容量或确定反应上界的证据。细节见 [CANCELLATIONS.csv](CANCELLATIONS.csv)。

## 启动、warmup 与正式成本

三个 probe 分别创建 worker，每个 worker 驻留后连续执行四个 trial，并轮换两臂顺序。worker entry→warmup 完成合计 **45.754120 秒**；其中模型加载墙钟合计 **8.025450 秒**，warmup 合计 **3.148698 秒**。正式 12 个 trial 的实际模型阶段合计 **53.480039 秒**，operator 提交→观察 drain 区间合计 **55.648942 秒**。这些区间分别报告，没有把加载摊进某一臂或隐藏为取消节约。

实际记录有 3 组 warmup-start/complete 标记；字节匹配的 worker 源码每组调用一次 synthetic-zero-audio `execute(..., warmup=True)`，其对应路径有一次 `model.generate`。因此可核对 **12 个正式 generation 调用 + 3 个 warmup generation 调用**。这不是逐次 forward 或 CUDA kernel 的计数；该层 instrumentation 未保留。见 [STARTUP.csv](STARTUP.csv)。

## 我的判断

物理退出已经从理想尾部上界变成了可执行的真实机制证据，而且 37-token 批也有稳定的净模型阶段缩短。最强数字仍来自少数异常固定输入；它证明“值得做服务小试”，尚未证明普遍负载收益、自然异常发生率或无关会话的 SLO 改善。

clean 两臂均启用同一个新执行器，因此其正负小变化支持“本组没有触发取消时结果稳定”，**不能单独量化新执行器相对旧 row-complete 的新增开销**。下一步最有价值的证据是原 row-complete、同执行器 no_cancel、watchdog、父版本取消、简单可信覆盖和因果取消，在真实 Consumer 与原输入义务下对其他合法会话造成的实际差异。
