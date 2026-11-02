# Reference V2启动接口审计

日期2026-11-02。只读核对冻结README/CLI、旧配置/环境/reference元数据与当前已生成PLAN/PRELAUNCH；未读新候选WAV或模型，未运行reference，未修改冻结树/CURRENT。额外原盘检查只读取了两个既有旧CONFIG JSON，验证其对象相等，不涉及音频/推理。

## 1. 结论：保留现有REFERENCE_PLAN_v1，不重复造plan

生成器实际源：`437d7628944076205eaccaea9bdee18964956f7b`，7files；manifest SHA：
`0f041caa69b82ae03912200239dc0061a5fe9477ead6447c0bc7c922d1b2610e`。
原盘14/14 CPU controls正式通过（`controls/REFERENCE_V2/GATE.json`），并非已完成神经参考。README中的“author未执行/尚未运行”是冻结前说明，不应覆盖这份正式控制收据。

当前`confirmation/REFERENCE_PLAN_v1.json` SHA：
`d7f810fbc68ef9014cf37ab9035fc20d7728edd4d6f07decae7baafc90d1af2b`。
它已绑定8个独立新speaker、141个原500ms/EOS steps。正常情况下额外执行282次原CandidateBridge恢复调用，另有一次固定warmup；这些是API步骤计数，不是将buffer-only步骤伪称GPU神经调用。诊断调用只在首失败时发生并单列。

### 当前template的直接核对

Root采用的raw正常final4f Full-call配置：

```
/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_20261031/paired32_v2/cells/SC_PAIRED32_V2_BAC009S0908W0369_final_fullcall_r0/CONFIG.json
SHA256 1516139c4ec98023b050242ad468b7f43b641c51d5c62c12becddce3312983e6
```

对应原冻结source-config：

```
/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_strengthening_20261031/paired32_v2_configs/SC_PAIRED32_V2_BAC009S0908W0369_final_fullcall_r0.json
SHA256 e3c2ea62897e9a7f678f88309f5a07c975cb6a7575a156dfda89b188f19a1f83
```

本次直接读取两份原盘旧JSON，结果：`full_config_objects_equal=true`、`settings_equal=true`、`settings_different_keys=[]`。字节SHA不同来自序列化格式；**settings没有变化**。V1 plan登记的raw SHA正确，不应把它替换成source-config SHA而不改路径。后续service freeze可优先使用原冻结source-config，reference V1无需重建。

## 2. 可直接使用的已有参数

为缩短表格，定义以下完整前缀；这是文档记号，不改变实际路径：

```
B  = /media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P  = B/projects/revtrace_dsn_native_confirmation_20261102
O  = B/results/revtrace/dsn_native_confirmation_20261102
PY = B/envs/revtrace-streamcorrect-20261028/bin/python
```

