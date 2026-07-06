"""
E: §6 Human Evaluation & Automated Alignment
C: §6 人工评估与自动化对齐

Evaluation_Schema.md §6.1~6.2
包含 / Includes:
  - 6.1 人工评分维度与量表 / Human Scoring Dimensions & Rubric
  - 6.2 自动化-人工相关性分析 / Automated-Human Correlation Analysis (Pearson r / Spearman ρ)
"""
from dataclasses import dataclass, field
from typing import Optional

from evaluation.core.thresholds import PEARSON_R, Grade


def _is_constant(arr: list) -> bool:
    """Check if array is constant (all values are the same)."""
    return len(set(arr)) <= 1


@dataclass
class HumanCorrelationMetrics:
    """E: Human-automation correlation results / C: 人工-自动化相关性结果"""
    num_samples: int = 0
    num_raters: int = 0

    # E: Pearson r (Node-F1 vs Readability) / C: Pearson r（节点F1 vs 可读性）
    node_f1_readability_r: float = 0.0
    node_f1_readability_p: float = 1.0
    # E: Spearman ρ (Node-F1 vs Readability) / C: Spearman ρ（节点F1 vs 可读性）
    node_f1_readability_rho: float = 0.0

    # E: Edge-F1 vs Hierarchy Intuitiveness / C: 边F1 vs 层级直观性
    edge_f1_hierarchy_r: float = 0.0
    edge_f1_hierarchy_rho: float = 0.0

    # E: UAS vs Hierarchy Intuitiveness / C: UAS vs 层级直观性
    uas_hierarchy_r: float = 0.0

    # E: LabelSim vs Readability / C: 标签相似度 vs 可读性
    label_sim_readability_r: float = 0.0

    # E: Inter-rater reliability / C: 评定者间信度
    icc: float = 0.0
    kendall_w: float = 0.0

    # E: Verdict / C: 裁定
    overall_verdict: str = "N/A"

    def to_dict(self) -> dict:
        return {
            'num_samples': self.num_samples,
            'num_raters': self.num_raters,
            'node_f1_vs_readability_pearson_r': round(self.node_f1_readability_r, 4),
            'node_f1_vs_readability_spearman_rho': round(self.node_f1_readability_rho, 4),
            'edge_f1_vs_hierarchy_pearson_r': round(self.edge_f1_hierarchy_r, 4),
            'uas_vs_hierarchy_pearson_r': round(self.uas_hierarchy_r, 4),
            'label_sim_vs_readability_pearson_r': round(self.label_sim_readability_r, 4),
            'overall_verdict': self.overall_verdict,
        }


def evaluate_human_correlation(
    automated_scores: Optional[list[dict]] = None,
    human_scores: Optional[list[dict]] = None,
) -> HumanCorrelationMetrics:
    """
    E: Compute correlation between automated metrics and human scores
    C: 计算自动化指标与人工评分的相关性

    Reference / 依据: Evaluation_Schema.md §6.2, §8.4
    Requires scipy.stats.pearsonr / spearmanr, minimum 30 samples
    使用 scipy.stats.pearsonr / spearmanr，需要至少 30 个样本

    Args / 参数:
        automated_scores: [{node_f1, edge_f1, uas, label_sim, ...}, ...]
        human_scores: [{readability, hierarchy_intuitiveness, ...}, ...]

    Returns / 返回:
        HumanCorrelationMetrics
    """
    if not automated_scores or not human_scores:
        return HumanCorrelationMetrics(overall_verdict="Insufficient data / 数据不足")

    if len(automated_scores) != len(human_scores):
        return HumanCorrelationMetrics(overall_verdict="Sample count mismatch / 样本数不匹配")

    n = len(automated_scores)

    # E: Extract paired metrics / C: 提取配对指标
    auto_node_f1 = [s.get('node_f1', 0.0) for s in automated_scores]
    auto_edge_f1 = [s.get('edge_f1', 0.0) for s in automated_scores]
    auto_uas = [s.get('uas', 0.0) for s in automated_scores]
    auto_label_sim = [s.get('label_sim', 0.0) for s in automated_scores]

    human_readability = [s.get('readability', 0.0) for s in human_scores]
    human_hierarchy = [s.get('hierarchy_intuitiveness', 0.0) for s in human_scores]
    human_information = [s.get('information_density', 0.0) for s in human_scores]

    # E: Compute correlations / C: 计算相关性
    try:
        from scipy.stats import pearsonr, spearmanr
    except ImportError:
        return HumanCorrelationMetrics(
            num_samples=n,
            overall_verdict="scipy not installed / scipy 未安装",
        )

    # Node-F1 vs Readability
    if _is_constant(auto_node_f1) or _is_constant(human_readability):
        r_nf1, p_nf1 = 0.0, 1.0
        rho_nf1 = 0.0
        print("    [Info] auto_node_f1 or human_readability is constant, skipped correlation")
    else:
        r_nf1, p_nf1 = pearsonr(auto_node_f1, human_readability)
        rho_nf1, _ = spearmanr(auto_node_f1, human_readability)

    # Edge-F1 vs Hierarchy Intuitiveness
    if _is_constant(auto_edge_f1) or _is_constant(human_hierarchy):
        r_ef1 = 0.0
        rho_ef1 = 0.0
        print("    [Info] auto_edge_f1 or human_hierarchy is constant, skipped correlation")
    else:
        r_ef1, _ = pearsonr(auto_edge_f1, human_hierarchy)
        rho_ef1, _ = spearmanr(auto_edge_f1, human_hierarchy)

    # UAS vs Hierarchy Intuitiveness
    if _is_constant(auto_uas) or _is_constant(human_hierarchy):
        r_uas = 0.0
        print("    [Info] auto_uas or human_hierarchy is constant, skipped correlation")
    else:
        r_uas, _ = pearsonr(auto_uas, human_hierarchy)

    # LabelSim vs Readability
    if _is_constant(auto_label_sim) or _is_constant(human_readability):
        r_ls = 0.0
        print("    [Info] auto_label_sim or human_readability is constant, skipped correlation")
    else:
        r_ls, _ = pearsonr(auto_label_sim, human_readability)

    # E: Compute inter-rater reliability / C: 计算评分者间信度
    icc_val = 0.0
    kendall_w_val = 0.0
    num_raters = 0
    if human_scores and 'raters' in human_scores[0] if human_scores else False:
        # Placeholder for actual ICC/Kendall W computation
        pass

    # E: Verdict / C: 判定
    band = PEARSON_R
    grade = band.grade(r_nf1)
    if grade in (Grade.EXCELLENT, Grade.GOOD):
        verdict = f"Valid / 有效 (Pearson r={r_nf1:.3f}, {grade.value})"
    else:
        verdict = f"Needs Improvement / 需改进 (Pearson r={r_nf1:.3f}, {grade.value})"

    return HumanCorrelationMetrics(
        num_samples=n,
        num_raters=num_raters,
        node_f1_readability_r=r_nf1,
        node_f1_readability_p=p_nf1,
        node_f1_readability_rho=rho_nf1,
        edge_f1_hierarchy_r=r_ef1,
        edge_f1_hierarchy_rho=rho_ef1,
        uas_hierarchy_r=r_uas,
        label_sim_readability_r=r_ls,
        icc=icc_val,
        kendall_w=kendall_w_val,
        overall_verdict=verdict,
    )
