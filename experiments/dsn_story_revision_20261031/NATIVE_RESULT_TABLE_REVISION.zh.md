# Native结果与故障表修订，2026-10-31

工作范围只修改新稿 `Paper_DSN/revisions/20261031_dsn_story_revision/` 下：

- `sections/05_native_retention.tex`
- `sections/05_same_source_validation.tex`
- `tables/native_reliability.tex`

旧v4、runtime、所有既有正式结果和CURRENT未改。新增模型调用0、新raw扫描0、SSH调用0。用户两份修改材料是编辑候选；选择性采纳结果优先、主策略命名和表格显式策略列，未扩大科学主张。

## 本次具体改变

1. 原生结果先写最终四来源的科学比较：Conservative execution与RevTrace（input-confirmed full calls）。正文先给45.2%→99.2%的offered audio双期限覆盖和0/8→6/8，再解释固定原任务与同资源。
2. 主表仅保留最终两臂，不让Earlier/Final版本矩阵先于主方法。表的coverage、D99、共同drain能耗及pass分别有明确单位与聚合层次。
3. 旧版本归属移入两个短段：来源最初由独立确认按metadata选出；本32-run为复用四来源的matched regression。早期独立bank37.0→66.33975s、0/8→8/8与早期matched8/8保持各自身份。
4. 保留真实代价：最终RevTrace较最终Conservative共同drain窗口能耗低6.52%，较早期matched RevTrace高10.61%（39.735→43.952kJ）；最终两EOS失守和0.163/0.050s回归差值保留。相近median不被写成版本等价。
5. 常驻结果以0/8→7/8与31.0→64.118875s开头，再定义single-outstanding、closed-loop、原file EOS以及实际消费后才开始下一请求。第二S0908 repeat D99=2.229s未删。
6. 内容结果用“相同内容更早到达”统领，保留最终matched22.5→51.0、resident24.0→50.259s及失配、unknown、180/14/166字符出现次数。106/136→104/136的all-offered匹配数也保留，防止将及时性收益写成总体临时文本质量提高。
7. 故障表从6条件×每格上下叠放改为12行显式Policy。所有24短trial完成和零非法安装集中于caption；Reject/selected-mutation、new-result、joint D2/C8、EOS、energy全部保留。每个数值与v4表逐项相同，并重新与冻结ALL36 bounded metadata独立核对。
8. 3976转换清楚属于24 short+4 regression+8 sustained =36trial总体，未误挂到24短trial表；其中零非法安装为独立结构检查的轨迹结论。8worker deaths、8局部重复/迟到拒绝、354durable/352原Owner install/2恢复首次消费保持。
9. 完整buffer控制保留match2/use2与mismatch2/reject2、accepted-before-death以及原身份，修复审计器的披露压为一句并保留原failed gate归档。未将其变成自然发生率或fault-time SLO。
10. 无reset长流的全部期限/质量失败、能耗变差、state/collection范围及必要撤回仍在正文。未用常驻EOS请求掩盖其失败。

## 证据映射

| 图表/主张 | 冻结来源 | 本轮验证 |
|---|---|---|
| 最终native两臂 | `experiments/dsn_strengthening_20261031/PAIRED32_V2_RESULTS/SUMMARY.json` | 直接聚合8trial/臂的offered、credit、median D99、共同external physical-model-drain energy和原pass；与主表小数显示逐项一致 |
| 原来源与版本代价 | 上述matched32原summary及`FINAL_RESEARCH_AND_PAPER_REPORT_20261031.zh.md` | 不混早期独立确认与新的matched regression；较早期39.735→43.952kJ仍在主文 |
| resident时序/请求通过 | `experiments/dsn_strengthening_20261031/RESIDENT4_V2_RESULTS/SUMMARY.json`及最终正式报告 | 仍是2trial/臂、8request instances/臂，而非8个独立模型常驻实验或连续录音 |
| 内容三段堆叠候选数 | `experiments/dsn_writing_closure_20261031/CONTENT_CPU_V4_RESULTS/complete20/SUMMARY.json`与用户`proposed_content_chart_values.json` | 四行逐项相符；类别互斥且相加等于相同66.33975s；unknown=0已确认，非当作缺项填0 |
| 12行故障表 | `experiments/dsn_native_resilience_20261030/FIGURE_TABLE_FORMAL36_v5_results/ALL36_MACHINE_TABLE.json`，cohort=short_main | 6条件×2策略×2repeat共24；完成/illegal、reject/mutation、new-result min/max、joint pass、EOS、energy min/max各项独立对应 |
| 3976与36trial | 同ALL36 | 独立确认36条cell记录的checked_durable_transitions合计3976；不与只含24trial的主表合并分母 |

显示名改变不改实验ID：`conservative`→Conservative（设置中解释Conservative execution），`fullcall`→RevTrace（设置中解释input-confirmed full calls）。该命名适用于最终原生适配器，不将其与core的相同原则误说为同一runtime源代码。

## 数值和源完整性检查

`verify_native_presentation.py`仅消费已有有界summary，不重扫raw。`NATIVE_PRESENTATION_CHECK_v2.json` gate为 `PASS_NATIVE_PRESENTATION_ONLY_FROZEN_VALUES_AND_12_POLICY_ROWS`：

- 主表最终credit/D99/energy/pass逐项与原32-run源一致。
- 12行故障表展开后与v4原上下叠放表数值完全一致。
- 12行又分别对照冻结ALL36 metadata，完成/拒绝/clock/pass/EOS/energy均守恒。
- 用户图值JSON与最终CPU字段逐项一致，三类互斥和同分母成立。
- 八个固定输入文件（含旧v4 PDF及三个旧TeX）哈希前后不变；记录见`NATIVE_RESULT_INPUT_HASHES_BEFORE.json`与check记录内同一列表。

原CPU内容summary SHA256仍为`a3c9292ecccebc3660870e181e491d1d41d778941827b51cffa5914f64a26e33`。CPU分析源与NN4f执行源身份保持不同；本轮只是展示算术和段落组织。

## 打印宽度与可读性检查

另在`native_table_qa_v1/`用IEEEtran默认10pt正文、`small`表字和516pt文本宽度独立排故障表。通过`latex-paper-en/scripts/compile.py main.tex --recipe pdflatex`编译，exit0，未直接调用TeX。log无Overfull/undefined；灰度1800px页已实际查看：Policy逐行可辨认，group多行标签、clock和能耗列完整，没有裁切或重叠。这是表的局部打印宽度检查，**不能替代Root对最终整稿全部页面的真实视觉QA**。

实际文件分词数：native正文含表从773到736；故障正文682保持682；fault表源从251到288（显式策略标签替代隐式上下行）。没有为节省篇幅缩小字体，表改为small而非旧8.5pt。

## 保留的解释边界

- matched最终bank无compatible-ahead机会，不能再称其验证100%保留或重新证明R×S；resident只有1个非空见证。
- 0.817s是跨兼容更新的Consumer事件状态驻留，非全部更新后收益、避免同长宕机或新增期限信用；末段最后同源观察右删失。
- 两个RevTrace bank各有2次必要不兼容撤回；原字符出现次数、总体匹配分母与人工CER分开。
- 旧事实重放1.36–1.81s与Owner新认证结果64.61–108.08s保持不同端点；存活worker的完成不等于替换worker已ready。
- 原no-reset长流质量和所有D2/C8失败，条件派发的低匹配比例及支持故障域都没有因重写消失。

本子任务完成；最终主图引用、Findings编号、整稿分页、冷读、匿名包和GitHub同步由Root统一收束。
