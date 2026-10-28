# 实际提前显示是否与后来 Canonical 一致

`canonical_usefulness.py` 是独立的离线重计数工具，只读现有 trace；不改 frozen runtime，不导入 GPU 库，不重新运行模型，也不更改 `aggregate_service.py` 或归档的 v4 聚合。

这里的“一致”只表示**实际完整可见文本与同一音频 F 上实际被选中的完整 Canonical 文本一致**。不是参考转录正确率，不是可在线使用的认证，也不能把它作为策略的未来输入。最终 WER 保持单列。音频前沿没有回撤，不代表文本没有修订。

## 固定口径

1. Canonical 必须有真实 `commit`、同 job 的完整 Authority worker result 和 `canonical-display`；校验 F、version、完整文本、选中 Z/P 和可用的文本字节哈希。禁止从更晚音频前沿的文本中截取“相当于早期 F”的文本。
2. 从实际 Consumer 的 `valid_visible_frontier > certified_frontier` 识别提前视图。原始字符串完全相等与规范化相等分开。规范化严格记录为 NFKC、casefold、弯撇号转 ASCII、Unicode 字母/数字和内部撇号分词、忽略其余标点、单空格；这种变换不保证保留语义。
3. `selected_lead_seconds` 是实际 Canonical 安装时刻减 Consumer 观察时刻。已经选中、只是在 Consumer 认证之前可见的视图单列，不能混成计算提前。另列直到实际 Consumer 观察该认证快照的 lead。
4. 主音频口径是**所有 offered frontier 的分区**：每个区间的 `audio_seconds` 只计一次，分给第一次实际覆盖它的完整 Consumer 视图。该视图 F 可大于 offered F；比较仍严格在视图 F。重复显示不会再次增加音频信用。
5. 逐一保留未观察、首次即认证、首次提前但同 F 未匹配、实际后来才选中、已选中但尚未在 Consumer 认证，以及原始/规范化一致或需改写的音频秒。分别报告 display<=2s 和原双期限 2s/8s 信用。
6. rho=3 的非共同边界若无实际同 F Canonical，留在 `UNMATCHED_NO_SELECTED_SAME_F`；带权分母保留，不能用较晚文本、前缀、oracle 或更细 arm 的结果补成正确。
7. 所有实际提前视图的次数与 session-wall exposure 是另一个描述性表，不作为额外音频样本或独立 N。源级重复不增加独立 speaker 数；cohort、adapter、arrival、rho、phase 分层保留。

## 运行

完整 8 TB 原始结果在其机器上可直接按冻结计划路径读取，输出必须为新目录：

```text
python -B canonical_usefulness.py --plan ../packages/SERVICE_PILOT_v2_CONFIG.json --additional-plan ../confirmation_design/SERVICE_CONTROLS_PLAN_v2.json --output 新目录
python -B canonical_usefulness.py --plan ../confirmation_design/PLAN_v3.json --output 另一个新目录
```

已合法复制的组可重复增加 `--results-root 路径`，按 cell 名查找，不改变原计划。H3 v3 从实际 argv/output 定位，保留的历史 `out` 字段不会把 v3 运行重新指向 v2。

本地 `service_opportunity_v2` 只有有界原始 trace 与原审计，缺完整 FREEZE/RUN_RECORD/ENVIRONMENT。显式增加 `--allow-bounded-traces --results-root ../service_opportunity_v2` 才允许描述性重计数，状态必须是 `BOUNDED_AUDITED_TRACE_RECOUNT_SOURCE_IDENTITY_NOT_REVALIDATED`，不能伪装为本次重新验证过执行源的正式实验。缺失/失败的计划 cell 均保留在 COVERAGE。完整元数据可用时，校验原完成 gate、原审计一致、源 commit、冻结配置和环境哈希。

输出包括 RUNS、OFFERED_FRONTIERS、AHEAD_VIEWS、SOURCE_METRICS、PAIRED_EFFECTS、SOURCE_PAIRED_EFFECTS、四臂 FACTORIAL_EFFECTS 及 SOURCE_FACTORIAL_EFFECTS、COHORTS、COVERAGE 和带脚本/实际输入哈希的 ANALYSIS_RECORD。配对需相同输入、speaker cohort、执行源、模型数值合同、到达、rho、repeat、fixture 与 phase；四臂缺失则不生成交互。该重计数不另做显著性检验，24 speaker 的正式聚类推断仍应与完整 H3 聚合一起进行。

## 能支持的科学判断

这能检查服务层 deadline 改善是否主要让“后来同 F Canonical 也选择的完整文本”提前到达用户，还是把需修订/同 F 无法检验的文本提早呈现。两者都保留，才可讨论进展的实用性与修订代价。它增强“及时且有后续同 F 支持的进展”的机制证据，但不能单独证明识别正确、用户收益、确定性保证或新来源上的组合创新。若 H3 的保留×Consumer 交互在此端点上也可重复出现，才增加组合贡献的依据；Standard 同效仍是合法替代实现证据。

开发时只运行了微型合成口径检查（完整同 F、规范化分离、重复覆盖不重复计音频、非共同边界未匹配、已选中时刻分离）。这些不是研究数据。实际重计数需在计时敏感实验完成后单独运行。
