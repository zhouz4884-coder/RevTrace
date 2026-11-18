# 原生R×S：有界收集与发布配方

2026-11-18。此文件与配套helper只准备收集/发布清单，不访问SSH、不改运行时/控制器、不调用GPU、不执行Git写入。本计划不是80格已完成的结果声明；最终状态以Root的代际闭合收据及实际GATE为准。

## 1. 本轮身份与必须分开的证据

| 角色 | 完整source commit | 文件数 |
|---|---|---:|
| 实际NN/服务运行时 |11453433c154aeffbff703c4c8dc9697421430e1|67|
| 参照/服务控制器 |1bd3b01265a57d844c192e88573dc2a13860f64f|22|
| 独立视图/连续性审计 |0571d51d85542e1eaf000be8082585a66e5978be|20|
| 资产/音频就绪检查复用源 |3fb1951ba58b74110403c72d885efa8077e3140c|3|

源包以`packages/{RUNTIME,CAMPAIGN,AUDIT}_SOURCE_V1.{json,bundle}`中的真实执行身份为准。完整plain snapshot按manifest逐文件复制，禁止对source目录直接无差别rglob复制`.git`或缓存。Readiness的3文件manifest/bundle另保留，不能当成第4个新神经运行时。

315/72/53是三套已冻结CPU suite实际日志中的测试数，均有独立CONFIG、ENVIRONMENT、RUN_RECORD、SUMMARY、GATE和CPU_CONTROLS.log；它们不是440种新故障或440次GPU实验。CPU_READINESS_V1、模型全字节gate、8条音频/header/来源信息单列。

还要保留production_support `a13fa0a335529dc188f7e738877a3acd027ce4a7` 的18文件依赖身份。如果它已有已验证公开bundle/plain snapshot，可记录精确提交、archive路径与SHA；三个新source bundle本身不代替这项实际执行依赖。原作者StreamCorrect/模型代码与环境依赖沿实际环境和资产manifest追溯，不重新打包模型权重。

## 2. 两个premodel失败必须完整保留

- REFERENCE8_V1：`FAIL_PREMODEL_ASSET_RECEIPT_SCHEMA_PRESERVED`。资产收据schema在模型import/load前拒绝；输出目录未创建，model_calls=0。保留原plan/prelaunch、PID/start_ticks handle、原process.log、ROOT_CLOSEOUT及修复解释。
- REFERENCE8_V2：`FAIL_PREMODEL_SELECTION_ORDER_BINDING_PRESERVED`。source顺序与原选择收据的严格顺序不符，仍在模型执行前拒绝；model_calls=0。保留同样身份。不能把“改回收据原顺序”写成改科学source集合。
- REFERENCE8_V3是实际付费参照生成：141 continuous full-step＋282 restored-input full-step，加1个固定warmup，共424次full-step调用。其中133＋266＋1=400次记录为native模型已评估；不是400个底层ASR/Transformer forward。八源全部原状态、原C和返回IDs相同，REFERENCE_DETAILS.json实际4,972,725字节。

这三次attempt分开归档，不能把V1/V2标成“GPU参照失败后择优V3”，也不能把V3参照成本并入服务能量/信用。

## 3. Root可直接使用的收集请求

`ops/prepare_collection_requests.py`已在本地执行，生成`COLLECTION_REQUESTS.json`：

- 80个冻结cell，五condition各16格；pilot20与confirm60分开。
- 1626项显式remote→local请求，包含原冻结config及其已知SHA、每格有界结果与代际记录、两阶段campaign记录、参照文件和两个premodel失败日志。
- 80个raw hash-index请求，指定原trial root、外部power和process log，**没有授权下载这些bulk原始流**。
- 三个新源manifest/bundle及plain snapshot逐行验证；Readiness依赖另列。

重新生成请求：

```text
python -B experiments/dsn_native_joint_retention_20261118/ops/prepare_collection_requests.py
```

每格mandatory有界文件为：

```text
CONFIG.json ENVIRONMENT.json RUN_RECORD.json ORIGIN.json GENESIS.json
SERVICE_END.json SUMMARY.json GATE.json
EXTERNAL_FACTORIAL_AUDIT.json INDEPENDENT_VIEW_AUDIT.json
WORKER_TIMER_LEDGER.json JOB_ACCOUNTING.json SAMPLED_ENERGY_OWNERSHIP.json
view_audit/{SUMMARY.json,GATE.json,CANONICAL_SUPPORT_EVENTS.json,OBSERVED_LOSS_WINDOWS.json}
```

还应收取两阶段`records/*_{PRELAUNCH,HANDLE}.json`，如有技术失败则额外收取对应FAILURE_CLEANUP/CLEANUP_UNVERIFIED，不只收成功记录。每次SLO未通过、每个zero-opportunity/tie的SUMMARY全部保留，不能用达标率筛文件。若某trial技术失败、某文件未生成，收集manifest应明确标missing及原失败gate，而不是补空JSON或0。

