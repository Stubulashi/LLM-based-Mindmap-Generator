# 思维导图评估指标说明文档（Metrics Guide）

> 本文档详细说明 AI MindMap 评估系统**最终评估报告**（`evaluation/eval_report_*.md`，由 `evaluation/report/markdown_renderer.py` 渲染）中出现的每一个指标：全称、含义、作用、计算方法、结果解读与参考值区间。
>
> 数据来源：`evaluation/core/thresholds.py`（阈值）、`evaluation/*/eval_*.py`（实现）、`Evaluation_Schema.md`（规范公式）。

---

## 1. 概述

评估系统将思维导图生成质量分解为 **7 个评估维度 + 1 个综合评分**。最终报告按以下章节输出：

| 章节 | 维度 | 核心指标 | 实现模块 |
|---|---|---|---|
| §1 | 节点标签质量（Node Label Quality） | Node-F1、Node-P、Node-R、LabelSim、Entity Recall | `evaluation/label/eval_label.py` |
| §2 | 层级结构正确率（Hierarchy Accuracy） | Edge-F1、Edge-P、Edge-R、UAS、PC-F1、LAR、nTED、Raw TED | `evaluation/hierarchy/eval_hierarchy.py` |
| §3 | 下游问答测试（Downstream QA） | Control/Experiment Accuracy、QA Retention、Token Reduction、BLEU-4、ROUGE-L、BERTScore、QA Composite | `evaluation/qa/eval_qa.py` |
| §4 | 效率与语音转录（Efficiency & STT） | T_total P50/P95、分阶段计时、STT Ratio、WER、KTRR、STT-导图相关性 | `evaluation/efficiency/eval_efficiency.py` |
| §5 | 多语言与鲁棒性（Multilingual & Robustness） | CN/EN/Mixed 指标、Max Δ、Recall Drop、Robustness Level | `evaluation/multilingual/eval_multilingual.py` |
| §6 | 人工对齐效度（Human Alignment） | Pearson r、Spearman ρ、ICC、Kendall W | `evaluation/human_correlation/eval_human_correlation.py` |
| §7 | 综合评分（Composite Score） | Composite Score 及其加权明细 | `evaluation/report/composite.py` |
| §8 | 诊断建议（Diagnostics） | 基于阈值自动生成的改进建议 | `markdown_renderer.py` |

**关键设计思想**：所有节点级与边级指标共享同一个**匈牙利节点对齐结果**（见 §2），确保标签评估与层级评估基于同一套节点对应关系，结果可复现、可互相比对。

---

## 2. 共享基础：匈牙利节点对齐（Hungarian Node Alignment）

> 这不是一个报告中的独立指标，而是 Node-P/R/F1、LabelSim、Edge-P/R/F1、UAS、LAR 等所有指标的**共享输入**。

**英文全称**：Hungarian Node Alignment

**含义**：将金标准导图的节点与生成导图的节点建立一一对应的最优匹配关系，判定"哪些节点是同一个概念"。

**计算方法**（`evaluation/core/aligner.py` 实现，共 4 步）：

1. **嵌入编码**：用多语言 embedding 模型（默认 `paraphrase-multilingual-MiniLM-L12-v2`，384 维）将每个节点标签编码为稠密向量。
2. **相似度矩阵**：计算所有金标准节点与生成节点标签之间的余弦相似度，构成矩阵 \(S \in [0,1]^{m \times n}\)。
3. **匈牙利最优指派**：将相似度矩阵转为成本矩阵 \(C(i,j) = 1 - S(i,j)\)，用匈牙利算法（`scipy.optimize.linear_sum_assignment`）求全局最优一一匹配 \(\mathcal{M}^*\)，使匹配对的相似度总和最大。
4. **阈值过滤**：引入相似度阈值 \(\tau\)（默认 **0.70**），丢弃低于阈值的低质量匹配，得到高质量匹配对集合 \(\mathcal{M}_\tau\)。

**混淆矩阵定义**（所有 P/R/F1 类指标的基础）：

- **TP（真阳性）**：通过阈值过滤的高质量匹配对数，即 |\mathcal{M}_\tau| 的大小
- **FP（假阳性）**：生成节点中未被匹配的数量，即 生成节点数 − TP（表示"冗余节点"）
- **FN（假阴性）**：金标准节点中未被匹配的数量，即 金标准节点数 − TP（表示"遗漏节点"）

**结果解读**：\(\tau=0.70\) 是 embedding 余弦相似度下"语义等价"的经验下限。低于此值通常意味着匹配不可靠（近义词混淆、跨概念误匹配）。阈值可在 0.60–0.75 范围内按 embedding 模型调优。

---

## 3. §1 节点标签质量（Node Label Quality）

> 该维度与层级结构完全解耦，只衡量"节点本身说了什么"——语义正确性、完整性与冗余程度。

### 3.1 Node-F1（节点 F1）

