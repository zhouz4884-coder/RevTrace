# RevTrace 本轮研究与DSN正文取舍

日期：2026-11-02。**本轮完整执行了历史持续覆盖分析和当前完整协议成本测量。正文只采用能够加强现有主线的成本证据，并进一步压缩开发史与防御性叙述。没有为得到第二个算法贡献而继续增加复杂机制。**

## 1. 研究结论与选择

| 问题 | 实际得到什么 | 决定 |
|---|---|---|
| 旧历史合法视图是否只有瞬时前沿差？ | 三条旧正常记录存在14段合法fallback覆盖区间，累计20.77294会话秒；第二实现逐区间、权限、原UID与音频并集复核通过。首次双期限信用不增加。 | 证明首次交付与持续覆盖是不同对象；保留在研究材料，不扩大当前方法贡献。 |
| 当前联合设计之后还需要历史选择器吗？ | 当前90个S-on core运行全部完整重放；joint34与完整正控22均无额外机会。唯一残余在一个R0S1运行，2段、1.72585秒。 | 不加新的Max selector，不开额外线上选择矩阵。 |
| 复杂完整状态/Consumer/WAL是否只剩旧微基准？ | 12次实际完整对象CPU重放和16次真实正常服务全部完成，完整任务、字节、Consumer与实际物理退出通过。 | 主文新增实际协议路径成本小表，替代用旧101微秒代表当前系统的说法。 |
| 计时开启更快是否揭示新算法机会？ | 八对选定任务与完成/放弃/发布数量相同；实际worker-host时长变化与D99差值8/8同向。运行顺序还存在policy内混杂。 | 不归因于observer，不声称净开销/加速，不追加无明确机会的新NN矩阵。 |

## 2. 历史持续覆盖：有价值的发现，也有明确停止理由

正式分析使用原实际Consumer的`observed_perf`、原发布FIFO、完整输入/结果绑定、模式/代际撤权和原core支持门。没有使用CPU快速重放时钟、candidate age或未发布host结果代替原服务时间。包含EOS尾段，不重复计算首次交付信用。

旧两银行共287个attempt：218份具有完整Worker绑定并完成检查；69份曾登记Private内容，但因SIGKILL等没有完整Worker输出文件，保持UNKNOWN，不能算零机会。它们没有被删除。当前core银行158份输入索引中，按事前目标正式分析了实际S-on的90份；其余68份S-off是已登记输入，不冒充本轮完成的S-on检验。

三条旧正例的14段fallback区间对应20个分段。既包括曾实际显示的节点重新可用，也包括旧publication在新root下首次合法；这些类别分开记录，不能都称恢复用户此前看过的文字。它们总计约41.06665 audio-s×wall-s缺失面积，属于固定原生产历史、零额外选择/应用延迟下的离线机会，不是新部署收益。普通索引与扫描同效，不否定服务完成性意义，也不支持新索引算法主张。

当前R1S1和完整联合正控没有残余，因此增加历史registry、选择器、回收或原生adapter状态工程没有本轮实测必要性。原R×S主线保留；这项探索不进入DSN正文的新贡献列表。

入口：[主解释](history/H1_H3_RESEARCH_INTERPRETATION.zh.md)、[独立解释](review/HISTORY_RESULTS_INTERPRETATION_v1.zh.md)、`history/RESULTS_H_ALL_V3`、`history/RESULTS_H_CURRENT_S_ON_V3`、`history/RESULTS_H_AUDIT_REPORTED_V2`、`history/BOUNDED_POSITIVE_TRACES`。

## 3. 当前完整协议成本：真正写入论文的增量

固定当前NN4f程序、原模型/精度/选择/更新、真实Consumer、同步WAL和双完整worker：

- 2条固定来源×2策略×3次fresh CPU进程，共12次完整对象重放。重建完整事实WAL逐字节相同，Consumer语义快照相同，实际fsync保留。
- 2来源×2策略×计时off/on×2fresh process，共16次真实NN服务；没有按性能删格或中途缩来源。八对完整选定状态、原纠错、返回IDs和质量相同。
- 原始C/U神经程序、观测器、试验driver、分析器、独立复核器保留不同实际源身份。原始功率、窗口、EOS、未完成/放弃工作与物理drain均保留。

主文Table III采用8个timing-on服务运行的逐run均值范围：

| 实际路径 | ms/次 |
|---|---:|
| 完整选定状态持久化提交 |20.35–27.25|
| 其中Owner实际fsync |15.78–22.18|
| 整视图Consumer应用 |18.58–23.91|

逐run fsync占提交wall时间的75.8%–83.4%，因此“同步写入占提交耗时的大部分”有直接依据。提交包含完整状态/原结果绑定验证与同步；Consumer包含事实绑定、整视图检查和同步日志。这些是观测到的完整操作路径，不能按行相加成系统wall，也不是移除协议的净开销。没有把旧事务原语101微秒移植到当前系统。

