# 课程思维导图生成质量评估标准（Evaluation Criteria for Lecture Mind Map Generation）

> **文档约定 / Document Conventions**：
>
> - 所有章节采用统一结构模板：**目标 → 方法 → 公式/计算过程 → 参考阈值 → 示例输出**
> - 中文与英文具有同等地位，公式符号优先采用国际通用记号
> - 标注 `[可选]` 的维度为建议性指标，可在资源受限时酌情省略
>
> **All sections follow a unified template**: Goal → Method → Formula/Computation → Reference Threshold → Example Output.
>
> **Chinese and English have equal status**; formula symbols use internationally standard notation.
>
> **Dimensions marked [Optional] are advisory** and may be omitted under resource constraints.

---

## 目录（Table of Contents）

- [1. 节点标签质量评估 / Node Label Quality Assessment](#1-节点标签质量评估node-label-quality-assessment)
  - [1.1 匈牙利节点对齐 / Hungarian Node Alignment](#11-匈牙利节点对齐hungarian-node-alignment)
  - [1.2 节点精确率-召回率-F1 / Node Precision-Recall-F1](#12-节点精确率-召回率-f1-node-precision-recall-f1)
  - [1.3 标签语义相似度 / Label Semantic Similarity](#13-标签语义相似度label-semantic-similarity)
  - [1.4 核心概念召回率 / Entity Recall](#14-核心概念召回率entity-recall)
- [2. 层级结构正确率评估 / Hierarchy Structure Accuracy](#2-层级结构正确率评估hierarchy-structure-accuracy)
  - [2.1 边精确率-召回率-F1 / Edge Precision-Recall-F1](#21-边精确率-召回率-f1-edge-precision-recall-f1)
  - [2.2 无标签依存得分 / Unlabeled Attachment Score](#22-无标签依存得分unlabeled-attachment-score)
  - [2.3 树编辑距离 / Tree Edit Distance (TED)](#23-树编辑距离tree-edit-distance-ted)
  - [2.4 父子关系 F1 / Parent-Child F1](#24-父子关系-f1-parent-child-f1)
  - [2.5 层级对齐率 / Level Alignment Rate](#25-层级对齐率level-alignment-rate)
- [3. 下游任务测试：开卷问答效能 / Downstream Task: QA Utility](#3-下游任务测试开卷问答效能downstream-task-qa-utility)
  - [3.1 实验设计 / Experimental Design](#31-实验设计experimental-design)
  - [3.2 题型设计原则 / Question Design Principles](#32-题型设计原则question-design-principles)
  - [3.3 评分标准 / Scoring Criteria](#33-评分标准scoring-criteria)
  - [3.4 Prompt 设计要求 / Prompt Design Requirements](#34-prompt-设计要求prompt-design-requirements)
- [4. 生成效率与语音转录保真度 / Generation Efficiency & Transcription Fidelity](#4-生成效率与语音转录保真度generation-efficiency--transcription-fidelity)
  - [4.1 端到端延迟测量 / End-to-End Latency](#41-端到端延迟测量endtoend-latency-measurement)
  - [4.2 语音转录质量评估 / STT Quality Assessment](#42-语音转录质量评估stt-quality-assessment)
- [5. 多语言适应性与鲁棒性 / Multilingual Adaptability & Robustness](#5-多语言适应性与鲁棒性multilingual-adaptability--robustness)
  - [5.1 多语言输入支持度 / Multilingual Input Support](#51-多语言输入支持度multilingual-input-support)
  - [5.2 噪声环境稳定性 / Noise Robustness](#52-噪声环境稳定性noise-robustness)
- [6. 人工评估与自动化对齐 / Human Evaluation & Automated Alignment](#6-人工评估与自动化对齐human-evaluation--automated-alignment)
  - [6.1 评分维度与量表 / Scoring Dimensions & Rubric](#61-评分维度与量表scoring-dimensions--rubric)
  - [6.2 自动化-人工相关性分析 / Automated-Human Correlation Analysis](#62-自动化-人工相关性分析automated-human-correlation-analysis)
- [7. 综合评估汇总 / Summary & Aggregation](#7-综合评估汇总summary--aggregation)
  - [7.1 指标速查表 / Quick Reference](#71-指标速查表quick-reference)
  - [7.2 综合评分公式 / Composite Score [可选]](#72-综合评分公式composite-score可选)
  - [7.3 评估报告模板 / Evaluation Report Template](#73-评估报告模板evaluation-report-template)

---

## 1. 节点标签质量评估（Node Label Quality Assessment）

> **目标 / Goal**：
>
> **中文**：独立衡量生成节点标签（label）的语义正确性、完整性以及冗余程度。该维度与层级结构完全解耦，仅关注"节点本身说了什么"。所有节点级指标均以匈牙利匹配为基础，确保对齐的一致性和可复现性。
>
> **English**: Independently measure the semantic correctness, completeness, and redundancy of generated node labels. This dimension is entirely decoupled from hierarchy structure and focuses solely on "what the node itself says". All node-level metrics build upon Hungarian matching as the shared foundation, ensuring alignment consistency and reproducibility.

---

### 1.1 匈牙利节点对齐（Hungarian Node Alignment）

> **定位 / Role**：本节是后续所有节点级和边级指标的**共享基础设施**。每个指标（Node-P/R/F1、LabelSim、Edge-P/R/F1、UAS、LAR）均依赖于本节定义的对齐结果。

**方法 / Method**：

给定标准标注树 $T_s$（节点集 $V_s = \{v_{s1}, \ldots, v_{sn}\}$，标签集 $L_s$）和生成导图树 $T_g$（节点集 $V_g = \{v_{g1}, \ldots, v_{gm}\}$，标签集 $L_g$），通过以下四步建立最优一一匹配：

**1. 嵌入编码（Embedding）**：使用多语言 embedding 模型（推荐 `paraphrase-multilingual-MiniLM-L12-v2` 或 `bge-m3`）将每个节点标签编码为稠密向量：

$$
\mathbf{v}_{si} = \text{embed}(l_{si}), \quad \mathbf{v}_{gj} = \text{embed}(l_{gj})
$$

**2. 相似度矩阵（Similarity Matrix）**：计算所有标签对之间的余弦相似度，构建矩阵 $S \in [0,1]^{m \times n}$：

$$
S(i, j) = \frac{\mathbf{v}_{gi} \cdot \mathbf{v}_{sj}}{\|\mathbf{v}_{gi}\| \cdot \|\mathbf{v}_{sj}\|}
$$

**3. 匈牙利最优指派（Hungarian Optimal Assignment）**：将相似度矩阵转换为成本矩阵 $C(i,j) = 1 - S(i,j)$，调用匈牙利算法（$O(\max(m,n)^3)$）求解全局最优一一匹配，得到匹配对集合 $\mathcal{M}^*$：

$$
\mathcal{M}^* = \arg\max_{\mathcal{M}} \sum_{(i,j) \in \mathcal{M}} S(i,j)
$$

其中 $|\mathcal{M}^*| = \min(m, n)$。

**4. 相似度阈值过滤（Threshold Filtering）**：引入相似度阈值 $\tau$（推荐值 **0.70**），丢弃低质量匹配，得到高质量匹配对集合 $\mathcal{M}_\tau$：

$$
\mathcal{M}_\tau = \{(i,j) \in \mathcal{M}^* \mid S(i,j) \geq \tau\}
$$

> **阈值设计依据 / Threshold Rationale**：$\tau = 0.70$ 对应 embedding 余弦相似度的经验"语义等价"下限。低于此值通常意味着匹配不可靠（近义词混淆、跨概念误匹配）。被丢弃的匹配对中的生成节点和标准节点分别计入 FP 和 FN（见 §1.2）。

**符号汇总 / Notation Summary**：

| 符号 / Symbol | 含义 / Meaning |
|---|---|
| $V_s, L_s$ | 标准树节点集合、标签集合 / Gold node set, label set |
| $V_g, L_g$ | 生成树节点集合、标签集合 / Generated node set, label set |
| $S \in [0,1]^{m \times n}$ | 余弦相似度矩阵 / Cosine similarity matrix |
| $\mathcal{M}^*$ | 匈牙利原始匹配对集合 / Raw Hungarian matching set |
| $\tau$ | 相似度阈值，推荐 0.70 / Similarity threshold, recommended 0.70 |
| $\mathcal{M}_\tau$ | 过滤后的高质量匹配对 / Filtered high-quality matching pairs |

**示例输出 / Example Output**：

```text
Gold labels    (n=5):  ["LLM", "Attention", "Transformer", "Fine-tuning", "RLHF"]
Generated      (m=6):  ["Large Language Model", "Self-Attention", "Transformer", 
                         "Fine-tune", "AI is cool", "RLHF"]

Similarity Matrix S (6x5):
                         LLM     Attn    Trans   FT      RLHF
Large Language Model     0.94    0.28    0.35    0.22    0.15
Self-Attention           0.18    0.91    0.42    0.20    0.10
Transformer              0.31    0.38    0.96    0.25    0.12
Fine-tune                0.12    0.15    0.18    0.89    0.22
AI is cool               0.05    0.08    0.06    0.10    0.08
RLHF                     0.10    0.12    0.14    0.20    0.93

Hungarian M* = {(0,0,s=0.94), (1,1,s=0.91), (2,2,s=0.96), (3,3,s=0.89), (5,4,s=0.93)}
After tau=0.70 filtering, all 5 pairs retained. "AI is cool" unmatched -> FP candidate.
```

---

### 1.2 节点精确率-召回率-F1（Node Precision-Recall-F1）

> **目标 / Goal**：基于匈牙利节点对齐与阈值过滤，以混淆矩阵方式衡量生成节点与标准节点的匹配质量——同时惩罚遗漏（召回不足）和冗余（精确率不足）。
>
> **English**: Based on Hungarian node alignment with threshold filtering, measure matching quality using confusion-matrix formulation — penalizing both omissions and extraneous additions.

**公式 / Formula**：

设 $V_g$ 为生成节点集合（$|V_g| = m$），$V_s$ 为标准节点集合（$|V_s| = n$）：

$$
\text{TP} = |\mathcal{M}_\tau|,\quad \text{FP} = m - \text{TP},\quad \text{FN} = n - \text{TP}
$$

$$
\text{Node-P} = \frac{\text{TP}}{\text{TP} + \text{FP}},\quad \text{Node-R} = \frac{\text{TP}}{\text{TP} + \text{FN}},\quad \text{Node-F1} = \frac{2 \times \text{Node-P} \times \text{Node-R}}{\text{Node-P} + \text{Node-R}}
$$

> **注意 / Note**：TP=FP=0 且 FN>0 时定义 P=0；TP=FN=0 且 FP>0 时定义 R=0。

**参考阈值 / Reference Threshold**：

| 指标 / Metric | 优秀 / Excellent | 良好 / Good | 需改进 / Needs Improvement |
|---|---|---|---|
| Node-F1 | $\geq 0.85$ | 0.70 – 0.84 | $< 0.70$ |
| Node-P | $\geq 0.80$ | 0.65 – 0.79 | $< 0.65$ |
| Node-R | $\geq 0.85$ | 0.70 – 0.84 | $< 0.70$ |

**示例输出 / Example Output**（续 §1.1 示例）：

```text
|M_τ|=5, m=6, n=5 -> TP=5, FP=1, FN=0
Node-P=5/6=0.833, Node-R=5/5=1.000, Node-F1=0.909 -> Excellent
```

---

### 1.3 标签语义相似度（Label Semantic Similarity）

> **目标 / Goal**：在节点已正确匹配（TP）的前提下，衡量匹配标签之间的语义贴近程度。仅关注"匹配上的标签有多相似"。
>
> **English**: Given nodes are correctly matched (TP), measure semantic closeness between matched label pairs.

**公式 / Formula**：仅对 $\mathcal{M}_\tau$ 中的 TP 节点对计算余弦相似度的宏观平均：

$$
\text{LabelSim} = \frac{1}{|\mathcal{M}_\tau|} \sum_{(i,j) \in \mathcal{M}_\tau} S(i,j)
$$

> **注意 / Note**：当 $|\mathcal{M}_\tau| = 0$ 时定义 LabelSim=0。此指标范围 $[\tau, 1.0]$。

**参考阈值 / Reference Threshold**：

| 等级 / Grade | LabelSim | 说明 / Description |
|---|---|---|
| 优秀 / Excellent | $\geq 0.85$ | 标签语义高度一致 |
| 良好 / Good | 0.75 – 0.84 | 大体一致，少量偏差 |
| 需改进 / Needs Improvement | $< 0.75$ | 语义偏差显著 |

**示例输出 / Example Output**：`LabelSim = (0.94+0.91+0.96+0.89+0.93)/5 = 0.926` → Excellent

---

### 1.4 核心概念召回率（Entity Recall）

**方法 / Method**：

预先从该节 Lecture 中确定 10–20 个必须掌握的核心概念集合 $E_s$（如本课程中的 LLM、Agent、MCP、ReAct、Sub-graph Retrieval 等），逐项检查其是否在生成导图的任意节点 label 或 details 中出现（通过 embedding 相似度 $\geq$ 阈值 $\tau$ 判定为"命中"）。

**预先从课程中确定核心概念集合，逐项检查其是否在生成导图中出现（通过 embedding 相似度判定为"命中"）。**

Pre-define a set of 10–20 essential concepts $E_s$ from the lecture. A concept is counted as "hit" if any generated node's label or details contains it with embedding similarity $\geq$ threshold $\tau$.

**公式 / Formula**：

$$
\text{Recall} = \frac{|\{e \in E_s \mid \exists\ l_g \in L_g \cup D_g,\ \text{cosine}(\text{embed}(e), \text{embed}(l_g)) \geq \tau\}|}{|E_s|}
$$

> **参数说明 / Parameters**：
>
> - $D_g$：生成节点 details 中所有条目的并集
> - $\tau = 0.70$（推荐值）
>
> - $D_g$: union of all detail entries across generated nodes.
> - $\tau = 0.70$ (recommended).

**参考阈值 / Reference Threshold**：

| 等级 / Grade | Recall | 说明 / Description |
|---|---|---|
| 优秀 / Excellent | $\geq$ 0.90 | 几乎无关键概念遗漏 / nearly no key concepts missed |
| 良好 / Good | 0.75 – 0.89 | 少量次要概念遗漏 / minor secondary concepts missed |
| 需改进 / Needs Improvement | $<$ 0.75 | 存在关键知识缺口 / significant knowledge gaps exist |

**示例输出 / Example Output**：

```text
Essential concepts (|Es|=15): [LLM, Agent, MCP, ReAct, RAG, Embedding, Transformer, ...]
Hits in generated map:      [LLM(details), Agent(label), MCP(label), ReAct(label), RAG(label),
                              Embedding(details), Transformer(label), ...]  -> 13 hits
Entity Recall = 13 / 15 = 0.867  -> Good
Missed: ["Tool Calling", "Hallucination"]
```

## 2. 层级结构正确率评估（Hierarchy Structure Accuracy）

> **目标 / Goal**：
>
> **中文**：独立衡量父子关系、从属关系的准确性，不与节点标签质量混淆。所有边级指标均依赖于 §1.1 的匈牙利节点对齐 $\mathcal{M}_\tau$，确保标签评估和层级评估使用同一套节点对应关系。
>
> **English**: Independently measure parent-child and subordination accuracy. All edge-level metrics depend on the Hungarian node alignment $\mathcal{M}_\tau$ from §1.1, ensuring label and hierarchy evaluations share the same node correspondence.

---

### 2.1 边精确率-召回率-F1（Edge Precision-Recall-F1）

> **目标 / Goal**：基于已建立的节点对应关系，衡量生成导图中有向边（父子关系）与标准标注的一致性——同时惩罚缺失边和多余边。
>
> **English**: Based on established node correspondences, measure consistency of directed edges between generated and gold maps.

**方法 / Method**：

给定标准边集 $E_s$ 和生成边集 $E_g$，利用 §1.1 的节点匹配 $\mathcal{M}_\tau$ 定义映射 $\mu$：$\mu(s) = g$ 当且仅当 $(g, s) \in \mathcal{M}_\tau$。

标准边 $e_s = (s_p, s_c) \in E_s$ 被判定为 TP 当且仅当 $\mu(s_p) \neq \bot \land \mu(s_c) \neq \bot \land (\mu(s_p), \mu(s_c)) \in E_g$。

**公式 / Formula**：

$$
\text{TP}_\text{edge} = |\{e_s \in E_s \mid \mu(e_s.\text{parent}), \mu(e_s.\text{child}) \text{ both mapped and form edge in } E_g\}|
$$

$$
\text{FN}_\text{edge} = |E_s| - \text{TP}_\text{edge},\quad \text{FP}_\text{edge} = |E_g| - \text{TP}_\text{edge}
$$

$$
\text{Edge-P} = \frac{\text{TP}_\text{edge}}{|E_g|},\quad \text{Edge-R} = \frac{\text{TP}_\text{edge}}{|E_s|},\quad \text{Edge-F1} = \frac{2 \times \text{Edge-P} \times \text{Edge-R}}{\text{Edge-P} + \text{Edge-R}}
$$

> **边界情况**：$|E_s|=0$ 时定义 Edge-R=1.0；$|E_g|=0$ 时定义 Edge-P=1.0。

**参考阈值 / Reference Threshold**：Edge-F1 $\geq 0.80$ 为优秀，0.65–0.79 为良好。

**示例输出 / Example Output**：

```text
Gold edges (5): (LLM,Attn), (LLM,Trans), (LLM,FT), (Trans,Enc), (Trans,Dec)
Gen edges  (6): above 5 + extra (LLM,RLHF)
TP=5, FN=0, FP=1 -> Edge-P=5/6=0.833, Edge-R=5/5=1.000, Edge-F1=0.909 -> Excellent
```

---

### 2.2 无标签依存得分（Unlabeled Attachment Score, UAS）

> **目标 / Goal**：借鉴依存句法分析领域经典指标 UAS（Jurafsky & Martin, 2023, Ch.19），以节点为视角衡量"每个生成节点的父节点是否正确"。
>
> **English**: Adapted from dependency parsing (Jurafsky & Martin, 2023), node-centric metric for correct parent assignment.

**方法 / Method**：

对 $\mathcal{M}_\tau$ 中每个匹配的标准节点 $s$，检查其生成对应节点的父节点是否等于其标准父节点的（匹配后）对应节点：

$$
\text{UAS} = \frac{|\{s \in V_s \mid \mu(s) \neq \bot \land \text{parent}_g(\mu(s)) = \mu(\text{parent}_s(s))\}|}{|\mathcal{M}_\tau|}
$$

根节点特殊处理：$s$ 为根且 $\mu(s)$ 为根时直接判定正确。

> **与 Edge-R 对比**：Edge-R 以边为单位（分母 $|E_s|$），UAS 以节点为单位（分母 $|\mathcal{M}_\tau|$）。UAS 对标签失败的容忍度更好——仅计算已匹配节点。

**参考阈值 / Reference Threshold**：UAS $\geq 0.85$ 为优秀，0.70–0.84 为良好。

**示例输出 / Example Output**：

```text
7 matched nodes: RLHF placed under LLM instead of Fine-tuning -> UAS=6/7=0.857 -> Excellent
```

---

### 2.3 树编辑距离（Tree Edit Distance, TED）

> **目标 / Goal**：
>
> **中文**：最小编辑操作框架（Zhang-Shasha 算法）将生成树和标准树之间的整体结构差异量化为一个单一距离分数。nTED 是该距离经节点数归一化后的版本，使不同规模的树可比。
>
> **English**: The minimum edit operation framework (Zhang-Shasha algorithm) quantifies the overall structural difference between the generated and gold trees as a single distance score. nTED is the node-count-normalized version, making trees of different sizes comparable.

**方法 / Method**：计算将 $T_g$ 转换为 $T_s$ 所需的最少编辑操作次数（插入节点、删除节点、重标记标签、变更父节点）。使用 Zhang-Shasha 算法（$O(|T_g| \times |T_s| \times \text{depth}^2)$）或 APTED 算法（$O(|T_g| \times |T_s|)$）。

**公式 / Formula**：

$$
\text{nTED} = \frac{\text{TED}(T_g, T_s)}{\max(|T_g|, |T_s|)}
$$

> **注意 / Note**：TED 对树规模和编辑代价敏感。使用 nTED 代替原始 TED 使不同大小树之间的分数可比。当节点数量悬殊时（如 $|T_g| \gg |T_s|$），nTED 可能因分母过大而低估结构差异，建议配合 Edge-P/R/F1 和 UAS 综合判断。

**参考阈值 / Reference Threshold**：nTED $\leq 0.25$

**实现建议 / Implementation**：推荐 `zss`（Zhang-Shasha）或 `apted`（APTED）Python 库。

---

### 2.4 父子关系 F1（Parent-Child F1）

> **目标 / Goal**：
>
> **中文**：基于语义标签相似度直接比对父子对——不依赖匈牙利节点对齐。与 §2.1 的 Edge-F1 互补：Edge-F1 基于对齐后的节点映射，PC-F1 基于标签本身。
>
> **English**: Direct parent-child pair comparison based on semantic label similarity — independent of Hungarian node alignment. Complements Edge-F1 (§2.1): Edge-F1 uses alignment-based node mapping, PC-F1 uses label-based matching.

> **注意**：与 Edge-F1 (§2.1) 的差异——PC-F1 通过语义相似度判定父/子标签是否匹配（余弦 $\geq \tau$），Edge-F1 通过匈牙利节点映射判定边是否存在。两者结果越接近，说明节点对齐（§1.1）的质量越高。

**方法 / Method**：将标准标注中的父子节点对 $(p_s, c_s)$ 与生成导图中的父子节点对 $(p_g, c_g)$ 进行匹配。一对父子关系被判定为"正确"，当且仅当父节点和子节点的 label 均能在对方集合中找到语义匹配（余弦相似度 $\geq \tau$）。

**公式 / Formula**：

$$
\text{PCA} = \frac{|\text{correct\_parent\_child\_pairs}|}{|\text{gold\_parent\_child\_pairs}|},\quad \text{PC-Precision} = \frac{|\text{correct\_parent\_child\_pairs}|}{|\text{generated\_parent\_child\_pairs}|},\quad \text{PC-F1} = \frac{2 \times \text{PCA} \times \text{PC-Precision}}{\text{PCA} + \text{PC-Precision}}
$$

**参考阈值 / Reference Threshold**：PC-F1 $\geq 0.75$

---

### 2.5 层级对齐率（Level Alignment Rate, LAR）

> **目标 / Goal**：
>
> **中文**：衡量已匹配节点在树中的层级深度是否一致。高的 LAR 意味着生成导图与标准标注不仅在节点和边上匹配，还保持了每层概念抽象程度的正确性。
>
> **English**: Measures whether matched nodes share the same tree depth. High LAR indicates that the generated map preserves the correct level of abstraction for each concept relative to the gold standard.

**方法 / Method**：节点的层级深度定义为从根到该节点的最短路径长度（根深度 = 0）。通过 §1.1 的匈牙利匹配 $\mathcal{M}_\tau$ 对齐节点后，对每个匹配对比较两者的深度。

**公式 / Formula**：

$$
\text{LAR} = \frac{|\{(g, s) \in \mathcal{M}_\tau \mid \text{depth}(g) = \text{depth}(s)\}|}{|\mathcal{M}_\tau|}
$$

**参考阈值 / Reference Threshold**：LAR $\geq 0.70$

---

## 3. 下游任务测试：开卷问答效能（Downstream Task: QA Utility）

> **目标 / Goal**：
>
> **中文**：不在直接层面上评价导图，而是考察"基于该导图回答问题的能力"——这是衡量数据结构信息密度的黄金标准。
>
> **English**: Rather than directly judging the mind map, assess the ability to answer questions based on it — the gold standard for measuring a data structure's information density.

---

### 3.1 实验设计（Experimental Design）

| 组别 | 输入内容 | 要求 | 记录指标 |
|---|---|---|---|
| **对照组** (Control) | 原始逐字稿全文 + 10 道测验题 | LLM 阅读全文后逐一作答 | 准确率、Token 消耗、推理时间 |
| **实验组** (Experimental) | 仅生成导图 JSON + 相同 10 题 | LLM 仅基于导图信息作答 | 准确率、Token 消耗、推理时间 |
| **变体组 [可选]** (Variant) | 导图 JSON + 原始逐字稿；或不同润色程度的导图 | 考察导图的额外增益 / 润色价值 | 同上 |

**统一控制变量 / Controlled Variables**：

- [ ] 同一 LLM（推荐 GPT-4o 或同等能力模型）
- [ ] 同一 Prompt 模板（仅输入内容不同）
- [ ] `temperature = 0`（确保可复现）
- [ ] 同一评分标准

---

### 3.2 题型设计原则（Question Design Principles）

三类题型按 `40% : 40% : 20%` 比例混合：

| 题型类别 | 占比 | 示例 | 考察维度 |
|---|---|---|---|
| **事实检索型** (Fact Retrieval) | 40% | "MCP 协议的全称是什么？"、"ReAct 的四个步骤分别是什么？" | 导图是否覆盖了关键事实信息 |
| **关系推理型** (Relation Inference) | 40% | "Agent 和 MCP 之间是什么关系？"、"如果去掉 Embedding 层，哪些下游任务会受影响？" | 导图是否保留了概念间的逻辑关系 |
| **综合应用型** (Synthesis) | 20% | "根据本课内容，设计一个基于 MCP 的问答系统架构。" | 导图是否能支撑高层次的综合推理 |

**题目设计约束 / Design Constraints**：

1. 所有题目必须可仅通过原始逐字稿回答（确保对照组基线有效）
2. 题目难度需经 2 位领域专家背对背评审
3. 每题有且仅有一个客观正确答案

---

### 3.3 评分标准（Scoring Criteria）

**自动化评分（主指标） / Automated Scoring (Primary)**：

采用三指标加权综合：

$$
\text{QA-Score} = 0.3 \times \text{BLEU-4} + 0.4 \times \text{ROUGE-L} + 0.3 \times \text{BERTScore}
$$

| 指标 / Metric | 说明 / Description | 权重 / Weight |
|---|---|---|
| BLEU-4 | 4-gram 精度，衡量生成答案与标准答案的 n-gram 重合度 / 4-gram precision measuring n-gram overlap | 0.3 |
| ROUGE-L | 最长公共子序列召回率，对长答案更友好 / longest common subsequence recall, friendly to long answers | 0.4 |
| BERTScore | 基于 contextual embedding 的语义相似度，弥补 BLEU/ROUGE 对近义词的盲区 / semantic similarity based on contextual embedding | 0.3 |

**人工评判（辅助验证） / Human Judgment (Auxiliary Validation)**：

随机抽取 30% 的问答对，由 3 位注释者采用三盲法（triple-blind）独立评分：

- **3 分**：答案完全正确，无歧义
- **2 分**：答案部分正确，有少量遗漏或近似正确
- **1 分**：答案基本错误或严重不完整
- **0 分**：完全错误或未作答

计算 Fleiss' $\kappa$ 衡量评分者间一致性（目标 $\kappa \geq 0.75$）。

---

### 3.4 Prompt 设计要求（Prompt Design Requirements）

为确保实验公平，需使用统一 Prompt 模板：

```text
System: You are a student who has just attended a lecture.
Your only source of information is the [provided material].
Answer each question based solely on that material.
If the material contains no relevant information, respond with
"Cannot determine from the provided material." Do not use prior knowledge.

User: [Provided Material: Full Transcript / Mind Map JSON / Mind Map JSON + Full Transcript]

Questions:
1. ...
2. ...
...
10. ...

Please answer each question concisely and accurately.
```

**关键约束 / Critical Constraints**：

- [ ] System Prompt 需明确禁止 LLM 使用先验知识（prior knowledge）
- [ ] 所有组使用相同的 System Prompt 和 Question 文本
- [ ] 答案顺序随机化（避免位置偏差）
- [ ] 每组至少重复 3 次实验取平均值（减少 LLM 随机性影响）

> **预期结论方向 / Expected Outcome Direction**：
> 若实验组准确率 $\geq$ 对照组的 90%，且 Token 消耗降低 $\geq 70\%$，则证明导图结构具有高效的信息压缩能力，显著优于原始逐字稿。

---

## 4. 生成效率与语音转录保真度（Generation Efficiency & Transcription Fidelity）

> **目标 / Goal**：
>
> **中文**：量化系统从音频输入到导图输出的全流程效率，以及上游 STT 质量对下游导图质量的影响程度。
>
> **English**: Quantify the end-to-end efficiency from audio input to mind-map output, and the impact of upstream STT quality on downstream mind-map quality.

---

### 4.1 端到端延迟测量（End-to-End Latency Measurement）

**方法 / Method**：

使用高精度计时器（`time.perf_counter()`）在管线各阶段关键节点打点。每个测试样本重复 5 次，取 P50 和 P95。

**使用高精度计时器在管线各阶段关键节点打点。**

Use high-precision timers at each pipeline stage. Repeat 5$\times$ per sample, report P50 and P95.

**分阶段计时 / Staged Timing**：

| 阶段 / Stage | 计时起止 / Timing | 符号 / Symbol |
|---|---|---|
| T1: STT 语音转文字 / Speech-to-Text | 音频文件加载 → STT 文本输出 / Audio load → STT output | $t_{stt}$ |
| T2: 概念提取 / Concept Extraction | LLM 请求发送 → 概念列表返回 / LLM request → concept list | $t_{concept}$ |
| T3: 层级规划 / Hierarchy Planning | LLM 请求发送 → 层级关系返回 / LLM request → hierarchy | $t_{hierarchy}$ |
| T4: Delta 生成 / Delta Generation | LLM 请求发送 → Delta 返回 / LLM request → delta | $t_{delta}$ |
| T5: 后处理 + 润色 / Post-processing + Polish | Delta 合并 + 润色迭代完成 / Merge + polish iteration | $t_{polish}$ |

总延迟：$T_{total} = t_{stt} + t_{concept} + t_{hierarchy} + t_{delta} + t_{polish}$

**参考阈值 / Reference Threshold**：

| 指标 / Metric | 实时交互目标 / Real-time Target | 批量处理目标 / Batch Target |
|---|---|---|
| $T_{total}$ P50 | $\leq$ 30s | $\leq$ 60s |
| $T_{total}$ P95 | $\leq$ 60s | $\leq$ 120s |
| STT 占比 / STT Ratio | $\leq$ 40% | $\leq$ 50% |

**示例输出 / Example Output**：

```text
Sample: lecture_03_LLM_agents.wav (45 min lecture)
Run 1: T_stt=12.3s, T_concept=4.2s, T_hierarchy=3.1s, T_delta=5.8s, T_polish=2.1s -> Total=27.5s
Run 2: T_stt=11.8s, T_concept=3.9s, T_hierarchy=3.5s, T_delta=6.1s, T_polish=2.3s -> Total=27.6s
...
P50 Total: 27.5s   P95 Total: 31.2s
STT ratio (P50): 12.1/27.5 = 44.0%
```

---

### 4.2 语音转录质量评估（STT Quality Assessment）

> **概述 / Overview**：
>
> **中文**：使用人工转写的标准文本（Ground-Truth Transcript）与 STT 输出进行比对，计算词错率（WER）和关键术语保留率（KTRR），并分析其对下游导图质量（第1节 Entity Recall）的衰减效应。
>
> **English**: Compare STT output against a manually transcribed ground-truth text. Compute WER and Key Term Retention Rate (KTRR), and analyze their attenuation effect on downstream map quality (Section 1 Entity Recall).

---

#### 4.2.1 词错率（Word Error Rate, WER）

**公式 / Formula**：

$$
\text{WER} = \frac{S + D + I}{N} = \frac{\text{替换数 + 删除数 + 插入数}}{\text{标准文本总词数}}
$$

- 使用 `jiwer` 库计算
- 对中文需先分词（推荐 `jieba`）

**参考阈值 / Reference Threshold**：`WER` $\leq 0.15$（即 $\geq 85\%$ 的转写准确率）

---

#### 4.2.2 关键术语保留率（Key Term Retention Rate, KTRR）

从标准文本中预先提取领域关键术语集合 $K_s$（建议 20–30 个，通过 TF-IDF 或专家标注）。

**公式 / Formula**：

$$
\text{KTRR} = \frac{|\{k \in K_s \mid k \in \text{STT\_output}\}|}{|K_s|}
$$

> **匹配策略 / Matching Strategy**：
>
> **中文**：采用模糊匹配（允许 1 字符编辑距离的中文容错）。
>
> **English**: Use fuzzy matching with a tolerance of 1 Chinese character edit distance.

**参考阈值 / Reference Threshold**：`KTRR` $\geq 0.90$（关键术语几乎不能丢失）

---

#### 4.2.3 STT 质量 → 导图质量关联分析（STT-to-Map Quality Correlation）

绘制 WER（横轴）vs Entity Recall（纵轴）散点图，拟合线性回归，报告 Pearson $r$ 和 Spearman $\rho$。

- 若 $\rho > 0.7$：STT 质量是导图质量的重要瓶颈，应优先优化 STT 模块
- 若 $\rho < 0.3$：管线自身具备一定的容错能力

---

## 5. 多语言适应性与鲁棒性（Multilingual Adaptability & Robustness）

> **目标 / Goal**：
>
> **中文**：评估系统对不同语言（尤其中英混合）输入的支持度，以及在噪声环境下的稳定性。
>
> **English**: Evaluate the system's support for different languages (especially Chinese-English mixed input) and stability under noisy conditions.

---

### 5.1 多语言输入支持度（Multilingual Input Support）

**方法 / Method**：

构建三组测试集，每组 5 个 Lecture 片段：

| 测试集 / Test Set | 语言组成 / Language Composition | 示例 / Example |
|---|---|---|
| CN-Only | 100% 中文 / 100% Chinese | 中文授课的《机器学习》课程 / Chinese-taught Machine Learning course |
| EN-Only | 100% 英文 / 100% English | 英文授课的 CS229 课程 / English-taught CS229 course |
| CN-EN-Mixed | 中英混合 / Chinese-English Mixed | "今天我们讲 Transformer Architecture..." / "Today we discuss Transformer Architecture..." |

每组分别计算：

- Entity Recall（§1.4）
- LabelSim（§1.3）
- PC-F1（§2.4）

> **参考阈值 / Reference Threshold**：
>
> **中文**：三组指标差异应 $\leq 15\%$，即系统在不同语言间性能不应出现显著分化。
>
> **English**: The difference across the three groups should be $\leq 15\%$, indicating no significant performance degradation across languages.

**报告要求 / Reporting Requirement**：
分别报告每组指标，并附语言分布饼图和差异热力图。

---

### 5.2 噪声环境稳定性（Noise Robustness）

**方法 / Method**：

向标准文本中注入模拟 STT 噪声，观察导图质量随噪声强度升高的衰减曲线。

噪声注入策略（二选一或组合使用）：

| 策略 / Strategy | 操作 / Operation | 参数范围 / Parameter Range |
|---|---|---|
| 字符级扰动 / Character-level Perturbation | 以概率 $p$ 对随机位置的字符进行替换、删除或插入 / Replace, delete, or insert characters at random positions with probability $p$ | $p \in \{0.00, 0.05, 0.10, 0.15, 0.20\}$ |
| WER 模拟 / WER Simulation | 使用开源 TTS + STT 回路生成真实噪声 / Use open-source TTS + STT loop to generate real noise | — |

在每个噪声水平下，测量：

1. Entity Recall 衰减率（相对于无噪声基线）
2. PC-F1 衰减率

**预期输出 / Expected Output**：

```text
Noise Level (p)  | WER    | Entity Recall | PC-F1  | Recall Drop |
-----------------|--------|---------------|--------|-------------|
0.00 (baseline)  | 0.000  | 0.92          | 0.85   | baseline    |
0.05             | 0.048  | 0.89          | 0.82   | -3.3%       |
0.10             | 0.096  | 0.83          | 0.76   | -9.8%       |
0.15             | 0.142  | 0.74          | 0.67   | -19.6%      |
0.20             | 0.191  | 0.61          | 0.54   | -33.7%      |
```

**鲁棒性级别判定 / Robustness Level**：

- **强鲁棒**：WER $\leq 0.10$ 时 Recall Drop $\leq 10\%$
- **中等鲁棒**：WER $\leq 0.10$ 时 Recall Drop 在 10%–25%
- **弱鲁棒**：WER $\leq 0.10$ 时 Recall Drop $> 25\%$

---

## 6. 人工评估与自动化对齐（Human Evaluation & Automated Alignment）

> **目标 / Goal**：
>
> **中文**：补充自动化指标无法覆盖的主观体验维度（可读性、布局合理性、教学实用性），并通过自动化-人工相关性分析验证自动化指标是否有意义——即自动化高分是否对应人类评估者认为的"好导图"。
>
> **English**: Supplement automated metrics with subjective experience dimensions, and validate that automated metrics are meaningful through correlation analysis — i.e., whether high automated scores correspond to maps that humans consider "good".

---

### 6.1 评分维度与量表（Scoring Dimensions & Rubric）

采用 5 点 Likert 量表（1=非常差, 5=非常好），评估者 $\geq 5$ 人，需包含至少 2 名目标用户（学生）。

| 维度 / Dimension | 评估问题 / Evaluation Question | 1 分锚定 / Score 1 Anchor | 5 分锚定 / Score 5 Anchor |
|---|---|---|---|
| **可读性** / Readability | 文字标签是否清晰易懂？ / Are labels clear and understandable? | 晦涩难懂，需反复阅读 / Obscure, requires repeated reading | 一目了然，信息完整 / Clear at a glance, complete information |
| **布局合理性** / Layout | 空间位置是否合理？有无重叠？ / Are spatial positions reasonable? Any overlaps? | 大量重叠、连线交叉混乱 / Heavy overlaps, chaotic crossing lines | 层次分明、视觉流畅 / Clear hierarchy, smooth visuals |
| **信息密度** / Information Density | 是否高效传达了核心内容？ / Does it efficiently convey core content? | 信息稀疏，缺少关键内容 / Sparse information, missing key content | 密度适中，概念与细节平衡 / Balanced density, concepts and details |
| **教学实用性** / Pedagogical Utility | 作为复习资料的使用意愿？ / Willingness to use as review material? | 不会使用——缺乏组织 / Won't use—lack of organization | 非常愿意——结构清晰 / Very willing—clear structure |
| **层级直觉性** / Hierarchy Intuitiveness | 父子从属关系是否符合直觉？ / Do parent-child relationships follow intuition? | 大量反直觉或不合理 / Mostly counter-intuitive or unreasonable | 完全符合认知 / Fully aligned with cognition |

**评分者间一致性 / Inter-rater Reliability**：计算 ICC(3,k) 或 Kendall's W，目标 $\geq 0.70$。

---

### 6.2 自动化-人工相关性分析（Automated-Human Correlation Analysis）

> **目标 / Goal**：验证自动化指标是否能够替代或近似人工评估。若关键自动化指标与人工评分达到强相关（Pearson $r \geq 0.70$），则证明自动化指标具有效标效度（criterion validity）。
>
> **English**: Validate whether automated metrics can substitute human evaluation. If key metrics achieve strong correlation (Pearson $r \geq 0.70$), they demonstrate criterion validity.

**方法 / Method**：

**1. 样本选择**：至少选取 30 个导图样本（覆盖优秀、良好、需改进各约 1/3），同时进行自动化和人工评估。

**2. 指标配对**：

| 自动化指标 / Automated Metric | 对应人工维度 / Human Dimension | 预期相关性理由 / Rationale |
|---|---|---|
| Node-F1 (§1.2) | 可读性 / Readability | 节点匹配质量直接影响标签可读性 |
| Node-F1 + Entity Recall (§1.4) | 信息密度 / Information Density | 概念覆盖度影响信息完整性感知 |
| Edge-F1 (§2.1) + UAS (§2.2) | 层级直觉性 / Hierarchy Intuitiveness | 边级指标直接影响层级合理性感观 |
| LabelSim (§1.3) | 可读性 / Readability | 标签语义质量影响阅读流畅性 |

**3. 相关性计算**：

Pearson 积差相关系数（衡量线性关系）：

$$
r(\mathbf{a}, \mathbf{h}) = \frac{\sum (a_i - \bar{a})(h_i - \bar{h})}{\sqrt{\sum (a_i - \bar{a})^2} \cdot \sqrt{\sum (h_i - \bar{h})^2}}
$$

Spearman 等级相关系数（衡量单调关系，对异常值更鲁棒）：

$$
\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)},\quad d_i = \text{rank}(a_i) - \text{rank}(h_i)
$$

**4. 效度判定标准**：

| 相关强度 | $r$ 或 $\rho$ 范围 | 结论 |
|---|---|---|
| 强 / Strong | $\geq 0.70$ | 自动化指标有效，可替代人工评估 |
| 中等 / Moderate | 0.40 – 0.69 | 自动化指标部分有效，需结合人工评估 |
| 弱 / Weak | $< 0.40$ | 自动化指标需重新设计或补充 |

> **目标阈值**：核心指标（Node-F1、Edge-F1）的 Pearson $r \geq 0.70$ 是自动化评估体系被认可的最低条件。

**示例输出 / Example Output**：

```text
Sample: n=36 maps (12 Excellent, 12 Good, 12 Needs Improvement)
  Pairing                          Pearson r   Spearman ρ   Verdict
  Node-F1 vs Readability           0.82 **     0.79 **      Strong (valid)
  Edge-F1 vs Hierarchy Intuit.     0.78 **     0.74 **      Strong (valid)
  UAS vs Hierarchy Intuit.         0.81 **     0.77 **      Strong (valid)
  LabelSim vs Readability          0.65 *      0.60 *       Moderate
** p < 0.001, * p < 0.01
```

---

## 7. 综合评估汇总（Summary & Aggregation）

### 7.1 指标速查表（Quick Reference）

| # | 维度 / Dimension | 指标 / Metric | 公式（简写）/ Formula | 优秀阈值 / Threshold | 必须/可选 / Required/Optional |
|---|---|---|---|---|---|
| 1.1 | 标签质量 / Label Quality | Node-F1 | $2$PR$/($P$+$R$)$ | $\geq 0.85$ | **必须 / Required** |
| 1.2 | 标签质量 / Label Quality | Node-P | TP $/ m$ | $\geq 0.80$ | **必须 / Required** |
| 1.3 | 标签质量 / Label Quality | Node-R | TP $/ n$ | $\geq 0.85$ | **必须 / Required** |
| 1.4 | 标签质量 / Label Quality | LabelSim | mean cosine over $\mathcal{M}_\tau$ | $\geq 0.85$ | **必须 / Required** |
| 1.5 | 标签质量 / Label Quality | Entity Recall | hits $/ |E_s|$ | $\geq 0.90$ | **必须 / Required** |
| 2.1 | 层级结构 / Hierarchy | Edge-F1 | $2$PR$/($P$+$R$)$ (edge-based) | $\geq 0.80$ | **必须 / Required** |
| 2.2 | 层级结构 / Hierarchy | UAS | correct-parent $/ |\mathcal{M}_\tau|$ | $\geq 0.85$ | **必须 / Required** |
| 2.3 | 层级结构 / Hierarchy | nTED | TED $/ \max(|T_g|,|T_s|)$ | $\leq 0.25$ | **必须 / Required** |
| 2.4 | 层级结构 / Hierarchy | PC-F1 | $2\times$PCA$\times$PCP$/$ (PCA$+$PCP) | $\geq 0.75$ | 建议 / Suggested |
| 2.5 | 层级结构 / Hierarchy | LAR | depth-match $/ |\mathcal{M}_\tau|$ | $\geq 0.70$ | 建议 / Suggested |
| 3 | 下游QA / Downstream QA | QA-Score | $0.3$BLEU$+0.4$ROUGE$+0.3$BERTScore | $\geq$ 90% of control | 建议 / Suggested |
| 4.1 | 效率 / Efficiency | $T_{total}$ P50 | $\Sigma\ t_{stage}$ | $\leq$ 30s (real-time) | **必须 / Required** |
| 4.2 | STT质量 / STT Quality | WER | $(S+D+I)/N$ | $\leq 0.15$ | **必须 / Required** |
| 4.2 | STT质量 / STT Quality | KTRR | matched $/ |K_s|$ | $\geq 0.90$ | 建议 / Suggested |
| 5.1 | 多语言 / Multilingual | $\Delta$Recall | $\max_{recall} - \min_{recall}$ | $\leq 0.15$ | 建议 / Suggested |
| 5.2 | 鲁棒性 / Robustness | Recall Drop | baseline $-$ recall$_{noisy}$ | $\leq 10\%$ | 建议 / Suggested |
| 6.2 | 对齐效度 / Alignment Validity | Pearson $r$ | Node-F1 vs Human Readability | $\geq 0.70$ | **必须 / Required** |
| 6 | 人工 / Human | Overall Mean | mean(all dims) | $\geq 4.0/5.0$ | **必须 / Required** |

> **表注 / Table Notes**：
>
> - "必须 / Required"指标为论文核心评估项，建议在所有实验中报告
> - "建议 / Suggested"指标可提升评估完整性，资源受限时可省略
> - §6 人工评估从"可选"提升为"必须"——至少需要 30 个样本的相关性分析以验证自动化指标效度

---

### 7.2 综合评分公式（Composite Score）[可选]

若需将多维指标聚合为单一分数用于排行榜或模型选型：

$$
\text{Composite} = 0.20 \times \text{Node-F1} + 0.15 \times \text{Edge-F1} + 0.10 \times \text{LabelSim} + 0.10 \times \text{EntityRecall} + 0.15 \times (1 - \text{nTED}) + 0.10 \times \text{UAS} + 0.10 \times \text{PC-F1} + 0.10 \times \text{QA-Relative}
$$

其中 $\text{QA-Relative} = \text{QA-Score}_{\text{实验组}} / \text{QA-Score}_{\text{对照组}}$，衡量相对于基线的下游任务保留率。

**其中 $\text{QA-Relative}$ 为实验组与对照组的 QA-Score 比值，衡量相对于基线的下游任务保留率。**

Where $\text{QA-Relative} = \text{QA-Score}_{\text{experimental}} / \text{QA-Score}_{\text{control}}$, measuring downstream task retention relative to baseline.

> **权重调整建议 / Weight Tuning Advice**：
>
> - **教学场景**：提高 Entity Recall 权重（完整性优先）
> - **实时交互场景**：降低 STT 质量权重（速度优先）
>
> - **Teaching scenarios**: Increase Entity Recall weight (prioritize completeness).
> - **Real-time interaction scenarios**: Decrease STT quality weight (prioritize speed).

---

### 7.3 评估报告模板（Evaluation Report Template）

```text
# Mind Map Generation Quality Report
# 思维导图生成质量报告

**Lecture / 讲座**: [Lecture Title & ID]
**Date / 日期**: [YYYY-MM-DD]
**Pipeline Config / 管线配置**: [CONCEPT_MODEL / HIERARCHY_MODEL / DELTA_MODEL]

## 1. Node Label Quality / 节点标签质量
| Metric / 指标          | Value / 值 | Threshold / 阈值 | Status / 状态 |
|-----------------|-------|-----------|--------|
| Node-F1         | 0.XX  | ≥ 0.85    | PASS/FAIL |
| Node-P          | 0.XX  | ≥ 0.80    | PASS/FAIL |
| Node-R          | 0.XX  | ≥ 0.85    | PASS/FAIL |
| LabelSim        | 0.XX  | ≥ 0.85    | PASS/FAIL |
| Entity Recall   | 0.XX  | ≥ 0.90    | PASS/FAIL |

## 2. Hierarchy Accuracy / 层级结构正确率
| Metric / 指标          | Value / 值 | Threshold / 阈值 | Status / 状态 |
|-----------------|-------|-----------|--------|
| Edge-F1         | 0.XX  | ≥ 0.80    | PASS/FAIL |
| UAS             | 0.XX  | ≥ 0.85    | PASS/FAIL |
| nTED            | 0.XX  | ≤ 0.25    | PASS/FAIL |
| PC-F1           | 0.XX  | ≥ 0.75    | PASS/FAIL |

## 3. Downstream QA / 下游问答测试
| Group / 组别           | Accuracy / 准确率 | Token Cost / Token消耗 | Relative / 相对值 |
|-----------------|----------|------------|----------|
| Control (Full) / 对照组 | 0.XX     | XX,XXX     | baseline / 基线 |
| Experiment (Map) / 实验组 | 0.XX     | X,XXX      | 0.XX     |

## 4. Efficiency & STT / 效率与语音转录
| Metric / 指标          | Value / 值 | Threshold / 阈值 | Status / 状态 |
|-----------------|-------|-----------|--------|
| T_total P50     | XX.Xs | ≤ 30s     | PASS/FAIL |
| WER             | 0.XX  | ≤ 0.15    | PASS/FAIL |
| KTRR            | 0.XX  | ≥ 0.90    | PASS/FAIL |

## 5. Multilingual & Robustness / 多语言与鲁棒性 (if applicable / 如适用)
| Metric / 指标          | CN   | EN   | Mixed / 混合 | Max Δ |
|-----------------|------|------|-------|-------|
| Entity Recall   | 0.XX | 0.XX | 0.XX  | 0.XX  |

## 6. Human Alignment / 人工对齐效度
| Metric / 指标                          | Value / 值 | Threshold / 阈值 | Status / 状态 |
|-------------------------------|-------|-----------|--------|
| Pearson r (Node-F1 vs Readability) | 0.XX  | ≥ 0.70    | PASS/FAIL |

## 7. Overall / 综合评分
Composite Score / 综合评分: 0.XX / 1.00
```

---

## 8. 实现建议（Implementation Notes）

> **目标 / Goal**：
>
> **中文**：本节提供评估指标的具体实现指引，确保不同评估者独立实现时能得到一致的结果。所有代码示例使用 Python 标准库和常见开源包。
>
> **English**: This section provides concrete implementation guidance for the evaluation metrics, ensuring consistent results across independent implementations. All code examples use Python standard library and common open-source packages.

---

### 8.1 Embedding 模型选择（Embedding Model Selection）

推荐的多语言 sentence-transformer 模型（按优先级排序）：

| 模型 / Model | 维度 / Dim | 语言 / Langs | 推荐阈值 $\tau$ / Rec. $\tau$ |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 50+ | **0.70** |
| `intfloat/multilingual-e5-small` | 384 | 100+ | 0.65 |
| `intfloat/multilingual-e5-base` | 768 | 100+ | 0.65 |
| `BAAI/bge-m3` | 1024 | 100+ | 0.65 |
| `text2vec-large-chinese` | 1024 | zh | 0.72 |

> **注意 / Note**：$\tau$ 值因模型而异——嵌入维度越高、模型越大，同类概念的余弦相似度通常越高，阈值可相应降低。建议在至少 50 个标注样本上做 grid search（$\tau \in \{0.60, 0.65, 0.70, 0.75\}$），选使人工-自动化相关性最大的值。

**Python 实现 / Python Implementation**：

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
generated_labels = [n['label'] for n in generated_nodes]
gold_labels = [n['label'] for n in gold_nodes]

emb_gen = model.encode(generated_labels)
emb_gold = model.encode(gold_labels)
```

---

### 8.2 匈牙利匹配（Hungarian Matching）

使用 `scipy.optimize.linear_sum_assignment` 实现最优匹配。相似度矩阵 $S$ 需转换为成本矩阵 $C(i,j) = 1 - S(i,j)$：

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

# S: (m x n) cosine similarity matrix
cost_matrix = 1.0 - S
row_idx, col_idx = linear_sum_assignment(cost_matrix)

# Build matching pairs M* = {(row_idx[k], col_idx[k], S[row_idx[k], col_idx[k]])}
matching = list(zip(row_idx, col_idx, S[row_idx, col_idx]))

# Apply threshold tau
tau = 0.70
M_tau = [(g, s, sim) for g, s, sim in matching if sim >= tau]

# Compute TP, FP, FN
tp = len(M_tau)
fp = m - tp
fn = n - tp

node_p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
node_r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
node_f1 = 2 * node_p * node_r / (node_p + node_r) if (node_p + node_r) > 0 else 0.0
```

---

### 8.3 UAS 计算（UAS Computation）

基于节点映射 $\mu$（由 $\mathcal{M}_\tau$ 构建）计算每对匹配节点的父节点是否正确：

```python
# Build node mapping mu: gold_id -> generated_id
mu = {gold_id: gen_id for gen_id, gold_id, _ in M_tau}

# Build parent maps for both trees
gold_parent = {child: parent for parent, child in gold_edges}
gen_parent = {child: parent for parent, child in gen_edges}

correct = 0
total = 0
for gold_id, gen_id in mu.items():
    total += 1
    g_parent = gold_parent.get(gold_id)  # None if root
    gen_parent_node = gen_parent.get(gen_id)
    
    if g_parent is None and gen_parent_node is None:
        # Both are roots
        correct += 1
    elif g_parent is not None and gen_parent_node is not None:
        # Check if gen_parent matches mu(g_parent)
        expected_gen_parent = mu.get(g_parent)
        if expected_gen_parent == gen_parent_node:
            correct += 1

uas = correct / total if total > 0 else 1.0
```

---

### 8.4 相关性分析（Correlation Analysis）

使用 `scipy.stats` 计算 Pearson 和 Spearman 相关系数：

```python
from scipy.stats import pearsonr, spearmanr

# a: automated metric scores (list of floats, n >= 30)
# h: human scores (list of floats, same length)
r, r_pval = pearsonr(a, h)
rho, rho_pval = spearmanr(a, h)

print(f"Pearson r={r:.3f} (p={r_pval:.4f}), Spearman rho={rho:.3f} (p={rho_pval:.4f})")
```

> **注意 / Note**：$n \geq 30$ 是 Pearson/Spearman 达到合理统计功效的标准最小样本量。p 值 $< 0.05$ 表示相关性在统计上显著。

---

### 8.5 端到端评估管线建议（End-to-End Assessment Pipeline）

建议按以下顺序收集数据并计算指标：

1. **标准标注准备**：为 30+ 个讲座标注标准导图 JSON（`gold_{tree, nodes, links}`）
2. **自动化指标计算**：对每个生成导图，执行 §8.1–8.3 的代码，生成 Node-F1/Edge-F1/UAS 等
3. **人工评估**：5+ 名评估者按 §6.1 量表评分，汇总各维度均分
4. **相关性分析**：执行 §8.4 的代码，确认 Pearson r $\geq 0.70$
5. **报告生成**：填写 §7.3 模板

> **版本记录 / Revision History**
>
> | 版本 / Version | 日期 / Date | 变更 / Changes |
> |---|---|---|
> | v1.0 | 2026-06-22 | 初始版本：解耦树比较为标签质量与层级结构两个独立维度；扩展下游QA/效率/STT/多语言/人工评估六个维度；统一文档结构 |
> | v1.1 | 2026-06-22 | 结构优化：全文公式统一为 `$...$` / `$$...$$` 语法；新增目录(TOC)；添加 `---` 分隔线；提升 4.2.x 为 `####` 标题 |
> | v1.2 | 2026-06-22 | 视觉优化：目录改为中英双语条目；目标/参数说明使用引用块强调；并列步骤重构为有序/无序列表；表格内容精简对齐；3.1 实验设计改用表格呈现 |
> | v1.3 | 2026-06-22 | 语言级别对等修正：中文与英文具有同等地位；移除"中文为正文，英文为对照注释"等不当表述；将所有英文斜体注释改为独立完整的中英文并列表述 |
> | v1.4 | 2026-06-29 | 重构评估框架：新增 §1.1 匈牙利节点对齐作为共享基础设施；新增 §1.2 Node-P/R/F1（TP/FP/FN 混淆矩阵框架）；新增 §2.1 Edge-P/R/F1；新增 §2.2 UAS（无标签依存得分，参考 Jurafsky & Martin, 2023）；新增 §6.2 自动化-人工相关性分析（Pearson r / Spearman ρ）；§6 从可选升级为必须；§7.1 速查表新增 Node-F1/Edge-F1/UAS/Pearson r 四项指标 |
| v1.5 | 2026-06-29 | 增强自解释性与可复现性：修复 §5.1 交叉引用编号（旧版编号更新为新版 §1.3/§1.4/§2.4）；统一 §2.3–§2.5 模板格式，补全目标/方法/注意块；替换 §7.3 报告模板为新指标体系；新增 §8 实现建议附录（含 embedding 选型表、匈牙利匹配/UAS/相关性分析的完整 Python 代码） |
>
> | Version | Date | Changes |
> |---|---|---|
> | v1.0 | 2026-06-22 | Initial version: decoupled tree comparison into label quality and hierarchy accuracy; extended six dimensions. |
> | v1.1 | 2026-06-22 | Structure optimization: unified formulas; added TOC; added separators; promoted subsections. |
> | v1.2 | 2026-06-22 | Visual optimization: bilingual TOC entries; blockquotes; streamlined tables. |
> | v1.3 | 2026-06-22 | Language parity correction: Chinese and English have equal status; removed "Chinese is main text, English serves as annotation"; converted all English italic notes to standalone parallel bilingual content. |
> | v1.4 | 2026-06-29 | Evaluation framework restructure: added §1.1 Hungarian Node Alignment as shared infrastructure; added §1.2 Node-P/R/F1 (TP/FP/FN confusion matrix framework); added §2.1 Edge-P/R/F1; added §2.2 UAS (adapted from Jurafsky & Martin, 2023); added §6.2 Automated-Human Correlation Analysis; §6 upgraded from Optional to Required; §7.1 quick reference added 4 new metrics. |
> | v1.5 | 2026-06-29 | Enhanced self-explanation & reproducibility: fixed §5.1 cross-references; unified §2.3–§2.5 template format; replaced §7.3 report template with new metric suite; added §8 Implementation Notes appendix with full Python code for Hungarian matching, UAS computation, and correlation analysis. |
