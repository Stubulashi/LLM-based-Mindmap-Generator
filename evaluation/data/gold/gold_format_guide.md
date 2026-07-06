# Gold Standard Mind Map File Format Guide

> zh: 金标准导图文件格式指南

## File Purpose

> zh: 文件用途

This guide explains the JSON file format for Gold Standard Mind Maps, helping developers and annotators create labeled data that meets the evaluation framework requirements. Place the gold standard JSON file in the `evaluation/data/gold/` directory, and the evaluation tool will auto-detect it for comparative assessment.

> zh: 本指南说明金标准导图（Gold Standard Mind Map）的 JSON 文件格式，帮助开发者和标注者创建符合评估框架要求的标注数据。将金标准 JSON 文件放入 evaluation/data/gold/ 目录后，评估工具可自动检测并用于对比评估。

### When to Use This Guide

> zh: 何时使用本指南

- You are creating a new gold standard mind map for a lecture to serve as a ground-truth reference.
  > zh: 为某课程创建新的金标准导图作为真实参考标准时。
- You are reviewing or validating an existing gold standard file for correctness.
  > zh: 审查或验证现有金标准文件的正确性时。
- You need to understand the field structure for debugging evaluation results.
  > zh: 需要理解字段结构以调试评估结果时。

---

## File Structure

> zh: 文件结构

The gold standard mind map JSON file contains a root-level object with nodes and optional fields:

> zh: 金标准导图 JSON 文件包含一个根级对象，其结构如下：

```json
{
  "nodes": [
    { "id": "...", "label": "...", "parent_id": "..." }
  ]
}
```

---

## Field Definitions

> zh: 字段定义

### id (Node Unique Identifier)

> zh: 节点唯一标识

**Required.** Lowercase letters with underscores; must be unique within the same file.

> zh: 必填。小写字母加下划线，在同一文件中必须唯一。

- **Example:** `linear_regression`, `kmeans`, `root`
- **Constraints:** No spaces, no special characters except underscore. Case-sensitive.
  > zh: 约束：无空格，除下划线外无特殊字符，区分大小写。

---

### label (Node Text Label)

> zh: 节点文本标签

**Required.** Chinese or English text; should be consistent with the concept name in the lecture transcript.

> zh: 必填。中文或英文文本，应与课程讲义中的概念名称保持一致。

- **Example:** `线性回归`, `K-Means Clustering`, `Reinforcement Learning`
- **Tip:** Use the exact terminology as it appears in the lecture for best evaluation accuracy.
  > zh: 提示：使用课程中出现的精确术语以获得最佳评估精度。

---

### parent_id (Parent Node ID)

> zh: 父节点 ID

**Required.** The root node's `parent_id` must be `null`. A child node's `parent_id` must reference an existing node `id` in the `nodes` array.

> zh: 必填。根节点的 parent_id 为 null；子节点的 parent_id 必须对应一个已存在于 nodes 数组中的节点 id。

- **Root node requirement:** Exactly one node must have `parent_id: null`. (zh: 有且仅有一个根节点)
- **Circular reference warning:** A's parent cannot be B if B's parent is A. (zh: 禁止循环引用)

---

### details (Node Details)

> zh: 节点详情

**Optional.** A string array for supplementary node descriptions. Recommended format: every two entries form a bilingual pair — first Chinese, then English.

> zh: 可选。字符串数组，用于补充节点的详细说明。推荐每两个条目形成一组中英双语说明：第一行中文，第二行英文。

```json
"details": [
  "一种监督学习算法",
  "A supervised learning algorithm"
]
```

- **Use case:** Provide definitions, examples, or important notes for a node. (zh: 提供节点的定义、示例或重要说明)

---

### metadata (Metadata)

> zh: 元数据

**Optional.** May include `depth` (hierarchy level), `type` (node type), and other auxiliary information.

> zh: 可选。可包含 depth（层级深度）、type（节点类型）等辅助信息。

| Field | Values | Description |
|-------|--------|-------------|
| type | `root` | Root node of the tree (zh: 根节点) |
| type | `category` | Category/branch node (zh: 分类节点) |
| type | `algorithm` | Algorithm/concrete node (zh: 算法节点) |
| depth | integer | Hierarchical depth level (1-based) (zh: 层级深度，从 1 开始) |

---

### links (Edge List)

> zh: 边列表

**Optional.** Each edge contains `source` (parent id) and `target` (child id). Can be auto-derived from nodes' `parent_id` fields. Included for compatibility with the `modify_mind_map` output format.

> zh: 可选。每条边包含 source（父节点 id）和 target（子节点 id）。可从节点的 parent_id 字段自动推导，用于与 modify_mind_map 输出格式保持一致。

```json
"links": [
  { "source": "root", "target": "linear_regression" },
  { "source": "linear_regression", "target": "cost_function" }
]
```

---

### tree (G6 Nested Tree Format)

> zh: G6 嵌套树格式

**Optional.** The G6 frontend nested tree format. Root nodes recursively contain subtrees via the `children` field. Consistent with the `tree` field in `modify_mind_map` output.

> zh: 可选。G6 前端消费的嵌套树格式，根节点通过 children 字段递归包含子树，与 modify_mind_map 输出的 tree 字段一致。

```json
"tree": {
  "id": "root",
  "label": "Machine Learning",
  "children": [
    { "id": "linear_regression", "label": "Linear Regression", "children": [] }
  ]
}
```

---

## How to Manually Label a Standard Tree from Lecture Notes

> zh: 如何从课程讲义手动标注标准树

1. Carefully read the full lecture notes or transcript.
   > zh: 仔细阅读课程讲义或逐字稿全文。
