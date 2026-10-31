# v4 基础上的 DSN 论证与图表修订

基点696bc889；immutable v4保留；新稿`Paper_DSN/revisions/20261031_dsn_story_revision`。用户两份文件和补充建议是编辑候选，以下是结合源码与数据后的选择，不自动把其中的所有图表或句子当作既定事实。

## Reader objective and one message

读者从首页应看到一个可靠性问题：原有选择持续纠正推测状态时，服务既要阻断无效推进，也不能无必要地丢掉仍有效的计算和已显示进展。本文提供完整输入资格、原选择授权和整视图支持的协调；问题重要性与贡献、实验逐一对应。

主句：A feedback revision can change the uses of speculative work without invalidating all of that work.

## Structure, then prose, then figures

| 位置 | 读者问题 / 段落职责 | 对应证据与边界 |
|---|---|---|
| Abstract / page1 | Feedback依赖→真实短语消失→因何不该撤→三个不同动作→两主结果和故障证据 | c16实际区间；24独立speaker指定分层；matched4speaker最终6/8；3976实际转移无违规，非一般概率保证 |
| II System and Feedback Contract | 组件/故障边界先显式；选中状态与whole view具体定义；一次讲清认证含义 | local fail-stop/重复迟到；存活Supervisor/Consumer/storage；不自行增加分区/拜占庭保证 |
| III Coordination | 同一j3 running example与图2，再EL/AU/SUP守卫、充分条件、可扫描事件表和selected-trace argument | complete frozen state/实际frontier/contract，unknown非refuted；ownprediction可错，原Correct/Update仍执行；不主张最小必要性 |
| IV Execution | 将身份、完整buffer与故障权限连上主机制 | death前accepted B与之后fenced message分开；普通WAL/RPC支撑完整组合，不单列为新理论 |
| V Evidence | 四臂联合机制→最终原生及时服务→何时有机会/失效→真实故障及范围 | Fig3因子+内容，主native表final两臂；48点边界缩为主文小表而完整图留artifact；负面结论仍正文 |
| VI–VIII | 近邻具体复用对象与额外反馈义务、集中范围、可迁移设计教训 | 不做“论文未评测=理论不能”勾叉表；结论以设计教训收束 |

## Selective decisions on latest suggestions

- 接受展示名：核心R1S1称RevTrace(joint retention)，native Full-call称RevTrace(input-confirmed full calls)；alternativejoint是我们完整正控，保留源码身份差异。冻结ID不变，DISPLAY_NAME_MAP.csv记录对应。
- 接受EL/AU/SUP作为三个判断的索引，**不**把它们另包装成一般必要性定理。Finding1–4用于实际可检查的结果，数量不因排版硬凑。
- 接受short abstract中的45.2%→99.2%，明确offered audio同时达两期限；6/8和four-speaker范围不能删。3976零非法安装写为有限bank观测，不能加“paired fail-stop”来冒充所有bank均配对。
- Fig1(b)仅在同开发c16、同source、同F区间真实轨迹经冻源提取后采用。**110确认不是该c16开发轨迹。** 旧记录还说明joint在同根没有aheadview，因此不能由0撤回总数画曲线或宣称同一对象的反事实保留。
- 问题现象称`avoidable withdrawal`，具体定义为兼容安装撤掉仍有完整支持的whole view；不是把所有纠错撤回都命名为故障。
- 不采用版本号/文本“能给的”那种过度简化的对照列，也不采用近邻EL/AU/SUP勾叉能力上限。正文用正面guard动作与复用对象表表达差异，完整primary-source定位留artifact。
- 机制图从producer死亡主导改成同次反馈安装的计算/选择/显示三判断，intro明确引用，死亡放执行与故障证据。

## Claims and figure contract

| Contribution | Mechanism | Main figure/table | Evidence status |
|---|---|---|---|
| 保留计算不自动保留服务 | R/S分别保护执行与完整显示对象，实际兼容应用协调 | Fig1真实案例；Fig3核心2×2 | 四臂同验证/选择任务，12/1/17/0；全部15run wholeD2fail；时序negative retained |
| 原任务不变的完整调用提前执行 | EL完整输入后确认、AU原Correct/Update、SUP整路径 | Fig2，同j3例子，event/evidence/action表，finalnative主表 | 30→65.821625/66.33975；0/8→6/8，resident7/8；4重复来源不改成新独立样本 |
| 及时收益可以核对内容和失效对象 | 同G firstwholeview后验模型一致，durable绑定+实际消费、失配拒绝 | Fig3内容分解；显式Policy故障表 | 22.5→51/24→50.259；180/14/166相同；接受结果跨死亡2positive/2negative；零违规3976不同于概率保证 |

## New work boundary and verification

无新神经实验、无runtime/dispatcher改动。唯一潜在新CPU数据处理是从已归档14个有界JSON提取另一臂的实际同区间轨迹，纳入新绘图源/输入manifest/环境/配置冻结，独立检查时钟和证据后再执行。所有旧输入和v4稿件哈希前后守恒。

编译只用latex-paper-en compile.py。完成后两次无项目历史冷读：page1+机制图；主结果图表+caption。最终重新核官方CFP、11页/≤150词、字体、灰度/打印尺寸、所有页面与匿名源码包冷构建。旧稿和失败记录保留；提交会议不在本轮授权内。

本轮复用上轮已核的DSN样文阅读，不冒称再次逐页读完全部样文；再次打开ReCraft作者PDF发现仍为同arXiv16页版本，而非假定camera-ready。可迁移的是具体能力/条件/实现/证据对齐，非统一会议模板。官方CFP于本轮重开确认。
