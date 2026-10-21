# R2 冻结契约与证明义务

D0是合法完整快照替换，不因回撤被称错误。D1在owner以相同Tokenizer/rollback5/unfixed2/parse独立重建选定Z及可信parent的P和累计修订text；完整EOS/cap检查、P和UTF8字节不符在WAL前失败。新增durable text_binding包含Render输入和文本摘要，并对certificate的Z/P/parent摘要绑定；恢复重算再发布。存储、caller、Tokenizer及adapter受信任；这不是神经执行attestation，也不保证识别完整。

D-Canonical：归纳于每次canonical install。初态为空；新快照必须有成功WAL的相同session/epoch/version/transaction/F，Render从同parent+Z重建且P相同；consumer先观察commit再接收对应快照。文本篡改在WAL前拒绝。恢复以存储完整与同contract为前提，重放验证text binding。

D-Ordering：consumer保留独立certified lane，旧display_revision/旧canonical_version消息不能改写它。旧parent的临时推测不变成认证后缀。

D-Recovery：首先仅为可靠本地FIFO、单owner incarnation；restart重发最新WAL快照并初始化新的消费流。跨连接乱序消息、浏览器绘制和网络exactly-once不在本实验保证内。

D-Liveness：有限输入、公平owner和consumer、任务返回/超时、同步成功、队列最终排空时，每个成功安装的快照最终被消费。没有有界wall-time或无限流量/无限内存保证。

## 后缀决定

**字符串后缀拼接NO-GO**：现有adapter无token–audio精确对齐，LCP/最大audio frontier/generation不能证明字符串可拼。不改变Z/P以做通过率。

有界可行机制是two-lane：认证全文与完整provisional hypothesis分开呈现。仅当在同一音频边界存在与新canonical P逐token相同的中间节点，且后续节点沿相同adapter/chunk边界、generation和精确P依赖链生成，才保留该**整体临时假设**为新parent下兼容的临时view；其内容仍未认证，可能修改已有词。否则显示为失效/待重算，不计有效覆盖。既不截出音频后缀，也不拼进认证全文。

证明是状态输入替换：同边界同P与确定的adapter/chunk转换提供相同的后续条件；已有后代调用可以保持其provisional来源身份。该证明不声称FP16结果等于FP32选择，也不将偶然LCP相同当P等价。未证明节点或缺字段保守失效。

所有成本先CPU控制/真实trace回放，之后才配对GPU。队列使用独立实际CPU线程，观测perf_counter；server emit、consumer观测、GPU与WAL时钟分开。主指标包含失效后的前沿损失，不能把留在灰色归档里的文本算持续有效覆盖。
