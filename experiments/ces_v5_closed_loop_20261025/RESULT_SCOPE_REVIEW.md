# 正式72单元：独立结果口径与证据范围复核

日期：2026-10-25。研究：`REVTRACE-CES-V5-CLOSED-LOOP-20261025`。

## 结论

本地三份预收集文件与冻结计划在单元、调用和汇总分母上互相一致。
**这是汇总交叉核验通过，不是本人重新执行了72条GPU历史的逐Token、证书、WAL或模型输入审计。**
服务器v2完整审计在其SUMMARY中报告72/72 PASS、无失败。当前新增控制器仍未展示优于强Fine/
Standard/Cost的系统收益：错峰Causal相对Fine的配对Goodput变化三次均为负。后继与双路径相对
同族弱化消融有正向点估计，但不能替代强基线比较，也不能据此宣布C2性能升级成功。

本复核没有修改原CSV、Runtime、计划、论文或测量数字，没有连接SSH、运行GPU或重新生成模型输出。
使用科学数据只读审计规则，保留原始表记录，按实际单元而非前沿数量解释重复与分母。

## 1. 实际可读的证据与暂缺证据

已读文件：

- `precollection/SUMMARY.json`：服务器v2审计的报告与逐单元检查状态。
- `precollection/SERVICE_CELLS.csv`：72个实际run的结果行。
- `precollection/PHYSICAL_COSTS.csv`：每run的Proposer/Authority两行物理成本。
- `PLAN.formal.json`：48个主比较与24个共同能力side-arm的冻结声明。
- `SOURCE_MANIFEST.json`及本地Runtime：140个文件逐一复核字节数/SHA，与干净
  `e45c66475ba1173a98b49b8c9e62f3e8cb45b333`一致。

本检查点还没有本地完整collected原始证据。因此尚未在本review内独立完成：

1. 从每条真实event/Consumer/receipt重建首次合法显示与持久提交的前沿时钟；
2. 对每个实际Job的Token/Stop、processed input、D1和完整WAL重新逐项复算；
3. 从实际Canonical文本和参考文本重新计算每源edit-distance的WER/CER分子与分母；
4. 逐run读取实际config/provenance，独立重验源顺序、种子、故障映射与实际GPU0子批启用；
5. 从本地完整resource记录重新核验当前控制器与所属PID/starttick释放。

这些不是已发现失败，而是本地证据尚未到齐的明确边界。不能用服务器SUMMARY中的PASS标签冒充
上述本地重算已经完成。

## 2. 单元完整性与实际调用数

| 检查 | 本地复算结果 |
|---|---:|
| 正式结果唯一cell、冻结计划唯一cell、SUMMARY逐cell检查 | 均为72，集合完全相同 |
| 主比较 / side-arm | 48 / 24 |
| 方法×到达方式组 | 24组，每组恰好3个fresh-process重复 |
| 每个正式run的并发 / traffic | 16 / Mixed-F2 |
| 物理成本记录 | 144，逐cell恰好proposal、authority各一行 |
| 实际模型调用 | 2,672，等于SUMMARY报告 |
| 其中Proposer / Authority调用 | 1,146 / 1,526 |
| 原始物理派发批数 | 2,556 |
| 额外真实Fallback调用 | 116，故2,556+116=2,672 |
| 验证行 / 接受行 / 拒绝与实际Fallback行 | 1,421 / 1,229 / 192 |
| 物理fsync观察次数 | 5,270，不等同于提交数 |

每个cell单独验证了以下恒等式，而非仅检查总和：

- `accepted_rows + rejected_rows = verified_rows`；
- `rejected_rows = fallback_rows = fallback_executed_rows`（本轮selective布局）；
- `Authority model calls = Authority physical batches + Fallback physical calls`；
- `Proposer model calls = Proposer physical batches`。

这里的`worker_service_s`与`physical_model_call_wall_s`是已声明的物理阶段/Worker墙钟量，
不是kernel-active时间，也不能把两卡时长或逐行时长相加当成服务关键路径。

此前4个n8 smoke serving runs与2个n4付费Strict Oracle是另外两套证据，不属于本72个正式
run。其报告调用分别为165与152，不混入2,672及正式性能比值。Oracle含额外诊断工作，不是
可部署吞吐/能耗基线。正式Strict六个run每次实际验证135行，不是那两个Oracle。

