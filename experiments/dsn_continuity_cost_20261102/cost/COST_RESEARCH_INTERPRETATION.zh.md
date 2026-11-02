# 当前协议成本：研究取舍与正文候选

2026-11-02。仅解读已取回本地的正式主聚合与独立审计SUMMARY；没有运行新模型、重放reader、访问B盘或修改任何冻结源/计划/旧数据。

## 结论与论文取舍

**这轮最值得保留的增量，是最终完整协议在真实服务中的毫秒级同步成本已经被量到，并与完整原任务和实际Consumer核对连在一起。它不是一个新的加速算法，也不支持“计时开关能加速服务”。** 建议主文最多一张很小的coarse成本表和两三句；微短函数、null校准和on/off方向分析留artifact。

不建议为了这张实测足迹表再运行16格NN。表的估计对象是八个已计时真实运行中的**观察到的函数足迹**，无需把off/on差识别为因果效应。补一轮严格AB/BA可以改善“观测开销”的估计，但当前正文不主张这个量，它不会直接增加核心机制的novelty。已有16格、次序缺口、全部端点与失败应完整保留。

正文可以借这轮回答审稿人一个具体问题：**完整输入与结果、身份、整视图及同步持久化是否真的在付费执行，还是只量了一个很便宜的孤立guard？** 当前证据可以正面回答前者；不要把这项支撑再扩大为一个新贡献。

## 最值三句（英文候选，不要求全用）

> An independent recount verifies complete original states, correction decisions, returned token IDs, and actual Consumer accounting in all 16 normal trials.
>
> With synchronous persistence enabled, the observed run-mean cost is 20.35–27.25 ms per complete fact commit and 18.58–23.91 ms per whole-view Consumer application.
>
> With timing capture disabled, retained calls improve original deadline credit in all four source/repeat comparisons with the equally protected conservative policy, by 2.50–4.66 audio-seconds per run.

如果现有主评估已经充分说明原任务保持和服务收益，只采用第二句加表即可；不要为重复已有结论增加一段实验目录。第三句只是这两个旧来源上的正常态确认，不用它替换更大四来源bank、6/8与7/8，也不用它增加独立声学样本。

### 一张可直接转LaTeX的小表

均为八个计时开启的真实正常NN运行，两个已测来源、两策略、两fresh。区间是**每格调用均值的最小/最大值**，不是单次调用范围或置信区间。

| 当前实际操作 | 观察到的run-mean wall成本 / ms·call⁻¹ | 每格调用数 |
|---|---:|---:|
| Owner：完整FactStore commit | **20.35–27.25** | 17 |
| Consumer：完整whole-view apply | **18.58–23.91** | 50–51 |
| Owner：实际 `fsync` | 15.78–22.18 | 17 |
| Supervisor/Consumer：实际 `fsync` | 14.43–18.56 | 170–173 |

建议caption：*Observed costs on the complete synchronous path. Ranges span per-run means in eight instrumented normal trials on two existing inputs. Fsync is nested within the higher-level paths; rows are not additive.*

这张表的有效含义是同步IO与完整对象处理确实支付了可见成本，不能以“全部检查近乎免费”解释服务收益。17次事实同步与170–173次Supervisor侧同步也提示日志/交付路径的成本结构；但本轮没有关闭某类同步的对照，不将其差值认定为可直接删除的成本或新的性能瓶颈贡献。

## 已完成证据与归属

- 主聚合：`../history/RESULTS_C_COST_AGGREGATE_V1/SUMMARY.json`，状态 `PASS_COMPLETE_CPU12_NN16_UNSUBTRACTED_COST_ACCOUNTING`；analysis=d727336dcc88540bcbe737388b0793d7d567fb8b。
- 独立核验：`../history/RESULTS_C_COST_INDEPENDENT_V1/SUMMARY.json`，状态 `PASS_INDEPENDENT_COST_OBJECT_FOREST_AND_ENDPOINT_RECOUNT`，独立源0f2fa687…；真实task、quality、nested forest、端点与能量与主结果一致。
- 实际协议/NN源4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47；observer=3cf7cd10a3ba76958b4173aa20eb6116ac779a39；driver=b16481983674dec34e798342caf519e566a2b1cd。三角色不互相替代。
- CPU12完成真实完整对象FactStore/Consumer重放，逐字节journal和Consumer语义一致；这不是十二次新的声学或部署实验。
- 原3cf null-target校准的参考中位数为wall190ns、threadCPU2755ns、processCPU1070ns。它解释微短函数的clock-bracket floor，所有实际footprint均未扣除该值。主表不使用接近floor的identity微秒量。
- NN16的八个off/on pair完整selected program相同，质量不变，全部offered/EOS保留；真实共同能量窗口为原origin→外部确认物理model drain。没有用Owner导出完成替换物理模型释放。

## 如何理解“on反而更快”

### 先看实际工作，不先命名为噪声或优化

现有摘要足以排除一类吸引人的解释：**八个off/on pair的completed、abandoned和publication计数差全部为0。**

