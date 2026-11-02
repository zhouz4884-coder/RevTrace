# HISTORY_V1控制失败：独立只读诊断

日期2026-11-02。正式源`bf81d68a81bd84375fb7f4b2029be02398cfbab1`；`controls/HISTORY_V1/GATE.json`为`FAIL_FROZEN_CPU_CONTROLS`，15tests、exit1、source clean、0model calls。STDERR包含7ERROR和2FAIL，正式历史bank尚未启动。

本次不运行fixture/reader，不改源/identity gate；只读失败收据与当前对应源码。已重核工作副本字节与冻结manifest相同：

- `history_analysis.py` SHA=`d1a38362552f6867b27ee2128e833ef38b27645994c1f1dcac0e162028e505ad`；
- `reference_view.py` SHA=`aa123b0912a6d73a36a5b38f3ab1a4c1d65597813a8891eaaed69addf595153c`；
- `test_history_analysis.py` SHA=`4d4d77f9ad421c0a3dd6ee98a91d23ca0e1a8480a666e9ef460c6557b0b72ee8`。

## 诊断：analysis污染了基线状态；fixture不应改

`reference_view.py:32`的初始Consumer state没有`Psha`，故第一批version0记录的`certified_P_sha256=s.get('Psha')`为None，直到实际Canonical应用才在51行写入选定projection。fixture在`test_history_analysis.py:76-83`使用未被analysis修改的原EnvelopeView逐事件生成Consumer记录；A、B、C三条private publication之前没有Canonical，因此它们记录的certified P均为None，这是原格式/原语义，不是漏填empty hash。

`history_analysis.py:346`的`state=view.states[sid]`取得真实reference状态的别名；347–348行为计算genesis支持，直接写`state['Psha']=digest_tokens(())`。过程如下：

1. A的重放和fixture原记录都输出certifiedP=None，当前identity检查通过。
2. analysis在A之后将query用的empty-root projection写进了reference基线state。
3. 原EnvelopeView重放B时从被污染state读取certifiedP=emptyhash，但fixture原B仍为None。
4. 新增完整身份门正确在Consumer row1拒绝；旧四个frontier/text字段相同，所以早期窄检查未能发现该分析器缺陷。

因此root的怀疑成立。不能将None与emptyhash视为等价跳过检查，也不能修改fixture输出让它跟随analysis；这都会隐藏“未安装事实”与“查询时采用已知genesis输入”的对象差异。

两项FAIL的期望分别是`immutable result binding`和`before host receipt`，但被同一提前发生的certifiedP错误挡住，故regex不匹配。它们目前并不构成另外两个已经确认的语义机制缺陷；修复后仍需正式跑完原15控制，才能知道是否存在后续问题。

## 最小修复建议与验收边界

- 把`view.states[sid]`保持只读，构造单独`query_state=dict(raw_state)`；仅在查询副本中表示已知genesis的empty projection。当前selector、compatibility与worker绑定代码只读nodes，浅副本足以隔离这个顶层字段修改；若后续helper修改nodes/tips，则应单独复制或使用不可变query对象。
- 基线身份检查仍逐字段执行，保留None/emptyhash的区别。不要修改原reference_view、原fixture Consumer记录或冻结V1包。
- 新增直接控制：genesis查询后，reference状态及下一条version0 Consumer certifiedP仍未改变；在Canonical真正到达之后才出现其选定projection。原tamper/未来host/最终EOS/同timestamp控制全部保留。
- 这是analysis实现缺陷，非数据、神经精度、原Consumer或科学假设失败。正式bank未启动，未产生可宣称的正/负持续面积。新修复必须新commit/manifest/config身份并重跑控制；不得将V2通过贴回V1。

结论已分别通知root和历史分析agent。成本V1控制是否通过属于独立活动，不因历史分析失败而被重标。
