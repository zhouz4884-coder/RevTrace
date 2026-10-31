# RevTrace：面向DSN的问题—创新—证据重构

基点：696bc889 / immutable v4。最终新稿：`Paper_DSN/revisions/20261031_dsn2027_release_v7`。v5/v6为保留的排版候选；最终v7只在已完成修订上完善Finding的独立加粗段落和标点空格。没有新增神经实验，没有修改runtime、dispatcher、原结果或指标。

## 我的核心判断

这篇论文对DSN最有吸引力的问题，是**可信修订下合法服务进展的保留与失效遏制必须同时完成**：一律拒绝旧工作可以守住某些状态边界，却会丢掉依然有效的计算和已经交付的内容；单独保住计算，也不能保证Consumer保住其完整显示。

对应的贡献是：在递归反馈任务里，将完整输入资格[EL]、原始选择权[AU]和整视图支持[SUP]绑定到各自可执行证据，再协调继续、缓冲、选择、撤回和释放。它的价值由固定原任务的因子实验、完整原调用的及时服务和失效对象正负控制共同支撑。这里的组合是论文贡献；普通WAL、RPC、依赖追踪是实现基础，不必反复为采用它们自我辩护。

本轮主要提高的是**新增能力的可见度与论证可审查性**：首页给具体损失，三判断给动作，主图给因子与内容证据，故障表给保留和拒绝的边界。对DSN风格的采用来自其问题、假设、机制和证据对齐方式；没有把几篇样文当统一录用模板。

## 已经完成的实质修改

1. 首页先讲按时交付却丢失仍合法内容的服务问题；定义`avoidable withdrawal`，解释D2/C8及frontier withdrawal，直接引用机制图。两个最强结果明确带对照：12→17→0的前沿撤回；最终Conservative→RevTrace的45.2%→99.2%双期限offered音频覆盖与0/8→6/8整场通过。
2. 摘要收束为问题、三判断、条件保证、两个比较和3976转移零非法安装，保留four-speaker/predeclared-stratum和原失败边界。未把有限零违规变成无条件概率或形式保证。
3. System and Failure Model前置。selected/Canonical state、whole provisional view、Owner/worker/actualConsumer和存活组件各有具体含义。完整反馈状态假设、浮点执行边界、原输入时钟集中定义。
4. 方法图前移至第3页，同一个j3/P2/P3例子先给直觉，再给充分条件。输入被确认而自己的下一预测仍可错；view失支持而未来输入仍unknown；原Correct/Update与同步安装保持权威。[EL]/[AU]/[SUP]贯穿图、算法与四个加粗Finding。
5. 算法改为Event/Evidence/Action表。按实际源码修正派发范围：原worker/sid扫描沿用；必要工作优先只在选定会话内部成立，不能暗示全局Canonical-first。没有为改善伪代码暗中改调度器。
6. 主结果视觉重排：Fig3a是独立24speaker指定分层的R×S矩阵，Fig3b是最终matched/resident同分母内容分解。主native表只呈最终两臂，早期版本和可靠性扩展10.61%能耗代价移至短段。完整正控更名Alternative joint implementation，明确为本研究另一完整实现。
7. 故障表改显式Policy的12行；24短trial和36bank/3976转移分开。零违规、必要拒绝、故障后新结果与原D2/C8各有端点；64.61–108.08s冷Owner新结果恢复仍在正文。
8. 48个工作点完整图及12个cohort原点保为辅助图，主文用边界表承接。c12/c16失败、时序变号、原同G模型一致性、字符量不变、无reset长流质量失败均保留。
9. 近邻表比较具体复用对象与反馈义务，替代简单勾叉能力矩阵。SSBD/Retire已有的联合复用、显示和失效保留正面承认，不将“原论文没测”写成不可能。
10. 结论以builder可用的设计教训结束：不同用途需要各自证据，才能让必要修订与合法服务保留共同成立。

## Fig1真实joint面板：新增的有限证据

原单例来自48-run开发c16，而非110格独立确认。两臂同source `3570-5694-0003`、同音频SHA、同完整12→14秒非EOS区间；实际首次wholetext与同G选中文本跨臂相同。只读本地14个已归档、有原下载SHA的JSON，冻结源后正式CPU提取一次，模型调用0。

| 对象 | Computation-only | RevTrace joint |
|---|---:|---:|
| 实际首次覆盖，相对各臂自己的ready / s |1.443905769|2.027437605|
| 首次实际认证覆盖 / s |3.719605122|3.794388615|
| 初显后F14区间覆盖缺口 / s |2.175941837|无观察到的后续缺口|
| 该区间D2 |通过|晚27.437605ms|

