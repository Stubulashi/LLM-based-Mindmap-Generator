"""
C: 步骤1 — 全量评估与候选排序：在全部完整 session 中，按「表现最好且最稳定」筛选录音。
E: Step 1 — Full evaluation & candidate ranking: select the best+most-stable recording
   across all complete sessions.
口径 / Criteria:
  - 表现好：Node-F1/Edge-F1/UAS/Entity-Recall 在 GTC 与 YQL 双基准下均值高（Edge-F1/UAS 不为 0 优先）
  - 稳定：GTC 与 YQL 两基准差异小；多 run session 内 run 间波动小
用法 / Usage:
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 venv/bin/python scripts/select_best_example.py
"""
import sys
import os
import glob
import json

sys.path.insert(0, os.getcwd())

from evaluation.core.data_loader import DataLoader
from evaluation.core.aligner import HungarianAligner
from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
from evaluation.label.eval_label import evaluate_label_quality

SESSIONS_BASE = "evaluation/data/sessions"
GOLD_BASE = "evaluation/data/gold"
COMPLETE_SESSIONS = [
    "20260730_085917", "20260730_111823", "20260730_113028",
    "20260730_123948", "20260730_130242",
    "20260804_091256", "20260804_092828", "20260805_080833", "20260805_193528",
]
PAIR_PREFIX = "Saarland University"


def gold_map(pair_name, baseline):
    p = os.path.join(GOLD_BASE, baseline, f"{pair_name}.json")
    return DataLoader.from_map_file(p) if os.path.isfile(p) else None


def list_gen_files(pair_dir):
    """Return list of gen-file paths (generated_map.json or generated_map_runN.json)."""
    f1 = os.path.join(pair_dir, "generated_map.json")
    if os.path.isfile(f1):
        return [f1]
    return sorted(glob.glob(os.path.join(pair_dir, "generated_map_run*.json")))


def pair_metrics(gold, gen):
    """Return (label_dict, hier_metrics) or None."""
    if gen is None or not gen.nodes:
        return None
    aligner = HungarianAligner(threshold=0.70)
    alignment = aligner.align(gold.nodes, gen.nodes)
    lab = evaluate_label_quality(gold, gen, aligner)
    hier = evaluate_hierarchy_quality(gold, gen, alignment)
    return lab, hier


def eval_one(gen_data, gold):
    gen = DataLoader.from_flat_dict(gen_data) if isinstance(gen_data, dict) else None
    return pair_metrics(gold, gen)