- **中文名**：节点 F1 分数
- **英文全称**：Node F1 Score
- **含义**：节点标签匹配质量的综合分数，同时惩罚遗漏（召回不足）和冗余（精确率不足）。
- **作用**：衡量生成导图的节点集合与金标准节点集合的整体重合程度，是标签质量的核心指标。
- **计算方法**：
  \[
  \text{Node-P} = \frac{TP}{TP+FP},\quad \text{Node-R} = \frac{TP}{TP+FN},\quad \text{Node-F1} = \frac{2 \times P \times R}{P + R}
  \]
  其中 TP/FP/FN 来自匈牙利节点对齐（见本文档第 2 节）。边界情况：TP=FP=0 且 FN>0 时 P=0；TP=FN=0 且 FP>0 时 R=0。
- **结果解读**：Node-F1 高说明生成节点的数量与内容都接近金标准；F1 偏低时需区分是 FN 高（概念遗漏，检查概念抽取阶段）还是 FP 高（冗余节点，检查 LLM 是否过度生成）。
- **参考值区间**：≥ 0.85 优秀；0.70 – 0.84 良好；< 0.70 需改进。

### 3.2 Node-P（节点精确率）

- **中文名**：节点精确率
- **英文全称**：Node Precision
- **含义**：生成节点中"确实是金标准中概念"的比例。
- **作用**：衡量生成导图的**冗余程度**——生成一堆不相关节点会拉低精确率。
- **计算方法**：\(\text{Node-P} = TP / (TP + FP) = TP / |V_g|\)
- **结果解读**：Node-P 低说明生成图存在大量多余/无关节点，需收紧概念抽取或减少 LLM 过度生成。
- **参考值区间**：≥ 0.80 优秀；0.65 – 0.79 良好；< 0.65 需改进。

### 3.3 Node-R（节点召回率）

- **中文名**：节点召回率
- **英文全称**：Node Recall
- **含义**：金标准中的概念被生成导图覆盖的比例。
- **作用**：衡量生成导图的**完整性**——漏掉关键概念会拉低召回率。
- **计算方法**：\(\text{Node-R} = TP / (TP + FN) = TP / |V_s|\)
- **结果解读**：Node-R 低说明金标准中的多个概念未被生成，可能是 STT 转录丢失或概念抽取遗漏。
- **参考值区间**：≥ 0.85 优秀；0.70 – 0.84 良好；< 0.70 需改进。

### 3.4 LabelSim（标签语义相似度）

- **中文名**：标签语义相似度
- **英文全称**：Label Semantic Similarity
- **含义**：在已正确匹配（TP）的节点对上，匹配标签之间的平均余弦相似度。
- **作用**：衡量"匹配上的标签到底有多像"——即使节点匹配上了，用词仍可能有差异（如 "LLM" vs "Large Language Model"）。
- **计算方法**（`eval_label.py`）：仅对 \(\mathcal{M}_\tau\) 中的匹配对计算余弦相似度的算术平均：
  \[
  \text{LabelSim} = \frac{1}{|\mathcal{M}_\tau|} \sum_{(i,j) \in \mathcal{M}_\tau} S(i,j)
  \]
  当无匹配对时定义为 0。理论范围 \([\tau, 1.0]\)。
- **结果解读**：LabelSim 高说明生成标签与金标准用词高度一致；低说明存在同义改写或措辞偏差（语义接近但不完全一致）。
- **参考值区间**：≥ 0.85 优秀（高度一致）；0.75 – 0.84 良好；< 0.75 需改进（语义偏差显著）。

### 3.5 Entity Recall（实体/核心概念召回率）

- **中文名**：实体召回率（核心概念召回率）
- **英文全称**：Entity Recall（Core Concept Recall）
- **含义**：预先定义的核心概念集合 \(E_s\) 中，有多少比例出现在生成导图的任意节点标签或 details 中。
- **作用**：衡量导图对**教学关键知识点**的覆盖度，是知识完整性的直接体现。核心概念集可通过 `evaluation/data/concepts/*.json` 提供；未提供时自动从金标准节点标签提取。
- **计算方法**（`eval_label.py`）：对每个核心概念 \(e \in E_s\)，计算它与生成导图所有文本（节点 label + details）的最大 embedding 余弦相似度，≥ τ 记为"命中"：
  \[
  \text{Entity Recall} = \frac{\text{命中概念数}}{|E_s|}
  \]
- **结果解读**：Entity Recall 高说明关键知识点几乎无遗漏；低时会明确列出"遗漏概念"清单（如报告中的 Missed concepts），可用于定位 STT 转录或概念抽取的问题。
- **参考值区间**：≥ 0.90 优秀；0.75 – 0.89 良好；< 0.75 需改进（存在关键知识缺口）。

---

## 4. §2 层级结构正确率（Hierarchy Accuracy）

> 该维度独立衡量父子关系、从属关系的准确性，不与节点标签质量混淆。所有指标依赖本文档第 2 节所述的匈牙利对齐结果 \(\mathcal{M}_\tau\)。

### 4.1 Edge-F1 / Edge-P / Edge-R（边级 F1/精确率/召回率）

