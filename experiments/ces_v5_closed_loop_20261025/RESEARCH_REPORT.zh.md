# CES V5 闭环接入与72单元GPU评测结项

日期：2026-10-25。实验ID：REVTRACE-CES-V5-CLOSED-LOOP-20261025。
冻结Runtime：`e45c66475ba1173a98b49b8c9e62f3e8cb45b333`。
证据基线：`d0529564935b4a045960645d3a00a2740c4bbaf4`。

## 结论

用户指出的两个接线缺口已经补上：**已释放后继的期限/价值回传**和**跨重规划的同身份服务义务**均进入实际Owner派发、Worker执行及提交退休回路，不再只停留在CPU原型。
同轮还接入了有界Private/Canonical双路径预测与共享GPU0子批次选择。

72个正式单元、4个试跑单元、2个付费Strict Oracle单元全部完成；正式72个单元的证书、WAL、Trusted Render、Row/Lease及实际Consumer审计通过。本地独立复算也通过。

**性能升级结论：当前冻结的完整Causal及Causal+joint均为NO-GO。**
同步Mixed下Causal的Goodput相对Fine基本持平，错峰下配对中位下降32.35%；加入GPU0 joint后进一步下降。
后继和Private组件在新控制器家族内部有局部正信号，但未弥补其与强Fine/Cost的差距。
这既不是“模块仍没接上”，也不支持“组合机制不能创新”或“原C1/C2/C3失效”的推论。

本轮没有修改论文正文、摘要、标题或投稿材料，没有重新启动Elastic rho、Grafting、V2 Selector，也没有根据结果调参替换运行。

## 1. 实现及边界

| 接入内容 | 实际实现与约束 |
|---|---|
| 后继回传 | 当前合法Parent后最多两层已释放音频义务；扣除剩余服务成本、参与候选排序和完整计划评分；未知未来Parent不构造成真实Job |
| 服务义务 | Session/epoch/Parent/Frontier/Contract身份绑定；只有实际派发增加推迟计数；保留已选后缀的经验P90完成意图；真实WAL安装退休 |
| 双路径 | 实际ACK建立已赚取收益；对真实在途Private Job预测交付，对Verify成功分支做只读exact-chain兼容性预览；未知Direct/Fallback分开建模 |
| 目标与成本 | 使用已观察Q/T的有限前缀场景比率；完整支付当前共同cut、后继Authority工作、失败Fallback和物理Lease，不免费取消旧工作 |
| GPU0动作 | 真实合法子批次选择；相同能力提供给Fine、Standard及Cost对照；不是只改变名称或行排序 |
| 安全 | 原准入、D1、A/B/C/D、WAL及单Owner条件不变；预测仅选择证据计算，不产生写权限 |

执行上限为两层后继、8个候选计划、最多两种交错及16场景；Private CDF保留质量并压缩为最多32个上端点。
这是有界顺序启发式，不是全局双GPU最优规划器。GPU1的未来展开尚不模拟尚未派发的未来GPU0工作；这是本轮发现的预测视野边界，不应把它写成已经完成的完整跨设备未来策略树。

源码、测试及日志字段的逐项对应见 `IMPLEMENTATION_COVERAGE.md`；公式及安全条件见 `ALGORITHM_EXPLANATION.zh.md`、`DESIGN_REVIEW.md`。
367个选定CPU回归在Windows与目标Linux分别通过，是同一套测试的跨环境验证，不能相加成734个独立测试。
另有独立代码/数学复核、校准复算及审计器回归，范围分别保留。

## 2. 正式协议与分母

- 双RTX3090：FP16 Proposer/GPU0、FP32 Authority/GPU1；fine=2s，rho=1，Row-complete、WAL、实际Consumer及完整成本口径共享。
- 同一16条独立音频，250.18 audio-s/run，135个请求前沿/run；同步与错峰Mixed-F2各3次fresh-process重复。
- 8个主方法形成48单元；4个共享GPU0能力副臂形成24单元。方法次序在运行前冻结。
- 主指标为第一次合法Display<=2s且耐久Commit<=8s的Audio Goodput；另报持续有效显示、认证Consumer、整run双P99、质量、回撤及成本。
- 正式共9720条前沿观测、18012.96重复audio-s；不是9720份独立声学样本。相同来源以前已用于标定/诊断，本轮不是新的held-out确认。
- 冻结故障位置相同不意味着实际暴露数相同：调度会改变哪些Proposer Job真正执行。注入、实际消费及自然故障发生率严格分开。

正式实际调用为2672次：Proposer 1146、Authority 1526。物理Batch 2556，另有116次真实Fallback模型调用。
4个试跑和2个付费Oracle单列；它们不进入正式性能的分母。

## 3. 性能结果

下表为每组三次运行的**中位数**。Goodput单位audio-s/wall-s；D99/C99单位秒；E为两张GPU的J/audio-s。

