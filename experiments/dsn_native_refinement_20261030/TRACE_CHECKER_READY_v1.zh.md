# 最终runtime实际轨迹精化检查器：准备完成，尚未读取新NN结果

**后续完成记录：**本文件为30309准备期说明。实际六开发trial已由窄schema修正后的c4dde9源码（35控件）全部硬验，详见[实际结果与范围](SHORT_ACTUAL_TRACE_RESULTS_v2.zh.md)及[机器facts](SHORT_ACTUAL_TRACE_FACTS_v2.json)；原六schema失败保留。不要将此历史准备状态当当前未执行状态。

独立source为`trace_source_v1`，commit `30309ccff11df9c8d20f4671ed66f090e76277f0`，完整6文件manifest SHA `717c1c17f539cf6e112f49c8ff3e103b6014c6db77910690f57f66fdf26b7b0e`；bundle、plain snapshot、root可解析完整commit与显式preflight齐。34/34本地**开发**合成控件通过、零skip；`TRACE_DEVELOPMENT_RESULTS_v1`明确不是实际服务轨迹验证。当前没有该checker的新NN数据PASS。

## 实际读取对象与硬检查

读取整个`facts.wal`、全部`owner_e*/dispatch.jsonl`与`worker_results.jsonl`、`owner_events.jsonl`、`policy_audit.jsonl`、Supervisor的`publications.jsonl`、实际`consumer.jsonl`、持续`ingress.jsonl`及原`ORIGIN.json`。不导入runtime的frame扫描/消费函数，也不依赖metrics的PASS。

1. 独立解析RVN1完整帧的长度、SHA256校验和、规范编码、序号和父链。默认不忽略torn tail；若明确允许，只报告末尾未提交部分，完整帧损坏始终失败，不修原数据。
2. 每次新事实必须唯一映射到实际发起且在原物理channel/incarnation收齐的原完整C/U结果，完整start/end、原选择与IDs全匹配；job/birth/Owner namespace/session epoch/incarnation不重签。完整状态字段不可投影，固定500ms/最终EOS cadence不能跳步。
3. 独立重建实际publication到Consumer的整个依赖路径。typed ASR预测与原完整C/U节点不同；认证只能来自durable事实，完整ahead view在兼容应用保持。Owner重启保留旧Consumer view也按原收到的完整path验证。
4. 重放old durable fact允许使用新Consumer namespace，原fact/job身份保持；旧Owner消息本身不能新获得写入权限。实际Consumer不得重复原事实推进新进展。
5. 对current-owned首次wellformed ASR/full phase，结合before/after的session/incarnation/inbound_seen判是否被误拒。字段缺失保持None；不从最终任务完成反推0。普通局部拒绝不能改Canon或清别的busy；只有已核的fenced terminal可释放其旧lease。
6. 逐Owner核worker replacement的原PID/start_ticks、confirmed exit、CUDA context release及新incarnation；Supervisor整组终止证明是额外证据，不冒称已由此覆盖。
7. 原ORIGIN、音频身份、offered clocks和所有接受输入的最终边界保持；dispatch不能读取尚未offered的target。实际认证必须处理完全部最终边界，完整durable prefix不等于完整任务已经完成。

## 绑定与实际运行

等root确认某一trial完整退出、资源释放和raw bank稳定后，使用`ops/bind_actual_trace_v1.py`仅按所有文件与原配置机械绑定输入hash，不按性能/文本筛选：

```text
python -B ops/bind_actual_trace_v1.py --case-root RAW_TRIAL_ROOT --runtime-source-commit FULL_ACTUAL_RUNTIME_COMMIT --output-config NEW_FROZEN_CONFIG --experiment-id UNIQUE_ANALYSIS_ID
python -B trace_source_v1/run_trace.py --config NEW_FROZEN_CONFIG --manifest packages/TRACE_SOURCE_v1.json --out NEW_RESULTS_DIRECTORY
```

正式运行前仍需root切CURRENT/无参source gate与配置/环境预登记；raw和正式结果应在8TB盘，开发bounded日志可审阅副本保留本地。实际模式会再次执行34个控制后读取完整真实数据，前后核全部输入SHA。

该检查器证明的是已记录API对象、原程序结果来源、durable接纳与实际消费之间的结构精化。在完整适配状态及host/source忠实执行前提下，它支持原程序允许轨迹；不证明GPU算术、人工正确率、任意独立重跑位等价、无限活性或自然发生率。固定参考全state/C/IDs比较仍由独立long/short oracle承担，两者互补而不替代。
