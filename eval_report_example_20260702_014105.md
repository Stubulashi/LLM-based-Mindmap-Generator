# Mind Map Generation Quality Report
# 思维导图生成质量报告
# (示例演示 / Example Demo)


**Date / 日期**: 2026-07-02 01:41:05
**Pipeline Config / 管线配置**: embedding=paraphrase-multilingual-MiniLM-L12-v2, threshold=0.7 (示例演示 / Example Demo)
**Embedding Model**: paraphrase-multilingual-MiniLM-L12-v2
**Threshold τ**: 0.7
**Gold Nodes / 金标准节点数**: 11
**Generated Nodes / 生成节点数**: 11

---
## Summary / 摘要

| **example** 维度 / Dimension | **example** 核心指标 / Metric | **example** 值 / Value | **example** 评级 / Grade |
| **example** --- | **example** --- | **example** --- | **example** --- |
| **example** 节点标签 / Node Label | **example** Node-F1 | **example** 0.273 | **example** 需改进 / Needs Improvement |
| **example** 层级结构 / Hierarchy | **example** Edge-F1 | **example** 0.000 | **example** 需改进 / Needs Improvement |
| **example** 层级结构 / Hierarchy | **example** UAS | **example** 0.000 | **example** 需改进 / Needs Improvement |
| **example** 层级结构 / Hierarchy | **example** nTED | **example** 0.727 | **example** 需改进 / Needs Improvement |

---
## 1. Node Label Quality / 节点标签质量

| **example** Metric / 指标 | **example** Value / 值 | **example** Threshold / 阈值 | **example** Grade / 评级 | **example** Status / 状态 |
| **example** --- | **example** --- | **example** --- | **example** --- | **example** --- |
| **example** Node-F1 | **example** 0.273 | **example** ≥ 0.85 | **example** 需改进 / Needs Improvement | **example** **FAIL** |
| **example** LabelSim | **example** 1.000 | **example** ≥ 0.85 | **example** 优秀 / Excellent | **example** **PASS** |
| **example** Entity Recall | **example** 0.360 | **example** ≥ 0.90 | **example** 需改进 / Needs Improvement | **example** **FAIL** |

**匈牙利匹配详情 / Hungarian Alignment Details**:
- 金标准节点数 / Gold nodes: 11
- 生成节点数 / Gen nodes: 11
- 高质量匹配对 (τ=0.7) / High-quality matches: 3
- 误报 FP (未匹配生成节点): 8
- 漏报 FN (未匹配金标准节点): 8

**匹配明细 / Match Details**:

| **example** 金标准标签 / Gold Label | **example** 生成标签 / Gen Label | **example** 相似度 / Similarity |
| **example** --- | **example** --- | **example** --- |
| **example** 支持向量机 | **example** 支持向量机 | **example** 1.0000 |
| **example** K-Means聚类 | **example** K-Means聚类 | **example** 1.0000 |
| **example** Q-Learning | **example** Q-Learning | **example** 1.0000 |

**Entity Recall 详情**:
- 核心概念总数: 25
- 命中: 9
- 遗漏: 16
- 遗漏概念: 机器学习基础, 机器学习, Machine Learning, 监督学习, Supervised Learning, 无监督学习, Unsupervised Learning, 线性回归, Linear Regression, SVM, Support Vector Machine, Decision Tree, 主成分分析, PCA, Principal Component Analysis, Policy Gradient

---
## 2. Hierarchy Accuracy / 层级结构正确率

| **example** Metric / 指标 | **example** Value / 值 | **example** Threshold / 阈值 | **example** Grade / 评级 | **example** Status / 状态 |
| **example** --- | **example** --- | **example** --- | **example** --- | **example** --- |
| **example** Edge-F1 | **example** 0.000 | **example** ≥ 0.80 | **example** 需改进 / Needs Improvement | **example** **FAIL** |
| **example** Edge-P | **example** 0.000 | **example** — | **example** — | **example** — |
| **example** Edge-R | **example** 0.000 | **example** — | **example** — | **example** — |
| **example** UAS | **example** 0.000 | **example** ≥ 0.85 | **example** 需改进 / Needs Improvement | **example** **FAIL** |
| **example** PC-F1 | **example** 0.000 | **example** ≥ 0.75 | **example** 需改进 / Needs Improvement | **example** **FAIL** |
| **example** LAR | **example** 1.000 | **example** ≥ 0.70 | **example** 优秀 / Excellent | **example** **PASS** |
| **example** nTED | **example** 0.727 | **example** ≤ 0.25 | **example** 需改进 / Needs Improvement | **example** **FAIL** |
| **example** Raw TED | **example** 8.00 | **example** — | **example** — | **example** — |

