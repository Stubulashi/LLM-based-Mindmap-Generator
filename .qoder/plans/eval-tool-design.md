# 命令行交互式评估工具实现方案

## Context / 背景

项目已有完整的评估方案文档（`Evaluation_Schema.md` v1.5）和匈牙利算法标签评测文档（`hungarian_label_evaluation.md`），定义了 7 大评估维度、20+ 个指标及其公式/阈值。但目前缺少一个可运行的评估工具来执行这些指标的计算和报告生成。

当前金标准树集合尚不可用，需要预留接口。评估工具需模块化设计、统一入口、支持交互式选择。

## 目录结构

```
evaluation/
├── __init__.py
├── run_evaluation.py              # 统一入口（交互式 CLI）
├── core/
│   ├── __init__.py
│   ├── data_loader.py             # 数据加载器
│   ├── aligner.py                 # 匈牙利匹配共享基类
│   ├── embedder.py                # Embedding 模型封装
│   └── thresholds.py              # 阈值定义
├── metrics/
│   ├── __init__.py
│   ├── eval_label.py              # §1 节点标签质量（4个指标）
│   ├── eval_hierarchy.py          # §2 层级结构正确率（5个指标）
│   ├── eval_qa.py                 # §3 下游 QA 测试（接口预留）
│   ├── eval_efficiency.py         # §4 效率与 STT 保真度（接口预留）
│   ├── eval_multilingual.py       # §5 多语言与鲁棒性（接口预留）
│   └── eval_human_correlation.py  # §6 人工评估相关性（接口预留）
├── report/
│   ├── __init__.py
│   ├── markdown_renderer.py       # Markdown 报告渲染器
│   └── composite.py               # §7.2 综合评分公式
└── utils/
    ├── __init__.py
    ├── tree_utils.py              # 树结构工具
    ├── io_utils.py                # JSON 读写
    └── console_utils.py           # 交互式 CLI 辅助
```

## 实现步骤

### Task 1: 核心基础设施（core/）

**修改文件**：全部新建

- `core/embedder.py`：封装 `SentenceTransformer`，支持懒加载、模型缓存（进程内类级缓存）、批量编码
- `core/thresholds.py`：定义 `ThresholdBand` 数据类，包含所有 12 个指标的优秀/良好/需改进阈值及其 `grade()` 方法
- `core/data_loader.py`：`MindMapData` 数据类 + `DataLoader` 类
  - `from_map_file()`：从 `maps/*.json` 格式加载
  - `from_flat_dict()`：从 `{nodes, links}` dict 加载
  - `extract_labels()`、`extract_edges()`、`compute_depth()` 等工具方法
  - `auto_detect_inputs()`：自动扫描 data/gold/、debug_output/、maps/ 目录
- `core/aligner.py`：`HungarianAligner` 共享基类
  - 接受 `gold_nodes` 和 `gen_nodes`（list[dict]）
  - 执行：标签提取 → embedding → 余弦相似度矩阵 → `scipy.optimize.linear_sum_assignment` → 阈值过滤
  - 返回 `AlignmentResult`（含 `raw_matches`、`filtered_matches`、`similarity_matrix` 等）
  - 所有节点级和边级指标共享同一个 `AlignmentResult`

### Task 2: 标签质量评估（metrics/eval_label.py）

- `evaluate_label_quality(gold_map, gen_map, aligner, essential_concepts)` → `LabelMetrics`
- 内部计算 1.1~1.4 全部指标
- 1.2 Node-P/R/F1：基于混淆矩阵（TP/FP/FN）
- 1.3 LabelSim：已匹配节点余弦均值
- 1.4 Entity Recall：核心概念 embedding 匹配

### Task 3: 层级结构评估（metrics/eval_hierarchy.py）

- `evaluate_hierarchy_quality(gold_map, gen_map, alignment)` → `HierarchyMetrics`
- 2.1 Edge-P/R/F1：基于节点映射 `mu`
- 2.2 UAS：基于 `mu` 检查父节点一致性
- 2.3 nTED：使用 `zss` 库计算树编辑距离
- 2.4 PC-F1：基于标签语义（不依赖对齐）
- 2.5 LAR：已匹配节点的深度一致性
- 边界情况处理：空边集、单节点树、全匹配/零匹配

