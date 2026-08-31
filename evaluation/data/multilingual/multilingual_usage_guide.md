# Multilingual Test Data Usage Guide

> zh: 多语言测试数据使用指南

## Purpose

> zh: 用途

This guide explains how to create test data required for Multilingual Adaptability & Robustness Evaluation (§5), which includes: three multilingual test set results and noise attenuation test results.

> zh: 本指南说明如何创建和使用多语言适应性与鲁棒性评估（§5）所需的测试数据，包括：三组多语言测试集结果 + 噪声衰减测试结果。

### When to Use This Guide

> zh: 何时使用本指南

- Evaluating how well your system handles non-English or mixed-language input.
  > zh: 评估系统对非英语或混合语言输入的处理能力。
- Testing system robustness against STT (Speech-to-Text) noise.
  > zh: 测试系统对 STT 噪声的鲁棒性。
- Comparing system performance across different language configurations.
  > zh: 比较不同语言配置下的系统性能。

---

## Test Set Composition

> zh: 测试集组成

### Three Test Groups

> zh: 三组测试集

Each group requires evaluation results from **5 lecture segments** (or mind maps):

> zh: 每组需要 5 个 Lecture 片段（或导图）的评估结果：

| Test Set | File Naming | Description |
|----------|-------------|-------------|
| Chinese-only | `example_cn_results.json` | 100% Chinese lecture segments (zh: 纯中文授课片段) |
| English-only | `example_en_results.json` | 100% English lecture segments (zh: 纯英文授课片段) |
| Chinese-English Mixed | `example_mixed_results.json` | Mixed Chinese-English lecture segments (zh: 中英混合授课片段) |

### Required Metrics Per Group

> zh: 每组需要包含的指标

- **Entity Recall** (§1.4) — measures concept coverage (zh: 概念覆盖率)
- **LabelSim** (§1.3) — measures label similarity (zh: 标签相似度)
- **PC-F1** (§2.4) — measures parent-child relationship F1 score (zh: 父子关系 F1 分数)

---

## Test Data Format

> zh: 测试数据格式

Each test set result JSON file follows this structure:

> zh: 每个测试集结果 JSON 文件格式如下：

```json
{
  "results": [
    {
      "segment_id": "cn_01",
      "entity_recall": 0.92,
      "label_sim": 0.88,
      "pc_f1": 0.85
    }
  ],
  "summary": {
    "mean_entity_recall": 0.912,
    "mean_label_sim": 0.870,
    "mean_pc_f1": 0.842
  }
}
```

### Field Definitions

> zh: 字段定义

| Field | Type | Description |
|-------|------|-------------|
| segment_id | string | Unique identifier for the lecture segment (zh: 课程片段唯一标识) |
| entity_recall | float | Entity Recall score (0.0-1.0) (zh: 实体召回率) |
| label_sim | float | Label Similarity score (0.0-1.0) (zh: 标签相似度) |
| pc_f1 | float | Parent-Child F1 score (0.0-1.0) (zh: 父子关系 F1 分数) |
| summary.mean_* | float | Mean of each metric across all segments (zh: 各指标在所有片段上的均值) |

### Result Interpretation Guide

> zh: 结果解读指南

| Metric Range | Interpretation |
|--------------|---------------|
| 0.90-1.00 | Excellent — strong multilingual adaptability (zh: 优秀，多语言适应性很强) |
| 0.80-0.89 | Good — minor language-specific issues (zh: 良好，存在轻微语言相关差异) |
| 0.70-0.79 | Acceptable — noticeable performance gap across languages (zh: 可接受，不同语言间有显著差异) |
| < 0.70 | Needs improvement — significant language-related degradation (zh: 需改进，语言相关退化显著) |

---

## Noise Test Data

> zh: 噪声测试数据

Noise tests evaluate system stability under different noise levels, using character-level perturbation (replace/delete/insert) to simulate STT (Speech-to-Text) noise.

> zh: 噪声测试用于评估系统在不同噪声水平下的稳定性，使用字符级扰动（替换/删除/插入）模拟 STT 噪声。

### How Noise Is Applied

> zh: 噪声施加方式

For each character in the input text, with probability `p`:
- **Replace:** Substitute the character with a random character from the same character set (zh: 替换)
- **Delete:** Remove the character entirely (zh: 删除)
- **Insert:** Add a random character adjacent to the current position (zh: 插入)

> zh: 对输入文本中的每个字符，以概率 p 执行替换、删除或插入操作。

### Noise Levels

> zh: 噪声水平

| Noise Probability `p` | Expected WER | Description |
|-----------------------|-------------|-------------|
| 0.00 | ~0.000 | Baseline — no noise (zh: 基线，无噪声) |
| 0.05 | ~0.048 | Low noise — mild STT errors (zh: 低噪声，轻度 STT 错误) |
| 0.10 | ~0.096 | Medium noise — moderate STT errors (zh: 中等噪声) |
| 0.15 | ~0.142 | High noise — significant STT errors (zh: 较高噪声) |
| 0.20 | ~0.191 | Very high noise — severe STT errors (zh: 高噪声) |

> **Expected behavior:** As `p` increases, `entity_recall` and `label_sim` should degrade gracefully. A well-designed system should maintain functional performance even at `p = 0.15`.
> zh: **预期行为：** 随 p 增大，entity_recall 和 label_sim 应逐渐下降但保持基本可用。设计良好的系统即使在 p=0.15 时也应维持功能性表现。

---

## Storage Location

> zh: 存放位置

All multilingual test data files should be placed in the `evaluation/data/multilingual/` directory.

> zh: 所有多语言测试数据文件应放置在 evaluation/data/multilingual/ 目录下。

---

## How to Use / 使用方法

> zh: 使用方法

Trigger this evaluation by selecting the `multilingual` option in the interactive CLI. The system will run evaluation across CN, EN, and Mixed language groups and report comparative results.

> zh: 通过交互式 CLI 的 multilingual 选项触发评估，系统将在 CN/EN/Mixed 三组语言上运行评估并报告对比结果。

## Purpose / 目的

> zh: 目的

Evaluates the system's stability and adaptability across different languages and noise conditions, ensuring consistent performance regardless of input language.

> zh: 评估系统在不同语言和噪声条件下的稳定性和适应性，确保无论输入语言如何都能保持一致的性能。

## Principle / 原理

> zh: 原理

Compare the maximum performance gap across CN, EN, and Mixed groups for three metrics: `entity_recall`, `label_sim`, and `pc_f1`. Character-level perturbations (replace/delete/insert) are applied to simulate STT (Speech-to-Text) noise at varying probability levels.

> zh: 对比 CN/EN/Mixed 三组在 entity_recall、label_sim、pc_f1 三个指标上的最大差值；通过字符级扰动（替换/删除/插入）模拟不同概率水平的 STT 噪声。

## Limitations / 局限性

> zh: 局限性

- **Limited language coverage:** Only 3 language scenarios (CN, EN, Mixed) are evaluated, which may not generalize to other language pairs. (zh: 仅覆盖 3 种语言场景，可能无法推广到其他语言对)
- **Simplified noise model:** The character-level perturbation model is a coarse approximation of real STT noise patterns. (zh: 字符级扰动模型是对真实 STT 噪声模式的粗略近似)
- **Test set scale:** Each group requires only 5 segments; larger test sets would provide more reliable statistical conclusions. (zh: 每组仅需 5 个片段，更大规模的测试集能提供更可靠的统计结论)

---

*Document Version: v1.0 | Created: 2026-06-29*
