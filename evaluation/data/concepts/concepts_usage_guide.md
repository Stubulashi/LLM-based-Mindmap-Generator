# Essential Concepts Set (Es) Usage Guide

> zh: 核心概念集合 Es 使用指南

## What is the Es Set

> zh: 什么是 Es 集合

Es (Essential Concepts Set) is the mandatory core concept collection required for Entity Recall (§1.4) evaluation. It defines the key terms that must be mastered from a lecture. The evaluation framework checks whether the generated mind map covers each concept defined in Es.

> zh: Es（Essential Concepts Set）是参与 Entity Recall（§1.4）评估所必需的核心概念集合，定义了从课程中必须掌握的关键术语。评估框架将逐项检查生成导图是否覆盖了 Es 中的每一个概念。

### Usage Scenarios

> zh: 使用场景

- **Auto-extraction (default):** When no Es file is provided, the framework extracts all unique concepts from the gold standard mind map node labels as a fallback.
  > zh: **自动提取（默认）：** 未提供 Es 文件时，框架自动从金标准导图节点 label 中提取所有唯一概念作为后备。
- **Manual annotation (recommended for accuracy):** For more precise control, manually create an Es file with curated concepts extracted from the lecture transcript.
  > zh: **手工标注（推荐，精度更高）：** 为获得更精确的控制，可手工从逐字稿中标注并创建 Es 文件。
- **CLI interactive input:** During interactive evaluation sessions, users can enter a comma-separated concept list directly via the command line.
  > zh: **CLI 交互输入：** 在交互式评估会话中，用户可直接通过命令行输入逗号分隔的概念列表。

---

## File Format

> zh: 文件格式

Es files should be placed in the `evaluation/data/concepts/` directory. The file name must pair with the gold standard mind map, using the format `{prefix}_concepts.json`.

> zh: Es 文件应放置在 `evaluation/data/concepts/` 目录下，文件名需与金标准导图配对，格式为 `{prefix}_concepts.json`。

```json
{
  "concepts": [
    "Linear Regression",
    "Support Vector Machine",
    "Neural Network"
  ]
}
```

### Field Definitions

> zh: 字段定义

| Field | Required | Description |
|-------|----------|-------------|
| concepts | Yes | String array of essential concepts (zh: 核心概念字符串数组) |
| `__purpose` | No | Chinese description marker for internal documentation (zh: 中文说明标记) |
| `__purpose_en` | No | English description marker for internal documentation (zh: 英文说明标记) |
| `__format_notes` | No | Format specification notes for internal documentation (zh: 格式规范说明) |

> Note: Fields prefixed with `__` are metadata markers for internal documentation purposes only and do not affect evaluation logic.
> zh: 注意：以 `__` 前缀的字段为内部文档元数据标记，不影响评估逻辑。

---

## How to Generate the Es Set

> zh: 如何生成 Es 集合

### Method 1: Auto-generate from Gold Standard Tree

> zh: 方法一：从金标准树自动生成

This is the default fallback mechanism. If no Es file is provided, the evaluation framework auto-extracts all unique concepts from the gold standard mind map node labels. This approach is quick and convenient but may miss implicit concepts not present in node labels.

> zh: 这是默认的后备机制。未提供 Es 文件时，评估框架自动从金标准导图节点 label 中提取所有唯一概念。此方法快捷方便，但可能遗漏节点 label 中未出现的隐含概念。

### Method 2: Manually Annotate from Transcript

> zh: 方法二：手工从逐字稿标注

1. Carefully read the full lecture transcript.
   > zh: 仔细阅读课程逐字稿全文。
2. Mark all important domain terms and proper nouns.
   > zh: 标记所有重要的领域术语和专有名词。
3. Include bilingual versions (Chinese + English) where applicable to cover generated maps in different languages.
   > zh: 建议包含中英文双语版本，以覆盖不同语言生成的导图。
4. Synonyms can be listed together (e.g., SVM and Support Vector Machine).
   > zh: 同义词可以并列列出（如 SVM 和 Support Vector Machine）。
5. Recommended concept count: 10-30 concepts per lecture.
   > zh: 建议概念数量为每讲 10-30 个。

---

## Priority Rules

> zh: 优先级规则