### Task 4: 其他评估模块（接口预留）

- `metrics/eval_qa.py`：`QAEvaluator` 类定义接口 `evaluate(gold_map, gen_map, questions)`，复用 `Config.LLM_*`
- `metrics/eval_efficiency.py`：延迟分析、WER/KTRR 接口
- `metrics/eval_multilingual.py`：多语言差异分析接口
- `metrics/eval_human_correlation.py`：Pearson/Spearman 相关性分析接口
- 以上模块定义完整参数签名和返回值类型，计算逻辑标注 `# TODO: implement when data available`

### Task 5: 工具函数（utils/）

- `utils/tree_utils.py`：深度计算、父子关系提取、边集转换、嵌套树/扁平树互转
- `utils/io_utils.py`：JSON 读写、结果持久化
- `utils/console_utils.py`：交互式多选（`interactive_multiselect`）、文件路径提示（`prompt_file`）、进度追踪（`ProgressTracker`）、结果表格打印

### Task 6: 报告生成（report/）

- `report/markdown_renderer.py`：`MarkdownReportRenderer` 类
  - `_render_header()`：讲座信息、管线配置、Embedding 模型、τ 值
  - `_render_summary()`：各维度核心指标摘要表
  - `_render_label_section()`：§1 详细表格 + 匈牙利匹配详情
  - `_render_hierarchy_section()`：§2 详细表格
  - `_render_diagnostics()`：诊断建议（基于指标值自动生成）
- `report/composite.py`：`compute_composite_score()` 实现 §7.2 公式

### Task 7: 统一入口（run_evaluation.py）

- 4 步交互流程：
  1. **选择评估方法**：多选（1~7），支持 "全量报告" 一键勾选
  2. **输入文件**：自动检测 → 显示候选 → 用户确认/手动指定
  3. **执行评估**：创建共享 `HungarianAligner`（只加载一次 embedding 模型），按序执行选中模块，带进度条
  4. **输出报告**：保存 `eval_report_<timestamp>.md`，可选终端显示摘要
- 处理金标准文件缺失的情况：用户选择 `label`/`hierarchy` 时金标准为必须，否则跳过
- 异常处理：各模块独立 try-catch，失败模块不影响其他模块

## 关键设计决策

1. **共享基础设施**：所有节点级/边级指标共用同一个 `AlignmentResult`，避免多次 embedding + 匈牙利匹配导致的结果不一致
2. **统一函数签名**：`evaluate_xxx(gold_map, gen_map, aligner, **kwargs) → dict`，便于 run_evaluation.py 统一调度
3. **P0 优先实现**：core/ + eval_label + eval_hierarchy + report + run_evaluation（形成完整闭环）
4. **QA 评估复用 Config**：直接 import `config.Config` 复用 LLM 配置，参考 `mcp_server.py._judge_by_main_model` 的调用模式
5. **诊断建议规则化**：基于 `(指标值, 阈值, 上下文)` 三元组自动生成可读的诊断文本

## 验证方式

1. **核心流程验证**：
   ```bash
   cd /home/akku/ai-mindmap-agent
   python evaluation/run_evaluation.py
   ```
   验证：交互式 CLI 正常显示各步骤，报告文件正确生成

2. **模块单元验证**：
   ```bash
   python -c "
   from evaluation.metrics.eval_label import evaluate_label_quality
   from evaluation.metrics.eval_hierarchy import evaluate_hierarchy_quality
   # 使用示例数据验证核心指标计算
   "
   ```

3. **匈牙利匹配验证**：使用文档中的示例数据（Vehicle→Transport, Car→Automobile, Bus→Coach, Train→Railway）验证匹配结果一致

4. **报告验证**：检查生成的 `.md` 报告是否包含指标值、阈值、评级、状态、诊断建议