def main():
    # results: key=(session,pair) -> dict with metrics per baseline and per run
    samples = []  # list of dict
    for sess in COMPLETE_SESSIONS:
        sdir = os.path.join(SESSIONS_BASE, sess)
        if not os.path.isdir(sdir):
            continue
        for d in sorted(os.listdir(sdir)):
            if not d.startswith(PAIR_PREFIX):
                continue
            pair_dir = os.path.join(sdir, d)
            if not os.path.isdir(pair_dir):
                continue
            gen_files = list_gen_files(pair_dir)
            if not gen_files:
                continue
            # separate primary vs multi-run
            primary_files = [f for f in gen_files if "run" not in os.path.basename(f)]
            run_files = [f for f in gen_files if "run" in os.path.basename(f)]
            primary_files = primary_files or run_files[:1]  # prefer single non-run file
            run_files = run_files or []

            gold_g = gold_map(d, "GTC")
            gold_y = gold_map(d, "YQL")

            def by_baseline(gen_data):
                res = {}
                if gold_g:
                    m = eval_one(gen_data, gold_g)
                    res["GTC"] = m
                if gold_y:
                    m = eval_one(gen_data, gold_y)
                    res["YQL"] = m
                return res

            # primary (single representative) metrics
            prim_dat = None
            with open(primary_files[0], "r", encoding="utf-8") as f:
                prim_dat = json.load(f)
            base_rows = by_baseline(prim_dat)

            # per-run metrics (for stability) — use same golds
            run_rows = []
            for rf in run_files or primary_files[:1]:
                with open(rf, "r", encoding="utf-8") as f:
                    rd = json.load(f)
                run_rows.append(by_baseline(rd))

            samples.append({
                "session": sess,
                "pair": d,
                "primary_files": primary_files,
                "run_files": run_files,
                "num_runs": max(1, len(run_files)),
                "base_rows": base_rows,
                "run_rows": run_rows,
            })

    # Aggregate ranking
    def metric_val(row, baseline, key):
        m = row.get(baseline) if row else None
        if not m:
            return None
        lab, hier = m
        if key in ("node_f1", "entity_recall"):
            return getattr(lab, key)
        return getattr(hier, key)

    ranked = []
    for s in samples:
        # mean over GTC/YQL of primary sample
        keys = ["node_f1", "edge_f1", "uas", "entity_recall"]
        means = {}
        for k in keys:
            vals = [metric_val(s["base_rows"], b, k) for b in ("GTC", "YQL")]
            vals = [v for v in vals if v is not None]
            means[k] = sum(vals) / len(vals) if vals else None
        # baseline diff (stability across GTC/YQL) for primary
        diffs = {}
        for k in keys:
            g = metric_val(s["base_rows"], "GTC", k)
            y = metric_val(s["base_rows"], "YQL", k)
            if g is not None and y is not None:
                diffs[k] = abs(g - y)
        # run variance: for each baseline, std of edge_f1 across runs of the (first) run_files
        run_var_edge = None
        if s["run_rows"]:
            var_list = []
            for k in ("edge_f1", "uas"):
                coll = []
                for rr in s["run_rows"]:
                    for b in ("GTC", "YQL"):
                        v = metric_val(rr, b, k)
                        if v is not None:
                            coll.append(v)
                if coll:
                    var_list.append((max(coll) - min(coll)))  # range
            run_var_edge = max(var_list) if var_list else None

        ranked.append({
            "session": s["session"],
            "pair": s["pair"],
            "nums_runs": s["num_runs"],
            "node_f1_mean": means["node_f1"],
            "edge_f1_mean": means["edge_f1"],
            "uas_mean": means["uas"],
            "entity_recall_mean": means["entity_recall"],
            "diff_node": diffs.get("node_f1"),
            "diff_edge": diffs.get("edge_f1"),
            "diff_uas": diffs.get("uas"),
            "base_diff_max": max(diffs.values()) if diffs else None,
            "run_var_max": run_var_edge,
            "edge_f1_gtc": metric_val(s["base_rows"], "GTC", "edge_f1"),
            "edge_f1_yql": metric_val(s["base_rows"], "YQL", "edge_f1"),
            "uas_gtc": metric_val(s["base_rows"], "GTC", "uas"),
            "uas_yql": metric_val(s["base_rows"], "YQL", "uas"),
            "node_gtc": metric_val(s["base_rows"], "GTC", "node_f1"),
            "node_yql": metric_val(s["base_rows"], "YQL", "node_f1"),
        })

    # Sort: higher edge_f1_mean priority, then lower diff
    ranked.sort(key=lambda r: (
        r["edge_f1_mean"] if r["edge_f1_mean"] is not None else -1,
        r["uas_mean"] if r["uas_mean"] is not None else -1,
        r["node_f1_mean"] if r["node_f1_mean"] is not None else -1,
        -(r["base_diff_max"] if r["base_diff_max"] is not None else 0),
    ), reverse=True)

    print("=" * 130)
    print("CANDIDATE RANKING (sorted by best+stability) / 候选排序")
    hdr = (f"{'rank':>4} {'pair':<8} {'sess':<16} | "
           f"{'node G/Y':>12} {'edge G/Y':>12} {'UAS G/Y':>11} | "
           f"{'edgeM':>6} {'uasM':>6} {'nodeM':>6} | {'difMx':>6} {'runVar':>6}")
    print(hdr)
    print("-" * 130)

    def fmt2(a, b):
        sa = "-" if a is None else "%.2f" % a
        sb = "-" if b is None else "%.2f" % b
        return "%s/%s" % (sa, sb)

    def fmt1(v):
        return "-" if v is None else "%.3f" % v

    for i, r in enumerate(ranked, 1):
        line = "%4d %-8s %-16s | " % (i, r["pair"].replace("Saarland University ", "U"), r["session"])
        line += "%13s " % fmt2(r["node_gtc"], r["node_yql"])
        line += "%13s " % fmt2(r["edge_f1_gtc"], r["edge_f1_yql"])
        line += "%12s | " % fmt2(r["uas_gtc"], r["uas_yql"])
        line += "%6s %6s %6s | " % (fmt1(r["edge_f1_mean"]), fmt1(r["uas_mean"]), fmt1(r["node_f1_mean"]))
        line += "%6s %6s" % ("-" if r["base_diff_max"] is None else "%.2f" % r["base_diff_max"],
                             "-" if r["run_var_max"] is None else "%.2f" % r["run_var_max"])
        print(line)
    print()
    # Print final selection top-5 detail
    print("TOP 5 DETAIL / 前 5 详细：")
    for r in ranked[:5]:
        print(f"  {r['session']}/{r['pair']}  runs={r['nums_runs']}  "
              f"node(mean)={r['node_f1_mean']:.3f} edge(mean)={r['edge_f1_mean']:.3f} "
              f"uas(mean)={r['uas_mean']:.3f} entR(mean)={r['entity_recall_mean']:.3f}")
        print(f"      GTC: node={r['node_gtc']:.3f} edge={r['edge_f1_gtc']:.3f} uas={r['uas_gtc']:.3f} | "
              f"YQL: node={r['node_yql']:.3f} edge={r['edge_f1_yql']:.3f} uas={r['uas_yql']:.3f} | "
              f"baseDiffMax={r['base_diff_max']:.2f} runVar={r['run_var_max']}")


if __name__ == "__main__":
    main()
