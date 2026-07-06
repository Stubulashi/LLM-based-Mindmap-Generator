# Human Scoring Data Usage Guide

> zh: 人工评分数据使用指南

## Purpose

> zh: 用途

This guide explains how to create and use human scoring datasets (§6) for automated-human correlation analysis. The goal is to validate whether automated metrics can substitute human evaluation. A Pearson correlation coefficient of **r >= 0.70** is the minimum threshold for automated evaluation validity.

> zh: 本指南说明如何创建和使用人工评分数据集（§6）用于自动化-人工相关性分析。目的是验证自动化指标是否能够替代或近似人工评估，Pearson r >= 0.70 是自动化评估有效性的最低要求。

### When to Collect Human Scores

> zh: 何时收集人工评分

- Before publishing automated evaluation results, to demonstrate alignment with human judgment.
  > zh: 在发布自动化评估结果之前，证明与人工判断一致。
- When developing new evaluation metrics, to validate their effectiveness.
  > zh: 开发新评估指标时，验证其有效性。
- For periodic calibration of automated evaluation pipelines.
  > zh: 定期校准自动化评估管线时。

---

## Scoring Rubric

> zh: 评分量表

A 5-point Likert scale is used: **1 = Very Poor**, **5 = Excellent**.

> zh: 采用 5 点 Likert 量表（1=非常差，5=非常好）。

### Evaluation Dimensions

> zh: 评估维度

| Dimension | Evaluation Question | Anchor (1) | Anchor (5) |
|-----------|-------------------|------------|------------|
| readability | Are the text labels clear and easy to understand? (zh: 文字标签是否清晰易懂？) | Obscure / Hard to understand (zh: 晦涩难懂) | Crystal clear / Self-explanatory (zh: 一目了然) |
| hierarchy_intuitiveness | Do parent-child relationships feel intuitive? (zh: 父子从属关系是否符合直觉？) | Many counter-intuitive relations (zh: 大量反直觉) | Fully aligned with cognition (zh: 完全符合认知) |
| information_density | Does the map efficiently convey core content? (zh: 是否高效传达了核心内容？) | Sparse / Too little information (zh: 信息稀疏) | Optimal density (zh: 密度适中) |
| pedagogical_utility | Would you use this as a study reference? (zh: 作为复习资料的使用意愿？) | Would not use (zh: 不会使用) | Very willing to use (zh: 非常愿意) |

### Detailed Scoring Guidelines

> zh: 详细评分指南

| Score | Meaning | When to Use |
|-------|---------|-------------|
| 1 | Very Poor | The dimension is completely unsatisfactory; major improvements required (zh: 完全不合格，需大幅改进) |
| 2 | Poor | Below average; noticeable issues exist (zh: 低于平均水平，存在明显问题) |
| 3 | Average | Acceptable quality; neither outstanding nor problematic (zh: 可接受，既不突出也无大问题) |
| 4 | Good | Above average; minor improvements possible (zh: 高于平均，略有改进空间) |
| 5 | Excellent | Exceptional quality; meets all expectations (zh: 卓越，满足所有期望) |

---

## Sample Size Requirements

> zh: 样本规模要求

- **Minimum 30 mind map samples**, covering approximately 1/3 excellent, 1/3 good, and 1/3 needs-improvement.
  > zh: 至少 30 个导图样本，覆盖优秀、良好、需改进各约 1/3。
- **At least 5 raters per sample**, including at least 2 target users.
  > zh: 每位评估者 >= 5 人，需包含至少 2 名目标用户。
- **Inter-rater reliability ICC(3,k) >= 0.70** to ensure consistent scoring.
  > zh: 评分者间信度 ICC(3,k) >= 0.70，确保评分一致性。

### Why These Requirements?

> zh: 为什么有这些要求

- **30 samples:** Provides sufficient statistical power for Pearson correlation analysis (zh: 为 Pearson 相关性分析提供足够统计功效)
- **5 raters:** Balances cost and reliability; fewer raters increase noise (zh: 在成本和可靠性之间取得平衡)
- **ICC >= 0.70:** Industry standard for "good" inter-rater reliability (zh: 评分者间信度的行业"良好"标准)

---

## Data Format

> zh: 数据格式

```json
{
  "samples": [
    {
      "sample_id": "map_01",
      "readability": 4.2,
      "hierarchy_intuitiveness": 4.0,
      "information_density": 3.8,
      "pedagogical_utility": 4.0,
      "raters": 3
    }
  ]
}
```

### Field Definitions

> zh: 字段定义

| Field | Type | Description |
|-------|------|-------------|
| sample_id | string | Sample unique identifier (zh: 样本唯一标识) |
| readability | float | Readability score (1.0-5.0) (zh: 可读性评分) |
| hierarchy_intuitiveness | float | Hierarchy intuitiveness score (1.0-5.0) (zh: 层级直觉性评分) |
| information_density | float | Information density score (1.0-5.0) (zh: 信息密度评分) |
| pedagogical_utility | float | Pedagogical utility score (1.0-5.0) (zh: 教学实用性评分) |
| raters | int | Number of raters who scored this sample (zh: 参与评分的评估者人数) |

> **Note:** Each dimension score should be the **mean** across all raters for that sample. Store individual rater scores separately for ICC calculation.
> zh: 注意：每个维度评分应为该样本所有评估者的**平均分**。单个评估者的原始评分应单独存储以用于 ICC 计算。

---

## Storage Location

> zh: 存放位置

Files should be placed in the `evaluation/data/human_scores/` directory with the naming format `{prefix}_human_scores.json`.

> zh: 文件应放置在 evaluation/data/human_scores/ 目录下，命名格式为 `{prefix}_human_scores.json`。

---

## How to Use / 使用方法

> zh: 使用方法

Trigger this evaluation by selecting the `human_corr` option in the interactive CLI. The system will load human score data from `evaluation/data/human_scores/` and compute correlations with automated metrics.

> zh: 通过交互式 CLI 的 human_corr 选项触发评估，系统将从 evaluation/data/human_scores/ 加载人工评分数据并计算与自动化指标的相关性。

## Purpose / 目的

> zh: 目的

Validates whether automated evaluation metrics are consistent with human judgment, with a target of Pearson correlation coefficient r ≥ 0.70.

> zh: 验证自动化评估指标是否与人工评分一致，目标 Pearson 相关系数 r ≥ 0.70。

## Principle / 原理

> zh: 原理

Compute Pearson and Spearman correlation coefficients between automated metrics (e.g., Node-F1) and 5-point Likert human scores across multiple evaluation dimensions.

> zh: 计算自动化指标（如 Node-F1 等）与 5 点 Likert 人工评分的 Pearson/Spearman 相关性。

## Limitations / 局限性

> zh: 局限性

- **Large sample requirement:** Requires a minimum of 30 samples for statistically meaningful correlation analysis. (zh: 需要至少 30 个样本才能获得有统计意义的相关性分析)
- **Rater consistency:** Requires high inter-rater reliability (ICC ≥ 0.70), which demands careful rater training. (zh: 评分者一致性要求高（ICC ≥ 0.70），需要对评分者进行认真培训)
- **Coverage gaps:** Human scores cannot cover all evaluation dimensions (e.g., real-time latency), limiting validation scope. (zh: 无法覆盖所有评估维度，如实时延迟等指标无法通过人工评分验证)

---

*Document Version: v1.0 | Created: 2026-06-29*
