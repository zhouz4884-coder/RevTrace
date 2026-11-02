# 精简TeX草案：主张、证据和页面预算

目标：让DSN读者理解三个判断为什么不可互换、结果为何能跨producer退出、何时输入确认能转化为实际服务。草案位于`EDITORIAL_PATCH_DRAFT_v1.tex`，没有修改Paper_DSN，也没有编译/声称11页验收。

采用`latex-paper-en`的section-writing流程；本轮只读section-writing模块及experiments指南。段落作用依次为：AU实际后果→对象身份机制→分层实证→可解释边界；新history/cost只留禁用的插入合同，不预写正结论。

|块/推荐位置|可接受主张|实际证据/身份|状态和不可推出|
|---|---|---|---|
|A：AU后或Discussion，三句|当前readset检查不保证返回内容受原可信选择；可能造成真实未来任务损害|`legal_progress_20261026/M_DECISION.md:77-114`；64content-only validation episodes，8tasks×2timing×4methods，原current clean基准；execution `ea9fc8999076aaf773e7618e170953fa1ccd1280`|supported historical stress。OCC答案14/16→0/16；三protected14/16，新增可归因14/16涉及7/8tasks。非currentnative敌手模型、非自然率、非事实真值保证。|
|B1：替换04_native_resilience开头与第一段|新消息权限结束与已接受完整结果有效性不同；原UID不重签|`resilience_policy`完整结果/namespace/lifecycle语义；v9现有refinement与下列buffer4真实见证|supported under declared identity/input assumptions。仅producer death不能给错误输入资格。|
|B2：替换buffer4段|同UID完整结果跨实际producer exit，匹配则安装一次、失配则拒绝|`FINAL_R1_EXECUTION_REPORT_20261031.zh.md`；C/U `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，originalfixture4eb、reader b867；两positive两negative|supported controlled NN interleavings。原CLI compound失败与reader修复留artifact，不说原执行全绿；不声称故障SLO或replacement neural-ready。|
|C：替换05_same_source最后混合比例，四行表或prose二选一|输入资格、durability、原Owner install、Consumer use是不同环节；机会随负载分层|`ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md:13-37`；analysis `ff95f04465d006f76a0e729d3fd5457c32769c1e`，725inputs绑定；40/57、58/90、96/924、166/830|supported。fault58confirmed≠52durable；fault52consumed=50originalOwnerinstall+2replay。总354durable/352originalinstall/354consumed与这四行一致。不是混合生产确认率或每个confirmed均被用。|
|D：long boundary结尾，替换重复范围句|已观测服务失败早于448条件；不能指定它是全部失败唯一解释|同v2报告全8格actualD/C/audio位置与offline长度下界，原CER/P99继续保留|supported temporal relation。无onlineprefixCER、无独特根因、无reset解决方案、非长流部署成功。|
|E：new history/cost结果插入位|暂时只确定被检验的对象与计量合同|待root冻结源/环境/run与独立gate，见本review的PROTOCOL_AND_CLAIM_REVIEW|needs evidence。不得放预测数字或从旧14pointcuts直接写duration/deployedbenefit。|

## 具体页面取舍

1. **B1/B2优先替换而非追加。** 保留已有RPC/ARIES引用和Finding4，删除正文中的reader audit-indexing开发叙述；全部失败/修复仍在artifact，可审阅性不变。
2. **C用四行小表时，不再保留旧360/1901段与表后逐数字复述。** 若新成本图占空间，则用C-ALT prose，仍完整显示四个分母。不要把主文变成实验账本目录。
3. **A限定三句、一个出现位置。** 它只解释AU的实际后果，不能成为新的M主贡献/安全模型扩展。若版面紧，优先C/B，A放artifact动机链。
4. **D保留一条时间先后结论。** 详细8格firstD/firstC/448/LB事件尺进artifact；主文保留当前实际P99/CER和失效事实，不能只留“有边界”而删失败数据。
5. **结果驱动的插入位不预占claim。** 新history若只旧N5正/当前bank零，主文只给Discussion扩展；成本若只spanfootprint，就用当前实现成本小表，不能写全协议因果税。

## 自审

- 清晰度：每段只有一种对象关系；机制先于大N，表内分别写eligibility与use。
- 流向：历史AU后果为动机，native身份/资格为机制，分层计数为实证；三种证据不合并成一个威胁模型。
- 术语：actualConsumer、originalC/U、originalUID、durablefact、matchinginput分别保留；“Strict-protected”仅M历史对照。
- 证据：原已正确两答案不计新增损害；fault58/90不写52/90确认；两个postdurable旧factreplay不加为新神经边。
- LaTeX：原cite/ref/label未在Paper改动；新表label只在草案，root若采用需核重。未新增文献或虚构section指针。
- 未验收项：root选择实际插入块、应用后的总页数/浮动位置/跨节指针、真实history/cost结果与独立gate；此草案不能代替这些最终检查。
