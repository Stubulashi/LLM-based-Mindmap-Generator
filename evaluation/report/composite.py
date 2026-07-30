"""
E: Composite Score — §7.2 Composite Score
C: 综合评分公式 — §7.2 Composite Score

Evaluation_Schema.md §7.2
Composite = 0.20*Node-F1 + 0.15*Edge-F1 + 0.10*LabelSim
          + 0.10*EntityRecall + 0.15*(1-nTED) + 0.10*UAS
          + 0.10*PC-F1 + 0.10*QA-Relative
"""
from typing import Optional


def compute_composite_score(
    label_metrics: Optional[dict] = None,
    hierarchy_metrics: Optional[dict] = None,
    qa_metrics: Optional[dict] = None,
) -> tuple[float, dict]:
    """
    E: Compute §7.2 composite score
    C: 计算 §7.2 综合评分

    Returns (score, details): composite score and detail breakdown
    返回 (score, details): 综合分数和明细字典
    """
    weights = {
        'node_f1': 0.20,
        'edge_f1': 0.15,
        'label_sim': 0.10,
        'entity_recall': 0.10,
        'nted_inv': 0.15,      # (1 - nTED)
        'uas': 0.10,
        'pc_f1': 0.10,
        'qa_relative': 0.10,
    }

    components = {}
    total_weight = 0.0

    if label_metrics:
        if 'node_f1' in label_metrics and label_metrics['node_f1'] is not None:
            components['node_f1'] = label_metrics['node_f1']
            total_weight += weights['node_f1']
        if 'label_sim' in label_metrics and label_metrics['label_sim'] is not None:
            components['label_sim'] = label_metrics['label_sim']
            total_weight += weights['label_sim']
        if 'entity_recall' in label_metrics and label_metrics['entity_recall'] is not None:
            components['entity_recall'] = label_metrics['entity_recall']
            total_weight += weights['entity_recall']

    if hierarchy_metrics:
        if 'edge_f1' in hierarchy_metrics and hierarchy_metrics['edge_f1'] is not None:
            components['edge_f1'] = hierarchy_metrics['edge_f1']
            total_weight += weights['edge_f1']
        if 'uas' in hierarchy_metrics and hierarchy_metrics['uas'] is not None:
            components['uas'] = hierarchy_metrics['uas']
            total_weight += weights['uas']
        if 'nted' in hierarchy_metrics and hierarchy_metrics['nted'] is not None:
            components['nted_inv'] = 1.0 - hierarchy_metrics['nted']
            total_weight += weights['nted_inv']
        if 'pc_f1' in hierarchy_metrics and hierarchy_metrics['pc_f1'] is not None:
            components['pc_f1'] = hierarchy_metrics['pc_f1']
            total_weight += weights['pc_f1']

    if qa_metrics:
        if 'qa_retention' in qa_metrics and qa_metrics['qa_retention'] is not None:
            components['qa_relative'] = qa_metrics['qa_retention']
            total_weight += weights['qa_relative']

    # E: Compute weighted composite score / C: 计算加权综合分
    score = 0.0
    detail = {}
    for key, value in components.items():
        w = weights.get(key, 0)
        detail[key] = {
            'value': value,
            'weight': w,
            'weighted': value * w,
        }
        score += value * w

    # E: Normalize (deduct weights of uncomputed metrics) / C: 归一化（扣除未计算指标的权重）
    if total_weight > 0:
        normalized_score = score / total_weight
    else:
        normalized_score = 0.0

    return normalized_score, {
        'composite_score': round(normalized_score, 4),
        'components': detail,
        'total_weight_used': round(total_weight, 2),
    }