## 3. 分母、时限、质量与触顶

### 音频与前沿

72个run每个均报告135次提交、250.18秒音频、未完成source为0。故本批共有9,720个前沿
**运行观察**及18,012.96秒**音频运行观察量**。这些来自同一个重复使用的音频池、方法与到达
排列，不能写成9,720个独立声学样本、18,012.96秒新独立音频或连续五小时soak。

每行的`Goodput × run wall`均在[0, 250.18]内；P50/P95/P99递增关系与双P99布尔标记一致。
完整前沿的2秒D/8秒C指示函数尚待原始Consumer与commit时钟进行本地独立重算。

### SLO与能耗

- **整run双P99(2s/8s)通过为0/72。** 72个run的Display P99均超过2秒，16个run的
  Commit P99超过8秒。非零Audio Goodput不是整run容量SLO通过。
- 两卡功耗采样覆盖字段最低为0.9987680203，全部`strict_energy_comparison_eligible=True`。
  这说明下载表保留了覆盖门槛；积分窗口、实际功率样本和J/audio-s仍需本地原始样本复算。

### 质量与cap

- 全72行报告同一最终聚合WER **2.03784570597%**、CER **0.644745325596%**。
  目前只能核对这些已导出比例相同，不能声称已独立重算edit-distance分子，也不证明所有
  Canonical Token/历史逐比特相同或每个source错误分布相同。
- `capped_authority_admissions`合计0。SUMMARY中的72个`NO_CAP_HIT`标签，按审计代码的
  定义只检查**已提交Authority**，不能扩大为“所有Proposer和Authority生成均未触顶”。
  这三份预收集文件没有完整Proposer cap计数。
- 最终WER相同也不等于中间显示无损：18个run报告过非零可见音频回撤；36个前沿观察在认证
  前曾撤回；6个run的stable-until-certified Goodput不同于primary first-visible Goodput。
  这些是重复run观察，保留其敏感性口径，不把primary指标替换成更有利的版本。

实际消费F2的Proposer Job数在run间为6至8（60个run为8、10个为7、2个为6）。冻结的外生
Session/frontier故障映射相同，不代表每个调度都实际执行同样多的故障Job；后者会随合法派发
与前沿推进变化。这不能被描述成自然故障发生率或直接以未经对齐的拒绝数排名。

## 4. 共同能力与强基线：声明级公平核验

主比较是Fine、完整Standard Safe Async、旧Cost、Always Strict+真实Fallback、service_cost、
reserved_progress、inherit、causal，共8方法×2到达×3重复。全部主比较GPU0策略为`ready`，
因此没有为了突显新算法而移除原Fine/Standard/Cost强操作点。

24个side-arm分别为：

| side-arm | 唯一允许改变的GPU0策略 | 同输入主比较 |
|---|---|---|
| fine_shared_progress | shared_progress | fine |
| standard_shared_progress | shared_progress | standard |
| cost_joint | causal_joint | cost |
| causal_joint | causal_joint | causal |

逐个side-arm检查了同pool、method、concurrency、arrival、traffic、repeat、seed均有且仅有
一个主比较匹配，除label、proposer_policy和side_arm标记外，其余声明完全相同。
CSV中的`runtime_method`也与冻结计划逐cell一致。代码提供共同Row-complete、两GPU、D1、
准入、WAL、Consumer和实际成本路径；GPU0能力并非Causal独占，原生Fine不被强迫运行无用的
昂贵预测器来人为增加基线成本。

这项结论是冻结计划/代码与结果标签的公平交叉核验。实际每cell config/provenance和模型输入
张量尚未本地重读。特别是CSV的`proposer_order=ready`是旧排序字段，不是
`proposer_policy`，不能据此认定side-arm未开启或所有GPU0能力相同。应以真实config与
`closed-loop-proposer-choice`派发证据检验实际启用与作用次数。

### 缺少纯guard-off消融

service_cost、reserved_progress、inherit和causal均启用跨重规划服务保护。计划中没有在其余
目标、场景、动作族、校准完全相同条件下关闭guard的单因素run。旧progress/Fine/Cost并不
满足该单因素条件。因此：

- 可以报告服务保护已实现、CPU重复后置反例被修复、实际服务book合法执行；
- 不能把本批相对旧48单元的任何尾延迟变化，独占归因于guard；
- reserved_progress→inherit可检查本批后继价值增量，inherit→causal可检查本批双路径
  增量；service_cost→inherit同时改变性能目标，不能称为纯后继消融。

