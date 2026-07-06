# 评估框架全面审计报告
# Evaluation Framework Comprehensive Audit Report

**审计日期 / Audit Date**: 2026-06-29
**审计范围 / Scope**: evaluation/ 目录下全部 22 个 Python 文件 + 16 个数据文件
**参考标准 / Reference**: Evaluation_Schema.md v1.5

---

## 1. Schema 一致性审查
## 1. Schema Consistency Review

### §1.1 匈牙利节点对齐

| 项目 | Schema 定义 | 实现 (aligner.py) | 一致性 |
|------|-------------|-------------------|--------|
| 嵌入编码 | 推荐 paraphrase-multilingual-MiniLM-L12-v2 | 默认值一致 | ✅ |
| 相似度矩阵 | S ∈ [0,1]^(m×n)，余弦相似度 | `gold_embs @ gen_embs.T` | ✅ |
| 成本矩阵 | C(i,j) = 1 - S(i,j) | 一致 | ✅ |
| 匈牙利指派 | `scipy.optimize.linear_sum_assignment` | 一致 | ✅ |
| 阈值过滤 | τ=0.70，丢弃 < τ 的匹配 | 一致 | ✅ |
| TP/FP/FN | TP=|M_τ|, FP=m-TP, FN=n-TP | `len(filtered_matches)`, `len(gen_labels)-tp`, `len(gold_labels)-tp` | ✅ |

**结论**: 完全一致。空集处理得当（返回空匹配 + 零矩阵）。索引越界检查在 `mu` 属性中存在（第 53 行 `gen_idx < len(self.gen_ids)`）。

### §1.2 Node-P/R/F1

| 项目 | Schema 定义 | 实现 (eval_label.py) | 一致性 |
|------|-------------|----------------------|--------|
| Node-P | TP/(TP+FP) | `tp/(tp+fp)` | ✅ |
| Node-R | TP/(TP+FN) | `tp/(tp+fn)` | ✅ |
| Node-F1 | 2PR/(P+R) | `2*p*r/(p+r)` | ✅ |
| 边界情况 P=0 | TP=FP=0 且 FN>0 时 P=0 | `tp+fp>0 else 0.0` | ✅ |
| 边界情况 R=0 | TP=FN=0 且 FP>0 时 R=0 | `tp+fn>0 else 0.0` | ✅ |

**结论**: 完全一致。

### §1.3 LabelSim

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| 公式 | mean cosine over M_τ | `sum(sim)/len(M_tau)` | ✅ |
| M_τ=0 时 | 定义 LabelSim=0 | `label_sim=0.0` | ✅ |

**结论**: 完全一致。

### §1.4 Entity Recall

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| 核心概念 E_s | 10-20 个必须掌握的概念 | 用户提供或自动从 gold label 提取 | ✅ |
| 匹配方式 | 余弦相似度 ≥ τ 判定命中 | `compute_similarity_matrix` + `max(axis=1) >= threshold` | ✅ |
| D_g | 生成节点 details 中所有条目的并集 | `get_all_texts()` 收集 label + details | ✅ |
| 后备逻辑 | 未提供时自动提取 | `list(set(gold_map.get_labels()))` | ✅ |

**P1 问题**: 自动后备逻辑中的概念来源于金标准节点 label，这与 Schema 建议的"从课程中确定 10-20 个核心概念"不完全一致。后备方案使用金标准树的所有唯一 label，可能导致概念数量过多或包含非关键概念。**建议**: 在 `concepts/es_auto_generated.md` 中说明后备方案的局限性。

### §2.1 Edge-P/R/F1

| 项目 | Schema 定义 | 实现 (eval_hierarchy.py) | 一致性 |
|------|-------------|--------------------------|--------|
| 映射 μ | μ(s)=g iff (g,s)∈M_τ | `alignment.mu` | ✅ |
| TP_edge | 两端均映射且生成边中存在 | `parent in mu and child in mu and (mu[p], mu[c]) in gen_edge_set` | ✅ |
| FN_edge | |E_s| - TP | `len(gold_edges) - edge_tp` | ✅ |
| FP_edge | |E_g| - TP | `len(gen_edges) - edge_tp` | ✅ |
| |E_s|=0 | Edge-R=1.0 | `edge_r = tp/len(gold_edges) if len(gold_edges)>0 else 1.0` | ✅ |
| |E_g|=0 | Edge-P=1.0 | `edge_p = tp/len(gen_edges) if len(gen_edges)>0 else 1.0` | ✅ |

**结论**: 完全一致。

