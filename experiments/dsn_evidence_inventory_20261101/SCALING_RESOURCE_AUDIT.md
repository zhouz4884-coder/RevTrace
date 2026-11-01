# RevTrace：历史扩展性、服务容量与资源证据检索

日期：2026-11-01。范围：只读检索旧 `Paper`、`Paper_TC`、当前 DSN v9、对应 `results/`、`experiments/` 和研究报告；本轮没有 SSH、GPU 调用、重新运行旧审计器或修改旧结果。以下是论文证据与研究机会评估，不是实现正确性复核。

## 核心判断

确实存在当前 DSN v9 未展开的较强历史执行与容量证据；但不能把它们与当前 R×S / Native 证据直接拼成“同一完整协议已在 64 路线性扩展且 D2/C8 达标”。最容易误用的两组 V100 数字来自**不同代执行器**：

1. `51.68 xRT / display P99 1.928 s` 是较晚、真实到达与证书执行的 TC-LIVE，Qwen **0.6B**、rho=3、volatile、4+4 V100、64 同步会话。
2. `157.786/111.722 xRT / display P99 1.089/1.394 s` 是更早 available-input 执行研究，排除音频到达等待，installer 仅轻量版本更新，未执行后来的 DGFT certificate checks。
3. `30,168 commits` 是整个 **96-run TC-LIVE** 重审计计数，既不是 64 路单点计数，也不是当前原生纠错服务的安装计数。

对 DSN 最有价值的旧资产不是把峰值吞吐换进摘要，而是给出一项清楚、可检验的系统教训：**到达受限时，总吞吐近乎不变，保护工作与显示尾延迟仍可显著改变；计算、交付连续性、可信完成及物理排空是不同预算。** 当前稿已经用后两者构造了主线，不应让一个跨合同 scaling 表冲淡它。

## 1. 51.68 / 1.928 的真实身份与分母

### 1.1 源码与配置

定位入口：

- `Paper_TC/tables/t10_live_results.tex:19`：`.6B, 4+4, c64, Coarse, 51.68, 12.02 J/audio-s, D99 1.928 [1.741,1.959], commit99 4.791, volatile`。
- `results/tc_live_20260906/raw/v100/qwen0.6B-coarse-p4a4-c64-sync-r0/config.json:2–62`：研究 `TC-LIVE-20260906`，rho=3，fine=2 s，16 kHz；FP16 Proposer / FP32 Authority；双方 transformers-eager、microbatch=16、max_new_tokens=256、rollback_tokens=5、unfixed_chunks=2；sync、duration_limit=0、decoupled；Proposer GPU0–3、Authority GPU4–7。
- 同目录 `provenance.json:2–18`：真实执行 commit **`c1783c9751967be124c357425d9a4e2dc70ce44f`**；8×Tesla V100-PCIE-32GB，driver 530.30.02，Python3.10.6、torch2.4.1、transformers4.57.6、qwen-asr0.0.6；PBS179711.manager。
- source/config 均绑定输入 manifest SHA `fb145d1471b9d164670d07cb0fcfd68c34fe0f4709fafd567666bc11c606c0c8`，模型 config SHA `76d3ae4601ce939830b2517f4a6cadb86cc51316c3900af6b020b051c21a478c`。这里不是重新校验全模型权重，不把 config hash 写成全权重 hash。

本轮从本地 Git 对象读取 c178 的 `src/revtrace/live_qwen.py`，SHA256 为 `ccc98dde32253767afa5b416c0f68e8314e09f77db8774ad3a07900e32729336`，与原 provenance 匹配。没有把当前脏树的同名源码当成历史执行源码。

### 1.2 实际输入不是 64 个独立来源

直接读取该 cell 的 `sessions.json`，得到 64 个会话，但仅 **12 个 unique source_id、12 个 unique audio_sha256**，全部 offset=0。来源名为 bilingual `chinese-00` / `english-00` 等；这是复用音频形成的并发压力，不是 64 位独立说话人。r0 offered 音频 **2127.2318125 s**，最后音频到达40.295 s。

上述 unique 计数只是本轮读取本地 JSON 集合得到的描述统计；不是再次执行神经实验或原审计器。输入来源与 v9 的 24 个独立新说话人 / 714.110 s 不是同一 cohort。

### 1.3 三个真实重复与不能省略的负例

各值来自对应 `...-r0/r1/r2/result.json` 与 `results/tc_live_20260906/summary/summary.json`。

