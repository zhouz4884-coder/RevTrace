# H1/H3：持续合法覆盖分析的研究判断

本报告解释已经完成的原盘CPU分析，不启动新模型、reader、全量hash或远端任务。NN成本窗口独占期间只读取了本地有界summary与旧元数据。分析source V3：`0cce9d3feff5dba1f6b70ae17163fd4e9fd2e942`；V2正例与独立复核身份分开保留。这里的view selection是在固定原producer/模型历史上的离线重放，不能当新部署Goodput。

## 结论

**结果有帮助，而且帮助是研究方向上的纠偏。** 旧的“首次D2信用没有增加”确实漏掉了一种真实持续可用价值：历史已登记且仍合法的view在原Consumer时间轴上可以填补非零空窗。但补查当前真正S-on银行后，残余只出现在计算保留关闭的R0S1中；当前joint与完整正控没有残余。最合适的论文取舍是加强“计算保留与消费保留共同维持合法服务”的主线，把历史最大合法view选择作为完成性扩展和边界证据，**不新增一个独占索引/调度主贡献，也不为这个小残余再开启selector线上升级**。

## 1. 旧目标淘汰的机会，重新计量后不是零

`RESULTS_H_ALL_V3/SUMMARY.json` 保留N5的151次、CK5的136次原attempt：287/287处理完，218条具备完整Worker绑定并通过核验；另69条虽有Private登记记录但缺完整Worker结果，保持censored/UNKNOWN，不能算零机会。N5/CK5分别完整核验128/90；缺失23/46，不能把90条CK5的零扩展为136条确定零。

所有已冻结输入SHA在前后检查相同。22个V3命名CPU控制通过；V1的baseline/query共用状态错误及15控件失败保留，V2/V3以新源身份修复，未将新commit贴回旧失败。

三个旧N5正常运行再次给出原canonical cut机会11/1/2，当前完整联合权限检查均接受其选中原job/P/Z/text。按原实际Consumer时钟，得到：

| 原运行 | 合并后gap段 | session缺失wall-s | audio-s×wall-s缺失area | 每run去重缺失audio-s |
|---|---:|---:|---:|---:|
| `fine_fair-return_low-r0` | 11 | 16.834954 | 29.407668 | 17.315 |
| `standard_fair-finite_overload-r1` | 1 | 0.886266 | 1.573122 | 1.775 |
| `fine_fair-return_low-r2` | 2 | 3.051721 | 10.085861 | 4.000 |

这些都是session观察窗口内的量；没有依赖末尾global-prefix延伸制造收益。wall-s是不同session缺口时长的描述性加总，不是一个用户连续停顿时长；audio去重也只在每条实际run内，不能把复用来源跨重复再说成新独立内容。

第一条run除11个canonical trigger外还出现3个display trigger；17个正clock pieces经合并得到11段。故原14个canonical point与新14个合并gap段**不能预先一一等同**，这次恰好数量相同不是计量定义。部分片段恢复曾实际显示的原node，部分是旧publication在新根下首次提供合法音频覆盖，不能统称“14个用户已见view被恢复”。

包含fractional EOS后，三条run的首次D2/C8信用依然不增加。这是一个干净的反例：**首次及时交付量相同，持续可用性仍可不同**。不再需要把恢复旧view重新包装成新的first-display credit。

V3还报告同一原apply-cut序列的文字代价：原/选择后擦除字符分别1106/1070、757/756、855/809；未发现equal-max-frontier不同text的tie。这里没有显示出增加字符擦除的代价，但这不是逐词准确率或完整部署UI保证，也不包括隐式资格边界上的所有文字切换。未对未对齐的中间视图计算假前缀WER。

旧V2三个正例已由另一个冻结CPU实现独立复核：source `5f1ca9be7f78dde265b48f1e1d7b5bd8c856e301`，见 `RESULTS_H_AUDIT_REPORTED_V2/SUMMARY.json`。它不是额外神经重复或独立新来源。

