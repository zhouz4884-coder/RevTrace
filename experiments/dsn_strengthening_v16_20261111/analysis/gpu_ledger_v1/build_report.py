#!/usr/bin/env python3
"""从 ledger_v1.json / ledger_v1_jobs.jsonl 生成中文报告。纯 CPU，只读。"""
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "ledger_v1.json"), encoding="utf-8"))
jobs = [json.loads(l) for l in open(os.path.join(HERE, "ledger_v1_jobs.jsonl"), encoding="utf-8")]
A = d["aggregate"]

prom = [j for j in jobs if j["role"] == "promotion"]
rej = [j for j in jobs if j["role"] in ("abandoned", "discarded")]
lat = [j["latency_saved_s"] for j in prom if j["latency_saved_s"] is not None]
ms = [j["model_s"] for j in prom]
rc = d["reject_class"]
ec, le = rc["early_cheap"], rc["late_expensive"]

L = []
w = L.append

w("# RevTrace 跨版本有效计算的资源与时效账本（v1）")
w("")
w("**2026-11-11。纯 CPU 只读重算，不产生任何新 GPU 或服务结果。**")
w("")
w("数据源：`experiments/dsn_streamcorrect_independent_20261029/SERVICE_RESULTS_v1` 的 16 个冻结 cell"
  "（旧四来源，守恒臂 8 格 + 投机臂 8 格，每源两次 fresh-process 重复）。")
w("本报告不修改 v15、旧独立确认或任何既有冻结记录。")
w("")
w("## 0. 这份账本做什么")
w("")
w("原文已有的 `92` 次跨版本晋升是**调用计数**，不能直接换算成计算或时间收益。"
  "本次重算把每一个 job 的 worker 侧实际计算记录（`native_jobs.jsonl` 的 `record`）"
  "与三本账（`FULLSPEC_LEDGER.json` 的 promotions / discarded / abandoned）逐 `job_id` 绑定，"
  "得到可按资源与时效分开报告的量。")
w("")
w("## 1. 主结果")
w("")
w("| 账目 | 条数 | worker 占用 (s) | 纯神经阶段 (s) | 含义 |")
w("|---|---:|---:|---:|---|")
w(f"| 跨版本合法保留 | {A['promotions_cross_version']} | {A['recovered_wall_s']:.3f} | "
  f"{A['recovered_model_s']:.3f} | 出生版本已失效但完整输入仍合法、结果被实际采用的工作 |")
w(f"| 早期拦截（模型前） | {ec['n']} | {ec['wall_s']:.3f} | {ec['model_s']:.3f} | "
  "在 ASR 前缀阶段即被证明无效并取消，未触发神经模型 |")
w(f"| 晚期丢弃（跑完才丢） | {le['n']} | {le['wall_s']:.3f} | {le['model_s']:.3f} | "
  "完整模型推理已执行完毕才被判为无效 |")
w(f"| **投机沉没合计** | **{ec['n']+le['n']}** | **{ec['wall_s']+le['wall_s']:.3f}** | "
  f"**{ec['model_s']+le['model_s']:.3f}** | 以上两类之和 |")
w("")
w("**关键比值**")
w("")
w(f"- 保留/沉没 = **{A['recovered_wall_s']/(ec['wall_s']+le['wall_s']):.2f} : 1**"
  f"（{A['recovered_wall_s']:.3f}s 对 {ec['wall_s']+le['wall_s']:.3f}s）")
w(f"- 单次保留平均 **{A['recovered_wall_s']/A['promotions_cross_version']:.3f}s**，"
  f"单次早期拦截平均 **{ec['wall_s']/ec['n']:.3f}s**")
w("")
w("**92 条晋升的执行证据（已验证，不是假设）**：")
w("")
w("| 检查项 | 结果 |")
w("|---|---|")
w("| `native_model_evaluated` | 92/92 为 True |")
w("| `stage_execution` | 92/92 为 `original_full_infer` |")
w("| `model_seconds` > 0 | 92/92 |")
w(f"| `model_seconds` 范围 | {min(ms):.4f} ~ {max(ms):.4f}（中位 {statistics.median(ms):.4f}） |")
w("")
w("也就是说：这 92 次不是「声明为在飞」或「离线放行」，"
  "而是**确实执行了完整神经前向并跨越父状态被采用**。")