### 逐字节收取与raw hash方法

1. 先用同PID＋start_ticks核实controller结束，核实实际model worker/CUDA ownership已释放，保存Root resource closure。不要把SSH超时当worker死亡。
2. 在原盘对已闭合trial读取原GATE、EXTERNAL_FACTORIAL_AUDIT等闭合标记。对所有raw普通文件和该cell外部power/process log流式SHA256；hash前后比较size/mtime，变化则不宣称稳定快照。禁止跟随symlink或把路径扩展至models/data/cache目录。
3. 保存`raw_hash_indices/<phase>/<cell>.json`，每项含实际绝对/相对path、bytes和sha256。参照原目录也另做hash-index。模型、WAV、完整power/consumer/publications/worker/Owner事件流、facts.wal继续留8TB。
4. 对每个有界请求先取远端bytes/SHA，再通过已有批准传输路由下载，下载后重验长度与SHA。REFERENCE_DETAILS必须同时等于已完成reference receipt中的4,972,725字节与原SHA。
5. **source config和raw CONFIG可能JSON字节布局不同**：只对原冻结config使用plan中的config_sha256；raw CONFIG保留自己的remote字节SHA，并按parsed object绑定到冻结配置。不要重复旧fixture序列化错误。
6. 每文件自动上限8MB；总payload soft96MB、hard128MB。超额时Root先审查重复性或非bounded误收，不按结果好坏裁剪、截断或删SLO失败。主SUMMARY、每格结果与全部80配置不得因负面结果被剔除。

## 4. 本地publication候选helper

`ops/build_publication_candidate.py`只读本地allowlist，生成`PUBLICATION_CANDIDATE.json`；不复制到Git工作树、不stage、不commit/push。

```text
python -B experiments/dsn_native_joint_retention_20261118/ops/build_publication_candidate.py
python -B experiments/dsn_native_joint_retention_20261118/ops/build_publication_candidate.py --require-complete
```

最初只收参照与准备材料时的本地库存为293文件、10,949,948字节；补入明确名单中的10个运维/收集脚本及审阅记录后，最近一次为305文件、11,023,660字节。它们**不是后续固定大小，也不是0个GPU格完成的远端判断**。helper字段`collected_complete_serving_cells`仅指已落本地的完整cell集合。

最终`--require-complete`要求80个cell的指定有界结果与view_audit文件齐全、原任务gate成功、两阶段campaign处于COMPLETE，同时230份只读论文文件字节不变；SLO失败仍可满足原任务gate。否则不能生成完整80格发布状态。候选中只累积明确的metadata、source包和有界结果，不收`.jsonl/.wal/.wav/.safetensors/.pt/.bin/.pdf/.zip`等bulk/model/paper材料。

当前helper已验证原`MANUSCRIPT_READONLY_SNAPSHOT.json`所列230个文件长度和SHA全部不变。Root最终发布前必须再跑一次；发现外部修改应保留差异记录，不自动reset或覆盖论文。

## 5. 最终报告、身份与发布顺序

最终有界报告应至少包括：

- 五condition的原始全部offered信用/coverage/whole-run结果，原SLO miss完整保留。
- S0/S1 actual compatible-ahead机会、avoidable/necessary/unknown撤回、removed audio-s、observed gap与分类window/censor范围。总high-water gap和same-root分类union不冒充可相加的同一量。
- 按source/repeat四臂配对与I、R/S直接效应，以及Conservative同期锚点。
- 真实model-active handover、重派、完整job终态守恒、worker wall与abort infer NA、两板service-origin→physical-drain J及sampled PID/UUID所有权。
- 两个premodel失败、V3独立付费reference、80个实际serving格各自的gate、资源闭合、source实际commit；archive GitHub commit只标作归档身份。

Root发布前先检查现有公共工作树HEAD、remote/main和dirty状态，可能已有其他v22写作提交；不要以旧交付commit为当前值，不pull/reset旧dirty根。用新的`codex/`分支或隔离工作树，仅stage本实验allowlist。必须确认没有160000 gitlink、嵌套`.git`、模型/音频/缓存、论文PDF/源码或凭据。执行源码plain snapshot按完整manifest给出，不依赖子仓库指针。

生成最终delivery manifest并核验**实际Git index blobs**的bytes/SHA，再commit与正常fast-forward push；不force。推送后核实remote/main commit/tree及关键blob/manifest。公共/匿名稿件仓库的更新是另一事项，本轮不修改稿件，不刷新匿名入口，不操作投稿门户。

所有结果准备完再报告科学结论。零S效果、极短gap或负交互都要作为真实结果保留；不能因“能否提升竞争力”预先筛选提交内容。
