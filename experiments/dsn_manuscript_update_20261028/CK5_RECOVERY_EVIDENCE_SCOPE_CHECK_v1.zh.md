# 旧 CK5 恢复证据：本地核验与正文范围建议

2026-10-29。仅本地读取和重哈希，没有远端访问、GPU、重跑审计或改正文。

**判断：证据容易定位且身份可直接核实，建议保留一个约90词的旧原型支持段。** 这能给当前“whole-process termination is recoverable”能力描述一个实际故障证据锚点；不能因此把旧故障结果移植成 f0 或 native 的已验证能力，也不需要增加恢复主图或恢复 headline。合同里的恢复表述应同步限定为“separately frozen recovery prototype/configuration”，否则读者仍会误以为当前全部运行栈已经做了同样的故障验证。

## 精确来源身份

本段所有路径相对于 `D:/VLA_QWEN/RevTrace/experiments/composed_kernel_20261026/`。

* 实际旧执行源码完整 commit：`b8aa802c687256d3801612dc8bee585ee849ddea`。
* `SOURCE_v6.json`：148文件，SHA256 `e909617cd7ec721e7e5ee799d6f3b31b1e5f87938cbde4c9ad93dd5dee219b8d`。
* `runtime/src/revtrace/composed_kernel.py`：SHA256 `3006b628348a3bcf0979157ee3a60a89aba018ece4646a9c47e8384f2c4ecbb2`。本轮确认 `git show b8aa802c687256d3801612dc8bee585ee849ddea:src/revtrace/composed_kernel.py` 的实际 blob 字节产生同一 SHA；148个 runtime 文件全部匹配来源 manifest。
* `SOURCE_v6.tar.gz`：239,588字节，SHA256 `aceb11a355cd7b138f0f516b37c3cca1809785a14e1085b7872f501c2659f5b8`。
* `RUNTIME_CK5_v6.bundle`：273,851字节，SHA256 `7afac21de81738c2c957ee3b49a5de37bdfb3453bd02a18a7db2b6ec11edf598`。本轮未导入或改 Git 对象；完整 b8 commit 已可在现有仓库解析。

这里的 `3006...` 不是后来 f0 runtime 的内核 `7f12...`，更不是 native 独立实现。旧代码的实测不自动覆盖后来新增的完整重根关系、row cancel、native C/U 或其全部恢复路径。

## 已归档的原始完成摘要与审计 gate

不是仅有中文报告。原有 bounded 包中含实际完成摘要、输入与 Canonical WAL、KILL/worker身份/启动和就绪收据、配置、独立复算 gate 与区分后的恢复时钟。

| 本地路径 | 状态/作用 | SHA256 |
|---|---|---|
| `BOUNDED_EVIDENCE_v1.tar.gz` | 5,190,920字节；2250成员 | `8a9c2791f7c9080ccd49cc4335c1c75342625edc9655cef75a318add11e8843c` |
| `collected_v6/FINAL_RESOURCE_AND_SOURCE_v1.json` | 84正式、6开发；各阶段 source/asset gates PASS | `ce3320b26bab766972e02aa3bb3d20850ec734e7c0ca83351c8c83b72dc1e8bd` |
| `collected_v6/normal_AUDIT.json` | 24正式；24/24联合P99通过 | `8877b74d37395bd6eee46ee4788ce60979feb8f8eaedbcb754c1e881dfa0067b` |
| `collected_v6/fault_AUDIT.json` | 36正式进程组SIGKILL；0/36联合P99通过 | `4b4bd5a99c5cd663330a8be326f5922e7fa272af304a4d4b9db0a5adc21c3cdf` |
| `collected_v6/boundary_AUDIT.json` | 16受控边界；12/16联合P99通过 | `b3e0ef3b026df6bf088f1f280730291ad28fcefa1e00079352a5f56bb1a2a73d` |
| `collected_v6/post_sync_AUDIT.json` | 8正式WAL同步后/安装发布前崩溃；0/8联合P99通过 | `ef566ed70659872f660594b0681893e4f7a40d2b26838ee4c7596e4681ae42b0` |
| `collected_v6/RECOVERY_CLOCKS_v2.json` | `PASS_DISTINCT_RECOVERY_CLOCKS`；分开原债务清空与最终offered消费 | `1c46da2bf3f363dbdea45bdd6f9192ce12f06660520155ce8f5109d70662ba78` |