因此没有将joint画成更快或D2通过。它在原另一臂F12交错时没有ahead view，不能称为同事件反事实避免2.176秒；但它在**自己**的F14认证应用时确实保住先前F16的274-code-point整视图。原完整边界输出、实际后继输入、事件记录和Consumer前后wholeSHA有逐条独立核对。

实际提取源73026a11f6db202d723e6028ad85e6833888ec78；原神经源仍f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf。第一次组合绘图CLI仅在最后图的tick布局失败，数据提取通过与失败CLI分别保留。最终图源aaa13a008772700a2befb0b0d8022e1098f7d7e5纯重绘复用同JSON，不重复运行实际reader，原值/原v4/输入/控制哈希前后守恒。

见[实际比较独立审查](FIGURE_COMPARISON_READER_REVIEW_v1.zh.md)、[最终图形QA](FIGURE_QA_v3.json)、[图源与数据映射](FIGURE_CAPTIONS_AND_EVIDENCE_MAP.zh.md)和[纯文字修订记录](FIGURE_TEXT_REVISION_v3.zh.md)。

## 独立核查与冷读的作用

- [派发语义核对](METHOD_DISPATCH_SCOPE_AND_REVISION.zh.md)定位实际源码范围与跨会话最小反例。
- [原生/故障表审查](NATIVE_RESULT_TABLE_REVISION.zh.md)逐值核对冻结summary；所有旧数据和v4守恒。
- [核心与48点审查](CORE_PRESENTATION_AUDIT_v1.zh.md)核查15/15主分层D2失败、三个交互、144historygroups/22正控对及边界表。c12计算单开有小secondary损失1/1/3，但没有冻结完整2秒非EOS强见证；不是说所有臂所有小损失为0。
- 两位无项目历史读者分别只看[首页+机制图](COLD_PROBLEM_MECHANISM_REVIEW_v1.zh.md)和[结果图表+caption](COLD_RESULTS_ONLY_REVIEW_v1.zh.md)，均能复述主线，并指出真实歧义。已补对照策略名、whole-run P99含义、UNKNOWN运行/缓冲、AU原完整结果、正控名、cohort累计和matched trial/resident request样本单位。小尾段以100%余量解释，全文匹配未称人工准确率。
- [取舍及闭环](REVIEW_RESOLUTION.zh.md)、[一页贡献证据卡](CONTRIBUTION_EVIDENCE_CARD.zh.md)、[展示名映射](DISPLAY_NAME_MAP.csv)可独立查看。

## 完整交付与剩余边界

最终v7为11页技术正文+1页纯参考文献，3张主图、5张表、21条引用。所有12页内容真实看过；最终与候选完全相同的8页有PNG字节同一证明，改变的4页重新检查；主图页面2/3/7另做实际灰度渲染。29字体全嵌入，无Type3、悬空引用或overfull。

PDF SHA256：`c75378b1452304b401625a3fb097c4993370ffe5ca6c769141e2f191b9911c71`。
匿名ZIP SHA256：`4aca80514b19d7aae0a1e74e1e033d83377c2ba169666fb24e29b7cf8305cc59`，625541 bytes。
干净包与全页QA记录：`experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v7.json`。
匿名包独立解压构建结果见`ANONYMOUS_COLD_BUILD_REVIEW_v7.json`，归档前最终门绑定其实际结果。全页彩色/主图灰度及自动检查有界副本在`FINAL_PAPER_VISUAL_QA_v7/`，不混入匿名源码ZIP。

研究事实的限制仍然成立：四native声学来源的外推有限；6/8和7/8不是生产SLO保证；selected-model agreement不是人工正确；必要撤回继续发生；无reset质量/期限失败和冷恢复代价没有被修复。本轮增加的是更清楚、可核查的贡献表达，没有将这些边界包装为新的算法胜利。

官方DSN2027 CFP本轮重开核对：Regular11页、摘要≤150词、Letter10pt/12pt、字体嵌入、参考文献独立页、AI Tool Usage披露。官方来源：https://dsn2027-berlin.github.io/call-for-contributions/ 。实际投稿、作者/冲突/标题定稿及公开稿善意双盲仍需投稿阶段处理；本轮不提交会议、不改公开仓库权限、不删除历史稿。

GitHub目的地仍为用户授权zhouz4884-coder/RevTrace。最新论文入口与有界审计、图源/数据映射/审查/渲染一并同步；实际main及字节核对见本目录DELIVERY_VERIFIED记录。旧v4、旧失败与legacy脏树HEAD7372133保留；CURRENT已恢复实际NN4f，59文件预检通过。