**边级指标详情 / Edge Metric Details**:
- 金标准边数 / Gold edges: 10
- 生成边数 / Gen edges: 10
- 正确边 TP: 0
- 多余边 FP: 10
- 缺失边 FN: 10

---
## 3. Downstream QA / 下游问答测试

| **example** Group / 组别 | **example** Accuracy / 准确率 | **example** Token Cost / Token消耗 | **example** Relative / 相对值 |
| **example** --- | **example** --- | **example** --- | **example** --- |
| **example** Control (Full) / 对照组 | **example** 0.000 | **example** — | **example** baseline |
| **example** Experiment (Map) / 实验组 | **example** 0.000 | **example** — | **example** 0.000 |

**QA Retention**: 0.000
**Token Reduction**: 0.0%

---
## 4. Efficiency & STT / 效率与语音转录

| **example** Metric / 指标 | **example** Value / 值 | **example** Threshold / 阈值 | **example** Status / 状态 |
| **example** --- | **example** --- | **example** --- | **example** --- |
| **example** T_total P50 | **example** 27.400 | **example** — | **example** — |
| **example** WER | **example** 0.000 | **example** ≤ 0.15 | **example** **PASS** |
| **example** KTRR | **example** 0.000 | **example** ≥ 0.90 | **example** **FAIL** |

---
## 5. Multilingual & Robustness / 多语言与鲁棒性

| **example** Metric / 指标 | **example** CN | **example** EN | **example** Mixed / 混合 | **example** Max Δ |
| **example** --- | **example** --- | **example** --- | **example** --- | **example** --- |
| **example** Entity Recall | **example** 0.912 | **example** 0.872 | **example** 1.483 | **example** 0.611 |

---
## 6. Human Alignment / 人工对齐效度

| **example** Metric / 指标 | **example** Value / 值 | **example** Threshold / 阈值 | **example** Status / 状态 |
| **example** --- | **example** --- | **example** --- | **example** --- |
| **example** Pearson r (Node-F1 vs Readability) | **example** 0.000 | **example** ≥ 0.70 | **example** — |
| **example** Spearman ρ (Node-F1 vs Readability) | **example** 0.000 | **example** ≥ 0.70 | **example** — |

---
## 7. Overall / 综合评分

**Composite Score / 综合评分**: 0.2314 / 1.00

| **example** 成分 / Component | **example** 值 / Value | **example** 权重 / Weight | **example** 加权分 / Weighted |
| **example** --- | **example** --- | **example** --- | **example** --- |
| **example** node_f1 | **example** 0.2727 | **example** 0.20 | **example** 0.0545 |
| **example** label_sim | **example** 1.0000 | **example** 0.10 | **example** 0.1000 |
| **example** entity_recall | **example** 0.3600 | **example** 0.10 | **example** 0.0360 |
| **example** edge_f1 | **example** 0.0000 | **example** 0.15 | **example** 0.0000 |
| **example** uas | **example** 0.0000 | **example** 0.10 | **example** 0.0000 |
| **example** nted_inv | **example** 0.2727 | **example** 0.15 | **example** 0.0409 |
| **example** pc_f1 | **example** 0.0000 | **example** 0.10 | **example** 0.0000 |
| **example** qa_relative | **example** 0.0000 | **example** 0.10 | **example** 0.0000 |

---
## 8. Diagnostics / 诊断建议

- **Node-F1 需改进 (0.273)**: 节点标签与金标准匹配率偏低。建议检查概念提取阶段是否遗漏关键概念，以及 LLM 输出是否产生过多冗余节点。
- **Entity Recall 需改进 (0.360)**: 存在关键概念遗漏。遗漏概念: 机器学习基础, 机器学习, Machine Learning, 监督学习, Supervised Learning。建议检查 STT 阶段是否正确转录了相关术语。
- **FP 偏高 (8个)**: 生成导图包含较多冗余节点，建议收紧概念提取阶段的阈值或减少 LLM 的过度生成。
- **Edge-F1 需改进 (0.000)**: 层级结构存在较多偏差。建议检查层级规划阶段是否正确组织了父子关系。
- **UAS 需改进 (0.000)**: 多个节点的父节点分配错误。建议检查层级规划阶段的输出质量。

---
*报告生成时间 / Report Generated: 2026-07-02 01:41:05*
*Generated by AI MindMap Evaluation Tool v1.0*
*依据 / Reference: Evaluation_Schema.md v1.5*