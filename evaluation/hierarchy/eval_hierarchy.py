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
    # E: Root node / C: 根节点
    gold_root = None
    for n in gold_map.nodes:
        pid = n.get('parent_id')
        if pid is None:
            gold_root = n['id']
            break
    gen_root = None
    for n in gen_map.nodes:
        pid = n.get('parent_id')
        if pid is None:
            gen_root = n['id']
            break

    uas_correct = 0
    uas_total = len(mu)
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

    uas = uas_correct / uas_total if uas_total > 0 else 1.0

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
        nted = None
    except Exception:
        nted = None

    # =========================================================
    # 2.4 PC-F1 (Parent-Child F1) / 父子 F1
    # =========================================================
    # E: Schema §2.4 — Check parent and child labels independently
    # C: Schema §2.4 — 分别检查父标签和子标签是否均语义匹配
    gold_pairs = extract_parent_child_pairs(gold_map.nodes)
    gen_pairs = extract_parent_child_pairs(gen_map.nodes)

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

        # E: Hit if parent_sim >= tau AND child_sim >= tau
        # C: 判定命中 — 父相似度 >= τ AND 子相似度 >= τ
        for i, (g_p, g_c) in enumerate(gold_p_labels):
            for j, (gen_p, gen_c) in enumerate(gen_p_labels):
                if parent_S[i, j] >= similarity_threshold and child_S[i, j] >= similarity_threshold:
                    pc_correct += 1
                    break

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
    for gold_id, gen_id in mu.items():
        if gold_depths.get(gold_id) == gen_depths.get(gen_id):
            lar_correct += 1

    lar = lar_correct / lar_total if lar_total > 0 else 1.0

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
    )


def _compute_nted(gold_map: MindMapData, gen_map: MindMapData) -> tuple[float, float]:
    """
    E: Compute normalized Tree Edit Distance using zss library
    C: 使用 zss 库计算归一化树编辑距离
    """
    from zss import Node as ZSSNode, simple_distance

    def build_zss_tree(nodes: list[dict], parent_id: Optional[str] = None) -> Optional[ZSSNode]:
        children = [n for n in nodes if n.get('parent_id') == parent_id]
        if not children and parent_id is not None:
            return None
        if parent_id is None:
            # root / 根节点
            root_nodes = [n for n in nodes if n.get('parent_id') is None]
            if not root_nodes:
                return None
            root = root_nodes[0]
            zss_root = ZSSNode(root.get('label', ''))
            _add_zss_children(zss_root, root['id'], nodes)
            return zss_root
        return None

    def _add_zss_children(parent_node: ZSSNode, parent_nid: str, nodes: list[dict]):
        children = sorted(
            [n for n in nodes if n.get('parent_id') == parent_nid],
            key=lambda x: x.get('label', '')
        )
        for child in children:
            child_node = ZSSNode(child.get('label', ''))
            parent_node.addkid(child_node)
            _add_zss_children(child_node, child['id'], nodes)

    gold_tree = build_zss_tree(gold_map.nodes, None)
    gen_tree = build_zss_tree(gen_map.nodes, None)

    if gold_tree is None or gen_tree is None:
        return 1.0, 1.0  # max distance / 最大距离

    raw_ted = simple_distance(gold_tree, gen_tree)
    max_nodes = max(len(gold_map.nodes), len(gen_map.nodes))
    nted = raw_ted / max_nodes if max_nodes > 0 else 1.0

    return nted, raw_ted