| 模型 / repeat | xRT | Display P99, s | Commit P99, s | Display >2 s / events | commits | GPU J/audio-s |
|---|---:|---:|---:|---:|---:|---:|
| 0.6B r0 | 51.73694 | 1.95920 | 4.52158 | **7/1107** | 390 | 12.14061 |
| 0.6B r1 | 51.68158 | 1.92800 | 4.85936 | 0/1107 | 390 | 12.01551 |
| 0.6B r2 | 51.62282 | 1.74114 | 4.79071 | 0/1107 | 390 | 12.02286 |
| 1.7B r0 | 49.60926 | **3.58421** | **9.25601** | 118/1107 | 390 | 16.91715 |
| 1.7B r1 | 49.48796 | **2.68733** | **9.33530** | 97/1107 | 390 | 17.51863 |
| 1.7B r2 | 50.02341 | **3.83346** | **8.89866** | 146/1107 | 390 | 16.83910 |

0.6B 的“3/3 runs display P99≤2 s”不等于所有前沿都及时；r0 的7次真实超时不可抹去。1.7B 同布局同 c64 的 display P99 **0/3** 达标，而且 commit P99 全部>8 s。该对比对识别模型容量边界有价值，对宣称当前1.7B完整系统64路达标构成直接反证。

终态质量字段：0.6B 各重复 English WER 0.03249097、Chinese CER 0.04081633；1.7B English WER相同、Chinese CER0.02511774；token_limit_events=0。它们是该固定 bilingual pool 的终态质量，不能代替现代同 F 整输出支持、逐前沿内容质量及真实纠错选择质量。

### 1.4 为什么不能直接变成当前 D2/C8 服务证据

冻结 c178 源码中的可核查事实：

- `src/revtrace/live_qwen.py@c178:241–253`：Owner 收到 proposal 后立即设置 `displayed=self.clock()` 并记录 `display`；事件同时记录 `parent_superseded`。这是**Owner 显示事件**，不是现代独立 Consumer 对整视图重新验证后实际 apply 的时钟。
- `@c178:320–326`：display/commit延迟分别来自其事件列表；检查 `ceil(duration/fine)` / `ceil(ceil(duration/fine)/rho)` 计数完整性。
- `@c178:327–338`：吞吐分母确实包含 arrival+drain，返回终态与各事件P99；没有现代 all-offered D2/C8 双期限信用、支持链持续交付面积、Consumer整视图撤回统计。
- `docs/reports/dsn_review_20261004/live_reaudit.json:2–6`：明确 volatile，配置先于 durable_journal_path；不能继承现代 WAL/recovery 保证。

**支持：**历史真实到达、执行和认证路径可在单机8卡上以4+4复制工作；该0.6B有限点显示P99有容量余量；粒度/调度影响尾延迟和成本。

**不支持：**现代R×S/Native同合同64路达标、当前完整Consumer交付、全部输入持续及时、durable recovery、线性扩展、多节点扩展、64个独立来源或1.7B的同点达标。

## 2. 30,168 commits 的正确用法

`docs/reports/dsn_review_20261004/live_reaudit.json:2–6` 给出96 runs、30,168 recorded commits、56,556 display events、volatile。它横跨模型/平台/策略/并发点。单看上述0.6B c64 Coarse只有3×390=1,170 commits。

`docs/reports/dsn_assets_20261006/PERFORMANCE_BRIDGE.json:1–34` 是后续选择18个历史运行、重放6,210次已记录提交的桥接审计，source commit逐cell为c178；这是对历史 raw 的审计覆盖，不是18个新GPU实验。

其中 `certificate_replays_rejected` 是重放/单次使用拒绝测试的计数：`scripts/audit_tc_live_qwen.py:100–126` 先断言原安装accepted，再将同certificate用于已推进state并断言duplicate rejected，最后以count汇总。本轮只读此逻辑，没有执行该审计器。不能误写为正常合法certificate大量失败，也不能用30,168扩大当前Native无非法安装的分母。DSN若需要“历史执行规模”可单独标明；当前实验的 audited transitions 应只用当前真实来源。

## 3. 早期 available-input V100 scaling：数据很好，但合同更弱

### 3.1 身份与明确边界

- `results/v100_v5_headline/SOURCE_MANIFEST.json:2–10`：PBS178169.manager、30/30cells、30rawfiles、三重复headline与allocation敏感性；原短commit `346be02` 在本地解析为完整 **`346be02998758a0db211d9ed64358b4ca251f126`**。
- 84格探索矩阵：`results/v100_v1_v4/V1_V4_EXECUTION_REPORT.md`，正常c16、allocation/concurrency、FP32粒度、microprofiles。
- `Paper_TC/supplement/dgft_details.tex:290–296` **明确写出**：排除audio arrival waiting，installer执行轻量version update，**而非DGFT certificate checks**；只刻画执行成本与allocation，不是live SLO capacity。
- `Paper/tables/t7_v100_scaling.tex:5–16`：以FP16 singleton作不同路径的参照；1.7B Coarse/Hybrid P95最终token edit=3.18%，8/16exact，而SG0%、16/16exact；volatile。

