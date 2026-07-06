# AI MindMap Evaluation System / 思维导图评估系统

## Overview / 概述

This evaluation system provides a comprehensive quality assessment framework for AI-generated mind maps, covering 7 evaluation dimensions (§1-§7). It supports both interactive CLI and batch evaluation modes.

> zh: 本评估系统为 AI 生成的思维导图提供全面的质量评估框架，涵盖 7 个评估维度（§1-§7），支持交互式 CLI 和批量评估两种模式。

## Quick Start / 快速开始

```bash
# Example demo mode — no input files required / 示例演示模式 — 无需输入文件
python evaluation/run_evaluation.py
# Select [1] Example Demo Mode

# Interactive mode — full audio-driven pipeline / 交互模式 — 完整音频驱动管线
python evaluation/run_evaluation.py

# Batch mode — process multiple audio-gold pairs / 批量模式 — 处理多组音频-金标准配对
python evaluation/run_evaluation.py --batch
python evaluation/run_evaluation.py --batch --audio-dir path/to/audio --gold-dir path/to/gold
python evaluation/run_evaluation.py --batch --methods label hierarchy qa
```

## Directory Structure / 目录结构

```
evaluation/
├── run_evaluation.py          # Unified entry point / 统一入口
├── core/                      # Shared infrastructure / 核心基础设施
│   ├── data_loader.py         # Mind map data loading / 导图数据加载
│   ├── aligner.py             # Hungarian aligner / 匈牙利匹配器
│   ├── embedder.py            # Embedding model wrapper / 嵌入模型封装
│   └── thresholds.py          # Metric thresholds & grading / 指标阈值与评级
├── label/                     # §1 Node Label Quality / 节点标签质量
├── hierarchy/                 # §2 Hierarchy Accuracy / 层级结构正确率
├── qa/                        # §3 Downstream QA / 下游 QA 测试
├── efficiency/                # §4 Efficiency & STT / 效率与 STT 保真度
├── multilingual/              # §5 Multilingual & Robustness / 多语言与鲁棒性
├── human_correlation/         # §6 Human Alignment / 人工对齐效度
├── report/                    # Report generation / 报告生成
│   ├── composite.py           # Composite score / 综合评分
│   └── markdown_renderer.py   # Markdown report renderer / Markdown 报告渲染器
├── utils/                     # CLI & I/O utilities / CLI 与 I/O 工具
├── data/                      # Input data files / 输入数据文件
│   ├── audio/                 # Audio files for transcription / 音频文件
│   ├── gold/                  # Gold standard mind maps / 金标准导图
│   ├── concepts/              # Essential concepts sets / 核心概念集合
│   ├── questions/             # QA question sets / 问答问题集
│   ├── timing/                # Timing logs & transcripts / 计时日志与标准文本
│   ├── multilingual/          # Multilingual test results / 多语言测试结果
│   ├── human_scores/          # Human scoring data / 人工评分数据
│   └── sessions/              # Evaluation session outputs / 评估会话输出
└── README.md                  # This file / 本文件
```

## Evaluation Methods / 评估方法

| § | Method / 方法 | Metrics / 指标 | Required Inputs / 必需输入 |
|---|---------------|----------------|---------------------------|
| 0 | Example Demo | All metrics with example data | None / 无 |
| 1 | label | Node-P/R/F1, LabelSim, Entity Recall | audio, gold, concepts |
| 2 | hierarchy | Edge-P/R/F1, UAS, nTED, PC-F1, LAR | audio, gold |
| 3 | qa | QA Retention, BLEU-4, ROUGE-L, BERTScore | audio, questions |
| 4 | efficiency | P50/P95 Latency, WER, KTRR | audio, timing, transcript, key_terms |
| 5 | multilingual | CN/EN/Mixed comparison, Noise robustness | audio, multilingual_results |
| 6 | human_corr | Pearson r, Spearman ρ | audio, human_scores |
| 7 | full | All of the above + Composite Score / 以上全部 + 综合评分 | All required inputs / 全部输入 |

## Usage Modes / 使用方式

### Mode A: Interactive CLI / 交互式 CLI 模式

1. Run `python evaluation/run_evaluation.py`
2. Select evaluation methods from the menu
3. Choose file upload method:
   - **A)** Auto-detect: Place files in `evaluation/data/` subdirectories
   - **B)** Step-by-step: Upload files individually
