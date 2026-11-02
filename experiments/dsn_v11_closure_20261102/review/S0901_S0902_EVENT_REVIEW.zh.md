# S0901/S0902期限失败：原事件只读核查

2026-11-02。v11方法与原32格永久保留。本核查通过既有批准的 `dsn_native_confirmation_20261102/ops/remote.py` 仅打开原JSON/JSONL，人工定位dispatch、worker结果、Owner安装、publication及Consumer行；没有运行formal分析器、模型、GPU命令、重放、修改源/日志/CURRENT/稿件。远端raw未下载，本文是唯一新增小输出。

## 判断

**两来源不能只标为“EOS失败”，也没有发现足以认定为调度正确性bug的证据。** S0901主要是完整输入沿前驱ASR链产生得晚，加上原infer耗时，EOS的ASR完成已越过D2；Supervisor还真实增加约0.19–0.21s交付延迟。S0902尾部连续完整输入预测被同F实际Canonical反证，正确调用转为等待真实父状态的串行路径；父状态一旦安装，派发只晚数毫秒。S0915则从6s开始出现连续非EOS失败，不能用一个短尾解释。

存在可优化的交付开销与个别边界敏感前沿，但目前不支持把它直接称为“修复实现即可恢复全部D2”。所有原SLO和输入/选择语义保持不变。

## 1. 文件、时钟和读取范围

