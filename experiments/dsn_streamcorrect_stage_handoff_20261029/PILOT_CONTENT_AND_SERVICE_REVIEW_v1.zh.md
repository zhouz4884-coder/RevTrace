# 三臂 source0 pilot：内容支持与实际服务的独立本地重计

**结论：完整推测臂在本次实际 pilot 的原信用是8.0/8.068s，但其中只有6.0s的首次整文本能取得“在该视图自身实际处理前沿上，与后来的完整 Canonical 文本严格相同”的回顾性支持。ready-handoff 对应为6.5s原信用、5.5s支持；保守完整执行为3.0s、3.0s。** 原信用、D2/C8及全部offered分母保持不变。raw 与仅删除 Unicode 空白的结果相同。三个原运行均未满足整轮D2 P99。

这是完成后的 secondary analysis，覆盖全部三个实际运行，没有新模型、GPU、远端操作或修改 frozen runtime。冻结分析 ID 为 `REVTRACE-SC-PILOT-CONTENT-LOCAL-20261029-v1`；[结果门](PILOT_CONTENT_ANALYSIS_RESULTS_v1/GATE.json)为 `PASS_ALL3_PILOT_CONTENT_SERVICE_RECOUNT`，SHA `65193b6e14eae0a311998702b607ee77e014a4e635c19337934d6bdcdfaa67a3`。

## 比较口径：offered F 和首次实际视图 G 必须分开

原端点对 offered F 查找第一条实际覆盖它的 Consumer row，其视图可以报告 G≥F。本次首先保留这个**原始首次cover**，将其完整文本与**准确 G** 处后来的完整 Canonical transcript 比较；不用最终EOS文本，不裁剪前缀，不寻找较高前沿凑相同。另列严格对齐子集 G=F。G>F 的观测在 offered F 上标记为不具备同前沿可比性，不能冒充 G=F 支持。

三个运行均有同一情况：F=0.5s与1.0s第一次被覆盖时，实际视图G=1.5s，文本为“严”。它与 Canonical(1.5s)相同，**不与 Canonical(0.5s/1.0s)替换比较**。这两个0.5s区间共1.0s原信用在三臂中均保留；严格 G=F 子集则全部单列出去。两种统计的差值相同，不改变臂间相对差异。

## 全三臂结果

每臂均为同一8.068s原始音频、17个offered前沿：16个完整0.5s区间与0.068s EOS尾部。一臂一进程、一次重复，按冻结实际顺序 full-spec → ready-handoff → conservative 执行，不能当成独立人群或重复稳定性结论。

| 作者实现的实际策略 | 原D2/C8信用(s) | 首cover恰逢追加/无变化(s) | 严格同实际G整文本支持的原信用(s) | 其中G=F且有支持(s) | 原D99 / C99(s) |
|---|---:|---:|---:|---:|---:|
| `two_full_early`，保守完整执行 | 3.0 | 3.0 / 0.0 | 3.0 | 2.0 | 5.144795 / 5.398821 |
| `ready_handoff`，ASR packet交接 | 6.5 | 5.0 / 1.5 | 5.5 | 4.5 | 3.467535 / 3.730839 |
| `two_full_spec_early`，完整调用推测 | 8.0 | 6.5 / 1.5 | 6.0 | 5.0 | 2.552455 / 2.835833 |

“追加/无变化”是**首次cover所在实际row相对上一row的LCP事件类别**，不是给新增字符对齐音频秒数。完整推测的8.0s中确有1.5s在累计文字没有新增的row首次cover；不能把8.0s写成8.0s新增转录文字，也不能据此删除原信用。三个运行的所有正F推进中，各有3条文字无变化row；认证前沿推进但文字不变的row各11条。

完整推测相对 ready-handoff 的原信用增加1.5s，对应 F=7.0/7.5/8.0s；其中只有 F=7.0s这一0.5s区间的首次整文本与同F Canonical相同，所以严格同G支持差为0.5s。完整推测相对保守执行的原增益为5.0s，同G支持差为3.0s。以上仍是回顾性选中模型输出一致性，不是修正后的服务信用或人工正确率。

## 所有首次视图也检查，不能只审已获信用者

三个运行的17个 offered 首次cover在 `(F,G,完整首次文本)` 上逐项完全相同，仅实际时间不同。按视图自身G比较，每臂12/17个首cover观测匹配，共6.0s音频权重；五个不匹配的F一致：

| F=G(s) | 首次实际文本与后来同F Canonical的差别 |
|---:|---|
| 5.0 | 首次停在“……上调票”，后者是“……上调票价” |
| 6.5 | 首次停在“……价外收”，后者是“……价外收费” |
| 7.5 | 首次后缀“……收费等违法”，后者为“……收费等法行” |
| 8.0 | 首次后缀“……等法行行”，后者为“……等法行为” |
| 8.068 EOS | 首次后缀“……等法行为的”，后者为“……等法行为为” |

五项不一致音频权重共2.068s，其中完整推测已有信用四项共2.0s；ready-handoff已有信用两项共1.0s；保守臂这些项均原本迟到。不能只在全信用子集汇报相同率，从而掩盖各臂相同的后续文字修订。