- **中文名**：边精确率-召回率-F1
- **英文全称**：Edge Precision / Recall / F1
- **含义**：生成导图的有向边（父子关系）与金标准边的一致性，同时惩罚缺失边和多余边。
- **作用**：衡量父子连接关系的准确程度，是层级结构的核心指标。
- **计算方法**（`eval_hierarchy.py`）：利用节点映射 \(\mu\)（由 \(\mathcal{M}_\tau\) 构建），金标准边 \((s_p, s_c)\) 判定为 TP 当且仅当两端节点都被映射且映射后的边存在于生成边集中：
  \[
  \text{Edge-P} = \frac{TP_{\text{edge}}}{|E_g|},\quad \text{Edge-R} = \frac{TP_{\text{edge}}}{|E_s|},\quad \text{Edge-F1} = \frac{2 \times P \times R}{P + R}
  \]
  边界情况：\(|E_s|=0\) 时 Edge-R=1.0；\(|E_g|=0\) 时 Edge-P=1.0。
- **结果解读**：Edge-F1 低说明层级规划阶段的父子关系错误较多。报告中会给出 TP/FP/FN 明细（Correct/Extra/Missing edges）。Edge-P 低 → 多余边多；Edge-R 低 → 缺失边多。
- **参考值区间**：Edge-F1 ≥ 0.80 优秀；0.65 – 0.79 良好；< 0.65 需改进。

### 4.2 UAS（无标签依存得分）

- **中文名**：无标签依存得分
- **英文全称**：Unlabeled Attachment Score
- **含义**：以节点为视角，衡量"每个已匹配生成节点的父节点是否正确"。
- **作用**：借鉴依存句法分析经典指标（Jurafsky & Martin, 2023），比 Edge-R 更宽容——只统计已匹配节点，不受标签失败影响。
- **计算方法**（`eval_hierarchy.py`）：对 \(\mathcal{M}_\tau\) 中每个匹配的金标准节点 \(s\)，检查其生成对应节点的父节点是否等于其金标准父节点的映射节点（根节点特殊处理：两边都是根则判正确）：
  \[
  \text{UAS} = \frac{\text{父节点正确的匹配节点数}}{|\mathcal{M}_\tau|}
  \]
- **结果解读**：UAS 低说明大量节点的父级分配错误（节点找对了位置放错了）。与 Edge-R 对比：Edge-R 以边为单位（分母 \(|E_s|\)），UAS 以节点为单位（分母 \(|\mathcal{M}_\tau|\)）。
- **参考值区间**：≥ 0.85 优秀；0.70 – 0.84 良好；< 0.70 需改进。

### 4.3 PC-F1（父子关系 F1）

- **中文名**：父子关系 F1
- **英文全称**：Parent-Child F1
- **含义**：基于标签语义相似度直接比对父子节点对，不依赖匈牙利对齐。
- **作用**：与本文档 4.1 节的 Edge-F1 互补——Edge-F1 基于对齐后的节点映射，PC-F1 基于标签本身。两者越接近，说明节点对齐质量越高。
- **计算方法**（`eval_hierarchy.py`）：将金标准的父子标签对与生成的父子标签对逐一比较，一对判定为"正确"当且仅当父标签相似度 ≥ τ 且子标签相似度 ≥ τ（一对一匹配避免重复计数）：
  \[
  \text{PCA} = \frac{\text{正确父子对数}}{\text{金标准父子对数}},\quad \text{PC-Precision} = \frac{\text{正确父子对数}}{\text{生成父子对数}},\quad \text{PC-F1} = \frac{2 \times \text{PCA} \times \text{PC-Precision}}{\text{PCA} + \text{PC-Precision}}
  \]
- **结果解读**：PC-F1 低说明父子"标签组合"层面就不匹配，可能是层级规划阶段结构错误或标签用词偏差。
- **参考值区间**：≥ 0.75 优秀；0.60 – 0.74 良好；< 0.60 需改进。

### 4.4 LAR（层级对齐率）

- **中文名**：层级对齐率
- **英文全称**：Level Alignment Rate
- **含义**：已匹配节点在树中的层级深度（根=0）与金标准一致的比例。
- **作用**：衡量生成导图是否保持了每个概念的抽象层级正确性（概念该放第几层）。
- **计算方法**（`eval_hierarchy.py`）：对 \(\mathcal{M}_\tau\) 中每个匹配对比较深度：
  \[
  \text{LAR} = \frac{|\{(g,s) \in \mathcal{M}_\tau \mid \text{depth}(g) = \text{depth}(s)\}|}{|\mathcal{M}_\tau|}
  \]
- **结果解读**：LAR 高说明节点不仅在内容上匹配，层级深度也一致；低说明概念被放到了错误的抽象层级（如把二级概念当成了根节点的兄弟）。
- **参考值区间**：≥ 0.70 优秀；0.50 – 0.69 良好；< 0.50 需改进。

### 4.5 nTED（归一化树编辑距离）与 Raw TED

- **中文名**：归一化树编辑距离
- **英文全称**：normalized Tree Edit Distance
- **含义**：将生成树转换为金标准树所需的最少编辑操作数（插入/删除/重标记/变更父节点），经节点数归一化后的值。**越低越好**。
- **作用**：以单一分数量化两棵树的整体结构差异，是结构相似度的全局度量。
- **计算方法**（`eval_hierarchy.py`）：使用 Zhang-Shasha 算法（`zss` 库）计算原始距离后再归一化：
  \[
  \text{nTED} = \frac{\text{TED}(T_g, T_s)}{\max(|T_g|, |T_s|)}
  \]
  若 `zss` 库未安装，报告中 nTED 显示为 N/A。