| 到达 | 方法 | Goodput | D99 | C99 | E |
|---|---|---:|---:|---:|---:|
| 同步 | Fine | 11.388 | 3.173 | 3.521 | 34.430 |
| 同步 | Cost-only | 11.105 | 3.286 | 3.501 | 34.076 |
| 同步 | Inherit | 11.327 | 3.146 | 4.758 | 33.636 |
| 同步 | Causal | 11.326 | 3.202 | 5.222 | 33.739 |
| 同步 | Cost+joint | 10.523 | 2.905 | 3.580 | 34.151 |
| 同步 | Causal+joint | 9.931 | 3.003 | 3.368 | 34.645 |
| 错峰 | Fine | 7.818 | 3.983 | 4.470 | 39.150 |
| 错峰 | Cost-only | 7.146 | 4.384 | 5.744 | 39.570 |
| 错峰 | Inherit | 4.919 | 7.674 | 7.673 | 44.828 |
| 错峰 | Causal | 5.289 | 6.838 | 8.397 | 44.620 |
| 错峰 | Cost+joint | 5.743 | 4.037 | 5.592 | 44.166 |
| 错峰 | Causal+joint | 4.951 | 8.811 | 8.809 | 46.081 |

以下为先按相同repeat计算相对变化、再取三次中位的**配对效应**，不是上述中位数之比：

| 比较 | 同步Goodput | 错峰Goodput |
|---|---:|---:|
| Causal / Fine | +0.006%（基本持平） | -32.348%（三次均负） |
| Causal / Cost-only | -0.841% | -25.988% |
| Causal+joint / Fine | -12.796%（三次均负） | -37.911%（三次均负） |
| Causal+joint / Cost+joint | -5.971% | -13.794% |

错峰Causal/Fine的三次Goodput变化为-32.348%、-36.634%、-24.945%；GPU能耗配对中位增加13.655%。
同步Causal/Fine的能耗配对中位下降0.611%，但Commit P99增加45.230%，不是无代价优势。
全部72个正式单元的整run双P99通过为0/72；不得把部分音频Goodput改称容量SLO通过。

所有正式单元最终聚合WER为2.0378457%，CER为0.6447453%；Canonical触顶准入和未完成来源均为0。
这些相等的聚合数不证明每步Token/历史相同或所有显示无损。
另有22/8892条Proposer生成触顶，36条前沿观测在认证前曾撤回，6个run的持续有效显示Goodput不同于第一次合法显示口径；这些均保留。

## 4. 新模块确实进入了在线选择

错峰Causal共有73次实际认证选择：36次包含已释放后继，28次有正Private价值预测，40次服务保护处于活动状态。
54个forced-target观察均出现在实际首批选择中。这些是相关决策观察，不是54份独立声学样本。
20个最大规划开销的冻结在线快照，跨四种新模式做CPU重放，全部规划输出字段与实际日志完全匹配。

新增机制的局部正信号也必须保留：

- 错峰Inherit/Reserved-progress：Goodput配对中位+7.357%，三次同方向；Commit P99也增加15.341%。
- 错峰Causal/Inherit：Goodput配对中位+7.040%，三次同方向；Commit P99配对中位增加18.615%。

这些说明后继与Private建模不是毫无作用，但对照仍是较弱的新控制器家族，不能据此跳过Fine/Cost宣布成功。
本轮没有“相同新规划器仅关闭service guard”的纯GPU消融；不能把旧48单元或不同Cost策略冒充该对照。
退休时推迟计数已被派发重置，不能用其为0证明从未等待；应查看实际派发与历史快照。

## 5. 为什么完整实现仍未产生净收益

### 5.1 规划计算也在消耗期限

错峰Causal的Authority规划累计中位1.468s/run，snapshot到首enqueue累计中位1.509s；单次规划P99中位158ms。
它约占整run墙钟的5.08%。Fine无此搜索开销。
CPU热点包括有界计划枚举、场景评估、反复的行CDF/时刻计算及成本预测。
现有预测从snapshot的now向前计算，未显式计入本次选择自身随后消耗的规划时间。

这是源码与实际时钟共同支持的建模缺口；但不能将1.468s直接从整run减掉，声称获得等量GPU加速。
改变时序会改变Batch组成、Private路径与后续输出。cProfile也有自身开销，且只覆盖纯choose函数，不覆盖原Owner全部上下文/日志成本。

### 5.2 实选Verify仍存在条件性低估

| 错峰实选操作 | Batch数 | 预测完整Lease均值 | 实际均值 | 实际超预测 |
|---|---:|---:|---:|---:|
| Causal Verify | 18 | 0.592s | 0.789s | +33.17% |
| Causal+joint Verify | 13 | 0.746s | 1.234s | +65.49% |
| Cost-only Verify | 16 | 0.425s | 0.573s | +34.71% |

Causal实际Fallback行18，预测约11.043；joint实际23，预测约12.536。同步Verify则零Fallback，模型反而偏保守。
这是对各方法**真正选中但不同的Batch**的校准诊断，不是同一Batch的V/G反事实；不能据此直接量化某次改选的收益。
完整计划的planned_seconds含后继，未拿它与单个首批比较。训练与诊断分别对齐完整Worker Lease、可信Render完成和实际Owner交付；没有声称测得纯kernel active time。

### 5.3 更少的Private工作次数，不等于更少的实际代价