### 3.2 容量和分配证据（保留正负）

`results/v100_v5_headline/178169.manager/V5_HEADLINE_REPORT.md:5–16`，各中位数为3 repeats，范围为min–max：

| 模型 | P+A / c | xRT | Display P99, s | Segment commit P99, s | >2s display events |
|---|---|---:|---:|---:|---:|
| 0.6B | 1+1 /64 | 40.319 | 4.125 | 11.756 |1184/2880|
| 0.6B | 3+5 /64 | 93.788 |1.756|4.991|**6/2880**|
| 0.6B | 4+4 /64 |157.786|1.089|3.080|0/2880|
| 0.6B | 4+4 /128|161.927|**2.079**|6.012|176/5760|
| 1.7B | 1+1 /64|28.238|5.475|19.698|1680/2880|
| 1.7B | 3+5 /64|77.704|**2.209**|6.273|106/2880|
| 1.7B | 4+4 /64|111.722|1.394|4.890|0/2880|
| 1.7B | 4+4 /128|107.305|**2.730**|10.153|960/5760|

不能把这种batch执行效率称作live流式xRT，也不能把6秒认证segment的commit分位数混入现代2秒前沿的C8定义。单机c64正点和c128饱和负点一起说明了**有限执行区间及P/A资源配比的重要性**；它不证明普遍linear scaling。3+5不自动优于4+4，不能仅凭“Authority更贵”推导合理分配。

V1 FP16/FP32相同batch重复稳定，但每模型仍有62个batch-vs-singleton request差异（`V1_V4_EXECUTION_REPORT.md`）；FP32不是忽略execution shape的数值等价证书。改变replica/microbatch可能改变权威输出，后续补测必须重新保留完整输出和质量。

### 3.3 对当前DSN的价值

适合 artifact 的“历史工程扩展与容量边界”表，最多在Discussion用一句话说明运行时不是天然限于两卡。**目前不建议塞进主评估或摘要**：其轻量installer和计时条件会引入一整套额外解释，容易让主贡献从可信反馈协调滑到通用batch/replica调度。若论文确实要主张完整协议scalability，必须用当前源、当前合同补少量点。

## 4. 更值得保留的历史运行资源证据

### 4.1 到达受限下，几乎不增吞吐也能改善服务尾延迟

`docs/reports/DSN_ASSET_STRENGTHENING_20261006.md:23–30` 与原TC-LIVE table：

- 双V100、1.7B、c16、volatile、3repeat：Fine→Coarse配对吞吐中位1.348×、能耗−39.672%，display P99中位3.342→1.690 s，显示run通过0/3→3/3，末尾drain15.633→1.098 s。
- 8V100、0.6B、c64：吞吐只约+1.3%，能耗−28.089%，display P99 2.458→1.928 s，run通过0/3→3/3，Coarse commit99仍4.791 s。
- 8V100 c16两个Qwen尺寸，显示和commit P99在3个repeat均<2 s；这是不同低负载点，不能写为c64的commit保证。

这是**历史正面、且比峰值吞吐更对口DSN的教训**。但它归因于认证粒度/调度，并非后期R×S整视图保留；不应作为R×S交互的第二条独立确认。

### 4.2 128会话的版本级调度配对控制

`Paper_TC/supplement/dgft_details.tex:364–398`：8个matched旧调度/decoupled pair、每version/cell仅一次，全部128终态文本与完整prompt tokens相同。V1001.7B/c16 Coarse显示P99 **5.712→1.733 s**；两3090 .6B/1.7B Coarse分别4.372→3.539、6.217→5.041。新版本同时变更ready-replica分发与authority-pending期间private推进，属于**版本级control**，不是one-switch ablation、不是3repeat。

可用来说明“粗认证并不必然阻塞private分支，执行协调有真实机会”。当前稿已经有更强的严格R×S设计，旧控制如需收录，放artifact机制历史，比再造一个贡献更合适。

### 4.3 能耗口径桥接（不能替换当前能耗）

`Paper_TC/supplement/dgft_details.tex:341–361`：另有3paired V100 power confirmation，6个GPU能量积分与保存总量误差<4e−11 J；pair节能28.70%、28.91%、27.97%。NVML采样最大间隔0.321–1.016 s。它提高了这几次历史GPU能耗的可审计性，**不是外部电表验证、host/network总系统能耗，也不是同一旧主表各run完整原NVML都在本地**。

`docs/reports/DSN_ASSET_STRENGTHENING_20261006.md:13–19,36–40` 还保存 durable 1.7B Fine/Coarse 1.403×、−32.18%GPU能耗，及volatile→durable吞吐1.912%差。但是原机器摘要 `results/dsn_strength_20261005/FINAL_REAUDIT_V4.json:1059,2335,2525` 明确 **available-input synchronous replay、16slots/12sources、合成状态/输出fault、P99为batch-ready-to-install而非live streaming、init excluded**。故这些强数字只能作为另一合同的认证粒度成本研究，不可拿来抵销当前59 J/audio-s或宣称现代部署节能。

