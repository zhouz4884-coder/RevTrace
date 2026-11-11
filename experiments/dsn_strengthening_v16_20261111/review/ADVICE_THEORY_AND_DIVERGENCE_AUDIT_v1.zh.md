# 新建议的理论与divergence审计

2026-11-11。只读附件3708、外部`analysis/divergence_v1`四文件及既有冻结规格/控制；没有执行其脚本、重算银行、生成模型结果、改source/CURRENT或开启实验。按用户最新收束要求，当前已启动的最后16格之后不加实验；下列“需要检查”是主张成立条件，不是新队列。

## 1. 可保留的核心：信息限制必须写成精确的条件命题

设H为允许的协议历史，j有不变完整输入s，O(h,j)是控制器实际允许看到的证据。仅在已有真实同frontier输入状态时定义二值E：相等为confirmed，不等为refuted；UNKNOWN不在这个二值域内，更不是false。

**观察受限引理。** 若存在h+、h−∈H，使`O(h+,j)=O(h−,j)`而`E(h+,j)=confirmed`、`E(h−,j)=refuted`，则没有只依赖O的即时二值eligibility classifier能够同时sound和complete。证明：同一个O必须给同一个值，两个相反E至少错一个。若进一步强制该时刻只能“不可撤销地discard”或“立即使用且禁止后续验证”，便分别损失h+合法工作或在h−错误使用。

**必须保留的逃逸路径。** 允许retain两者、输出pending、等待更完整witness、在AU处再验证，就没有上述强制两难。safe UIR恰恰允许计算跑完但仍做完整输入/AU/SUP；不能用引理宣称它必须discard合法结果或提交非法结果。引理也不单独推出延迟/能耗收益。

“birth version/ancestor fingerprint”不是足够明确的O。若version ID唯一绑定完整actual input，它可以携带所需witness，属于该引理前提之外的实现。实际强DependencyVersioned先调用FullSpec完整输入classifier，且expected-parent用完整FeedbackCut绑定；它不是纯粗版本观察器。其同效与witness充分性相容，**不是信息引理被实验验证**。

一个有限两历史实例可用同一job的frozen start与birth/冻结祖先、同一frontier/ordinal version，而让真实同F父cut不同；但O必须明确排除其完整状态或注入式hash。既有规格允许原C/U两种选择，可表达这种差异。状态空间H、O的字段与这对历史的同O关系尚未新增机械检查；当前没有据此声称实际NN3自然出现了该两历史pair。逻辑引理的证明与真实原程序可达性是两层。

## 2. 已有可执行反例：连续selected链不强迫birth-parent gap=1

最有价值的现成方法案例是冻结`aa9db5c2396b76d9b50f5281fa4a68b54aca844a`的`formal_source_dev/test_model.py:58–70`，named control：

`test_unknown_future_input_survives_ancestor_loss_then_converges`。

该控制已包含在既有35控件PASS中；**本次只是逐行解释，没有执行新检查**。模型每个cut为`(frontier,opaque-state-bit)`；原调用按`end.state=(start.state+choice)%2`取允许后继。两worker、三frontier、四次发起的动作如下：

| 步 | 原job/动作 | 结果与实际selected root |
|---|---|---|
| 0 | A=j0/w0从P0=(0,0)运行；ASR预测Q1=(1,0)。B=j1/w1从Q1运行 | root仍P0；两个原完整调用身份冻结 |
| 1 | `full(B,choice=0)`先于A完成，得到P2=(2,0)，放入future full buffer | B的完整输入Q1尚未确认，不能selected |
| 2 | 已空闲w1发起C=j2，start=P2、target3，C的birth仍P0；预测Q3=(3,1) | C完整输入尚为UNKNOWN；不是B结果已被选中 |
| 3 | `commit(full(A,choice=1))`产生P1=(1,1) | 合法selected边P0→P1；Q1≠P1，故B输入refuted，但C在F2的完整输入仍UNKNOWN |
| 4 | 变异“ancestor mismatch取消C”被控制断言拒绝 | 更早Q1失配不证明未来P2输入失配 |
| 5 | w0发起D=j3，从真实P1执行`choice=1`，得到P2=(2,0)并selected | D以原完整call建立P1→P2；C的原冻结start现在CONFIRMED |
| 6 | C原call完成`choice=0`得到P3=(3,0)，经实际parent检查后selected | 最终selected序列P0→P1→P2→P3，job顺序A、D、C；C birth始终P0 |

**三个直接含义：**

* C的birth-parent索引差是2，所有selected frontier仍连续，没有skip、rollback或跨会话祖先。B完成释放物理worker便可让grandchild先发起；“规范链无洞→gap1”被这个有限协议见证直接否定。
* B.end与后来真实P2相同也不授予B选择权：B.start=Q1已失效，实际原D才建立selected P2。C只因**自己的完整输入**后来等于P2而可用，且应使用其原完整C结果P3，不是预测Q3。这把EL、原FullCall AU与结果身份具体连起来。
* B在future buffer中出现过但从未selected，所以**ready admission不等于ready reuse**。这个case不要求一次ready结果命中。零ready命中不能单独证明没有释放worker发起更远后继。

该案例是允许关系上的**有限符号协议见证**，不是自然GPU发生率、所有原模型均可收敛或已发现NN3性能独占收益。该test不执行实际Consumer应用；若旧whole view包含Q1，它在P1处需要独立SUP拒绝，而C输入仍UNKNOWN。Consumer是否实际展示过该路径与计算对象是否失去祖先支持必须分别计量。