原计时器的CPU括号比wall括号多包含时钟读取。固定null校准的参考中位数为wall190ns、thread CPU2755ns，解释了微短函数CPU读数可高于wall；没有扣除floor或把残差称锁等待。主文选择远高于该分辨率的coarse路径，只用一张小表，不写校准过程和限制目录。

八对off/on的总时延/能量差保留为观察记录，不作为观测税的因果估计。实际冻结顺序中Fullcall每对on→off，Conservative每对off→on，policy内AB/BA没有实现，尽管GPU和block顺序已改变。这个偏差完整记于[实际顺序记录](cost/OBSERVATION_ORDER_RECORD.zh.md)，没有回写旧计划、伪称counterbalance完成或选择有利的配对。正文不写因果开销或observer加速，所以不为该主张追加16个NN；独立审阅同意该取舍不阻断实际路径足迹。

入口：[完整聚合](cost/FINAL_AGGREGATE/PAPER_DATA.json)、[coarse数据](cost/FINAL_AGGREGATE/PAPER_COARSE_FOOTPRINT.csv)、[逐格数据](cost/FINAL_AGGREGATE/NN_CELLS.csv)、[八对观测](cost/FINAL_AGGREGATE/OBSERVATION_PAIRS.csv)、[独立复核](review/FINAL_COST_INDEPENDENT/GATE.json)。

## 4. 完成的独立验证与资源闭合

- 第二实现不导入主summarizer，重新构造PID/thread/span森林、独占区间、原窗口、事实/发布计数、完整原任务和CER、EOS/双期限、两个能量端点。28格、8对全部通过。
- 原c4 checker不修改算法，逐格检查本轮16份实际NN轨迹，全部通过；每格原35个控制是重复，不算560种新故障。新闭合收据绑定原NN pending gate的SHA，保留原记录，并明确`root_actual_trace_recheck_pending=false`。
- 所有原Owner/模型worker按PID generation确认已退出，CUDA compute process为空；没有为了清理而误杀其它进程。
- 模型资产31份、15,845,541,719字节实际逐SHA复核；实际神经执行源为原4f59文件，始终与GitHub归档HEAD分开。

入口：`cost/FINAL_C4_CLOSURE`、`FINAL_RESOURCE_CLOSURE.json`、`BOUNDED_COLLECTION_MANIFEST_v1.json`。模型、环境、原始span、功率和大日志继续保留指定8TB盘，只归档有界源/配置/索引/结果。

## 5. 论文怎样增强

新稿：[DSN v10](../../Paper_DSN/revisions/20261102_dsn2027_release_v10/main.pdf)。保持11页正文、1页参考文献、31篇已引用文献、4幅原矢量主图。没有把实验次数堆成新颖性。

1. 主线仍是完整输入资格、原选择权和整视图支持的联合协调；保留原R×S反直觉结果和原生完整调用证据。
2. 新增当前实际协议路径成本表及简短解释，说明端到端收益已经支付完整状态验证、持久化和交付费用。
3. 缩短第一页缩写解释、方法重复与流水账；突出已经接收的完整结果跨producer退出保持原身份，与新到旧消息被fence分开。
4. 原生主结果只呈现最终同协议对照；旧prototype版本速度/能耗排序和完整32格版本比较留材料，不将跨版本差异冒充单因素消融。
5. 长流保留状态捕获/集合验证及“全部服务失败、原任务插入错误、更高能耗”的实际结论，完整数值和根因诊断放材料；没有只取正面计数或伪造448唯一根因。
6. M、旧历史selector、旧250k fuzz、旧微秒提交和V100容量没有塞进新正文。原生20/92已经直接支撑“输入确认不等于自身预测获权”，无需另引不同攻击/应用模型。

所有原始负结果、旧稿、失败gate与v9均保留。本文的取舍是围绕一个可检验研究论点组织证据，不保证DSN录用，也不把没有当前机会的新分支写成贡献。

## 6. 过程修复记录

H1首个冻结分析源在15控制中暴露genesis查询污染reference状态。独立诊断确认分析器错误；新源分离query副本、保留身份门，17/22控制通过后才跑正式数据。旧失败源/GATE未覆盖。一次独立审核源的后续本地修改也被clean-source prelaunch拦下，未启动分析；新版本冻结后正式重跑，旧树字节恢复并保留记录。未冻结的早期7项observer开发检查单列，不贴未来commit；正式69文件源在原盘重跑通过。

这些开发过程留在材料，不进入正文。正式科学判定以冻结源、配置/环境、原盘结果、独立复核和最终稿QA为准。