## 5. 当前合同下资源证据：主要没有遗漏，负例已经有科学价值

### 5.1 36/48格服务区间与成本

`experiments/dsn_service_stability_20261028/RESULTS_FINDINGS.zh.md:7–15`：实际执行源 **f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf**，FP16/FP32、原D2/C8、all-offered/EOS/质量/能耗、row_complete、3freshprocess、四臂。8源121.205s与16源250.180s不同source mix，不是纯并发因果曲线。

`同文件:32–34,58–62`：36格C8全pass，c16失败全由D2；c8 P99pass仍有0.215s尾段扣信用。c16 joint相对Neither总model减少0.656–1.585s、lease减少0.662–1.374s，但wall与energy有正有负。

当前v9 `sections/05_operating_boundaries.tex:14–69` 已包含48点8/12/16工作负载表、D2/C8正负、source mix、成本和质量边界。**这不是被漏掉的坏点，也无需用旧V100好点“修正”。** 它支持“连续性保证与首次及时交付分别受机制和容量约束”。

### 5.2 R×K：同输入物理释放至服务的一条完整链

`experiments/dsn_joint_retention_exit_20261028/RESULTS_FINDINGS.zh.md:7–13`：同f0源、16独立旧开发来源、250.180s、FP16P/FP32A、rho1、16固定行、2phase×4arm×3repeat=24；F2受控长尾，不能作自然发生率。

- `:19–45`：sync R1K1 D2/C8通过2/3，staggered0/3；R×K服务交互符号混合。单纯claim“联合提升”会损害可信度。
- `:49–65`：675严格processed-input/prompt/audio/peer-order pair完整输出相同；sync后继96行全部实际Consumer应用，R1后继batch早473–577ms；其中6个R0/R1×repeat batch新增期限信用分别8/4/12/12/12/2音频秒。
- `:74–87`：合法兼容正常decode与covered无用工作确实同run共存；但正常最多17newtokens、最长model1.2919s，不是2swatchdog误杀长合法工作证明；91cancel的request→ACK最大0.645s、ACK→drain最大1.643s，**没有稳定全场节能**。

v9 `sections/05_execution_only.tex:3–15` 已用675pair、96row、473–577ms和scope写入。可加强的地方是图形清楚画出 **request→ACK→drain→next dispatch→actual apply→D2/C8命中**，无需增加新GPU。它比历史scale-out更直接支撑DSN的可靠资源生命周期。

### 5.3 当前两客户端 admission 机会已实测NO-GO

`experiments/dsn_strengthening_20261031/INTERFERENCE_FINAL_REPORT_v1.zh.md:3–14`：probe源2198b8d517e068cb8a08e0bc022104b4fed4c8c7、实际NN源4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47；4原来源、A先B晚2s、两repeat固定门。r0 Full对B C99多1.799878s，但r1仅0.132839s；额外C8miss均0，合取门NO-GO。

`:22–38`：16probe requests D2/C8联合门全失败；energy按真实共有origin→certifiedEOS及→model/CUDA drain分别报告，不能按client归因。`:40–47`实际原dispatch/lease/queue证据与1190转移独立复核保留。

这使“开发新admission controller”当前不具优先级。旧c12 admission成功也不能越过该固定门来拯救：旧 `docs/reports/tail_robust_admission_closure.md:3–63` 是另一selective/risk-bound结构，c12 heldout maxP99 1.877s、U95 1.868s虽好，但120s no-reset age profile P99 **5.367s、240miss**；c14原点继续拒绝。应作为历史边界，不应拼入现代exact/完整纠错合同的服务承诺。

## 6. 对论文的选择与后续最小实验建议

### 6.1 现在就可做的高性价比改动

1. **主文保持当前合同。** 加强物理释放至服务的因果图/短表，让审稿人清楚看到“完成合法、持续可见、物理资源释放”三条时钟；数据已经齐全。
2. artifact增加一页 **historical execution-capacity ledger**：TC-LIVE和早期available-input分开，列actualsource、rho、precision、Consumer时钟、journal、offered及独立来源数、质量、能量窗口、正点和负点。这样保留工程深度，又不借错合同扩大主张。
3. 如篇幅允许，Discussion只用一两句旧live教训：同8卡0.6B点，throughput约不变但displayP99与能耗改善；**明确其volatile和旧Owner-display时钟**。不要用“current full protocol has proven64-session scalability”。

### 6.2 若要新增一个真正提升DSN说服力的资源实验

