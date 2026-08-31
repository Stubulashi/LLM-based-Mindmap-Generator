"""
E: §1 Node Label Quality Assessment
C: §1 节点标签质量评估 — Node Label Quality Assessment

Evaluation_Schema.md §1.1~1.4
包含 / Includes:
  - 1.1 匈牙利节点对齐 (HungarianAligner, 在 core/aligner.py)
  - 1.2 Node-P / Node-R / Node-F1
  - 1.3 LabelSim (Label Semantic Similarity)
  - 1.4 Entity Recall (核心概念召回率 / Core Concept Recall)
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from evaluation.core.aligner import HungarianAligner, AlignmentResult
from evaluation.core.embedder import compute_similarity_matrix
from evaluation.core.data_loader import MindMapData


@dataclass
class LabelMetrics:
    """E: §1 Label quality evaluation results / C: §1 节点标签质量评估结果"""
    # 1.1 Alignment Info / 对齐信息
    alignment: AlignmentResult

    # 1.2 Node-P/R/F1 / 节点精确率/召回率/F1
    node_precision: float
    node_recall: float
    node_f1: float
    tp: int
    fp: int
    fn: int

    # 1.3 LabelSim / 标签语义相似度
    label_sim: float

    # 1.4 Entity Recall / 实体召回率
    entity_recall: float = 0.0
    entity_hits: list[str] = field(default_factory=list)
    entity_misses: list[str] = field(default_factory=list)
    entity_total: int = 0

    def to_dict(self) -> dict:
        # E: node_p/node_r are the keys consumed by THRESHOLD_MAP and the report
        #    renderer; node_precision/node_recall are kept for backward compatibility
        #    with persisted eval_result.json files.
        # C: node_p/node_r 是 THRESHOLD_MAP 与报告渲染器使用的键；
        #    node_precision/node_recall 保留以兼容已持久化的 eval_result.json。
        return {
            'node_precision': round(self.node_precision, 4),
            'node_recall': round(self.node_recall, 4),
            'node_p': round(self.node_precision, 4),
            'node_r': round(self.node_recall, 4),
            'node_f1': round(self.node_f1, 4),
            'label_sim': round(self.label_sim, 4),
            'entity_recall': round(self.entity_recall, 4),
            'tp': self.tp,
            'fp': self.fp,
            'fn': self.fn,
            'entity_hits': self.entity_hits,
            'entity_misses': self.entity_misses,
            'entity_total': self.entity_total,
            'matches': self.alignment.node_matches_table(),
            'threshold': self.alignment.threshold,
            'model_name': self.alignment.model_name,
            'gold_count': len(self.alignment.gold_labels),
            'gen_count': len(self.alignment.gen_labels),
        }


def evaluate_label_quality(
    gold_map: MindMapData,
    gen_map: MindMapData,
    aligner: HungarianAligner,
    essential_concepts: Optional[list[str]] = None,
    alignment: Optional[AlignmentResult] = None,
) -> LabelMetrics:
    """
    E: Compute all §1 label quality metrics.
        All metrics share the same AlignmentResult.
    C: 执行 §1 所有节点标签质量指标的完整计算。
        所有指标复用同一个 AlignmentResult。

    参数 / Args:
        gold_map: 金标准导图 / Gold standard mind map
        gen_map: 生成导图 / Generated mind map
        aligner: 匈牙利匹配器 / Hungarian aligner
        essential_concepts: 核心概念集合列表（可选，用于 §1.4 Entity Recall）
            可以从标准化 Es.json 文件加载（参见 evaluation/data/concepts/ 目录），
            也可以从交互式 CLI 输入逗号分隔的字符串生成。
            如果为 None 或空列表，框架自动从金标准导图的节点 label 中提取作为后备。
            参考 / Reference: Evaluation_Schema.md §1.4
            / Essential concepts list (optional, for §1.4 Entity Recall)
            Can be loaded from a standardized Es.json file (see evaluation/data/concepts/),
            or generated from comma-separated input in the interactive CLI.
            If None or empty, the framework auto-extracts from gold standard node labels.
        alignment: 已计算的对齐结果（可选）— 传入时跳过内部重复对齐，
            兑现规范 §1.1“所有边级指标共享同一 M_τ”的定位，避免重复 embedding。
            / Optional pre-computed alignment — skips internal realignment so label
            and hierarchy metrics share the same M_τ (spec §1.1).

    返回 / Returns:
        LabelMetrics: 包含所有 §1 指标
    """
    # --- 1.1 Hungarian Node Alignment / 匈牙利节点对齐 ---
    if alignment is None:
        alignment = aligner.align(gold_map.nodes, gen_map.nodes)
    M_tau = alignment.filtered_matches

    # --- 1.2 Node-P/R/F1 / 节点精确率/召回率/F1 ---
    tp = alignment.tp
    fp = alignment.fp
    fn = alignment.fn
    node_p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    node_r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    node_f1 = (2 * node_p * node_r / (node_p + node_r)
               if (node_p + node_r) > 0 else 0.0)

    # --- 1.3 LabelSim / 标签语义相似度 ---
    if len(M_tau) > 0:
        label_sim = sum(sim for _, _, sim in M_tau) / len(M_tau)
    else:
        label_sim = 0.0

    # --- 1.4 Entity Recall / 实体召回率 ---
    entity_recall = 0.0
    hits = []
    misses = []
    total_concepts = 0

    # E: Use user-provided essential concept list / C: 使用用户提供的核心概念列表
    if essential_concepts:
        concepts = essential_concepts
    else:
        # E: Auto-extract from gold node labels / C: 自动从金标准节点 label 提取
        concepts = list(set(gold_map.get_labels()))

    if concepts:
        total_concepts = len(concepts)
        gen_texts = gen_map.get_all_texts()
        if gen_texts:
            S = compute_similarity_matrix(concepts, gen_texts, aligner.model_name)
            max_sim = S.max(axis=1)
            for i, concept in enumerate(concepts):
                if max_sim[i] >= aligner.threshold:
                    hits.append(concept)
                else:
                    misses.append(concept)
        else:
            misses = list(concepts)
        entity_recall = len(hits) / total_concepts if total_concepts > 0 else 0.0

    return LabelMetrics(
        alignment=alignment,
        node_precision=node_p,
        node_recall=node_r,
        node_f1=node_f1,
        tp=tp, fp=fp, fn=fn,
        label_sim=label_sim,
        entity_recall=entity_recall,
        entity_hits=hits,
        entity_misses=misses,
        entity_total=total_concepts,
    )