2. Extract all key concept terms and mark their appearances in the text.
   > zh: 提取所有关键概念术语，标记它们在文中的出现位置。
3. Determine hierarchical relationships: which concepts are parent concepts and which are their children.
   > zh: 确定概念之间的层级关系：哪些是上层概念，哪些是其子概念。
4. The root node is typically the lecture's central topic.
   > zh: 根节点通常是该讲的最核心主题。
5. Level 2 nodes are the main branch topics under the root.
   > zh: 第 2 层节点是根节点下的主要分支主题。
6. Level 3 and deeper nodes are specific concepts or algorithms under each branch.
   > zh: 第 3 层及更深节点是各分支下的具体概念或算法。
7. Assign a unique `id` and descriptive `label` to each node.
   > zh: 为每个节点分配唯一的 id 和描述性的 label。
8. **Optional:** Add `details` for important nodes with definitions or examples.
   > zh: 可选：为重要节点添加 details，补充定义或示例说明。

---

## Tree Structure Validation

> zh: 树结构验证

After labeling, verify the following conditions to ensure a valid tree:

> zh: 标注完成后，请检查以下条件：

- **Root node check:** Exactly one root node exists (`parent_id` is `null`). (zh: 有且仅有一个根节点)
- **Reachability check:** All nodes can be linked to the root via `parent_id` chain. (zh: 所有节点均可通过 parent_id 链接到根节点)
- **Cycle check:** No circular references exist (e.g., A's parent is B and B's parent is A). (zh: 不存在循环引用)
- **Node count check:** Recommended minimum of 3 levels depth and 8+ nodes for meaningful evaluation. (zh: 建议至少 3 层深度，8 个以上节点)

> **Validation tip:** Write a simple script to traverse the `parent_id` chain from each node to verify it reaches the root. A cycle detection algorithm (DFS with visited set) can help catch circular references automatically.
> zh: **验证提示：** 编写简单脚本从每个节点沿 parent_id 链遍历，验证能到达根节点。使用 DFS 加访问集合的环检测算法可自动捕获循环引用。

---

## Common Mistakes and Fixes

> zh: 常见错误与修复

| Mistake | Description | Fix |
|---------|-------------|-----|
| Missing root node | No node with `parent_id: null` in the nodes array (zh: 缺少根节点) | Add a root node with `parent_id: null` (zh: 添加一个 parent_id 为 null 的根节点) |
| Orphaned node | A child node's `parent_id` references a non-existing id (zh: 孤立节点) | Ensure all referenced `parent_id` values exist in the `nodes` array (zh: 确保所有 parent_id 值在 nodes 数组中存在) |
| Duplicate labels | Different concepts share the same `id` or `label` (zh: 标签重复) | Assign unique `id` values; labels can repeat only if they refer to the same concept (zh: id 必须唯一) |
| Hierarchy confusion | Nodes at the same level incorrectly set as parent-child (zh: 层级混乱) | Review the lecture structure — sibling concepts should share the same parent (zh: 同级概念应有相同父节点) |

---

## How to Use This Guide

> zh: 如何使用本指南

1. Refer to `gold_example.json` for a complete example dataset.
   > zh: 参考 gold_example.json 查看完整的范例数据。
2. Follow this guide's field definitions to create your own gold standard files.
   > zh: 按照本指南的字段定义创建自己的金标准文件。
3. Place the JSON file in the `evaluation/data/gold/` directory.
   > zh: 将 JSON 文件放入 evaluation/data/gold/ 目录。
4. Run the evaluation tool and select `label` and `hierarchy` evaluation methods.
   > zh: 运行评估工具时选择 label 和 hierarchy 评估方法。
5. The evaluation tool auto-detects and loads gold standard files for comparative assessment.
   > zh: 评估工具会自动检测并加载金标准文件进行对比评估。

---

## How to Use / 使用方法

> zh: 使用方法

Trigger this evaluation via the `--batch` mode or select the `label` or `hierarchy` option in the interactive CLI. The system auto-detects gold standard JSON files from `evaluation/data/gold/`.

> zh: 通过 --batch 模式或交互式 CLI 的 label/hierarchy 选项触发评估，系统会自动检测 evaluation/data/gold/ 下的金标准 JSON 文件。

## Purpose / 目的

> zh: 目的

Provides a ground-truth reference standard for computing metrics such as Node-Precision/Recall/F1, Edge-F1, and PC-F1.

> zh: 提供 ground-truth 参考标准，用于计算 Node-P/R/F1、Edge-F1 等指标。

## Principle / 原理

> zh: 原理

The Hungarian algorithm is used to find the optimal one-to-one matching between generated nodes and gold standard nodes. Precision, Recall, and F1 scores are then computed based on the matched pairs.

> zh: 通过 Hungarian 算法将生成节点与金标准节点进行最优匹配，然后计算 Precision/Recall/F1 等指标。

## Limitations / 局限性

> zh: 局限性

- **Annotation quality dependency:** Results heavily rely on the accuracy and completeness of human annotation. (zh: 标注质量高度依赖人工，结果受标注准确性和完备性影响)
- **Single gold standard:** A single ground-truth cannot cover all possible reasonable structures — different valid mind maps may organize information differently. (zh: 单一金标准无法覆盖所有可能的合理结构，不同有效的导图可能以不同方式组织信息)
- **Intentionality of hierarchy:** Hierarchical relationships are inherently interpretive; different domain experts may disagree on the optimal parent-child structure. (zh: 层级关系本身具有意图性，不同领域专家可能对最优父子结构存在分歧)

---

*Document Version: v1.0 | Created: 2026-06-29*