为避免把早期同一个G=1.5s视图的三个cover当作独立样本，还分别输出：每臂15个正处理前沿的首次实际视图，其中10相同、5不同；以及每臂20个不同 `(G,raw完整文本)` 的首次出现，其中15相同、5不同。这些只是不同去重粒度，不是新的样本量。[全部51个首cover](PILOT_CONTENT_ANALYSIS_RESULTS_v1/FIRST_COVERS_WITH_EXACT_F_SUPPORT.json)、[每个正G的首次视图](PILOT_CONTENT_ANALYSIS_RESULTS_v1/FIRST_ACTUAL_VIEW_PER_POSITIVE_F.json)及[不同G/文本视图](PILOT_CONTENT_ANALYSIS_RESULTS_v1/FIRST_UNIQUE_F_TEXT_VIEWS.json)均保留。

## EOS、文字生命周期与撤回

完整推测的16个完整0.5s区间全部满足原D2/C8，合计8.0s；最大D为1.956222s、最大C为2.232807s。**唯一D2 miss是0.068s EOS**，D=2.666023s、C=2.950695s。17个前沿的原线性P99仍为D=2.552455s，因此整轮D2失败，不能删尾后宣布通过。分位数以17个offered前沿计算，信用按音频时长加权，不能因尾部音频短就把两个端点混同。最大完整区间D距2s仅约43.8ms，一次运行不建立稳定服务边界。ready-handoff完整区间D2 miss为3个，保守臂为10个；三臂C8均无miss。

沿实际Consumer全部row重计，三个运行均引入27个LCP版本化codepoint occurrence、撤去4个、最终可见23个，raw/去空白相同。各有3次文字擦除事件，全部发生在 Canonical 应用、前后**音频F不变**，旧视图是 `typed_ASR_projection`，新文本逐项等于相同F的完整 Canonical 文本。这不是4个识别错误，也不是4个不同字符位置的最小编辑数；LCP后缀重识别沿用原定义。

三臂实际相邻Consumer row的**音频前沿withdrawal均为0**，因此此pilot没有需要分类的兼容或不兼容前沿撤回。不能把文字擦除算成兼容ahead前沿损失，也不能从0撤回反推全部临时文本都与正确选择相同。上述同F投影被选择结果替换是实际选择修订；本次不以runtime flag为由声称对任意显示策略都“必须”撤掉它。没有新的、可替代核心R/S试验的连续性胜负证据。

## 证据身份与可复算记录

- 实际神经运行源码：`bdfa3b1307d267a5a4caf6484e1ad465c39a592e`。本次独立离线分析源码为单独干净Git仓库 `c12803e3ab411ad7898a34a2e257fdee313df81c`，没有冒用实验归档HEAD。完整[源码manifest](PILOT_CONTENT_ANALYSIS_SOURCE_v1.json) SHA `f84d0d3ee715e5cd56f093b647ee9029ef2758983c48a1d4c60e8961ada9887e`；[冻结配置](PILOT_CONTENT_ANALYSIS_v1_FROZEN.json) SHA `9352ff27d6506828dd4fdeeaa16574db7435ec06089fd3d19c74674737ce2d74`；bundle位于 `packages/PILOT_CONTENT_ANALYSIS_SOURCE_v1.bundle`。
- 只读取collection已验证的18个文件，共857,152字节；全部逐项对上collection SHA。来源为 `SERVICE_PILOT_RESULTS_v1`，没有新增远程读取。使用旧内容分析冻结 `bd18bc8...` 的原字节函数独立重算，三臂原content summary完全复现；原信用、P99、全部miss均一致。
- 另独立逐对象比较三臂17步完整 Canonical WAL（完整state、selection、dispatch epoch、source identity），全部相同。这支持保持本次原选择历史，不认证Private内容。epoch记录相同不等于本报告另外证明所有物理租约/恢复性质。
- 5项有界控制通过：higher-F cover不能冒充G=F、raw/空白区别与整文本比较、禁止较高/最终参考替换、文字擦除不伪造音频撤回、原信用变化必须报错。[冻结源码控制日志](PILOT_CONTENT_ANALYSIS_CONTROLS_v1/RAW.log)及独立config/env/run-record/gate完整保留。[RUN_RECORD](PILOT_CONTENT_ANALYSIS_RESULTS_v1/RUN_RECORD.json)与[完整逐臂结果](PILOT_CONTENT_ANALYSIS_RESULTS_v1/RUNS.json)记录实际环境、输入/源码/配置身份；实际三臂分析输出共409,831字节。

**论文取舍：本pilot可以展示强完整推测对照的重要性及实际时序机会；当前ASR packet交接并未胜过它。应用组合仍可有贡献，但不能用构件69项通过或同源旧保守基线的改善代替这个强对照。** 原始收益与严格同前沿回顾性文本支持都要并列；不将本次source0/r0排序扩展成泛化、独立确认、在线内容认证或整轮SLO成功。
