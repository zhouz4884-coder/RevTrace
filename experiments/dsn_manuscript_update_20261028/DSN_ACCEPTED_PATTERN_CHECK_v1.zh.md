# 已收录 DSN 论文的有界论证模式核查 v1

2026-10-29。为落实用户“从往届 DSN 收录文章提取共性”的要求，本轮先定位已有 `docs/research/independent_synthesis_20261028/DSN_READING.zh.md`，再重新访问官方收录名单和原文。采用 literature citation-verification 流程；专用学术 MCP 未挂载，使用官方会议页面与官方/作者正文作为主源。没有远端 SSH、模型/GPU 实验，没有修改论文。

## 样本与身份边界

本轮实质样本选择 **2 篇 DSN 2024 Regular**，均位于要求的 2024–2026 年区间，官方名单明确标注 `(Reg)`。选择理由是分别提供“细粒度保留服务＋实际成本”和“表征—动作—最终效果的强消融”参照。只凭两个定向样本，不宣称统计代表三届全体 DSN 文章，更不能推断录用概率。

三个核心主源链接：

1. [DSN 2024 官方 Research Track 收录名单](https://dsn2024uq.github.io/cpaccepted.html)：`Reboot-based Recovery of Unikernels at the Component Level (Reg)` 与 `iPrism: Characterize and Mitigate Risk by Quantifying Change in Escape Routes (Reg)`。
2. [Reboot-based Recovery of Unikernels at the Component Level：官方 proceedings 正文](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a015/410500a015.pdf)，系统名 VampOS。
3. [iPrism：官方 proceedings 正文](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a142/410500a142.pdf)。

没有以 Workshop、Disrupt、Poster、工具短文或同名预印本替代这两篇 Regular 身份。

### 额外重核的两个名字，不用于凑 Regular 样本

* **ReCraft** 的完整题目与作者确实出现在 [DSN 2025 官方 Research Track 名单](https://dsn2025.github.io/cpaccepted.html)。本轮也重新读取了[作者 v1 原文](https://arxiv.org/html/2504.14802v1)的 failure assumptions、条件性活性和 §VII-A/B：正常 etcd 性能相近，转换时的中断才是评价对象。官网该名单没有逐项标 Regular/PER/Tool，因此这里确认的是 **Research Track accepted**，不额外升级未标明的子类别，也不把旧 memo 的名称当证据。
* **PRAXIS** 的题目/作者见 [DSN 2026 官方 Research Track 名单](https://dsn2026.github.io/cpaccepted.html)，[作者正文 v3](https://arxiv.org/html/2512.22113v3)同时声明 accepted to DSN 2026。正文区分 code-available 诊断范围、给基线 code tools、PDG 消融和诊断开销。该官方名单同样未逐项标明细分类，因此不计入本轮两个有明确 `(Reg)` 标签的主样本。

Keylime 未重新精读，不把它列成本轮新增的已核论证样本。以上额外身份说明也不等于要求把这些论文加到 RevTrace Related Work。

## 两篇原文究竟提供了什么

### VampOS：恢复粒度必须落实为仍在运行的服务，而非只有重启时间

原文 §IV–V 先给保留应用内存、恢复有状态组件的问题，再组织消息交互、隔离与重放。§VII 比较调度/组件合并配置，测时间与空间成本，并以 Nginx 请求成功和 Redis 请求延迟检查恢复期间服务。§VIII 明确共享 hypervisor 状态组件不能直接一致重启，确定性重复 bug 也在当前故障模型外。[官方正文，§IV–VIII](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a015/410500a015.pdf)

**我的归纳：** 单独减少重启/计算耗时还不够，机制承诺保住的对象必须在应用端真正继续服务；组合的收益与维持这种组合的开销应共同显示。该文不能为 RevTrace 提供崩溃或内存隔离保证，能借鉴的是评价对象与贡献对象一致。

### iPrism：新表征有用，不等于动作有效；动作有效仍需给适用范围和开销

原文 §V 将风险预警、风险表征、控制后事故减少与真实数据特征分开提问。Table III 保留有/无 STI 的控制器消融，并显式区分仿真危险场景与真实 Argoverse 特征分析。§V-E 给表征与控制器开销；结论限定 actor-related 风险及所演示控制动作，未覆盖天气、传感器遮挡或软硬件故障。[官方正文，§V 与 §VII](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a142/410500a142.pdf)

**我的归纳：** 不能把“识别到了机会”“执行了动作”和“最终服务更好”合并为一个证明。消融要删掉真正新增的信息/动作，完整应用效果则保留正常任务、实际成本和失效边界。该文并不要求 RevTrace 训练控制器；我们只迁移这种证据分层。

## 可以落实到当前稿的共性与写作映射

下面都是我对上述定向样本的跨论文归纳，**不是 DSN 官方录用规则**，也不是要求每篇 DSN 必须有同一种故障、定理或矩阵。大部分证据 RevTrace 已经完成，当前主要是主文选择与论证闭环。

| 我的归纳 | RevTrace 已有对应材料 | 最终稿可落实的写作动作 |
|---|---|---|
| **受损服务性质先于技术清单。** | 原完整 2-s 区间及时首显，兼容更新后撤回 37 个新显示字符，在原 D2 读点缺失，随后原文相同地回来。 | 第一页先说“已交付且依赖仍有效的服务为什么丢了”；再引入合同与动作。不以 WAL、哈希、双 GPU 或自造技术名词开篇。保留本例来自 overloaded c16 的范围。 |
| **失效反例应直接导出机制的检查条件。** | 旧 birth version 不说明实际依赖失效；同文本不等于同完整状态；实际 frontier 与冻结输入决定接续；native 输入确认与自身输出预测不同。 | 在方法中把同 frontier 完整 state、完整执行边、冻结输入/身份紧贴反例；短充分性命题与具体 guard 对应。不把它吹成新的通用增量计算理论。 |
| **保住正确性路径之外，还要保住合法服务。** | core 相同 Canonical 历史下 R-only 撤回 17、双关 12、joint 0；native 原 C/U、完整 state 和 IDs 不变。 | 用两个服务问题组织评价：已交付服务能否持续可用；同一选中任务能否在原期限内继续完成。core 与 native 各承担自己的问题，不互借“全栈保证”。 |
| **消融信息/动作，完整实现正控说明组合身份。** | R/S 四臂共用验证、耐久与执行底座；Full Standard 是作者构造的完整组合替代；native 同资源保守完整执行与 full-call。 | 明确定义两种对照角色：四臂解释保留动作；完整替代说明能力是否依赖某一 policy。将作者正控写为 ours，不把它当外部先例，也不要求它失败才算创新。 |
| **机会见证、端到端收益、代价三层独立。** | 真实 model-in-flight promotion/坏 start 停在 C 前；实际 Consumer 原信用/全文支持；两板能耗、所有 EOS；K 请求/ACK/drain/后继链。 | promotion 数不能代替期限收益；组件保真不能代替部署结果；首覆盖音频信用不能改称新增文字。主结果旁给完整任务/质量保持和能耗口径。 |
| **边界解释能力，不淹没主论点。** | 48 格包含负 c12；headline D2 失败；K 错峰混合；旧两 full replicas 容量阴性；encoder eager 净慢停止。 | c12 和服务边界在图/紧邻正文保留；旧试错目录、组件失败沿革移 artifact。把 stop 作为设计选择，避免连续免责声明占据摘要。 |

## 对目前 one-system contribution 的具体判断

我认为与这些 Regular 样本相符的论文形态是：**一个具体反馈合同，两个必须分别处理的保留对象，一条从合法性条件到实际服务与成本的证据链**。不是“所有构件都首次发明”，也不是“做了很多检查所以可靠”。

这也与往届官方类别定义相容：[DSN 2025 Regular CFP](https://dsn2025.github.io/cfpapers.html) 明确允许以既有技术的实现和评价为内容的实验研究，同时要求新的科学贡献和知识推进。这个正式定义支持具体组合/应用创新的论文形态；它不保证某项组合自然满足新颖性，也不代替与最近邻的实质比较。

可保持的主张是：RevTrace 提出并实现这套组合，在完整声明接口内给可执行的继续使用资格，协调已执行工作与实际整视图，并在保留原选中任务的情况下刻画服务收益和边界。新的 native full-call 是这一原则在原递归纠错流程中的具体实现和实测，不应降为审计 appendix。

以下三项最终文字检查最有用：

1. 摘要、引言贡献和结论是否都说同一个合同与组合，且给 core/native 各自实际能支撑的服务效果？
2. 每个机制条件旁是否能找到一个它排除的具体坏交错，或一个因此得以保留的实际执行对象？
3. 主表的性能差异是否同时可见全部 offered/EOS、同原选择任务、强简单对照和真实能耗？若边界失败，是否在同一小节就能看到，而非需要翻 artifact 才发现？

这些动作都可用已有正文与本轮已冻结确认完成，不建议新增 GPU 研究分支。上述机制无关的 DSN 论文是**研究组织参照**，无需为显示“读过 DSN”而加入 RevTrace Related Work 引用。

## 本轮核查结论

* 两个主样本的标题、年份、作者来源和 Regular 类别已由官方 `(Reg)` 名单与官方 proceedings 正文匹配。
* ReCraft/PRAXIS 的 Research Track 收录身份重新得到主源支持；未将官网没有展示的细分类当作已核事实。
* 共性是我基于定向样本的论证归纳，不是全会场统计，也不是“满足后保证录用”的公式。
* 没有新建文献堆砌型 Related Work、没有改稿、没有新实验或上传。
