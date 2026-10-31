# DSN 正文与图形实读：给 RevTrace 写作收束的建议

日期：2026-10-31。工作类型：公开论文阅读与当前 v2 稿件只读比较；没有启动神经实验、远端任务或新矩阵，没有修改稿件、实现、CURRENT 或 Git 状态。

## 1. 结论与阅读边界

RevTrace 应围绕一个服务问题组织全文：**可信反馈到达时，哪些已经执行、正在执行和已经交付的进展仍可合法保留，以及谁仍有权推进原任务。** 输入资格、原选择权威和整视图支持是协调这一问题的三个判断，不能写成三项互不相关的系统功能。

实际阅读不支持“DSN 论文必须统一按具体案例开篇”或“必须有某类大矩阵”的说法。四篇开篇顺序不同；可迁移的是问题、机制对象、比较对象和最终证据保持对应。以下是针对 RevTrace 的编辑判断，不是录用规则、录用概率估计或四篇论文的代表性统计。

本轮先读取既有 `experiments/dsn_manuscript_update_20261028/DSN_ACCEPTED_PATTERN_CHECK_v1.zh.md` 定位来源，再重新访问官方录用名单、获取实际 PDF、抽取正文并渲染图页。专用 academic-search MCP 本会话未挂载，采用 `nature-academic-search` 的主源核验原则及 `pdf` 的渲染检查流程；没有用搜索摘要代替正文。

参考的用户材料为 `E:/Downloads/RevTrace_DSN_Writing_and_Closure_4411513.md`，写作起点为 `Paper_DSN/revisions/20261031_dsn2027_release_v2`。该材料用于理解中心问题，不自动升级其中所有建议为必须增加的实验。

## 2. 样本身份、实际阅读页与来源

页码均为 PDF 的 1-based 页码。两篇 2024 文献是会议官方 proceedings PDF；2025/2026 使用作者公开 arXiv 版本，不能把其版面长度、附录安排当作 DSN 2027 的格式规则。

