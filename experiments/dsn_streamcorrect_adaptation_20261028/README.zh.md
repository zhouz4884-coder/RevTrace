# StreamCorrect 有界适配：当前完成状态

2026-10-29 最新状态：两个真实 native witness 与原定十二个 formal 格、冻结后分析均已完成。完整结果见`NATIVE_RESULTS_REPORT.zh.md`，当前状态以
`CURRENT_STATUS.json` 为准。用户指定 ModelScope 路线后，已发现公开原版发行并核验其原始权重身份。
`modelscope_metadata_v1/EXACT_WEIGHT_IDENTITY_PROOF.json` 记录了 ModelScope
SHA-256 重建出的 Git-LFS pointer 与 Meta 官方公开 tree 的 blob SHA-1
完全匹配。此前 HF 单一路线的 401 限制已经解决，不再据此停止此线。
全部原始资产现已取得，并完成31项原始文件及2项辅助元数据的独立完整 SHA 核验。
ModelScope 的身份依据保持冻结；
传输改走已证实相同完整字节身份的公开 HF 发行，保留部分文件并独立核验完整 SHA，未更换模型。

当前实际神经执行源码为 v8 `61c9afac00561f7ff1351f3eba9fd95adb239e8c`；
有界源码快照、完整 bundle、逐文件 manifest、25项CPU测试与实际双卡median合法oracle控制均已冻结。
原始 v6 初始化失败及 v7 不正确的非负输入域控制失败均保留，随后只修复原生依赖API与作者遥测时钟接口。
两个完成的 witness 在独立离线审计修复后满足原门控：17个非空raw-changed交错与36个unchanged交错。
这些标签不等于语义纠错收益。正式三臂各4格完整Canonical状态/输出历史一致、CER均为8.79%；
原插值D2/C8整格均0/4通过。信用sequential18.5s、drop12.5s、joint17.0s，offered均66.42975s。
当前500ms双会话点不能声称native部署SLO成功；Joint减少相对drop的重算和进展损失，但未超过强两副本sequential。
离线审计源码 `a0652a81a205483ba2091dfd345b85be72ee8b19` 只修正空文本应显示前沿0的预期，
完成的正式执行仍调用未改动的v8服务源码、原冻结配置/顺序；没有重放或重标两格原始神经执行。

以下首先保留此前 CPU 阶段和访问探针的历史记录；这些不是后续实验结果。

## 已完成的具体工作

1. 对照 ACL 官方完整论文及作者固定源码，定位了真实的候选生成、
   SpeechLM 选择、selected token feedback 与 cache/beam reset 入口。
2. 找到作者真实发布的 LoRA 权重，排除了“setup 占位符等于没有发布”
   的错误推断。作者 HF 账号 `playwithmino` 的主页链接同一个
   `vu-duy-tung` GitHub 账号。公开资产与具体文件身份记录在
   `PROTOCOL.md`、`public_asset_metadata_v2/`、`public_asset_metadata_v3/`
   和 `author_checkpoint_metadata_v1/`。
3. 实现了直接调用作者原生 `PaddedAlignAttWhisper.infer` 的桥接接口，
   没有重写 corrector 的 prompt、generate、候选清理或选定 token 规则。
   兼容切面纳入实际音频 buffer 字节、token 分组、context、对齐游标、
   语言、冻结模型/配置身份、输入前沿与完整显示文本。
4. 完成 13 项 CPU 测试：完整状态 roundtrip、实际音频字节突变、
   同文本但 alignment cursor 不同、逐状态字段扰动、缺少边界、
   旧分支迟到、变更合约、未清理 KV/beam cache 均有相应控制。
   **这些是合成 CPU 接口/约束测试，不是原生神经准确率或在线性能证据。**
5. 冻结了后续最小研究方案：四个 metadata 先选的 AISHELL 完整来源，
   分两个双会话 cohort；sequential / conservative drop / joint 三臂，
   fresh-process 两次，共 12 格。必须先自然观察真实修改与未修改选择，
   不按模型输出筛来源、不人为匹配根、不训练新模型。

## 历史记录：最初遇到的原生依赖门槛（已通过后续公开同一权重路线解决）

StreamCorrect 发布的 LoRA 确实存在；但它不是一个自包含 corrector。
底模 `fixie-ai/ultravox-v0_5-llama-3_2-1b` 的公开 1.366GB 权重仅含
其训练过的组件。固定源码 `ultravox_config.py` 会另外读取
`meta-llama/Llama-3.2-1B-Instruct` 配置，`ultravox_model.py` 的
`_create_language_model` 会另外加载该原始骨干。

当前本地对原始骨干 `config.json` 的官方匿名请求返回 HTTP 401；
本地和实验机均没有既有 HF 登录，预期 HF cache 与指定实验盘的模型目录
没有该原始骨干。证据为 `backbone_access_v1/SUMMARY.json` 和
`REMOTE_SUMMARY.json`，未读取或打印任何令牌。

因此，没有把公开 Ultravox 音频塔当成完整模型、没有用随机初始化或另一个
Llama 替代，也没有先下载约 7GB 资产后再宣称原生应用完成。
**原生神经调用：0；应用服务格：0；真实纠错/未纠错 witness：尚无。**
桥接接口仍待真实原生模型验证，其状态充分性不能仅由 CPU 测试宣告成立。

## 我的论文判断

这条应用线有实质价值：它能把“可信反馈推进与临时计算协调”落到一个已有的
纠错反馈流程，尤其能检验真正的修订是否迫使分支撤回，以及自然不修改的选择
能否留下足够复用机会。但它的价值来自完整反馈语义的接入，不能来自多写一个
模型名字，更不能把固定纠错轨迹重放写成原生服务测量。

它不应成为主论文必须满足的又一个成功条件。现有核心组合、独立来源确认、
服务区间和保留×物理退出证据可构成论文主线；本轮原生访问未满足时，正文不应
包含 StreamCorrect 的应用收益表或虚构的第三方接入结论。相关工作应继续准确
承认其真实纠错→后续前缀反馈机制。

恢复此线所需的是**已授权可访问的原始 Llama-3.2-1B-Instruct 骨干**，不是
再开训练或寻找一个容易成功的替代应用。获得该条件后，沿同一冻结方案继续，
首项检查为完整原生输入/状态 roundtrip 和 naturally corrected / unchanged
updates；没有这些 witness 就不进入三臂收益结论。

## 可核验执行身份

- 实际 CPU 执行源码 commit：`fd878ecf80a91bf7d883a92ccb391db3c4a1c3ae`。
  精确完整值以 `packages/SOURCE_v1.json` 为准。
- `source_snapshot_v1/` 是有界普通文件存档；`source_v1/` 是被本目录
  `.gitignore` 排除的独立 clean 执行 checkout。快照逐文件匹配同一 manifest。
- 完整历史 bundle：`packages/SOURCE_v1.bundle`，已导入主仓库单独
  `codex/streamcorrect-adapter-v1` 引用；没有变更主仓库 HEAD 或旧稿。
- CPU run ID：`DSN_STREAMCORRECT_CPU_INTERFACE_V1`。
  `cpu_gate_v1/` 保存冻结配置、环境、运行记录、13 项原始测试输出与 gate。
- 外部作者源码只 clone 到 8TB 实验盘；模型权重、音频和外部整库没有放进 GitHub。