The concept sources for Entity Recall follow this priority order:

> zh: Entity Recall 使用的概念来源遵循以下优先级：

1. **Highest priority:** User enters a comma-separated concept list via interactive CLI (zh: 最高优先级：用户从交互式 CLI 输入逗号分隔的概念列表)
2. **Second priority:** Batch mode auto-loads `evaluation/data/concepts/{pair}_concepts.json` (zh: 第二优先级：批量模式下自动加载)
3. **Fallback:** Auto-extract from gold standard mind map node labels (zh: 后备方案：从金标准导图节点 label 自动提取)

---

## Interactive Mode Usage

> zh: 交互模式使用方法

When selecting label evaluation in the interactive CLI, the system displays the following prompt:

> zh: 当在交互式 CLI 中选择 label 评估时，系统会显示以下提示：

```
[Entity Recall] Enter essential concepts (comma-separated)
> zh: 输入核心概念列表（逗号分隔）
Recommended: use a standard Es.json file from evaluation/data/concepts/
> zh: 建议使用 evaluation/data/concepts/ 下的标准 Es.json 文件
Leave empty to auto-extract from gold node labels
> zh: 留空则使用金标准节点 label 自动提取
```

If left empty, the framework auto-extracts concepts from gold standard node labels as fallback.

> zh: 如果留空，框架将自动从金标准节点 label 中提取概念作为后备。

---

## Batch Mode Auto-Loading Rules

> zh: 批量模式自动加载规则

In batch mode (`--batch`), for each evaluation pair, the system auto-detects the Es file:

> zh: 在批量评估模式（--batch）中，对于每个 pairing，系统会自动检测：

1. Build path: `evaluation/data/concepts/{pair_name}_concepts.json` (zh: 构建路径)
2. If the file exists, auto-load the concepts array (zh: 如果文件存在，自动加载 concepts 数组)
3. If the file does not exist, pass `None` — triggers fallback logic (zh: 如果文件不存在，传入 None，触发后备逻辑)

---

## Example File

> zh: 示例文件

Refer to `evaluation/data/concepts/example_essential_concepts.json` as a template for creating your own Es sets.

> zh: 可参考 `evaluation/data/concepts/example_essential_concepts.json` 作为创建自己的 Es 集合的模板。

---

## How to Use / 使用方法

> zh: 使用方法

Trigger this evaluation via the `--batch` mode with the `concepts` argument, or select the `label` option in the interactive CLI. Prepare a `{prefix}_concepts.json` file under `evaluation/data/concepts/` with the essential concepts list.

> zh: 通过 --batch 模式的 concepts 参数或交互 CLI 的 label 选项触发评估。在 evaluation/data/concepts/ 下准备 `{prefix}_concepts.json` 核心概念文件。

## Purpose / 目的

> zh: 目的

Provides the core concept standard for Entity Recall (§1.4), measuring whether the generated mind map covers the key terminology from the lecture.

> zh: 为 Entity Recall（§1.4）提供核心概念标准，衡量生成导图是否覆盖了课程关键术语。

## Principle / 原理

> zh: 原理

The essential concepts list is fuzzy-matched against generated mind map node labels using cosine similarity with a threshold of τ = 0.70. The hit rate (ratio of matched concepts) is reported as the Entity Recall score.

> zh: 概念列表与生成导图节点 label 进行模糊匹配（余弦相似度 ≥ τ=0.70），计算命中率作为 Entity Recall 得分。

## Limitations / 局限性

> zh: 局限性

- **Subjectivity in concept selection:** Different annotators may choose different essential concepts, affecting comparability of results. (zh: 概念选择的主观性，不同标注者可能选择不同的核心概念，影响结果可比性)
- **Incomplete concept lists:** An incomplete list may produce falsely low scores even for high-quality maps that contain valid but unlisted terms. (zh: 概念列表不完备时，即使高质量的导图包含有效但未列出的术语，也会产生虚假低分)
- **Synonym issues:** The same concept expressed using different synonyms (e.g., "SVM" vs. "Support Vector Machine") may be missed if not explicitly listed. (zh: 同义词问题，同一概念使用不同同义词表达时若未显式列出可能导致遗漏)

---

*Document Version: v1.0 | Created: 2026-06-29*
