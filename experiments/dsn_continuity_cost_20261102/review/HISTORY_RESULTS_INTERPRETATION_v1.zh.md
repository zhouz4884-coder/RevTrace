# 持续覆盖结果的独立解释与贡献定位

日期2026-11-02。此文件只解释本地已交付的有界结果，不运行reader/hash/模型，不访问B盘。H2原分析源`aa1965c650f42eee00c6015297f1d706e6dcec23`；独立复核源`5f1ca9be7f78dde265b48f1e1d7b5bd8c856e301`，`RESULTS_H_AUDIT_REPORTED_V2/GATE.json`已PASS3/3。当前S-on银行分析源`0cce9d3feff5dba1f6b70ae17163fd4e9fd2e942`，`RESULTS_H_CURRENT_S_ON_V3/GATE.json`90/90完成、无失败；当前银行尚不与旧三条合并统计。

## 1. 得到了什么有信息量的新证据

旧S的14个Canonical point cuts，现在被原Consumer时轴上的非零持续区间支持。独立复核从原raw重建FIFO、job/P/Z/text与权限，未导入主分析器的selector、merger或积分函数；只调用原冻结Consumer兼容关系与原core申请/应用谓词，并以第二次端点分割比对整个正区间集合。

|已知正例（历史N5正常工作负载）|主报告合并gap数|同source观察内缺失wall-s|缺失面积audio-s×wall-s|新增first D2/C8信用|
|---|---:|---:|---:|---:|
|Fine / return-low / r0|11|16.835|29.408|0|
|Alternative joint / finite-overload / r1|1|0.886|1.573|0|
|Fine / return-low / r2|2|3.052|10.086|0|

这些数字描述**原实际历史view相对最大合法已登记view的离线机会**。原producer/dispatch/model/selected历史不变，额外selection/apply延迟按零处理，所以不是已部署增益或实际用户实验。三条是根据原正例选择，不是新的独立确认集；subset独立审核也不单独证明全部其它attempt没有机会。主活动全bank分母应另援引其实际gate。

新增first信用为0和持续缺口为正并不矛盾：一次按时交付之后，仍可发生稍后的失去覆盖；同一音频不能在恢复时再次获得first-delivery信用。这正是当前论文first-delivery与continued availability区别的实际支持。它不能被改称“又增加了多少D2 goodput”。

## 2. 新性质应如何定义，才不破坏现有S命题

v9当前S命题是：Canonical应用前当前whole view h若兼容且ahead，此次应用保留h不变。**无条件选全历史最大F**可能用另一个更大旧tip替换仍合法的h，改写整段文字，因此不能默默当作原命题的同一个实现。

最稳妥的扩展是：

> 当前view仍合法时保持它；当前view失效/不存在时，在该时刻已登记、未被明确撤权、仍有完整支持证据的历史结果中选择合法fallback；没有候选时返回Canonical。

在这个有限证据集合内，可以要求fallback选择完整，或选择最大frontier。它没有新增Canonical authority，不复活已fenced epoch/generation，也不是全局/永久最大合法进展或无条件活性定理。最终apply仍需原完整门。

**独立复核已消除一个风险**：旧三条的20个atomic positive pieces全部发生在actual view等于Canonical frontier时；“升级已经合法的ahead view”均为0。因而这些正例确实属于缺ahead时的fallback空间，不需要牺牲当前view不变性质来制造更大F。

其中16个atomic pieces恢复原来实际显示过的同一node；4个使用旧publication在新根下首次提供此前未覆盖音频。atomic pieces会因host到达/原事件而切分，不能将16/4解释为20个独立窗口/任务。合并gap、distinct job、source、恢复曾显示节点和首次变合法历史publication必须继续分列。

## 3. 当前90个S-on控制让主张更清楚，而不是更大

当前银行包含34个R0S1、34个R1S1、22个Alternative joint runs，来自已有core确认/服务区间合同，**不是最终native4f的新90次实验**。唯一残余是R0S1、c16 staggered、repeat1：2段缺口、1.725851s、2.981398audio-s×wall-s；首次D2/C8信用仍无变化。该run原apply-cut擦除字符281，最大历史查询的相同cut序列为280；这只是固定cut的离线比较，不是新UI完整时间轴或人类准确性。

R1S1及Alternative joint全部没有发现额外注册历史收益。这支持当前论文选择：在这些已有完整组合轨迹上，额外maxselector没有可测残余服务机会，**不应为追求新机制再开线上Max矩阵**。它不是所有运行/模型都选择完备的证明，也不意味着旧N5缺口是假的。

有价值的科学结论是：**保住当前view、从历史找回合法view、以及R与S联合后机会是否仍存在，是三个不同问题。** 本轮把它们分别测清了。组合创新仍可由实际对象、可检查义务、服务后果与公平完整实现建立，不要求独占一个索引算法；同样，不必把没有当前收益的扩展升格为第四项贡献。

## 4. 建议怎样进入论文

- 主文方法保留现有per-application连续性命题，**不加入全局最大合法进展承诺**。
- Discussion可用两三句说：历史查询确能恢复某些首次交付后缺失的覆盖，但在当前完整joint银行未发现额外收益，因此本稿采用当前view保留，不引入额外selector。旧正例与当前无残余分别指artifact。
- artifact给一幅原Consumer时轴的真实case：actual frontier、合法registered fallback、Canonical、必要mode/epoch撤权标记；图只能表示固定历史离线机会，不能画成已部署反事实。原文字身份/同F内容支持和partialEOS继续保留。
- 若主文篇幅紧，只保留性质区别和停止决定，不插三条历史数字表；论文正面证据仍是当前R×S与native完整调用。

可供root选择的英文短段（proposal，未改Paper）：

```latex
Preserving the current supported view does not ensure that every usable
registered result is selected. Historical fixed-trace checks expose
nonzero intervals in which a legal older view could restore coverage
without adding first-delivery credit. However, no further such opportunity
is found in the tested joint-retention traces. We therefore retain the
current-view rule and treat historical fallback as a scoped extension,
rather than adding another online selector.
```

该段中的“joint-retention traces”必须链接当前core90中R1S1/Alternative joint范围；不能暗示已扫全部native4f。真正部署fallback还需实际状态保留/查询/申请/Consumer代价与ACK影响，旧时轴零延迟面积不代替这些测量。

## 5. 对成本结果的衔接

历史结果已经足够决定不新开Max在线机制。接下来成本实验回答当前完整实现如何支付资格、原调用绑定、持久性和实际whole-view检查；它不需要用历史max增益“抵消”CPU成本，也不能将audio-time面积与CPU毫秒直接相减。CPU12是完整真实对象的操作足迹；NN16 off/on测观测总影响。待实际NN与独立检查结束后，再决定成本段是否有优化/边界结论。
