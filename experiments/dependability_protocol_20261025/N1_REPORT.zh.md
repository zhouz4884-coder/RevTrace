# N1结项证据：过时发布、实际可见性与错误SLO信用分开

## 范围与身份

原冻结Row SDK2bc71af；实测新增Runtime f0e5864。2个Pilot与54个正式双3090
fresh-process服务单元，4条按旧PhaseD元数据顺序选择的完整音频，fine2s/rho3，
FP16 Proposer/GPU0、FP32 Authority/GPU1、batch返回、durable group-ready WAL、
D1与实际本地FIFO Consumer。不是54组独立音频、不是自然故障率或浏览器/网络测量。
用户追加CDE后没有中断、替换、调参或重启这组已冻结矩阵。

正式54单元完整，无STOP；原控制器与108个GPU Worker身份均已核验退出。
完整证据包5,653,418bytes，SHA256
c5ee313a7d32949d4e1d44cd83640eec7241738973c69731a58375af765f6913，
909个证据文件逐字节核验。原大资产保留8TB，不发送音频/权重/凭据。

## 已审计的事实

* 54个run的每条规范化Canonical提交历史一致：各17次提交，完整Parent、区间、
  Z/P/text相同，不只是末端WER相同；各自不同contract digest/WAL单独合法重放。
  各run末端英文WER9/226=3.9823%；纯英文池不填写虚假的中文CER0。
* 24对两种交付顺序共192个目标行比较：192/192冻结逻辑输入相同、192/192完整
  输出相同；只有180/192的实际完整Batch输入布局也相同。其余12例布局差异保留，
  不用于最强的固定张量布局因果归因，亦不从总体运行/覆盖分母删除。
* Owner单Freshness检查消融的18个run产生34次过时服务端发布；其余36个Owner
  完整保护run无该类发布。现有Consumer成功拦截covered-target，不能把34次
  发布叫34次实际用户伤害或Canonical污染。
* 发现1个实际Consumer接受的根不兼容领先视图，伴随1个2秒音频前沿的错误
  raw-dual-deadline信用。它出现在**conventional owner + snapshot Consumer消融**，
  不是完整Standard Safe Async。完整RevTrace(two_lane)与完整Standard(two_lane)
  均无该问题；带强Consumer的Owner-Freshness消融也无实际非法视图。
* 9个run的遗留event-only DisplayP99会给出<=2s，而完整合法音频前沿P99>2s。
  这是计量边界问题，不是9次新的准入故障；不能靠退休慢事件宣称服务达标。
  所有正式结论使用共同合法前沿，保留所有退休/未及时显示的音频。

## 关键真实见证及其边界

运行`standard-snapshot-ahead-authority_first-0`，来源1995-1836-0010，
proposal-2-19在8秒音频前沿生成并于8.883717s发布，实际Consumer8.884231s应用。
其出生Parent0，当前Canonical Parent1/前沿6秒；冻结输入有23token，而当前
Canonical边界有22token。两条路径在词`of`上不同，不是Parent编号不同就判错。
Snapshot仍给出可见前沿8秒，而认证前沿保持6秒。

独立反向链审计与第二份正向完整token图遍历均确认无精确当前Canonical根链。
该8秒前沿的raw显示延迟0.884231s，首次合法显示延迟3.812506s，持久提交延迟
7.004040s；所以raw错误记入2秒音频的双期限信用。认证前沿从未被篡改成8秒。
这不是“Stale-as-Fresh认证覆盖”或Canonical被污染，而是把不兼容Private当作
合法当前视图时，产生了错误的可见性和Goodput信用。

**该见证发生在所选12/14秒IPC干预之前的共享执行前缀。** 它证明真实GPU
异步可达性，不是该后续特定IPC调序的因果效果；不能用它估计IPC延迟导致故障
的概率。配对受控顺序证明covered目标的发布检查作用，二者证据分开。
两种完整协议都已包含保护，不将旧CPU漏洞说成完整当前实现仍未修复。

这也不是识别准确率下降的证明：私有文字包含`of`甚至可能更接近参考文本。
违例针对声明的认证根连续性，而非“每个不兼容假设都更差”的质量结论。
Canonical历史和末端WER在本轮不变。必要识别修正与可避免的错误新发布不得混同。

## 合法规则反事实

原实际Snapshot消费可逐字段重放。对完全相同GPU事件流，仅将Consumer解释
改为two_lane的CPU反事实，会在该点保持认证前沿6秒并标记不兼容，而不展示
该8秒私有视图。该反事实没有新GPU执行、没有新时延/能耗测量，也不冒充相同
完整部署契约的在线重跑。实际完整two_lane GPU强基线独立保留，不能删去。
文件：N1_VISIBLE_WITNESS_FORWARD_v1.json、N1_VISIBLE_WITNESS_POLICY_REPLAY_v1.json。

## 质量、成本与主张

实际完整输入/输出已由CPU独立重建：54run、3102完整行、1185实际物理Batch，
完整Z/Stop/投影/文本和Batch张量哈希核对通过；这是CPU processor/render重建，
不是3102次额外神经Oracle。全部认证/WAL/时钟审计另行通过。
GPU能量从原NVML样本独立重算，附测量窗口覆盖；两个GPU的真实Worker/model-call
区间每物理Batch只计一次。IPC hold包含在墙钟/能耗中，不伪造为模型计算。
WAL同步次数、实际write/fsync、Renderer host-wall、Consumer CPU和文件字节另列。
总Owner CPU与broker序列化CPU未独立计时，不虚报“零开销”。

GO：真实异步交错可违反服务端Freshness；仅保护Canonical或仅按当前版本/覆盖
检查，并不推出声明的精确根可见性；强Consumer/完整常规组合确实能保护。
NO-GO：自然发生率、每个旧Parent都非法、34个独立用户伤害、Canonical污染、
无条件SLO通过、独占Standard性能优势，均不由本研究支持。

本轮是协议必要性证据，不是新CES/调度胜利。新增CDE、条件性攻击与最终稿仍
按追加目标继续，本N1结项不代表P0–P5及追加任务整体完成。

## 版本纪律

N1_LOCAL_SUMMARY_v2的数值正确，但scope字段残留“无实际非法视图”的草稿假设。
v3修正文义并明确snapshot是Consumer消融；数值、原始证据和两份CSV不变。
不隐藏v2，不重跑GPU来修复元数据。独立辅助审计最初类方法绑定错误也保留，
修复后仅重跑CPU审计，未修改已测Runtime或token。
