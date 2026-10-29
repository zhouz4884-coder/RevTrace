# source0 三臂 pilot：选择完整调用保留，保留阶段交接的负结果

这轮最有价值的发现，是我们新组装的完整调用保留实现已经把真实反馈链上的待确认计算转化为合法进展。它没有换掉原作者的纠错选择，也没有依赖增加 GPU、修改 offered 分母或去掉最后一小段 EOS。阶段交接仍是一个保真可实现的组合，但首版 ready-only 调度没有赢过这个同样由我们设计的完整组合，因此不应为了一个代码分支的排名继续横向加实验。

以下是原4个开发来源中的 source0（BAC009S0764W0209），每臂1次 fresh-process 的实际服务 pilot。其用途是决定是否值得做固定确认，不能称为独立来源泛化或显著性结果。

| 实际执行臂 | 原 D2/C8 音频信用 / 8.068s | 全 offered D99 | C99 | C50 | 服务两卡能耗 |
|---|---:|---:|---:|---:|---:|
| 完整调用推测与保留 `two_full_spec_early` | 8.000s | 2.552s | 2.836s | 1.466s | 4420.75J |
| ready-only 阶段交接 `ready_handoff` | 6.500s | 3.468s | 3.731s | 1.857s | 5111.51J |
| 保守原反馈链 `two_full_early` | 3.000s | 5.145s | 5.399s | 3.192s | 4802.78J |

全部三臂的17个完整 Canonical state、原 selected C、返回 IDs 精确等于冻结原任务。三个臂都有两卡、相同 FP32 公开作者推理配置、完整 learned-C neural-ready 预热、同一 ASR 早显语义、同一 Consumer、同一2s lookahead、全部0.5s和EOS offered。保守臂也装载两份完整模型；它的保守性在于未获真实父输入确认前不提前启动未来完整调用，不能将它称为最强并行调度。

完整调用保留比保守臂多5.0s信用，C50下降54.1%，服务两卡能耗下降7.95%。它通过预先冻结的音频信用门，但**三个臂都未通过原 whole D2/C8 分位测试**。这个负点必须与信用一起报告。

## 阶段交接到底花了什么

不是用早期 operator 的9ms来推断部署开销。下面都来自本次实际 producer、物理进程间 Queue、Controller 接收、消费 worker 的日志，单位是毫秒，中位数：

| 实际环节 | 样本数 | 中位 |
|---|---:|---:|
| 完整语义 packet 捕获 | 19 | 11.93 |
| 原 identity-tail 投影 | 19 | 3.37 |
| JSON wire 序列化 | 19 | 10.12 |
| Queue 发出至 Controller 完整 get | 19 | 5.12 |
| receipt 至完整 admit | 19 | 18.08 |
| 同一个包 capture 开始至实际 admit（逐包实算） | 19 | 48.09 |
| consume worker decode/verify | 5 | 8.80 |
| consume 输入匹配与 open-state 恢复 | 5 | 8.33 |
| consume 原 C/U tail | 5 | 239.48 |
| consume worker 完整 wall（含 export） | 5 | 260.29 |

19个实际 wire 中位971,973B，总17,039,897B。Queue区间包含 Controller 轮询、排队和 multiprocessing 内部搬运，不是纯网络延迟。不同环节的中位数不能相加；表中48.09ms是逐包真实端点的中位值。consume 的 decode/restore/C/U也不是全部系统 IPC 成本。

实际 ready hit 是5次，不是旧 trace 的285个 ready机会。5次都保持原 birth/job，完整 birth-start 等于当前 consume-start，epoch相同，packet真正收到后才 dispatch。它们说明细粒度保留可工作，但不能把“存在可复用对象”当成“该调度总体最优”。

另有4次 Authority 派发时已有完全相同输入及epoch的 producer仍在途。producer后来均先于新 Authority ASR完成，分别领先278、360、309、122ms；等待 producer的实际剩余时间约559、385、74、533ms。这是 ready-only 在该时点选择重新执行 A 的具体代价。上述时序只证明重复计算窗口存在，**没有测得假设 join 调度的端到端收益**，也没有证明所有等待都对未来服务有利。

