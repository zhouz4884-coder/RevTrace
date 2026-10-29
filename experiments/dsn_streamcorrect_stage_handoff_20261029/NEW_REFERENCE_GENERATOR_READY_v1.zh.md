# 条件性新四 speaker 原完整参考：工具已准备，尚未执行

当前只有本地通用生成器与纯 CPU 控件完成。**没有选择来源、没有读取远端 reference.json、没有下载 WAV、没有新来源最终配置、没有 remote stage、没有模型或 GPU 调用，也没有生成新参考。** 是否使用它由当前16格旧来源确认后的 root 决定。

- 实际独立 source：`reference_generator_source_v1`，clean commit `66abab7b8ce668a1a1ddefb65f6115af45e99cec`，5 文件。
- plain snapshot：`reference_generator_snapshot_v1`。
- 完整 manifest：`packages/NEW_REFERENCE_GENERATOR_SOURCE_v1.json`，SHA `406c743e44eac2f9defe1d85de15c5b66bedec8d65f2f8249fb81b45ca355561`。
- bundle：`packages/NEW_REFERENCE_GENERATOR_SOURCE_v1.bundle`，SHA `4efd37f882d835553392d8d0c8788f80e93c0d439ae35c02a2dbbf781f131cc4`。
- `NEW_REFERENCE_GENERATOR_LOCAL_PREFLIGHT_v1.json`：显式 source/manifest identity PASS、5/5 字节正确；生成器实际 commit 已从 bundle 导入当前证据仓库 refs，可解析，没有改 legacy HEAD 或 CURRENT。
- 13 项开发期纯标准库 CPU 控件 PASS，0 skip；不加载 torch/model、网络、ZIP 或音频文件。

工具严格导入完整、clean、逐文件 byte-matched 的**未修改 bdfa 方法 runtime**，不复制/修改方法文件。原 bdfa manifest SHA 和原 source0 config SHA 均固定；backend 必须与原 config 完全相同。source0 原音频与原 1.5→2.0 s warmup 状态也必须原样，真实 C 非 None 后丢弃/回 genesis。生成器 source66 与导入 model runtime bdfa 在 run record 分开记录；不把 bdfa 冒称整个新 oracle driver 的 source。

每条新来源从其自身 immutable-audio genesis 顺序调用 `CandidateBridge.full_step`：`on_asr=None`、`capture_required=False`、`before_corrector=None`，不早显、不推测、不做 stage handoff、不等待服务时钟。完整 source0 warmup 不改变新来源规则。原 C、IDs、完整输入/输出 cut、早期 None/empty、全部500ms点及最终 partial EOS 都写入参考；不会在结果出来后重新挑来源。

输出为与 unchanged bdfa `run_service_campaign.audit_cell` 兼容的 `DETAILS.json`：每行至少有 `{source_id,end,original_full_cut,original_full_result{token_ids,selected_correction}}`，并附完整 start、input hash 与 reference-only 标签。保存 CPU controls、config/env/run/model readiness、输入hash、raw JSONL、progress、summary/gate。没有 ORIGIN/Consumer/服务进展或能耗指标，不把 offline oracle/参考运行写成 serving。

后续只有 root 确认需要独立来源时，才按固定 metadata 规则锁4speaker/顺序并冻结 `SOURCE_SELECTION_v1.json`；其中须有 `metadata_only_before_neural=true`、`method_source_commit=bdfa...`、时间、全部旧 speaker 排除与 `sources`。生成器要求计划中的 sources 与该 receipt 完全相同。各来源包含实际source/speaker ID、8TB WAV path、完整SHA、实际frames（8–15s）与官方 reference，archive/header provenance可附加。未读取模型输出或兼容率作为选源条件。

根据 SC 的本地 inventory，未来可用原固定 ZIP central-directory metadata 做metadata预筛，远端完整文本 reference 与 bounded Range/CRC/header/SHA 核实留待授权窗口完成；本工具不实现选择或下载。建议新数据路径为8TB `datasets/revtrace/streamcorrect_independent_20261029/audio/`，与旧 bank 分离。

只有这些锁定完成后才生成实际 final oracle PLAN，并在独占窗口运行：

```text
python -B original_full_reference.py --plan FROZEN_ORACLE_PLAN.json --manifest NEW_REFERENCE_GENERATOR_SOURCE_v1.json --out NEW_8TB_REFERENCE_OUTPUT
```

先要求该 reference gate完整PASS，机械锁 `DETAILS.json` SHA，再冻结最终 timed-service plan。最终 timed service 始终复用原 bdfa source；参考生成阶段和最终服务阶段不混淆。现在没有可执行的新来源 PLAN，所以不存在误启动或默认选源的通道。