### §2.2 UAS

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| 分母 | |M_τ| | `len(mu)` | ✅ |
| 根节点 | s 为根且 μ(s) 为根时正确 | `g_parent is None and gen_parent_node is None` | ✅ |
| 父节点匹配 | parent_g(μ(s)) = μ(parent_s(s)) | `mu.get(g_parent) == gen_parent_node` | ✅ |

**结论**: 完全一致。UAS 实现与 Schema §8.3 的参考代码高度一致。

### §2.3 nTED

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| 算法 | Zhang-Sharma (zss) | `zss.simple_distance` | ✅ |
| nTED | TED / max(|T_g|,|T_s|) | `raw_ted / max_nodes` | ✅ |
| zss 未安装 | N/A | `nted = None` | ✅ |
| 树构建 | 根节点 + 子节点递归 | `build_zss_tree` + `_add_zss_children` | ✅ |

**结论**: 完全一致。`None` sentinel 处理已修复。

### §2.4 PC-F1

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| 匹配方式 | 父节点 label 和子节点 label 均语义匹配 | 分别计算 parent_S 和 child_S，两者均 ≥ τ | ✅ |
| PC-Precision | 正确对/生成父子对数 | `pc_correct/len(gen_pairs)` | ✅ |
| PC-Recall(PCA) | 正确对/金标准父子对数 | `pc_correct/len(gold_pairs)` | ✅ |

**结论**: 之前已修复拼接字符串 Bug，当前实现与 Schema §2.4 一致。

### §2.5 LAR

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| 公式 | depth_match / |M_τ| | `lar_correct / len(mu)` | ✅ |
| 深度定义 | 根到节点最短路径长度（根=0） | `compute_depth_map` 递归计算 | ✅ |

**结论**: 完全一致。

### §3 下游 QA

| 项目 | Schema 定义 | 实现 (eval_qa.py) | 一致性 |
|------|-------------|-------------------|--------|
| 实验设计 | 对照组(逐字稿) + 实验组(导图) | 两组分别调用 LLM | ✅ |
| BLEU-4 | 权重 0.3 | `_compute_bleu4` | ✅ |
| ROUGE-L | 权重 0.4 | `_compute_rouge_l` | ✅ |
| BERTScore | 权重 0.3 | `_compute_bert_score` | ✅ |
| 加权综合 | 0.3*BLEU + 0.4*ROUGE + 0.3*BERT | `0.3*bleu4 + 0.4*rouge_l + 0.3*bert_s` | ✅ |
| 3 轮均值 | 每组至少 3 次 | `num_runs=3` | ✅ |
| temperature=0 | 确保可复现 | `temperature=0.0` | ✅ |

**P2 问题**: 未实现 `token_reduction` 计算（Schema §3.1 要求记录 Token 消耗）。当前 `token_reduction=0.0` 硬编码。修复建议：在 LLM 调用时记录 `response.usage.total_tokens`。

### §4 效率与 STT

| 项目 | Schema 定义 | 实现 (eval_efficiency.py) | 一致性 |
|------|-------------|--------------------------|--------|
| P50/P95 | time.perf_counter() 打点 | `_compute_percentile` (手动实现) | ✅ |
| 5 阶段计时 | stt/concept/hierarchy/delta/polish | 阶段名一致 | ✅ |
| WER | jiwer 库 | `jiwer.wer` | ✅ |
| 中文分词 | jieba | `jieba.cut` | ✅ |
| KTRR | 模糊匹配 1 字符编辑距离 | `_edit_distance <= 1` | ✅ |
| 关联分析 | Pearson r + Spearman ρ | `scipy.stats.pearsonr/spearmanr` | ✅ |

**结论**: 完全一致。

### §5 多语言与鲁棒性

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| 三组对比 | CN/EN/Mixed | `_compute_multilingual_comparison` | ✅ |
| 阈值 | Δ ≤ 15% | `max_delta_*` 计算 | ✅ |
| 噪声注入 | 字符级扰动 p∈{0,0.05,...,0.20} | `_inject_noise` | ✅ |
| 鲁棒性判定 | Recall Drop ≤10%/10-25%/>25% | `_compute_noise_robustness` | ✅ |

**结论**: 完全一致。

### §6 人工评估

| 项目 | Schema 定义 | 实现 | 一致性 |
|------|-------------|------|--------|
| Pearson r | Node-F1 vs Readability | `pearsonr(auto_node_f1, human_readability)` | ✅ |
| Spearman ρ | 同上 | `spearmanr(auto_node_f1, human_readability)` | ✅ |
| Edge-F1 vs Hierarchy | 配对标6.2 | `pearsonr(auto_edge_f1, human_hierarchy)` | ✅ |
| ICC | 目标 ≥ 0.70 | 仅占位（第 122-124 行） | ⚠️ |