首选不是重新追求50xRT，也不是新取消规则，而是回答 **当前完整合同的服务收益，在增加资源后保留/消失的边界是什么？** 只有论文要明确主张可部署scale-out时才值得做。

最小设计：冻结当前完整NN/Owner/Consumer/WAL源、同一16或24独立来源集合、同模型/precision/rho/完整输出预算、同offered时钟与请求序列；比较一个单P/A对与两个独立P/A对（若确有4卡资源），分别在一个欠载点与一个压力点做3freshprocess重复，R×S只保留能回答假设所需的四臂。所有臂同资源机会、相同调度实现。若只有2卡，不用旧8V100或虚拟oracle冒充这个实验，可保留为limitations。

必须同时给：all-offered D2/C8信用和miss、实际Consumer连续性、完整selected histories/输出质量、真实两/四板共同窗口能耗、wall到物理drain、实际source/音频独立性。变replica/peer会改变浮点执行shape，不能预设完整结果相同；按实测报告quality与selection。源身份必须另行cleancommit+manifest冻结，不修改旧CURRENT身份冒充同源。

可证伪预期：增加资源应改善首次D2及时性，但兼容跨根交错减少时，R×S的额外信用可能收敛；持续视图保留的语义区别仍成立。如果欠载后差异消失，那是机制机会取决于relative progress的解释证据，仍能加强论文，不必制造“所有点共同最优”。如果开销/quality或full-output合同使规模收益很小，保留负结果并缩短部署主张。

不建议为了这次“遗漏检索”立即启动该矩阵：当前v9的主信息是支持条件与持续交付，而非水平扩展。先由主线需要决定是否补它；上述旧记录足以表明研究机会存在，尚不足证明当前收益已经在大规模兑现。

## 7. 本轮新查实的事实与范围

- 本地解析两个真实执行commit：c1783c9751967be124c357425d9a4e2dc70ce44f、346be02998758a0db211d9ed64358b4ca251f126。
- c178源码字节SHA与原provenance匹配，定位到Owner-display与expected-event分母。
- 原c64 JSON集合统计64session /12source /12audioSHA；直接读取各repeatendpoint，没有重新推断GPU性能。
- 检索到的历史强正例、c64 1.7B/c128/质量/admission/长龄负例全部保留；没有以report的“PASS”标签覆盖其scope。
- 本文只是证据检索清单，不是新执行源、正式实验结果或当前部署验证；没给旧run重贴当前commit/合同。

## 8. 追加：modern dsn_* 全链检索与 v9 呈现差距

本追加按Root要求覆盖现代DSN实验族的入口、主要结果、后续解释及v9对应正文。仍只读，没有运行旧reader或新实验。这里的“值得补强”主要指**已有证据的解释和可视表达**；没有发现一张可以合法替换当前失败边界的隐藏大胜表。

### 8.1 覆盖路径与已被采用的内容

