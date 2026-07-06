# 🎯 Mind Map Generation Quality Report
# 思维导图生成质量报告
# (Example Demo / 示例演示)


**Date / 日期**: 2026-07-05 20:58:20
**Pipeline Config / 管线配置**: embedding=paraphrase-multilingual-MiniLM-L12-v2, threshold=0.7 (Example Demo / 示例演示)
**Embedding Model**: paraphrase-multilingual-MiniLM-L12-v2
**Threshold τ**: 0.7
**Gold Nodes / 金标准节点数**: 11
**Gold Links / 金标准边数**: 10
**Generated Nodes / 生成节点数**: 11

---
## 📋 Summary / 摘要

| **example** Dimension / 维度 | **example** Key Metric / 核心指标 | **example** Value / 值 | **example** Grade / 评级 | **example** Status / 状态 |
|---|---|---|---|---|
| **example** Composite / 综合 | **example** Score / 评分 | **example** 0.2314 | **example** — | **example** — |
| **example** Node Label / 节点标签 | **example** Node-F1 | **example** 0.273 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** Hierarchy / 层级结构 | **example** Edge-F1 | **example** 0.000 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** QA / 问答 | **example** QA Retention | **example** 0.000 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** Multilingual / 多语言 | **example** Max Δ Recall | **example** 0.611 | **example** — | **example** **—** |
| **example** Human Corr / 人工对齐 | **example** Pearson r | **example** N/A | **example** — | **example** — |

---
## 🏷️ 1. Node Label Quality / 节点标签质量

| **example** Metric / 指标 | **example** Value / 值 | **example** Threshold / 阈值 | **example** Grade / 评级 | **example** Status / 状态 |
|---|---|---|---|---|
| **example** Node-F1 | **example** 0.273 | **example** ≥ 0.85 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** LabelSim | **example** 1.000 | **example** ≥ 0.85 | **example** 🏆 Excellent / 优秀 | **example** **✅ PASS** |
| **example** Entity Recall | **example** 0.360 | **example** ≥ 0.90 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |

**Hungarian Alignment Details / 匈牙利匹配详情**:
- Gold nodes / 金标准节点数: 11
- Gen nodes / 生成节点数: 11
- High-quality matches (τ=0.7) / 高质量匹配对: 3
- FP (Unmatched generated nodes) / 误报 FP: 8
- FN (Unmatched gold nodes) / 漏报 FN: 8

**Match Details / 匹配明细**:

| **example** Gold Label / 金标准标签 | **example** Gen Label / 生成标签 | **example** Similarity / 相似度 |
|---|---|---|
| **example** 支持向量机 | **example** 支持向量机 | **example** 1.0000 |
| **example** K-Means聚类 | **example** K-Means聚类 | **example** 1.0000 |
| **example** Q-Learning | **example** Q-Learning | **example** 1.0000 |

**Entity Recall Details / Entity Recall 详情**:
- Total core concepts / 核心概念总数: 25
- Hits / 命中: 9
- Misses / 遗漏: 16
- Missed concepts / 遗漏概念: 机器学习基础, 机器学习, Machine Learning, 监督学习, Supervised Learning, 无监督学习, Unsupervised Learning, 线性回归, Linear Regression, SVM, Support Vector Machine, Decision Tree, 主成分分析, PCA, Principal Component Analysis, Policy Gradient

---
## 🌳 2. Hierarchy Accuracy / 层级结构正确率

| **example** Metric / 指标 | **example** Value / 值 | **example** Threshold / 阈值 | **example** Grade / 评级 | **example** Status / 状态 |
|---|---|---|---|---|
| **example** Edge-F1 | **example** 0.000 | **example** ≥ 0.80 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** Edge-P | **example** 0.000 | **example** — | **example** — | **example** — |
| **example** Edge-R | **example** 0.000 | **example** — | **example** — | **example** — |
| **example** UAS | **example** 0.000 | **example** ≥ 0.85 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** PC-F1 | **example** 0.000 | **example** ≥ 0.75 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** LAR | **example** 1.000 | **example** ≥ 0.70 | **example** 🏆 Excellent / 优秀 | **example** **✅ PASS** |
| **example** nTED | **example** 0.727 | **example** ≤ 0.25 | **example** ⚠️ Needs Improvement / 需改进 | **example** **❌ FAIL** |
| **example** Raw TED | **example** 8.00 | **example** — | **example** — | **example** — |

**Edge Metric Details / 边级指标详情**:
- Gold edges / 金标准边数: 10
- Gen edges / 生成边数: 10
- Correct edges TP / 正确边 TP: 0
- Extra edges FP / 多余边 FP: 10
- Missing edges FN / 缺失边 FN: 10