| 论文 | 身份核验 | 实际阅读 | 主源正文 |
|---|---|---|---|
| **Reboot-based Recovery of Unikernels at the Component Level**，系统名 VampOS，2024 | [DSN 2024 官方 Research Track 名单](https://dsn2024uq.github.io/cpaccepted.html)明确 `(Reg)`，标题与作者匹配 | 主文 PDF pp.1–12；引言 pp.1–2，方法 pp.4–8，实验 pp.9–11，局限 p.12；Fig.1–8 均视觉核对 | [官方 PDF](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a015/410500a015.pdf) |
| **iPrism: Characterize and Mitigate Risk by Quantifying Change in Escape Routes**，2024 | [同一官方名单](https://dsn2024uq.github.io/cpaccepted.html)明确 `(Reg)` | 主文 PDF pp.1–12；引言 pp.1–2，方法 pp.3–5，设置 pp.5–7，评价 pp.7–11，局限 p.12；Fig.1–7 均视觉核对 | [官方 PDF](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a142/410500a142.pdf) |
| **ReCraft: Self-Contained Split, Merge, and Membership Change of Raft Protocol**，2025 | [DSN 2025 官方 Research Track 名单](https://dsn2025.github.io/cpaccepted.html)有题目与作者；页面未逐项标 Regular/PER/Tool，因此本报告仅称 **Research Track accepted** | 作者 v1 主文 PDF pp.1–12；引言 pp.1–2，协议 pp.3–8，证明 pp.9–10，评价 pp.10–12；Fig.1–8 均视觉核对。没有精读 pp.15–16 的附录证明 | [作者 PDF v1](https://arxiv.org/pdf/2504.14802v1)、[可定位章节的作者 HTML](https://arxiv.org/html/2504.14802v1) |
| **PRAXIS: Integrating Program Analysis with Observability for Root-Cause Analysis**，2026 | [DSN 2026 官方 Research Track 名单](https://dsn2026.github.io/cpaccepted.html)有题目与作者；作者 PDF p.1 有 DSN 2026 accepted 声明。仍仅称 **Research Track accepted** | 作者 v3 主文 PDF pp.1–12；引言 p.1，概览/方法 pp.2–7，设置 pp.7–8，评价与局限 pp.8–12；Fig.1–7 均视觉核对 | [作者 PDF v3](https://arxiv.org/pdf/2512.22113v3)、[作者 HTML](https://arxiv.org/html/2512.22113v3) |

本地读取副本与页渲染位于 `C:/Users/LENOVO/AppData/Local/Temp/RevTrace_dsn_style_20261031/`，不纳入证据仓库。下表标识本轮实际读到的字节；不把作者预印本称为已核 camera-ready。

| 本地 PDF 名 | 页数 | SHA-256 |
|---|---:|---|
| `VampOS_2024.pdf` | 14 | `6b23bf3e1b726faca86f4564adb739e4d44c9005b1cfd4765d3f1a9276e87348` |
| `iPrism_2024.pdf` | 14 | `9c8f8e1235f3c73b5a797e85af20873fa64de007ab6b536c18f3dfb218f84a3e` |
| `ReCraft_2025_v1.pdf` | 16 | `6e67cb7322219ec6a05da7bbd5d87cd9b31f565a86d47339142f7aaa11cdede1` |
| `PRAXIS_2026_v3.pdf` | 15 | `3db46534775e40330f360ca6936dcc1cb8f37d744fcce8bd41aaccbf4be56a4a` |

## 3. 逐篇实读：论证与图形如何共同工作

以下各卡片仅保留直接影响此次写作的观察；不重述论文全部结果，也不要求将这些机制无关的文献加入 RevTrace Related Work。每篇仅保留一处短引，均少于 25 个英文词。

### VampOS：被保留的对象需要在应用端继续工作

引言从 unikernel 用途进入具体 bug，再说明全重启为何损失未受损的应用状态，随后给组件恢复机制和贡献。实验先问运行/空间成本、重启时长，再看应用与恢复期间服务；代价没有被短恢复时间遮住。可核短引：“How can we perform reboot-based recovery of unikernels efficiently?”（p.2）。[正文 pp.1–2、9–12](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a015/410500a015.pdf)

Fig.1–4 主要用灰阶、方框和箭头解释对象与状态恢复；Fig.5/6 用单栏堆叠柱拆开成本，单位分别为微秒/毫秒；Fig.7 将应用吞吐比与内存分为上下两图；Fig.8 在请求延迟曲线上直接标失败影响。图注给结果含义。应借其对象到服务的闭环；不借用其隔离或故障保证。[图页 pp.4–6、8–11](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a015/410500a015.pdf)

### iPrism：表征、控制动作和最终效果分别回答

开篇以事故背景进入逃生路线直觉，第一页示意图把危险变化与动作结果连起来；之后再定位已有指标。评价明确分为预警、风险表征、控制效果、真实数据特征和成本。短引：“Does reducing STI reduce the likelihood of accidents?”（p.7）。这使“指标识别到了风险”不自动等于“动作改善了结果”。[正文 pp.1–2、7–12](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a142/410500a142.pdf)

Fig.1 用橙/绿路线和分支箭头解释前后关系；Fig.2 用虚/实线区分训练与执行；Fig.4 是 3×5 面板，红/蓝线、阴影及红叉分别编码结局、变异与事故时点，图注解释风险方向和单位。Table III 显示消融与比较理由。应借编码的明确性；不照搬其十五小图密度，也不把仿真安全效果迁移成部署证据。[图页 pp.1、4、9](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a142/410500a142.pdf)

### ReCraft：比较要紧贴协议改变的那段执行

引言从重配置用途进入正确性约束和现有实现限制，再给 self-contained 机制、证明与 etcd 实现。短引：“ReCraft does not rely on external coordinators and blocks minimally.”（p.1）。评价先检正常开销，再测 split/merge；明确说明 TC 是 emulation，并解释为何这样比较，故障容忍分析单列。[作者正文 pp.1–3、10–12](https://arxiv.org/pdf/2504.14802v1)

Fig.1 灰阶集合图解释 quorum；Fig.2/4 用带行号伪代码，红字标通信；Fig.3 以状态序列解释协议。Fig.7/8 把随时间的吞吐和操作延迟分成 (a)/(b)，注明 30 秒事件；延迟柱使用纹理，轴有秒/毫秒，图注明确 x 轴组合含义。应借事件对齐与对照身份；不把大幅伪代码图的字号压缩照搬过来。[作者图页 pp.2、4–5、11](https://arxiv.org/pdf/2504.14802v1)

### PRAXIS：解释为什么有效，需要删除真正新增的信息组织

引言从未解决事故的代价进入诊断对象、双图机制和结果；具体失败案例放方法。评价按准确性、PDG 消融、诊断成本组织；基线也加 code tools，消融另比纯观测和 raw code。短引：“How does incident-centric program context via PDG reasoning contribute to PRAXIS’s improvement?”（p.9）。[作者正文 pp.1–3、8–11](https://arxiv.org/pdf/2512.22113v3)

Fig.1 将代码、依赖和输出放在同一例；Fig.2–6 用一致方框、箭头和局部高亮延续该例。主结果主要用紧凑三线表，标均值/变异、优劣方向、粗体/底色。Table V 将完成时间与正确诊断代价分开。应借连续案例和公平信息权限；少用装饰图标，避免把多段代码及结论框挤入 RevTrace 单栏图。[作者图页 pp.3–7、9–11](https://arxiv.org/pdf/2512.22113v3)

## 4. RevTrace 引言应如何落到具体句子

当前 v2 已有可用问题材料和 Fig.1。主要障碍是第一屏同时引入分层、统计、原任务、完整状态、两种后端及多个身份，读者尚未理解失去的服务，就要消化测量和协议语言。应先完成一个因果链，再给结果规模。

### 推荐五段骨架

1. **服务与实际失败。** 用两句交代“识别结果成为后续输入”，随后给 1.444→1.544→3.720 秒的具体案例。将 37 个字符和原期限读点保留为可观察事实。c16 的过载来源在图注或本段末一句交代。
2. **中心问题。** 已经及时给出正确来源的工作，在新可信反馈到来时仍可能被整体清除；完成/首显指标不能回答中间是否持续可用。本文要决定哪些进展仍有资格存续，同时保留原选择程序。
3. **三个障碍，连到三种动作。** 旧出生版本不能证明完整输入失效；已确认输入不能授予状态选择权；显示失支持不能证明一个未来父输入未知的调用失配。最后补一句：生产者退出涉及未来消息权限，已接受的完整结果需独立判断。
4. **机制。** 先以普通动词写 confirm / retain / withdraw / select / install，再给 input eligibility、selection authority、whole-view support 三个术语。写清继续执行的充分条件与必要撤回各由什么证据触发。
5. **贡献与证据。** 三项贡献对应服务缺口、任务保持的协调机制、实机证据；本段只留两个主结果，其余研究规模和版本沿革进 Evaluation/Artifact。

可直接作为重写起点的英文句子（这是本报告原创草案，不是往届论文引文）：

> Feedback-driven recognition feeds an earlier hypothesis into later inference. A trusted correction may therefore invalidate one call while leaving another call—and an already displayed hypothesis—usable. In one measured interval, the Consumer displayed a complete phrase at 1.444 s, removed it at a compatible update at 1.544 s, and displayed the same text again at 3.720 s. Both first-delivery deadlines were met, yet the phrase was absent when the original two-second deadline was read.

随后用一句点题，而不是立即追加矩阵：

> The service must preserve progress whose support survives an update while revoking progress whose support has actually failed.

机制桥接句：

> RevTrace makes three decisions separately: whether a call's complete frozen input remains eligible, whether the original selector authorizes a transition, and whether the Consumer's whole hypothesis remains supported. These decisions govern execution, installation, and withdrawal without replacing the selected feedback task.

解释本研究最容易被误读的点：

> Confirming a call's input permits that original call to continue; its own prediction of the next state need not be correct. The original correction and update still determine the selected result.

这些句子需要与最终采用的符号、合同及核验数据一致；不能把“完整输入”简化为相同文本或相同音频，也不能让 unknown 在文中变成已证失配。

## 5. Evaluation 以可回答的问题收束

下面使用的是 v2 已陈述的已有结果，未重新测量。冻结只读复算若更新最终 4f 的全文支持数据，应替换相应引用，不借早期 bdfa 的值。

| 主节问题 | 要区分的假设 | 最少需要展示的已有证据 | 段末可写的 lesson |
|---|---|---|---|
| **协调计算与视图为何必要？** | 保住计算是否自然保住 Consumer 已交付进展 | 共同验证底座下四臂；12→17→0 撤回；714.110 s 的信用与同一选中历史；保留负重复 | 计算保留与显示保留解决不同对象；联合收益依赖实际相对进展和兼容反馈 |
| **完整原调用能否产生服务收益？** | 提前执行是否仍执行原 correction/update，而非替换任务 | 最终版本同资源 Conservative/Full-call，30.0→65.821625 / 66.33975 s，0/8→6/8；完整状态、原 C/U、IDs；单列常驻 7/8 | 完整输入确认可把提前执行转为原任务进展；两个 EOS miss 仍然约束期限结论 |
| **失效后什么仍有资格存续？** | 生产者死亡是否必然作废所有既有成果；失配是否被拒绝 | 两匹配 buffer 安装/消费、两失配拒绝，保留原 UID/birth/incarnation；区分 fenced 新消息、已接受结果、持久 fact replay 和新推理 | 失效遏制的边界是权限与支持关系，而不是把生产者存活当作统一有效期 |
| **机会和代价的边界在哪？** | 延迟/信用改善是否等于质量、容量或故障 SLO 改善 | 全 offered/EOS、原时钟；最终/早期全文支持版本归属；共同 drain 能耗；c12、长流及容量阴性 | 声学质量、内容支持、及时信用、持续可用性和资源成本分别成立；不合并成一个“可靠性分数” |

每个结果小节采用四步即可：**问题/假设一段 → 比较与端点一段 → 结果图表和必要机制证据 → 一句得到的知识及其范围。** 不按“先做 pilot、再修 reader、再做下一阶段”的开发时间线组织主文。

可直接复用的英文段落框架：

> We first test whether retaining valid computation is sufficient to preserve delivered progress. The four arms share input accounting, validation, durable selection, and physical execution; they differ only in computation retention and whole-view retention. ... The result shows that retaining work and retaining its supported presentation are separate obligations.

> We next ask whether input-confirmed full calls improve service while preserving the original correction task. ... The final implementation improves deadline credit and whole-run passes, while its two EOS misses remain in the offered-input denominator.

> We then separate producer failure from result eligibility. ... Matching results remain installable with their original identities after producer fencing; mismatching results are rejected against the actual parent state.

读者需要在结果旁看见版本和端点边界，但不需要在每段重复全套免责声明。最终版本主表不能出现早期 8/8 冒充最终表现；“D99”为每运行 P99 的中位数，也不能改成合并总体 P99。

## 6. 图与表的具体取舍

本节基于实际查看 v2 `QA_RENDERED_v1/page-01.png` 至 `page-09.png` 和上述论文图页。这里建议的是改写时的图任务，不预设必须增加图数。

| 当前/拟用图表 | 必须传达的一个主信息 | 具体编辑动作 |
|---|---|---|
| **Fig.1 实际缺口时序** | 首次显示达标仍可能失去依赖有效的已交付区间 | 保留现有可见/认证阶梯、D2 读点和缺口阴影。注释缩到三处事件，完整说明留 caption。保持原 offered 时钟；不添加伪造联合臂反事实线 |
| **主机制图**，替换/重构现有 Fig.2 的重心 | 同一次反馈或失效事件需要对输入资格、选择权威、整视图支持分别作决定 | 用对象泳道或少量事件面板，画出：新父状态确认旧出生的完整调用；该调用自己的下一预测可错；视图失支持但未来父输入未知时单独撤回视图；已接收结果跨 producer fencing 保留。每个保留/撤回箭头旁只标所用证据，不列完整函数名 |
| **主机制旁短算法/决策表** | 每个结论可落实为 guard 与动作 | unknown / equal / unequal 三值先分清；原 selector 授权和同步写入独立；producer death 对新消息的 fence 与既有完整结果的处理独立；物理 release 留到 terminal+drain。不要再给普通 WAL/CAS/RPC 建立新贡献名 |
| **现有 Fig.3 operating workloads** | 首显、信用、后续缺口是不同端点 | 保留三面板和全部点，包括 c12。现有色与 marker 双编码可用；面板名称与正文 R/S 名称统一。c12 不改画成容量折线，三个重复不画平滑趋势 |
| **core 主表** | 交互效果必须在共享底座下读 | 四消融加 Full (ours) 完整正控。保留实际单位、聚合层次和 D2 不通过；Full 的身份在比较设计处一次讲清，无需每行加警告 |
| **native 主表** | 最终可靠版本在原任务上的收益与代价 | 使最终两行视觉上优先；若仍保留早期两行，用明确版本分组。credit、每运行 D99、pass、共同窗口能耗并列。旧独立确认与匹配回归用不同文字解释，不能合并成新独立样本 |
| **故障/恢复小表** | 合法存续和故障性能是两种结论 | 对象、触发、允许动作、观察/端点四列足够。实际新推理恢复慢和 deadline failure 保留；不把旧 fact 重放列入“新结果恢复时间” |

主机制图若同时承载正常反馈和 producer 失效，应限制为少量相连的面板，保持同一批对象与标识，避免两套无关 cartoon。现有 Fig.2 的 batch-drain 细节有实现价值，但占用近半幅主图；可压成 ownership 泳道中的一个终点，完整 race 放算法/正文。新图应先解释论文中心的三种判断。

### 制图与图注约定

这些是本报告给 RevTrace 的编辑规格，不是从四篇论文推断出的会议强制要求。

- 最终栏宽下检查标签；目标字号 8–9 pt，注释不小于轴刻度。无法读清就删信息，不靠整图缩小解决。
- 全文同一对象保持同一颜色，另用虚实线/marker 辅助。建议选中状态用蓝、仍有支持的 provisional 用绿、必要撤回用橙、未决/物理资源用灰；图例写对象或动作，避免只给颜色名。
- 单条线/箭头只表示一种关系。依赖、消息传送、选择授权和时间先后若共存，必须分别编码或拆面板。架构块图不承担精确时序证据。
- 数值图轴上保留单位；seconds of offered audio、wall seconds、J/audio-s 不能只标 `Time`/`Cost`。百分比要给分母。真实点、观察范围、标准差与置信区间分别标明；没有某种统计量就不画成该统计量。
- 图内说明事件或对象，caption 说明比较、聚合和可得结论；完整协议放正文。不要让图注变成全套方法与限制段落。
- 每张图由一句 takeaway 开头，再说明点/线、单位和关键边界。实际案例、原始测量、机制示意和离线复算在图注中各自标识；示意图不带伪测量坐标。

Fig.1 的建议 caption 起点：

> **A compatible update can remove progress after timely first delivery.** The actual computation-only run displays the interval at 1.444 s, withdraws it at 1.544 s, and restores identical text at 3.720 s. The vertical line marks the original D2 read point; shading marks the visibility gap. This c16 overload case illustrates the failure mode rather than its natural incidence.

主机制图的建议 caption 起点：

> **RevTrace separates eligibility, authority, and visible support.** Matching a call's complete frozen input permits the original call to continue; the original selector still determines its result. A whole view is retained or withdrawn by its own dependency witness. Fencing a producer removes future message authority while preserving already accepted results that remain eligible.

具体 caption 应与最终面板实际画出的事件一致；未画出的失效分支不要仅在 caption 宣称已解释。

## 7. 重写后的验收问题

1. 未参与项目的读者看完第一页，能否指出“已交付进展丢失”这一服务问题，而不只复述 speculative ASR？
2. 能否用一个旧出生调用说明“输入资格确认”与“自己的下一预测正确”不同，并指出最终选择仍由谁完成？
3. 能否指出 unknown 对应等待哪些证据，而不是把它当作失配或自动取消？
4. 每项贡献是否有一个机制判断和一组相应的实际证据；是否避免把组件数量、日志数量或检查数量当成贡献？
5. 在主结果附近能否同时读到原任务保持、全部 offered/EOS、最终 6/8 和常驻 7/8、实际内容支持版本及共同能耗窗口？
6. 图注能否在脱离开发日志时被理解，图中字体能否在最终双栏 PDF 上读清？

本轮给出的写作决策是：**保留已有问题时序图和真实负结果，重构主机制图与问题驱动的评价叙述；不因模仿往届版式而增加新神经实验、额外矩阵或无关引用。**
