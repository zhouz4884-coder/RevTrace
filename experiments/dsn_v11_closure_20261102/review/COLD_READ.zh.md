# v11 独立冷读：四处值得收束的连接

日期：2026-11-02。阅读对象为当前 v11 `main.tex`、18 个节文件及其实际嵌套的 `tables/native_reliability.tex`（共 20 个 `.tex`），并以 12 页 `main.pdf` 的逐页文本、表图及当前 p1/p2/p3/p5 渲染复看定位首次阅读次序。PDF SHA256：`2cc3121e2a210bb96d850453dfd394d20fd360934c8ea606e976e8396d3776a8`。此次重新形成研究判断，不将此前排版 PASS 当作论证 PASS。未改论文、模型、运行代码或 CURRENT，未运行 GPU。

独立判断：可以保持当前方法和单一主线。最可复述的信息是：**可信反馈改变的是旧工作的具体使用资格；输入确认、原程序选定和实际整视图保留必须各有证据，才能把仍合法的工作兑现为服务。** §III-A 已经成功区分“输入确认但自身预测可错”与“视图失去支持但后续调用输入仍未知”，无需再发明第四个性质或增加定理。新 8 来源、564 个选定转移和同 G 内容证据足以承担主原生结果。下面四项均可用替换文字或既有事件完成。

## 1. 第一页的第三项贡献仍像实验目录，独立确认的力度没有进入占位句

定位：`sections/01_progress_introduction.tex:77`，PDF p1；对照 `05_native_retention.tex:4–10`，PDF p7。

摘要已优先呈现新 8 来源；正文主表也将新 8 放在旧 4 之前，顺序正确。但贡献列表只说 factorial/native/protocol-cost/fault controls，首次读者不知道原生收益是开发来源重复还是冻结的新来源确认。用一个来源配对结果替换实验类型清单即可：新 8、+53.3 pp 及 speaker-paired CI。保留核心 factorial 在原生前面的顺序，因为它先回答联合是否必要；无需全节重排，也无需再加一幅来源图。

## 2. 三判断的区别成立，但“条件保证 → 服务后果”还缺一条短的显式连接

定位：`03_coordination_overview.tex`，`03_native_refinement_working.tex:42–48`，PDF p3/p5；`05_native_retention.tex:113–127`，PDF p8。

目前三个命题本身没有明显越界：重定根是充分见证；连续性是一次兼容应用上的性质；refinement 投影只有 durable selected facts。弱处在于读者要自己把三者与 p7–p8 的服务结果连起来。用约 60–90 词替换现有命题后总结，明确合法保留保住了哪种使用，真实收益还取决于完整结果和实际 Consumer 的到达时间；紧接评估就能自然检验这条链。

另做一次词级澄清即可：让 [AU] 始终指 **original content selection**，producer exit 的权限始终称 **new-message admission**。当前两者大体已分开，但引言的 authority 与故障段的 authority 容易让扫读者误以为 [AU] 就是 producer-liveness 检查。无需扩写失败模型。

## 3. 用剩余六次 D2 失败解释“兑现”，不要仅用中位数收尾

定位：`05_native_retention.tex` 新 8 主结果/表 II，PDF p7；S0901/S0902/S0915 的既有完整事件由 root 独立分析。

主表的 median D99 和 10/16 正确，但读者仍不知道确认的机会如何用完，尤其 S0915。最有价值的补充是新 8 内部的一条执行链，而非再报告一组故障数：在原 offer/D2 上标明条件调用实际启动、输入确认、原完整结果/选定完成、实际首视图应用，定位哪一段跨过 D2。确认、完整结果成为可选、真正被消费是不同事件，不能用确认率或原模型 CER 推断阻塞原因。

正文只需一条最清楚的 S0915 轨迹，加一句另外两来源是否重复同一种先后关系。若事件只证明观测到的关键路径，写“lies on the observed path / remains on the path to delivery”；不要把没有反事实对照的阶段差直接称为该阶段的因果贡献。可以用“全部八个来源配对增益为正”替换现有 `218/282` 计数句，腾出位置：后者口径正确，却没有前者直接回答独立来源是否普遍受益。具体事件数字必须等 root 的原 UID/原时钟复核完成，本文不预填原因。

## 4. 结尾可以更精确，也更少防御性枝节

定位：`07_progress_discussion.tex:15–20`，`08_progress_conclusion.tex:11–15`，PDF p11。

“these witnesses preserve useful service” 比三个条件命题稍宽，容易被读成时限或持续服务保证。把它收敛为 selected-task legality 和兼容应用时的 whole-view retention，再由独立实验承担 timely-service gain，贡献会更可检查。

Discussion 中“此前饱和双来源没有胜过独立副本”和“resident 不能修复 no-reset 质量”已各有旧合同与边界，连续列在结尾容易使独立确认后的主线变成未成功事项清单。可将这两句移到 artifact，保留 c12/c16 和冷恢复的具体解释，把省下的文字给当前新 8 中实际有用的兑现路径。无需追加一个更长的 limitations 段。

## 三段可直接选择替换的英文

### A. 替换引言第三项贡献的实验目录句

```latex
\item Evidence that computation retention alone can worsen delivered
  progress, and that coordinated retention improves service while
  preserving the selected task. Across eight previously unused native
  speakers, timely coverage increases by 53.3 percentage points
  (paired-speaker 95\% CI [44.8, 59.6]), with unchanged original selected
  histories (Section~\ref{sec:eval}).
```

此段只使用已冻结的新 8 主估计；不把 32 runs 或 282 frontiers 当独立 n，不引入新的优越性对象。

### B. 替换 §III-F 命题后的一部分重复总结，衔接服务评估

```latex
Durable append selects one complete original transition; installation,
consumption and replay do not select it again.
Proposition~\ref{prop:refinement} binds selected advancement to that call's
original selection and update. Proposition~\ref{prop:continuity}
independently preserves the supported whole view at a compatible
application. These conditions preserve distinct uses of early work.
The resulting deadline benefit depends on when complete results become
selectable and reach the actual Consumer. Our evaluation therefore checks
selected histories, avoidable withdrawal and timely coverage separately.
```

保留原有 producer-exit/accepted-buffer 的身份句，放在执行协议部分即可；以上段落不把选定事实投影扩大为完整 provisional UI trace。

### C. 替换 Conclusion 最后一段

```latex
The practical lesson is to bind each use to its own evidence: the complete
frozen input for retaining a call, the original complete result for
selected advancement, and a whole dependency path for retaining a
displayed view. Under the declared state and failure contract, these
witnesses preserve selected-task legality and supported views at
compatible applications. The independent native study demonstrates how
retaining that lawful work improves timely service while original
correction and feedback remain intact.
```

三段均是供 root 在编辑副本中选择的替换，不建议再增加新摘要、贡献项、图或定理。剩余实验工作应止于原事件解释和提交前核查；当前证据不要求新增 GPU 分支。
