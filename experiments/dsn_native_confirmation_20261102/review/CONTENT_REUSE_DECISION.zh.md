# 新 8 来源确认的同内容证据复用判断

日期：2026-11-02。只读审查；未读取新 32 格结果，未运行分析或模型，未修改任何冻结源。

## 决定

可以低成本补充同口径的“同内容更早交付”证据。不要重跑旧 complete20 runner，也无需新增内容判据：新服务仍调用原 4f，每格已自动将原函数输出写入 `SUMMARY.json`。在全部 32 格和独立实际轨迹检查完成后，冻结新的统计入口，完整聚合这些现有字段即可；V1 primary/bootstrap 保持原样。

## 原实现与身份

- 实际 NN：`4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`。
- `experiments/dsn_native_resilience_20261030/source_v2/resilience_trial.py:163–167` 调用 `resilience_metrics.analyze_trial(out)`，检查原 task gate，然后将完整结果写为 `SUMMARY.json`。
- `resilience_metrics.py:107–118` 定义 `posterior_support`；`:212` 产生实际 Consumer 的 all-offered frontiers；`:236` 将其放入结果的 `posterior_whole_text_support`。
- 原 `resilience_metrics.py` SHA256：`1e3f7fbf50d4f621d51700f44ef4fb80cc335e3439e6e43e190aca9275cf121e`。
- 原 `content_endpoints.py` SHA256：`07d16f211cbc4320b3df109049083285863d0ae709d8ac008c75eb78a2776b52`。
- 两文件分别与旧 CONTENT_V4 的 vendored 文件逐字节相同，已仅对源码做 SHA 核验。新 strict reference 仅改变完整原任务参考审查，不改变该内容判断。

旧 CONTENT_V4 来源为 `experiments/dsn_writing_closure_20261031/content_source_v4`，commit `6eb6639478a87e6be971e23282bd2f31789f242f`；manifest `content_packages_v4/CONTENT_SOURCE_v4.json`，SHA256 `2dac41b61a84c5de8846564bdcb7c7c6bd8159e51b35012f385c6e781282637c`。旧 CLI 为 `python -B run_content_recount.py --config CONFIG_FROZEN.json --manifest CONTENT_SOURCE_v4.json --out OUTPUT`。

该完整 runner 不可仅换 config 复用：`run_content_recount.py:93–96` 硬锁 20 trials、16 paired+4 resident 和 4 sources；`:118` 锁 32 requests；`:120–125` 核旧 22.5/51.0 秒与字符数；`content_reader.aggregate:246–253` 强制四组且每组 8 requests。这些是旧银行守恒门，不能删掉后仍声称运行了旧冻结源。

## 新统计应读取的精确字段

每格 `SUMMARY.posterior_whole_text_support` 有 `raw`、`whitespace_stripped` 和一个字符串 `scope`。前两者各含：

```text
original_credit_supported_seconds
original_credit_mismatching_seconds
original_credit_unknown_seconds
all_offered_frontier_counts.{supported?, mismatching?, unknown?}
```

`all_offered_frontier_counts` 由 Counter 转 dict，零类可缺省；读取时用 `.get(class, 0)`，拒绝未知额外类别。不能假设每格一定出现三种 key。

每格、每个 mode 的三秒数之和必须等于 `SUMMARY.primary.dual_deadline_audio_credit_seconds`，并等于 `SUMMARY.content.original_dual_credit_audio_seconds`。三类 counts 之和必须等于 `SUMMARY.content.offered_frontiers`，也应与原 `primary.offered_frontiers` 一致。总 offered 分母为原 `primary.offered_audio_seconds`，并与 `content.offered_audio_seconds`、冻结 frames/16000 守恒，不能用 counts 或 C8 过滤后重建分母。Unknown 保留；负配对差不裁零。

## 不变的 first-G 语义

`content_endpoints.py:76–94` 按每个原始 500ms 前沿和最终部分 EOS 枚举 F。原 offer 为 `origin + F/16000`；取第一个实际满足 `observed >= offer` 且 `visible_frontier >= F` 的 Consumer row，其实际显示前沿记为 G。音频权重是相邻原 F 的差除以 16000；credit 仍要求原 D<=2、C<=8。

`posterior_support` 用 `(source_id, G)` 查实际 durable selected fact 的完整 transcript，比较整个首视图文本。`raw` 逐码点比较；`whitespace_stripped` 只去 Unicode 空白。没有该 row 或该 G 尚无 selected fact 时为 unknown。三类 counts 覆盖全部 offered F；三秒数仅累计原 credit 为真的 F。

该判断不取 F 的文本、不截前缀、不拿最终 EOS 文本或 reference 作替代；也不是人工正确性、字符新增量或持续覆盖面积。可写“及时覆盖音频中，其完整首视图与同一实际 G 上后来选定文本一致的部分”。

## 聚合与写稿

完整保留 8 来源×2 策略×2 fresh repeats，原 all-offered/EOS 分母不变。先合并同来源两次重复，再报告 8 个独立来源的配对差；不可把前沿或重复当独立 n。先固定输出三分区、原 credit 与 offered 守恒，以及 raw/去空白两种口径，再读取效果。只有新结果有信息增量时更新主原生图；旧 4 来源 resident 与新 8 来源 matched 不能合并分母或互借内容数字。