每阶段原完成摘要分别在 `collected_v6/{normal,fault,boundary,post_sync}/SUMMARY.json`；数量为24/36/16/8，均 `COMPLETE`。它们只证明执行完成，服务成功与保留输入的结论来自相应 `_AUDIT.json`，不能只凭 `COMPLETE` 推导。

方便核对单次实际记录的例子：

```text
collected_v6/fault/002-qwen-dgft_original-early-k1-r0/KILL.json
collected_v6/fault/002-qwen-dgft_original-early-k1-r0/RUN_COMPLETE_PENDING_AUDIT.json
collected_v6/fault/002-qwen-dgft_original-early-k1-r0/canonical.wal.pre-recovery
collected_v6/fault/002-qwen-dgft_original-early-k1-r0/input.wal.pre-recovery
collected_v6/fault/002-qwen-dgft_original-early-k1-r0/attempt1/FACTS_AND_DEBT_RESTORED.json
collected_v6/fault/002-qwen-dgft_original-early-k1-r0/attempt1/EXECUTORS_READY.json
```

`attempt1/result.json` 明确警告其部分 event P99 是历史诊断口径。正文应使用 `_AUDIT.json` 重建的原始 offered/时钟统计，不应抽取该 result 的诊断 P99 代替。

## 本轮实际重新核验的范围

本轮重算 bounded archive 的完整 SHA；逐项读取全部2250成员。其中2249内容对 `RAW_INDEX_v1.json` 的原始 bytes/SHA全部一致，解包后本地文件也与这些 archive 内容逐字节一致；索引自身由已核的 archive SHA 覆盖。148源码文件全部匹配 `SOURCE_v6.json`。

这验证的是**存档字节和来源身份**；没有访问8TB原始长日志再重跑全部科学审计。原独立审计的实际路径、checker SHA、状态与逐运行结果本地可读，因此本次不是仅重复最终中文结论。原始长日志的全部3975文件/230,763,651字节仍属于原8TB证据，不伪称本轮完整重新执行或重新审计。

## 从原 gate 直接重计的核心事实

* 正式84格＝normal24＋fault36＋boundary16＋post_sync8；另6开发探针不并入。
* fault36和post_sync8的 acknowledged-input loss记录均为0，原 offered clock保留，联合全run D2/C8通过均为0。
* 24个 early fault运行和全部8个post_sync运行，旧事实实际Consumer恢复都早于worker就绪。
* Qwen旧 `dgft_original` 配置三重复中位数：worker-gated旧视图RTO **31.013197788s**，early+kernel旧视图 **14.736040702s**，该early+kernel首次新增认证消费 **33.829463942s**。
* 原完整组合 `standard_fair` 同样受益：旧视图31.222506467→14.471188097s，early+kernel首次新增认证消费32.494930037s。不能把收益归成RevTrace某一份调度代码的独占性，也不能把早恢复策略的收益都归给内核开关。

聚合便读表：`analysis_v1/RECOVERY_GROUPS_v1.csv`（SHA `f7e79f779b1864ef02bf3eaa1dce845a20811a00cd097b0ee2c11f679ae34128`）。本轮直接从fault audit逐运行数值重取中位数，与该表一致。

14.736s对应**旧持久事实重新实际消费**，不是新音频处理进展；原接受未认证输入的债务保持独立。实验只覆盖同一完好文件系统上的可信Owner/选择/渲染和进程组死亡围栏，不覆盖断电、损坏存储、Byzantine宿主或远端浏览器网络恢复。

## 建议加入正文的英文支持段（约90词）

> A separately frozen recovery prototype completed 84 GPU service runs: 24 normal, 36 process-group SIGKILL, 16 controlled-boundary, and eight post-sync crashes. Archived audits recorded no acknowledged-input loss. All 32 early-recovery crash runs reapplied old facts before workers were ready. In one Qwen configuration, median old-view recovery changed from 31.013 to 14.736 s; first new certified output still took 33.829 s. The complete-composition control shared the recovery benefit. All 44 crash runs missed the joint whole-run D2/C8 target. These measurements concern the earlier prototype and do not establish fault recovery for the current core or native adapter.

适合放在执行协议的 validation boundaries 末尾，或评价中一个短的 earlier recovery validation 段；不再开独立结果主节。完整source/hash放实验工件说明，不必把会反向定位公开作者仓库的commit写进匿名正文。

若最终版没有约90词空间，次选是保留一条“earlier frozen prototype”及44次故障全SLO失败的实测说明，并收紧合同中的当前能力承诺。完全删除实测、同时保留不加范围的recoverable全栈承诺，是我最不建议的组合。
