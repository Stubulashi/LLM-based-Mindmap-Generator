# Question Set Usage Guide

> zh: 问答问题集使用指南

## Purpose

> zh: 用途

This guide explains how to create and use standard question set files required for Downstream QA Evaluation (§3). Question sets are used for control group (full transcript) vs experiment group (generated map only) comparative evaluation.

> zh: 本指南说明如何创建和使用下游 QA 评估（§3）所需的标准问题集文件。问题集用于执行对照组（原始逐字稿）与实验组（仅生成导图）的对比评估。

### Understanding the Comparison

> zh: 理解比较方式

- **Control group:** A human (or LLM) answers questions using the full lecture transcript as reference. This establishes a baseline performance level.
  > zh: **对照组：** 人类（或 LLM）使用完整逐字稿作为参考回答问题，建立基线性能水平。
- **Experiment group:** A human (or LLM) answers the same questions using only the generated mind map as reference. The gap between the two groups measures how well the mind map preserves the lecture's information.
  > zh: **实验组：** 人类（或 LLM）仅使用生成的导图作为参考回答同样问题。两组之间的差距衡量导图保留课程信息的程度。
- **Expected outcome:** The experiment group should achieve at least 80% of the control group's accuracy for the mind map to be considered "information-preserving."
  > zh: **预期结果：** 实验组应达到对照组准确率的至少 80%，导图才可被视为"信息保持"。

---

## File Format

> zh: 文件格式

Question sets should be placed in the `evaluation/data/questions/` directory with the file name `{prefix}_questions.json`.

> zh: 问题集应放置在 evaluation/data/questions/ 目录下，文件名为 `{prefix}_questions.json`。

```json
{
  "questions": [
    {
      "id": 1,
      "type": "fact_retrieval",
      "question": "What is the definition of supervised learning?",
      "answer": "Supervised learning is a type of machine learning where the model is trained on labeled data."
    }
  ]
}
```

### Field Definitions

> zh: 字段定义

| Field | Required | Description |
|-------|----------|-------------|
| id | Yes | Question number (integer) (zh: 题目编号，整数) |
| type | Yes | Question type category (zh: 题型分类) |
| question | Yes | Question text (zh: 问题文本) |
| answer | Yes | Gold standard answer (zh: 标准答案) |

### Question Type Distribution

> zh: 题型分布

Per Evaluation_Schema.md §3.2 requirements:

> zh: 按照 Evaluation_Schema.md §3.2 的要求：

| Type | Ratio | Assessment Dimension |
|------|-------|---------------------|
| fact_retrieval | 40% | Fact Retrieval — direct information lookup from the lecture (zh: 事实检索) |
| relation_inference | 40% | Relation Inference — understanding connections between concepts (zh: 关系推理) |
| synthesis | 20% | Synthesis — combining multiple pieces of information (zh: 综合应用) |

#### Design Rationale

> zh: 设计理念

- **fact_retrieval (40%):** Tests basic information coverage — can the user find a specific fact in the map? (zh: 测试基本信息覆盖——用户能否在导图中找到特定事实？)
- **relation_inference (40%):** Tests hierarchical understanding — does the map convey relationships between concepts? (zh: 测试层级理解——导图是否传达了概念间关系？)
- **synthesis (20%):** Tests holistic understanding — can the user compose insights from multiple nodes? (zh: 测试整体理解——用户能否综合多个节点得出见解？)

---

## Design Constraints

> zh: 设计约束

1. All questions must be answerable from the transcript alone — ensures a valid control baseline.
   > zh: 所有题目必须可仅通过原始逐字稿回答，确保对照组基线有效。
2. Question difficulty must be reviewed by 2 domain experts independently.
   > zh: 题目难度需经 2 位领域专家背对背评审。
3. Each question has exactly one objective correct answer.
   > zh: 每题有且仅有一个客观正确答案。
4. Each group should be repeated **3 times and averaged** to reduce LLM randomness.
   > zh: 每组至少重复 3 次实验取平均值，减少 LLM 随机性影响。

---

## Usage

> zh: 使用方法

### Interactive Mode

> zh: 交互模式

Select the `qa` evaluation method in the interactive CLI. The system will prompt for question set loading. Currently, the question set needs to be passed programmatically to QAEvaluator.

> zh: 在交互式 CLI 中选择 qa 评估方法，系统会提示加载问题集。当前需要将问题集以代码方式传入 QAEvaluator。

### Batch Mode

> zh: 批量模式

In batch mode, the system detects question set files in `evaluation/data/questions/`.

> zh: 在批量模式下，系统会检测 evaluation/data/questions/ 下的问题集文件。

---

## How to Use / 使用方法

> zh: 使用方法

Trigger this evaluation by selecting the `qa` option in the interactive CLI. The system loads the question set and runs comparative evaluation between the control group (full transcript) and the experiment group (generated map only).

> zh: 通过交互式 CLI 的 qa 选项触发评估，系统加载问题集并执行对照组（完整逐字稿）与实验组（仅生成导图）的对比评估。

## Purpose / 目的

> zh: 目的

Measures whether the generated mind map preserves sufficient semantic information from the lecture to serve as a viable substitute for the full transcript in downstream QA tasks.

> zh: 衡量生成导图是否保留了课程的语义信息，能否替代完整逐字稿用于下游 QA 任务。

## Principle / 原理

> zh: 原理

The evaluation compares QA accuracy between the control group (full transcript as reference) and the experiment group (generated map as reference). The QA Retention rate is computed as `accuracy_experiment / accuracy_control × 100%`.

> zh: 对比对照组（完整逐字稿）与实验组（仅导图）的 QA 准确率，计算 QA Retention = 实验组准确率 / 对照组准确率 × 100%。

## Limitations / 局限性

> zh: 局限性

- **Question set quality:** The quality of the question set directly affects evaluation results — poorly designed questions may produce misleading conclusions. (zh: 问题集质量直接影响评估结果，设计不佳的问题可能得出误导性结论)
- **LLM answer randomness:** LLM-based QA exhibits inherent randomness; multiple repetitions (≥3) and averaging are required to mitigate this. (zh: LLM 回答具有随机性，需要多次重复实验取平均值来缓解)
- **Limited question coverage:** The question set cannot cover all possible information contained in the lecture, potentially missing some aspects of information retention. (zh: 问题覆盖范围受限，问题集无法涵盖课程中所有可能的信息点)

---

*Document Version: v1.0 | Created: 2026-06-29*