- **结果解读**：nTED 越低说明树结构越接近金标准。注意：当两树节点数悬殊时，nTED 可能因分母过大而低估差异，建议与 Edge-F1、UAS 综合判断。
- **参考值区间**：≤ 0.25 优秀；0.25 – 0.40 良好；> 0.40 需改进。
- **Raw TED**：归一化前的原始编辑距离，仅作参考展示，无独立阈值。

---

## 5. §3 下游问答测试（Downstream QA）

> 不直接评价导图，而是考察"基于该导图能否回答好问题"——这是衡量数据结构信息密度的黄金标准（需要 LLM API 和预置问题集）。

### 5.1 Control Accuracy（对照组准确率）与 Experiment Accuracy（实验组准确率）

- **英文全称**：Control Group Accuracy / Experiment Group Accuracy
- **含义**：对照组（LLM 阅读**完整逐字稿**）与实验组（LLM 仅阅读**生成导图**）对同一批问题的作答准确率。
- **作用**：对照组作为基线，实验组体现导图的信息保留能力。
- **计算方法**（`eval_qa.py`）：对每轮 LLM 回答与标准答案做精确字符串匹配（忽略大小写），3 轮取平均。
- **结果解读**：实验组准确率越高，说明导图承载的信息越完整、越可用。
- **参考值区间**：无独立阈值，以对照组为基准比较（见 QA Retention）。

### 5.2 QA Retention（QA 保留率）

- **中文名**：QA 信息保留率
- **英文全称**：QA Retention Rate
- **含义**：实验组准确率相对对照组准确率的比值，衡量导图对信息量的"压缩保留"能力。
- **计算方法**：
  \[
  \text{QA Retention} = \frac{\text{Experiment Accuracy}}{\text{Control Accuracy}}
  \]
- **结果解读**：若 ≥ 90% 且 Token 消耗大幅降低，则证明导图具有高效的信息压缩能力。
- **参考值区间**：≥ 0.90 优秀；0.75 – 0.89 良好；< 0.75 需改进。

### 5.3 Token Reduction（Token 缩减率）

- **中文名**：Token 消耗缩减率
- **英文全称**：Token Reduction Rate
- **含义**：用导图作答相比用逐字稿作答的输入 Token 估算缩减比例。
- **计算方法**（`eval_qa.py`）：按字符数粗估 Token（中文 1.5 字符/token，英文 4 字符/token）：
  \[
  \text{Token Reduction} = 1 - \frac{\text{导图估算 Token}}{\text{逐字稿估算 Token}}
  \]
- **结果解读**：高值说明导图极大地压缩了输入规模（通常 >70%）。无独立阈值，配合 QA Retention 使用。

### 5.4 BLEU-4 / ROUGE-L / BERTScore / QA Composite

- **中文名**：BLEU-4（4-gram 精度）、ROUGE-L（最长公共子序列 F 值）、BERTScore（语义相似度）、QA 综合分
- **英文全称**：Bilingual Evaluation Understudy (4-gram Precision) / Recall-Oriented Understudy for Gisting Evaluation (Longest Common Subsequence) / BERT-based Score / QA Composite Score
- **含义**：三种机器翻译/摘要领域的经典文本相似度指标，用于衡量 LLM 答案与标准答案的文本重合度与语义贴近度；QA Composite 为三者加权综合。
- **作用**：弥补精确匹配准确率过于严苛的不足（答案措辞不同但语义正确时，精确匹配会判错）。
- **计算方法**（`eval_qa.py`）：
  - **BLEU-4**：答案与标准答案的 4-gram 精度（nltk，带平滑）。
  - **ROUGE-L**：最长公共子序列的 F 值（rouge-score 库），对长答案更友好。
  - **BERTScore**：基于 contextual embedding 的 F1（bert-score 库，默认 `lang="en"`）。
  - \[
    \text{QA Composite} = 0.3 \times \text{BLEU-4} + 0.4 \times \text{ROUGE-L} + 0.3 \times \text{BERTScore}
    \]
- **结果解读**：三者高说明答案与标准答案高度一致；BERTScore 对近义词改写更宽容，BLEU/ROUGE 对文本重合更敏感。
- **参考值区间**：无独立阈值（依赖库可用性，缺失时返回 0.0 并打印警告）。

---

## 6. §4 生成效率与语音转录（Efficiency & STT）

> 量化从音频输入到导图输出的全流程效率，以及上游 STT 质量对下游导图质量的影响。

### 6.1 T_total P50 / P95（端到端总延迟）

- **中文名**：端到端总延迟第 50/95 百分位
- **英文全称**：Total End-to-End Latency (P50 / P95)
- **含义**：从音频加载到导图输出（STT + 导图生成全流程）的总耗时，P50 为典型值，P95 为最差情况（95% 请求不超过此值）。
- **作用**：衡量系统响应速度，是实时交互可用性的关键指标。每个样本重复测量（默认 1 次，建议 5 次）后取百分位数。
- **计算方法**（`eval_efficiency.py`）：使用 `time.perf_counter()` 打点，汇总各阶段耗时：
  \[
  T_{total} = t_{stt} + t_{concept} + t_{hierarchy} + t_{delta} + t_{polish}
  \]