---
## ❓ 3. Downstream QA / 下游问答测试

| **example** Group / 组别 | **example** Accuracy / 准确率 | **example** Token Cost / Token消耗 | **example** Relative / 相对值 |
|---|---|---|---|
| **example** Control (Full) / 对照组 | **example** 0.000 | **example** — | **example** baseline |
| **example** Experiment (Map) / 实验组 | **example** 0.000 | **example** — | **example** 0.000 |

**QA Retention**: 0.000
**Token Reduction / Token 缩减**: 0.0%

---
## 4. Efficiency & STT / 效率与语音转录

*Not executed / 未执行（requires timing logs and STT data）*

---
## 🌐 5. Multilingual & Robustness / 多语言与鲁棒性

| **example** Metric / 指标 | **example** CN | **example** EN | **example** Mixed / 混合 | **example** Max Δ |
|---|---|---|---|---|
| **example** Entity Recall | **example** 0.912 | **example** 0.872 | **example** 1.483 | **example** 0.611 |

---
## 👤 6. Human Alignment / 人工对齐效度

| **example** Metric / 指标 | **example** Value / 值 | **example** Threshold / 阈值 | **example** Status / 状态 |
|---|---|---|---|
| **example** Pearson r (Node-F1 vs Readability) | **example** 0.000 | **example** ≥ 0.70 | **example** **Needs Improvement / 需改进** |
| **example** Spearman ρ (Node-F1 vs Readability) | **example** 0.000 | **example** ≥ 0.70 | **example** **Needs Improvement / 需改进** |

---
## 📊 7. Overall / 综合评分

**Composite Score / 综合评分**: 0.2314 / 1.00

| **example** Component / 成分 | **example** Value / 值 | **example** Weight / 权重 | **example** Weighted / 加权分 |
|---|---|---|---|
| **example** node_f1 | **example** 0.2727 | **example** 0.20 | **example** 0.0545 |
| **example** label_sim | **example** 1.0000 | **example** 0.10 | **example** 0.1000 |
| **example** entity_recall | **example** 0.3600 | **example** 0.10 | **example** 0.0360 |
| **example** edge_f1 | **example** 0.0000 | **example** 0.15 | **example** 0.0000 |
| **example** uas | **example** 0.0000 | **example** 0.10 | **example** 0.0000 |
| **example** nted_inv | **example** 0.2727 | **example** 0.15 | **example** 0.0409 |
| **example** pc_f1 | **example** 0.0000 | **example** 0.10 | **example** 0.0000 |
| **example** qa_relative | **example** 0.0000 | **example** 0.10 | **example** 0.0000 |

**Interpretation Guide / 解读指南**:
- Score ≥ 0.85: Excellent overall quality / 整体质量优秀
- Score ≥ 0.70: Good quality, minor improvements possible / 整体质量良好，有改进空间
- Score < 0.70: Needs improvement in key areas / 关键领域需要改进

---
## 🔍 8. Diagnostics / 诊断建议

> **⚠️ Node-F1 Needs Improvement (0.273) / 节点F1需改进**. Node labels have low match rate with gold standard. Check concept extraction for missed concepts and LLM output for redundant nodes. / 节点标签与金标准匹配率低。检查概念抽取是否有遗漏，以及 LLM 输出是否有多余节点。
> **⚠️ Entity Recall Needs Improvement (0.360) / 实体召回率需改进**. Key concepts missing / 关键概念缺失: 机器学习基础, 机器学习, Machine Learning, 监督学习, Supervised Learning. Check STT transcription for these terms. / 检查这些术语的 STT 转录。
> **⚠️ High FP (8) / FP 过高**. Generated map has redundant nodes. Tighten concept extraction threshold or reduce LLM over-generation. / 生成图存在冗余节点。建议收紧概念抽取阈值或减少 LLM 过度生成。
> **⚠️ Edge-F1 Needs Improvement (0.000) / 边F1需改进**. Hierarchy has significant deviations. Check hierarchy planning stage for correct parent-child relationships. / 层级结构存在显著偏差。检查层级规划阶段父子关系是否正确。
> **⚠️ UAS Needs Improvement (0.000) / UAS 需改进**. Multiple nodes have incorrect parent assignments. Check hierarchy planning quality. / 多个节点的父级分配错误。检查层级规划质量。
> **⚠️ QA Retention Needs Improvement (0.000) / QA 保持率需改进**. The generated map does not preserve sufficient information for downstream QA tasks. / 生成导图未能为下游 QA 任务保留足够信息。

---
*Report Generated / 报告生成时间: 2026-07-05 20:58:20*
*Generated by AI MindMap Evaluation Tool v1.0*
*Reference / 依据: Evaluation_Schema.md v1.5*