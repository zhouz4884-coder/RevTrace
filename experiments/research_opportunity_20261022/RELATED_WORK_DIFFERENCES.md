# 正式发表相关工作与差异

本轮采用文献检索技能的multi-source-search路径。学术MCP未提供，OpenAlex回退收到429，保留错误；使用CrossRef及作者/正式会议页面核验，不把预印本当作既有正式发表结论。不是穷尽检索，也不宣称first。

| 正式工作 | 已有能力 | RevTrace B可研究的较窄区别／不能主张的部分 |
|---|---|---|
| [RIFL, SOSP2015](https://seojinpark.net/projects/rifl/)，[作者PDF](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf)，DOI10.1145/2815400.2815416（CrossRef核验） | RPC结果记录、重试定位及去重；不是“普通RPC从不保留结果” | 本应用需把恢复后仍合法的父状态/音频/执行χ与新epoch重新授权对接。但可用通用结果跟踪承载，不能宣称“跨epoch接回结果”本身全新或现有组件做不到 |
| [Ray, OSDI2018](https://www.usenix.org/conference/osdi18/presentation/moritz) | task/actor统一执行和容错控制状态 | 本原型没有Ray完整分布式故障覆盖；差异仅是对模型生成状态的准入谓词及新owner选择规则。不能把一个Supervisor+Pipe当作发明actor/任务容错 |
| [RobustRL, OSDI2026](https://www.usenix.org/conference/osdi26/presentation/chen-zhenqian) | 角色级故障隔离、失败角色恢复及重连存活角色 | 模型角色存活/重连不是新颖性依据。本轮研究的是Authority计算来源可存活但写权限需新纪元重授的应用条件；不能把避免模型重载的全部收益归给收养算法 |

RIFL主要处理已完成操作及重试语义；本轮还测了正在计算的任务，但活任务服务/actor同样可保存未完成请求。仅增加该故障点并不能自动建立创新性。另一方面，旧parent已变或任务已提交时应拒绝/重放而非盲目接受，这是可执行安全条件，不是对通用基础设施表达能力的不可能性定理。

LUMEN、FailSafe检索结果只有本轮未核实正式发表身份的预印本，按用户既定口径不作为新颖性否决依据；也不据此声称已排除所有近邻。AMBROSIA技术报告不计入本表的正式会议证据。

## 对后续强基线的要求

若B继续，至少加入“相同Supervisor+规范请求ID+结果跟踪+当前输入谓词”的普通任务重试/缓存组合，允许它实现全部规则。若与B等价，就把该机制界定为应用特化的恢复策略/可执行规格与实证，不包装成排他的新算法。当前Warm Strict只是保守的安全丢弃政策，不能代表所有最强常规系统。
