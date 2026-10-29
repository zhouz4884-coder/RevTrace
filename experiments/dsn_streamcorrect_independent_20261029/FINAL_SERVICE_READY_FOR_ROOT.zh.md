# 最终四新 speaker 的 16 格服务确认

已完成纯 CPU stage，未由本 agent 启动模型。root 可将 `CURRENT_FINAL_SERVICE_CANDIDATE_v1.json` 保存为机器 CURRENT 后执行 no-argument preflight，再运行 `../dsn_streamcorrect_stage_handoff_20261029/ops/launch_final_independent_service_v1.py`。launcher 自身重新验证 no-argument preflight、完整 38 文件、所有配置/参考/数据/appraisal hash、干净 bdfa checkout、无已有输出及 GPU empty。

- 唯一正式计划：`FINAL_SERVICE_v2_FROZEN.json`，SHA `cab424783f30ff9b53db8deef5eba482d3b101f15336b65de8b1c7d9ced3679a`。v1 保留但未使用；v2 仅修正 fidelity 文字并增加此次 revision 记录，16 个配置字节完全相同。
- 方法：选源前已冻结 bdfa3b1307d267a5a4caf6484e1ad465c39a592e。4 个 metadata-selected 新 speaker、每源两次 fresh process、两臂，8 个配对 block 随机化，repeat 交换 GPU 角色并反转每源 arm order。seed 2026102932。
- 全部 68 个 original-full 参考已真实完成、源和全 state/C/IDs 可查；参考不是服务结果。16 格共有 272 次完整 Canonical 步；每臂提供音频 1,061,436 samples / 66.33975 秒，含全部 partial EOS。
- 独立 CPU prerequisite 源：5ea7925201443f668d58dd997a5e4f6932966a5e；完整 5 文件 manifest、bundle、本地可解析 commit 及身份记录已保存。12 个配置反例/重复控件全过，实际远端全配置、完整 runtime manifest、5 WAV SHA/header、软件环境、全部参考覆盖及静态 appraisal 核验全过。CPU 门 `service_cpu_v1/GATE.json` SHA `50f3e411a7bb6d0e3113b7eb01b2e5f5592f038c82322414260b184c23c4af6a`。模型/GPU 调用数为 0。
- bdfa campaign 原审计器保持不变；其删除 stage_execution 的旧投影不构成本轮完整 fidelity 硬门。SC 独立后分析必须要求本轮参考与服务的全部 state、完整 start、C、ID **含 stage_execution** 严格相同，不投影任何字段。
- 主要方向确认的静态规则已在新参考 NN 前冻结：全部 16 格严格有效；8 个配对原 A2,8 差合计为正且至少 3/4 speaker 的两次差合计为正。4 个声学独立单位，8 个 timing pairs；不把八次当八个独立来源，也不要求 8/8 全胜。
- whole-run D99/C99、C50、两 GPU 能耗、actual-G 完整首见文本后验 Canon 支持、CER、实际 model-active promotion/已知输入失效退出均独立报告。无论结果正负仅此组，不换源、调方法或改期限。

实际 raw 留指定 8 TB 盘；有限收集后逐文件核 SHA。首次 handle 本地为 `FINAL_SERVICE_HANDLE_v1.json`，remote 位于 `results/revtrace/dsn_streamcorrect_independent_20261029/FINAL_SERVICE_HANDLE_v1.json`。不得把瞬时 GPU empty 当整组完成；必须检查该 exact PID/start/cmd identity 消失且完整 16 格 GATE PASS。