| 实验族 / 本轮实际读取入口 | 查到的核心证据及版本边界 | v9状态 |
|---|---|---|
| `dsn_service_stability_20261028/RESULTS_FINDINGS.zh.md` | f0源36格，3204前沿路径，c8 pass/c16 D2 fail；R-only兼容撤回45次，joint0；实际物理工作、wall、energy不同端点 | `05_operating_boundaries.tex`已纳入工作区间和成本；不是遗漏的主实验 |
| `dsn_midpoint_continuity_20261029/MIDPOINT_FINDINGS.zh.md` | 12探索格完整，D2全fail，strong witness STOP；secondary窗口与完整非EOS强见证不同 | v9已纳入12-session边界，不能把它改成成功点 |
| `dsn_full_interval_case_20261029/README.zh.md`、`dsn_story_revision_20261031/FIG1_COMPARISON_AVAILABILITY.zh.md` | 完整非EOS2秒段首显及时、后兼容撤回37字符、2.176s缺口；原案例为posthoc、两臂不同时序 | v9首页已加入真实Joint对照并正确区分D2+27.4ms、跨臂首显差583.5ms；不能再以“补Joint面板”为新建议 |
| `dsn_joint_retention_exit_20261028/RESULTS_FINDINGS.zh.md` | 24格，675同完整processed input/peer输出一致，96后继行真实消费，部分改变期限命中，ACK≠drain | `05_execution_only.tex`已压成一段；**链条可视化仍明显弱于证据本身** |
| `dsn_streamcorrect_adaptation_20261028/NATIVE_RESULTS_REPORT.zh.md` | 旧61c9双会话14格；三臂formal全0/4通过；strong Sequential18.5s>Joint17>Drop12.5；Joint energy比Sequential高84.94% | 当前主文选择单链新实现，旧饱和负点保留为边界合理；不可把旧Joint对Drop优势写成对完整顺序对照胜出 |
| `dsn_native_content_20261029/RESULTS_FINDINGS.zh.md` | bd18只读old14：Joint17s first-cover均append，但总文本擦除57>Drop22；原音频信用不是新增文字量 | v9已用更后final4f内容重计替代headline；旧14统计只适合artifact，不宜再回填主图 |
| `dsn_streamcorrect_stage_profile_20261029/RESULTS_REPORT.zh.md` | 41dea69步full state/C/IDs保真；64个non-None C，A约435ms/C约269ms，非部署handoff；h>0.47只是忽略税的必要粗界 | v9方法只一句developmental control；可补“为什么选full-call对象”的设计依据，不能用A/C分解预测实测吞吐 |
| `dsn_streamcorrect_stage_handoff_20261029/PILOT_STAGE_COST_AND_DECISION_v1.zh.md`、`CONFIRMATION_INDEPENDENT_FINDINGS_v1.zh.md`、`CONFIRMATION_CONTENT_AND_SERVICE_REVIEW_v1.zh.md` | 单源三臂pilot已真实做出ready_handoff；5hit、19包、capture→admit48.09ms；随后bdfa旧4源16格确认 | 正文主讲最终full-call恰当；**所选对象的成本取舍几乎消失** |
| `dsn_streamcorrect_encoder_profile_20261029/RESULTS_REPORT.zh.md` | 316b组件13calls，4对错完整反馈下E逐bit同、接收后原D/C/U保真；4/14使用率下eager全税账−0.305s，STOP | 当前v9未展开，适合小型设计取舍表/appendix；不能伪装为服务cache或普遍不可行性 |
| `dsn_streamcorrect_independent_20261029/FINAL_INDEPENDENT_RESULTS_v2.zh.md` | bdfa新4speaker16格；272完整转移；92在途promotion，其中20自身预测end被原C改变；信用37→66.33975、8/8pass；2必要撤回+1兼容保持 | `05_native_retention.tex`已明确早期独立bank和20/92；**机制反直觉点可比数字更显眼** |
| `dsn_native_refinement_20261030/FORMAL_MODEL_RESULTS_v3.zh.md`、`SHORT_ACTUAL_TRACE_RESULTS_v2.zh.md` | deb326有限模型20305states/36941edges/27controls；短开发6格102 durable、305Consumer、107links；short缺natural compatible/closed-buffer事件 | v9有有限模型界和最终actual36，不把6开发格补充计数加大样本；已正确 |
| `dsn_native_sustained_20261030/SELECTION_RULE_v1_FROZEN.json` 与两份 `LONG_REFERENCE_PLAN_*_FROZEN.json` 的路径/阶段身份 | 该目录主要是新两speaker×24utt的metadata-first选择/采集/参照计划；selection源6ad60，旧8speaker排除；不是另一组独立服务结果 | 最终服务结果位于resilience族，**不能因有两个目录就double-count长流** |
| `dsn_native_resilience_20261030/FINAL_LONG_NEGATIVE_SYNTHESIS_v1.zh.md`、`SUSTAINED_STATE_BOUNDARY_READING_v1.zh.md`、`SYNTHESIS_NOVELTY_ROUND5.zh.md`、`EXISTING36_EVENT_WITNESS_DECISION_v1.zh.md` | 875连续+875restored对照、3500在线步骤；8长流全服务/质量fail；4实际view跨worker exit；旧36无completed buffer安装，后来定点buffer4另补 | v9已把长流降为state stress，已新增buffer4。早期报告“c4尚未完成”是历史状态，不能用作当前unknown；**边界时间先后及对象生命周期可更清楚** |
| `dsn_strengthening_20261031/ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md`、`FINAL_R1_EXECUTION_REPORT_20261031.zh.md`、`INTERFERENCE_FINAL_REPORT_v1.zh.md` | final4f matched32/resident4、受控buffer4、固定admission4 NO-GO；ff95派发全账5529、条件1901、分层C/R/U及354/352/354 | 最终6/8、7/8、能耗增10.61%、buffer身份和NO-GO均保留；**分层条件机会表被压到只剩混合360/1901** |
| `dsn_writing_closure_20261031/FINAL4F_CONTENT_RECOUNT_REPORT.zh.md`、`FINAL_WRITING_AND_RESEARCH_REPORT.zh.md` | 6eb663零NN扫20trial/32requests/544facts/1604Consumer；final4f同G支持22.5→51、24→50.259；唯一非空兼容view1/1、0.81686s观察保持 | v9内容图和措辞已充分吸收，不应再建议换回早期29→51.518或把音频量改名正确文字 |
| `dsn_story_revision_20261031/CORE_PRESENTATION_AUDIT_v1.zh.md`、`dsn_editorial_delta_20261101/{EDITORIAL_DIFF,CLAIM_REVIEW,FIGURE_HANDOFF,READER_CHECK}.md` | v7→v9修正区间/整场、core/native角色、AU/SUP各自事件、原正控身份、图中两种support与实际Consumer；core主图已从卡片改因子图 | 这些问题大部已闭合；应对现稿提出新增价值，不重复前轮已完成的rename/重画/增引用建议 |
| `dsn_manuscript_update_20261028/IMPLEMENTATION_CLOSE_DECISION_v1.zh.md` | 在新4speaker结果前冻结选择bdfa full-call；stage/E停止有事前理由，非事后将外部基线改成自己方法 | 有利于说明作者提出的组合与对象选择；不宜在主文复述实验开发流水 |

