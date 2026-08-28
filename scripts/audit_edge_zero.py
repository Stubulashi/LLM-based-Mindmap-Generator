"""
C: 边指标归零根因验证脚本（临时） / E: Edge-metric-zero root-cause audit (temp)
用法 / Usage:
  venv/bin/python scripts/audit_edge_zero.py
比对逻辑：
  - 复现 _find_gold_for_pair 的加载路径（root -> GTC -> YQL）
  - 分别用 GTC / YQL 金标准对 20260804_092828 批次生成图做边集合比对
  - 确认是否「评估未正确读取/匹配边」还是「生成树结构确实不达标」
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from evaluation.core.data_loader import DataLoader
from evaluation.core.aligner import HungarianAligner

GOLD_ROOT = "evaluation/data/gold"
SESSION = "evaluation/data/sessions/20260804_092828"
PAIRS = ["Saarland University 1", "Saarland University 6"]


def find_gold(pair_name):
    """复现 run_evaluation.run_reuse_sessions._find_gold_for_pair"""
    candidates = [
        os.path.join(GOLD_ROOT, f"{pair_name}.json"),
        os.path.join(GOLD_ROOT, "GTC", f"{pair_name}.json"),
        os.path.join(GOLD_ROOT, "YQL", f"{pair_name}.json"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c, os.path.dirname(c)
    return None, None


def run_pair(pair_name):
    print("=" * 78)
    print(f"PAIR: {pair_name}")
    gold_path, gold_dir = find_gold(pair_name)
    print(f"  _find_gold_for_pair -> {gold_path}   [dir={gold_dir}]")

    gen_path = os.path.join(SESSION, pair_name, "generated_map.json")
    with open(gen_path, "r", encoding="utf-8") as f:
        gen_data = json.load(f)
    print(f"  generated_map.json nodes={len(gen_data.get('nodes', []))} links={len(gen_data.get('links', []))}")

    # 若 _find_gold_for_pair 命中 root，则与 GTC/YQL 都无关；这里同时显式给出两种金标准
    for tag in ["GTC", "YQL"]:
        src = os.path.join(GOLD_ROOT, tag, f"{pair_name}.json")
        if not os.path.isfile(src):
            print(f"  [{tag}] 金标准不存在: {src}")
            continue
        gold = DataLoader.from_map_file(src)
        gen = DataLoader.from_flat_dict(gen_data)

        # E: Use tree-aware get_edges (now backfills flatten-dropped parent_id via tree)
        # C: 使用感知 tree 的 get_edges（现会经 tree 拓底扁平化丢掉的 parent_id）
        ge = set(gold.get_edges())
        pe = set(gen.get_edges())

        # 复现 eval 的 mu / 边匹配
        aligner = HungarianAligner(threshold=0.70)
        mu = aligner.align(gold.nodes, gen.nodes).mu
        tp = 0
        used = []
        for p, c in sorted(ge):
            if p in mu and c in mu:
                mapped = (mu[p], mu[c])
                hit = mapped in pe
                used.append((p, c, mapped, hit))
                if hit:
                    tp += 1
            else:
                used.append((p, c, "PART_NOT_MATCHED", False))

        print(f"  ---- {tag}金标准: gold_nodes={len(gold.nodes)} gold_edges={len(ge)} "
              f"gen_edges={len(pe)} tp={tp} ----")
        print(f"    GOLD_EDGES: {sorted(ge)}")
        print(f"    GEN_EDGES : {sorted(pe)}")
        print(f"    MU        : {mu}")
        for p, c, mapped, hit in used:
            print(f"      {'TP+' if hit else '   '} gold({p},{c}) -> {mapped}  {'HIT' if hit else 'miss'}")
    print()


if __name__ == "__main__":
    for p in PAIRS:
        run_pair(p)