## 2. 当前S-on结果决定它应该放在论文哪里

`RESULTS_H_CURRENT_S_ON_V3/SUMMARY.json`：当前90/90个真实S-on cell的原FIFO/root/text/可用身份字段完整匹配，0分析失败，原输入前后SHA一致。分母是confirmation66 + service-stability18 + midpoint6；不是全部158个cell，也不包括68个S-off snapshot对照。

| 当前S-on类别 | cell数 | registered最大合法view的剩余正机会 |
|---|---:|---|
| R1S1 joint | 34 | 0 |
| Alternative/full joint正控 | 22 | 0 |
| R0S1 view-only | 34 | 仅1个cell，2段 |

唯一非零是 `stability-c16-staggered-r0_s1-r1/attempt0`：

- 2段，3个clock pieces；缺失wall **1.725851s**，area **2.981398 audio-s×wall-s**，每run去重缺失音频 **2.905s**。
- 两个触发均为canonical application；其片段分类为“旧登记publication新提供合法音频覆盖”，不是此前用户已见同一node的恢复。
- 原/选择后apply-cut擦除字符281/280；首次D2/C8覆盖保持 **157.58/250.18s**，没有新first-credit。
- 这仍是固定原producer历史的离线机会，不是实际新增1.726s线上交付，更不是额外2.905s按时覆盖。

**自己的判断：这是对联合设计更有利的结果。** 简单地保留更多历史，并没有在当前joint/完整正控之后找到尚待修补的普遍缺口。残余集中于关闭R的情况，与“单独消费保留不等于完整联合协调”一致；但一次配对观察不能进一步升格为“R必然消除所有历史孤立”的因果定理。

普通scan与普通index选中原ID同效是正确的强控制。它说明不该主张新索引算法，不妨碍把合法已登记view的完成性作为系统性质。当前主文应继续以已有强2×2、真实Consumer和保留/执行协议为中心。

## 3. 建议写入、建议保留于工件的内容

正文可以增加一句很短的独立观察，放在持续可用端点或Scope附近：

> A first-delivery deadline does not capture revision-time availability: fixed-history replay found nonzero coverage gaps even when no additional interval could earn first-delivery credit. In the current S-enabled bank, the residual occurred only with computation retention disabled; joint retention and its full positive control had no observed residual.

精确表格和69条UNKNOWN放补充材料/工件。无需把整套历史selector当成新的主方法；11页正文不宜增加第三套主性能图。

若未来真的集成历史恢复，应保留当前命题：当前合法ahead view优先保持；只有它不合法/不存在时，才从原已登记、未撤权且joint-admissible集合选择fallback。无条件max-frontier若在当前h合法时换成更大的旧tip，可能不满足“h整视图保持不变”的原命题；离线max-reg机会上界与最终在线策略不能混写。

## 4. 不继续扩实验的理由与具体后续

本轮目的已经完成：旧first-credit目标漏掉的持续价值被真正量化，current-S之后有没有实际剩余也得到90个cell的回答。现在继续为selector扩模型/负载，收益不足以超过完善当前论文证据链。NN16同合同成本试验完成后，应把成本、原joint服务和这里的边界组织起来写稿。

NN独占窗口解除后，只需取回4条正例的有界GAPS/CUTS/INPUTS与独立复核输出，用于确认各段F_actual等于/大于Canonical、持续期端点、实际node分类及原raw定位。需要的文件清单另存 `BOUNDED_GAP_DOWNLOAD_REQUEST.json`，本报告编写期间未访问B盘或下载。

first-D2/C8辅助输出在故障/恢复attempt不能跨attempt直接累加为整episode信用：先前first-view历史可能在另一Consumer文件，sessions也包含整个计划输入。本文使用的三个旧正例和90当前cell都为完整正常运行；全287attempt主要承担观察前缀分母和missing-evidence边界。
