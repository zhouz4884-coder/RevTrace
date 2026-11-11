#!/usr/bin/env python3
"""
RevTrace 跨版本有效计算的资源/时效账本（v1）

纯 CPU、只读重算。数据源：experiments/dsn_streamcorrect_independent_20261029
冻结原始记录（旧四来源 16 格，两臂各 8 格）。不产生任何新 GPU/服务结果。

输入（只读，不修改）：
  SERVICE_RESULTS_v1/<cell>/FULLSPEC_LEDGER.json   promotions / discarded / abandoned
  SERVICE_RESULTS_v1/<cell>/native_jobs.jsonl      每 job 实际计算记录（record）
  SERVICE_RESULTS_v1/<cell>/events.jsonl           canonical_install 时间戳

输出：
  ledger_v1.json        逐 job 明细 + 分源汇总
  LEDGER_REPORT.zh.md   报告表（由 build_report.py 生成）

口径与假设（必须与结果一同报告，不得省略）：
  A1 「计算成本」取 record.worker_job_wall_seconds（worker 实际占用时长），
     同时单列 record.model_seconds（纯神经阶段）。两者不同，不能混用。
  A2 「跨版本」判定：promotion.birth_canonical_sha != promotion.actual_parent_sha。
     两者相等的晋升属于同版本晋升，版本策略本身也会保留，不计入跨版本收益。
  A3 「时效节省」= (父状态实际安装时刻 + 本 job model_seconds) - 本 job 完成时刻。
     含义：若某策略在父状态安装的瞬间杀掉该在飞调用并重派，则完成时刻会推迟这么多。
     这是反事实估计，不是实测重跑；为负表示保留并无时效收益。
  A4 「被取消成本」= ledger.abandoned/discarded 条目的
     worker_job_end_perf - worker_job_begin_perf（已实际沉没的占用）。
  A5 不把 audio-seconds、GPU-seconds、J 互换，不换算成加速比，不折算成「节省 x% 计算」。
"""
import json
import os
import sys
from collections import Counter, defaultdict

SVC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..",
    "dsn_streamcorrect_independent_20261029", "SERVICE_RESULTS_v1",
)
SVC = os.path.normpath(SVC)
OUT = os.path.dirname(os.path.abspath(__file__))


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(p):
    rows = []
    if not os.path.exists(p):
        return rows
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def arm_of(cell):
    if "two_full_spec_early" in cell:
        return "spec"
    if "two_full_early" in cell:
        return "conservative"
    return "unknown"


def source_of(cell):
    # SC_FINAL_INDEPENDENT_V1_two_full_spec_early_BAC009S0905W0246_r0
    for part in cell.split("_"):
        if part.startswith("BAC"):
            return part
    return cell


def repeat_of(cell):
    return cell.rsplit("_", 1)[-1] if cell.endswith(("_r0", "_r1")) else "?"


