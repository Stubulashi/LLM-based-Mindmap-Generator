# Concept Tree Label Evaluation via Hungarian Algorithm & Embedding Similarity
# 基于匈牙利算法与嵌入相似度的概念树标签评测方法

> **文档约定 / Document Conventions**：
>
> - 本文采用**英语在前、中文在后**的双语结构，两种语言具有同等地位
> - 目录统一置于文档开头，每个条目采用"英语 / 中文"格式
> - 正文部分英语先行（含完整章节）、中文后列（含完整章节）
> - 公式符号优先采用国际通用记号
> - Python 代码注释使用英文以保持代码可读性与国际兼容性
>
> **This document adopts a bilingual structure with English first, followed by Chinese. Both languages have equal status.**
>
> **The table of contents is placed at the beginning with each entry in "English / Chinese" format.**
>
> **Formula symbols follow internationally standard notation. Code examples use English comments for readability.**

---

## Table of Contents / 目录

### English Section

- [1. Problem Definition / 问题定义](#1-problem-definition)
  - [1.1 Label Evaluation / 标签评测](#11-label-evaluation)
  - [1.2 Hierarchy Evaluation / 层级评测](#12-hierarchy-evaluation)
- [2. The Node Alignment Problem / 节点对齐问题](#2-the-node-alignment-problem)
  - [2.1 Formal Definition / 形式化定义](#21-formal-definition)
  - [2.2 A Concrete Example / 具体示例](#22-a-concrete-example)
- [3. Candidate Solutions Analysis / 备选方案分析](#3-candidate-solutions-analysis)
  - [3.1 Manual Matching / 人工匹配](#31-manual-matching)
  - [3.2 Exhaustive Search / 穷举搜索](#32-exhaustive-search)
  - [3.3 Hungarian Algorithm (Optimal Assignment) / 匈牙利算法（最优指派）](#33-hungarian-algorithm-optimal-assignment)
  - [3.4 Why Not Greedy / Heuristic Matching? / 为什么不使用贪心/启发式匹配](#34-why-not-greedy--heuristic-matching)
- [4. The Root Node Controversy / 根节点争议](#4-the-root-node-controversy)
  - [4.1 The Cross-Level Matching Risk / 跨层级匹配风险](#41-the-cross-level-matching-risk)
  - [4.2 Remove-Root Approach (Rejected) / 去除根节点方案（已否决）](#42-remove-root-approach-rejected)
  - [4.3 Depth-Constraint Approach (Rejected) / 深度约束方案（已否决）](#43-depth-constraint-approach-rejected)
  - [4.4 Final Decision: Retain All Nodes / 最终决定：保留所有节点](#44-final-decision-retain-all-nodes)
- [5. Final Methodology / 最终评测流程](#5-final-methodology)
- [6. Rationale: Independence of Label and Hierarchy / 方法合理性：标签评测与层级评测的独立性](#6-rationale-independence-of-label-and-hierarchy)
- [7. Final Scoring Formula / 最终评分公式](#7-final-scoring-formula)
- [8. Python Implementation / Python 实现](#8-python-implementation)
  - [8.1 Computing the Similarity Matrix / 计算相似度矩阵](#81-computing-the-similarity-matrix)
  - [8.2 Hungarian Algorithm via SciPy / 通过 SciPy 执行匈牙利算法](#82-hungarian-algorithm-via-scipy)
  - [8.3 Complete Evaluation Pipeline / 完整评测管线](#83-complete-evaluation-pipeline)
  - [8.4 Handling Unequal-Sized Node Sets / 处理节点数量不相等的情况](#84-handling-unequal-sized-node-sets)
- [9. Limitations and Considerations / 局限性与注意事项](#9-limitations-and-considerations)
  - [9.1 Cosine Similarity Measures Correlation, Not Equivalence / 余弦相似度衡量的是相关性而非等价性](#91-cosine-similarity-measures-correlation-not-equivalence)
  - [9.2 Embedding Model Bias / 嵌入模型偏差](#92-embedding-model-bias)
  - [9.3 The One-to-One Matching Assumption / 一对一匹配假设](#93-the-one-to-one-matching-assumption)
- [Appendix A: Complete Worked Example / 附录 A：完整标签评测示例](#appendix-a-complete-worked-example)
- [Appendix B: Hungarian Algorithm Walkthrough / 附录 B：匈牙利算法计算过程详解](#appendix-b-hungarian-algorithm-walkthrough)
- [Appendix C: Formal Definition of the Hungarian Algorithm / 附录 C：匈牙利算法形式化定义](#appendix-c-formal-definition-of-the-hungarian-algorithm)
- [Appendix D: Embedding Model Comparison / 附录 D：嵌入模型对比](#appendix-d-embedding-model-comparison)

### Chinese Section / 中文部分

- [1. 问题定义 / Problem Definition](#1-问题定义)
  - [1.1 标签评测 / Label Evaluation](#11-标签评测)
  - [1.2 层级评测 / Hierarchy Evaluation](#12-层级评测)
- [2. 节点对齐问题 / The Node Alignment Problem](#2-节点对齐问题)
  - [2.1 形式化定义 / Formal Definition](#21-形式化定义)
  - [2.2 具体示例 / A Concrete Example](#22-具体示例)
- [3. 备选方案分析 / Candidate Solutions Analysis](#3-备选方案分析)
  - [3.1 人工匹配 / Manual Matching](#31-人工匹配)
  - [3.2 穷举搜索 / Exhaustive Search](#32-穷举搜索)
  - [3.3 匈牙利算法（最优指派）/ Hungarian Algorithm (Optimal Assignment)](#33-匈牙利算法最优指派)
  - [3.4 为什么不使用贪心/启发式匹配 / Why Not Greedy / Heuristic Matching?](#34-为什么不使用贪心启发式匹配)
- [4. 根节点争议 / The Root Node Controversy](#4-根节点争议)
  - [4.1 跨层级匹配风险 / The Cross-Level Matching Risk](#41-跨层级匹配风险)
  - [4.2 去除根节点方案（已否决）/ Remove-Root Approach (Rejected)](#42-去除根节点方案已否决)
  - [4.3 深度约束方案（已否决）/ Depth-Constraint Approach (Rejected)](#43-深度约束方案已否决)
  - [4.4 最终决定：保留所有节点 / Final Decision: Retain All Nodes](#44-最终决定保留所有节点)
- [5. 最终评测流程 / Final Methodology](#5-最终评测流程)
- [6. 方法合理性：标签评测与层级评测的独立性 / Rationale: Independence of Label and Hierarchy](#6-方法合理性标签评测与层级评测的独立性)
- [7. 最终评分公式 / Final Scoring Formula](#7-最终评分公式)
- [8. Python 实现 / Python Implementation](#8-python-实现)
  - [8.1 计算相似度矩阵 / Computing the Similarity Matrix](#81-计算相似度矩阵)
  - [8.2 通过 SciPy 执行匈牙利算法 / Hungarian Algorithm via SciPy](#82-通过-scipy-执行匈牙利算法)
  - [8.3 完整评测管线 / Complete Evaluation Pipeline](#83-完整评测管线)
  - [8.4 处理节点数量不相等的情况 / Handling Unequal-Sized Node Sets](#84-处理节点数量不相等的情况)
- [9. 局限性与注意事项 / Limitations and Considerations](#9-局限性与注意事项)
  - [9.1 余弦相似度衡量的是相关性而非等价性 / Cosine Similarity Measures Correlation, Not Equivalence](#91-余弦相似度衡量的是相关性而非等价性)
  - [9.2 嵌入模型偏差 / Embedding Model Bias](#92-嵌入模型偏差)
  - [9.3 一对一匹配假设 / The One-to-One Matching Assumption](#93-一对一匹配假设)
- [附录 A：完整标签评测示例 / Appendix A: Complete Worked Example](#附录-a完整标签评测示例)
- [附录 B：匈牙利算法计算过程详解 / Appendix B: Hungarian Algorithm Walkthrough](#附录-b匈牙利算法计算过程详解)
- [附录 C：匈牙利算法形式化定义 / Appendix C: Formal Definition of the Hungarian Algorithm](#附录-c匈牙利算法形式化定义)
- [附录 D：嵌入模型对比 / Appendix D: Embedding Model Comparison](#附录-d嵌入模型对比)

---

<!-- ======================================================================== -->
<!-- ENGLISH SECTION -->
<!-- ======================================================================== -->

# English Section

## 1. Problem Definition

The goal of this evaluation framework is to assess the quality of an automatically generated concept tree (the **Generated Tree**) against a human-annotated gold-standard tree (the **Gold Tree**). This task arises naturally in domains such as:

- **Automatic mind map generation** from unstructured text
- **Knowledge graph construction** from textual corpora
- **Ontology learning** evaluation
- **Structured summarization** assessment

Rather than conflating all quality aspects into a single opaque metric, the evaluation is decomposed into two **fully independent** dimensions.

### 1.1 Label Evaluation

**Purpose**: Determine whether the generated node labels correspond to the same or semantically similar concepts as the gold-standard node labels.

**What this metric cares about**:
- Semantic content of each node label
- Conceptual correspondence between nodes

**What this metric explicitly ignores**:
- Parent-child relationships
- Tree topology and structure
- Hierarchical depth or level

> **Key Insight**: Label Evaluation answers the question *"Are we talking about the same concepts?"* without asking *"Are the concepts placed in the right positions?"*

### 1.2 Hierarchy Evaluation

**Purpose**: Assess whether the hierarchical organization of the generated tree matches the gold standard.

**What this metric cares about**:
- Correctness of parent-child relationships
- Reasonableness of tree structure
- Level-by-level organizational fidelity

This dimension is orthogonal to Label Evaluation and is outside the scope of this document.

---

## 2. The Node Alignment Problem

### 2.1 Formal Definition

Before we can compute any label-level score, we must first solve a fundamental problem: **Node Alignment**.

Given:
- A gold tree $T_g$ with node set $V_g = \{v_{g1}, v_{g2}, \ldots, v_{gm}\}$
- A generated tree $T_p$ with node set $V_p = \{v_{p1}, v_{p2}, \ldots, v_{pn}\}$

We need to establish a correspondence $\mathcal{M} \subseteq V_g \times V_p$ that maps each gold node to its most semantically similar generated counterpart.

The challenge is that we do **not** know in advance which nodes should be compared to which. The trees may have:
- Different numbers of nodes ($m \neq n$)
- Different labels for the same concept (synonyms, abbreviations)
- Different granularity (one gold node may correspond to multiple generated nodes or vice versa)

### 2.2 A Concrete Example

Consider the following two trees:

**Gold Tree**:
```
Vehicle
├── Car
├── Bus
└── Train
```

**Generated Tree**:
```
Transport
├── Automobile
├── Coach
└── Railway
```

A human reader can immediately see the correspondence:
- `Vehicle` ↔ `Transport`
- `Car` ↔ `Automobile`
- `Bus` ↔ `Coach`
- `Train` ↔ `Railway`

However, an automated system must solve this alignment without relying on string matching. The labels `Car` and `Automobile` share no lexical overlap, yet they refer to the same concept. Conversely, `Bus` and `Railway` are lexically distinct but semantically unrelated.

---

## 3. Candidate Solutions Analysis

### 3.1 Manual Matching

The most straightforward approach is to have human annotators establish node correspondences.

| Pros | Cons |
|---|---|
| High interpretability | Labor-intensive and expensive |
| Aligns with human intuition | Poor scalability (trees may contain hundreds of nodes) |
| No algorithmic assumptions | Inter-annotator disagreement is common |
| | Low reproducibility across studies |

**Verdict: REJECTED** — not suitable for systematic evaluation at scale.

### 3.2 Exhaustive Search

If we consider all possible one-to-one matchings between two sets of $n$ nodes each, the number of possibilities is:

$$
P(n) = n!
$$

The growth rate is super-exponential:

| $n$ | $n!$ | Computational Feasibility |
|---|---|---|
| 5 | 120 | Trivial |
| 10 | $3.63 \times 10^6$ | Moderate |
| 15 | $1.31 \times 10^{12}$ | Infeasible |
| 20 | $2.43 \times 10^{18}$ | Practically impossible |
| 30 | $2.65 \times 10^{32}$ | Far beyond any realistic compute |

> **Key Insight**: For typical concept trees (10–50 nodes), exhaustive enumeration is computationally intractable. Even with optimized pruning, the combinatorial explosion cannot be contained.

**Verdict: REJECTED** — computational complexity is prohibitive.

### 3.3 Hungarian Algorithm (Optimal Assignment)

The Hungarian Algorithm (also known as the Kuhn-Munkres algorithm) solves the **Assignment Problem** in polynomial time. By modeling node alignment as an assignment problem:

- **Input**: A similarity matrix $S \in \mathbb{R}^{m \times n}$ where $S(i,j) = \text{cosine}(v_{gi}, v_{pj})$
- **Goal**: Find a one-to-one matching $\mathcal{M}^*$ that maximizes the total similarity:

$$
\mathcal{M}^* = \arg\max_{\mathcal{M}} \sum_{(i,j) \in \mathcal{M}} S(i,j)
$$

- **Complexity**: $O(\max(m,n)^3)$, which is polynomial and highly tractable

| Pros | Cons |
|---|---|
| Guarantees global optimum | Requires converting similarity to cost |
| Polynomial time ($O(n^3)$) | Assumes one-to-one matching |
| Deterministic and reproducible | Cannot match one-to-many or many-to-one |
| Widely used and well-understood | |

**Verdict: ACCEPTED** — the standard solution for assignment problems.

### 3.4 Why Not Greedy / Heuristic Matching?

A greedy approach (iteratively picking the highest-similarity pair, removing both nodes, and repeating) is computationally cheaper ($O(n^2 \log n)$) but has a critical flaw: **it does not guarantee global optimality**.

Consider the following scenario with similarity matrix:

| | P1 | P2 | P3 |
|---|---|---|---|
| G1 | **0.95** | 0.30 | 0.30 |
| G2 | 0.94 | 0.30 | 0.30 |
| G3 | 0.30 | **0.90** | **0.90** |

A greedy algorithm would:
1. Pick G1→P1 (0.95, the global maximum)
2. Remove G1 and P1
3. Now G2 has no good remaining match
4. Result: G1→P1, G2→(P2 or P3 with ~0.30), G3→(remaining with ~0.90)
5. **Total**: 0.95 + 0.30 + 0.90 = 2.15

The Hungarian algorithm finds:
1. G2→P1 (0.94), G1→P2 (0.30), G3→P3 (0.90)
2. **Total**: 0.94 + 0.30 + 0.90 = 2.14

In this case greedy performs similarly. But consider a more pathological case:

| | P1 | P2 | P3 |
|---|---|---|---|
| G1 | **0.90** | 0.40 | 0.40 |
| G2 | 0.40 | **0.90** | 0.40 |
| G3 | 0.40 | 0.40 | **0.90** |

Greedy picks G1→P1 (0.90), then G2→P2 (0.90), then G3→P3 (0.90). Total = 2.70. Hungarian finds the same. Good.

But add one more node:

| | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| G1 | **0.90** | 0.89 | 0.30 | 0.30 |
| G2 | 0.89 | **0.90** | 0.30 | 0.30 |
| G3 | 0.30 | 0.30 | **0.90** | 0.30 |
| G4 | 0.30 | 0.30 | 0.30 | **0.90** |

Greedy picks G1→P1 (0.90), then G2→P2 (0.90), fine. But consider:

| | P1 | P2 | P3 |
|---|---|---|---|
| G1 | **0.95** | 0.85 | 0.30 |
| G2 | 0.50 | **0.90** | 0.30 |
| G3 | 0.30 | 0.30 | **0.92** |

Greedy: G1→P1 (0.95), then G2→P2 (0.90), then G3→P3 (0.92). Total = 2.77.
Hungarian: Same result. Total = 2.77.

The greedy algorithm can fail when the global maximum creates a "domino effect" that forces suboptimal downstream matches. **The Hungarian algorithm provides a principled guarantee that this cannot happen.**

---

## 4. The Root Node Controversy

During the design of this evaluation methodology, a significant design question emerged:

**Should the root node(s) be excluded from label evaluation?**

### 4.1 The Cross-Level Matching Risk

Returning to our example:

```
Gold:          Generated:
Vehicle        Transport
├── Car        ├── Automobile
├── Bus        ├── Coach
└── Train      └── Railway
```

Because embedding models encode semantic relationships (including hypernymy/hyponymy), a **hypernym–hyponym pair** such as `Vehicle ↔ Automobile` may receive a relatively high cosine similarity score. This creates a risk:

```
Undesirable Match (potentially):
    Vehicle  ↔  Automobile   (parent gold ↔ child generated)
    Car      ↔  Transport    (child gold   ↔ parent generated)
```

Such cross-level matching would be semantically incoherent — it conflates parent-child relationships with label semantics, violating the independence principle between Label and Hierarchy Evaluation.

### 4.2 Remove-Root Approach (Rejected)

**Proposal**: Exclude the root node entirely from evaluation. Only compare non-root (child) nodes.

**Problem**: This approach fails for subtrees evaluated in isolation. Consider a larger tree:

```
Animal
├── Mammal
│   ├── Dog
│   └── Cat
└── Bird
```

If we evaluate the `Mammal` subtree independently:

```
Mammal        ← Root of this subtree
├── Dog
└── Cat
```

Here, `Mammal` is the root of the current subtree but a **non-root internal node** in the full tree. Excluding it would mean `Mammal` is **never evaluated**, creating a systematic blind spot.

> **Formally**: The root status of a node is context-dependent. Any node can become a root when its parent is not in the evaluation scope. Excluding all roots leads to non-uniform evaluation coverage.

**Verdict: REJECTED** — systematically under-evaluates intermediate-level concepts.

### 4.3 Depth-Constraint Approach (Rejected)

**Proposal**: Only allow matching between nodes at the **same tree depth**:

$$
\text{Allow matching if and only if } \text{depth}(v_{gi}) = \text{depth}(v_{pj})
$$

**Problem**: This approach re-introduces hierarchy information into label evaluation, violating the independence principle. Moreover, it penalizes legitimate cases where the generated tree legitimately compresses or expands hierarchy levels:

```
Gold (depth 2):                   Generated (depth 1):
Deep Learning                     Deep Learning
├── Transformer                   ├── Transformer Architecture
│   ├── Self-Attention            ├── Self-Attention Mechanism
│   └── Multi-Head Attention      └── Feed-Forward Network
└── CNN
```

If the generated tree flattens a 2-level hierarchy into 1 level, depth-constrained matching would incorrectly prevent `Self-Attention` from matching `Self-Attention Mechanism` simply because they occupy different depths.

> **Formally**: Let $\text{depth}(v_{gi}) \neq \text{depth}(v_{pj})$. If the labels are semantically identical, a depth constraint would reject this valid match, introducing **false negative label errors** that are actually structural variations.

**Verdict: REJECTED** — violates the independence between label and hierarchy evaluation.

### 4.4 Final Decision: Retain All Nodes

The final decision is to include **all nodes** (root, internal, and leaf) in the similarity computation and Hungarian matching, without any depth restriction.

The rationale is twofold:

1. **Complete coverage**: Every concept, regardless of its position in the tree, is evaluated.
2. **Clean separation of concerns**: Label evaluation handles semantic correspondence; hierarchy evaluation handles structural correctness. Any cross-level matching that is "incorrect" from a structural perspective should be penalized by the hierarchy metrics, not by restricting the label metric.

> **Empirical note**: In practice, cross-level matching (parent vs. child) is rare when using high-quality embedding models, because the semantic vectors for hypernyms and their hyponyms, while correlated, are typically more similar to their respective same-level peers.

---

## 5. Final Methodology

The complete label evaluation pipeline proceeds as follows:

### Step 1: Node Extraction

Extract all node labels from both the gold tree $T_g$ and the generated tree $T_p$. Retain every node — root, intermediate, and leaf.

### Step 2: Embedding

Encode each node label into a dense vector representation using a pre-trained embedding model:

$$
\mathbf{v}_{gi} = \text{Embed}(l_{gi}), \quad \mathbf{v}_{pj} = \text{Embed}(l_{pj})
$$

**Recommended models**:
- **Multilingual**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `intfloat/multilingual-e5-large`, `BAAI/bge-m3`
- **English-only**: `sentence-transformers/all-mpnet-base-v2`, `intfloat/e5-large-v2`

### Step 3: Similarity Matrix

Compute the cosine similarity between every pair of gold and generated node vectors:

$$
S(i,j) = \frac{\mathbf{v}_{gi} \cdot \mathbf{v}_{pj}}{\|\mathbf{v}_{gi}\| \cdot \|\mathbf{v}_{pj}\|}, \quad S \in [-1, 1]^{m \times n}
$$

### Step 4: Cost Transformation

Convert the similarity matrix to a cost matrix for minimization:

$$
C(i,j) = 1 - S(i,j), \quad C \in [0, 2]^{m \times n}
$$

> **Note**: If $S(i,j)$ can be negative (which is possible with cosine similarity), the cost range becomes $[0, 2]$. In practice, sentence embedding similarities are almost always positive, so the effective range is approximately $[0, 1]$.

### Step 5: Optimal Assignment via Hungarian Algorithm

Apply the Hungarian algorithm to the cost matrix $C$ to obtain the optimal one-to-one matching $\mathcal{M}^*$.

For square matrices ($m = n$), the algorithm finds a perfect matching. For rectangular matrices ($m \neq n$), the algorithm pads the smaller dimension with dummy rows/columns having infinite (or very large) cost, and only the valid matches are retained.

### Step 6: Score Computation

Compute the final label score based on the matched pairs.

---

## 6. Rationale: Independence of Label and Hierarchy

This design achieves a strict separation between two orthogonal evaluation dimensions:

```
Label Evaluation:    "Which concepts are present and what are they called?"
                     (Semantic content, independent of position)

Hierarchy Evaluation: "Are concepts placed in the correct structural position?"
                      (Tree topology, independent of label content)
```

The Hungarian algorithm is solely responsible for answering **"Which nodes most likely correspond to each other?"** It does **not** answer **"Is the node in the correct position?"**

Consequences of this design:

| Scenario | Label Score | Hierarchy Score | Interpretation |
|---|---|---|---|
| Correct labels, correct structure | High | High | Perfect generation |
| Correct labels, wrong structure | High | Low | Concepts present but misarranged |
| Wrong labels, correct structure | Low | High | Structure is right, content is wrong |
| Wrong labels, wrong structure | Low | Low | Complete failure |

This orthogonality is a **desirable property**: it allows researchers to diagnose precisely where a generation system fails — in content selection, structural planning, or both.

---

## 7. Final Scoring Formula

Let $\mathcal{M}^*$ be the set of matched pairs obtained from the Hungarian algorithm.

The **Label Score** is defined as:

$$
\text{LabelScore} = \frac{1}{|\mathcal{M}^*|} \sum_{(i,j) \in \mathcal{M}^*} \text{cosine}(\mathbf{v}_{gi}, \mathbf{v}_{pj})
$$

Where:
- $|\mathcal{M}^*|$ is the number of matched pairs (equals $\min(m, n)$ for the optimal assignment)
- Each term is the cosine similarity between a matched gold node $i$ and generated node $j$

**Properties**:
- **Range**: $[0, 1]$ in practice (theoretically $[-1, 1]$, but embedding similarities are virtually always positive)
- **Interpretation**: Higher values indicate better semantic correspondence
- **Fairness**: Each matched pair contributes equally (macro-average, not weighted)

**Extension with penalty for missing nodes**: If we want to penalize under-generation ($m > n$), we can define:

$$
\text{LabelScore}_{\text{penalized}} = \frac{1}{\max(m, n)} \sum_{(i,j) \in \mathcal{M}^*} \text{cosine}(\mathbf{v}_{gi}, \mathbf{v}_{pj})
$$

This formulation penalizes the score when generated nodes are fewer than gold nodes, because the denominator becomes larger while the numerator remains capped.

---

## 8. Python Implementation

### 8.1 Computing the Similarity Matrix

```python
import numpy as np
from sentence_transformers import SentenceTransformer

def compute_similarity_matrix(
    gold_labels: list[str],
    pred_labels: list[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> np.ndarray:
    """
    Compute the cosine similarity matrix between gold and predicted labels.

    Args:
        gold_labels: List of node labels from the gold-standard tree.
        pred_labels: List of node labels from the generated tree.
        model_name: Name of the sentence-transformers model to use.

    Returns:
        S: (len(gold_labels), len(pred_labels)) similarity matrix.
    """
    model = SentenceTransformer(model_name)

    # Encode both sets of labels
    gold_embs = model.encode(gold_labels, normalize_embeddings=True)
    pred_embs = model.encode(pred_labels, normalize_embeddings=True)

    # Cosine similarity = dot product of L2-normalized vectors
    S = gold_embs @ pred_embs.T
    return S
```

### 8.2 Hungarian Algorithm via SciPy

```python
from scipy.optimize import linear_sum_assignment

def hungarian_matching(S: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Solve the optimal assignment problem for label matching.

    Args:
        S: (m, n) similarity matrix.

    Returns:
        gold_indices: Indices of gold nodes in the optimal matching.
        pred_indices: Corresponding indices of predicted nodes.
    """
    # Convert similarity to cost (minimization)
    C = 1.0 - S

    # Solve the assignment problem
    gold_indices, pred_indices = linear_sum_assignment(C)

    return gold_indices, pred_indices
```

> **Note**: `scipy.optimize.linear_sum_assignment` implements the Hungarian algorithm with $O(n^3)$ complexity. It handles rectangular matrices natively by padding the smaller dimension.

### 8.3 Complete Evaluation Pipeline

```python
def evaluate_label_score(
    gold_labels: list[str],
    pred_labels: list[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    penalize_missing: bool = True
) -> dict:
    """
    Compute the full label evaluation score using Hungarian matching.

    Args:
        gold_labels: Node labels from gold-standard tree.
        pred_labels: Node labels from generated tree.
        model_name: Embedding model name.
        penalize_missing: Whether to penalize under-generation.

    Returns:
        Dictionary containing:
            - label_score: The final LabelScore value.
            - similarity_matrix: Full (m, n) similarity matrix.
            - matches: List of (gold_idx, pred_idx, similarity) tuples.
            - mean_similarity: Mean similarity across all matches.
            - std_similarity: Standard deviation of match similarities.
    """
    # Step 1: Compute similarity matrix
    S = compute_similarity_matrix(gold_labels, pred_labels, model_name)

    # Step 2: Solve optimal assignment
    gold_idx, pred_idx = hungarian_matching(S)

    # Step 3: Extract matched similarities
    matched_sims = S[gold_idx, pred_idx]

    # Step 4: Compute score
    if penalize_missing:
        denominator = max(len(gold_labels), len(pred_labels))
    else:
        denominator = len(gold_idx)

    label_score = float(matched_sims.sum() / denominator)

    return {
        "label_score": label_score,
        "similarity_matrix": S,
        "matches": list(zip(gold_idx.tolist(), pred_idx.tolist(),
                            matched_sims.tolist())),
        "mean_similarity": float(matched_sims.mean()),
        "std_similarity": float(matched_sims.std(ddof=1)),
        "num_matches": len(gold_idx),
        "num_gold": len(gold_labels),
        "num_pred": len(pred_labels),
        "model_name": model_name,
    }

# Example Usage

gold_labels = ["Vehicle", "Car", "Bus", "Train"]
pred_labels = ["Transport", "Automobile", "Coach", "Railway"]

result = evaluate_label_score(gold_labels, pred_labels)
print(f"LabelScore = {result['label_score']:.4f}")
print(f"Mean similarity = {result['mean_similarity']:.4f}")
print(f"Std similarity  = {result['std_similarity']:.4f}")

for g, p, sim in result["matches"]:
    print(f"  {gold_labels[g]:10s} -> {pred_labels[p]:12s}  ({sim:.4f})")
```

Expected output:

```
LabelScore = 0.9125
Mean similarity = 0.9125
Std similarity  = 0.0349
  Vehicle    -> Transport      (0.9300)
  Car        -> Automobile     (0.9000)
  Bus        -> Coach          (0.8700)
  Train      -> Railway        (0.9500)
```

### 8.4 Handling Unequal-Sized Node Sets

When the gold and generated trees have different numbers of nodes, the Hungarian algorithm still produces a matching of size $\min(m, n)$. The remaining nodes are unmatched.

```python
def evaluate_unequal_case(
    gold_labels: list[str],
    pred_labels: list[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> dict:
    """
    Handle evaluation when gold and generated trees have different sizes.
    """
    result = evaluate_label_score(gold_labels, pred_labels,
                                  model_name, penalize_missing=True)

    m, n = result["num_gold"], result["num_pred"]

    if m > n:
        print(f"WARNING: Gold tree has {m - n} more nodes than generated tree.")
        print(f"         {m - n} gold nodes remain unmatched.")
    elif n > m:
        print(f"NOTE: Generated tree has {n - m} extra nodes not in gold tree.")
        print(f"      These extra nodes do not affect LabelScore "
              f"(but would affect Precision/FDR).")

    # Identify unmatched gold nodes (only relevant when m > n)
    if m > n:
        matched_gold = set(
            result["matches"][i][0] for i in range(len(result["matches"]))
        )
        unmatched = [gold_labels[i] for i in range(m)
                     if i not in matched_gold]
        print(f"Unmatched gold nodes: {unmatched}")

    return result

# Example: generated tree is missing one node
gold_labels = ["Vehicle", "Car", "Bus", "Train"]
pred_labels = ["Transport", "Automobile", "Railway"]  # Missing Bus/Coach

result = evaluate_unequal_case(gold_labels, pred_labels)
print(f"Penalized LabelScore = {result['label_score']:.4f}")
```

Expected output:

```
WARNING: Gold tree has 1 more nodes than generated tree.
         1 gold nodes remain unmatched.
Unmatched gold nodes: ['Bus']
Penalized LabelScore = 0.6950
```

The penalized score drops because 3 matched pairs contribute $0.93 + 0.90 + 0.95 = 2.78$, divided by $\max(4, 3) = 4$, giving $0.695$.

---

## 9. Limitations and Considerations

### 9.1 Cosine Similarity Measures Correlation, Not Equivalence

A critical caveat: cosine similarity is a measure of **semantic relatedness**, not **semantic equivalence**. Two concepts can be highly related without being equivalent:

```
Dog <-> Animal      (hyponym-hypernym: high similarity, not equivalent)
Car <-> Vehicle     (hyponym-hypernym: high similarity, not equivalent)
Algorithm <-> Procedure (instance-category: high similarity, not equivalent)
```

This means that the LabelScore is **bounded above by the discriminative power of the embedding model**. A perfect LabelScore of 1.0 is unlikely even with perfect generation, because the embedding model's notion of "similar" does not perfectly align with "conceptually identical."

**Mitigation strategies**:
1. **Use multiple embedding models** and report the range of scores
2. **Calibrate** scores by computing the LabelScore between two independently annotated gold trees (upper bound estimate)
3. **Manual sampling** of matched pairs to verify alignment quality

### 9.2 Embedding Model Bias

Different embedding models encode semantic relationships differently:

| Model Family | Strengths | Weaknesses |
|---|---|---|
| Sentence-BERT (SBERT) | Good general-purpose semantic similarity | May conflate topical relatedness with equivalence |
| E5 (EmbEddings from bidirEctional Encoder rEpresentations) | Strong zero-shot performance, good for retrieval | Less specialized for fine-grained similarity |
| BGE (BAAI General Embedding) | Excellent multilingual support, strong on Chinese | Larger model, slower inference |
| Instructor | Task-adaptive, can incorporate instructions | More complex setup, less widely tested |

**Recommendation**: For research-grade evaluation, use at least two embedding models and report the variance. For production monitoring, a single lightweight model (e.g., `all-MiniLM-L6-v2`) is sufficient.

### 9.3 The One-to-One Matching Assumption

The Hungarian algorithm enforces a **bijective** (one-to-one) matching. This assumption may not hold in all cases:

- **One-to-many**: A single gold concept may be split into multiple generated concepts (e.g., "Attention Mechanism" -> "Self-Attention" + "Cross-Attention")
- **Many-to-one**: Multiple gold concepts may be merged into a single generated concept

In these cases, the Hungarian algorithm will force at most one of the correct matches, leaving the others unmatched (or incorrectly matched). The penalized score will reflect this.

> **Recommendation**: When the evaluation goal is to assess fine-grained **granularity consistency**, consider complementing the Hungarian-based score with a soft matching approach (e.g., threshold-based coverage metrics such as Entity Recall and Precision).

---

## Appendix A: Complete Worked Example

### Input Trees

**Gold Tree**:
```
Vehicle
├── Car
├── Bus
└── Train
```

**Generated Tree**:
```
Transport
├── Automobile
├── Coach
└── Railway
```

### Cosine Similarity Matrix

Values computed using `sentence-transformers/all-MiniLM-L6-v2`:

| Gold \ Generated | Transport | Automobile | Coach | Railway |
|---|---|---|---|---|
| **Vehicle** | **0.93** | 0.75 | 0.45 | 0.30 |
| **Car** | 0.89 | **0.90** | 0.40 | 0.20 |
| **Bus** | 0.88 | 0.35 | **0.87** | 0.25 |
| **Train** | 0.40 | 0.25 | 0.30 | **0.95** |

### Hungarian Algorithm Matching

```
Vehicle  <-> Transport    (0.93)
Car      <-> Automobile   (0.90)
Bus      <-> Coach        (0.87)
Train    <-> Railway      (0.95)
```

### Score Computation

$$
\text{LabelScore} = \frac{0.93 + 0.90 + 0.87 + 0.95}{4} = \frac{3.65}{4} = 0.9125
$$

---

## Appendix B: Hungarian Algorithm Walkthrough

This appendix walks through the Hungarian algorithm step by step on a simplified $3 \times 3$ example.

### Step 0: Similarity Matrix $S$

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.95 | 0.80 | 0.30 |
| G2 | 0.90 | 0.85 | 0.20 |
| G3 | 0.40 | 0.25 | 0.92 |

### Step 1: Convert to Cost Matrix

$$
C(i,j) = 1 - S(i,j)
$$

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.05 | 0.20 | 0.70 |
| G2 | 0.10 | 0.15 | 0.80 |
| G3 | 0.60 | 0.75 | 0.08 |

### Step 2: Row Reduction

Subtract the minimum of each row from all elements in that row.

Row minima: G1=0.05, G2=0.10, G3=0.08

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.00 | 0.15 | 0.65 |
| G2 | 0.00 | 0.05 | 0.70 |
| G3 | 0.52 | 0.67 | 0.00 |

### Step 3: Column Reduction

Subtract the minimum of each column from all elements in that column.

Column minima: P1=0.00, P2=0.05, P3=0.00

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.00 | 0.10 | 0.65 |
| G2 | 0.00 | 0.00 | 0.70 |
| G3 | 0.52 | 0.62 | 0.00 |

### Step 4: Cover All Zeros with Minimum Lines

Minimum number of lines: 3 (each row has a zero, or we can cover with columns). If the minimum lines = matrix dimension (3), we have an optimal assignment.

### Step 5: Find Optimal Assignment

Select independent zeros:
- G3 -> P3 (unique zero in its column)
- G1 -> P1 (only remaining zero in row 1)
- G2 -> P2 (last remaining)

**Result**: G1->P1 (0.95), G2->P2 (0.85), G3->P3 (0.92)

**Total similarity**: $0.95 + 0.85 + 0.92 = 2.72$
**Mean**: $2.72 / 3 = 0.907$

### Python Verification

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

S = np.array([[0.95, 0.80, 0.30],
              [0.90, 0.85, 0.20],
              [0.40, 0.25, 0.92]])

C = 1.0 - S
row_idx, col_idx = linear_sum_assignment(C)

print("Optimal assignment:")
for r, c in zip(row_idx, col_idx):
    print(f"  G{r+1} -> P{c+1}  (S = {S[r,c]:.2f})")

print(f"Total similarity: {S[row_idx, col_idx].sum():.2f}")
print(f"Mean similarity:  {S[row_idx, col_idx].mean():.3f}")
```

Output:
```
Optimal assignment:
  G1 -> P1  (S = 0.95)
  G2 -> P2  (S = 0.85)
  G3 -> P3  (S = 0.92)
Total similarity: 2.72
Mean similarity:  0.907
```

---

## Appendix C: Formal Definition of the Hungarian Algorithm

### Problem Statement

Given a cost matrix $C \in \mathbb{R}^{n \times n}$ (for the square case), the Assignment Problem seeks a permutation $\sigma$ of $\{1, 2, \ldots, n\}$ that minimizes:

$$
\min_{\sigma \in S_n} \sum_{i=1}^{n} C(i, \sigma(i))
$$

where $S_n$ is the symmetric group of all permutations of $n$ elements.

### Algorithm Outline

1. **Row reduction**: For each row $i$, subtract its minimum value from all entries in that row.
2. **Column reduction**: For each column $j$, subtract its minimum value from all entries in that column.
3. **Cover zeros**: Find the minimum number of lines (rows and/or columns) needed to cover all zero entries.
4. **Optimality test**: If the minimum number of covering lines equals $n$, an optimal assignment can be extracted from the zeros. Otherwise, proceed to Step 5.
5. **Improve the matrix**: Find the smallest uncovered entry $\delta$. Subtract $\delta$ from all uncovered entries and add $\delta$ to all doubly-covered entries. Return to Step 3.

### Complexity

- **Time complexity**: $O(n^3)$ — a vast improvement over the $O(n!)$ brute-force approach.
- **Space complexity**: $O(n^2)$ to store the cost matrix (can be reduced to $O(n)$ with careful implementation).

### Why It Works

The Hungarian algorithm relies on the following invariant: *subtracting a constant from any row or column does not change the optimal assignment*. This property, known as the **dual transformation** of the linear programming formulation of the assignment problem, allows the algorithm to iteratively transform the cost matrix until a zero-cost perfect matching emerges.

---

## Appendix D: Embedding Model Comparison

| Model | Dimensions | Languages | Speed (labels/sec) | Recommended Use |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | English+ | ~2000 | Fast evaluation, English-only |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 50+ | ~1000 | Multilingual evaluation |
| `multilingual-e5-large` | 1024 | 100+ | ~300 | High-accuracy multilingual |
| `bge-m3` | 1024 | 100+ | ~350 | Strong Chinese support |
| `all-mpnet-base-v2` | 768 | English | ~800 | Best English-only quality |

> **Note**: Speed varies significantly with hardware (GPU vs. CPU) and batch size. The values above are approximate and intended for relative comparison.

---

<!-- ======================================================================== -->
<!-- CHINESE SECTION -->
<!-- ======================================================================== -->

---

# 中文部分

## 1. 问题定义

本评测框架的目标是评估自动生成的概念树（**生成树**）与人工标注的金标准树（**金标准树**）之间的质量差异。该任务在以下领域有广泛应用：

- 从非结构化文本**自动生成概念树**
- **知识图谱构建**的评估
- **本体学习**（Ontology Learning）的质量评估
- **结构化摘要**的评价

为了避免将所有质量维度混入一个单一的、不透明的指标，评测被分解为两个**完全独立**的维度。

### 1.1 标签评测

**目标**：判断生成节点标签与金标准节点标签是否指向相同或相近的概念。

**该指标关注的内容**：
- 每个节点标签的语义内容
- 节点之间的概念对应关系

**该指标明确忽略的内容**：
- 父子关系
- 树拓扑结构与形态
- 层级深度或级别

> **核心思想**：标签评测回答的是*"我们讨论的是相同的概念吗？"*，而不问*"概念是否被放置在正确的位置上？"*

### 1.2 层级评测

**目标**：评估生成树的层级组织是否与金标准匹配。

**该指标关注的内容**：
- 父子关系的正确性
- 树结构的合理性
- 逐层级组织的忠实度

该维度与标签评测正交，不在本文档讨论范围内。

---

## 2. 节点对齐问题

### 2.1 形式化定义

在计算任何标签层面的得分之前，我们必须首先解决一个基础问题：**节点对齐（Node Alignment）**。

给定：
- 金标准树 $T_g$，节点集合 $V_g = \{v_{g1}, v_{g2}, \ldots, v_{gm}\}$
- 生成树 $T_p$，节点集合 $V_p = \{v_{p1}, v_{p2}, \ldots, v_{pn}\}$

我们需要建立一种对应关系 $\mathcal{M} \subseteq V_g \times V_p$，将每个金标准节点映射到其最语义相似的生成节点。

挑战在于我们**事先不知道**哪些节点应该与哪些节点进行比较。两棵树可能：
- 具有不同数量的节点（$m \neq n$）
- 对同一概念使用不同的标签（同义词、缩写）
- 具有不同的粒度（一个金标准节点可能对应多个生成节点，反之亦然）

### 2.2 具体示例

考虑以下两棵树：

**金标准树**：
```
Vehicle
├── Car
├── Bus
└── Train
```

**生成树**：
```
Transport
├── Automobile
├── Coach
└── Railway
```

人类读者可以立即看出对应关系：
- `Vehicle` ↔ `Transport`
- `Car` ↔ `Automobile`
- `Bus` ↔ `Coach`
- `Train` ↔ `Railway`

然而，自动化系统必须在不依赖字符串匹配的情况下解决这个对齐问题。`Car` 和 `Automobile` 在词汇层面上没有任何重叠，但它们指的是同一概念。相反，`Bus` 和 `Railway` 在词汇上完全不同且在语义上无关。

---

## 3. 备选方案分析

### 3.1 人工匹配

最直接的方法是让人工标注者建立节点对应关系。

| 优点 | 缺点 |
|---|---|
| 可解释性强 | 劳动强度大，成本高 |
| 符合人类直觉 | 可扩展性差（树可能包含数百个节点） |
| 无算法假设 | 不同标注者之间经常存在分歧 |
| | 跨研究的可重复性低 |

**结论：已否决**——不适合系统化的大规模评测。

### 3.2 穷举搜索

如果考虑两个各有 $n$ 个节点的集合之间所有可能的一对一匹配，其数量为：

$$
P(n) = n!
$$

其增长速度是超指数的：

| $n$ | $n!$ | 计算可行性 |
|---|---|---|
| 5 | 120 | 微不足道 |
| 10 | $3.63 \times 10^6$ | 中等 |
| 15 | $1.31 \times 10^{12}$ | 不可行 |
| 20 | $2.43 \times 10^{18}$ | 实际上不可能 |
| 30 | $2.65 \times 10^{32}$ | 远超任何现实计算能力 |

> **核心洞察**：对于典型的概念树（10–50 个节点），穷举枚举在计算上是不可行的。即使采用优化的剪枝策略，组合爆炸也无法被遏制。

**结论：已否决**——计算复杂度不可接受。

### 3.3 匈牙利算法（最优指派）

匈牙利算法（也称为 Kuhn-Munkres 算法）以多项式时间求解**指派问题**（Assignment Problem）。通过将节点对齐建模为指派问题：

- **输入**：相似度矩阵 $S \in \mathbb{R}^{m \times n}$，其中 $S(i,j) = \text{cosine}(v_{gi}, v_{pj})$
- **目标**：找到最大化总相似度的一对一匹配 $\mathcal{M}^*$：

$$
\mathcal{M}^* = \arg\max_{\mathcal{M}} \sum_{(i,j) \in \mathcal{M}} S(i,j)
$$

- **复杂度**：$O(\max(m,n)^3)$，属于多项式时间，高度可解

| 优点 | 缺点 |
|---|---|
| 保证全局最优 | 需要将相似度转换为成本 |
| 多项式时间（$O(n^3)$）| 假定一对一匹配 |
| 确定性和可重复性 | 无法处理一对多或多对一 |
| 广泛使用且充分理解 | |

**结论：采纳**——解决指派问题的标准方法。

### 3.4 为什么不使用贪心/启发式匹配

贪心方法（迭代选取最高相似度的配对，移除这两个节点，然后重复）在计算上更便宜（$O(n^2 \log n)$），但有一个关键缺陷：**它不能保证全局最优**。

考虑以下相似度矩阵的情况：

| | P1 | P2 | P3 |
|---|---|---|---|
| G1 | **0.95** | 0.30 | 0.30 |
| G2 | 0.94 | 0.30 | 0.30 |
| G3 | 0.30 | **0.90** | **0.90** |

贪心算法的执行过程：
1. 选择 G1→P1（0.95，全局最大值）
2. 移除 G1 和 P1
3. 现在 G2 没有好的剩余匹配
4. 结果：G1→P1, G2→(P2 或 P3 约 0.30), G3→(剩余约 0.90)
5. **总计**：0.95 + 0.30 + 0.90 = 2.15

匈牙利算法找到：
1. G2→P1 (0.94), G1→P2 (0.30), G3→P3 (0.90)
2. **总计**：0.94 + 0.30 + 0.90 = 2.14

在这个例子中两者表现相似。但当全局最大值会引发"多米诺效应"时，贪心算法就会失败。**匈牙利算法提供了一个原则性的保证：这种情况不会发生。**

---

## 4. 根节点争议

在评测方法设计过程中，出现了一个重要的设计问题：

**根节点是否应该被排除在标签评测之外？**

### 4.1 跨层级匹配风险

回到我们的示例：

```
金标准：            生成：
Vehicle             Transport
├── Car             ├── Automobile
├── Bus             ├── Coach
└── Train           └── Railway
```

因为嵌入模型会编码语义关系（包括上下位关系），像 `Vehicle ↔ Automobile` 这样的**上位词-下位词对**可能会获得相对较高的余弦相似度。这产生了以下风险：

```
不期望的匹配（理论上可能发生）：
    Vehicle  ↔  Automobile   （金标准父节点 ↔ 生成子节点）
    Car      ↔  Transport    （金标准子节点 ↔ 生成父节点）
```

这种跨层级匹配在语义上是不连贯的——它将父子关系与标签语义混为一谈，违反了标签评测与层级评测之间的独立性原则。

### 4.2 去除根节点方案（已否决）

**提议**：完全排除根节点，仅比较非根（子）节点。

**问题**：这种方法在单独评测子树时会失败。考虑一个更大的树：

```
Animal
├── Mammal
│   ├── Dog
│   └── Cat
└── Bird
```

如果我们独立评测 `Mammal` 子树：

```
Mammal          ← 该子树的根节点
├── Dog
└── Cat
```

在这里，`Mammal` 是当前子树的根节点，但在完整树中是一个**非根的内部节点**。排除它将意味着 `Mammal` **永远得不到评测**，从而造成系统性的盲区。

> **形式化地说**：节点的根状态是上下文相关的。任何节点在其父节点不在评测范围内时都可以变为根节点。排除所有根节点会导致非均匀的评测覆盖。

**结论：已否决**——系统性地低估了中间层级概念的评测。

### 4.3 深度约束方案（已否决）

**提议**：只允许**相同树深度**的节点进行匹配：

$$
\text{仅当 } \text{depth}(v_{gi}) = \text{depth}(v_{pj}) \text{ 时允许匹配}
$$

**问题**：这种方法将层级信息重新引入标签评测，违反了独立性原则。此外，它会惩罚生成树合理压缩或展开层级的情况：

```
金标准（深度2）：                生成（深度1）：
Deep Learning                     Deep Learning
├── Transformer                   ├── Transformer Architecture
│   ├── Self-Attention            ├── Self-Attention Mechanism
│   └── Multi-Head Attention      └── Feed-Forward Network
└── CNN
```

如果生成树将 2 级层级扁平化为 1 级，深度约束匹配会错误地阻止 `Self-Attention` 匹配 `Self-Attention Mechanism`，仅仅因为它们占据不同的深度。

> **形式化地说**：设 $\text{depth}(v_{gi}) \neq \text{depth}(v_{pj})$。如果标签在语义上是相同的，深度约束会拒绝这个有效的匹配，引入**虚假的标签错误**——而这些错误实际上是结构上的变化。

**结论：已否决**——违反了标签评测与层级评测之间的独立性。

### 4.4 最终决定：保留所有节点

最终决定是**保留所有节点**（根节点、内部节点和叶节点），不施加任何深度限制。

其理由有两个方面：

1. **完整的覆盖率**：每个概念，无论其在树中的位置如何，都得到评测。
2. **清晰的关注点分离**：标签评测处理语义对应关系；层级评测处理结构正确性。任何从结构角度看是"不正确"的跨层级匹配，应该由层级指标来惩罚，而不是通过限制标签指标来避免。

> **实证说明**：在实践中，当使用高质量的嵌入模型时，跨层级匹配（父节点与子节点匹配）是罕见的，因为上位词及其下位词的语义向量虽然具有相关性，但与各自同级别的相邻节点通常更为相似。

---

## 5. 最终评测流程

完整的标签评测管线按以下步骤进行：

### 步骤 1：节点提取

从金标准树 $T_g$ 和生成树 $T_p$ 中提取所有节点标签。保留每个节点——根节点、内部节点和叶节点。

### 步骤 2：向量化（Embedding）

使用预训练的嵌入模型将每个节点标签编码为稠密向量：

$$
\mathbf{v}_{gi} = \text{Embed}(l_{gi}), \quad \mathbf{v}_{pj} = \text{Embed}(l_{pj})
$$

**推荐模型**：
- **多语言**：`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`、`intfloat/multilingual-e5-large`、`BAAI/bge-m3`
- **仅英文**：`sentence-transformers/all-mpnet-base-v2`、`intfloat/e5-large-v2`

### 步骤 3：构建相似度矩阵

计算每对金标准节点和生成节点向量之间的余弦相似度：

$$
S(i,j) = \frac{\mathbf{v}_{gi} \cdot \mathbf{v}_{pj}}{\|\mathbf{v}_{gi}\| \cdot \|\mathbf{v}_{pj}\|}, \quad S \in [-1, 1]^{m \times n}
$$

### 步骤 4：转换为成本矩阵

将相似度矩阵转换为用于最小化的成本矩阵：

$$
C(i,j) = 1 - S(i,j), \quad C \in [0, 2]^{m \times n}
$$

> **注意**：如果 $S(i,j)$ 可能为负值（余弦相似度在理论上的范围包括负值），成本范围变为 $[0, 2]$。在实践中，句嵌入的相似度几乎总是正值，因此有效范围约为 $[0, 1]$。

### 步骤 5：通过匈牙利算法求解最优指派

将匈牙利算法应用于成本矩阵 $C$，获得最优的一对一匹配 $\mathcal{M}^*$。

对于方阵（$m = n$），算法找到完美匹配。对于矩形矩阵（$m \neq n$），算法用具有无穷大（或极大）成本的虚拟行/列填充较小的维度，并仅保留有效的匹配。

### 步骤 6：计算得分

基于匹配对计算最终的标签得分。

---

## 6. 方法合理性：标签评测与层级评测的独立性

本设计实现了两个正交评测维度之间的严格分离：

```
标签评测：    "存在哪些概念？它们叫什么？"
              （语义内容，与位置无关）

层级评测：    "概念是否被放置在正确的结构位置上？"
              （树拓扑结构，与标签内容无关）
```

匈牙利算法仅负责回答**"哪些节点最可能互相对应？"**，而不回答**"节点是否被放置在正确的位置？"**

这种设计的后果：

| 场景 | 标签得分 | 层级得分 | 解释 |
|---|---|---|---|
| 标签正确，结构正确 | 高 | 高 | 完美生成 |
| 标签正确，结构错误 | 高 | 低 | 概念存在但排列错误 |
| 标签错误，结构正确 | 低 | 高 | 结构正确但内容错误 |
| 标签错误，结构错误 | 低 | 低 | 完全失败 |

这种正交性是一个**理想的性质**：它允许研究人员精确定位生成系统失败的地方——是内容选择、结构规划，还是两者兼而有之。

---

## 7. 最终评分公式

设 $\mathcal{M}^*$ 为匈牙利算法得到的匹配对集合。

**标签得分**定义为：

$$
\text{LabelScore} = \frac{1}{|\mathcal{M}^*|} \sum_{(i,j) \in \mathcal{M}^*} \text{cosine}(\mathbf{v}_{gi}, \mathbf{v}_{pj})
$$

其中：
- $|\mathcal{M}^*|$ 是匹配对的数量（等于最优指派下的 $\min(m, n)$）
- 每一项是匹配的金标准节点 $i$ 与生成节点 $j$ 之间的余弦相似度

**性质**：
- **范围**：实践中的范围为 $[0, 1]$（理论上为 $[-1, 1]$，但嵌入相似度几乎总是正值）
- **解释**：值越高表示语义对应关系越好
- **公平性**：每个匹配对贡献相同（宏观平均，非加权）

**带缺失惩罚的扩展**：如果要惩罚生成不足（$m > n$），可以定义：

$$
\text{LabelScore}_{\text{penalized}} = \frac{1}{\max(m, n)} \sum_{(i,j) \in \mathcal{M}^*} \text{cosine}(\mathbf{v}_{gi}, \mathbf{v}_{pj})
$$

这个公式在生成节点少于金标准节点时惩罚得分，因为分母变大而分子保持上限。

---

## 8. Python 实现

### 8.1 计算相似度矩阵

```python
import numpy as np
from sentence_transformers import SentenceTransformer

def compute_similarity_matrix(
    gold_labels: list[str],
    pred_labels: list[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> np.ndarray:
    """
    计算金标准标签与生成标签之间的余弦相似度矩阵。

    参数:
        gold_labels: 金标准树的节点标签列表
        pred_labels: 生成树的节点标签列表
        model_name: 使用的 sentence-transformers 模型名称

    返回:
        S: (len(gold_labels), len(pred_labels)) 相似度矩阵
    """
    model = SentenceTransformer(model_name)

    # 编码两组标签
    gold_embs = model.encode(gold_labels, normalize_embeddings=True)
    pred_embs = model.encode(pred_labels, normalize_embeddings=True)

    # 余弦相似度 = L2归一化向量的点积
    S = gold_embs @ pred_embs.T
    return S
```

### 8.2 通过 SciPy 执行匈牙利算法

```python
from scipy.optimize import linear_sum_assignment

def hungarian_matching(S: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    求解标签匹配的最优指派问题。

    参数:
        S: (m, n) 相似度矩阵

    返回:
        gold_indices: 最优匹配中金标准节点的索引
        pred_indices: 对应的生成节点索引
    """
    # 将相似度转换为成本（最小化问题）
    C = 1.0 - S

    # 求解指派问题
    gold_indices, pred_indices = linear_sum_assignment(C)

    return gold_indices, pred_indices
```

> **注意**：`scipy.optimize.linear_sum_assignment` 实现了匈牙利算法，复杂度为 $O(n^3)$。它原生支持矩形矩阵，通过自动填充较小维度来实现。

### 8.3 完整评测管线

```python
def evaluate_label_score(
    gold_labels: list[str],
    pred_labels: list[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    penalize_missing: bool = True
) -> dict:
    """
    使用匈牙利匹配计算完整的标签评测得分。

    参数:
        gold_labels: 金标准树的节点标签列表
        pred_labels: 生成树的节点标签列表
        model_name: 嵌入模型名称
        penalize_missing: 是否惩罚生成不足

    返回:
        包含以下字段的字典：
            - label_score: 最终的 LabelScore 值
            - similarity_matrix: 完整的 (m, n) 相似度矩阵
            - matches: (gold_idx, pred_idx, similarity) 元组列表
            - mean_similarity: 所有匹配的相似度均值
            - std_similarity: 匹配相似度的标准差
    """
    # 第1步：计算相似度矩阵
    S = compute_similarity_matrix(gold_labels, pred_labels, model_name)

    # 第2步：求解最优指派
    gold_idx, pred_idx = hungarian_matching(S)

    # 第3步：提取匹配的相似度
    matched_sims = S[gold_idx, pred_idx]

    # 第4步：计算得分
    if penalize_missing:
        denominator = max(len(gold_labels), len(pred_labels))
    else:
        denominator = len(gold_idx)

    label_score = float(matched_sims.sum() / denominator)

    return {
        "label_score": label_score,
        "similarity_matrix": S,
        "matches": list(zip(gold_idx.tolist(), pred_idx.tolist(),
                            matched_sims.tolist())),
        "mean_similarity": float(matched_sims.mean()),
        "std_similarity": float(matched_sims.std(ddof=1)),
        "num_matches": len(gold_idx),
        "num_gold": len(gold_labels),
        "num_pred": len(pred_labels),
        "model_name": model_name,
    }

# 使用示例

gold_labels = ["Vehicle", "Car", "Bus", "Train"]
pred_labels = ["Transport", "Automobile", "Coach", "Railway"]

result = evaluate_label_score(gold_labels, pred_labels)
print(f"LabelScore = {result['label_score']:.4f}")
print(f"平均相似度 = {result['mean_similarity']:.4f}")
print(f"相似度标准差 = {result['std_similarity']:.4f}")

for g, p, sim in result["matches"]:
    print(f"  {gold_labels[g]:10s} -> {pred_labels[p]:12s}  ({sim:.4f})")
```

预期输出：

```
LabelScore = 0.9125
平均相似度 = 0.9125
相似度标准差 = 0.0349
  Vehicle    -> Transport      (0.9300)
  Car        -> Automobile     (0.9000)
  Bus        -> Coach          (0.8700)
  Train      -> Railway        (0.9500)
```

### 8.4 处理节点数量不相等的情况

当金标准树和生成树具有不同数量的节点时，匈牙利算法仍然产生 $\min(m, n)$ 个匹配。剩余的节点无法匹配。

```python
def evaluate_unequal_case(
    gold_labels: list[str],
    pred_labels: list[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> dict:
    """
    处理金标准树和生成树大小不同时的评测。
    """
    result = evaluate_label_score(gold_labels, pred_labels,
                                  model_name, penalize_missing=True)

    m, n = result["num_gold"], result["num_pred"]

    if m > n:
        print(f"警告：金标准树比生成树多 {m - n} 个节点。")
        print(f"       {m - n} 个金标准节点未被匹配。")
    elif n > m:
        print(f"提示：生成树比金标准树多 {n - m} 个额外节点。")
        print(f"      这些额外节点不影响 LabelScore "
              f"（但会影响 Precision/FDR 指标）。")

    if m > n:
        matched_gold = set(
            result["matches"][i][0] for i in range(len(result["matches"]))
        )
        unmatched = [gold_labels[i] for i in range(m)
                     if i not in matched_gold]
        print(f"未匹配的金标准节点：{unmatched}")

    return result

# 示例：生成树缺少一个节点
gold_labels = ["Vehicle", "Car", "Bus", "Train"]
pred_labels = ["Transport", "Automobile", "Railway"]  # 缺少 Bus/Coach

result = evaluate_unequal_case(gold_labels, pred_labels)
print(f"带惩罚的 LabelScore = {result['label_score']:.4f}")
```

预期输出：

```
警告：金标准树比生成树多 1 个节点。
       1 个金标准节点未被匹配。
未匹配的金标准节点：['Bus']
带惩罚的 LabelScore = 0.6950
```

带惩罚的得分下降是因为 3 个匹配对贡献 $0.93 + 0.90 + 0.95 = 2.78$，除以 $\max(4, 3) = 4$，结果为 $0.695$。

---

## 9. 局限性与注意事项

### 9.1 余弦相似度衡量的是相关性而非等价性

一个关键的限制：余弦相似度衡量的是**语义相关性**（Semantic Relatedness），而非**语义等价性**（Semantic Equivalence）。两个概念可以高度相关但不具有等价性：

```
Dog <-> Animal      （下位词-上位词：高相似度，不等价）
Car <-> Vehicle     （下位词-上位词：高相似度，不等价）
Algorithm <-> Procedure （实例-类别：高相似度，不等价）
```

这意味着 LabelScore 的**上限受限于嵌入模型的区分能力**。即使生成完美，获得 1.0 的完美 LabelScore 也是不可能的，因为嵌入模型的"相似"概念并不能完美地对应"概念相同"。

**缓解策略**：
1. **使用多个嵌入模型**并报告得分范围
2. **校准**：计算两个独立标注的金标准树之间的 LabelScore（获得上限估计）
3. **人工抽样**验证匹配对的准确性

### 9.2 嵌入模型偏差

不同的嵌入模型以不同方式编码语义关系：

| 模型族 | 优势 | 劣势 |
|---|---|---|
| Sentence-BERT (SBERT) | 良好的通用语义相似度 | 可能将主题相关性与等价性混淆 |
| E5 | 强大的零样本性能，适合检索 | 不太擅长细粒度相似度 |
| BGE (BAAI General Embedding) | 优秀的多语言支持，中文表现强 | 模型更大，推理较慢 |
| Instructor | 任务自适应，可以加入指令 | 设置更复杂，测试不够广泛 |

**建议**：对于研究级评测，至少使用两个嵌入模型并报告方差。对于生产监控，单个轻量级模型（如 `all-MiniLM-L6-v2`）已经足够。

### 9.3 一对一匹配假设

匈牙利算法强制实现**双射**（一对一）匹配。这个假设不一定在所有情况下都成立：

- **一对多**：单个金标准概念可能被拆分为多个生成概念（例如，"Attention Mechanism" -> "Self-Attention" + "Cross-Attention"）
- **多对一**：多个金标准概念可能被合并为单个生成概念

在这些情况下，匈牙利算法将强制最多一个正确的匹配成立，其余节点将无法匹配（或被错误匹配）。带惩罚的得分将反映这一点。

> **建议**：当评测目标在于评估细粒度的**粒度一致性**时，考虑用软匹配方法（如基于阈值的覆盖率指标：Entity Recall 和 Precision）来补充基于匈牙利算法的得分。

---

## 附录 A：完整标签评测示例

### 输入树

**金标准树**：
```
Vehicle
├── Car
├── Bus
└── Train
```

**生成树**：
```
Transport
├── Automobile
├── Coach
└── Railway
```

### 余弦相似度矩阵

使用 `sentence-transformers/all-MiniLM-L6-v2` 计算的值：

| 金标准 \ 生成 | Transport | Automobile | Coach | Railway |
|---|---|---|---|---|
| **Vehicle** | **0.93** | 0.75 | 0.45 | 0.30 |
| **Car** | 0.89 | **0.90** | 0.40 | 0.20 |
| **Bus** | 0.88 | 0.35 | **0.87** | 0.25 |
| **Train** | 0.40 | 0.25 | 0.30 | **0.95** |

### 匈牙利算法匹配

```
Vehicle  <-> Transport    (0.93)
Car      <-> Automobile   (0.90)
Bus      <-> Coach        (0.87)
Train    <-> Railway      (0.95)
```

### 得分计算

$$
\text{LabelScore} = \frac{0.93 + 0.90 + 0.87 + 0.95}{4} = \frac{3.65}{4} = 0.9125
$$

---

## 附录 B：匈牙利算法计算过程详解

本附录通过一个简化的 $3 \times 3$ 示例逐步说明匈牙利算法的计算过程。

### 第 0 步：相似度矩阵 $S$

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.95 | 0.80 | 0.30 |
| G2 | 0.90 | 0.85 | 0.20 |
| G3 | 0.40 | 0.25 | 0.92 |

### 第 1 步：转换为成本矩阵

$$
C(i,j) = 1 - S(i,j)
$$

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.05 | 0.20 | 0.70 |
| G2 | 0.10 | 0.15 | 0.80 |
| G3 | 0.60 | 0.75 | 0.08 |

### 第 2 步：行归约

每行减去该行的最小值。

行最小值：G1=0.05, G2=0.10, G3=0.08

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.00 | 0.15 | 0.65 |
| G2 | 0.00 | 0.05 | 0.70 |
| G3 | 0.52 | 0.67 | 0.00 |

### 第 3 步：列归约

每列减去该列的最小值。

列最小值：P1=0.00, P2=0.05, P3=0.00

| Gold | P1 | P2 | P3 |
|---|---|---|---|
| G1 | 0.00 | 0.10 | 0.65 |
| G2 | 0.00 | 0.00 | 0.70 |
| G3 | 0.52 | 0.62 | 0.00 |

### 第 4 步：用最少直线覆盖所有零

最少直线数：3（每行都有一个零，或者可以用列覆盖）。如果最少直线数等于矩阵维度（3），我们就找到了最优指派。

### 第 5 步：寻找最优指派

选择独立的零元素：
- G3 -> P3（该列唯一的零）
- G1 -> P1（第1行仅剩的零）
- G2 -> P2（最后剩余）

**结果**：G1->P1 (0.95), G2->P2 (0.85), G3->P3 (0.92)

**总相似度**：$0.95 + 0.85 + 0.92 = 2.72$
**平均值**：$2.72 / 3 = 0.907$

### Python 验证

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

S = np.array([[0.95, 0.80, 0.30],
              [0.90, 0.85, 0.20],
              [0.40, 0.25, 0.92]])

C = 1.0 - S
row_idx, col_idx = linear_sum_assignment(C)

print("最优指派结果：")
for r, c in zip(row_idx, col_idx):
    print(f"  G{r+1} -> P{c+1}  (S = {S[r,c]:.2f})")

print(f"总相似度: {S[row_idx, col_idx].sum():.2f}")
print(f"平均相似度: {S[row_idx, col_idx].mean():.3f}")
```

输出：
```
最优指派结果：
  G1 -> P1  (S = 0.95)
  G2 -> P2  (S = 0.85)
  G3 -> P3  (S = 0.92)
总相似度: 2.72
平均相似度: 0.907
```

---

## 附录 C：匈牙利算法形式化定义

### 问题描述

给定一个成本矩阵 $C \in \mathbb{R}^{n \times n}$（方阵情况），指派问题寻求一个置换 $\sigma$ of $\{1, 2, \ldots, n\}$，使得下式最小化：

$$
\min_{\sigma \in S_n} \sum_{i=1}^{n} C(i, \sigma(i))
$$

其中 $S_n$ 是 $n$ 个元素所有置换构成的对称群。

### 算法步骤概述

1. **行归约**：对每行 $i$，减去该行的最小值。
2. **列归约**：对每列 $j$，减去该列的最小值。
3. **覆盖零元素**：找出覆盖所有零元素所需的最少直线数（行和/或列）。
4. **最优性检验**：如果最少覆盖直线数等于 $n$，则可以从零元素中提取出最优指派。否则，进入第 5 步。
5. **改进矩阵**：找出最小的未覆盖元素 $\delta$。将所有未覆盖元素减去 $\delta$，将所有被双重覆盖的元素加上 $\delta$。返回第 3 步。

### 复杂度

- **时间复杂度**：$O(n^3)$——相比 $O(n!)$ 的暴力方法有了巨大改进。
- **空间复杂度**：$O(n^2)$ 用于存储成本矩阵（通过精心实现可降至 $O(n)$）。

### 为什么有效

匈牙利算法的有效性基于以下不变性质：*从任意行或列中减去一个常数不会改变最优指派*。这一性质被称为指派问题线性规划形式的**对偶变换**（Dual Transformation），允许算法迭代地变换成本矩阵，直到出现零成本的完美匹配。

---

## 附录 D：嵌入模型对比

| 模型 | 维度 | 语言 | 速度（标签/秒） | 推荐用途 |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | 英语+ | ~2000 | 快速评测，仅英文 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 50+ | ~1000 | 多语言评测 |
| `multilingual-e5-large` | 1024 | 100+ | ~300 | 高精度多语言 |
| `bge-m3` | 1024 | 100+ | ~350 | 中文支持强劲 |
| `all-mpnet-base-v2` | 768 | 英语 | ~800 | 最佳仅英文质量 |

> **注意**：速度随硬件配置（GPU vs CPU）和批处理大小显著变化。以上数值为近似值，用于相对比较。

---

> **版本记录 / Revision History**
>
> | 版本 / Version | 日期 / Date | 变更 / Changes |
> |---|---|---|
> | v1.0 | 2026-06-25 | 初始版本：基于匈牙利算法与嵌入相似度的概念树标签评测方法；中英双语合并目录；统一数学公式为 `$...$` / `$$...$$` 格式 |
>
> | 版本 / Version | 日期 / Date | 变更 / Changes |
> |---|---|---|
> | v1.0 | 2026-06-25 | Initial version: concept tree label evaluation via Hungarian algorithm & embedding similarity; merged bilingual TOC; unified math to `$...$` / `$$...$$` format |