比较用v9可达正文：`03_native_extension.tex`、`03_native_refinement_working.tex`、`04_native_resilience_working.tex`、`05_evaluation_core.tex`、`05_operating_boundaries.tex`、`05_native_retention.tex`、`05_execution_only.tex`、`05_same_source_validation.tex`。本追加是TeX/证据映射检查，不冒充新的PDF视觉验收。

### 8.2 五项具体补强，按价值排序

#### A. 把混合360/1901改为可解释的四行机会账（最高优先级）

**目前隐藏的不是好点，而是分母结构。** v9 `05_same_source_validation.tex` 末尾给360/1901、1541refuted后仅说workload-specific ratios remain separate，却没展示各层。原 `ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md:11–22,69–74` 有完整表：

| 固定证据层 | 条件派发 | 完整输入确认 | 后来durable/Consumer使用 |
|---|---:|---:|---:|
| Normal short |57|40 (70.18%)|40/40|
| Controlled faults |90|58 (64.44%)|52/52|
| No-reset S0770 stress |924|96 (10.39%)|96/96|
| No-reset S0903 stress |830|166 (20.00%)|166/166|

坏长流占1754/1901派发，混合18.94%不是“生产预测准确率”。保留四层一起展示，读者才能理解条件执行何时有机会、何时因原任务退化失去机会。建议用四行紧凑表代替当前末段部分散文；若图，画每层C/R/U堆叠并以小标记给durable-use，**不画跨层总体置信区间、不混成预测accuracy**。所有计数已有frozen输出，不需GPU或新reader。

科学价值：把“input confirmation与use不同”从声明变为实测关系；同时诚实解释长期坏任务为何不能靠协议保留挽救。它比又加一个总speedup更能回应deployability与机会分布。

#### B. 用同一job的身份图展示“匹配结果活过producer，旧消息仍被隔离”

v9 `05_same_source_validation.tex:49–64`已有两matching/two mismatch buffer控制，但最强设计区别藏在短段里。`FINAL_R1_EXECUTION_REPORT_20261031.zh.md` 的buffer4段和b867独立重计给出已接收完整C/U buffer保原child UID/birth/incarnation，在真实producer exit/CUDA release/sealed-channel validation/fence后，等原parent确认再install/consume；同输入不匹配的两负控拒绝。**不是producer活着才使结果有效，也不是worker death后可重新授权旧消息。**

建议一个小型对象生命周期图（可替代正文中若干重复故障解释）：上轨“accepted full result”横跨producer exit；下轨“new late message”在fence处红叉；末端分为same-start parent→AU install、different-start→reject。原UID贯穿，不给它画新birth。另以虚线区分“已有ASR view跨death直到合法correction”的4个原36事件，避免把view存活冒充完整C/U buffer安装。精确原event索引在 `EXISTING36_EVENT_WITNESS_DECISION_v1.zh.md:5–16,24–29`。

图旁可用实际354 durable /352原Owner install /354Consumer的两个缺口说明selection、installation、replay不同：`ACTUAL_PAIRING...:24–37` 两个post-durable/pre-install死亡fact由新Owner原身份replay，没增加新选定边；六confirmed conditional job未durable的原因另列。原4eb CLI/执行compound gate失败必须仍在artifact，不把b867零NN重审改写为原执行gate全绿。

科学价值：直接把中心保留对象与DSN的fail-stop、fencing和durability连起来，增加完整协议的可理解性；强于单列“零非法安装3976次”。

#### C. 把“为什么保留完整调用”写成一项有证据的对象选择（重要但可放appendix）

目前v9 `03_native_extension.tex`仅将ready-only ASR handoff称为developmental control，没有说明为何最后选full-call。已有的两条负/边界证据能提升设计深度：

- `PILOT_STAGE_COST_AND_DECISION_v1.zh.md:9–15,20–40`：同源单次三臂、每臂8.068s offered、同2完整FP32worker；full-call8.0s，ready-handoff6.5s，conservative3s信用，**三臂whole-run门均失败**。ready-only真正hit5次、19packet实际capture→admit中位48.09ms，另4个same-input producer尚在途窗口。不能以历史285ready机会取代5actualhits，不能把未测join端到端收益补进去。
- `dsn_streamcorrect_encoder_profile_20261029/RESULTS_REPORT.zh.md:3–9,26–35`：E细对象在完整反馈失配时仍4/4神经保真，但按4/14使用率支付完整eager生产/传递/校验税，0.670275−0.843307−0.132044=−0.305077s组件work余量，停止该carrier。不是实测部署慢305ms。