## 5. 性能结论需要同时保留内部正项与强基线负项

以下只列三次run的组内中位Audio Goodput（audio-s/wall-s），不是配对效应：

| 主方法 | 同步 | 错峰 |
|---|---:|---:|
| Fine | 11.388040 | 7.818262 |
| Standard | 11.304700 | 7.921359 |
| Cost | 11.104501 | 7.146414 |
| Strict+Fallback | 4.780541 | 4.050811 |
| service_cost | 10.786352 | 5.738634 |
| reserved_progress | 11.320881 | 4.733081 |
| inherit | 11.326907 | 4.918802 |
| causal | 11.326237 | 5.289208 |

按相同到达方式和repeat匹配，先计算每对`target/reference-1`，再取三对中位数：

| 比较 | 同步配对中位变化 | 错峰配对中位变化 |
|---|---:|---:|
| Causal / Fine | +0.006262% | -32.348031%（三对均负） |
| Causal / Cost | -0.841141% | -25.987939%（两负一正） |
| Inherit / Reserved | +1.517113% | +7.357067%（三对均正） |
| Causal / Inherit | -0.903875% | +7.040104%（三对均正） |
| Causal / Reserved | +0.599525% | +14.915116%（三对均正） |
| Causal-joint / Cost-joint | -5.970985% | -13.794183% |

三对run不是独立来源的大样本检验；此表没有自行生成新“显著性”结论。同步Causal/Fine的
“组中位数之比”约为-0.54%，而配对变化中位数为+0.006262%；二者统计对象不同，禁止混写。

内部消融的错峰正项说明新增预测有可测的调度影响，不应抹掉。但完整Causal仍明显落后
Fine/Standard等强基线，不能用“胜过Reserved”替代系统升级成功。新增GPU0能力也没有
自动改善Goodput：Causal-joint/Causal的同步、错峰配对中位变化分别为-11.028592%、
-7.574805%。同能力Cost-joint必须保留，不把其额外能力从强参考中撤掉。

错峰Causal的planner wall组中位数为1.468227秒，Fine约0.000065秒；这只是完整成本中的
真实差异，尚不能用汇总表把Goodput损失全部归因于Host开销、某个遗漏后继、某次Fallback或
某种Batch屏障。需要正式原始event/Worker/Consumer时钟与选择记录进行可证伪的关键路径诊断。

## 6. 研究与DSN主张的当前边界

冻结源、CPU测试、实际72单元与服务器v2审计支持“此前CPU设计已进入真实运行路径，且被测
历史保持原准入/恢复约束”的实现层结论。它们不支持“已找到优于强安全异步参考的C2算法”
这一性能主张。原C1/C3既有证据不因这个固定fine=2s、rho=1的调度扩展失败而消失，亦不
能由它重新扩大适用域。

本批用的原validation来源已参与上一轮诊断与执行profile拟合，是**复用训练/诊断来源**，
不是新的held-out或独立来源确认。不得把人工Mixed-F2压力条件与自然发生率混为一层。

后续决定须基于完整raw收集后的独立重算及原因诊断。这里不宣称穷尽该topic、保证录用、
证明所有组合无创新，或建议为制造胜出而削弱基线。正式结果应该保留，包括这次未通过强
性能升级门槛的负面证据。

## 输入身份

| 文件 | SHA256 |
|---|---|
| precollection/SERVICE_CELLS.csv | a50c8a8a668930be3d42af547c7baa3059113a453fdecfd51febf23aa3e2bd8b |
| precollection/PHYSICAL_COSTS.csv | 96cf0c0c3c5ff873314a078b1020997d09ae68c38a6af68a38435853c3a4bd89 |
| precollection/SUMMARY.json | 34d91b354fb104c906dc46ad7695e9029351b224d1b413e0bda1734f269225f2 |
| PLAN.formal.json | a21974de7dda66084ae946272b883001fecac89d95301ab11a4be4df70dd1dd5 |
| SOURCE_MANIFEST.json | 80633f359122e7a7bb379934511fe45b42d31e9adf6176015809670b14fbf81c |

审核结果：`PASS_SCOPE_AND_ARITHMETIC_CROSSCHECK_PENDING_LOCAL_RAW_REVIEW`。