原8TB基目录：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_confirmation_20261102/service_confirmation_v1/cells/`

核查六个目录：`SC_NEWTEST_BAC009S0901W0183_fullcall_r0/r1`、`SC_NEWTEST_BAC009S0902W0343_fullcall_r0/r1`、`SC_NEWTEST_BAC009S0915W0286_fullcall_r0/r1`。后缀r0/r1指两个实际目录，不是路径通配重跑。

以下表格均为相对各格原 `ORIGIN.json.origin_perf` 的perf_counter秒。原origin：

| 来源 | r0 | r1 |
|---|---:|---:|
|S0901|5362500.126311523|5362572.400053527|
|S0902|5361324.487417803|5363684.408591590|
|S0915|5361984.144473837|5363091.297502208|

精确字段：

- `owner_e0/dispatch.jsonl`：`job.job_id/start.frontier/end/dispatched_perf/started_on_canonical`、`physical_slot`。
- `owner_e0/worker_results.jsonl`：`event.kind`；ASR的 `produced_perf/start_state_sha/projection.end_state_sha`；完整结果的 `record.worker_job_begin_perf/model_start/model_end/worker_job_end_perf/start_state/end_state`；退出的 `proof`。
- `owner_e0/owner_events.jsonl`：`canonical_install.observed/parent_state_sha/next_state_sha`；`durable_sync.receipt.synced_perf`。
- `publications.jsonl`：`event.publication_id`、Supervisor物理reader的 `received_perf`。
- `supervisor.jsonl`：外层 `observed` 与内层Owner `event.observed`，按publication_id定位。
- `consumer.jsonl`：`observed/visible_frontier/certified_frontier/private_job/canonical_sha`。

`record.model_start→model_end` 是原infer及CUDA同步包围的host区间，包含ASR、原C/U及其早显回调；不是纯GPU kernel时间。restore/audio插入在model_start前（原 `native_bridge.py:151–178`），因此worker开始与model开始分开。原结果日志没有每条消息的精确Owner主循环receipt时刻，故sent→install不能再强拆成纯IPC或纯WAL。

## 2. 原端点事实：三来源覆盖了全部未及时音频

| 来源 / repeat | Display P99 / s | 原信用 / audio-s | D2 miss | EOS miss | 未及时前沿 |
|---|---:|---:|---:|---:|---|
|S0901 r0|2.404875|8.0|1|1|130209(EOS)|
|S0901 r1|2.548393|7.5|2|1|128000、130209(EOS)|
|S0902 r0|2.216074|8.5|1|1|137055(EOS)|
|S0902 r1|2.716528|8.0|2|1|136000、137055(EOS)|
|S0915 r0|3.071474|5.5|7|1|96000、104000、112000、120000、128000、136000、143969(EOS)|
|S0915 r1|3.073607|5.5|7|1|同r0|

全部C8仍通过。S0901实际EOS权重0.1380625s，S0902为0.0659375s，S0915为0.4980625s。两repeat合计未及时音频分别为0.776125、0.631875、6.996125s，和为原全cohort的8.404125s。其余五speaker的RevTrace两repeat全部通过，原10/16不变。

## 3. S0901：输入生成链已迟，另有实际FIFO交付等待

### EOS实际链

| 相对时刻 / s | r0 | r1 |
|---|---:|---:|
|原EOS offer|8.138063|8.138063|
|原D2 deadline|10.138063|10.138063|
|前驱j17产生匹配的完整F=128000预测输入|9.893323|10.043908|
|EOS j18派发|9.901836|10.053633|
|worker实际开始|9.905366|10.057785|
|原model开始|9.916315|10.068367|
|EOS ASR produced|10.448645|10.559963|
|EOS原完整model结束|10.768835|10.819886|
|EOS Owner Canon安装|10.807978|10.885453|
|首次实际D消费|10.635294|10.773896|
|首次实际C消费|10.891007|10.974294|

定位：两格 `dispatch.jsonl:18` 为j18；worker ASR/complete在 `worker_results.jsonl:35/36`；Owner EOS安装在 `owner_events.jsonl:36`；D/C在 `consumer.jsonl:48/49`。

j18冻结start SHA为 `5076d4a54a1ec495c181cdbafdc5e6954017ebbe35f4aaa3199b4f362b798b29`。原 `worker_results.jsonl:33` 的j17 `projection.end_state_sha`正好为此值；对应真实父Canonical到 `owner_events.jsonl:34` 才确认（r0=10.421246、r1=10.581262）。因此EOS调用已经在父确认之前运行，预测输入产生后8.5/9.7ms就派发，并没有保守地等父C完成。

**事实**：command派发→worker开始约3.5/4.2ms；EOS ASR produced本身已比deadline晚0.311/0.422s。仅删除该ASR之后的处理时间，也无法在原实际时间线上让这两个EOS命中D2。

从offer到dispatch的1.764/1.916s不能称为“worker命令排队”：它主要跨越前驱完整输入尚未产生的阶段。r0前驱F8调用j17在9.119254开始原infer，ASR到9.893323；r1为9.271549→10.043908。F8原infer完整区间分别1.259/1.266s。该相位已经接近D2，随后仅0.138s的EOS增量仍需要一次完整原调用。

### FIFO与应用开销也不是零

EOS private publication48，r0从Owner emit10.456766、reader收到10.457486，到Supervisor note10.605245、Consumer observed10.635294；r1分别10.585740、10.586378、10.703841、10.773896。reader收到→主循环note约147.8/117.5ms；ASR produced→D消费约186.6/213.9ms。

精确位置：`publications.jsonl:48`、`supervisor.jsonl:54`、`consumer.jsonl:48`。它前面的publication46/47位于三日志同号行，Supervisor行为52/53：

- pub46 Canonical F8消费于10.483571/10.602013；
- pub47 private snapshot消费于10.587571/10.679250；
- 两次消费的visibleF/certifiedF均128000、private_job均null、canonicalSHA均5076d4a54a1e…、textSHA均2324c0838759…。

所以确实有一个不改变上述可见状态的snapshot排在EOS前，及连续同步日志/验证的FIFO成本。**推断边界**：这些字段相同不自动授权删掉publication；它仍携带顺序、ACK/pin与whole-view一致性用途。现有日志也没有把等待细分为每次fsync/CPU/排队。不能把整段187/214ms叫纯网络或单个UI检查成本，更不能直接从P99相减当修复结果。

## 4. S0902：原完整输入连续反证后，正确链及时派发但失去lookahead

两repeat尾部都有3条已执行ASR前缀被反证：j19(start120000→128000)、j21(128000→136000)、j23(136000→EOS)。原proof全部为 `actual_canonical_disagrees_with_complete_start`，witness分别120000、128000、136000；expected/actual完整cut SHA不同。worker原行分别36、39、42，派发行19、21、23。不是按旧birth或低置信度随意取消。

EOS错误j23冻结期望start为2f8aace27916…，实际F136000选定start为 `9151b07d6be81ffa1315a842ad489365e4ed62be95b75bb6421666bc47447b08`。正确EOS j24使用后者，原日志中没有产生该start的匹配ASR预测；只能由实际选定父状态确认。

| 正确调用 | r0父install→派发 / s | r1父install→派发 / s |
|---|---:|---:|
|F128000 j20|9.112737→9.116109|9.522400→9.526328|
|F136000 j22|9.688488→9.691848|10.121907→10.125487|
|EOS j24|10.447245→10.452414|10.928204→10.933112|

这些正确调用均 `started_on_canonical=true`；父install后约3.4–5.2ms派发，command→worker又仅3–5ms。没有看到“正确完整输入和空槽都在，但被长时间不合理搁置”的反例。

EOS精确节点：两格 `dispatch:24`、worker ASR/complete `43/44`、Owner安装 `38`、Consumer D/C `52/53`。

| 相对时刻 / s | r0 | r1 |
|---|---:|---:|
|EOS offer / deadline|8.565938 /10.565938|8.565938 /10.565938|
|正确EOS dispatch|10.452414|10.933112|
|原model开始|10.467045|10.941963|
|ASR produced|10.838397|11.337414|
|完整model结束|11.077550|11.596196|
|Owner安装|11.108509|11.640600|
|首次D / C消费|10.880000 /11.142405|11.391517 /11.669272|

r1在EOS派发时就超过deadline0.367s；r0也只剩0.114s，而本次原ASR从model开始到produced实际用了0.371s。ASR之后的额外交付延迟只有约41.6/54.1ms，不能解释全部超时。

r1的延迟已在EOS之前积累：F136000首次D为10.684100，距该完整非EOS区间的8.5s offer达2.184100s；ASR produced10.618016也已经迟于其10.5s deadline。两repeat正确EOS派发相差约0.481s，与真实父F136000安装相位差约0.481s一致。它不是仅由EOS自身model耗时增加导致。

注意F120000的首次D来自更早private publication40，早于后来正确j18的ASR；不能把任意frontier的首次显示都强行配给最终Canonical job。上述EOS及F136000节点已按实际publication/Consumer定位。

## 5. S0915对照：从6s起是持续非EOS积压

两repeat均26dispatch；r0为18complete+8abandoned，r1为19complete+7abandoned。r1多一个完整但未入选结果，原信用仍同为5.5s；没有把这些支付的工作抹去。

从F96000(6s)到F136000(8.5s)，正确选定j15/17/19/21/23/25均在full0当前父状态上执行；父install后约2–5ms就派发。r0六次原infer区间为0.643/0.733/0.542/0.733/0.564/0.651s，r1为0.643/0.741/0.538/0.715/0.531/0.644s，均长于500ms输入节奏。另一个worker反复在错误未来start上执行前缀后退出，不能当作正确链的可用完成结果。

| offered音频秒 | r0实际D延迟 / s | r1实际D延迟 / s |
|---|---:|---:|
|6.0|2.022780|2.048483|
|6.5|2.319514|2.339379|
|7.0|2.402830|2.419717|
|7.5|2.719864|2.696823|
|8.0|2.773764|2.768878|
|8.5|3.002190|3.021866|
|EOS8.9980625|3.085666|3.084204|

对应D消费行为33/36/39/42/45/48/51；正确派发行15/17/19/21/23/25/26。这组几乎可重复的累积曲线不是一个0.498s EOS尾段造成的。

**一个明确的应用边界敏感例外**：首个失败F6，r0 ASR在7.976400产生，早于8.0deadline23.6ms，D消费却为8.022780；r1 ASR7.998608仅早1.4ms，D消费8.048483。因此交付开销确实决定了这两个边缘点的hit/miss。其后大部分ASR自身已经越过相应deadline，优化这一个后缀并不能据此声称恢复整轮D2。

## 6. 事实、解释与可修假说的反证要求

当前事实支持“原调用/输入依赖进展 + 实际执行耗时 + 有限交付开销共同形成期限边界”，不支持单一“EOS格式bug”“worker排队太长”或“Consumer独自造成全部失败”。

- **若声称dispatcher有可修错误**：需给出完整输入/用途已具备、合法authority明确、物理槽已释放，却无其他约束仍长时间不派发的实际区间。S0902正确尾部反而是父install后3–5ms派发；S0901空闲worker不代表其F8完整输入已经存在。这些是该假说必须解释的反证。
- **若声称取消误杀了可保留工作**：需推翻own-start-frontier上actual/expected完整cut的反证，或找到实际匹配却被拒绝的原回执。不能以同文本prefix、旧版本不同或更早祖先后来可能收敛代替完整输入证明。现有三个S0902 tail proof及原c4闭环未给出这种反例。
- **若声称只修Consumer就能兑现本轮全部D2**：S0901两个EOS、S0902两个EOS及S0915多数后段在ASR produced时已经late，是直接反证。F6确有应用敏感窗口，必须分别报告，不能泛化为整轮修复。
- **若优化同步日志/重复snapshot**：S0901 pub46/47是值得定位的实现成本候选，但新分支须保持durable选择、原ingress、publication顺序、whole-view校验、ACK/pin与真实apply时钟，不能移早时间戳或免费删除安全步骤。应对原输入/完整输出、同资源两策略与重复运行验证；当前不能把记录中的等待直接换算成新性能结果。
- **若降低原infer耗时**：先用同完整输入、重复运行与合法原程序oracle区分实现/数值/模型机制；改变精度、原C/U、VAD或EOS语义会改变合同，不属于对永久保留v11结果的原位修复。

本阶段不建议更改v11方法/32格或开GPU。可以把这份事件证据用作服务边界解释：输入匹配与保留能减少可避免损失，但不会消除原反馈依赖的推进速率、实际模型时长与物理交付成本。任何性能修复应另冻新源/新ID；现有结果及代码身份不重贴。
