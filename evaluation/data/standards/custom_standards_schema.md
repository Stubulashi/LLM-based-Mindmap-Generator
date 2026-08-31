# Custom Efficiency Standards Schema / 自定义效率标准格式说明

> zh: 您可以通过上传自定义 JSON 标准文件来覆盖效率评估的默认性能基准。

## File Format / 文件格式

```json
{
  "standards": [
    {"stage": "stt",       "p50_target": 30.0, "p95_target": 60.0},
    {"stage": "concept",   "p50_target": 5.0,  "p95_target": 10.0},
    {"stage": "hierarchy", "p50_target": 5.0,  "p95_target": 10.0},
    {"stage": "delta",     "p50_target": 5.0,  "p95_target": 10.0},
    {"stage": "polish",    "p50_target": 3.0,  "p95_target": 5.0},
    {"stage": "map_gen",   "p50_target": 18.0, "p95_target": 35.0},
    {"stage": "total",     "p50_target": 48.0, "p95_target": 95.0}
  ]
}
```

## How to Use / 使用方法

1. Create a JSON file following the format above with your custom targets.
   > zh: 按照上述格式创建自定义标准的 JSON 文件。

2. Place it in `evaluation/data/standards/custom_standards.json` or specify its path when selecting the `efficiency` method.
   > zh: 将其放入 `evaluation/data/standards/custom_standards.json`，或在选择 efficiency 方法时指定路径。

3. The system will automatically compare measured P50/P95 values against these targets in the report.
   > zh: 系统将自动在报告中比较实测 P50/P95 值与目标值。

## Field Definitions / 字段定义

| Field / 字段 | Type / 类型 | Description / 说明 |
|-------------|-------------|-------------------|
| stage | string | Pipeline stage name / 管线阶段名 (stt, concept, hierarchy, delta, polish, map_gen, total) |
| p50_target | float | Target P50 latency in seconds / P50 延迟目标值（秒） |
| p95_target | float | Target P95 latency in seconds / P95 延迟目标值（秒） |

## Default Values / 默认值

| Stage / 阶段 | P50 Target | P95 Target | Description / 说明 |
|-------------|-----------|-----------|-------------------|
| stt | 30s | 60s | STT speech-to-text / 语音转文字 |
| concept | 5s | 10s | Concept extraction / 概念提取 |
| hierarchy | 5s | 10s | Hierarchy planning / 层级规划 |
| delta | 5s | 10s | Delta generation / Delta 生成 |
| polish | 3s | 5s | Post-processing polish / 后处理润色 |
| map_gen | 18s | 35s | Total map generation (concept+...+polish) / 导图生成总时间 |
| total | 48s | 95s | End-to-end pipeline (STT + map_gen) / 端到端管线总时间 |
