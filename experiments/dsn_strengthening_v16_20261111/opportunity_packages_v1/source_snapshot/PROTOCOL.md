# PILOT24机会审计：固定v5定义，不重排调度

本实现依照Root在任何新serving outcome前冻结的
`PILOT_OPPORTUNITY_AND_INTERPRETATION_v5.json`，不是新增GPU结果。代码在pilot
运行期间仅作者化/冻结，作者不读live cell结果；正式CPU测试和raw读取必须等待Root
在pilot结束后提供idle window。完整原始结果、逐decision和Consumer重建留8TB。

只接纳NN de0936/66、driver f367/20和完整24格计划SHA2ceea09f...。
每格固定Source/arm/repeat/config hash、原500ms/8000sample和partial EOS、全部offered
音频。读取actual NN的scan/fact_audit/reference_audit和原端点纯函数，byte-reuse
f367 job_accounting；不调用analyze_trial写回原raw、不repair WAL。

关键层次：

1. 每次ACTUAL canonical install，重建当时仍tracked的live/Owner-ready job。
   原串行dispatch/complete-receipt/install序号定义边界；异常终结保留原时钟界。
   witness只按实际已发生install前缀更新，禁止读未来cut到当前predicate。
2. 精确complete-start未被反证、未covered时保留，与较早frozen ancestor已反证后
   dependency-version永久fence分别判断。首次祖先反证时记录sticky shadow fence；
   单列pending、当前confirmed、后来实际selected、后来refuted/refused等。shadow只在
   actual trace上比较predicate，不生成另一个schedule，更不折成audio-seconds。
3. 普通direct compatible handover两策略都保留，另列，不能把所有promotion当差异。
   model-active必须有actual completed original record的native_model_evaluated=true且
   model_start<=install<model_end。queued、Owner-ready、worker前/后infer、physical
   completed但Owner未admit、缺infer timer分别列；abandon的ASR timer缺测不是0。
4. Consumer按实际publication与fact、完整BranchStep链重建，区分非空visible与仅内部
   ahead，compatible support preservation与必要撤回；缺失证据保持missing。gap只量到
   同一root后首次实际恢复或下一canonical，截断/删失显式，不更改首次D2/C8 credit。
5. Owner ready-bank复用按实际buffered完整receipt与install顺序，不以物理model_end
   判ready。Ready0是有效结果，不能证明与Conservative等价。
6. before-C退出、known-invalid/covered hints、UIR suppressed hints、late完整拒绝、
   redispatch、每job占用和缺测infer分别记账。仅记录实际后继派发，不称因果延迟节省。
7. 所有24格/六臂/两个speaker/两个repeat全表。原credit、same-G posterior支持与
   both-board-to-physical-drain能量单列。外来GPU owner令该能量unverifiable，不删除
   latency/correctness/失败证据。五主臂不是factorial，不分摊各check的唯一audio秒贡献。

presence输出两种透明basis：inflight primary用actual fullcall，版本差异同时给actual
fullcall basis与fullcall/dependency_versioned union（不混入strict-birth auxiliary）；
early-exit用actual fullcall的已证known-invalid/covered before-C terminal。每speaker
跨两个repeat至少1仅为最低激活presence，非power/显著性门；technical PASS独立于这些
布尔值。SUP固定，只能诊断，不能给这五臂归因SUP的独立收益。

postpilot prepare仅在Root idle receipt+GPU无compute owners时枚举固定计划的全部raw
路径并freeze input hashes/config/env。任何缺失/未执行cell都保留表行和configured
offered分母，不补metric0，不以partial说完整PASS。源码、bundle、manifest、root可解析
ref、config/env/prelaunch、8TB raw/summary/gate各角色分别记录。CURRENT从不由审计修改。