4. System executes: Audio → Whisper transcription → Map generation → Evaluation
5. View the generated Markdown report

### Mode B: Batch Evaluation / 批量评估模式

1. Prepare audio files in `evaluation/data/audio/` and gold files in `evaluation/data/gold/`
2. Run `python evaluation/run_evaluation.py --batch`
3. System auto-discovers pairs and processes each one
4. Summary report saved to `evaluation/data/sessions/{timestamp}/`

### Mode C: Example Demo / 示例演示模式

- Select `[1] Example Demo Mode` in interactive CLI
- No input files required — uses built-in example data

## Output / 输出产物

- **Markdown evaluation report**: `evaluation/eval_report_{timestamp}.md`
- **Session outputs**: `evaluation/data/sessions/{timestamp}/{pair_name}/` (transcription, generated map, evaluation results)
- **Debug outputs**: `debug_output/{type}_{pair_name}_{timestamp}.json`

## File Conventions / 文件规范

All input JSON files should be placed in their respective `evaluation/data/` subdirectories. The file naming convention uses `{pair_name}` as a shared prefix to enable automatic discovery and pairing:

> zh: 所有输入 JSON 文件应放置在 `evaluation/data/` 下对应的子目录中，`{pair_name}` 作为共享前缀实现自动发现与配对：

| Category / 类别 | Directory / 目录 | File Pattern / 文件名模式 | Example / 示例 |
|-----------------|-----------------|--------------------------|----------------|
| Audio | `data/audio/` | `{pair_name}.mp3` (also .wav/.m4a/.ogg/.flac) | `lecture_01.mp3` |
| Gold map | `data/gold/` | `{pair_name}.json` | `lecture_01.json` |
| Concepts | `data/concepts/` | `{pair_name}_concepts.json` | `lecture_01_concepts.json` |
| Questions | `data/questions/` | `{pair_name}_questions.json` | `lecture_01_questions.json` |
| Timing logs | `data/timing/` | `{pair_name}_timing_logs.json` | `lecture_01_timing_logs.json` |

---

## Pair Name Convention / 配对名规范

### What is pair_name / 什么是配对名

`pair_name` (配对名) is the key identifier that connects an audio file with its corresponding gold standard mind map and all associated input files. The system uses this name to automatically discover file pairs and organize evaluation outputs.

> zh: `pair_name` 是连接音频文件与对应金标准导图及其所有附属输入文件的关键标识符。系统基于配对名自动发现文件配对并组织评估输出。

### How pair_name Is Derived / 配对名如何推导

The system follows these steps to derive `pair_name`:

> zh: 系统按以下步骤推导配对名：

1. **From audio**: Take the audio filename and strip its extension. This becomes the pair_name.
   > zh: **从音频推导**：取音频文件名去掉扩展名，即得到配对名。
2. **Match gold**: Look for a JSON file in `data/gold/` with the exact same name (minus extension).
   > zh: **匹配金标准**：在 `data/gold/` 中查找同名（去掉扩展名）的 JSON 文件。
3. **Associate inputs**: All supplementary input files (concepts, questions, timing logs, etc.) are expected to use the same pair_name as a prefix.
   > zh: **关联输入**：所有补充输入文件（概念集、问题集、计时日志等）均应使用同一配对名作为前缀。

### Complete Example / 完整示例

For a lecture titled "Linear Regression" with audio and gold standard files:

> zh: 以标题为"线性回归"的讲座为例，音频和金标准文件的布局如下：

```
evaluation/data/
├── audio/
│   └── linear_regression.mp3        ← Audio file / 音频文件
├── gold/
│   └── linear_regression.json       ← Gold standard / 金标准 (matched by name)
├── concepts/
│   └── linear_regression_concepts.json  ← Essential concepts / 核心概念
├── questions/
│   └── linear_regression_questions.json ← QA questions / 问答问题集
└── timing/
    ├── linear_regression_timing_logs.json    ← Timing logs / 计时日志
    ├── linear_regression_reference_transcript.txt ← Reference transcript / 参考转写
    └── linear_regression_key_terms.json      ← Key terms / 关键术语
```

In this example, `pair_name = "linear_regression"`. All files share this prefix.

> zh: 此例中 `pair_name = "linear_regression"`，所有文件共享此前缀。

### Naming Constraints / 命名约束

> zh: 命名约束