建议三行“retained object / witness / measured tax / decision”设计表，严格标developmental service pilot、component profile、final implementation各层；核心教训：**可复用的更细对象不自动成为更好的服务优化，输入依赖、确认时序及交接税共同决定边界。** 该教训支撑作者的具体组合设计，而不是仅宣称把现有检查模块接在一起。无需增加取消算法、cache工程或新模型网格。

若正文仅有两三行空间，保留E“合法但经济性不成立”的结论及artifact指针即可，不用把single-source三臂数字挤入主性能表。

#### D. 将R×K短段升级成“物理释放如何兑现期限”的真实链

当前 `05_execution_only.tex`列675pairs、96rows、473–577ms，信息正确，但把机制因果压成数字列表。原 `dsn_joint_retention_exit_20261028/RESULTS_FINDINGS.zh.md:49–65` 已具足够事件证据：request、安全点ACK、actual batch drain、下一batch dispatch/compute、actual Consumer apply、同targetF首次D/C六段。

推荐一个紧凑真实时序inset，只选事前scope内r1/R1具体见证并标其来源：request→ACK **22.196ms**，ACK→drain **13.359ms**，后继16行实际Consumer首次消费早 **456.5–573.0ms**，其中 **6 miss→hit、10本来hit**；同输入/完整output/peer顺序已对上。三重复的R1 switch数6/6/1保留，图不将整batch16行都涂成新增信用。

这能让审稿人理解物理lifetime为何是协议一部分，且自然解释为何ACK不是release、被Owner obsolete不等于整个输入义务失败。同步/错峰mixed效果与无稳定energy收益继续用一句话保留，不能宣称R×K普遍协同。这个图形收益无需新NN，优先于旧V100扩展表。

#### E. 长流把“先服务失败、后长度条件”可视化，避免错误根因故事

v9已诚实报告8/8fail、449–503s D99、巨大原任务CER、875连续参照及64-entry窗口。但末段把服务边界、原decoder长度条件和offline oracle挤在一起，读者难以看到其诊断意义。

`ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md:41–59`已有8条**实际位置**：

- S0770 Full-call r0/r1首次D2失败位于21/20音频秒，首次C8失败32/31.5秒；原after-trim≥448条件59.5秒；宽松offline excess-length下界首次>0为27.5秒。
- S0903 Full-call r0/r1首次D2失败11.5/11秒，首次C8失败23/21.5秒；after-trim≥448条件128.5秒；offline下界首次>0为16秒。
- Conservative更早失败，原质量边界两策略同位置；这些audio坐标不是wall时刻，length条件也不是逐分支decoder guard探针。

推荐artifact一张按audio位置的双source事件尺，画各臂首D2/C8fail、offline长度下界、after-trim条件，拒绝画不可识别的每500ms prefixCER。正文用一条直接教训：**观察到的服务和插入异常早于长度条件，因此不能把所有退化归因于448；状态闭合正确也不保证任务质量/容量。** 不要把条件命名为唯一root cause，也不把它转换成在线reset/VAD策略。

若需展示资源稳定性，另画原wall轴上unreferenced terminal/audit窗口与live/pinned closure，横轴保留input end后的drain；模型cut/累计transcript/RSS不同对象分开。不要给糟糕长流安排半页“服务性能胜利”图。主文只需结论，诊断细图放artifact；这一边界证据会让DSN读者更信任短流正结果。

### 8.3 优先级与应避免的重复劳动

建议先做 **A分层表 + B身份/生命周期图**；它们最能提高当前主线的解释力。C作为设计理由或appendix，D为现有执行短段的小inset，E保留artifact诊断即可。不是要求五项全部挤进11页。

不建议再补一轮final4f内容计数：已有22.5→51、24→50.259和180/14/166已经把文字量、准确性、在线SUP、期限覆盖分开，v9基本充分采用。也不建议再次把92promotion里20个own-end变化包装为新current4f统计，它属于早期bdfa独立bank。这个反直觉机制可以在native方法与Finding2更早强调，但版本边界应保留。

上述五项均可仅用已有冻结有界事实形成可复核初稿。只有在选择做更细原始事件图、需要未导出的绝对行时钟时，才另冻结只读分析；不要为了画得丰富捏造中间事件或打开GPU。新的科学实验机会仍是前节的当前同合同资源扩展，而非从上述旧结果推测一个新调度器必然成功。