def main():
    cells = sorted(
        d for d in os.listdir(SVC)
        if os.path.isdir(os.path.join(SVC, d)) and d.startswith("SC_")
    )
    print(f"[ledger] 发现 {len(cells)} 个 cell", flush=True)

    per_job = []          # 逐条明细
    cell_rows = []        # 每 cell 汇总
    warnings = []
    sha_install_global = {}   # (cell, sha) -> install perf

    for cell in cells:
        cdir = os.path.join(SVC, cell)
        arm = arm_of(cell)
        src = source_of(cell)
        rep = repeat_of(cell)

        # --- 每个 job 的实际计算记录 ---
        jobs = {r["job_id"]: r for r in load_jsonl(os.path.join(cdir, "native_jobs.jsonl"))}

        # --- install 时刻：job_id -> observed ; end_state -> observed ---
        install_by_job = {}
        for e in load_jsonl(os.path.join(cdir, "events.jsonl")):
            if e.get("kind") == "canonical_install":
                install_by_job[e["job_id"]] = e.get("observed")
        sha_install = {}
        for jid, r in jobs.items():
            rec = r.get("record") or {}
            sha = rec.get("end_state")
            t = install_by_job.get(jid)
            if sha and t is not None:
                sha_install[sha] = t
                sha_install_global[(cell, sha)] = t

        row = {
            "cell": cell, "arm": arm, "source_id": src, "repeat": rep,
            "jobs_total": len(jobs),
            "jobs_native_model_evaluated": sum(
                1 for r in jobs.values() if (r.get("record") or {}).get("native_model_evaluated")
            ),
        }

        lf = os.path.join(cdir, "FULLSPEC_LEDGER.json")
        if not os.path.exists(lf):
            # 守恒臂：无 ledger。仅记录基线成本作参照。
            row.update({
                "promotions": 0, "promotions_cross_version": 0,
                "discarded": 0, "abandoned": 0,
                "recovered_wall_s": 0.0, "recovered_model_s": 0.0,
                "wasted_wall_s": 0.0, "wasted_model_s": 0.0,
                "latency_saved_s": 0.0, "latency_saved_n": 0,
                "has_ledger": False,
            })
            tot_wall = sum((r.get("record") or {}).get("worker_job_wall_seconds") or 0.0
                           for r in jobs.values())
            tot_model = sum((r.get("record") or {}).get("model_seconds") or 0.0
                            for r in jobs.values())
            row["baseline_wall_s"] = tot_wall
            row["baseline_model_s"] = tot_model
            cell_rows.append(row)
            continue

        L = load_json(lf)
        promos = L.get("promotions", []) or []
        discs = L.get("discarded", []) or []
        aband = L.get("abandoned", []) or []

        # ---------- 账 1：跨版本合法保留 ----------
        rec_wall = rec_model = 0.0
        n_cross = 0
        lat_saved = 0.0
        n_lat = 0
        for p in promos:
            jid = p.get("job_id")
            birth = p.get("birth_canonical_sha")
            parent = p.get("actual_parent_sha")
            cross = (birth is not None and parent is not None and birth != parent)
            rec = (jobs.get(jid) or {}).get("record") or {}
            wall = rec.get("worker_job_wall_seconds") or 0.0
            model = rec.get("model_seconds") or 0.0
            end = rec.get("worker_job_end_perf")
            disp = None
            # 父状态安装时刻
            t_parent = sha_install.get(parent) if parent else None

            lat = None
            if cross and end is not None and t_parent is not None:
                lat = (t_parent + model) - end
                lat_saved += lat
                n_lat += 1
            if cross:
                n_cross += 1
                rec_wall += wall
                rec_model += model
            per_job.append({
                "cell": cell, "arm": arm, "source_id": src, "repeat": rep,
                "role": "promotion", "job_id": jid,
                "cross_version": cross,
                "birth_sha": birth, "actual_parent_sha": parent,
                "wall_s": wall, "model_s": model,
                "dispatched_perf": disp,
                "parent_install_perf": t_parent,
                "job_end_perf": end,
                "latency_saved_s": lat,
                "native_model_evaluated": rec.get("native_model_evaluated"),
                "stage_execution": rec.get("stage_execution"),
            })

        # ---------- 账 2：被策略正确拒绝的投机沉没成本 ----------
        was_wall = was_model = 0.0
        refuse_detail = Counter()
        for grp, entries in (("abandoned", aband), ("discarded", discs)):
            for e in entries:
                jid = e.get("job_id")
                b = e.get("worker_job_begin_perf")
                en = e.get("worker_job_end_perf")
                if b is not None and en is not None:
                    wall = en - b
                else:
                    rec = (jobs.get(jid) or {}).get("record") or {}
                    wall = rec.get("worker_job_wall_seconds") or 0.0
                rec = (jobs.get(jid) or {}).get("record") or {}
                model = rec.get("model_seconds")
                model = 0.0 if model is None else model
                was_wall += wall
                was_model += model
                # 执行到了哪一步：优先用 worker 侧实际记录，其次用 ledger 布尔标记
                if rec:
                    stage = rec.get("stage_execution") or "unknown"
                    ran_model = bool(rec.get("native_model_evaluated"))
                else:
                    stage = "asr_prefix" if e.get("asr_prefix_executed") else "none"
                    if e.get("learned_C_executed"):
                        stage = "learned_C"
                    if e.get("C_U_completed"):
                        stage = "C_U_complete"
                    ran_model = False
                # early_cheap = 在神经模型之前就被拦住；late_expense = 已跑完完整模型才被丢弃
                rclass = "late_expensive" if ran_model else "early_cheap"
                refuse_detail[f"{grp}:{rclass}:{stage}"] += 1
                per_job.append({
                    "cell": cell, "arm": arm, "source_id": src, "repeat": rep,
                    "role": grp, "job_id": jid,
                    "cross_version": None, "birth_sha": None,
                    "actual_parent_sha": (e.get("proof") or {}).get("expected_cut_sha"),
                    "wall_s": wall, "model_s": model,
                    "dispatched_perf": None, "parent_install_perf": None,
                    "job_end_perf": en, "latency_saved_s": None,
                    "native_model_evaluated": (rec.get("native_model_evaluated") if rec else None),
                    "stage_execution": stage,
                    "reject_class": rclass,
                    "proof_kind": (e.get("proof") or {}).get("kind"),
                    "witness_frontier": (e.get("proof") or {}).get("witness_frontier"),
                })

        row.update({
            "has_ledger": True,
            "promotions": len(promos),
            "promotions_cross_version": n_cross,
            "discarded": len(discs),
            "abandoned": len(aband),
            "recovered_wall_s": rec_wall,
            "recovered_model_s": rec_model,
            "wasted_wall_s": was_wall,
            "wasted_model_s": was_model,
            "latency_saved_s": lat_saved,
            "latency_saved_n": n_lat,
            "refuse_detail": dict(refuse_detail),
            "baseline_wall_s": sum((r.get("record") or {}).get("worker_job_wall_seconds") or 0.0
                                   for r in jobs.values()),
        })
        cell_rows.append(row)

        if n_lat < n_cross:
            warnings.append(
                f"{cell}: {n_cross - n_lat} 个跨版本晋升找不到父状态安装时刻，未计入时效账")

    # ---------------- 汇总 ----------------
    spec = [r for r in cell_rows if r["arm"] == "spec"]
    cons = [r for r in cell_rows if r["arm"] == "conservative"]

    def s(rows, k):
        return sum(r.get(k) or 0 for r in rows)

    agg = {
        "cells": len(cell_rows),
        "spec_cells": len(spec),
        "conservative_cells": len(cons),
        "promotions": s(spec, "promotions"),
        "promotions_cross_version": s(spec, "promotions_cross_version"),
        "discarded": s(spec, "discarded"),
        "abandoned": s(spec, "abandoned"),
        "recovered_wall_s": s(spec, "recovered_wall_s"),
        "recovered_model_s": s(spec, "recovered_model_s"),
        "wasted_wall_s": s(spec, "wasted_wall_s"),
        "wasted_model_s": s(spec, "wasted_model_s"),
        "latency_saved_s": s(spec, "latency_saved_s"),
        "latency_saved_n": s(spec, "latency_saved_n"),
        "spec_total_wall_s": s(spec, "baseline_wall_s"),
        "cons_total_wall_s": s(cons, "baseline_wall_s"),
    }

    # 分源（用于与既有文档的 24/18/24/26 表对照）
    by_src = defaultdict(lambda: {"promotions": 0, "cross_version": 0,
                                  "abandoned": 0, "discarded": 0,
                                  "recovered_wall_s": 0.0, "wasted_wall_s": 0.0,
                                  "latency_saved_s": 0.0})
    for r in spec:
        b = by_src[r["source_id"]]
        b["promotions"] += r["promotions"]
        b["cross_version"] += r["promotions_cross_version"]
        b["abandoned"] += r["abandoned"]
        b["discarded"] += r["discarded"]
        b["recovered_wall_s"] += r["recovered_wall_s"]
        b["wasted_wall_s"] += r["wasted_wall_s"]
        b["latency_saved_s"] += r["latency_saved_s"]

    # 拒绝成本分类：early_cheap（模型前拦截） vs late_expensive（跑完模型才丢）
    rej_class = defaultdict(lambda: {"n": 0, "wall_s": 0.0, "model_s": 0.0})
    for j in per_job:
        if j["role"] in ("abandoned", "discarded"):
            b = rej_class[j.get("reject_class") or "unknown"]
            b["n"] += 1
            b["wall_s"] += j["wall_s"]
            b["model_s"] += j["model_s"]

    # 可复现性：同一 source 的 r0 vs r1（fresh-process 重复）
    repro = {}
    for sid in sorted({r["source_id"] for r in spec}):
        pair = {r["repeat"]: r for r in spec if r["source_id"] == sid}
        if set(pair) != {"r0", "r1"}:
            continue
        a, b = pair["r0"], pair["r1"]

        def rel(x, y):
            return None if not y else abs(x - y) / abs(y) * 100.0

        keys = ("promotions_cross_version", "abandoned", "discarded",
                "recovered_wall_s", "wasted_wall_s", "latency_saved_s")
        repro[sid] = {
            "r0": {k: a[k] for k in keys},
            "r1": {k: b[k] for k in keys},
            "rel_diff_pct": {k: rel(a[k], b[k]) for k in
                             ("recovered_wall_s", "wasted_wall_s", "latency_saved_s")},
        }

    out = {
        "schema": "revtrace_cross_version_ledger_v1",
        "data_source": SVC,
        "assumptions": [
            "A1 计算成本=record.worker_job_wall_seconds；model_seconds 单列为纯神经阶段",
            "A2 跨版本=birth_canonical_sha != actual_parent_sha；相等的同版本晋升不计入",
            "A3 时效节省=(父状态安装时刻+本job model_seconds)-本job完成时刻（反事实估计）",
            "A4 被取消成本=worker_job_end_perf-worker_job_begin_perf（已实际沉没）",
            "A5 不混用 audio-s/GPU-s/J，不折算加速比",
        ],
        "aggregate": agg,
        "reject_class": dict(rej_class),
        "reproducibility": repro,
        "by_source": dict(by_src),
        "cells": cell_rows,
        "warnings": warnings,
    }
    with open(os.path.join(OUT, "ledger_v1.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, "ledger_v1_jobs.jsonl"), "w", encoding="utf-8") as f:
        for r in per_job:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps(agg, ensure_ascii=False, indent=2), flush=True)
    print("\n分源（spec 臂）:", flush=True)
    for k, v in sorted(by_src.items()):
        print(f"  {k}: 晋升{v['promotions']} 跨版本{v['cross_version']} "
              f"取消{v['abandoned']}+{v['discarded']} "
              f"回收{v['recovered_wall_s']:.3f}s 沉没{v['wasted_wall_s']:.3f}s "
              f"时效{v['latency_saved_s']:.3f}s", flush=True)
    if warnings:
        print("\n警告:", flush=True)
        for w in warnings:
            print("  -", w, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