- **Allowed characters**: Letters (a-z, A-Z), digits (0-9), underscores (_), hyphens (-). (zh: 允许字母、数字、下划线、连字符)
- **Case-sensitive**: `Lecture_01` and `lecture_01` are treated as different pairs. (zh: 大小写敏感)
- **Extension**: Audio files support `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`. (zh: 音频支持扩展名)
- **Uniqueness**: Each pair_name must be unique within a session. (zh: 每个配对名在单个会话中必须唯一)

### How Pairing Works / 配对算法

Behind the scenes, the `discover_pairs()` function in `run_evaluation.py` implements this logic:

> zh: 底层由 `run_evaluation.py` 中的 `discover_pairs()` 函数实现：

```python
def discover_pairs(audio_dir, gold_dir):
    # 1. Scan all audio files / 扫描所有音频文件
    audio_candidates = []
    for ext in ['.wav', '.mp3', '.m4a', '.ogg', '.flac']:
        audio_candidates.extend(glob.glob(f"{audio_dir}/*{ext}"))
    
    # 2. Build gold file index by basename / 按文件名建立金标准索引
    gold_index = {os.path.splitext(os.path.basename(p))[0]: p
                  for p in glob.glob(f"{gold_dir}/*.json")}
    
    # 3. Match: audio basename → gold basename / 匹配：音频名 → 金标准名
    pairs = []
    for apath in audio_candidates:
        base = os.path.splitext(os.path.basename(apath))[0]
        if base in gold_index:
            pairs.append((base, apath, gold_index[base]))
    return pairs
```

Files that cannot be paired will be skipped with a warning.

> zh: 无法配对的音频文件将被跳过并提示警告。

### Output Organization / 输出组织

Pair_name is used throughout the output paths:

> zh: 配对名贯穿整个输出路径：

```
# Session output / 会话输出
evaluation/data/sessions/{timestamp}/
└── {pair_name}/
    ├── transcription.txt           # Whisper transcription / Whisper 转录
    ├── generated_map.json           # Generated mind map / 生成导图
    └── eval_result.json             # Evaluation results / 评估结果

# Debug output / 调试输出
debug_output/
├── generated_map_{pair_name}_{timestamp}.json
├── eval_result_{pair_name}_{timestamp}.json
```

## FAQ / 常见问题

**Q: How does the system match audio files with gold standards? / 系统如何匹配音频文件和金标准？**
A: The system follows a simple basename-matching rule. For each audio file in `data/audio/`, it strips the file extension to derive a `pair_name`, then looks for a JSON file in `data/gold/` with the same basename. All supplementary files (concepts, questions, timing logs) are expected to use the same `pair_name` as a prefix. See the [Pair Name Convention](#pair-name-convention--配对名规范) section above for details and examples.

> zh: **问：系统如何匹配音频文件和金标准？**
> 答：系统遵循简单的文件名匹配规则。对 `data/audio/` 中的每个音频文件，去掉扩展名得到 `pair_name`，然后在 `data/gold/` 中寻找同名的 JSON 文件。所有补充文件（概念集、问题集、计时日志）应使用同一 `pair_name` 作为前缀。详见上方[配对名规范](#pair-name-convention--配对名规范)章节。

**Q: Why is audio required for all evaluation methods?**
A: The evaluation system is audio-driven — it transcribes audio, generates a mind map from the transcript, and then evaluates the map quality. This ensures consistent end-to-end evaluation.

> zh: **问：为什么所有评估方法都需要音频？**
> 答：评估系统是音频驱动的 — 它先转录音频，再从转录文本生成导图，最后评估导图质量。这确保了端到端的一致性评估。

**Q: What if I already have a generated mind map?**
A: Place the generated map JSON in `maps/` directory and the gold standard in `data/gold/`, then run the evaluation. The system will use your map instead of generating one from audio.

> zh: **问：如果我已经有生成好的导图怎么办？**
> 答：将生成导图 JSON 放入 `maps/` 目录，金标准放入 `data/gold/`，然后运行评估。系统将使用您已有的导图。

**Q: Can I run only specific methods?**
A: Yes, in interactive mode, select the methods you want. In batch mode, use `--methods label hierarchy`.

> zh: **问：能否只运行特定的评估方法？**
> 答：可以。在交互模式中选择所需方法即可。在批量模式下使用 `--methods label hierarchy`。

## Reference / 参考

- Evaluation_Schema.md — Full evaluation framework specification / 完整评估框架规范
- `evaluation/data/*/` usage guides — Detailed documentation for each input data type