|参数/角色|当前准确值|登记SHA/身份|
|---|---|---|
|generator source|`P/reference_v2`|`437d7628944076205eaccaea9bdee18964956f7b`|
|generator manifest|`P/REFERENCE_V2_SOURCE.json`|`0f041caa69b82ae03912200239dc0061a5fe9477ead6447c0bc7c922d1b2610e`|
|actual NN dependency|`B/projects/revtrace_dsn_native_resilience_20261030/source_v2`|`4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，clean59files|
|base manifest|`B/projects/revtrace_dsn_native_resilience_20261030/SOURCE_v2.json`|`60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`|
|FP32 environment|`B/projects/revtrace_dsn_strengthening_20261031/ENVIRONMENT_v2_FROZEN.json`|`40c867b5225ee1d23253fe63dba4e5e2727f97ececa34f9c94d26f39ff51920a`|
|new selection receipt|`O/audio_acquisition_v2/SOURCE_RECEIPT.json`|`e8a76b9e5c8f59e7c7cb68d73a1ac427597ba21cac1a31b6dae7cbd24dacc07d`|
|asset gate argument|`P/ASSET_GATE_BINDING_v1.json`|`a71f2541a9e6e45e467eb2dabfef3d0f840db456ca50a112218cfe1c3dc64c8a`|
|underlying asset audit|`P/ASSET_BYTE_GATE_v1.json`|`d2f31b6eb46240ecc57bd90ed2446fad08cdf218570e1906bb8b3483a1a7a18a`|
|cache|`B/cache/revtrace_dsn_native_confirmation_20261102`|仅8TB缓存|
|new raw output|`O/short_references_v1`|必须在首次启动前不存在；失败后不得覆写|
|physical GPU|index0|`GPU-ef01d441-985f-50b3-6e64-5d4c3e2def3a`|

**asset argument必须是BINDING文件。** 它有`status=PASS_DECLARED_MODEL_ASSET_BYTES`和`all_asset_bytes_verified=true`；原始ASSET_BYTE_GATE只记录31文件/15,845,541,719bytes等审计内容，不具备run_reference.boot所需的同名PASS字段，不能误传。当前plan正确引用BINDING，并通过其`original_receipt_sha256`指回原始byte audit。

环境含`packages`和`executable`，满足make_reference_plan的实际schema。登记的主要包为torch2.9.1、transformers4.57.6、numpy2.2.6、peft0.18.0、soundfile0.14.0、torchaudio2.9.1；`worker_packages`另外列triton3.5.1。boot直接检查`packages`；Root的新环境前置检查应同时核对已登记worker_packages，不由代码忽略字段推断版本不重要。原ASR/corrector浮点参数均FP32、TF32关闭、seed1701，运行时MODEL_READY再次给出实际dtype。

上述GPU UUID来自已有机器元数据，不代表现在仍空闲；实际`gpu_precondition`必须在启动时再次确认UUID及没有任何CUDA owner，Root exclusive租约也必须成立。

## 3. 固定warmup到底是什么

当前template完整嵌入旧warmup cut，生成器不会用新来源搜索warmup：

|项|精确值|
|---|---|
|source_id|`BAC009S0764W0209`|
|WAV路径|`B/datasets/revtrace/streamcorrect_adaptation_20261028/audio/BAC009S0764W0209.wav`|
|WAV SHA|`e48f4231f1bb8ff05f2f1214652257b9c1d9b052470e50bcf3d1fd674d517d95`|
|原完整WAV frames|129088|
|固定起止|24000→32000 samples（1.5→2.0s）|
|嵌入原start cut SHA|`881ad9fb2c7e4567e5581f6c4d925a5a2b0dbf212f56e0f2d11f8cd072752460`|
|原cut transcript|`严`|
|行为|原neural C必须返回非None；丢弃输出、完整重置genesis|

代码读取的键是`fixed_start/fixed_end`及`original_reference_start_state.frontier`，不是不存在的`warmup.start/end`。make_reference_plan核frontier24000，run固定调用end32000；真正rebind由原CandidateBridge.rebind_warm_cut执行，使用实际4f合同与原WAV SHA。warmup原先已用于旧研究，**不计作新增8speaker之一**。

## 4. 旧reference元数据在哪里，哪些只作历史来源

旧四source原参考（a13/final4f旧matched比较所用）：

```
B/results/revtrace/dsn_streamcorrect_independent_20261029/reference_v1/DETAILS.json
SHA256 58a33465f5af8dc0f39983253abdcf9bccb9ac79e03690e342792281a36c57a6
B/results/revtrace/dsn_streamcorrect_independent_20261029/reference_v1/GATE.json
SHA256 28aa26207c509a733db2a9ab95612c48a4b5a96d233faf4460fbaa88a0017524
```

其原生成器为`66abab7b8ce668a1a1ddefb65f6115af45e99cec`、实际模型runtime为旧`bdfa3b1307d267a5a4caf6484e1ad465c39a592e`，不是4f；原plan SHA `bf8dd4e8cc14ba4c23d6040f2502d80b5f45e426457ed49fd905dca3f4b66fe2`。本地入口`dsn_streamcorrect_independent_20261029/ORIGINAL_FULL_REFERENCE_PLAN_v1_FROZEN.json`及`REFERENCE_HANDLE_v1.json`保存该来源。

原warmup经旧stage服务配置传入独立服务，再由a13.freeze_plans原样继承。历史method-config指针：

```
B/projects/revtrace_dsn_streamcorrect_stage_handoff_20261029/service_pilot_v1_configs/SC_STAGE_SERVICE_PILOT_V1_two_full_spec_early_source0_r0.json
SHA256 30387d477ccd1ecbf35f8a37fcd72ee99360ba37383b68da254397d502ea759a
```

新生成器并不把这些旧DETAILS当作新source结果。**新的REFERENCE_DETAILS必须由新8source的实际4f连续原engine执行产生**，状态marker保持4f；旧metadata仅说明template/warmup来源。对新source采用strict参考，不能通过把新输出重贴成BDFA来伪造保真。

## 5. 当前准确run命令与prelaunch

Root已生成plan，不再重复调用make_reference_plan。当前run对应的命令为（前缀展开同§2）：

```
PY -B P/reference_v2/run_reference.py
  --plan P/REFERENCE_PLAN_v1.json
  --manifest P/REFERENCE_V2_SOURCE.json
  --prelaunch P/REFERENCE_ENTRY_v1.json