- **结果解读**：P50 ≤ 30s 满足实时交互目标；P50 > 60s 仅适合批量处理。
- **参考值区间**（越低越好）：P50 ≤ 30s 优秀、≤ 60s 良好；P95 ≤ 60s 优秀、≤ 120s 良好。

### 6.2 分阶段计时（Staged Timing）

- **中文名**：各管线阶段计时
- **英文全称**：Per-Stage Timing（STT / Concept / Hierarchy / Delta / Polish / Map Gen）
- **含义**：管线各阶段的 P50/P95 耗时及与内置标准的对比（✅ PASS / ❌ FAIL）。
- **作用**：定位延迟瓶颈所在阶段。报告中展示 STT、Map Gen（概念+层级+Delta+润色合并）、Total 三行；详细阶段数据见 `staged_timing`。
- **计算方法**：每个阶段用高精度计时器打点，重复测量后计算百分位数，并与 `DEFAULT_STANDARDS`（可被自定义 JSON 覆盖）对比。
- **结果解读**：某阶段 FAIL 即该阶段耗时超标，优先优化该模块（如 STT 慢则换转录模型，概念提取慢则换轻量 LLM）。
- **参考值区间**（越低越好，P50）：STT ≤ 30s 优秀、≤ 45s 良好；Concept/Hierarchy/Delta ≤ 5s 优秀、≤ 8s 良好；Polish ≤ 3s 优秀、≤ 5s 良好；Map Gen ≤ 18s 优秀、≤ 30s 良好。

### 6.3 STT Ratio（STT 耗时占比）

- **中文名**：STT 耗时占比
- **英文全称**：STT Time Ratio
- **含义**：STT 阶段耗时占总延迟的比例。
- **计算方法**：\(\text{STT Ratio} = t_{stt}^{P50} / T_{total}^{P50}\)
- **结果解读**：占比过高说明系统瓶颈在语音转录环节。
- **参考值区间**（越低越好）：≤ 40% 优秀（实时交互目标）；≤ 50% 良好；> 50% 需改进。

### 6.4 WER（词错率）

- **中文名**：词错率
- **英文全称**：Word Error Rate
- **含义**：STT 转录文本与人工转写标准文本之间的词级错误比例。**越低越好**。
- **作用**：衡量语音转录的准确性，是上游质量的核心指标。
- **计算方法**（`eval_efficiency.py`）：使用 `jiwer` 库：
  \[
  \text{WER} = \frac{S + D + I}{N} = \frac{\text{替换数 + 删除数 + 插入数}}{\text{标准文本总词数}}
  \]
  中文文本先经 `jieba` 分词再计算；`jiwer` 未安装时返回 0.0 且方法标记为 `unavailable`。
- **结果解读**：WER 越低转录越准；WER > 0.15 时会触发诊断建议"检查音频质量或更换模型"。
- **参考值区间**（越低越好）：≤ 0.15 优秀（即 ≥85% 转写准确率）；0.15 – 0.30 良好；> 0.30 需改进。

### 6.5 KTRR（关键术语保留率）

- **中文名**：关键术语保留率
- **英文全称**：Key Term Retention Rate
- **含义**：预先定义的领域关键术语集合 \(K_s\) 中有多少比例出现在 STT 输出中。
- **作用**：衡量转录对专业术语的保真度——术语丢失会直接导致下游概念缺失。
- **计算方法**（`eval_efficiency.py`）：模糊匹配（允许 1 字符编辑距离容错）：
  \[
  \text{KTRR} = \frac{|\{k \in K_s \mid k \in \text{STT\_output}\}|}{|K_s|}
  \]
- **结果解读**：KTRR 低说明 STT 丢失了专业术语，是 Entity Recall 下降的常见上游原因。
- **参考值区间**：≥ 0.90 优秀；0.80 – 0.89 良好；< 0.80 需改进。

### 6.6 STT-导图相关性（Pearson r / Spearman ρ）

- **中文名**：STT 质量与导图质量相关性
- **英文全称**：STT-to-Map Quality Correlation
- **含义**：WER（横轴）与 Entity Recall（纵轴）之间的相关系数，衡量 STT 质量对导图质量的影响程度。
- **计算方法**（`eval_efficiency.py`）：用 `scipy.stats.pearsonr` / `spearmanr` 计算（需要 ≥3 个样本）。
- **结果解读**：|ρ| > 0.7 → STT 是导图质量的重要瓶颈，优先优化 STT；|ρ| < 0.3 → 管线具备 STT 容错能力。
- **参考值区间**：|ρ| ≤ 0.10 强容错；0.10 – 0.25 中等；> 0.25 弱容错（对 Recall Drop 而言，见本文档 7.3 节）。

---

## 7. §5 多语言适应性与鲁棒性（Multilingual & Robustness）

### 7.1 CN / EN / Mixed 三组指标

