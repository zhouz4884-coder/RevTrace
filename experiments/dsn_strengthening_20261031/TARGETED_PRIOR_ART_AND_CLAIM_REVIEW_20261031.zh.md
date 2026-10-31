# 定向先例与论点边界核验（2026-10-31）

## 决定

**只建议补 1 条必要基础归属，另保留 1 条可选基础归属；不建议以 19→30 为目标扩充参考文献。** 当前工作稿已经直接讨论 SSBD、PredGen、Adapton / Nominal Adapton，这些正是最需要正面对照的先例。本次未找到需要替换当前科学主线的新近直接碰撞；此为限定问题的定向核验，不是穷尽性新颖性检索。

核验对象为 `Paper_DSN/revisions/20261031_strengthening_progress` 中当前正文及三份 `.bib`；补充判断读取了 `ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md`。本次只做本地只读审查和公开原始文献核验，不访问远端实验主机，不发起 NN，不改 source、CURRENT、Git 或论文文件。本报告是建议，尚未把新条目加入工作稿。

使用 nature-academic-search 的定向多源检索 / 引文核验流程。会话未挂载学术检索 MCP，故使用公开 web 工具核对作者版本、官方出版记录及原论文。OpenReview 的 PredGen 页面要求浏览器验证，改用作者 arXiv v2；Birrell 作者 PDF 抓取超时、ACM 返回 403，改读原始期刊论文的大学托管扫描件，并与 Microsoft Research 官方记录核对。没有使用博客、综述或问答页面支撑下列技术判断，也没有上传本地稿件。

## 已有最接近先例：保持并写准，不再增条目

