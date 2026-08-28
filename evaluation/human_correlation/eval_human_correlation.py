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


def _compute_inter_rater_reliability(human_scores: list[dict]) -> tuple[float, float, int]:
    """E: Compute ICC(3,k) and Kendall's W from per-sample 'raters' maps.
    C: 从每个样本的 'raters' 映射计算 ICC(3,k) 与 Kendall's W。

    Data format / 数据格式:
        human_scores: [{..., 'raters': {'A': 4, 'B': 5}}, ...]

    Returns (icc, kendall_w, num_raters); (0.0, 0.0, 0) when insufficient data.
    返回 (icc, kendall_w, num_raters)；数据不足时返回 (0.0, 0.0, 0)。"""
    samples = [s.get('raters') for s in human_scores if isinstance(s.get('raters'), dict)]
    if len(samples) < 3:
        return 0.0, 0.0, 0

    rater_ids = sorted({rid for s in samples for rid in s})
    if len(rater_ids) < 2:
        return 0.0, 0.0, 0

    # E: Build sample x rater matrix (listwise deletion of incomplete rows)
    # C: 构建 样本 x 评分者 矩阵（listwise 删除不完整行）
    matrix = []
    for s in samples:
        row = [s.get(rid) for rid in rater_ids]
        if any(v is None for v in row):
            continue
        matrix.append(row)
    n = len(matrix)
    k = len(rater_ids)
    if n < 3 or k < 2:
        return 0.0, 0.0, 0

    # E: ICC(3,k) — two-way mixed, average measures, absolute agreement
    # C: ICC(3,k) — 双因素混合模型、均值度量、绝对一致性
    row_means = [sum(r) / k for r in matrix]
    col_means = [sum(matrix[i][j] for i in range(n)) / n for j in range(k)]
    grand = sum(row_means) / n
    ssb = sum((rm - grand) ** 2 for rm in row_means) * k
    ssj = sum((cm - grand) ** 2 for cm in col_means) * n
    sse = sum(
        (matrix[i][j] - row_means[i] - col_means[j] + grand) ** 2
        for i in range(n) for j in range(k)
    )
    msb = ssb / (n - 1)
    msj = ssj / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    denom = msb + (msj - mse) / n
    icc = (msb - mse) / denom if denom else 0.0
    icc = max(-1.0, min(1.0, icc))

    # E: Kendall's W (with tie correction) / C: Kendall's W（含 tie 修正）
    def _rank_with_ties(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            avg_rank = (i + j) / 2 + 1
            for idx in range(i, j + 1):
                ranks[order[idx]] = avg_rank
            i = j + 1
        return ranks

    ranks_by_rater = [_rank_with_ties([matrix[i][j] for i in range(n)]) for j in range(k)]
    r_sums = [sum(ranks_by_rater[j][i] for j in range(k)) for i in range(n)]
    mean_r = sum(r_sums) / n
    s = sum((ri - mean_r) ** 2 for ri in r_sums)

    tie_correction = 0.0
    for j in range(k):
        col = sorted(matrix[i][j] for i in range(n))
        i = 0
        while i < n:
            jj = i
            while jj + 1 < n and col[jj + 1] == col[i]:
                jj += 1
            t = jj - i + 1
            if t > 1:
                tie_correction += t ** 3 - t
            i = jj + 1
    denom_w = k ** 2 * (n ** 3 - n) - k * tie_correction
    kendall_w = (12 * s / denom_w) if denom_w else 0.0
    kendall_w = max(0.0, min(1.0, kendall_w))

    return icc, kendall_w, k


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
            'icc': round(self.icc, 4),
            'kendall_w': round(self.kendall_w, 4),
            'overall_verdict': self.overall_verdict,
        }


def evaluate_human_scores(samples: Optional[list[dict]] = None) -> dict:
    """
    E: Lightweight aggregation of interactive human scores (1-10 dual scoring).
        Unlike the correlation analysis above, this feeds the composite score as a
        §6 human compensation component (normalized to [0, 1]) that offsets the
        reduced §2 Hierarchy Accuracy weight, guarding against hierarchy
        False Negatives dominating the final total.
    C: 交互式人类评分（1-10 双评分）的轻量聚合。
        与上述相关性分析不同，本结果作为 §6 人工补偿分量（归一化到 [0,1]）
        计入综合评分：当 §2 层级结构正确率权重下调后，用人工评分补偿其
        评分鲁棒性，防止层级指标 False Negative 主导最终总分。

    Args / 参数:
        samples: [{audio, gen_score, human_score, gold_source}, ...]

    Returns / 返回:
        {num_samples, gen_mean, human_mean, overall_mean, overall_normalized}
    """
    from evaluation.human_correlation.interactive_scorer import aggregate_human_scores
    return aggregate_human_scores(samples or [])


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
    if human_scores and isinstance(human_scores[0].get('raters'), dict):
        icc_val, kendall_w_val, num_raters = _compute_inter_rater_reliability(human_scores)

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