- **中文名**：纯中文 / 纯英文 / 中英混合测试
- **英文全称**：Chinese-only / English-only / Chinese-English Mixed Test Sets
- **含义**：对三种语言组成（100% 中文、100% 英文、中英混合）分别计算 Entity Recall、LabelSim、PC-F1。
- **作用**：考察系统对不同语言（尤其中英混合输入）的支持度。
- **计算方法**（`eval_multilingual.py`）：每组独立运行标签与层级评估，汇总三组数值。
- **结果解读**：三组数值应大致接近，若某组明显偏低则说明系统对该语言支持不足。
- **参考值区间**：三组指标差异（Max Δ）应 ≤ 0.15（15%），即性能不应随语言显著分化。

### 7.2 Max Δ（组间最大差异）

- **中文名**：组间最大差异
- **英文全称**：Maximum Delta across groups
- **含义**：三种语言组中同一指标的最大值与最小值之差。
- **作用**：量化语言间的性能分化程度。
- **计算方法**：\(\text{Max Δ} = \max(\text{cn}, \text{en}, \text{mixed}) - \min(\text{cn}, \text{en}, \text{mixed})\)
- **结果解读**：Δ 越大说明语言间性能越不均衡。
- **参考值区间**：≤ 0.15 优秀；0.15 – 0.25 良好；> 0.25 需改进。

### 7.3 Recall Drop（召回衰减率）与 PC-F1 Drop

- **中文名**：召回衰减率 / 父子 F1 衰减率
- **英文全称**：Entity Recall Drop / PC-F1 Drop under noise
- **含义**：向文本注入字符级噪声（替换/删除/插入，概率 p ∈ {0.00, 0.05, 0.10, 0.15, 0.20}）后，导图质量相对无噪声基线的衰减百分比。
- **作用**：衡量系统在噪声（模拟 STT 错误）环境下的稳定性。
- **计算方法**（`eval_multilingual.py`）：
  \[
  \text{Recall Drop} = \frac{\text{baseline Recall} - \text{noisy Recall}}{\text{baseline Recall}} \times 100\%
  \]
- **结果解读**：衰减越小越鲁棒。
- **参考值区间**（越低越好）：在 WER≈0.10 处，Recall Drop ≤ 10% 为强鲁棒；10% – 25% 为中等鲁棒；> 25% 为弱鲁棒（对应阈值 excellent=0.10, good=0.25）。

### 7.4 Robustness Level（鲁棒性级别）

- **中文名**：鲁棒性级别
- **英文全称**：Robustness Level
- **含义**：综合 Recall Drop 得出的整体鲁棒性结论（强/中等/弱鲁棒）。
- **作用**：一句话结论，便于快速判断系统对 STT 噪声的敏感度。
- **判定规则**：取最接近 0.10 的噪声水平的 Recall Drop：≤10% → 强鲁棒；10–25% → 中等鲁棒；>25% → 弱鲁棒。

---

## 8. §6 人工对齐效度（Human Alignment）

> 通过自动化指标与人工评分的相关性，验证自动化指标是否有意义（效标效度）。

### 8.1 Pearson r 与 Spearman ρ

- **中文名**：Pearson 积差相关系数 / Spearman 等级相关系数
- **英文全称**：Pearson Product-Moment Correlation Coefficient / Spearman's Rank Correlation Coefficient
- **含义**：自动化指标分数与人工评分（5 点 Likert 量表）之间的相关性。
- **作用**：验证"自动化高分是否对应人类评估者认为的好导图"。报告中主要展示 **Node-F1 vs Readability（可读性）** 的 r 与 ρ；实现中还计算 Edge-F1 vs Hierarchy Intuitiveness、UAS vs Hierarchy、LabelSim vs Readability 等配对。
- **计算方法**（`eval_human_correlation.py`，`scipy.stats`）：
  \[
  r = \frac{\sum (a_i - \bar{a})(h_i - \bar{h})}{\sqrt{\sum (a_i - \bar{a})^2} \cdot \sqrt{\sum (h_i - \bar{h})^2}},\quad
  \rho = 1 - \frac{6\sum d_i^2}{n(n^2 - 1)}
  \]
  要求至少 30 个样本；任一序列为常数（方差为 0）时跳过计算返回 0。
- **结果解读**：r ≥ 0.70 强相关 → 自动化指标有效，可替代人工评估；0.40 – 0.69 中等 → 部分有效，需结合人工；< 0.40 弱 → 指标需重新设计。
- **参考值区间**：≥ 0.70 优秀；0.40 – 0.69 良好；< 0.40 需改进。

### 8.2 ICC 与 Kendall's W

- **中文名**：组内相关系数 / 肯德尔和谐系数
- **英文全称**：Intraclass Correlation Coefficient (ICC(3,k)) / Kendall's Coefficient of Concordance (W)
- **含义**：多位人工评分者之间的一致性程度。
- **作用**：确保人工评分本身可靠（评分者间信度），否则相关性分析无意义。
- **计算方法**：目标 ≥ 0.70（当前实现为占位，未实际计算；依赖 `human_scores` 中的 `raters` 数据）。
- **参考值区间**：≥ 0.70 优秀；0.50 – 0.69 良好；< 0.50 需改进。

