# Fig1 实际 Joint 对照的本地可用性

检查范围仅为现有本地有界文件的身份、长度和原下载哈希；没有 SSH，没有重新扫描远端 raw，没有运行新时间/内容分析，没有以汇总零回撤生成曲线。

## 身份

- 原单臂案例：`stability-c16-staggered-r1_s0-r0`。
- 对应联合臂：`stability-c16-staggered-r1_s1-r0`。
- 原 paired block：`stability-c16-staggered-r0`，同 source `3570-5694-0003`、sid7、offset1.75秒、audio SHA `153d9db9de6c0d950963aa1deee5b51f3da85731d57807d1bdb8d3e5d3eedaff`。
- 原目标完整区间：audio12→14秒，即192000→224000 samples（16kHz），非EOS；这与旧展示的2秒区间相同。
- 原神经源：`f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`；先前两臂source7提取源：`c9e8a89a7df2f269fad0007a4891922da02d728d`。不是最终native NN4f。

## 已有文件与冻结索引

目录 `experiments/dsn_service_stability_20261028/trace_illustration_v1/RESULTS_v1/` 下，`R1_S0` 和 `R1_S1` 各有 `CONSUMER.json`、`EVENTS.json`、`WORKER_RECORDS.json`、`SESSION.json`、`EPISODE.json`、`MANIFEST_ROW.json`、`PROOF.json`。这14个文件共1,490,680bytes，与该目录旧 `DOWNLOAD_VERIFICATION.json` 的每项bytes/SHA完全匹配。

本次只读可用性清单：`FIG1_COMPARISON_LOCAL_INPUT_INDEX_v1.json`，含每个本地/远端提取路径、原bytes/SHA、原source/cell以及共同session身份。原下载索引SHA为 `47e9bce1607104239102fe51aa8272fbf954cd0ca88cb2ef3b2040dbe7e7c673`。

两个 `CONSUMER.json` 各自包含该source的实际应用序列；events和complete worker records用于恢复依赖支持，不能拿聚合withdrawal计数替代它们。原全raw位置及哈希仍在旧 `trace_illustration_v1/RESULTS_v1/CONFIG.json.expected_inputs`，若不扩大分析对象，无需再次远端访问。

## 给最小冻结提取器的约束

1. 使用每臂自己的 `EPISODE.origin_perf + SESSION.offset + 224000/16000` 定义该区间ready；两臂物理origin不同，不能把R1S0 origin抄给Joint。
2. 用实际 `CONSUMER.observed_perf` 记录完整可见/认证frontier，而不是Owner publication时钟；保持所有实际阶梯，不补平滑线。
3. 第一条涵盖F14的完整实际view是否存在、何时出现、是否后来撤回，都必须由Joint自身的真实行导出。需要声明它是同输入/同重复的另一臂观察，而非同一执行交错上的反事实。
4. 旧 `dsn_full_interval_case_20261029/source_v2/case.py` 硬依赖R1S0 compatible-losswindow，不能直接用它处理Joint而删除assert。新双臂只读reader应单独冻结、索引所有输入、使用原时钟并给真实gate。
5. 旧单臂 `RESULTS_v2/PLOT_MANIFEST.json.caption` 明确记录：“No Joint counterfactual is drawn; it had no ahead view at the same root.” 因此即使新图画出实际Joint曲线，也不能说它在该同根更新上保住了原R1S0那个ahead对象。对比的可解释范围需由实际时序结果决定。
6. 同一source并不保证临时文字和墙钟交错相同；若要突出同一完整短语，还需用actual whole text与对应完整结果检查，不以frontier相同代替文字相同。

本次判断是 **LOCAL_COMPLETE_SOURCE7_INPUTS_AVAILABLE_FOR_FROZEN_CPU_EXTRACTION**；不是新的连续性效果PASS，也未改原36/48统计、原案例或负载/中点阴性决定。