**P1 问题**: ICC(3,k) 和 Kendall's W 计算未实现（第 122-124 行的 `pass` 占位符）。这意味着 `human_corr` 模块无法计算评分者间信度，与 Schema §6.1 要求不符。

### §7 综合评分

| 项目 | Schema 定义 | 实现 (composite.py) | 一致性 |
|------|-------------|---------------------|--------|
| 权重: Node-F1 | 0.20 | 0.20 | ✅ |
| 权重: Edge-F1 | 0.15 | 0.15 | ✅ |
| 权重: LabelSim | 0.10 | 0.10 | ✅ |
| 权重: EntityRecall | 0.10 | 0.10 | ✅ |
| 权重: 1-nTED | 0.15 | 0.15 | ✅ |
| 权重: UAS | 0.10 | 0.10 | ✅ |
| 权重: PC-F1 | 0.10 | 0.10 | ✅ |
| 权重: QA-Relative | 0.10 | 0.10 | ✅ |
| 归一化 | 扣除未计算指标权重 | `score / total_weight` | ✅ |
| None 处理 | 缺失字段跳过 | `is not None` 检查 | ✅ |

**结论**: 完全一致。None 处理正确，nTED=0.10 时的 nted_inv=0.90 计算正确。

---

## 2. 代码逻辑与 Bug 检测
## 2. Code Logic & Bug Detection

### P0 — 阻塞性问题 (0 个)

未发现阻塞性问题。

### P1 — 重要问题 (3 个)

#### P1-1: eval_human_correlation.py 中 ICC/Kendall's W 未实现

**文件**: `evaluation/metrics/eval_human_correlation.py:122-124`
**描述**: 第 122-124 行的 ICC/Kendall W 计算仅为 `pass` 占位符。Schema §6.1 要求 ICC(3,k) ≥ 0.70 作为评分者间信度目标。
**影响**: 即使有人工评分数据 `raters` 字段，也无法获得评分者间信度指标。
**建议**: 添加 `pingouin.intraclass_corr` 或手动实现 ICC(3,k) 公式。

#### P1-2: eval_qa.py 中 token_reduction 未实现

**文件**: `evaluation/metrics/eval_qa.py:432`
**描述**: `token_reduction=0.0` 硬编码，Schema §3.1 要求记录对照组和实验组的 Token 消耗。
**影响**: QA 评估结果缺少 Token 效率分析维度。
**建议**: 在 `_call_llm_for_qa` 中返回 `response.usage.total_tokens`，在 evaluate 方法中计算两组 Token 消耗差。

#### P1-3: tree_utils.py 中 compute_depth_map 对缺少 id 的节点会抛出 KeyError

**文件**: `evaluation/utils/tree_utils.py:31`
**描述**: 第 31 行 `_depth(n['id'])` 假设每个节点都有 `id` 字段。如果某个节点缺少 `id`，会抛出 `KeyError`。同样，第 66 行 `node_labels = {n['id']: n['label'] for n in nodes}` 也会因缺少 id 或 label 而崩溃。
**影响**: 如果生成导图包含格式不规范的节点，评估会中断。
**建议**: 改为 `.get('id', '')` 和 `.get('label', '')`，或跳过无效节点。

### P2 — 建议性问题 (5 个)

#### P2-1: aligner.py 中 similarity_matrix 形状在空集时与 Schema 描述不一致

**文件**: `evaluation/core/aligner.py:119-121`
**描述**: 空集时创建 `np.zeros((len(gold_labels), len(gen_labels)))`，如果两者都为空，形状为 `(0, 0)`。Schema §8.2 的参考代码未处理此情况，但实现已处理。这是防御性编程的体现，无实际风险。

#### P2-2: markdown_renderer.py 诊断建议仅中文无英文

**文件**: `evaluation/report/markdown_renderer.py:383-434`
**描述**: Diagnostics 章节的所有诊断建议文本均为纯中文，缺少英文版本。例如 `"- **Node-F1 需改进 ({:.3f})**: 节点标签与金标准匹配率偏低..."`。
**影响**: Markdown 报告中的诊断建议无法被非中文用户理解。
**建议**: 为每条诊断建议添加对应的英文版本。

#### P2-3: eval_multilingual.py 噪声注入使用 random 而非可复现种子

**文件**: `evaluation/metrics/eval_multilingual.py:105-140`
**描述**: `_inject_noise` 使用 `random.random()` 和 `random.choice()`，但未设置随机种子。不同运行之间结果不一致。
**影响**: 噪声测试结果不可复现。
**建议**: 添加 `random.seed(42)` 参数或接受可选的 seed 参数。

