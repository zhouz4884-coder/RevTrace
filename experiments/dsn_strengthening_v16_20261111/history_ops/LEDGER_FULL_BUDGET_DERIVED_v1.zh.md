# 全预算派生：更多worker占用与更高及时内容信用

记录类型：**DERIVED_FROM_FROZEN_OUTPUT_NOT_NEW_RUN**，2026-11-11。本表只是已经冻结/发布输出的算术重组，没有新正式CPU实验、原events/native_jobs/Consumer扫描、模型调用或GPU运行。旧冻结ledger及其门不修改。

**完整成本不是“省了69秒计算”。** 同一旧四speaker/bdfa16格中，RevTrace全部162次派发消耗104.676268 worker-s，Conservative136次为87.194045 worker-s，前者增加20.05%。但原D2/C8信用37→66.339750秒，及时且后来实际同G全文支持的信用29→51.518125秒，增长超过占用增加；单位实际worker占用对应的信用也提高。

## 1. 两臂全部派发的完整预算

| 已冻结观测 | Conservative旧8格 | RevTrace旧8格 |
|---|---:|---:|
| 全部派发jobs |136|162|
| 实际installed jobs |136|136|
| installed worker-s |87.194045|91.161527|
| installed原infer已观察区间s |86.216504|90.201303|
| ASR后、C前abandon jobs / worker-s |0 /0|24 /12.573526|
| completed-discard jobs / worker-s |0 /0|2 /0.941216|
| **全部worker-s** |**87.194045**|**104.676268**|
| 原infer已观察区间合计s |86.216504|91.126818，另24次缺测|
| installed记录model_evaluated=true |128|128|
| 全部返回记录model_evaluated=true |128|130，含2个discard|

24次abandon的ASR确已执行，但完整infer timer因异常未产出，保持NA；“已观察区间合计”不等于总神经时间。worker wall也不是GPU active seconds；同job的infer与worker区间嵌套，不能相加。两个worker的占用秒可以加总，却不是服务episode墙钟。

69.016526秒是92个跨版本晋升调用的全程worker子集，它们属于已安装91.161527秒之内，不可再与全预算相加。13.514742秒是24个abandon加2个discard子集，必须进入全预算。旧外部92.102742秒仅含完成返回的jobs，漏掉12.573526秒abandon，不能作为RevTrace全部成本。

## 2. 同scope信用与占用的直接权衡

两臂各66.339750 offered audio-s、136个原500ms/EOS前沿；仅四条既有声学来源，每源两次fresh，八次时序配对不增加独立speaker。以下没有混入new8、final4f matched、old14三臂或H3/LCP银行。

| 指标 | Conservative | RevTrace | 相对变化 |
|---|---:|---:|---:|
| 全部occupied worker-s |87.194045|104.676268|+20.05%|
| 原D2/C8信用audio-s |37.000000|66.339750|—|
| 及时且后来实际G全文支持的audio-s |29.000000|51.518125|—|
| 及时但同G全文失配的audio-s |8.000000|14.821625|—|
| 同G参照unknown信用audio-s |0|0|—|
| **原期限信用 /occupied worker-s** |**0.424341**|**0.633761**|**+49.35%**|
| **及时同G支持信用 /occupied worker-s** |**0.332592**|**0.492166**|**+47.98%**|

这是有实质信息的正向权衡：在这组单链固定工作负载中，更多实际占用换来更大及时信用，且占用分母下的信用产出也更高。它不是服务wall goodput、能耗效率、人工文字准确率、被因果挽回的GPU工作，不能代替强版本/Ready/UIR新闭环或多链资源机会成本比较。

“同G支持”仍是原实际首view全文与其后来实际G选定文本相等；不是在线已认证、真值正确或新增文字量。失配14.821625秒照列，未按支持状态重新过滤offered分母。

## 3. 两次repeat完整保留

每repeat覆盖相同四speaker，每臂offered33.169875秒：

| repeat/臂 | jobs | installed worker-s | abandon worker-s | discard worker-s | 全部worker-s | 原信用 /worker-s | 及时同G支持 /worker-s |
|---|---:|---:|---:|---:|---:|---:|---:|
| r0 Conservative |68|43.557345|0|0|43.557345|0.424727|0.332894|
| r0 RevTrace |81|45.580041|6.272558|0.472278|52.324877|0.633922|0.492291|
| r1 Conservative |68|43.636701|0|0|43.636701|0.423955|0.332289|
| r1 RevTrace |81|45.581486|6.300968|0.468937|52.351391|0.633601|0.492042|

两repeat各自原信用18.5→33.169875秒，及时同G支持14.5→25.7590625秒。两次同向只描述该固定四source重测，没有设置2%有效性筛选，也不提供总体显著性或未来负载保证。

## 4. 来源绑定与可复算公式

主输入为已冻结 `results/LEDGER_v2/JOBS.json` 的298行，SHA256：

`d5656bed0ca04fcf455bef2594b75a29ca03a13af88460cb912e35d4cd8cfbe0`。

父正式分析source `817ebbbabce15e6d9c2d84f8435bbbc8640d8b22`；原神经执行source保持 `bdfa3b1307d267a5a4caf6484e1ad465c39a592e`。原每cell SUMMARY与 `LEDGER_CONFIG_v2` 已绑定hash一致，16个content RUNS的cell/source/arm/repeat完全一致、primary对象逐项相等；config及Consumer原hash与旧Collection manifest、content INPUT_HASHES相同。这里只核metadata中的hash，不重新扫描原Consumer。

额外复用已经冻结的 `dsn_streamcorrect_independent_20261029/FINAL_CONTENT_RESULTS_v2`：RUNS SHA `866e91f95ea884bd462bd1f46485af5c12e83d857f12536b7f7660148a2a49dc`，SUMMARY SHA `cf00e70e61a62673fe88fcfc8a1e1a2046b4481a7757a8c7a86c663231e81a87`；其原Gate为PASS_ALL16_272_ORIGINAL_AND_CONTENT_RECOUNT。逐cell支持/失配/unknown之和守恒到原信用，总和复核到其旧汇总29/51.518125。

公式：全部worker预算为**所有派发job**的worker_reported_wall_s之和；原期限产出率为信用audio-s除以该全部预算；同G支持产出率为原及时同G支持audio-s除以同一预算。比率取汇总分子/汇总分母，不取各cell比率平均，也不把模型结束时间或取消数换成节省量。

机器可读完整表、逐repeat和16cell及每个输入SHA在 `LEDGER_FULL_BUDGET_DERIVED_v1.json`，SHA256 `9b9386697febe95a722a057432114959600040f1046daaaac322d598025572ed`；算术脚本 `derive_full_budget.py` 的自身hash已写入JSON。此派生文档没有赋予新实验执行source或新神经结果身份。
