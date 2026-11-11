# v16最终数值一致性只读审查

**结论：PASS，当前纳入main的正文、宏、表与图数据没有剩余数值must-fix。** 只读核对，没有修改论文、运行模型、控制实验或编译。审查对象为隔离写作树的实际main输入链；旧六个05文件未再纳入构建，不把其历史文字当作当前PDF声明。

本次源快照时间为2026-11-11 14:48:45 UTC。9个当前源/图数据文件的SHA见`V16_FINAL_NUMERIC_REVIEW_SNAPSHOT_v1.json`；最终N8数据锚为`FINAL_N8_SUMMARY.json`。这是数值表示与已有证据的一致性审查，不是重新测量服务。

## 1. 最终N8：摘要、引言、评估、宏和表一致

| 指标 | 证据原值 | 当前论文表示 | 核对 |
|---|---|---|---|
| 每臂全offered分母 |137.864125s|表caption137.864s|正常舍入 |
| Full/Ready信用 |129.46 /58.5s|129.460 /58.500|一致 |
| Full/Ready信用比例 |93.9040523% /42.4330840%|宏93.9/42.4，表93.90/42.43|正常舍入 |
| pooled信用差 |51.4709682pp|宏51.47pp|一致，使用未舍入值相减 |
| 整场D2/C8通过 |10/16 /0/16|10/16 /0/16|一致；不同于原任务32/32 PASS |
| Full/Ready worker occupation |223.214949712 /322.990538775s|223.215 /322.991s|一致 |
| worker相对下降 |30.8911801%|引言30.9%|一致 |
| 两板origin→确认物理drain能量 |91879.705750 /117822.717632J|91.880 /117.823kJ|一致 |
| 能量相对下降 |22.0186840%|引言/评估22.0%|一致 |

`figure_data_v16.json`的8来源×2策略×4字段（offered、credit、credit%、board J），共64项，与最终N8逐来源汇总一致；32个individual-repeat信用点也一致，容差1e-8。三个controller输入SHA与当前闭合汇总一致，元数据中的相对路径按E目录解析。图的J/audio-s由同一来源两次重复的两板能量/全offered计算，未改用有用输出分母。

八个来源与十六对重复均Full>Ready的文字与逐来源/重复表一致。主比较只取32格Full/Ready，不混入其他pilot臂或RESOURCE8。Ready-only最终有三次admitted complete-result reuse；正文已写三次。后面的pilot零命中明确限定于二来源、24格机制银行，未外推为最终N8零命中。

## 2. Core H3：6→17与12→17各守其口径

- 摘要、引言与新core图用可避免/兼容loss：6→17；评估先给总withdrawal12→17，再明确R00为6兼容＋6必要修订，二者一致。
- Core图数据为credit `[654.115,628.435,664.150,680.760]/714.110`、avoidable `[6,0,17,0]`、主对齐D+S `[150,49,267,49]`，与原H3及正式CPU内容重计相符。
- 文字信用差16.610s与52.325s正确；view-only零可避免loss和一次必要withdrawal已区分，没有称两模块都是低修订的必要条件。
- 主/替代最优对齐的267→49、266→48，以及暴露203.297→134.207、276.509→208.373，与正式结果一致。末次actual text逐来源hash相同；569被明确说明为LCP suffix retirement，未称569真实修改或人类阅读负担。

审查中指出的一处小措辞已经由Root修正：core图caption原来写“minimum code-point deletions/substitutions”，可能把主对齐D+S267误作D+S本身的最小值。当前已改为**primary minimum-distance alignment**；主/替代对齐数据无需变化。

## 3. OP及其他银行未混合

实际OP24表重核：Full与VDag均56 model-active confirmations、credit32.340125s；Ready为0复用、49 before-C、9 late-full refusals、worker82.145437991s；Full worker51.764636354s。UIR credit30.840125s，差1.5s；正文把该机会限定S0901，未将全能量差归因取消。VDag零predicate分歧被写作当前工作点结果，没有推出普遍等价或独占机制增益。

LA2段落的32.340125→31.340125/33.11625s、canonical-only30.840125s、4→0字符，以及32.740→24.403覆盖积分均匹配固定pilot日程的CPU结果；共享Full/SUP、原G不变和非线上替代系统的角色边界保留。

Resource8的两会话11.5 vs10.5/33.11625s、四会话9 vs10/66.91s及全部八场D2失败均正确。形式控制35含原27，没有写成35新增再加27。旧恢复初始化与18.6–23.9ms Consumer开销明确属于早期银行，未冒充当前NN的每调用成本。

## 4. 同一八人银行身份

当前评估明确写出：两来源pilot＋六来源后续确认；早期Conservative比较使用**同一speaker bank**、不同旧runtime，其CER13.22%和旧端点只作历史支持，不增加声学来源。图元数据也标明eight existing speakers。当前摘要/引言未写“八名从未使用过的新说话人”，未转用旧bootstrap CI或53.3pp作本轮Ready比较。尽管Full总信用129.46s与旧银行恰好相同，当前表的Ready58.5s、worker和能量均来自本轮三批结果。

本轮未提出新增实验或额外编译要求；Root可以继续现有编译/发布流程。