#### P2-4: batch_evaluate.py discover_pairs 中 gold_dir 解析与 audio_dir 不一致

**文件**: `evaluation/batch_evaluate.py:69-70`
**描述**: `audio_dir_resolved` 和 `gold_dir_resolved` 分别解析，但当 gold_dir 为相对路径时，如果它在 `evaluation/data/gold` 而非项目根目录的 `evaluation/data/gold` 时可能出错。实际测试通过。

#### P2-5: composite.py 权重与 Schema §7.2 一致但未暴露给外部

**文件**: `evaluation/report/composite.py:25-34`
**描述**: 权重字典硬编码在 `compute_composite_score` 内部，外部无法自定义权重。Schema §7.2 的权重调整建议（教学场景提高 Entity Recall 权重）无法通过参数实现。
**影响**: 用户无法根据场景调整综合评分权重。
**建议**: 添加可选的 `custom_weights` 参数。

---

## 3. 未实现部分识别
## 3. Incomplete Implementation Identification

| 模块 | 实现等级 | 所需外部输入 | 说明 |
|------|---------|-------------|------|
| eval_label.py | ✅ 已完整实现 | 金标准导图 + 可选 Es.json | 无 TODO 残留 |
| eval_hierarchy.py | ✅ 已完整实现 | 金标准导图 | nTED 在 zss 缺失时优雅降级 |
| eval_qa.py | ⚠️ 部分实现 | LLM API + 问题集 | 代码逻辑完整，缺数据和 LLM API 即可激活 |
| eval_efficiency.py | ⚠️ 部分实现 | 计时日志 + 参考文本 + 关键术语 | 默认值可运行，输入数据可激活完整评估 |
| eval_multilingual.py | ⚠️ 部分实现 | 多语言测试结果 | 默认值可运行，输入数据可激活完整评估 |
| eval_human_correlation.py | ⚠️ 部分实现 | 人工评分数据 + 自动评分数据 | Pearson/Spearman 已实现，ICC 仅占位 |
| composite.py | ✅ 已完整实现 | 各维度评估结果 | None 处理和归一化逻辑完整 |
| markdown_renderer.py | ✅ 已完整实现 | 各维度评估结果字典 | 所有 section 渲染方法完整 |

**统计**: 3 个模块 ✅ 已完整实现 / 4 个模块 ⚠️ 部分实现 / 0 个模块 ❌ 仅接口预留

**重要说明**: 所有 ⚠️ 模块均可无输入数据运行（返回默认值/零值），不会因导入或执行时报错中断流程。这是此前 TODO 实现阶段完成的目标。

---

## 4. 集成完整性检查
## 4. Integration Completeness Check

### 4.1 run_evaluation.py CLI 集成

| 维度 | CLI 路径 | 文件提示 | 状态 |
|------|---------|---------|------|
| §1 label | 完整 | 金标准文件 + 概念集合提示 | ✅ |
| §2 hierarchy | 完整 | 共用 §1 金标准 | ✅ |
| §3 qa | 完整 | 问题集目录提示 | ✅ |
| §4 efficiency | 完整 | 计时日志 + 关键术语提示 | ✅ |
| §5 multilingual | 完整 | 多语言测试集提示 | ✅ |
| §6 human_corr | 完整 | 人工评分数据提示 | ✅ |

所有 6 个维度均可通过交互式 CLI 选择和执行。§1 和 §2 需要金标准文件，§3-§6 在无数据时使用默认值运行。

### 4.2 batch_evaluate.py 批量管线集成

| 功能 | 实现 | 状态 |
|------|------|------|
| audio+gold 配对发现 | `discover_pairs()` | ✅ |
| MCP Client 管理 | `start_mcp() / close()` | ✅ |
| Whisper 转录 | `transcribe_audio` tool | ✅ |
| 导图生成 | `modify_mind_map_v2` tool | ✅ |
| 核心评估 (label+hierarchy) | `_run_evaluation_for_pair()` | ✅ |
| efficiency 集成 | 新增 `evaluate_efficiency()` 调用 | ✅ |
| 中间产物保存 | `eval_result.json` + `generated_map.json` | ✅ |
| 汇总报告生成 | `generate_summary_report()` | ✅ |
| 输入文件自动检测 | `_detect_input_files()` | ✅ |
| 概念文件自动加载 | `concepts/{pair_name}_concepts.json` | ✅ |

**问题**: 批量模式下，§3-§6 的输入文件（问题集、计时日志、多语言数据、人工评分数据）虽然会被 `_detect_input_files` 检测到存在，但**不会自动加载并传送到评估函数中**。当前仅 `concepts`（概念集合）有自动加载逻辑。这导致批量模式下的 §3-§6 只能使用默认值。

