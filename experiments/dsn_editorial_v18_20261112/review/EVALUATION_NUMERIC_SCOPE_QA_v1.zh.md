# v18数值/证据范围只读QA

**结论：B/A/C/E/D及N8的数值均通过；未发现必须重算数据的问题。剩一处历史银行标注建议在发布前说清。** 本审查只读当前source/PDF和已封存结果，没有编辑论文、运行实验/模型或编译。PDF数字通过现有pdftotext抽取核对，视觉版式由Root另查。

## 唯一需要说清的证据标签

`05_evaluation_v16.tex:149–153`的“earlier runtime comparison ... under both policies”未点名旧比较为**Conservative–Fullcall**，前文当前比较则是Ready-only–Fullcall。建议直接点名旧策略，避免把218/282、47→107.162、CER13.22%误读为当前Ready-only结果。

218/282是每个旧策略各自的后见same-G全文匹配**计数**；已有汇总不证明两个218集合成员逐一相同。当前文字应作“each policy has218...”理解，不能升级为同一218个frontier或瞬时视图文本完全相同。该标签澄清不需更改数字或补实验。

## 核对映射

| 块 | 当前稿 | 原证据与范围 | 判断 |
|---|---|---|---|
| B | cohort I=18.530/6.205/17.555s；source fraction I均值5.90pp，描述95%区间[1.13,10.28] | H3 aggregate/RUNS、FACTORIAL_EFFECTS、SPEAKER_BOOTSTRAP，primary/Qwen/rho1/staggered；24source、3cohort四臂块；原dual_audio_fraction，不是U_norm | 正确；已明确定义I与source fraction，未改成joint-vscompute差 |
| A | c16r2：201.960 vs194.735s，原D2读点缺失4.000 vs0 | timely_continuity_v1/README.zh.md:23–31，post-hoc secondary开发银行；原credit不变 | 正确，首次事件指标与当前服务状态反排名 |
| C | 92实际model-active promotion，其中20 tentative ASR successor state不同于原C/U结果 | dsn_streamcorrect_independent_20261029/FINAL_PRIMARY_RESULTS_v2/SUMMARY.json → aggregates.two_full_spec_early.mechanism_counts：92/92/92/20；analysis_snapshot_v1/analyze_confirmation.py:68–85 | 正确。20定义为asr_early.projection.end与job.end不等；不是20个输入错误、20个非法安装或20个人工转写错误 |
| E | 两after-durable事实，durable/原Owner安装/Consumer use=2/0/2；3976selected、9068provisional、90compat保持 | dsn_strengthening_20261031/ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md生命周期表；dsn_native_resilience_20261030/FINAL_EXECUTION_AUDIT_GATE_v1.json:64–78 | 正确。原job同一identity、sequence5恢复重放；应用数不是故障种类或新N8样本 |
| D | commit20.35–27.25ms，nested fsync15.78–22.18，Consumer18.58–23.91 | dsn_continuity_cost_20261102/FINAL_RESEARCH_REPORT.zh.md:27–46；8个timing-on run的mean范围 | 正确；表caption限定旧实现、inclusive非相加。4.1–5.5%为500ms间隔比例，没有称因果observer tax |
| N8 | 93.9/42.4%、51.47pp、223.215/322.991worker-s、91.880/117.823kJ、10/16vs0/16 | FINAL_N8_SUMMARY.json，当前NNde09、32格；worker总时包含completed/abandoned，能量到物理drain | 正确；源内合并后八来源三轴同向，最终3次Ready复用与pilot0次分开 |

N8 P99定义现在准确：先每source对两次per-run P99取median，再跨8source取median；Full1.667370→1.67、Ready4.984474→4.98。没有误用全部16run中位数1.630878/5.008969。条件2/256的统计假设和source内重复处理也保留。

负差现在区分两种效应：paired_jitter/A/r1的R11−R10=−4.245s、I=−2.245s，仍有5次兼容保留；primary-sync pooled R11−R10=−.790s、I=+2.565s，仍有3次。这里是更新边界机会，不是去重view identity；已删除“无ahead所以无效”和上线前单变量预测器推断。

## PDF与当前源

现有PDF中可检索到B区间、A反排名、N8表/宏、P99双层median数值、D成本范围，以及两个负差与I的正确符号。图输入保留此前核准的native8source/32repeat点及H3 primary图；没有新图数据银行混入。

本次核对时：main.pdf SHA `bffdc0529c0593a84f8ca3d76793ff383280e08338c9c809b625488168d09332`；05 SHA `c24fb282195cb16a714f4ea05de34e0033d4ac11e529af3d5c0597469ba912c9`；04 SHA `15ef755bf5372b0f77e6b759f6a8d974aff8548361ecce639f56e565dbc34079`。Root随后缩写venue/重编会产生新PDF身份，不影响本次数值结论。
