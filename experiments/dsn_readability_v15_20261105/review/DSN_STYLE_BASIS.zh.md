# v15 的 DSN 写作依据：三篇公开论文的定点复读

日期：2026-11-05。审阅 ID：`dsn_readability_v15_20261105_style_basis`。结论：三篇身份均已由本轮访问的官方 Research Track 名单核实，可作为写法实例；以下是针对 RevTrace 的编辑判断，不是 DSN 规则、代表性统计或录用保证。没有上传 RevTrace 稿件，没有增加参考文献、修改 TeX/Bib、启动 GPU 或新实验。

本轮使用 `nature-academic-search` 的引文核验流程和 `pdf` 的只读页面检查。专用 academic-search MCP 未挂载，改用官方会议网页和作者公开正文。先读取本地 `experiments/dsn_writing_closure_20261031/DSN_STYLE_AND_FIGURE_READING.zh.md` 定位来源，再独立重访主源、复读相关正文并视觉检查三张实际图页；不把旧报告当作本轮正文阅读。RevTrace 比较对象是 v14 的实际 `main.pdf` 第 1、3、6 页及最终冷读报告。

## 身份与本轮实际覆盖

页码均为 PDF 的 1-based 页码。2025/2026 正文是作者公开版本；未将其称为已核 camera-ready。官方名单对 2024 明标 `(Reg)`；2025/2026 不逐项标论文类型，故仅记 Research Track accepted。

| 简称及核实标题 | 官方身份来源 | 本轮阅读锚点 |
|---|---|---|
| VampOS，**Reboot-based Recovery of Unikernels at the Component Level**，Takeru Wada、Hiroshi Yamada，2024 | [DSN 2024 Research Track](https://dsn2024uq.github.io/cpaccepted.html)，标题与两作者匹配，标 Reg | [官方正文](https://dsn2024uq.github.io/Proceedings/pdfs/DSN2024-6rvE3SSpzFYmysif75Dkid/410500a015/410500a015.pdf)：pp.1–2 §I/II；p.4 §IV 与 §V 开头；p.9 §VII/§VII-A；p.11 §VII-D/E、Fig.8（视觉核对）。 |
| ReCraft，**ReCraft: Self-Contained Split, Merge, and Membership Change of Raft Protocol**，Kezhi Xiong 等六作者，2025 | [DSN 2025 Research Track](https://dsn2025.github.io/cpaccepted.html)，标题与作者匹配 | [作者 PDF v1](https://arxiv.org/pdf/2504.14802v1)：pp.1–3 §I–III-A；p.10 §VII 设置；p.11 §VII-A/B/C、Fig.6–8（视觉核对）。可定位 [§I](https://arxiv.org/html/2504.14802v1#S1)、[§III-A](https://arxiv.org/html/2504.14802v1#S3.SS1)、[§VII](https://arxiv.org/html/2504.14802v1#S7)、[§VII-B](https://arxiv.org/html/2504.14802v1#S7.SS2)。 |
| PRAXIS，**PRAXIS: Integrating Program Analysis with Observability for Root-Cause Analysis**，Shengkun Cui、Rahul Krishna、Saurabh Jha、Ravishankar K. Iyer，2026 | [DSN 2026 Research Track](https://dsn2026.github.io/cpaccepted.html)，标题与作者匹配；作者正文 p.1 亦写 accepted | [作者 PDF v3](https://arxiv.org/pdf/2512.22113v3)：pp.1–3 §I–IV 开头、Fig.1/2（视觉核对）；p.8 §V-B–E/VI 开头；p.10 §VI-B/C、Table IV、Fig.7。另读作者 HTML 的 [§VI](https://arxiv.org/html/2512.22113v3#S6)。可定位 [§II](https://arxiv.org/html/2512.22113v3#S2)、[§III](https://arxiv.org/html/2512.22113v3#S3)、[§VI-B](https://arxiv.org/html/2512.22113v3#S6.SS2)。 |

实际 PDF 字节沿用先前取得的公开本地副本，本轮重算 SHA-256，页数和哈希见同名 JSON。未声称与本轮重新下载的远程 PDF 逐字节比较；本轮未重新下载。

## 五条可迁移的写法与 v15 动作

1. **先让读者复述一种能力，再拆实现义务。** VampOS 的 §I/IV 围绕保留应用运行状态的组件重启；PRAXIS 的 §I/III 围绕定位并解释故障根因。ReCraft 实际同时贡献 split/merge 和 membership change，不能据此宣称往届论文都只有一个机制。对 RevTrace 的编辑判断是用“可信修订后保留仍然有效的进展，同时保持原选择任务”统领 EL/AU/SUP、接收结果及故障路径；后者是实现这种能力所需的不同判断，不宜在开头成为并列术语清单。

2. **先交代逻辑角色和对象，再交代线程、存储及身份编码。** PRAXIS 先在 §II 定义依赖图和诊断对象，再由 §III 给调查过程，§IV/V 才展开工具和实现。VampOS p.4 先讲保留谁、重启谁，再进入 §V 的专用线程和通信。RevTrace v14 的角色定义位于 §II-A（从 p.1 页末开始），引言却先出现 EL/AU/SUP。v15 可提前用一句交代 Worker 执行完整调用、Owner 按原规则选择、Consumer 维护当前完整视图；继而解释一次修订为何让三者采取不同动作，再给标签。保持三者为逻辑角色；不暗示每一角色必须独占一个进程。

3. **结论后紧接比较、结果与机制解释。** ReCraft §VII-B p.11 将吞吐和操作延迟分开，并说明改变的协议步骤；PRAXIS §VI-B p.10 把消融结果接到实际错误推理路径；VampOS §VII-E p.11 从注入故障、观察请求延迟走到保留状态为何避免恢复。RevTrace 每个主要结果小节可采用“所问能力 → 同资源/同权限比较与端点 → 数值或图表 → 一句机制解释与适用边界”。不要用阶段沿革、日志路径或版本修复过程替代论证；作者构建的正控和实际部署仍需明确区分。

4. **机制例子保持同一批对象，读者才看得见因果。** PRAXIS Fig.1（p.3）把告警、具体代码依赖和不同诊断接在一起；Fig.7（p.10）回到同一类重试故障解释消融。对 RevTrace，应在同一原调用、实际父状态、完整结果和当前 Consumer 视图上解释“可继续执行”“可选择安装”“可保留视图”，随后才引入一般符号。完整输入确认不等于认可该调用对后继状态的预测；UNKNOWN 可运行/缓冲仍不能提交。这是本稿的技术边界，不能为简化案例而删掉。

5. **测量图要自己说明观察到了什么，示意图要明示它解释什么。** ReCraft Fig.7/8（p.11）给时间/延迟单位、拆分或合并对象、操作时点及 TC emulation 身份；VampOS Fig.8（p.11）在时间轴上标出请求失败区间。其版式并非必须照搬，尤其不能把示意曲线当实测反事实。RevTrace v14 Fig.1 已是实测服务案例，Fig.2 已明示无时间尺度的因果示意：v15 应保持这种区别。测量图注至少独立交代对象、坐标/单位、事件、比较身份及一个可观察结论；不能让读者查协议章节才知道阴影、缺口或期限读点的含义。

## 本轮编辑判定

`STYLE_BASIS_COMPLETE`：主源核验及定点实读已完成。建议集中处理能力主线、角色先后、结果段的证据衔接及图注独立性；不据此新增实验、引文或改变结论。公开论文只能展示有效表达实例，不能证明某种写法导致录用。v14 现有技术边界、原始计数和负结果继续约束 v15；本报告不取代最终稿的全文技术审阅与实际 PDF 视觉验收。