---

## 9. §7 综合评分（Composite Score）

- **中文名**：综合评分
- **英文全称**：Composite Score
- **含义**：将各维度核心指标按权重聚合为 0–1 的单一分数，用于排行榜或模型选型。
- **作用**：快速横向对比不同模型/配置的整体质量。
- **计算方法**（`evaluation/report/composite.py`）：

  \[
  \text{Composite} = 0.20 \times \text{Node-F1} + 0.15 \times \text{Edge-F1} + 0.10 \times \text{LabelSim}
  \]
  \[
  + 0.10 \times \text{EntityRecall} + 0.15 \times (1-\text{nTED}) + 0.10 \times \text{UAS} + 0.10 \times \text{PC-F1} + 0.10 \times \text{QA-Relative}
  \]

  其中 `nted_inv = 1 - nTED`（nTED 越低越好，故取反）；`qa_relative` 使用 QA Retention（未执行 QA 时该成分不参与）。

- **归一化逻辑（重要）**：未执行/缺失的维度会从总分中**剔除其权重并对剩余权重重新归一化**（`score / total_weight_used`）。因此两份报告的综合分只有在评估维度集合相同时才可直接比较。报告中会注明"Only X% of total weight was evaluated"。
- **各成分权重一览**：

  | 成分 | 权重 | 说明 |
  |---|---|---|
  | node_f1 | 0.20 | 节点标签质量（权重最高） |
  | edge_f1 | 0.15 | 边级层级结构 |
  | nted_inv | 0.15 | 树结构全局相似度 |
  | label_sim | 0.10 | 标签语义贴近度 |
  | entity_recall | 0.10 | 核心概念覆盖 |
  | uas | 0.10 | 父节点分配正确率 |
  | pc_f1 | 0.10 | 父子标签对匹配 |
  | qa_relative | 0.10 | 下游 QA 信息保留 |

- **结果解读**：综合分 ≥ 0.85 整体质量优秀；0.70 – 0.84 良好；< 0.70 关键领域需改进。评分仅覆盖已评估的维度，缺失维度越多，综合分参考价值越低。
- **参考值区间**：≥ 0.85 优秀；≥ 0.70 良好；< 0.70 需改进。

---

## 10. 参考值区间速查表

> 表中"优秀/良好"为 `evaluation/core/thresholds.py` 中的 `excellent` / `good` 边界值；箭头方向表示指标"越高越好 ↑"或"越低越好 ↓"。未列出的指标（如 Raw TED、BLEU-4 等）无独立阈值。

### 10.1 节点标签与层级结构（§1–§2）

| 指标 | 全称 | 方向 | 优秀 | 良好 | 需改进 |
|---|---|---|---|---|---|
| Node-F1 | Node F1 Score | ↑ | ≥ 0.85 | 0.70–0.84 | < 0.70 |
| Node-P | Node Precision | ↑ | ≥ 0.80 | 0.65–0.79 | < 0.65 |
| Node-R | Node Recall | ↑ | ≥ 0.85 | 0.70–0.84 | < 0.70 |
| LabelSim | Label Semantic Similarity | ↑ | ≥ 0.85 | 0.75–0.84 | < 0.75 |
| Entity Recall | Core Concept Recall | ↑ | ≥ 0.90 | 0.75–0.89 | < 0.75 |
| Edge-F1 | Edge F1 Score | ↑ | ≥ 0.80 | 0.65–0.79 | < 0.65 |
| UAS | Unlabeled Attachment Score | ↑ | ≥ 0.85 | 0.70–0.84 | < 0.70 |
| nTED | normalized Tree Edit Distance | ↓ | ≤ 0.25 | 0.25–0.40 | > 0.40 |
| PC-F1 | Parent-Child F1 | ↑ | ≥ 0.75 | 0.60–0.74 | < 0.60 |
| LAR | Level Alignment Rate | ↑ | ≥ 0.70 | 0.50–0.69 | < 0.50 |

### 10.2 下游 QA（§3）

| 指标 | 方向 | 优秀 | 良好 | 需改进 |
|---|---|---|---|---|
| QA Retention | ↑ | ≥ 0.90 | 0.75–0.89 | < 0.75 |
| Token Reduction | ↑ | 通常期望 > 70% | — | — |

### 10.3 效率与 STT（§4）

| 指标 | 方向 | 优秀 | 良好 | 需改进 |
|---|---|---|---|---|
| T_total P50 | ↓ | ≤ 30s | 30–60s | > 60s |
| T_total P95 | ↓ | ≤ 60s | 60–120s | > 120s |
| STT Ratio | ↓ | ≤ 0.40 | 0.40–0.50 | > 0.50 |
| STT 阶段 P50 | ↓ | ≤ 30s | 30–45s | > 45s |
| STT 阶段 P95 | ↓ | ≤ 60s | 60–90s | > 90s |
| Concept/Hierarchy/Delta P50 | ↓ | ≤ 5s | 5–8s | > 8s |
| Polish P50 | ↓ | ≤ 3s | 3–5s | > 5s |
| Map Gen P50 | ↓ | ≤ 18s | 18–30s | > 30s |
| WER | ↓ | ≤ 0.15 | 0.15–0.30 | > 0.30 |
| KTRR | ↑ | ≥ 0.90 | 0.80–0.89 | < 0.80 |