错峰Causal的Proposer Batch中位15，Fine为21；但累计完整Lease中位分别26.680s和21.207s。
Causal三次中有2条Proposer触顶，Fine为0；Causal最长Proposer Batch达14.548s，Fine为2.389s。
不能把包含触顶行的整批成本全部归给该行，也不能把两GPU并行时间和Host时间相加。

静态代码核对表明，GPU1的未来展开支付当前和两层后继Authority成本，并读取已派发Private的剩余CDF；它没有展开“本次认证等待将怎样改变随后新启动的GPU0工作及长尾”。
GPU0另有当前ready cut选择，但不是完整的跨设备未来耦合rollout。

因此，有证据支持的是：**决策成本、条件性Verify成本误差和实际Private长尾共存，而现预测视野未覆盖全部反馈成本。**
“认证推迟导致某条Private触顶”仍只是待检验解释；本轮新增扫描未找到可直接用于该因果归因的同声明逻辑输入触顶/不触顶配对类，未用CPU重解释替代实际GPU反事实。

### 5.4 P99变好也可能丢失总体及时音频

同步Fine+shared-progress相对Fine的Display P99配对中位改善约8.02%，但Goodput下降7.72%；Causal+joint相对Causal的同步Goodput下降11.03%。
这不是“拆批一定无用”，而是本负载中优化尾部、Batch效率和按时音频量存在实测权衡。
共同能力的收益或代价不能只归给Full CES。

## 6. 安全、审计与所有失败记录

正式：72/72安全审计PASS，2672次实际调用、9720条请求前沿；本地重新从Consumer/commit/power及原参考文本计算Goodput、双P99、能耗、WER/CER和关键路径，全部对齐。
归档核验1771个有界文件及完整分块哈希，原始GPU证据继续保留在8TB；156个原Worker PID/starttick和两个GPU控制器身份均已退出。

四类工具/归档问题没有被伪装成GPU重跑或性能修复：

1. 原试跑审计器误拒绝正确的首层后继继承；保留原STOP，修正v2在同一4+2日志上复核通过。
2. 诊断器把WAL的journals容器误认成额外实验单元；v2验证WAL来源/内容后分类，所有核心CSV逐字节不变。
3. 收集器需要根目录manifest；增加与已冻结runtime manifest完全相同的元数据镜像。
4. Linux pytest临时目录含current符号链接；新收集器明确登记排除该CPU basetemp，保留测试源码、命令、日志和JUnit，不删除目录，不把fixture当GPU证据。

原失败日志、修正源码和hash均保留。`FORMAL_FREEZE_LOCAL.json`中的7c0a3b为未执行过渡记录；真实控制器以`formal_FREEZE.json`与`FORMAL_CONTROLLER_FINAL.json`的f17378为准。

## 7. 决策与下一步优先级

| 项目 | 决策 |
|---|---|
| 本轮两项CPU-only缺口的在线接入 | 完成，源码/测试/真实派发/重放支持 |
| 当前声明约束下的准入安全保持 | 本轮全部实测审计通过；沿用原信任与存储假设 |
| 完整Causal作为新的C2性能主贡献 | NO-GO |
| 当前GPU0 joint作为净系统升级 | NO-GO |
| 后继与Private组件的内部局部收益 | 保留为有条件机制证据，不能放大为胜强基线 |
| 原论文C1/C2/C3是否被否定 | 不支持这种结论 |

如果继续，优先顺序应是：

1. 对实际冻结快照做语义等价的搜索/CDF缓存和决策预算修正，将规划自耗时纳入期限判断；不预告GPU收益。
2. 针对实选Verify的分桶支持与尾部失配改进共同成本模型，并把相同模型提供给Cost-only。
3. 为未来GPU0工作与Private长尾建立可证伪的付费模型/受控对照；先确认实际机会，而不是继续加更深的预测树。

以上是由本轮证据定位的后续候选，不是已经执行或已经验证的性能修复。本轮到此冻结，不追加GPU调参、不修改正文。
只有新版本真正超过强参考且通过新的来源验证，才建议替换论文C2性能主张。

## 8. 证据位置与复核入口

本地根：`experiments/ces_v5_closed_loop_20261025`；本地`collected/`在发布包中名为`evidence/`。

- `formal_audit/`：完整证书、WAL、输入/Consumer/指标审计。
- `formal_summary/`：预冻结成对统计，三重复区间仅为有界诊断。
- `formal_independent_diagnostics_v2/`：真实关键路径、服务义务、后继激活和预测对照；v1失败保留。
- `formal_chosen_prediction_v1/`：真正派发的首批预测与物理时钟。
- `formal_cpu_snapshot_profile_v1/`：20个精确CPU重放与热点，不是GPU收益。
- `formal_proposal_tails_v1/`：8892条Proposer行及22条触顶；其中method为runtime方法，副臂须按cell标签分组。
- `analysis/`：独立本地事件、质量与能耗复算；本地目录名`local_review/`。
- `RAW_INDEX.json`、`MANIFEST.json`、`COLLECTION_TRANSPORT_INDEX.json`：原始索引、有界文件哈希及85,453,556-byte传输包验证。

原始路径：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v5_closed_loop_20261025`。
