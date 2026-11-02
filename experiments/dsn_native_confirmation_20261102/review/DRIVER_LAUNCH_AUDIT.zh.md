# Confirmation driver V2：准确构建/发车清单

2026-11-02，只读审冻结源与接口，不执行模型、配置生成、CURRENT或修改任何冻结文件。

## 被审身份

- driver：**d865af11e9a8d6c451146942d1708a8caed8d1d9**，6files；本地 `packages/CONFIRMATION_V2_SOURCE.json` SHA256 **dee522a8df4680f2d676cac9ed9f852398e5ec39f54db1ff00f1dcf97d1f277e**。不要用6aeV1或archiveHEAD替代。
- actualNN：4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47，原59文件/source_v2。
- production support：a13fa0a335529dc188f7e738877a3acd027ce4a7，原完整18files，包括PID-generation cleanup、ExternalObserver、READY/allocator和task/endpoint audit。
- reference generator为另一个冻结身份；其receipt必须标actualNN4f。reference GPU费用不进入serving成功或能耗分母。

V2仅修正完整split namespace，原V1保留。新receipt每source必须同时有：

`original_split = AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96`

`split_directory = StreamCorrect/aishell1_testset`

`archive_member.path = StreamCorrect/aishell1_testset/<source_id>.wav`

## Plan构建前外部终门

1. 严格audio acquisition命令正常退出且GATE为PASS；核对其外部receiptSHA、DATA_MANIFEST SHA、完整原N与每个WAV/PCM/header、全版本split。不能只看到一个写出的PASS receipt就跳过最终GATE。
2. 连续original+每start restored重复参考完整PASS；receipt的selection SHA绑定上述**audio-ready receipt**，不是PENDING_AUDIO metadata文件。DETAILS/GATE/GENESIS都已终结并匹配path/SHA/bytes，source完整对象与全部IDs/expected_steps一致。
3. reference资源退出、CUDA释放与Root独占GPU窗口明确。以下服务脚本不执行或补全reference。
4. Root准备原单反馈链final4f正常CONFIG模板、原共享FP32环境及完整当前model-byte gate。模板不是resident入口，也不需要计时observer。

## 准确Plan CLI

以下为Linux8TB环境模板，变量由Root填现有绝对路径；不是已执行命令。

```bash
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
PY="$B/envs/revtrace-streamcorrect-20261028/bin/python"

"$PY" -B "$DRIVER_V2/make_service_plan.py" \
  --manifest "$DRIVER_V2_MANIFEST" \
  --selection-receipt "$AUDIO_READY_RECEIPT" \
  --reference-receipt "$TERMINAL_REFERENCE_RECEIPT" \
  --template "$OLD_FINAL4F_SINGLE_CHAIN_CONFIG" \
  --environment "$FROZEN_SHARED_FP32_ENVIRONMENT" \
  --base-source "$B/projects/revtrace_dsn_native_resilience_20261030/source_v2" \
  --base-manifest "$B/projects/revtrace_dsn_native_resilience_20261030/SOURCE_v2.json" \
  --support-source "$B/projects/revtrace_dsn_strengthening_20261031/paired_resident_source_v2" \
  --support-manifest "$B/projects/revtrace_dsn_strengthening_20261031/PAIRED_RESIDENT_SOURCE_v2.json" \
  --expected-sources 8 \
  --config-dir "$NEW_8TB_CONFIG_DIRECTORY" \
  --raw-root "$NEW_8TB_SERVICE_ROOT" \
  --out "$FROZEN_SERVICE_PLAN"
```

当前Root已固定新8speaker则为32cell；若终结receipt人数不同，必须先显式冻定实际N，再填该参数，不得按成绩改人数。所有config、plan和raw路径不得覆盖旧输出。原模板可用此前paired32正常final/conservative的源CONFIG（项目 `paired32_v2_configs/...final_conservative_r0.json`）；保留原backend、解码、warmup/max_ahead32000，两完整FP32workers，无VAD/500ms/EOS。

Plan生成器完整校验自身/4f/a13clean源码、实际receipt、reference终门后，才写4Nconfig。保存每speaker的r0随机策略顺序，r1显式用该speaker的r0[::-1]；source顺序/GPU旋转及每speakerABBA由验证器重新核对，避免旧block-parity问题。

## 服务PRELAUNCH JSON：实际读取的键

```json
{
  "plan_sha256": "<SHA256 of frozen service PLAN>",
  "root_noarg_preflight": "<Root CURRENT noarg receipt file>",
  "root_noarg_preflight_sha256": "<SHA256 of that receipt>",
  "exclusive_GPU_window_authorized_by_root": true,
  "asset_byte_gate": {
    "path": "<current complete asset-byte gate>",
    "sha256": "<SHA256 of that gate>"
  }
}
```

注意runner读取的是**plan_sha256**，不是其他controller使用的config_sha256。Root noarg receipt要有SOURCE_IDENTITY_PASS、code_commit=d865…、manifest_sha256=本V2manifestSHA，以及CURRENT.json指针字段；只用显式source gate或NN4f的旧CURRENT门不够。

asset gate须status以PASS开头、all_asset_bytes_verified=true，且asset_manifest_sha256等于冻结环境的assets_manifest_sha256。环境实际解释器和packages逐项一致；原allocator由child_env固定expandable_segments:True并清除PYTORCH_ALLOC_CONF别名和CUDA_VISIBLE_DEVICES覆盖，使用真实物理GPU0/1。

## 准确服务Launch CLI

```bash
"$PY" -B "$DRIVER_V2/run_confirmation.py" \
  --plan "$FROZEN_SERVICE_PLAN" \
  --manifest "$DRIVER_V2_MANIFEST" \
  --prelaunch "$SERVICE_PRELAUNCH_JSON" \
  --out "$NEW_8TB_SERVICE_ROOT"
```

runner只有这四个required CLI参数，没有cost driver的phase/observer参数。out必须等于plan.raw_result_location。每个freshcell前再核driver/4f/a13完整字节身份与configSHA；先写外置PRELAUNCH，再Popen并保存PID/startticks/commandSHA。内部实际命令是原4f `resilience_trial.py --config ... --manifest 原4fmanifest --out ...`。

## 结果与资源判定

- 原模型加载与实际learned-C warmup、两worker READY/精度/allocator都真实记录；原D2/C8、全部offered/partialEOS和原Consumer时钟不改。
- deadline性能miss继续全32格。仅身份/技术/语义/资源失败停止，保留已完成/失败/未运行计划，不能换source或删尾。
- actualC/U/reference/source-state/returnedIDs、所有Consumer端点由原4f及独立a13复核；两板能量分别保留usefulcertifiedEOS与外部确认physicalmodeldrain窗口。引用主能耗时使用后者共同窗口，不混入reference模型费用。
- 清理复用生产PID-generation、同run后代group与CUDA释放证明；发现已有其他GPUowner不启动，不杀不明工作。
- 完整结束输出source级合两repeat配对，N为speaker、2N为每policy trial、4N为全部trial，不能用前沿数扩大n。Root仍须运行另冻c4实际来源/依赖链审计；runtime/reference PASS不自动等于零非法安装。

独立审查未发现V2的发车参数或namespace接口阻断。本文是launch审计清单，未执行以上命令或重发任何模型任务。
