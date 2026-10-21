# Property D：可证明的范围及反例边界

这是研究实现契约，不是论文正文或新颖性“first”声明。证明对象是认证事实及本地消费view，不是ASR transcript语义真实、完整、永不修订或浏览器体验。

## 前提

单owner；每会话至多一个native private在途；生成调用条件不可变；χ明确包含text-state投影、Tokenizer/Parser/Processor资产及软件、chunk规则、语言和预算；选定Authority/caller和依赖受信任；WAL成功同步且存储完整；本地FIFO正确传递；owner/consumer公平、有限输入。GPU numerical KV不跨调用作为未建模状态复用。

## D-Canonical：字节与准入事实对应

对新转移，先由选定Z与冻结parent独立Render得到P及text，逐项核对，然后才准备WAL和安装。发布后的session/epoch/version/transaction/F/Z/P/text摘要必须对应这次已安装事实。基础状态为空；每次转移保持该关系，因此对有限accepted history归纳成立。文本独立篡改、错误P或非法终止不能在该路径产生新的合法发布。

WAL checksum不是该语义证明；必须先有Renderer绑定。证书没有证明模型识别正确或输出完整；合法cap输出仍可能是不完整识别。恶意Authority、依赖被篡改、硬件执行attestation不由本性质覆盖。

## 私有whole-hypothesis兼容性

在同一个输入前沿F，若记录的private节点实际P与新canonical P逐token相同，且所有后代通过同χ的chunk/输入状态边按序连接、generation和在途冻结输入均能验证，则该后代可重新锚定为新canonical事实的**未认证私有后代**。

理由不是字符串前缀：相同边界上的接口状态值可替换；之后每个已执行/已冻结调用的模型相关操作数不变，仅根的版本身份重标定。因此实际旧计算不会因元数据重锚而凭空获得不同输入或未来音频。新产生的调用继续沿该私有链；它们仍需Authority才能写canonical。

这里冻结的是同一调用及其实际batch条件，不是与另一batch重执行的数值等价保证。若χ包含额外数值KV等隐藏状态，token P相等不够。若根状态不同、边断、字段缺失，必须原路径rebase/失效，不能用LCP或最大音频前沿代替证据。没有token–audio对齐，**认证字符串后缀拼接NO-GO**。

## D-Ordering：认证lane不被旧临时状态改写

认证lane只由已安装的canonical消息更新；private不写此lane。版本、epoch、contract和revision围栏将旧消息拒于状态更新之前。两个通道中whole provisional可以与certified transcript文字不同，但不能被标成已认证后缀。canonical文本本身可以因合法ASR修正而改变。

前提为同一声明的可靠FIFO/owner incarnation。新epoch须新run-start上下文；跨连接乱序、网络身份认证、持久client ACK与浏览器绘制不是这里的定理。

## D-Recovery及条件性可观察进展

成功WAL事实存活；恢复在相同χ下重放并重建text，最新认证快照可以向新消费流重新公布。单次发布前崩溃可能使原consumer尚未观察；恢复新流需实际重发，不能只凭日志存在宣称可见。

在owner与consumer公平、队列最终排空、协议数据有效的条件下，**已提交**快照最终可被观察，且不因过期private而等待其合法性。这不保证每个未来proposal都得到提交，也不保证任意负载的有界RTO或SLO。真实SIGKILL/RTO测试分别核对账本、模型初始化、首次认证消费和剩余输入排空时钟。

## 证据与证明不可互换

CPU交错/负控检验实现义务，真实GPU同内容因子实验检验收益与代价；独立WAL/Renderer/输入链/消费重算检验观察与规格的一致性。没有一个有限样本能证明任意模型、任意长度或所有故障下的系统可靠性。Standard Safe Async也能承载完整规则；等价正控不是新颖性“不可能组合”的证据。