- Conservative每格17个completed、16个model-evaluated、0个abandoned、50个publication。
- S0908 Full-call每格18个completed、17个model-evaluated、4个ASR-prefix abandoned、51个publication。
- S0916 Full-call每格17个completed、16个model-evaluated、2个ASR-prefix abandoned、50个publication。

所以这不是“开计时后多保留/少取消了几项工作”的已观察证据。完整selected轨迹一样也不自动证明非selected调用的全部输入与位置一样；这里不越过摘要的分母。

下面只对已有标量作描述性比较。`Σworker-host`是按每worker实际job区间归并后的累计host时长，再跨worker累计；它不是关键路径或GPU kernel时间。所有差值均为on−off，单位秒。

| 来源 / 策略 / repeat | ΔΣworker-host | ΔD99 | ΔC99 |
|---|---:|---:|---:|
| S0908 / Conservative / r0 | +0.353 | +0.373 | +0.420 |
| S0908 / Conservative / r1 | −0.086 | −0.039 | −0.067 |
| S0908 / Full-call / r0 | −0.604 | −0.318 | −0.338 |
| S0908 / Full-call / r1 | −0.186 | −0.179 | −0.131 |
| S0916 / Conservative / r0 | −0.572 | −0.564 | −0.556 |
| S0916 / Conservative / r1 | −0.215 | −0.235 | −0.248 |
| S0916 / Full-call / r0 | −0.183 | −0.135 | −0.178 |
| S0916 / Full-call / r1 | +0.136 | +0.055 | −0.004 |

实际host区间变化与D99方向**8/8一致**、与C99方向**7/8一致**。特别是S0916 Conservative/r0，所有17项原选定调用均由同一full0顺序执行；host累计下降0.572s，C99下降0.556s。这里已经存在比“观测器产生新调度算法”更直接的、真实量到的解释线索：本次完整调用host耗时本身发生变化。

这仍不把原因简单叫作GPU噪声。host区间包含原调用CPU/预处理等；两个进程的新鲜执行、不同物理worker分配及实际反馈相位都可能改变它。摘要中Conservative有的pair在full1执行一小项，有的全在full0；Full-call各worker区间也改变。因此相对时序敏感性是真实对象，**但当前没有隔离哪一个因素造成了改善**。

S0916 Full-call/r1更说明总量不是关键路径：host累计增加0.136s，D99增加0.055s，而C99仅下降0.004s。它支持把总工作时间、首显与可信完成分开解释，不足以单独提出一个优化。

### 一个必须保留的设计事实：policy内次序没有反转

已冻结16行的实际顺序显示：四个Full-call pair全部是 **on→off**，四个Conservative pair全部是 **off→on**。第二repeat确实交换primary GPU并反转source/policy blocks，但`blocks.reverse()`与`(block+repeat)%2`共同使每个policy内的mode次序保持原向。

所以“Full-call四对C99都改善”还与mode/period顺序混杂。不能宣称原计划的policy内AB/BA counterbalance已实现，也不能由7/8的方向算一个代表因果效应的显著性值。完整设计记录另见 `OBSERVATION_ORDER_RECORD.zh.md`；所有计划、源码与结果原样保留。

## 是否值得新增机会门

**现在不值得开新NN门。** 原因不是预先认定这只是噪声，而是：工作计数没有新增机会，时长方向已有实际host区间变化支持，且mode顺序未隔离；用这组结果设计“观测式pacing算法”会把一个未识别的关联包装成机制。为不进入正文的observer开销重新做16格，收益也不足。

若Root希望把解释收口，可只取三个pair的有界逐job ledger，零模型调用：

1. S0916 Conservative/r0：几乎一比一的host/C99变化，作为普通执行耗时解释的控制；
2. S0908 Full-call/r0：最大实际信用变化+1s，检查同数量工作是否存在不同的输入/worker分配及已确认父状态等待；
3. S0916 Full-call/r1：host增、C99几乎不变、D99变坏，定位重叠和交付时钟的区别。

每格只需job UID、slot/incarnation、完整start SHA、start/targetF、dispatch/worker-begin/end、selected durable-sync/install、对应实际Consumer及原17个frontier端点；promotion和abandon的原UID/实际时刻单列。所有时钟相对原origin，不能把sent当Owner-receipt。无需拿模型文件、张量、全文或重跑完整reader。

只有它显示一个**可保持原任务与全部安全条件、重复出现且足够大的合法工作等待窗口**，又不能仅由实际调用时长/不同输入解释，才考虑事前冻结一个小型新机会门。否则将其作为当前系统的timing sensitivity收束。当前更有竞争力的动作是把已有机制、真实保留对象和完整协议付费成本写清，而不是再增加一个pacing分支。

## 最终建议

主文保留coarse footprint的一个小表或第二句；CPU12、null与on/off详细比较放artifact。不要把7/8改善写为贡献、不要新增“无开销”结论，也不要因计时floor给正文再堆一组免责声明。完整结果与设计事实仍可查，叙事聚焦于原贡献。
