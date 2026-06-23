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
  - [1.1 标签语义相似度 / Label Semantic Similarity](#11-标签语义相似度label-semantic-similarity)
  - [1.2 核心概念召回率 / Entity Recall](#12-核心概念召回率entity-recall)
  - [1.3 重要节点遗漏率 / Miss Rate](#13-重要节点遗漏率miss-rate)
  - [1.4 多余/无关节点引入率 / Precision & FDR](#14-多余无关节点引入率precision--false-discovery-rate)
- [2. 层级结构正确率评估 / Hierarchy Structure Accuracy](#2-层级结构正确率评估hierarchy-structure-accuracy)
  - [2.1 树编辑距离 / Tree Edit Distance (TED)](#21-树编辑距离tree-edit-distance-ted)
  - [2.2 父子关系准确率 / Parent-Child Accuracy](#22-父子关系准确率parentchild-relationship-accuracy)
  - [2.3 层级对齐率 / Level Alignment Rate](#23-层级对齐率level-alignment-rate)
  - [2.4 推荐实现方案对比 / Recommended Approaches](#24-推荐实现方案对比recommended-approaches)
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
- [6. 人工评估维度 [可选] / Human Evaluation [Optional]](#6-人工评估维度-可选human-evaluation-optional)
  - [6.1 评分维度与量表 / Scoring Dimensions & Rubric](#61-评分维度与量表scoring-dimensions--rubric)
  - [6.2 评分表样例 / Sample Scoring Sheet](#62-评分表样例sample-scoring-sheet)
- [7. 综合评估汇总 / Summary & Aggregation](#7-综合评估汇总summary--aggregation)
  - [7.1 指标速查表 / Quick Reference](#71-指标速查表quick-reference)
  - [7.2 综合评分公式 / Composite Score [可选]](#72-综合评分公式composite-score可选)
  - [7.3 评估报告模板 / Evaluation Report Template](#73-评估报告模板evaluation-report-template)

---

## 1. 节点标签质量评估（Node Label Quality Assessment）

> **目标 / Goal**：
>
> **中文**：独立衡量生成节点标签（label）的语义正确性、完整性以及冗余程度。该维度与层级结构完全解耦，仅关注"节点本身说了什么"。
>
> **English**: Independently measure the semantic correctness, completeness, and redundancy of generated node labels. This dimension is entirely decoupled from hierarchy structure and focuses solely on "what the node itself says".

---

### 1.1 标签语义相似度（Label Semantic Similarity）

**方法 / Method**：

使用通用 multilingual embedding 模型（推荐 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` 或 `text2vec-large-chinese`），将生成节点的 label 与标准标注节点的 label 分别编码为稠密向量，计算余弦相似度（Cosine Similarity），并取宏观平均作为最终得分。

**使用通用 multilingual embedding 模型，将生成节点标签与标准标注标签编码为稠密向量，计算余弦相似度并取宏观平均作为最终得分。**

Use a general multilingual embedding model to encode generated and gold-standard labels into dense vectors, compute pairwise cosine similarity, and take the macro-average as the final score.

**公式 / Formula**：

设生成节点标签集合 $L_g = \{l_{g1}, l_{g2}, ..., l_{gm}\}$，标准标注标签集合 $L_s = \{l_{s1}, l_{s2}, ..., l_{sn}\}$。

**设生成标签集合为 $L_g$，标准标注标签集合为 $L_s$。**

Let generated labels be $L_g$ and gold-standard labels be $L_s$.

计算步骤如下：

1. **最优匹配对齐（Hungarian Algorithm）**：先对每对 $(l_{gi}, l_{sj})$ 计算余弦相似度得到相似度矩阵 $S \in [0,1]^{m \times n}$，再使用匈牙利算法求解最优一一匹配（将 $m$ 个生成标签对齐到最相似的 $n$ 个标准标签），得到匹配对集合 $\mathcal{M}$。

2. **宏观平均**：

$$
\text{LabelSim} = \frac{1}{|\mathcal{M}|} \sum_{(i,j) \in \mathcal{M}} \text{cosine}(\mathbf{v}_{gi}, \mathbf{v}_{sj})
$$

其中 $\mathbf{v}_{gi} = \text{embed}(l_{gi})$，$\mathbf{v}_{sj} = \text{embed}(l_{sj})$。

> **注意 / Note**：
>
> - 若 $m < n$（生成节点少于标准），未匹配的标准标签贡献为 0，降低宏观平均。
>
> - If $m < n$ (generated nodes fewer than gold-standard), unmatched gold labels contribute 0 to the average, penalizing under-generation.

**参考阈值 / Reference Threshold**：

| 等级 / Grade | LabelSim | 说明 / Description |
|---|---|---|
| 优秀 / Excellent | $\geq$ 0.80 | 标签语义高度一致 / labels semantically highly consistent |
| 良好 / Good | 0.65 – 0.79 | 大体一致，少量偏差 / mostly consistent, minor deviations |
| 需改进 / Needs Improvement | $<$ 0.65 | 语义偏差显著 / significant semantic drift |

**示例输出 / Example Output**：

```text
Gold labels:    ["Large Language Model", "Attention Mechanism", "Transformer Architecture"]
Generated:      ["LLM", "Attention", "Transformer"]
Cosine Matrix:  [[0.92, 0.35, 0.48],
                 [0.28, 0.96, 0.62],
                 [0.41, 0.55, 0.94]]
Optimal Match:  (LLM->Large Language Model, Attention->Attention Mechanism, Transformer->Transformer Architecture)
LabelSim = (0.92 + 0.96 + 0.94) / 3 = 0.940  -> Excellent
```

---

### 1.2 核心概念召回率（Entity Recall）

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

---

### 1.3 重要节点遗漏率（Miss Rate）

**方法 / Method**：

Entity Recall 的互补指标，直接衡量遗漏程度。从标准标注树中识别未被生成导图覆盖的节点。

**Entity Recall 的互补指标，直接衡量遗漏程度。**

Complementary to Entity Recall; measures omission directly. Identify gold-standard nodes not covered by the generated map.

**公式 / Formula**：

$$
\text{MissRate} = 1 - \frac{|\text{covered\_labels}|}{|L_s|} = 1 - \text{Label-level Recall}
$$

> **说明 / Note**：
>
> - $\text{covered\_labels}$：标准 label $l_s$ 在生成节点集合中能找到相似度 $\geq 0.70$ 的匹配
> - 推荐使用匈牙利匹配结果判定覆盖关系，比简单阈值匹配更精确
>
> - $\text{covered\_labels}$: gold labels with a match in generated nodes (cosine $\geq 0.70$).
> - Using Hungarian matching is recommended for more accurate coverage determination.

**参考阈值 / Reference Threshold**：`MissRate` $\leq 0.20$（即至少覆盖 80% 的标准节点）。

---

### 1.4 多余/无关节点引入率（Precision / False Discovery Rate）

**方法 / Method**：

衡量生成导图中"画蛇添足"的程度。对每个生成节点 label，检查其是否能在标准标注集中找到语义相似度 $\geq 0.70$ 的对应项；若不能，则标记为"无关引入"。

**衡量生成导图中"画蛇添足"的程度。对每个生成标签检查是否能在标准集中找到语义相似度匹配。**

For each generated label, check if a semantically similar match (cosine $\geq 0.70$) exists in the gold-standard set. If not, mark it as an extraneous introduction.

**公式 / Formula**：

$$
\text{Precision} = \frac{|\text{matched\_generated\_labels}|}{|L_g|}
$$

$$
\text{FDR (False Discovery Rate)} = 1 - \text{Precision} = \frac{|\text{extraneous\_labels}|}{|L_g|}
$$

**参考阈值 / Reference Threshold**：`Precision` $\geq 0.75$，即无关引入率 $\leq 25\%$。

**示例输出 / Example Output**：

```text
Generated labels (|Lg|=12): [LLM, Agent, MCP, ReAct, RAG, "AI is cool", Transformer, ...]
Matched to gold:            [LLM, Agent, MCP, ReAct, RAG, ..., Transformer]  -> 10 matched
Extraneous:                 ["AI is cool", "Future of AI"]  -> 2 extraneous
Precision = 10 / 12 = 0.833  -> Good
FDR = 2 / 12 = 0.167
```

---

## 2. 层级结构正确率评估（Hierarchy Structure Accuracy）

> **目标 / Goal**：
>
> **中文**：独立衡量父子关系、从属关系的准确性，不与节点标签质量混淆。关注"节点之间的从属关系是否正确"，而非"节点本身是什么"。
>
> **English**: Independently measure parent-child and subordination accuracy, without conflating with label quality. Focus on "whether the subordinate relationships between nodes are correct", not "what the node itself is".

---

### 2.1 树编辑距离（Tree Edit Distance, TED）

**方法 / Method**：

计算将生成导图树结构 $T_g$ 转换为标准标注树 $T_s$ 所需的最少编辑操作次数（插入节点、删除节点、替换节点标签、变更父子关系）。距离越小，层级结构越接近标准。

**计算将生成导图树转换为标准标注树所需的最少编辑操作次数。**

Compute the minimum number of tree edit operations (insert node, delete node, relabel, change parent) required to transform $T_g$ into $T_s$. Smaller distance = closer hierarchy.

**公式 / Formula**：

$$
\text{nTED} = \frac{\text{TED}(T_g, T_s)}{\max(|T_g|, |T_s|)}
$$

> **符号说明 / Notation**：
>
> - $|T|$ 为树的节点数。归一化后使不同规模的树可比。
>
> - $|T|$ is the number of nodes in tree T. Normalization makes trees of different sizes comparable.

**参考阈值 / Reference Threshold**：`nTED` $\leq 0.25$

**实现建议 / Implementation**：推荐使用 `zss`（Zhang-Shasha 算法）或 `apted` Python 库。

---

### 2.2 父子关系准确率（Parent-Child Relationship Accuracy）

**方法 / Method**：

将标准标注中的父子节点对 $(p_s, c_s)$ 与生成导图中的父子节点对 $(p_g, c_g)$ 进行匹配。一对父子关系被判定为"正确"，当且仅当父节点和子节点的 label 均能在对方集合中找到语义匹配。

**将标准标注中的父子节点对与生成导图中的父子节点对进行匹配。**

A parent-child pair is judged "correct" iff both the parent and child labels can be semantically matched across the gold and generated maps.

**公式 / Formula**：

$$
\text{PCA} = \frac{|\text{correct\_parent\_child\_pairs}|}{|\text{gold\_parent\_child\_pairs}|}
$$

$$
\text{PC-Precision} = \frac{|\text{correct\_parent\_child\_pairs}|}{|\text{generated\_parent\_child\_pairs}|}
$$

$$
\text{PC-F1} = \frac{2 \times \text{PCA} \times \text{PC-Precision}}{\text{PCA} + \text{PC-Precision}}
$$

**参考阈值 / Reference Threshold**：`PC-F1` $\geq 0.75$

---

### 2.3 层级对齐率（Level Alignment Rate）

**方法 / Method**：

统计生成节点与标准节点层级深度一致的比例。节点的层级深度定义为其到根节点的最短路径长度。通过匈牙利匹配先对齐节点，再比较匹配对的层级深度。

**统计生成节点与标准节点层级深度一致的比例。**

Count the proportion of generated nodes whose depth (shortest path to root) matches their aligned gold-standard counterpart.

**公式 / Formula**：

$$
\text{LAR} = \frac{|\{(g, s) \in \mathcal{M} \mid \text{depth}(g) = \text{depth}(s)\}|}{|\mathcal{M}|}
$$

其中 $\mathcal{M}$ 为匈牙利匹配得到的节点对集合。

**参考阈值 / Reference Threshold**：`LAR` $\geq 0.70$

---

### 2.4 推荐实现方案对比（Recommended Approaches）

| 维度 | 方案 A：TED + PC Accuracy | 方案 B：Embedding 子树匹配 |
|---|---|---|
| **核心思路** | 经典树编辑距离 + 父子对精确比对 | 节点嵌入向量与层级特征拼接后进行结构对齐 |
| **优点** | 精确、可解释、有成熟理论体系；适合论文严格评估 | 计算速度快（$O(n^2)$ vs TED 指数级最坏）；大规模导图友好 |
| **缺点** | 大型树（$>100$ 节点）TED 开销大，需剪枝优化 | 依赖 embedding 质量；可解释性较弱 |
| **适用场景** | 正式评估报告、论文核心指标 | 快速迭代评估、A/B 测试 |
| **推荐库** | `zss`, `apted` | `sentence-transformers` + 自写匹配逻辑 |

**推荐策略 / Recommended Strategy**：

- **正式论文**：方案 A 作为主指标，方案 B 作为辅助验证
- **工程迭代**：方案 B 用于日常回归测试

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

- Entity Recall（1.2 节）
- Label Semantic Similarity（1.1 节）
- PC-F1（2.2 节）

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

## 6. 人工评估维度 [可选]（Human Evaluation [Optional]）

> **目标 / Goal**：
>
> **中文**：补充自动化指标无法覆盖的主观体验维度，包括可读性、布局合理性和教学实用性。
>
> **English**: Supplement automated metrics with subjective experience dimensions including readability, layout reasonableness, and pedagogical utility.

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

---

### 6.2 评分表样例（Sample Scoring Sheet）

```text
Evaluator ID: E03
Map ID: lecture_07_MCP_deep_dive
Date: 2026-06-22

Dimension             Score (1-5)   Comments
────────────────────────────────────────────────────────
Readability           4             标签简洁，偶有缩写不明确
Layout                3             部分三级节点拥挤，建议增加间距
Information Density   4             核心概念覆盖全面
Pedagogical Utility   5             非常适合期中复习使用
Hierarchy Intuit.     4             大部分从属关系合理，1处值得商榷

Overall (mean): 4.0 / 5.0
```

**评分者间一致性 / Inter-rater Reliability**：计算 ICC(3,k) 或 Kendall's W，目标 $\geq 0.70$。

---

## 7. 综合评估汇总（Summary & Aggregation）

### 7.1 指标速查表（Quick Reference）

| # | 维度 / Dimension | 指标 / Metric | 公式（简写）/ Formula | 优秀阈值 / Threshold | 必须/可选 / Required/Optional |
|---|---|---|---|---|---|
| 1.1 | 标签质量 / Label Quality | LabelSim | cosine macro-avg | $\geq 0.80$ | **必须 / Required** |
| 1.2 | 标签质量 / Label Quality | Entity Recall | hits / $|E_s|$ | $\geq 0.90$ | **必须 / Required** |
| 1.3 | 标签质量 / Label Quality | Miss Rate | $1 -$ Recall | $\leq 0.20$ | 建议 / Suggested |
| 1.4 | 标签质量 / Label Quality | Precision | matched / $|L_g|$ | $\geq 0.75$ | **必须 / Required** |
| 2.1 | 层级结构 / Hierarchy | nTED | TED / $\max(|T_g|,|T_s|)$ | $\leq 0.25$ | **必须 / Required** |
| 2.2 | 层级结构 / Hierarchy | PC-F1 | $2\times$PCA$\times$PCP/(PCA+PCP) | $\geq 0.75$ | **必须 / Required** |
| 2.3 | 层级结构 / Hierarchy | LAR | depth-match / $|\mathcal{M}|$ | $\geq 0.70$ | 建议 / Suggested |
| 3 | 下游QA / Downstream QA | QA-Score | $0.3$BLEU$+0.4$ROUGE$+0.3$BERTScore | $\geq$ 90% of control | 建议 / Suggested |
| 4.1 | 效率 / Efficiency | $T_{total}$ P50 | $\Sigma\ t_{stage}$ | $\leq$ 30s (real-time) | **必须 / Required** |
| 4.2 | STT质量 / STT Quality | WER | $(S+D+I)/N$ | $\leq 0.15$ | **必须 / Required** |
| 4.2 | STT质量 / STT Quality | KTRR | matched / $|K_s|$ | $\geq 0.90$ | 建议 / Suggested |
| 5.1 | 多语言 / Multilingual | $\Delta$Recall | $\max_{recall} - \min_{recall}$ | $\leq 0.15$ | 建议 / Suggested |
| 5.2 | 鲁棒性 / Robustness | Recall Drop | baseline $-$ recall$_{noisy}$ | $\leq 10\%$ | 建议 / Suggested |
| 6 | 人工 / Human | Overall Mean | mean(all dims) | $\geq 4.0/5.0$ | 可选 / Optional |

> **表注 / Table Notes**：
>
> - "必须 / Required"指标为论文核心评估项，建议在所有实验中报告
> - "建议 / Suggested"指标可提升评估完整性，资源受限时可省略
> - "可选 / Optional"指标适用于有用户调研条件的场景
>
> - "Required" metrics are core evaluation items for papers and should be reported in all experiments.
> - "Suggested" metrics enhance evaluation completeness and may be omitted under resource constraints.
> - "Optional" metrics apply to scenarios with user research conditions.

---

### 7.2 综合评分公式（Composite Score）[可选]

若需将多维指标聚合为单一分数用于排行榜或模型选型：

$$
\text{Composite} = 0.25 \times \text{LabelSim} + 0.20 \times \text{EntityRecall} + 0.10 \times \text{Precision} + 0.20 \times (1 - \text{nTED}) + 0.15 \times \text{PC-F1} + 0.10 \times \text{QA-Relative}
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
| LabelSim        | 0.XX  | ≥ 0.80    | PASS/FAIL |
| Entity Recall   | 0.XX  | ≥ 0.90    | PASS/FAIL |
| Precision       | 0.XX  | ≥ 0.75    | PASS/FAIL |
| Miss Rate       | 0.XX  | ≤ 0.20    | PASS/FAIL |

## 2. Hierarchy Accuracy / 层级结构正确率
| Metric / 指标          | Value / 值 | Threshold / 阈값 | Status / 状态 |
|-----------------|-------|-----------|--------|
| nTED            | 0.XX  | ≤ 0.25    | PASS/FAIL |
| PC-F1           | 0.XX  | ≥ 0.75    | PASS/FAIL |

## 3. Downstream QA / 下游问答测试
| Group / 组别           | Accuracy / 准确率 | Token Cost / Token消耗 | Relative / 相对值 |
|-----------------|----------|------------|----------|
| Control (Full) / 对照组 | 0.XX     | XX,XXX     | baseline / 基线 |
| Experiment (Map) / 实验组 | 0.XX     | X,XXX      | 0.XX     |

## 4. Efficiency & STT / 效率与语音转录
| Metric / 指标          | Value / 值 | Threshold / 阈값 | Status / 状态 |
|-----------------|-------|-----------|--------|
| T_total P50     | XX.Xs | ≤ 30s     | PASS/FAIL |
| WER             | 0.XX  | ≤ 0.15    | PASS/FAIL |
| KTRR            | 0.XX  | ≥ 0.90    | PASS/FAIL |

## 5. Multilingual & Robustness / 多语言与鲁棒性 (if applicable / 如适用)
| Metric / 指标          | CN   | EN   | Mixed / 混合 | Max Δ |
|-----------------|------|------|-------|-------|
| Entity Recall   | 0.XX | 0.XX | 0.XX  | 0.XX  |

## 6. Overall / 综合评分
Composite Score / 综合评分: 0.XX / 1.00
```

---

> **版本记录 / Revision History**
>
> | 版本 / Version | 日期 / Date | 变更 / Changes |
> |---|---|---|
> | v1.0 | 2026-06-22 | 初始版本：解耦树比较为标签质量与层级结构两个独立维度；扩展下游QA/效率/STT/多语言/人工评估六个维度；统一文档结构 |
> | v1.1 | 2026-06-22 | 结构优化：全文公式统一为 `$...$` / `$$...$$` 语法；新增目录(TOC)；添加 `---` 分隔线；提升 4.2.x 为 `####` 标题 |
> | v1.2 | 2026-06-22 | 视觉优化：目录改为中英双语条目；目标/参数说明使用引用块强调；并列步骤重构为有序/无序列表；表格内容精简对齐；3.1 实验设计改用表格呈现 |
> | v1.3 | 2026-06-22 | 语言级别对等修正：中文与英文具有同等地位；移除"中文为正文，英文为对照注释"等不当表述；将所有英文斜体注释改为独立完整的中英文并列表述 |
>
> | Version | Date | Changes |
> |---|---|---|
> | v1.0 | 2026-06-22 | Initial version: decoupled tree comparison into label quality and hierarchy accuracy; extended six dimensions. |
> | v1.1 | 2026-06-22 | Structure optimization: unified formulas; added TOC; added separators; promoted subsections. |
> | v1.2 | 2026-06-22 | Visual optimization: bilingual TOC entries; blockquotes; streamlined tables. |
> | v1.3 | 2026-06-22 | Language parity correction: Chinese and English have equal status; removed "Chinese is main text, English serves as annotation"; converted all English italic notes to standalone parallel bilingual content. |