| 已引文献 | 原始来源核实的重合点 | 当前稿件应保留的区别与限制 |
| --- | --- | --- |
| Adapton / Nominal Adapton | 记录计算依赖、输入改变后的复用，以及名称和命名空间支持的计算匹配。Nominal Adapton 也明确讨论参数匹配及 from-scratch consistency。[Adapton 作者论文](https://matthewhammer.org/adapton/adapton-pldi2014.pdf)，[Nominal Adapton 作者 v2](https://arxiv.org/html/1503.07792v2)。 | “相同完整输入允许复用”本身不是新原理。RevTrace 的具体任务是将此原则实例化为原始神经反馈调用的资格，并把其资格与原始 C/U 的选择权、Consumer 整视图支持分开；不能把已有确定性语言结果直接移植为浮点神经重复执行相等定理。当前 §6 的归属基本充分。 |
| SSBD | 旧翻译作为更新输入下的 draft，重新验证；另有仅显示层 mask-k、内部仍保留 suffix 的策略，且实验含无 bias 配置。[作者 v2，§3.2–3.4 与消融](https://arxiv.org/html/2509.21740v2)。 | 不能声称首次联合“计算复用＋显示稳定”，也不能把 SSBD 全部称为近似方法。区别应落在实际已执行完整调用、保护原 C/U、完整状态与 whole-view 依赖，而非笼统的“它只有 token，我们有系统”。当前相关工作已直接点名这项重合。 |
| PredGen | 输入尚在到达时提前生成回复和 TTS；更新输入后验证并复用。其 greedy、top-k 与 reflection 的接受语义不同；作者明确称 greedy 复现基础模型输出。[作者 v2，算法 1 与 §3.1、§6](https://arxiv.org/html/2506.15556v2)。 | 不能声称首次输入期跨阶段推测，不能把 PredGen 全部归为语义近似。当前工作应说明它固定的是递归反馈任务的完整原始选定转移，以及该转移与已显示整视图的关系；未运行完整 PredGen，不能把自建控制称作完整系统复现。当前已有引用足够。 |

表中最后一列是对 RevTrace 已声明边界的比较判断，并非各先例自称“不支持”某项功能；本次没有对这些完整系统做代码重现或实验对战。

## 必要新增：Abadi–Lamport，给投影 / 停顿步正确归属

**建议：加入。** 新写入的 selected-trace refinement 使用了标准行为投影与 stuttering 思路，当前三个 `.bib` 中没有对应基础归属。1991 年期刊记录及作者版本可核验：Theoretical Computer Science 82(2):253–284；作者版本 §1 解释内部步和停顿，§2.4 定义实现所允许的可观察行为须为规范允许行为的子集。[官方期刊记录](https://www.sciencedirect.com/science/article/pii/030439759190224P)，[作者版本](https://lamport.org/pubs/abadi-existence.pdf)。

**支持范围：** 论证方法与语义概念的归属。**不支持范围：** 自动证明 RevTrace 的适配器状态充分、Python/CUDA/OS 正确、神经独立重跑相同、完整运行时 refinement 或活性。本文没有调用该论文的存在性完备定理，也不需要为引用它而额外引入 history / prophecy variables。

精确 BibTeX（新 key，建议放 `formal_refs.bib`；这里只提供文本）：

```bibtex
@article{abadi1991refinement,
  author  = {Abadi, Mart{\'i}n and Lamport, Leslie},
  title   = {The Existence of Refinement Mappings},
  journal = {Theoretical Computer Science},
  year    = {1991},
  volume  = {82},
  number  = {2},
  pages   = {253--284},
  doi     = {10.1016/0304-3975(91)90224-P},
  url     = {https://www.sciencedirect.com/science/article/pii/030439759190224P}
}
```

建议位置：`sections/03_native_refinement_working.tex` 中 Proposition 前的投影定义之后。可用两句：

> Following the standard projection and stuttering view of refinement~\cite{abadi1991refinement}, we relate the durable selected prefix to the protected transition relation. This safety argument treats replay of an existing fact as stuttering with respect to selection; provisional whole-view support and agreement with an independently rerun neural reference remain separate checks.

必须继续保留的观察层界限：刚同步、尚未安装的 fact 可以在 recovery replay 中首次被 Consumer 使用；因此 replay 对 **selected-prefix** 不增加转移，不代表它对 **Consumer 可见状态** 必然没有改变。当前证明投影掉 provisional view，所以不能单凭本 proposition 声称包含 provisional 显示的全部外部行为与原串行程序等价。原始关系允许非确定性时，“实际选定边属于原始合法关系”也不等于“任意另一次神经运行应选同一条边”。这是本文论证范围的判断。

## 可选新增：Birrell–Nelson，给身份 / 重复 / 跨重启区分归属

**建议：可选加入；若 §4.2 仍详细保留这些机制，则加入更合适。** 原论文 §3.2（印刷页 50–51）明确用 call ID 关联当前结果、排除迟到旧结果和重复请求，并用递增序号与 conversation identity 区分重启后的 incarnation。[原始期刊论文扫描件](https://research.cs.wisc.edu/areas/os/Qual/papers/rpc.pdf#page=12)，[Microsoft Research 官方记录](https://www.microsoft.com/en-us/research/publication/implementing-remote-procedure-calls/)。

**支持范围：** 这是成熟的请求身份与重复抑制工程原则。**不支持范围：** 不把原 RPC 方案等同于 RevTrace 的 worker / Owner 协议，也不据其宣称本系统实现跨故障端到端 exactly-once；accepted complete buffer 的输入资格、选择权及整视图支持仍由本任务自己的契约说明。已有 ARIES/OCC 引用解决其他归属，不能单独承担这一身份机制的来源。

精确 BibTeX（原文首页与官方记录支持作者、期刊、卷期、年月、页码；不强加未从本次可读官方页面提取的 DOI 字段）：

```bibtex
@article{birrell1984rpc,
  author  = {Birrell, Andrew D. and Nelson, Bruce Jay},
  title   = {Implementing Remote Procedure Calls},
  journal = {ACM Transactions on Computer Systems},
  year    = {1984},
  month   = feb,
  volume  = {2},
  number  = {1},
  pages   = {39--59},
  url     = {https://www.microsoft.com/en-us/research/publication/implementing-remote-procedure-calls/}
}
```

建议位置：`sections/06_progress_related.tex` 的 execution / authorization / recovery 段，在 Retire 后、OCC 前；或者 §4.2 第一段缩成单一引文。可用两句：

> Call identifiers, monotonic sequence numbers, and incarnation distinctions are established techniques for rejecting delayed or duplicate RPC traffic~\cite{birrell1984rpc}. Here they bind message admission; retaining an already accepted complete buffer additionally requires the original full-input and protected-selection checks.

## 应集中论证的组合贡献

1. **完整输入确认、输出预测正确性和选择权是三个判断。** 原 C/U 实际执行产生结果；早期 identity prediction 只给后继条件输入。后继完整输入后来匹配，不要求该后继自己的 predicted end 正确。输入匹配使调用 eligible，并不自动赋予一个已失去 authority 的新消息提交权。论文应沿用现有分层账本，不以“确认数”替代“durable / Consumer use”。本地 v2 诊断是既有 36 格的 CPU 重配，不是新 NN 性能实验。
2. **执行资格与整视图支持可以分离。** 旧祖先失配可以撤掉当前 provisional view 的支持，却尚未用同 start-frontier 的 actual selected state 反证更后面的完整输入；这提供保留 unresolved call 的具体理由。随后必须单独验证实际 whole-view，不能由“保留计算”推出“不撤显示”。这比声称一般性的“版本号不够”更具体。
3. **恢复的抽象选择语义与显示效果分别检查。** durable append 选一次，重放旧 fact 不再选择；接受完整 buffer 的身份与新消息 ingress authority 分开。这部分基础工具成熟，本文价值在于把它们与实际完整反馈转移、整视图应用以及物理释放关系说清，并由合法正控、错误输入负控和实际 Consumer 事件验证。

这些是可争取的**具体组合贡献**，不是对依赖复用、推测执行、停顿步、WAL 或重复抑制本身的首次提出声明。一个正确实现完整契约的正控制能够复现相应行为，说明行为可重现、边界得到验证，并不自动消除组合贡献；若其采用的条件已经与 RevTrace 相同，它也不再是缺少该组合的反事实基线。比较应公开双方持有的状态、资格、选择与 view 规则，以数据回答更简单方案是否已足够。不能只因增加了正控就声称创新失败，也不能靠给同一原则换名获得新颖性。

本次不新增第三条文献；也不提出用更多泛泛 speculative decoding / exactly-once / verification 引文提升竞争力。下一步的竞争力主要取决于父任务正在形成的配对结果、独立 EOS 请求及跨 producer death 的完整 buffer 正负控能否支持上述具体边界；本报告不预判这些尚未核验的结果，也不把成功预写入论文。

## 查阅与验证记录

- 本地审查：当前 `main.tex`、Introduction / Contract / Continuation / Native extension / Native refinement / Native resilience / Related work / Discussion，以及 `refs.bib`、`formal_refs.bib`、`coordination_refs.bib`；相关三个最近先例均已在当前正文引用，无需重复新增。
- 公开核验时间：2026-10-31；Abadi–Lamport 的官方期刊元数据及作者全文；Birrell–Nelson 的官方 Microsoft 元数据及原期刊全文；SSBD v2、PredGen v2、Adapton 作者论文、Nominal Adapton v2。
- 网络限制记录：Birrell 作者站点 PDF 超时、ACM 403；本机直接 CrossRef HTTP 被套接字权限拒绝，未将其空结果当成核验成功。上述可选 BibTeX 采用已经实际读到的原始元数据。无未核验作者、卷期或性能数字被补入。
- 本次未执行测试或实验。除本报告外没有修改论文或执行代码；建议文字是可审阅稿，不是已发表结论。
