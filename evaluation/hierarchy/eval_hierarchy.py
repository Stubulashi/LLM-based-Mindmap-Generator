"""
E: §2 Hierarchy Structure Accuracy
C: §2 层级结构正确率评估 — Hierarchy Structure Accuracy

Evaluation_Schema.md §2.1~2.5
包含 / Includes:
  - 2.1 Edge-P / Edge-R / Edge-F1
  - 2.2 UAS (Unlabeled Attachment Score)
  - 2.3 nTED (normalized Tree Edit Distance)
  - 2.4 PC-F1 (Parent-Child F1)
  - 2.5 LAR (Level Alignment Rate)
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from evaluation.core.aligner import AlignmentResult
from evaluation.core.data_loader import MindMapData
from evaluation.core.embedder import compute_similarity_matrix
from evaluation.utils.tree_utils import (
    extract_edges, extract_parent_child_pairs, compute_depth_map,
)


@dataclass
class HierarchyMetrics:
    """E: §2 Hierarchy evaluation results / C: §2 层级结构评估结果"""
    # 2.1 Edge-P/R/F1 / 边精确率/召回率/F1
    edge_precision: float
    edge_recall: float
    edge_f1: float
    edge_tp: int
    edge_fp: int
    edge_fn: int

    # 2.2 UAS / 无标注依存得分
    uas: float

    # 2.3 nTED / 归一化树编辑距离
    nted: Optional[float]
    raw_ted: float = 0.0

    # 2.4 PC-F1 / 父子 F1
    pc_precision: float = 0.0
    pc_recall: float = 0.0
    pc_f1: float = 0.0
    pc_tp: int = 0

    # 2.5 LAR / 层级对齐率
    lar: float = 0.0

    # 2.6 Alignment coverage / 对齐覆盖（供诊断区分“无对齐”与“父级错误”）
    aligned_count: int = 0

    def to_dict(self) -> dict:
        return {
            'edge_precision': round(self.edge_precision, 4),
            'edge_recall': round(self.edge_recall, 4),
            'edge_f1': round(self.edge_f1, 4),
            'edge_tp': self.edge_tp,
            'edge_fp': self.edge_fp,
            'edge_fn': self.edge_fn,
            'uas': round(self.uas, 4),
            'nted': round(self.nted, 4) if self.nted is not None else None,
            'raw_ted': round(self.raw_ted, 4),
            'pc_precision': round(self.pc_precision, 4),
            'pc_recall': round(self.pc_recall, 4),
            'pc_f1': round(self.pc_f1, 4),
            'pc_tp': self.pc_tp,
            'lar': round(self.lar, 4),
            'aligned_count': self.aligned_count,
        }


def evaluate_hierarchy_quality(
    gold_map: MindMapData,
    gen_map: MindMapData,
    alignment: AlignmentResult,
    similarity_threshold: float = 0.70,
) -> HierarchyMetrics:
    """
    E: Compute all §2 hierarchy metrics.
        Depends on §1.1 AlignmentResult as node mapping foundation.
    C: 执行 §2 所有层级结构指标的完整计算。
        依赖 §1.1 的 AlignmentResult 作为节点映射基础。

    参数 / Args:
        gold_map: 金标准导图 / Gold standard mind map
        gen_map: 生成导图 / Generated mind map
        alignment: 匈牙利匹配结果 (来自 eval_label 或 aligner.align) / Hungarian alignment result (from eval_label or aligner.align)
        similarity_threshold: 语义相似度阈值 τ (用于 PC-F1) / Semantic similarity threshold τ (for PC-F1)

    返回 / Returns:
        HierarchyMetrics: 包含所有 §2 指标 / Contains all §2 metrics
    """
    mu = alignment.mu
    inv_mu = alignment.inv_mu

    gold_edges = gold_map.get_edges()
    gen_edges = gen_map.get_edges()
    gold_edge_set = set(gold_edges)
    gen_edge_set = set(gen_edges)

    # =========================================================
    # 2.1 Edge-P/R/F1 / 边精确率/召回率/F1
    # =========================================================
    edge_tp = 0
    for parent, child in gold_edges:
        if parent in mu and child in mu:
            if (mu[parent], mu[child]) in gen_edge_set:
                edge_tp += 1

    edge_fn = len(gold_edges) - edge_tp
    edge_fp = len(gen_edges) - edge_tp

    edge_p = edge_tp / len(gen_edges) if len(gen_edges) > 0 else 1.0
    edge_r = edge_tp / len(gold_edges) if len(gold_edges) > 0 else 1.0
    edge_f1 = (2 * edge_p * edge_r / (edge_p + edge_r)
               if (edge_p + edge_r) > 0 else 0.0)

    # =========================================================
    # 2.2 UAS (Unlabeled Attachment Score) / 无标注依存得分
    # =========================================================
    gold_parent = {}
    for p, c in gold_edges:
        gold_parent[c] = p
    gen_parent = {}
    for p, c in gen_edges:
        gen_parent[c] = p

    # E: Guard — non-empty alignment with empty edge sets makes parent matching
    #    unreliable (every node would look like a root). Warn instead of silent
    #    inflation; the empty-mu case itself is handled below with explicit 0.0.
    # C: 边界加固 — 对齐非空但任一边集为空时，父匹配不可靠（所有节点都会像根节点）。
    #    显式告警而非静默虚高；空 mu 的情况在下文显式返回 0.0。
    if len(mu) > 0 and (not gold_edges or not gen_edges):
        import logging
        logging.getLogger(__name__).warning(
            "[eval_hierarchy] UAS: gold or gen edge set is empty with non-empty alignment — "
            "parent matching may be unreliable / 金标准或生成边集为空但存在对齐节点，父匹配可能不可靠"
        )

    uas_correct = 0
    uas_total = len(mu)
    if uas_total == 0:
        # E: No aligned nodes — explicit 0.0 marker instead of misleading 1.0
        # C: 无对齐节点 — 返回显式 0.0 标记而非误导性的 1.0
        import logging
        logging.getLogger(__name__).warning(
            "[eval_hierarchy] UAS: mu is empty (no aligned nodes), returning 0.0 / 无对齐节点，UAS 返回 0.0"
        )
        uas = 0.0
    else:
        for gold_id, gen_id in mu.items():
            g_parent = gold_parent.get(gold_id)  # None if root / 若无则为根节点
            gen_parent_node = gen_parent.get(gen_id)

            if g_parent is None and gen_parent_node is None:
                # both roots / 两个都是根节点
                uas_correct += 1
            elif g_parent is not None and gen_parent_node is not None:
                expected_gen_parent = mu.get(g_parent)
                if expected_gen_parent == gen_parent_node:
                    uas_correct += 1

        uas = uas_correct / uas_total

    # =========================================================
    # 2.3 nTED (normalized Tree Edit Distance) / 归一化树编辑距离
    # =========================================================
    # E: None means zss library not installed, unavailable
    # C: None 表示 zss 库未安装，无法计算
    nted: Optional[float] = None
    raw_ted = 0.0
    try:
        nted, raw_ted = _compute_nted(gold_map, gen_map)
    except ImportError:
        # zss not installed / zss 未安装
        import logging
        logging.getLogger(__name__).warning(
            "[eval_hierarchy] nTED unavailable: zss library not installed / zss 库未安装，nTED 返回 None"
        )
        nted = None
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"[eval_hierarchy] nTED computation failed / nTED 计算失败: {e}, returning None"
        )
        nted = None

    # =========================================================
    # 2.4 PC-F1 (Parent-Child F1) / 父子 F1
    # =========================================================
    # E: Schema §2.4 — Check parent and child labels independently
    # C: Schema §2.4 — 分别检查父标签和子标签是否均语义匹配
    gold_pairs = extract_parent_child_pairs(gold_map.nodes, gold_map.links)
    gen_pairs = extract_parent_child_pairs(gen_map.nodes, gen_map.links)

    pc_correct = 0
    if gold_pairs and gen_pairs:
        gold_p_labels = [(p_label, c_label) for p_label, c_label, _, _ in gold_pairs]
        gen_p_labels = [(p_label, c_label) for p_label, c_label, _, _ in gen_pairs]

        # E: Extract parent and child label lists separately
        # C: 分别提取父标签列表和子标签列表
        gold_parents = [p for p, c in gold_p_labels]
        gold_children = [c for p, c in gold_p_labels]
        gen_parents = [p for p, c in gen_p_labels]
        gen_children = [c for p, c in gen_p_labels]

        # E: Compute parent-parent and child-child similarity matrices
        # C: 分别计算父-父和子-子相似度矩阵
        parent_S = compute_similarity_matrix(gold_parents, gen_parents, alignment.model_name)
        child_S = compute_similarity_matrix(gold_children, gen_children, alignment.model_name)

        # E: Hit if parent_sim >= tau AND child_sim >= tau — global optimal
        #    one-to-one assignment (order-independent), replacing the previous
        #    first-fit greedy loop that systematically underestimated pc_tp.
        # C: 判定命中 — 父相似度 >= τ AND 子相似度 >= τ，全局最优一对一指派
        #    （与排列顺序无关），替换此前顺序敏感的贪心匹配（会低估 pc_tp）。
        hit = (parent_S >= similarity_threshold) & (child_S >= similarity_threshold)
        if hit.size:
            from scipy.optimize import linear_sum_assignment
            g_idx, c_idx = linear_sum_assignment(-hit.astype(float))
            pc_correct = int(hit[g_idx, c_idx].sum())

    pc_recall = pc_correct / len(gold_pairs) if gold_pairs else 1.0
    pc_precision = pc_correct / len(gen_pairs) if gen_pairs else 1.0
    pc_f1 = (2 * pc_precision * pc_recall / (pc_precision + pc_recall)
             if (pc_precision + pc_recall) > 0 else 0.0)

    # =========================================================
    # 2.5 LAR (Level Alignment Rate) / 层级对齐率
    # =========================================================
    gold_depths = gold_map.get_depths()
    gen_depths = gen_map.get_depths()

    lar_correct = 0
    lar_total = len(mu)
    if lar_total == 0:
        # E: No aligned nodes — explicit 0.0 marker instead of misleading 1.0
        # C: 无对齐节点 — 返回显式 0.0 标记而非误导性的 1.0
        import logging
        logging.getLogger(__name__).warning(
            "[eval_hierarchy] LAR: mu is empty (no aligned nodes), returning 0.0 / 无对齐节点，LAR 返回 0.0"
        )
        lar = 0.0
    else:
        for gold_id, gen_id in mu.items():
            if gold_depths.get(gold_id) == gen_depths.get(gen_id):
                lar_correct += 1

        lar = lar_correct / lar_total

    return HierarchyMetrics(
        edge_precision=edge_p,
        edge_recall=edge_r,
        edge_f1=edge_f1,
        edge_tp=edge_tp,
        edge_fp=edge_fp,
        edge_fn=edge_fn,
        uas=uas,
        nted=nted,
        raw_ted=raw_ted,
        pc_precision=pc_precision,
        pc_recall=pc_recall,
        pc_f1=pc_f1,
        pc_tp=pc_correct,
        lar=lar,
        aligned_count=len(mu),
    )


def _compute_nted(gold_map: MindMapData, gen_map: MindMapData) -> tuple[float, float]:
    """
    E: Compute normalized Tree Edit Distance using zss library
    C: 使用 zss 库计算归一化树编辑距离

    E: The ZSS tree is built from the SAME edge source as the other §2 metrics
       (parent_id → links → nested tree via extract_edges). Previously the tree
       was built from parent_id only, which collapsed flat maps (nodes without
       parent_id, structure carried by links/tree) into single-node trees and
       made nTED meaningless. Multiple roots / orphan nodes are wrapped under a
       virtual root so every node enters the tree and the normalizer
       max(|T_g|, |T_s|) stays consistent with the spec.
    C: ZSS 树使用与其余 §2 指标相同的边源构建（parent_id → links → tree，经
       extract_edges 兜底）。此前仅按 parent_id 建树，无 parent_id 的扁平图
       （结构由 links/tree 承载）会退化为单节点树，nTED 失真。多根/孤儿节点
       用虚拟根包裹，保证全部节点入树，归一化分母与规范一致。
    """
    from zss import Node as ZSSNode, simple_distance

    def build_zss_tree(mind_map: MindMapData) -> Optional[ZSSNode]:
        nodes = mind_map.nodes
        edges = extract_edges(nodes, mind_map.links, mind_map.tree)
        parent_map = {c: p for p, c in edges}
        child_ids = set(parent_map.keys())
        roots = [n for n in nodes if str(n.get('id', '')) not in child_ids]
        if not roots:
            return None

        def _add_children(parent_node: ZSSNode, parent_nid: str, visited: Optional[set[str]] = None) -> None:
            # E: In-path guard against cycles (same semantics as compute_depth_map)
            # C: 路径内防环（与 compute_depth_map 的语义一致）
            if visited is None:
                visited = set()
            if parent_nid in visited:
                return
            visited.add(parent_nid)
            children = sorted(
                [n for n in nodes if parent_map.get(str(n.get('id', ''))) == parent_nid],
                key=lambda x: x.get('label', '')
            )
            for child in children:
                child_node = ZSSNode(child.get('label', ''))
                parent_node.addkid(child_node)
                _add_children(child_node, str(child.get('id', '')), visited)

        if len(roots) == 1:
            root = roots[0]
            zss_root = ZSSNode(root.get('label', ''))
            _add_children(zss_root, str(root.get('id', '')))
            return zss_root
        # E: Multiple roots / orphans — wrap in a virtual root so every node enters the tree
        # C: 多根/孤儿节点 — 用虚拟根包裹，保证全部节点入树
        vr = ZSSNode('__virtual_root__')
        for r in roots:
            _add_children(vr, str(r.get('id', '')))
        return vr

    gold_tree = build_zss_tree(gold_map)
    gen_tree = build_zss_tree(gen_map)

    if gold_tree is None or gen_tree is None:
        return 1.0, 1.0  # max distance / 最大距离

    raw_ted = simple_distance(gold_tree, gen_tree)
    max_nodes = max(len(gold_map.nodes), len(gen_map.nodes))
    nted = raw_ted / max_nodes if max_nodes > 0 else 1.0
    # E: Clamp to [0, 1] — zss simple_distance may exceed the node count for
    #    structurally divergent trees, while spec §2.3 defines nTED ∈ [0, 1];
    #    otherwise composite's (1 - nTED) component could go negative.
    # C: 截断到 [0, 1] — zss 的 simple_distance 对结构差异较大的树可能超过节点数，
    #    而规范 §2.3 定义 nTED ∈ [0, 1]；否则 composite 的 (1 - nTED) 分量会变负。
    nted = min(1.0, max(0.0, nted))

    return nted, raw_ted