```

当前`REFERENCE_ENTRY_v1.json`应精确绑定：

```json
{
  "exclusive_GPU_window_authorized_by_root": true,
  "config_sha256": "d7f810fbc68ef9014cf37ab9035fc20d7728edd4d6f07decae7baafc90d1af2b",
  "root_noarg_preflight": "P/ROOT_NOARG_REFERENCE_RUN_V1.json",
  "root_noarg_preflight_sha256": "c32ec4662c8b7af53eca3edeccab469787140767d81b7bf1cadedec677a2acd8"
}
```

这里JSON中的P只是本文前缀记号，真实文件必须是完整绝对路径。Root现有ENTRY_PRELAUNCH镜像已使用完整路径和上述值。

不要混淆两级配置：外层`REFERENCE_JOB_v1.json`SHA为`b6f4c2c366750f618a3272a4e634f7d64028c22be3f04aa7bbe2a40ba0b700f7`，它登记launch命令与角色；**run_reference.boot要求的是内层PLAN的d7f810...SHA**。当前entry填写正确。

启动必须使用GPU job包装器，非CPU-only launcher。现有prelaunch环境scope写明GPU reference/service，`CUDA_VISIBLE_DEVICES`由冻结entrypoint选择。不要复用旧14controls的CPU启动收据作为这次NN环境/资源门；当前REFERENCE_RUN_V1单独记录已区分。

## 6. 静态结论和终结条件

当前未发现template/settings、environment schema、warmup键、split身份或CLI不相容的静态阻断。原配置raw/source对象相等，保留V1 plan是正确取舍。剩下是实际运行门，不是应当再改方法：

1. source437d的fresh CURRENT/noarg、原clean4f59、实际环境/资产/音频身份及独占GPU同时满足；新音频字节的实际读取验证由冻结entrypoint执行，本审计没有代做。
2. 全8source/141连续steps及每edge2恢复比较通过；任一失败保留原reference与first-failure controls，不换source、不覆写结果。
3. 成功DETAILS/GATE/GENESIS/REFERENCE_RECEIPT终结SHA一致；only then可冻结服务配置。
4. Root按已登记PID/startticks在进程退出后外部确认CUDA空，再归还GPU窗口。entrypoint的reference PASS不自动证明自己进程已释放CUDA。

参考的加载、warmup、连续/恢复/诊断时间与能量全部reference-only，不能计作已完成的服务性能，也不能被静默放入某一策略或当免费oracle。原4f、冻结437d和旧8995均未在本审计中修改。