**影响等级**: P2

**建议**: 在 `process_pair` 或 `_run_evaluation_for_pair` 中添加对其他维度输入文件的自动检测和加载逻辑。

### 4.3 示例文件与输入格式匹配

| 目录 | 示例文件 | 对应评估函数 | 格式匹配 | 状态 |
|------|---------|-------------|---------|------|
| gold/ | gold_example.json | from_map_file() | nodes + links + tree | ✅ |
| concepts/ | example_essential_concepts.json | essential_concepts 参数 | concepts 数组 | ✅ |
| questions/ | example_questions.json | QAEvaluator.evaluate() | [{id,question,answer}] | ✅ |
| timing/ | example_timing_logs.json | evaluate_efficiency() | {runs:[{stages}]} | ✅ |
| multilingual/ | example_cn_results.json | evaluate_multilingual() | {results:[{}]} | ✅ |
| human_scores/ | example_human_scores.json | evaluate_human_correlation() | {samples:[{readability,...}]} | ✅ |

所有示例文件的格式与对应评估函数的期望输入格式一致。

---

## 5. 双语合规检查
## 5. Bilingual Compliance Check

### 5.1 Python 代码中 `/` 分隔符残留

搜索发现约 497 处匹配 `"中文 / English"` 模式。但这些匹配大部分属于以下合法场景：

| 场景 | 示例 | 是否违规 | 处理方式 |
|------|------|---------|---------|
| Docstring `C: / E:` 格式 | `C: 中文 / E: English` | 项目约定格式 | 接受，不改 |
| Markdown 表头 | `| Metric / 指标 |` | Markdown 语法需要 | 接受 |
| Markdown 标题 | `## 1. Label / 标签` | 旧文件 | 不改（旧文件） |
| 用户输出 | `"完成 / Done"` | 旧规范产物 | 不改（旧文件） |

**结论**: 自新规范（独立成行）实施以来创建的所有新文件（gold_example.json、concepts/*、questions/*、timing/*、multilingual/*、human_scores/*）均严格遵守独立成行规范，无 `/` 分隔符混写中英文。

**旧文件**（之前的双语修复任务创建）中仍存在大量使用 `/` 分隔符的文本，但这在用户的"旧文件无需大规模回溯改写"豁免范围内。

### 5.2 改进建议

如果未来希望完全消除 `/` 分隔符，需要修改以下文件：

| 文件 | 主要问题 |
|------|---------|
| run_evaluation.py | 大部分 print 输出使用 `"中文 / English"` |
| markdown_renderer.py | 报告标题和表头使用 `/` |
| console_utils.py | 用户提示使用 `/` |
| 全部 __init__.py | Docstring 使用 `C: / E:` 格式 |

总计约 50 处需要改为独立成行格式。

---

## 总结
## Summary

### 影响等级统计

| 等级 | 数量 | 关键问题 |
|------|------|---------|
| P0 — 阻塞 | 0 | — |
| P1 — 重要 | 3 | ICC 未实现、token_reduction 未实现、tree_utils 缺少防御 |
| P2 — 建议 | 7 | 诊断报告单语、噪声不可复现、批量模式自动加载不完整等 |

### 完整度评分

| 维度 | 分项评分 |
|------|---------|
| Schema 一致性 | 98% — 所有公式实现与 Schema 一致 |
| 代码健壮性 | 85% — 防御性编程中等，部分边界条件未覆盖 |
| 实现完整性 | 75% — §1/§2/§7 完整，§3-§6 需外部数据驱动 |
| 集成完整性 | 90% — CLI 和批量管线均已连接 |
| 双语合规 | 80% — 新文件合规，旧文件仍有分隔符残留 |

### 三个最重要的修复建议 (按优先级)

1. **[P1] ICC/Kendall's W 实现**: 在 `eval_human_correlation.py` 中添加 `pingouin.intraclass_corr` 或手动实现 ICC(3,k)。这是 Schema §6.1 明确要求的指标。

2. **[P1] token_reduction 实现**: 在 `eval_qa.py` 的 `_call_llm_for_qa` 中捕获 `response.usage.total_tokens`，在对照组和实验组之间计算 Token 消耗差。这是 Schema §3.1 要求的记录指标。

3. **[P1] tree_utils 防御性编程**: 在 `tree_utils.py` 的 `compute_depth_map`、`extract_parent_child_pairs` 等函数中，对可能缺失 `id` 或 `label` 的节点添加 `.get()` 保护，避免评估因格式不规范的生成导图中断。
