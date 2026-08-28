"""
C: 生成侧树形后处理优化效果验证脚本（对比原始 vs 后处理）
E: Verify generated-side tree post-processing benefit (original vs postprocessed)

用法 / Usage:
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 venv/bin/python scripts/audit_postprocess.py [session_ts ...]

对指定 session 每个 pair：用 GTC 金标准分别评估「原始生成图」与「经 postprocess_map_structure 修复后的图」，
对比 Edge-F1 / UAS / edge_tp / edge_fp / edge_fn。
"""
import sys
import os
import json
import glob

sys.path.insert(0, os.getcwd())

from evaluation.core.data_loader import DataLoader
from evaluation.core.aligner import HungarianAligner
from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
from mindmap_agent import postprocess_map_structure

GOLD_ROOT = "evaluation/data/gold"
SESSIONS = sys.argv[1:] or ["20260804_092828", "20260730_123948"]
PAIRS = sys.argv[1:] and [] or None  # None -> 全部


def load_gold(pair_name):
    p = os.path.join(GOLD_ROOT, "GTC", f"{pair_name}.json")
    return DataLoader.from_map_file(p) if os.path.isfile(p) else None


def gen_files_of(pair_dir):
    f1 = os.path.join(pair_dir, "generated_map.json")
    if os.path.isfile(f1):
        return [f1]
    runs = sorted(glob.glob(os.path.join(pair_dir, "generated_map_run*.json")))
    return runs


def metric(gold, gen_data):
    if not gen_data or not gen_data.get("nodes"):
        return None
    gen = DataLoader.from_flat_dict(gen_data)
    aligner = HungarianAligner(threshold=0.70)
    alignment = aligner.align(gold.nodes, gen.nodes)
    h = evaluate_hierarchy_quality(gold, gen, alignment)
    return h


def run_session(session_ts):
    session_dir = os.path.join("evaluation/data/sessions", session_ts)
    if not os.path.isdir(session_dir):
        print(f"[skip] session not found: {session_ts}")
        return
    print("=" * 76)
    print(f"SESSION: {session_ts}")
    hdr = f"{'pair':<22} | {'orig EF1':>8} {'UAS':>6} {'tp':>3} {'fp':>3} {'fn':>3} | {'post EF1':>8} {'UAS':>6} {'tp':>3} {'fp':>3} {'fn':>3}"
    print(hdr)
    print("-" * 76)
    for d in sorted(os.listdir(session_dir)):
        if not d.startswith("Saarland"):
            continue
        pair_dir = os.path.join(session_dir, d)
        if not os.path.isdir(pair_dir):
            continue
        gold = load_gold(d)
        if gold is None:
            continue
        files = gen_files_of(pair_dir)
        if not files:
            continue
        # 取第一个 gen 文件做对比（与记录一致）
        with open(files[0], "r", encoding="utf-8") as f:
            raw = json.load(f)
        orig = metric(gold, raw)
        post = metric(gold, postprocess_map_structure(raw))

        def fmt(m):
            if m is None:
                return f"{'-':>8} {'-':>6} {'-':>3} {'-':>3} {'-':>3}"
            return f"{m.edge_f1:>8.3f} {m.uas:>6.3f} {m.edge_tp:>3} {m.edge_fp:>3} {m.edge_fn:>3}"
        print(f"{d:<22} | {fmt(orig)} | {fmt(post)}")
    print()


if __name__ == "__main__":
    for s in SESSIONS:
        run_session(s)
