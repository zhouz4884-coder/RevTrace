# 收集器静态复核与operator修复

2026-11-18。按Root要求，仅静态复核`ops/collect_closed.py`、`build_publication_candidate.py`及`prepare_collection_requests.py`，并修改operator helpers。没有SSH调用、GPU查询/实验、冻结source修改、论文修改、Git操作或实际收集。外层代码与嵌入远端代码均经AST解析，未执行远端代码。

## 已发现并修复

1. **两个premodel失败日志漏收。** 原collector只筛service-phase前缀，所有`preserved_premodel_failures/*/process.log`请求都未被执行。现在默认追加独立`REFERENCE_AND_PREMODEL`包，收全V3参照有界文件与V1/V2零模型失败原日志；验证三次reference句柄均已退出，且两次失败`model_calls=0`。
2. **重试会因ZIP已存在而失败。** 原archive用`x`但无恢复路径；网络中断后再次运行会撞文件。现在新用`*.bounded_collection_v2.zip`，成功archive有schema与完整request-fingerprint；重试先验证manifest、每个成员字节SHA和required集合后复用。未完成`.partial`包另存abandoned，正式ZIP以完整写出后重命名产生。坏本地cache另存badsha，正常不可变镜像仍拒绝内容冲突。
3. **覆盖Root已有资源闭合UTC。** 原代码每次重写ROOT_RESOURCE_CLOSURE，再映射到已有`launch_ops/<phase>/RESOURCE_CLOSURE.json`，会触发immutable mirror差异。现在写入独立`COLLECTION_RESOURCE_CLOSURE.json`，原Root闭合收据不动；重试复用已验证同pid/start_ticks/格数的collection闭合文件，不重新生成UTC。
4. **raw哈希缺少稳定性检查。** 新stream SHA在读取前后核对device/inode/size/mtime，并拒绝symlink/路径逃逸。每格完整raw目录、外部power和process log仍只写hash-index，不下载；V3 reference raw也单列hash-index。索引使用`COLLECTION_RAW_HASH_INDEX_V2.json`和`raw_hash_indices/*.collection_v2.json`，避免自指或覆盖旧索引。
5. **收集器缺少硬性内容类型边界。** 现在只下载JSON与两份明确premodel失败LOG，正常service process log保持hash-only；service文件必须在冻结结果root或确切source-config集合内，reference/extras也限制为V3目录或V1/V2日志。不允许WAV、WAL、jsonl、权重或任意8TB文件因错误请求被下载。
6. **publication readiness不足。** 最终`--require-complete`除80格有界文件及阶段COMPLETE外，还要求有效reference gate/DETAILS/GATE/GENESIS哈希绑定、两阶段generation-bound资源闭合、覆盖所有cell的raw provenance index（至少含facts/Consumer/publications/power/log）、两个premodel原日志。
7. **论文只读检查仅检查旧文件，没看新增文件。** 现除230个文件长度/SHA外，也检查paper目录新增普通文件；发现差异仅拒绝完整发布状态，不reset/覆盖论文。
8. **新collection索引遗漏allowlist。** 新增`COLLECTION_INDEX_V2.json`与campaign collection闭合元数据为可发布有界记录。最终分析输出`review/FINAL_RECOUNT_V1`（如有V2同样）已由review递归JSON/MD/CSV/log allowlist覆盖，不缺f29输出。

## 最终重算输入覆盖

对照`analysis_source/final_recount.py`逐项检查：actual CONFIG/GATE/SUMMARY、ORIGIN/SERVICE_END、EXTERNAL_FACTORIAL_AUDIT、INDEPENDENT_VIEW_AUDIT、JOB_ACCOUNTING、WORKER_TIMER_LEDGER、SAMPLED_ENERGY_OWNERSHIP、view_audit的SUMMARY/GATE/CANONICAL_SUPPORT_EVENTS/OBSERVED_LOSS_WINDOWS均在显式请求内。原冻结80配置在plans/configs并另收frozen_configs副本；reference receipt/details/gate/genesis在本地有界文件内。

6项source/dependency身份已由Root补入两个helper的SOURCE_MAP：NN67、campaign22、audit20、readiness3、analysis3、production_support18。plain source逐manifest文件验证；bundle/manifest单列，不复制嵌套`.git`。315/72/53 CPU套件各自CONFIG/ENV/RUN/SUMMARY/GATE/log已由baseline allowlist覆盖。

## Root运行方式与边界

确认所有serving phase与实际CUDA owners释放后，Root运行：

```text
python -B experiments/dsn_native_joint_retention_20261118/ops/collect_closed.py
python -B experiments/dsn_native_joint_retention_20261118/ops/build_publication_candidate.py --require-complete
```

collector默认收pilot、confirm、reference和premodel失败；`--phase`可选收阶段，`--skip-extras`只适用于extras已独立完整收过的情况。最终helper会阻止漏失败日志/漏raw索引而宣称完整。

当前collector默认仍要求campaign技术性COMPLETE；若后续发生技术失败而非SLO失败，Root应单独进行有界失败诊断收集并保留失败状态，不能让此模式将失败campaign冒充完成。现有80格协议不因SLO、零机会或负效应中止，故这些结果仍会完整被收取。

实际收集、最终SHA验证、Git index/blobs检查及发布仍由Root执行；本静态审阅不构成“已收集80格”或远端运行通过的声明。