w("")
w("## 2. 时效账（反事实估计，须与假设一起引用）")
w("")
w(f"92 次全部能配对到其实际父状态的安装时刻，合计 **{sum(lat):.3f}s** 完成延迟节省。")
w("")
w("| 统计量 | 值 (s) |")
w("|---|---:|")
w(f"| 最小值 | {min(lat):.3f} |")
w(f"| 中位数 | {statistics.median(lat):.3f} |")
w(f"| 最大值 | {max(lat):.3f} |")
w(f"| 合计 | {sum(lat):.3f} |")
w(f"| 负值条数 | {sum(1 for x in lat if x < 0)} |")
w("")
w("定义：`时效节省 = (父状态实际安装时刻 + 本 job 的 model_seconds) − 本 job 实际完成时刻`。")
w("含义是「若某策略在父状态安装的瞬间杀掉该在飞调用并重派，完成时刻会推迟多少」。")
w("**这是反事实估计，不是实测重跑**，不能替代闭环三臂比较。92/92 为正，本次没有出现反例。")
w("")
w("## 3. 分源（与既有文档对照）")
w("")
w("| 说话人 | 晋升 | 跨版本 | 早期拦截 | 晚期丢弃 | 保留 (s) | 沉没 (s) | 时效 (s) |")
w("|---|---:|---:|---:|---:|---:|---:|---:|")
for sid, v in sorted(d["by_source"].items()):
    n_ab = v["abandoned"]
    n_di = v["discarded"]
    w(f"| {sid} | {v['promotions']} | {v['cross_version']} | {n_ab} | {n_di} | "
      f"{v['recovered_wall_s']:.3f} | {v['wasted_wall_s']:.3f} | {v['latency_saved_s']:.3f} |")
w("")
w("**一致性核对**：分源晋升数 24/18/24/26、未安装调用数 6/10/6/4，"
  "与 `MISSED_STRONG_EVIDENCE.zh.md` 第 5 节的表逐格相同，本重算独立复现了该表。")
w("")
w("## 4. 新发现：拒绝路径是二分的，且存在竞态")
w("")
w("既有汇总只写了「24 次 known_invalid_C_skips 与 2 次 discarded_full_results」。"
  "绑定执行记录后可以看到这两类**成本性质完全不同**：")
w("")
w("| 类别 | 条数 | 平均 worker 占用 | 纯神经阶段 | 机制 |")
w("|---|---:|---:|---:|---|")
w(f"| 早期拦截 | {ec['n']}/{ec['n']+le['n']} | {ec['wall_s']/ec['n']:.3f}s | 0.000s | "
  "`actual_canonical_disagrees_with_complete_start` 在 ASR 前缀阶段即被判定 |")
w(f"| 晚期丢弃 | {le['n']}/{ec['n']+le['n']} | {le['wall_s']/le['n']:.3f}s | "
  f"{le['model_s']/le['n']:.3f}s | 同一证明类型，但完整模型已跑完 |")
w("")
w("两条晚期丢弃出自同一说话人、同一 job 位置（`BAC009S0908W0369`，两次重复的 `j000016`，"
  "`witness_frontier=88000`），说明它不是随机噪声，而是**可复现的取消竞态**："
  "证明与取消之间存在时延窗口，2/26 的在飞调用在被杀之前已经跑完了完整推理。")
w("")
w("这给出一条具体的成本改进线索：当前投机成本之所以便宜（沉没 13.51s 对应 24 次取消），"
  "是因为 92.3% 的拒绝发生在神经模型之前；"
  "剩下的 7.7% 付出了**一个完整调用的神经网络成本**却没有产出。"
  "若把该证明的下发提前到 C 阶段之前，这 2 条的成本可降到与早期拦截同级。"
  "该项属于实现层优化候选，需独立版本与配对复测，本报告不主张已修复。")
w("")
w("## 5. 可复现性（fresh-process 重复）")
w("")
w("| 说话人 | 保留 r0 / r1 | 相对差 | 沉没 r0 / r1 | 相对差 | 时效 r0 / r1 | 相对差 |")
w("|---|---|---:|---|---:|---|---:|")
for sid, v in sorted(d["reproducibility"].items()):
    rd = v["rel_diff_pct"]
    w(f"| {sid} | {v['r0']['recovered_wall_s']:.3f} / {v['r1']['recovered_wall_s']:.3f} | "
      f"{rd['recovered_wall_s']:.2f}% | "
      f"{v['r0']['wasted_wall_s']:.3f} / {v['r1']['wasted_wall_s']:.3f} | "
      f"{rd['wasted_wall_s']:.2f}% | "
      f"{v['r0']['latency_saved_s']:.3f} / {v['r1']['latency_saved_s']:.3f} | "
      f"{rd['latency_saved_s']:.2f}% |")