### 10.4 多语言与鲁棒性（§5）

| 指标 | 方向 | 优秀 | 良好 | 需改进 |
|---|---|---|---|---|
| Max Δ（三组间差异） | ↓ | ≤ 0.15 | 0.15–0.25 | > 0.25 |
| Recall Drop @WER≈0.10 | ↓ | ≤ 10% | 10%–25% | > 25% |

### 10.5 人工对齐效度（§6）

| 指标 | 方向 | 优秀 | 良好 | 需改进 |
|---|---|---|---|---|
| Pearson r / Spearman ρ | ↑ | ≥ 0.70 | 0.40–0.69 | < 0.40 |
| ICC / Kendall's W | ↑ | ≥ 0.70 | 0.50–0.69 | < 0.50 |

### 10.6 综合评分（§7）

| 指标 | 优秀 | 良好 | 需改进 |
|---|---|---|---|
| Composite Score | ≥ 0.85 | 0.70–0.84 | < 0.70 |

---

## 11. 报告解读示例

以 `evaluation/eval_report_Saarland University 1_20260730_111823.md` 的片段为例：

```
| Node-F1 | 0.500 | ≥ 0.85 | ⚠️ Needs Improvement | ❌ FAIL |
| LabelSim | 0.851 | ≥ 0.85 | 🏆 Excellent | ✅ PASS |
| Entity Recall | 0.667 | ≥ 0.90 | ⚠️ Needs Improvement | ❌ FAIL |
```

**逐项解读**：

1. **Node-F1 = 0.500**：节点匹配质量不佳。配合下方匈牙利详情 `TP=2, FP=3, FN=1` 可定位原因——FP=3 说明生成图多了 3 个冗余节点，FN=1 说明漏了 1 个金标准节点。诊断建议会提示"收紧概念抽取阈值或减少 LLM 过度生成"。
2. **LabelSim = 0.851**：虽然节点数量对不上，但**匹配上的 2 对**节点（"Explanation part"↔"Explanation Part" 0.9986、"E-dictionaries"↔"Electronic Dictionaries" 0.7031）语义高度接近，说明标签措辞质量本身不错。
3. **Entity Recall = 0.667**：3 个核心概念只命中 2 个，遗漏 "Word Gender"，诊断建议会指向"检查该术语的 STT 转录"。

**联动关系小结**：
- 若 Node-F1 低但 LabelSim 高 → 问题在"节点数量/冗余"，不在"措辞"。
- 若 Entity Recall 低 → 优先查 STT 转录与概念抽取，而不是层级规划。
- 若 Edge-F1 低但 UAS 尚可 → 缺失边多（召回不足）；若两者都低 → 父级分配系统性错误。
- 若 Edge-F1 与 PC-F1 结果接近 → 节点对齐质量好；差异大 → 对齐或标签用词有问题。

---

## 12. 注意事项与常见陷阱

1. **指标降级（不可用时为 0 或 N/A）**：
   - `nTED`：`zss` 库未安装时显示 N/A。
   - `WER`：`jiwer` 未安装时返回 0.0 且方法标记 `unavailable`——此时 **0.0 不代表转录完美**，需看 `WER Method` 一栏确认。
   - `BERTScore`：`bert-score` / `torch` 未安装时返回 0.0。
   - `STT-to-Map 相关性`：样本 < 3 时不计算。

2. **空集边界值**：金标准或生成导图为空时，P/R 会取特殊值（Edge-P/R 空集时为 1.0），导致 F1 出现看似矛盾的数值（如空导图的 Edge-P=1.000、Edge-F1=0.000），需结合 TP/FP/FN 明细解读。

3. **综合分的可比性**：综合分只在评估维度集合一致时可比。缺失维度会重新归一化，报告中 "Only X% of total weight was evaluated" 提示缺失情况。

4. **nTED 的规模敏感性**：两树节点数悬殊时 nTED 可能低估差异，需配合 Edge-F1、UAS 综合判断，勿只看单一指标。

5. **指标间不是孤立的**：Node-F1/Edge-F1/UAS 都建立在同一个匈牙利对齐（τ=0.70）之上；τ 改变会同时影响所有相关指标。评估报告间对比时应使用相同的 embedding 模型与 τ。

6. **Entity Recall 概念集的来源**：未提供核心概念集时自动从金标准节点标签提取，此时 Entity Recall 与 Node-R 高度重叠；使用独立概念集（`data/concepts/`）才能体现其独立价值。

7. **QA 的随机性**：LLM 回答存在随机性，报告默认重复 3 轮取平均；精确匹配准确率对措辞敏感，解读时应结合 BLEU/ROUGE/BERTScore 综合判断。

8. **WER=0 的双重含义**：可能是转录完美，也可能是 `jiwer` 不可用或文本为空——务必查看 `WER Method` 与 `Samples` 列。

---

*本文档依据 Evaluation_Schema.md v1.5 与 evaluation/ 模块代码整理，指标名称与阈值以代码为准。*