根据 completed job 记录，本点阶段臂实际有19个 producer ASR和11个 Authority fresh ASR，另外5次 Authority consume只运行原 C/U，learned C的non-None调用仍是15次。其 identity 预测会返回 correction-shaped 字段，但不运行 learned C，不能把该字段数当神经纠错次数。完整调用臂是16个完成 ASR，加4个被实际完整输入否定后退出的 ASR前缀；保守臂16个 ASR。额外包成本与重复 A 一起解释为什么阶段切面本身较细不保证服务更好；没有隔离开销消融，不能把全部劣势都归因序列化。

## 完整调用保留的机制与 EOS 边界

独立逐 job 核验见 `PILOT_FULLSPEC_CAUSAL_REVIEW_v1.zh.md`。10次 promotion 均满足实际 model_start < 父 Canon 安装 < model_end；child与parent模型路径真实重叠0.154–0.512s，且完整 frozen input 被真实父状态确认、birth未改。它们不是只跨 Controller 队列的“在途”计数。3个保留调用自己的 identity预测end随后被原C改变，仍能保留当前原调用；**输入相容与最终输出预测正确是不同条件**。

4次 C-entry skip 都有其自身完整start被实际同F Canon否定的见证。原A前缀成本与两卡能耗留在账内，无 learned C、无完整反馈cut、无认证信用。未知未来父状态和仅早期祖先失去支持都不能授权取消。

完整调用臂16个完整0.5s间隔均满足D2，唯一失去信用的是EOS的0.068s。其错误预测EOS输入被实际父修订否定，合法父F=128000直到10.228s才安装，晚于EOS D2 deadline10.068s；正确EOS随后原样执行，D=2.666s/C=2.951s。这不是同输入对象可以合法保留的情况。不能删除EOS、按音频权重掩盖P99、或者把两个不同start的EOS算成复用。

这轮没有自然出现 Canon 更新后保留 ahead view 的事件，因此它单独支持“在相同消费合同下保留在途计算”的真实应用价值，不能单独承担消费保留的必要性交互主张。后者仍依赖核心实验。内容上还须区分 processed-frontier信用与真实文本增量；原 first-cover LCP 分类中 fullspec信用有6.5s触发严格追加、1.5s触发文本不变，更严格的原版本同G文字支持应读取独立 `PILOT_CONTENT_AND_SERVICE_REVIEW_v1.zh.md`，不能将8s称为新增识别文字。

## 当前选择与有限下一步

选择 fullspec 是选择我们提出的完整组合的一种执行实现，并非承认它是别人已发表的现成方案。它与 ready-only 阶段臂共同说明：系统贡献应围绕受保护的完整反馈输入、合法的计算保留/退出和消费关系组织；保留对象可以是完整原调用，也可以是细阶段 packet，不能把“只留某种对象”预设为创新成立条件。

支持已冻结的16格确认：4个原来源全部纳入，2次fresh，完整调用保留与保守原反馈链配对；repeat0/1对换主卡，每来源第二次反转臂顺序，原D2/C8、全部offered/EOS、质量、内容与两卡能耗继续记录。先完成全部16格，再决定是否固定最终同代码做4个speaker-disjoint的元数据先选新来源；不依据这轮输出挑成功来源，不为阶段臂追平我们当前更好实现添加join矩阵。

本地离线分析冻结源 `082a4409d0a5f8eeffefc41e19b41549ec5bf2d0`，完整bundle/manifest/快照均保留。`pilot_transport_analysis_RESULTS_v2/SUMMARY.json` SHA256：`dc8b84dbce4462f314f44bc76d53426b9b685fb70bb7e73afc7e5221e32dc32e`。V1曾将identity的correction-shaped payload计为“C non-None”，V2已明确拆成payload数与真实learned-C数；原V1保留，服务数据和时序结果未改。该分析仅重计18个已经取回的实际小文件，没有新GPU实验、远端I/O或新性能宣称。