实际NN3 `versioned_policy.py:167–220`也没有`parent_index−birth_index==1`的保留条件。没有ancestor反证时，任意多次匹配expected-parent handover均可保留；特有分歧是**冻结祖先已refuted而该job完整start未refuted**，并保留sticky fence到后续收敛。gap≥2本身既不充分也不等价于该分歧；“ancestor未refuted但start refuted”一象限里两个实际实现都因共享classifier拒绝。

## 3. 不能把两个零或两个时间点强接成定理

1. **无Consumer withdrawal不推出无计算祖先refutation。** withdrawal只涉及实际被选中、到达且仍显示的whole view；未被显示、非当前view、已被覆盖或没有非空ahead文本的计算分支仍可失去祖先支持。反向也不成立：支持/用途/物理状态不同。二者在本bank同时为0只能各自报告。
2. **install-sampled pending=0不等于运行中从无UNKNOWN。** 新Fullcall在父安装前已执行的56个兼容确认对象，之前就可能是pending。290个profile是规定采样边界下的决策截面，不是所有dispatch/等待瞬间的穷尽。
3. **92次历史gap1若经正式复核，可作经验结构描述，不能变成无限可达性结论。** 还需区分birth dispatch、父terminal、Owner验证/安装、actual Consumer；慢于两步不必产生深链，但也不排除future buffer先释放slot产生深链。
4. **strict-birth recorded promotions=0不是独立验证gap1。** 策略按定义拒绝旧birth，且自身refresh路径不进行同样promotion记账；任何正gap都可能被拒绝，不特指gap1。新旧bank/source/执行合同也不同。aggregate credit同为12不能推出实际schedule或资源等价。
5. **69.017是原完整调用worker构成，不是丢掉/节省的已执行前缀。** 已正式ledger给出确认前约22–24个累计job-seconds；68.308是含ASR/C/U/callback的infer同步墙钟，不是“纯神经/GPU active”。不能沿用外部旧label或跨schedule删除69秒求收益。

## 4. 外部四文件的状态与源码问题

以下均位于`analysis/divergence_v1`，不是本轮新冻结/独立正式实验。静态核查发现没有独立完整source commit/clean manifest/bundle、ID/config/env/RUN_RECORD/8TB raw/gate链；代码main只记两个汇总输入hash，没有逐个绑定实际读取的24份profiles/Consumer事件和8份canonical histories并前后验证。Part B还使用`analysis/gpu_ledger_v1`外部旧ledger，而非已完成的正式ledger v2。

| 文件 | 当前SHA256（仅文件身份，不是结果认证） |
|---|---|
| compute_divergence.py |741b42d9c327128f46f81a6bd8641deca3326ff49d6fd672c0a0b5f1e77ca250|
| DIVERGENCE_AUDIT_V1.json |6e921635f39077df9ebdf4c91f2b78729e011b3cb7c73f2449331535c1c25c19|
| DIVERGENCE_JOBS_V1.jsonl |310c3deb6069c5ad3baf176f06b58ec7697cbced8dad545631b9946efdcda6c0|
| DIVERGENCE_REPORT.zh.md |635cdd60cccdbe12093c248a2316d5bce1b07db9a4daf62ce5c6320b7ccf14c0|

源码概念错误包括把实际DependencyVersioned错写成gap1规则，把fullcall错写成“仅confirmed才retain”（pending也retain）；根据Consumer事件kind推ancestor因果，且该文件事件schema并不保证这个kind；per-arm字段解析夹带sourceID。即使某些数字恰重现既有官方输出，也不是一套独立理论交叉验证。四文件保留作外来探索/建议来源，不能直接作为正式新结果或论文定理证据。

## 5. 真正有用的后续检查条件（当前不新执行）

如果以后要新增正式理论/可达性主张，至少需：精确定义O及其能否访问完整输入digest；从实际dispatch/frozen dependency和**GENESIS+每个原fact**重建完整前缀；在原两worker/单writer/accepted target/ahead bound下显式保留future-buffer admission/slot释放动作；检查h+/h−同O且相反完整输入判断；分别允许wait/retain/AU的控制与强制立即commit/discard控制；对strong输入绑定Vdag按实际代码而非gap替身比较；把当前/pending/refuted、后来合法AU、Consumer h支持与真实paid work分列。

旧35中的上面case已经足以否定“无洞强迫gap1”，不需要现在追加实验来凑控制数。实际NN3若无祖先分歧，依既有v5接受这一自然机会/效果边界，不通过跳frontier、rollback canonical、跨session共享祖先制造有利洞；这些改变原task/选择与故障合同，不能加入本轮来争胜。

## 6. 给Master的决定

保留“信息有限时需要更细witness”的条件知识、原call状态收敛案例、共同AU/SUP下的多实现与实际合法在飞收益。拒绝把Vdag tie当定理验证或全局无用证明，拒绝制造洞。论文应展示**一个原完整调用在何时可继续、何时可selected、何时whole view仍可读**的具体协议与动作归纳，而不是只有三个谓词名；一般引理、符号见证、源码守卫、正式自然trace各自标边界。

当前工作是结束已启动最后16格并整合v16正文/证据，**不新增实验分支**。建议中的停止与收束意识值得保留，但“所有将来96格必然同一0”等结构断言不进入Master结论。