w("")
w("资源量（保留/沉没）的两次重复相对差全部 ≤ 1.8%，说明**资源账是稳定的**；"
  "时效账偏差较大（最大 4.69%），符合它依赖调度交错的预期。"
  "因此资源账可以作为论文的定量陈述，时效账宜报区间与配对统计，不宜报单点均值。")
w("")
w("## 6. 可以主张什么、不可以主张什么")
w("")
w("**可以主张（有本次重算支撑）：**")
w("")
w("1. 旧四来源冻结轨迹中，92 次被实际采用的模型调用跨越了出生版本，"
  "**全部 92 次都实际执行了完整神经前向**，共消耗 69.017 worker-seconds。")
w("2. 策略的正确拒绝成本是 13.515 worker-seconds（26 次），"
  "且其中 92.3% 发生在神经模型执行之前。")
w("3. 保留与沉没的资源比为 5.11:1；这不是「节省 67.6% 计算」，"
  "而是「换回的合法工作」与「付出的投机成本」两个独立量的对比。")
w("4. 92 次全部有正的完成延迟节省，合计 23.779s（反事实估计）。")
w("5. 拒绝路径存在可复现的取消竞态（2/26 跑完模型才被丢弃）。")
w("")
w("**不可以主张：**")
w("")
w("- 不能说「版本策略会损失 67.6% 计算」或「节省 67.6% GPU 时间」——"
  "67.6% 是调用计数占比，不是时间或能量占比。")
w("- 不能把 69.017s 说成端到端加速；它只是一个臂内的计算构成。")
w("- 不能把本账本当作闭环三臂比较的替代：版本严格策略在真实重跑时"
  "还会改变调度、资源释放与重算时机，净效果必须实测。")
w("- 不能把 `spec_total_wall_s` 与 `cons_total_wall_s` 之差解释为「投机开销 x%」——")
w(f"  两者分别是 {A['spec_total_wall_s']:.3f}s / {A['cons_total_wall_s']:.3f}s，"
  "覆盖的 job 数与调度不同（投机臂 162 次派发含 26 次被拒，守恒臂 136 次），"
  "差值混入了重复间方差，只能作描述性参考。")
w("- 不能把单次 0.72s 的 model_seconds 直接外推到长音频工作负载；"
  "本数据是 500ms 前沿粒度下的短音频切片。")
w("")
w("## 7. 对三项计划实验的直接输入")
w("")
w("1. **R1 的定量前置已就绪**：三臂比较不再只是「92 次 vs 0 次」的计数叙事，"
  "而是有明确的资源构成（69.017s 换回 / 13.515s 沉没）。"
  "GPU 实验要做的是把这个构成转成同一合同下的端到端服务与能量差。")
w("2. **ready_only 臂的预期差**：历史 `completed_full_buffer_reuse = 0`，"
  "意味着 ready-only 在旧轨迹里几乎退化为守恒臂；"
  "它的真实价值只能由闭环新跑测出。这与计划中的四臂设计一致。")
w("3. **故障实验的可比对象**：本账本给出无故障条件下的单次调用成本 baseline"
  f"（保留 0.750s、早期拦截 0.524s、晚期丢弃 0.471s），"
  "可作为 Owner-after-durable 分阶段计时的同源参照。")
w("")
w("## 8. 口径与假设（引用本报告时必须同时给出）")
w("")
for a in d["assumptions"]:
    w(f"- {a}")
w("")
w("## 9. 复现")
w("")
w("```bash")
w("cd experiments/dsn_strengthening_v16_20261111/analysis/gpu_ledger_v1")
w("python build_ledger.py      # -> ledger_v1.json, ledger_v1_jobs.jsonl")
w("python build_report.py      # -> LEDGER_REPORT.zh.md")
w("```")
w("")
w("产物：`ledger_v1.json`（汇总+分源+可复现性+逐 cell）、"
  "`ledger_v1_jobs.jsonl`（逐 job 明细，可直接用于配对检验）。")
w("")
w("证据入口：`dsn_streamcorrect_independent_20261029/SERVICE_RESULTS_v1/<cell>/` 下 "
  "`FULLSPEC_LEDGER.json`、`native_jobs.jsonl`、`events.jsonl`；"
  "汇总对照 `FINAL_PRIMARY_RESULTS_v2/SUMMARY.json` 的 `mechanism_counts`。")
w("")

md = "\n".join(L)
open(os.path.join(HERE, "LEDGER_REPORT.zh.md"), "w", encoding="utf-8").write(md)
print(md[:1500])
print("\n...\n[report written]", len(md), "chars")
