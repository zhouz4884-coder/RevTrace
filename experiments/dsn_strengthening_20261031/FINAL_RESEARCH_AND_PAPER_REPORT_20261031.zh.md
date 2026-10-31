# RevTrace：2026-10-31 补强结果与论文 v2

**本轮完整范围已完成。** 44个真实NN trial、70个请求实例、1190个原程序状态转换（含原buffer-only路径）经独立重算。原模型、C/U和4f核心59文件未为凑正结果而改写；编排、时序注入和分析器分别冻结。没有会议投稿。

## 我的判断

这轮最实质的提升，是把“合法保留”推进到**最终可靠实现上可复查的服务机会**，并补齐**已接收完整计算结果跨producer死亡**的关键交错。中心仍是完整输入资格、原选择权威、整个已消费视图支持的联合。成熟原语不否定此组合的贡献；自建完整正控同效支持设计可达性。

新证据同时纠正了旧语境：bdfa的8/8不是4f的8/8；进展合法不等于每次请求满足期限；输入相同不等于物理权限仍在或实际使用。正文据数据重写，而不是只ADD表格保住旧强数字。

## 完成的工作

| 范围 | 主要结果 | 明确边界 |
|---|---|---|
| 原36格actual-dispatch重配，0新NN、67CPU控、725输入前后SHA | 5529实际dispatch；条件1901=360最终完整input相同+1541反证，0未决 | 不是354/366，也不是409/457的补数；不得池化为生产确认率 |
| 同条件版本配对32trial、544原转换 | bdfa Full8/8，4f Full6/8，两版Cons0/8。4f信用65.821625/66.33975s，对照30s | 4个旧来源的matched regression，不是新的独立声学确认；两失败为S0908 EOS D2 |
| 常驻4trial、16请求、272原转换 | 每trial两worker只load一次、PID连续。Full7/8请求过原D2/C8，对照0/8；信用64.118875对31s | 四个独立文件EOS请求、closed-loop；不是在线VAD/单条长录音/开放到达容量 |
| 完整buffer跨producer死，2正2负、102原转换 | 原任务/ref/clock全过；新冻结reader重审证实2正控原UID/birth/inc安装消费，2负控实际父输入不同而拒绝；正控有后续请求 | 原4eb审计/CLI/watchdog/compound FAIL原样保留；新0NN机制证据与原执行状态分开 |
| 两client原4f观察probe4trial、272原转换、280派发 | 两rep均有A新推测排在B已ready必要work前，实际7/3次；B C99惩罚1.799878s/0.132839s | 后一rep未过事前重复性门，最终NO-GO；不开发新策略/不扫来源或相位。16请求联合D2/C8全部失败、C8均零miss |

配对共用模型、FP32、warmup、allocator、GPU轮换和外部观察。Full跨版本D99有3对更快、5对更慢，均值差+0.076108s；median接近不代表等价。最终Full相对最终Cons的共同模型drain双板能耗低6.52%；相对早期Full则高10.61%。认证EOS是另一终点，原source-specific service end也不同，不能硬拼能耗。常驻第二fresh的S0908 D99=2.228824s，保留该失守，不称8/8或持续SLO保证。

## 原日志增加的知识

条件input最终相同按证据层分列：正常短流40/57、受控fault58/90、两个无reset压力来源96/924与166/830。总体18.94%被坏长流主导。360个live确认job中354成为durable事实、352有原Owner安装记录、354被Consumer用到：2个durable前Owner死亡和4个worker死亡解释6个未选；另外2个durable后Owner死亡事实经恢复首次消费。确认、authority、选择、安装与消费不是一个计数。

全部8个旧长流里，实际D/C超限和宽松offline excess-length下界先于trim后448条件；不能把638.48%/251.53% CER唯一归因到448，也不能把该oracle叫在线prefixCER。旧无reset失败未被新EOS合同覆盖。两个worker ready发送仅差0.389–39.560ms，且缺精确Owner接收时刻，不支持为此改恢复实现。

## buffer原失败怎样处理

原fixture `4eb03d6f4f9a918cce693c979e9cfa07e3d6bb28` 的四次神经执行完整原任务通过；posthoc检查器把两个物理READY错键成 `(None,ready)`，导致原BUFFER/CLI/watchdog/compound失败。新reader `b8670073141a94a550abe5113222a508b63b5624` 只修审计及其控制，9个执行文件逐字节相同；正式31CPU控及零NN分析对全四格raw/watchdog前后hash不变重审。原失败一个未改，也没有仅为旧CLI翻绿重跑四次GPU。

精确记录：[R1总门/SHA](FINAL_R1_EXECUTION_RECORD_20261031.json)、[R1报告](FINAL_R1_EXECUTION_REPORT_20261031.zh.md)、[新机会总门/SHA](INTERFERENCE_FINAL_EXECUTION_RECORD_v1.json)、[全部A/B指标和原行](INTERFERENCE_FINAL_REPORT_v1.zh.md)。独立重算1190状态/C/IDs、每请求clock及probe派发/lease/view；1262原文件348155321B前后SHA一致。所有大raw、模型、语音、环境、缓存仅留既有8TB，Git只收有界证据。

## 选择与收束

最终因果线为：计算保留仍丢进展的反例→完整input与whole-view两个见证→原C/U完整调用→失效下已取得成果的资格→最终实现服务机会及边界。主native表改为matched32，新增常驻请求与完整buffer正负控；旧K24/旧normal重复细数压缩。21个引用只补必要的refinement/RPC归属，不凑30。selected-prefix stutter不等于完整UI行为等价。

额外probe的实际倒置未在两rep稳定造成预写幅度的损害，所以停止该分支，不把它包装成已验证的准入控制器或多会话公平性。这不是所有项都成功的故事；当前主张所需的高价值缺口已经有完整、可复查的正负结果，继续横向展开会分散论文。我据此转入最终稿与交付。

新稿：[PDF](../../Paper_DSN/revisions/20261031_dsn2027_release_v2/main.pdf)、[匿名源包](../../Paper_DSN/revisions/20261031_dsn2027_release_v2/RevTrace_DSN2027_anonymous_source_v2.zip)。11技术页+1参考文献页，131词摘要、21引用、3图3表；全部12页由Root实际查看，23字体全嵌入，无Type3/溢出/未定义引用。[最终QA/打包](../dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v2.json)。旧v1及全部失败链保留。

PDF SHA256 `a91618cc80ca5649ac1ffd118fb08188b2693d903ccd69750b533c4c7b1dbb32`；ZIP SHA256 `8b704826835d7d51a167cb29ddcca1c2af165ab79a41006290eaf3f3a18997ce`。Git交付阶段`dsn2027_strengthening_20261031_release_v2`，普通push并逐blob/远端main校验；archive提交不作为NN源码。会议投稿未执行，录用不能预先保证。
