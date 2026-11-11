# 全调用与父确认前工作：正式ledger CPU核验

2026-11-11。新实验 `REVTRACE-V16-FULL-JOB-LEDGER-20261111-V2` 已完整PASS，零新GPU。实际分析source `817ebbbabce15e6d9c2d84f8435bbbc8640d8b22`，6项控制全过，完整manifest/bundle已导入本地可解析ref `codex/v16-ledger-v2`；默认4f与显式source预检均通过。没有覆盖外部 `analysis/gpu_ledger_v1`，没有修改v15。

## 1. 原表总数重现，但标签与可解释对象必须改正

| 实际类别 | jobs | 全调用worker区间s | 已观察原infer区间s | infer timer缺测 |
|---|---:|---:|---:|---:|
| 跨版本晋升后实际安装 |92|69.016526|68.308115|0|
| ASR后、学习C前abandon |24|12.573526|不可确定|24|
| 完整结束后discard |2|0.941216|0.925515|0|

无效调用worker区间合计13.514742秒，完整晋升调用/无效调用的worker构成比5.10676。**这个比值是全调用成本构成，不是已节省计算比、回收收益比或GPU利用率。** worker区间包含restore/insert/infer/export等；原infer同步墙钟包含ASR、C/U及callback，不是独占GPU算时。24条abandon明确已执行ASR，它们因异常不产生完整infer timer，不能用缺省0称“未触发神经模型”。

## 2. 真正已在父确认前做掉多少工作

逐一将92个完整冻结输入绑定到后来实际安装的完整父状态；其实际parent receipt与canonical_install日志之间是原控制器应用边界的记录区间，promotion本身没有独立timestamp。按该区间给出父确认前工作上下界：

| 92个晋升job的观察对象 | 父terminal receipt前 | 父install receipt前 |
|---|---:|---:|
| worker区间交集合计s |22.428636|24.487472|
| 原infer区间交集合计s |21.865507|23.924343|

92个父receipt和install receipt均位于对应child原infer区间内。因此这里确实有真实完整调用已经执行的前缀机会；但69秒全程中大量工作发生在父确认之后，不能把69秒都称为因取消会丢失的既有工作。上述界依赖原trace记录边界，不是精确promotion瞬间，更不是重执行的版本策略实际损失。

外部23.779086896秒公式完整重现，但展开等于 `parent_install−child_model_start−(child_worker_end−child_model_end)`。它是固定原infer时长、立即重派且省略重启队列等条件下的重启代理；不是观测到的因果完成延迟节约，也不能跨job求和当episode关键路径收益。三/四策略闭环仍需真实运行。

## 3. dispatch完整守恒，没有靠省掉未安装状态凑数

| 终态 | Conservative旧8格 | Spec旧8格 |
|---|---:|---:|
| dispatch |136|162|
| 实际installed |136|136|
| ASR后before-C abandon |0|24|
| completed-discarded |0|2|
| completed-ready但未installed |0|0|
| active无terminal |0|0|
| suppressed-before-execution |0|0|
| fault/other |0|0|

这是对每个dispatch、terminal、abandon/discard ledger、原DISPATCHES和安装事件的集合分解后得到的结果，未预设三项等式。逐cell显式零状态在 `results/LEDGER_v2/CELLS.json`。原ready使用数0只能描述旧轨迹，不能证明新ready-only策略在改调度后等价保守臂。

## 4. 两个晚discard的修复机会被否定为“提前发同一hint”

S0908的r0/r1 `j000016` 原ASR `produced_perf` 时刻晚于代码中的原 `before_corrector` 检查，但早于 `on_asr`、`sent_perf`及Queue.put。父j15原infer结束仍分别晚于这个已产出时刻6.739ms/70.530ms。它不是发送完成或精确C入场时间。实际proof随后才能产生，因此仅加快同一hint下发，不能让它赶上**原有检查点**。

这不是已经证实的hint实现缺陷。**在ASR publication之后、原学习C调用之前再加一次非阻塞检查**，是不同的、尚未测量的低成本候选；旧trace没有记录Queue.put返回或精确C入口，不能宣布它必定有效，也不能据此排除它。合法C中途取消或等待父输入是另外的候选。完整六时钟与proof SHA见 `LATE_DISCARD_TIMELINES.json`；独立审阅见 `../review/LEDGER_v2_INDEPENDENT_REVIEW.zh.md`，术语勘误见 `LEDGER_TIMESTAMP_CLARIFICATION.zh.md`。已冻结source与结果保持不变。

## 5. 已完成内容补强的正向结果也应保留

独立29格内容CPU结果显示：H3主层R-only的最优对齐D+S267，在Joint降至49，减少81.65%；第二完整对齐规则为266→48，减少81.95%。原双期限信用同时664.150→680.760秒，增加16.610/714.110=2.326pp。R00的150→R-only267还使“只保留计算会增加中间文本修改”的观察超出LCP代理本身。

但R01同为49，因此不能说两个因素都对低修改量必要；Joint应连到及时性与连续性联合目标。最终actualConsumer全文逐source跨臂的byte-hash一致性将由已授权的独立v2内容曝光任务补验，不能从总长度10575或相同WER推断。内容结果详见 `HISTORY_CPU_RESULTS.zh.md`；新增曝光字符秒仍是测量代理，不是已经验证的体验收益。

## 6. 输入、身份与结果字节

旧四source16格的输入136项全部逐文件匹配原Collection manifest，再由正式reader在8TB执行前后重哈希。实际神经源保持bdfa，不拿本轮分析commit改旧run。

- source manifest SHA256：`6993b20a88435db68fbe393a01d2c96da1145d7a177a43b050636707dd635300`
- source bundle SHA256：`ec49bd1da9f15b764062dbc2e0663c82015ff5cc305bbd1d0bb86d56027e00fa`
- config SHA256：`1d95334a30974e500607231e17e38c9dea2d5c749142082e916983fc32074dbb`
- environment SHA256：`2bb763bc4e72fcecafdbd1f80a7313195cc9dec1bccf75e62ad2cd32ae897a82`
- SUMMARY SHA256：`f45f76636321933a08ce7f1fd98a554bfccbbb67bea424b256be8416c0d7f9ca`
- GATE SHA256：`da26ffd73f1d44643b2e63080a668c9d9003878a280aff3d06edd2498ac26a85`

8TB raw：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/ledger_v2`。有界9文件405,432字节取回本目录 `results/LEDGER_v2` 并逐SHA一致。结果门为 `PASS_FULL_JOB_BINDINGS_TERMINAL_CONSERVATION_AND_TIMER_SCOPES`。
