"""
E: Composite Score — §7.2 Composite Score (refactored weights)
C: 综合评分公式 — §7.2 Composite Score（权重重构）

Evaluation_Schema.md §7.2 (refactored / 重构后)
Composite = 0.20*Node-F1 + 0.08*Edge-F1 + 0.10*LabelSim
          + 0.10*EntityRecall + 0.08*(1-nTED) + 0.07*UAS
          + 0.07*PC-F1 + 0.10*QA-Score + 0.20*Human-Score

权重设计说明 / Weight Rationale:
- §2 层级结构正确率（Edge-F1 / nTED / UAS / PC-F1）权重由 0.50 降至 0.30，
  以降低层级指标 False Negative（误判失败）对最终总分的误伤；
- §6 人工评分（Human-Score，权重 0.20）作为针对层级结构的补偿机制，
  承接其释放的 0.20 权重，提升最终评分的鲁棒性；
- §3 QA 以重构后的逐题 1-5 评分归一化分量（qa_score）取代旧 qa_relative。
"""
from typing import Optional


def compute_composite_score(
    label_metrics: Optional[dict] = None,
    hierarchy_metrics: Optional[dict] = None,
    qa_metrics: Optional[dict] = None,
    human_metrics: Optional[dict] = None,
    custom_weights: Optional[dict] = None,
) -> tuple[float, dict]:
    """
    E: Compute §7.2 composite score
    C: 计算 §7.2 综合评分

    E: custom_weights — optional weight overrides (e.g. {'human_score': 0.30})
        only affects provided keys; unspecified keys keep defaults.
    C: custom_weights — 可选权重覆盖（如 {'human_score': 0.30}），
        仅覆盖传入的键，未指定的键保持默认权重。

    E: human_metrics — §6 interactive human scores
        {num_samples, gen_mean, human_mean, overall_mean, overall_normalized};
        only counted when num_samples > 0 (human compensation component).
    C: human_metrics — §6 交互式人工评分结果；
        仅在 num_samples > 0 时计入（人工补偿分量）。

    Returns (score, details): composite score and detail breakdown
    返回 (score, details): 综合分数和明细字典
    """
    weights = {
        'node_f1': 0.20,
        'edge_f1': 0.08,
        'label_sim': 0.10,
        'entity_recall': 0.10,
        'nted_inv': 0.08,      # (1 - nTED)
        'uas': 0.07,
        'pc_f1': 0.07,
        'qa_score': 0.10,
        'human_score': 0.20,
    }
    if custom_weights:
        weights.update(custom_weights)

    components: dict[str, float] = {}
    total_weight = 0.0

    if label_metrics:
        for key in ('node_f1', 'label_sim', 'entity_recall'):
            if key in label_metrics and label_metrics[key] is not None:
                components[key] = label_metrics[key]
                total_weight += weights[key]

    if hierarchy_metrics:
        if 'edge_f1' in hierarchy_metrics and hierarchy_metrics['edge_f1'] is not None:
            components['edge_f1'] = hierarchy_metrics['edge_f1']
            total_weight += weights['edge_f1']
        if 'nted' in hierarchy_metrics and hierarchy_metrics['nted'] is not None:
            components['nted_inv'] = 1.0 - hierarchy_metrics['nted']
            total_weight += weights['nted_inv']
        if 'pc_f1' in hierarchy_metrics and hierarchy_metrics['pc_f1'] is not None:
            components['pc_f1'] = hierarchy_metrics['pc_f1']
            total_weight += weights['pc_f1']
        if 'uas' in hierarchy_metrics and hierarchy_metrics['uas'] is not None:
            components['uas'] = hierarchy_metrics['uas']
            total_weight += weights['uas']

    if qa_metrics:
        # E: New refactored QA score (normalized 1-5 grading) / C: 新重构 QA 评分
        if qa_metrics.get('num_questions', 0) > 0 and qa_metrics.get('qa_score') is not None:
            components['qa_score'] = qa_metrics['qa_score']
            total_weight += weights['qa_score']
        # E: Legacy fallback for old eval_result.json (qa_retention) / C: 旧结果兼容
        elif 'qa_retention' in qa_metrics and qa_metrics['qa_retention'] is not None:
            components['qa_score'] = qa_metrics['qa_retention']
            total_weight += weights['qa_score']

    if human_metrics:
        # E: §6 human compensation — counts only when samples exist / C: 仅在有样本时计入
        if human_metrics.get('num_samples', 0) > 0 and human_metrics.get('overall_normalized') is not None:
            components['human_score'] = human_metrics['overall_normalized']
            total_weight += weights['human_score']

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
