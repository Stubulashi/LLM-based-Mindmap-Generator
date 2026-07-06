# Efficiency Evaluation Guide — Auto-Instrumented Pipeline Timing

> zh: 效率评估指南 — 自动仪表化的管线计时

## Overview / 概述

Unlike other evaluation methods that require a gold standard, the **efficiency** evaluation is audio-only. Simply upload an audio file, and the system will:

> zh: 与其他需要金标准的评估方法不同，**效率**评估仅需音频文件。系统将：

1. Transcribe the audio via Whisper (STT) / 通过 Whisper 转录音频
2. Generate a mind map from the transcription / 从转录文本生成导图
3. **Automatically capture timing data at every pipeline stage** / **自动采集各管线阶段的计时数据**
4. Compare measured latency against built-in performance standards / 将实测延迟与内置性能标准对比
5. Report WER (Word Error Rate) and KTRR (Key Term Retention Rate) / 报告 WER 和 KTRR

> zh: **无需金标准**。效率评估完全由音频驱动，系统在运行管线时自动采集计时数据。

---

## Purpose / 目的

> zh: 目的

- Measure end-to-end latency of the mind map generation pipeline. (zh: 测量导图生成管线的端到端延迟)
- Identify performance bottlenecks at each stage. (zh: 识别各阶段的性能瓶颈)
- Evaluate STT transcription accuracy via WER. (zh: 通过 WER 评估 STT 转录准确率)
- Evaluate key term preservation via KTRR. (zh: 通过 KTRR 评估关键术语保留率)
- Compare against configurable performance standards. (zh: 与可配置的性能标准对比)

---

## Principle / 原理

> zh: 原理

### Automatic Timing Instrumentation / 自动计时仪表化

The system uses `time.perf_counter()` to timestamp each pipeline stage automatically:

> zh: 系统使用 time.perf_counter() 自动标记各管线阶段的时间戳：

```python
# E: STT stage / C: STT 阶段
t0 = time.perf_counter()
stt_result = await transcribe_audio(...)
t1 = time.perf_counter()  # stt duration = t1 - t0

# E: Map generation stage / C: 导图生成阶段
t2 = time.perf_counter()
map_result = await modify_mind_map_v2(...)
t3 = time.perf_counter()  # map_gen duration = t3 - t2
                         # total duration = t3 - t0
```

### Computed Metrics / 计算指标

| Metric / 指标 | Description / 说明 |
|---------------|-------------------|
| **P50 / P95** | Median and 95th percentile latency per stage (zh: 各阶段延迟的中位数和第95百分位数) |
| **STT Ratio** | STT time / total time (zh: STT 时间占总时间比例) |
| **WER** | Word Error Rate via jiwer library (zh: 词错率，通过 jiwer 库计算) |
| **KTRR** | Key Term Retention Rate via fuzzy matching (zh: 关键术语保留率，通过模糊匹配) |

### Standards Comparison / 标准对比

Measured P50/P95 values are compared against built-in performance targets. Each stage gets a **PASS/FAIL** status in the report.

> zh: 实测 P50/P95 值与内置性能目标对比，每个阶段在报告中获得 PASS/FAIL 状态。

---

## Performance Standards / 性能标准

### Built-in Defaults / 内置默认值

| Stage / 阶段 | P50 Target | P95 Target |
|-------------|-----------|-----------|
| stt | ≤ 30s | ≤ 60s |
| concept | ≤ 5s | ≤ 10s |
| hierarchy | ≤ 5s | ≤ 10s |
| delta | ≤ 5s | ≤ 10s |
| polish | ≤ 3s | ≤ 5s |
| map_gen | ≤ 18s | ≤ 35s |
| **total** | **≤ 48s** | **≤ 95s** |

### Custom Standards / 自定义标准

You can provide your own standards by creating a JSON file at `evaluation/data/standards/custom_standards.json`. See the [custom_standards_schema.md](../standards/custom_standards_schema.md) for the format.

> zh: 您可以通过在 `evaluation/data/standards/custom_standards.json` 创建 JSON 文件来提供自定义标准。格式请参考 custom_standards_schema.md。

---

## How to Use / 使用方法

> zh: 使用方法

### Interactive Mode / 交互模式

1. Run `python evaluation/run_evaluation.py`
2. Select `efficiency` (or `full` to include all methods)
3. Upload an audio file (or let the system auto-detect it)
4. The system will automatically transcribe, generate, time, and evaluate
5. View the report with per-stage timing and standards comparison

### Batch Mode / 批量模式

```bash
python evaluation/run_evaluation.py --batch --methods efficiency
```

---

## Limitations / 局限性

> zh: 局限性

- **Timing precision:** Accuracy depends on hardware and system load; results may vary across environments. (zh: 计时精度依赖硬件和系统负载，不同环境结果可能有差异)
- **Coarse stage granularity:** Current instrumentation measures STT and total map generation as two blocks. Finer granularity (concept/hierarchy/delta/polish) requires MCP server instrumentation. (zh: 当前仪表化将 STT 和导图生成作为两个块测量。更细粒度需要 MCP 服务端仪表化)
- **WER availability:** Requires `jiwer` library; falls back gracefully if unavailable. (zh: WER 需要 jiwer 库；不可用时自动降级)
- **KTRR:** Requires a key terms list; if not provided, KTRR is reported as unavailable. (zh: KTRR 需要关键术语列表；未提供时报告为不可用)
- **Single run:** Currently captures one pipeline run; repeated runs for P50/P95 accuracy require manual configuration. (zh: 当前捕获单次管线运行；多次运行以获得准确的 P50/P95 需要手动配置)

---

*Document Version: v2.0 | Created: 2026-07-02*
