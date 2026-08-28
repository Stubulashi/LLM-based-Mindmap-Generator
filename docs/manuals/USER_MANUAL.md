# AI MindMap Agent — Full User Manual / 全功能使用手册

> AI MindMap Agent: FastAPI orchestration layer + MCP client/server + three-stage agent pipeline + Vue3 frontend + evaluation framework.
> 系统构成：FastAPI 编排层 + MCP 客户端/服务端 + 三阶段 Agent 管线 + Vue3 前端 + 评估框架。

## Table of Contents / 目录

### Part I — English (英文全文)

- [1. 30-Second Quick Overview](#en-1-30-second-quick-overview)
- [2. Main Features](#en-2-main-features)
  - [2.1 Install Dependencies](#en-21-install-dependencies)
  - [2.2 Configure and Start the Backend](#en-22-configure-and-start-the-backend)
  - [2.3 Use the Frontend (index.html)](#en-23-use-the-frontend-indexhtml)
  - [2.4 Three-Stage Pipeline](#en-24-three-stage-pipeline)
  - [2.5 MCP Server Tools (8)](#en-25-mcp-server-tools-8)
  - [2.6 CLI Pipeline (cli_pipeline.py)](#en-26-cli-pipeline-cli_pipelinepy)
- [3. Evaluation Framework](#en-3-evaluation-framework)
  - [3.1 Unified Entry: evaluation/run_evaluation.py](#en-31-unified-entry-evaluationrun_evaluationpy)
  - [3.2 Seven Evaluation Dimensions](#en-32-seven-evaluation-dimensions)
  - [3.3 Report Output and Reading Guide](#en-33-report-output-and-reading-guide)
- [4. API and Environment Configuration](#en-4-api-and-environment-configuration)
  - [4.1 .env and api.env](#en-41-env-and-apienv)
  - [4.2 config.py Reference](#en-42-configpy-reference)
  - [4.3 .gitignore Conventions](#en-43-gitignore-conventions)
- [5. Testing and Maintenance](#en-5-testing-and-maintenance)
  - [5.1 Run All Tests](#en-51-run-all-tests)
  - [5.2 scripts/ Utilities](#en-52-scripts-utilities)

### Part II — 中文全文 (Chinese)

- [1. 三十秒速览](#zh-1-三十秒速览)
- [2. 主功能使用](#zh-2-主功能使用)
  - [2.1 安装依赖](#zh-21-安装依赖)
  - [2.2 配置并启动后端](#zh-22-配置并启动后端)
  - [2.3 前端界面使用](#zh-23-前端界面使用)
  - [2.4 三阶段管线](#zh-24-三阶段管线)
  - [2.5 MCP 服务器 8 个工具](#zh-25-mcp-服务器-8-个工具)
  - [2.6 CLI 管线（cli_pipeline.py）](#zh-26-cli-管线-cli_pipelinepy)
- [3. 评估框架使用](#zh-3-评估框架使用)
  - [3.1 统一入口 evaluation/run_evaluation.py](#zh-31-统一入口-evaluationrun_evaluationpy)
  - [3.2 七个评估维度](#zh-32-七个评估维度)
  - [3.3 报告输出与阅读](#zh-33-报告输出与阅读)
- [4. API 与环境配置](#zh-4-api-与环境配置)
  - [4.1 .env 与 api.env](#zh-41-env-与-apienv)
  - [4.2 config.py 配置项参考](#zh-42-configpy-配置项参考)
  - [4.3 .gitignore 约定](#zh-43-gitignore-约定)
- [5. 测试与维护](#zh-5-测试与维护)
  - [5.1 运行全部测试](#zh-51-运行全部测试)
  - [5.2 scripts/ 工具脚本](#zh-52-scripts-工具脚本)

---

# Part I — English

## <a id="en-1-30-second-quick-overview"></a>1. 30-Second Quick Overview

### Module responsibilities (one line each)

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI orchestration layer. Pure orchestrator — no LLM calls or business logic; validates every MCP tool result, retries and degrades on failure. |
| `mcp_client.py` | Spawns `mcp_server.py` as a subprocess and talks to it over stdio (MCP protocol). |
| `mcp_server.py` | Exposes 8 MCP tools (chat, transcription, polish, map modify, annotation, definition). |
| `mindmap_agent.py` | Three-stage pipeline (concept extraction → hierarchy planning → delta generation) plus the single-model fallback agent. |
| `cli_pipeline.py` | Web-free CLI pipeline: audio/text → mind map JSON, saved to `maps/`. |
| `evaluation/run_evaluation.py` | Unified evaluation entry: interactive CLI, batch mode, offline re-computation. |
| `index.html` | Vue3 + G6 v5 frontend: chat, transcription, canvas, link editor, bilingual UI, export/import, map CRUD. |
| `config.py` | All environment-driven configuration with defaults. |

### Data flow of one request

```
Browser → POST /chat → main.py orchestrates →
  MCP chat_generate (chat reply) →
  MCP modify_mind_map_v2 (three-stage pipeline, incremental delta) →
  {answer, map} → frontend renders with G6
```

### Minimal runnable example

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
# Edit api.env: fill DEEPSEEK_API_KEY / LLM_API_KEY
./venv/bin/python main.py
# Open http://localhost:8000 in a browser
```

## <a id="en-2-main-features"></a>2. Main Features

## <a id="en-21-install-dependencies"></a>2.1 Install Dependencies

Create a virtual environment and install from `requirements.txt`:

```bash
cd /home/akku/ai-mindmap-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Notes:

- Always run through the project venv (`./venv/bin/python ...`), not the system Python.
- Core deps: `fastapi`, `uvicorn`, `openai`, `mcp>=1.0.0`, `python-dotenv`, `wikipedia-api`, `openai-whisper`, `sentence-transformers`.
- Evaluation metrics add `nltk`, `rouge-score`, `bert-score`, `jiwer`, `jieba`, `zss`, `scipy` (all declared in `requirements.txt`).
- Optional `pypinyin` enables offline pinyin generation; when absent the system falls back to the LLM automatically.
- `openai-whisper` and `sentence-transformers` download models on first use (Whisper `small`, embedding `paraphrase-multilingual-MiniLM-L12-v2`); the embedding model is cached under `.hf_cache/`.

## <a name="en-22-configure-and-start-the-backend"></a>2.2 Configure and Start the Backend

Start the backend:

```bash
./venv/bin/python main.py
```

- Serves on `0.0.0.0:8000`; the frontend is served same-origin at `http://localhost:8000` (GET `/` returns `index.html`).
- On startup the FastAPI lifespan spawns the MCP server subprocess (`mcp_server.py`) via `mcp_client.py`; if the client fails to start, the service refuses to start.
- CORS allows only `http://localhost:8000` and `http://127.0.0.1:8000` — the project is an internal tool with no auth design.
- Configure API keys in `.env` (loaded by `config.py`) before starting; see Section 4.

## <a name="en-23-use-the-frontend-indexhtml"></a>2.3 Use the Frontend (index.html)

The single-page frontend (Vue3 + Tailwind + G6 v5 canvas) is served by the backend. Main features:

**Chat**

- Type a message and press Enter / click send → `POST /chat` with `{message, current_map:{nodes,links}}`; the response contains `answer` (chat text) and `map` (updated `{tree, nodes, links}`), then the canvas re-renders.
- Language auto-detection: on the first user message, the UI language follows the input language (CJK → Chinese) unless a language was chosen manually before.
- Transcript as context: toggle "include transcript as context" to attach the transcript list to the chat request (`transcript_context` field).
- Subtree conversation: start a sub-topic from a node — new nodes are attached under that node; the conversation has independent memory and only sees the subtree plus ancestors.

**Audio transcription**

- Upload an audio file → `POST /upload_audio` → Whisper transcription + LLM polishing; result appears in the transcript panel with speaker/time.
- Each transcript entry can be edited, deleted, or re-downloaded; the transcript list is used for map drawing and as chat context.

**Canvas (G6 v5)**

- Drag nodes, zoom, collapse/expand branches, select a node to inspect its `details`, delete it, or open a subtree conversation on it.
- Link editor: click a link to change its type (7 types, see 2.5) or label, or delete the link.
- Clicking an underlined (annotated) term opens a definition popup.

**Language switching**

- Settings panel offers UI language selection (English / 中文); all UI text switches instantly, and the G6 canvas re-renders (link-type labels follow the language).
- Preferences persist in `localStorage` (key `mindmap-settings`); a manual language choice overrides auto-detection.

**Export / Import**

- Export PNG: canvas snapshot downloaded via `graph.toDataURL` (2x pixel ratio).
- Export JSON: current `{nodes, links}` downloaded as `mindmap_YYYY-MM-DD.json`.
- Import JSON: load a `{nodes, links}` file to replace the canvas content.

**Map CRUD (persistence in `maps/*.json`)**

- Save `POST /save_map` `{map_data, name}` → returns `map_id` (8-char UUID).
- Load `GET /load_map?map_id=...`; List `GET /list_maps` (sorted by update time); Rename `POST /rename_map`; Delete `DELETE /delete_map?map_id=...`.

**Term annotation and definition**

- `POST /annotate` analyzes the map and marks key terms with underlines (`density_mode`: low/medium/high; `detail_level`: brief/medium/detailed; `language`: zh/en).
- `POST /define` fetches a term definition — Wikipedia first, LLM fallback, plus IPA and literal meaning (`lookup_dictionary`).

## <a name="en-24-three-stage-pipeline"></a>2.4 Three-Stage Pipeline

`modify_mind_map_v2` internally runs a three-stage multi-model pipeline (orchestrated by `MindMapPipelineOrchestrator` in `mindmap_agent.py`):

1. **Stage 1 — Concept extraction** (`ConceptExtractionAgent`): extracts atomic concepts (label, color, details) from the conversation / transcript.
2. **Stage 2 — Hierarchy planning** (`HierarchyPlanningAgent`): groups concepts into parent-child relationships (with recursive sub-groups).
3. **Stage 3 — Delta generation** (`DeltaGenerationAgent`): outputs CRUD instructions (`add_nodes` / `update_nodes` / `append_details` / `add_links`), which `state_merge` applies to the current map. Returns `{tree, nodes, links}`.

Degradation chain (each stage failure falls back gracefully):

- Stage 1 fails → skip stages 1+2, run the legacy single-model agent directly.
- Stage 2 fails → skip stage 2; stage 3 receives only concept hints.
- Stage 3 fails → return the original map unchanged.

Model configuration (all optional; unset values fall back to `LLM_MODEL`, behaving exactly like the single-model `modify_mind_map`):

- `CONCEPT_MODEL` / `CONCEPT_BASE_URL` / `CONCEPT_API_KEY` — stage 1.
- `HIERARCHY_MODEL` / `HIERARCHY_BASE_URL` / `HIERARCHY_API_KEY` — stage 2. Set `HIERARCHY_MODEL=""` or `HIERARCHY_SKIP=true` for a two-stage mode.
- `DELTA_MODEL` / `DELTA_BASE_URL` / `DELTA_API_KEY` — stage 3 (defaults to the main model).

Related switches: `DETAILS_ENRICHMENT_ENABLED` (append AI-reply explanations into node `details`), `DEPTH_FIRST_ENABLED` / `MIN_TREE_DEPTH` / `MAX_SIBLINGS_PER_NODE` (depth-first generation strategy), `TREE_POSTPROCESS_ENABLED` (deterministic structure repair before persisting: cycle cutting, orphan re-parenting, shallow-tree deepening).

The pipeline is invoked through the MCP tool `modify_mind_map_v2`; `main.py` (the orchestrator) is the only caller in the web path, while `cli_pipeline.py` and the evaluation framework call it as well.

## <a name="en-25-mcp-server-tools-8"></a>2.5 MCP Server Tools (8)

`mcp_server.py` runs as a subprocess and exposes 8 tools via the MCP stdio protocol; `mcp_client.py` dispatches calls with validation and retry (1 retry, then degrade).

| # | Tool | Arguments | Returns |
|---|---|---|---|
| 1 | `chat_generate` | `messages` (OpenAI-format list) | `{reply_text}` |
| 2 | `transcribe_audio` | `file_path` | `{raw_text, detected_language}` |
| 3 | `polish_text` | `raw_text`, `detected_language`, `session_ts?` | `{polished_text}` |
| 4 | `modify_mind_map` | `chat_history`, `current_map` | `{tree, nodes, links}` |
| 5 | `modify_mind_map_v2` | `chat_history`, `current_map`, `session_ts?` | `{tree, nodes, links}` |
| 6 | `annotate_terms` | `current_map`, `density_mode`, `detail_level`, `user_language`, `session_ts?` | `{status, annotations, detail_level}` |
| 7 | `get_definition` | `term`, `detail_level`, `language`, `session_ts?` | `{definition, wikipedia_definition, wikipedia_url, llm_definition, ipa, literal_meaning, source}` |
| 8 | `lookup_dictionary` | `term`, `session_ts?` | IPA + literal meaning dict |

Notes:

- `tree` is the G6 nested-tree format (consumed by the frontend directly); `nodes`/`links` are flat formats for incremental round-trip.
- `modify_mind_map_v2` = three-stage pipeline; `modify_mind_map` = single-model ReAct (identical behavior when no stage-specific models are configured).
- Link types (single source of truth: `schema.py` `LINK_TYPE_SCHEMA`, 7 types): `solid` parent-child, `dashed` indirect, `containment` containment, `dotted` weak, `reference` reference, `contrast` contrast, `causal` causal. Invalid types fall back to `solid`.
- `get_definition` chain: Wikipedia → LLM → IPA + literal meaning (`source` field tells which one won).

## <a name="en-26-cli-pipeline-cli_pipelinepy"></a>2.6 CLI Pipeline (cli_pipeline.py)

Web-free pipeline (Whisper transcription + LLM map generation), automatically loads `api.env` (override). Results are saved to `maps/{map_id}.json`; logs go to stderr, results to stdout.

```bash
# Text mode: text → map
./venv/bin/python cli_pipeline.py "机器学习的分支包括监督学习和无监督学习"

# Audio mode: audio → Whisper → polish → map
./venv/bin/python cli_pipeline.py lecture.mp3 --audio --name "课堂笔记"

# Audio mode, skip LLM polishing (keep raw transcript)
./venv/bin/python cli_pipeline.py lecture.mp3 --audio --skip-polish

# Interactive mode: incremental rounds, map grows round by round (type /exit or Ctrl+C to quit)
./venv/bin/python cli_pipeline.py -i

# Dependency check only (no model loading)
./venv/bin/python cli_pipeline.py --check-deps
```

First run loads Whisper `small` (~10–30 s). The pipeline prefers the three-stage pipeline and degrades to the single-model agent on failure.

## <a id="en-3-evaluation-framework"></a>3. Evaluation Framework

## <a id="en-31-unified-entry-evaluationrun_evaluationpy"></a>3.1 Unified Entry: evaluation/run_evaluation.py

Run via the project venv; `api.env` is loaded at the CLI entry (real keys) and `.env` at import time (HF endpoints etc.).

**Interactive mode (default)** — guided menu: select methods → provide files → per-audio transcription/map generation/evaluation → Markdown reports:

```bash
./venv/bin/python evaluation/run_evaluation.py
```

**Batch mode** — evaluate all audio files in a directory against gold standards:

```bash
./venv/bin/python evaluation/run_evaluation.py --batch \
  --audio-dir evaluation/data/audio \
  --gold-dir evaluation/data/gold \
  --methods label hierarchy efficiency
```

**Offline re-computation (session reuse)** — recompute metrics from a saved session, skipping transcription and LLM generation (zero-cost regression after evaluation-side fixes):

```bash
./venv/bin/python evaluation/run_evaluation.py \
  --reuse-sessions 20260804_092828 \
  --methods label hierarchy \
  --prefer-gold GTC
```

**Common parameters**

| Parameter | Meaning | Default |
|---|---|---|
| `--batch` | Batch mode | off |
| `--audio-dir` / `--gold-dir` | Input directories for batch mode | `evaluation/data/audio` / `evaluation/data/gold` |
| `--methods` | Space-separated method list, e.g. `label hierarchy qa` | `label hierarchy efficiency` (batch) / `label hierarchy` (reuse) |
| `--repeat N` | Independent runs per pair; metrics averaged | 1 |
| `--reuse-sessions <ts>` | Offline re-evaluation of a saved session dir | none |
| `--model-name` | Embedding model for semantic alignment | `paraphrase-multilingual-MiniLM-L12-v2` |
| `--threshold` | Semantic similarity threshold τ | 0.70 |
| `--prefer-gold` | Preferred gold baseline subdir (GTC / YQL) | none (auto: root → GTC → YQL) |
| `--postprocess` | Apply tree postprocessing to stored maps during reuse | off |
| `--triple-report` | Generate the Chinese-named triple comparison report (STT / agent tree / human tree) | off |
| `--auto-install` | pip-install missing dependencies | off |
| `--ignore-missing-deps` | Continue despite missing packages | off |
| `--gold-example-transcript/json` | Gold example pair for the example demo mode | none |

Notes:

- Offline runs of the embedding model need the HF cache; when offline use `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python ...`.
- Input data lives under `evaluation/data/`: `audio/`, `gold/` (with optional `GTC/`, `YQL/` baselines), `concepts/`, `questions/`, `timing/`, `multilingual/`, `human_scores/`, `sessions/`, `standards/`.

## <a name="en-32-seven-evaluation-dimensions"></a>3.2 Seven Evaluation Dimensions

| Method | Required inputs | Key metrics | How triggered |
|---|---|---|---|
| `label` — Node label | gold, audio, concepts | Node-F1, LabelSim, Entity-Recall | selected in menu / `--methods` |
| `hierarchy` — Hierarchy | gold, audio | Edge-F1/P/R, UAS, PC-F1, LAR, nTED | selected in menu / `--methods` |
| `qa` — Downstream QA | audio | QA score (20 auto-generated questions, 1–5 each) | selected in menu / `--methods` |
| `efficiency` — Efficiency & STT | audio, timing, transcript, key_terms | WER, token reduction, etc. | selected in menu / `--methods` |
| `multilingual` — Multilingual | audio, multilingual_results | Max Δ Recall across cn/en/mixed + noise tests | selected in menu / `--methods` |
| `human_corr` — Human alignment | audio | interactive 0–10 scoring; ICC(3,k), Kendall's W, overall_normalized | selected in menu |
| `full` — Full report | all of the above | all methods + composite score | selected in menu (`full` expands to all) |

- Semantic alignment uses Hungarian matching on multilingual embeddings; τ=0.7 by default.
- Human scoring (0–10 per audio, two scores: system map / human-labeled map) acts as a compensation mechanism for hierarchy false negatives and enters the composite score.
- Composite score components (from `evaluation/report/composite.py`): node_f1 0.20, label_sim 0.10, entity_recall 0.10, edge_f1 0.15, uas 0.10, nted_inv 0.15, pc_f1 0.10, plus qa/human when available; missing dimensions are excluded and remaining weights renormalized. Interpretation: ≥ 0.85 excellent, ≥ 0.70 good, < 0.70 needs improvement.

## <a name="en-33-report-output-and-reading-guide"></a>3.3 Report Output and Reading Guide

Every pair generates a Markdown report saved in two places (dual save):

1. `evaluation/data/sessions/{timestamp}/{pair_name}/eval_report.md` (also holds all intermediate JSONs of the session)
2. `evaluation/eval_report_{pair_name}_{timestamp}.md` (project root under `evaluation/`)

Reading the report (see any `evaluation/eval_report_*.md` example):

- **Summary table**: one row per dimension — key metric value, grade, PASS/FAIL status; the composite score row sits on top.
- **Dimension sections** (1 Node Label, 2 Hierarchy, 3 QA, 4 Efficiency, 5 Multilingual, 6 Human, 7 Composite): metric tables with per-metric thresholds and grades; hierarchy metrics graded against e.g. Edge-F1 ≥ 0.80, UAS ≥ 0.85, PC-F1 ≥ 0.75, LAR ≥ 0.70, nTED ≤ 0.25; label metrics against Node-F1 ≥ 0.85, LabelSim ≥ 0.85, Entity-Recall ≥ 0.90.
- **Details blocks**: Hungarian match details (gold vs generated labels + similarity), entity recall misses, edge TP/FP/FN breakdown.
- **Composite section**: per-component value / weight / weighted score, with a note when weight was renormalized due to missing dimensions.
- **Diagnostics section**: auto-generated suggestions per under-performing metric.

## <a id="en-4-api-and-environment-configuration"></a>4. API and Environment Configuration

## <a id="en-41-env-and-apienv"></a>4.1 .env and api.env

Two env files coexist (both are git-ignored; never commit real keys):

- **`.env`** — loaded by `config.py` at import time (main.py, mcp_server.py, cli_pipeline.py, tests). Recommended place for `LLM_*` variables and tuning switches. Example:
  ```bash
  # Generic OpenAI-compatible provider (recommended)
  LLM_API_KEY=sk-xxxx
  LLM_BASE_URL=https://api.deepseek.com
  LLM_MODEL=deepseek-chat
  # Optional: stage-specific models for the 3-stage pipeline
  # CONCEPT_MODEL=deepseek-lite
  # HIERARCHY_MODEL=deepseek-lite
  # DELTA_MODEL=deepseek-chat
  ```
- **`api.env`** — real keys; loaded with `override=True` by `cli_pipeline.py` and by `evaluation/run_evaluation.py` in `main()` only (not at import time, to avoid polluting host processes). Example:
  ```bash
  DEEPSEEK_API_KEY=sk-xxxx
  DEEPSEEK_BASE_URL=https://api.deepseek.com
  DEEPSEEK_MODEL=deepseek-chat
  OPENAI_API_KEY=sk-your-openai-key-here
  ```
- Fallback priority in `config.py`: `LLM_*` env vars → `DEEPSEEK_*` env vars → defaults (DeepSeek). Any OpenAI-compatible provider works without code changes.

## <a name="en-42-configpy-reference"></a>4.2 config.py Reference

All settings are environment-driven with defaults; a `python -m venv`-style check: `./venv/bin/python config.py` prints the loaded LLM config.

| Group | Variable | Default / meaning |
|---|---|---|
| LLM | `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | fallback chain: `LLM_*` → `DEEPSEEK_*` → `OPENAI_API_KEY` / `https://api.deepseek.com` / `deepseek-chat` |
| LLM | `API_TIMEOUT` | 30 s |
| Polish | `POLISH_MODEL` / `POLISH_BASE_URL` / `POLISH_API_KEY` / `POLISH_ITERATIONS` | unset = main-model direct polish; hybrid review mode with lightweight model when set (iterations 1–5, default 3) |
| Stage 1 | `CONCEPT_MODEL` / `CONCEPT_BASE_URL` / `CONCEPT_API_KEY` | unset = `LLM_MODEL` |
| Stage 2 | `HIERARCHY_MODEL` / `HIERARCHY_BASE_URL` / `HIERARCHY_API_KEY` | unset = `LLM_MODEL` (3-stage mode); `""` or `HIERARCHY_SKIP=true` = 2-stage mode |
| Stage 3 | `DELTA_MODEL` / `DELTA_BASE_URL` / `DELTA_API_KEY` | defaults to main model |
| Light LLM | `LLM_LIGHT_MODEL` / `LLM_LIGHT_BASE_URL` / `LLM_LIGHT_API_KEY` / `LLM_LIGHT_ENABLED` | for low-cost batch tasks (definition fallback, dictionary lookup); enabled iff `LLM_LIGHT_MODEL` set |
| MCP | `MCP_SERVER_SCRIPT` | auto-pointed to `mcp_server.py` (no manual config) |
| Debug | `DEBUG_OUTPUT_ENABLED` / `DEBUG_OUTPUT_DIR` | `true` / `debug_output/` (per-session intermediate results) |
| Details | `DETAILS_ENRICHMENT_ENABLED` | `true` — AI-reply definitions/explanations appended to node `details` |
| Depth-first | `DEPTH_FIRST_ENABLED` / `MIN_TREE_DEPTH` / `MAX_SIBLINGS_PER_NODE` | `true` / 3 / 6 |
| Eval align | `EVAL_STRUCTURE_ALIGN` / `MAX_CONCEPTS` / `EVAL_TARGET_DEPTH` / `EVAL_MAX_SIBLINGS` | `false` / 12 / 2 / 4 — compact hierarchy for batch evaluation scenarios |
| Postprocess | `TREE_POSTPROCESS_ENABLED` | `true` — deterministic structure repair before persist |
| Annotation | `ANNOTATION_ENABLED` | `true` — term underline annotation |
| Wikipedia | `WIKIPEDIA_LANGUAGE` / `WIKIPEDIA_TIMEOUT` / `WIKIPEDIA_USER_AGENT` / `WIKIPEDIA_RATE_LIMIT` | `en` / 5 s / project UA / 1.0 req/s |
| Dictionary | `FREE_DICT_TIMEOUT` | 5 s |

## <a name="en-43-gitignore-conventions"></a>4.3 .gitignore Conventions

Only source code, docs, and reference inputs (gold standards, audio) are committed; runtime outputs are never tracked:

- **Secrets**: `.env`, `*.env`, `.env.local`, `api.env` — never committed.
- **Python/venv**: `__pycache__/`, `*.py[cod]`, `venv/`, `env/`.
- **IDE**: `.vscode/*` (except `settings.json`, `tasks.json`), `.idea/`.
- **Model cache**: `.hf_cache/`.
- **Debug output**: `debug_output/`.
- **Reports**: `evaluation/eval_report_*.md`, `evaluation/eval_report_example_*.md`, root `Report_*.md`, `evaluation_audit_report.md`, `hungarian_label_evaluation.md`.
- **Sessions**: `evaluation/data/sessions/`.
- **Generated artifacts**: `reference_example/`, `maps/`.

## <a id="en-5-testing-and-maintenance"></a>5. Testing and Maintenance

## <a id="en-51-run-all-tests"></a>5.1 Run All Tests

Run each test file from the project root with the venv Python:

```bash
./venv/bin/python test_core.py          # core pipeline pure functions (unittest): state_merge, tree flatten round-trip, depth stats, JSON parsing
./venv/bin/python test_api.py           # OpenAI-compatible API connectivity (needs a reachable API key)
./venv/bin/python test_eval_fixes.py    # regression: ICC(3,k) / Kendall's W / tree_utils defenses / token_reduction
./venv/bin/python test_eval_hierarchy.py # regression: Edge/Hierarchy metrics — id-type consistency, empty-mu, nTED, PC-F1, threshold, multi-run averaging (unittest)
./venv/bin/python test_link_type.py     # link_type preserved through flatten_to_tree ↔ flatten_from_tree round-trip
```

`test_core.py` and `test_eval_hierarchy.py` are `unittest` suites (run `./venv/bin/python -m unittest test_core test_eval_hierarchy` as an alternative); the others are plain scripts.

## <a name="en-52-scripts-utilities"></a>5.2 scripts/ Utilities

| Script | Purpose | Usage |
|---|---|---|
| `cleanup_debug.py` | Delete `debug_output/` session dirs older than N days (not wired into startup; run manually) | `./venv/bin/python scripts/cleanup_debug.py --days 30 --dry-run` |
| `audit_edge_zero.py` | Temporary root-cause audit for zero Edge metrics — replays the gold-loading path (root → GTC → YQL) and compares edge sets | `./venv/bin/python scripts/audit_edge_zero.py` |
| `audit_postprocess.py` | Verify generated-side tree postprocessing benefit: evaluate original vs postprocessed map per pair (Edge-F1/UAS/TP/FP/FN) | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python scripts/audit_postprocess.py [session_ts ...]` |
| `select_best_example.py` | Step 1 of gold-example selection: rank recordings by best + most stable across GTC and YQL baselines | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python scripts/select_best_example.py` |
| `inspect.sh` | One-click MCP Inspector: wraps `mcp_server.py` with the official inspector for an interactive JSON-RPC debug UI in the browser (needs Node.js ≥ 18) | `bash scripts/inspect.sh` |

Maintenance notes:

- `debug_output/` accumulates per-session intermediates (transcription, per-stage pipeline results, generated maps, annotation caches); clean it with `cleanup_debug.py` — it never runs automatically.
- Session dirs under `evaluation/data/sessions/` are reusable inputs for `--reuse-sessions` offline re-computation; keep them if regression runs are planned.
- `maps/` holds saved maps from the web UI and the CLI; `.gitignore` excludes it from version control.

---

# Part II — 中文

## <a id="zh-1-三十秒速览"></a>1. 三十秒速览

### 各模块一句话职责

| 模块 | 职责 |
|---|---|
| `main.py` | FastAPI 编排层。纯编排器——不直接调用 LLM、不含业务逻辑；对每个 MCP 工具结果做结构校验，失败自动重试与降级。 |
| `mcp_client.py` | 以子进程方式拉起 `mcp_server.py`，通过 stdio 走 MCP 协议通信。 |
| `mcp_server.py` | 对外提供 8 个 MCP 工具（聊天、转录、润色、导图修改、标注、定义）。 |
| `mindmap_agent.py` | 三阶段管线（概念提取 → 层级规划 → Delta 生成）与单模型兜底 Agent。 |
| `cli_pipeline.py` | 无 Web 依赖的命令行管线：音频/文本 → 导图 JSON，保存到 `maps/`。 |
| `evaluation/run_evaluation.py` | 评估统一入口：交互式 CLI、批量模式、离线重算。 |
| `index.html` | Vue3 + G6 v5 前端：聊天、转录、画布、连线编辑、中英切换、导出/导入、导图 CRUD。 |
| `config.py` | 全部由环境变量驱动的配置，带默认值。 |

### 一次请求的数据流向

```
浏览器 → POST /chat → main.py 编排 →
  MCP chat_generate（聊天回复）→
  MCP modify_mind_map_v2（三阶段管线，增量修改）→
  {answer, map} → 前端 G6 渲染
```

### 最小可运行示例

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
# 编辑 api.env：填入 DEEPSEEK_API_KEY / LLM_API_KEY
./venv/bin/python main.py
# 浏览器打开 http://localhost:8000
```

## <a id="zh-2-主功能使用"></a>2. 主功能使用

## <a id="zh-21-安装依赖"></a>2.1 安装依赖

创建虚拟环境并从 `requirements.txt` 安装：

```bash
cd /home/akku/ai-mindmap-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

注意事项：

- 一律通过项目 venv 运行（`./venv/bin/python ...`），不要使用系统 Python。
- 核心依赖：`fastapi`、`uvicorn`、`openai`、`mcp>=1.0.0`、`python-dotenv`、`wikipedia-api`、`openai-whisper`、`sentence-transformers`。
- 评估指标额外依赖 `nltk`、`rouge-score`、`bert-score`、`jiwer`、`jieba`、`zss`、`scipy`（均已写入 `requirements.txt`）。
- 可选 `pypinyin` 用于离线拼音生成；未安装时自动回退 LLM。
- `openai-whisper` 与 `sentence-transformers` 首次使用会下载模型（Whisper `small`、嵌入模型 `paraphrase-multilingual-MiniLM-L12-v2`）；嵌入模型缓存在 `.hf_cache/`。

## <a name="zh-22-配置并启动后端"></a>2.2 配置并启动后端

```bash
./venv/bin/python main.py
```

- 服务监听 `0.0.0.0:8000`；前端由后端同源提供，浏览器访问 `http://localhost:8000`（GET `/` 返回 `index.html`）。
- 启动时 FastAPI lifespan 通过 `mcp_client.py` 拉起 MCP 服务端子进程（`mcp_server.py`）；客户端启动失败则服务拒绝启动。
- CORS 仅放行 `http://localhost:8000` 与 `http://127.0.0.1:8000`——本项目为内部工具，无登录/认证设计。
- 启动前先在 `.env` 中配置 API 密钥（由 `config.py` 加载），详见第 4 节。

## <a name="zh-23-前端界面使用"></a>2.3 前端界面使用

单页前端（Vue3 + Tailwind + G6 v5 画布）由后端同源提供。主要功能：

**聊天**

- 输入消息后回车或点击发送 → `POST /chat`，请求体 `{message, current_map:{nodes,links}}`；返回 `answer`（聊天文本）与 `map`（更新后的 `{tree, nodes, links}`），画布随之重渲染。
- 语言自动检测：第一条用户消息时，界面语言自动跟随输入语言（含中日韩字符 → 中文），除非此前已手动选择过语言。
- 转录作为上下文：打开「转录作为上下文」开关后，转录列表随聊天请求一起发送（`transcript_context` 字段）。
- 子树对话：从某个节点开启子话题——新节点挂载到该节点之下；对话拥有独立记忆，只看得到该子树及其祖先。

**音频转录**

- 上传音频文件 → `POST /upload_audio` → Whisper 转录 + LLM 润色；结果带发言人/时间显示在转录面板。
- 每条转录可编辑、删除、重新下载；转录列表既用于画图，也可作为聊天上下文。

**画布（G6 v5）**

- 支持拖拽节点、缩放、折叠/展开分支；选中节点可查看 `details`、删除节点、或开启子树对话。
- 连线编辑：点击连线可修改连线类型（共 7 种，见 2.5）与标签，也可删除连线。
- 点击带下划线的标注术语，弹出术语定义浮窗。

**中英切换**

- 设置面板提供界面语言选择（English / 中文）；切换后全部界面文案即时变化，G6 画布同步重渲染（连线类型标签跟随语言）。
- 偏好持久化在 `localStorage`（键 `mindmap-settings`）；手动选择的语言优先于自动检测。

**导出 / 导入**

- 导出 PNG：画布截图下载（2 倍像素比，`graph.toDataURL`）。
- 导出 JSON：当前 `{nodes, links}` 下载为 `mindmap_YYYY-MM-DD.json`。
- 导入 JSON：选择 `{nodes, links}` 格式文件，替换画布内容。

**导图 CRUD（持久化在 `maps/*.json`）**

- 保存 `POST /save_map` `{map_data, name}` → 返回 `map_id`（8 位 UUID）。
- 加载 `GET /load_map?map_id=...`；列表 `GET /list_maps`（按更新时间倒序）；重命名 `POST /rename_map`；删除 `DELETE /delete_map?map_id=...`。

**术语标注与定义**

- `POST /annotate` 分析导图并给关键术语加下划线（`density_mode`：low/medium/high；`detail_level`：brief/medium/detailed；`language`：zh/en）。
- `POST /define` 获取术语定义——Wikipedia 优先、LLM 回退，另附 IPA 音标与字面含义（走 `lookup_dictionary`）。

## <a name="zh-24-三阶段管线"></a>2.4 三阶段管线

`modify_mind_map_v2` 内部执行三阶段多模型管线（由 `mindmap_agent.py` 中的 `MindMapPipelineOrchestrator` 编排）：

1. **阶段 1 — 概念提取**（`ConceptExtractionAgent`）：从对话/转录中提取原子化概念（label、color、details）。
2. **阶段 2 — 层级规划**（`HierarchyPlanningAgent`）：将概念分组规划父子关系（支持递归子分组）。
3. **阶段 3 — Delta 生成**（`DeltaGenerationAgent`）：输出增删改指令（`add_nodes` / `update_nodes` / `append_details` / `add_links`），由 `state_merge` 应用到当前导图。返回 `{tree, nodes, links}`。

降级链（每阶段失败自动兜底）：

- 阶段 1 失败 → 跳过阶段 1+2，直接使用 legacy 单模型 Agent。
- 阶段 2 失败 → 跳过阶段 2；阶段 3 仅接收概念提示。
- 阶段 3 失败 → 原图原样返回。

模型配置（全部可选，未配置自动回退 `LLM_MODEL`，行为与单模型 `modify_mind_map` 完全一致）：

- `CONCEPT_MODEL` / `CONCEPT_BASE_URL` / `CONCEPT_API_KEY` — 阶段 1。
- `HIERARCHY_MODEL` / `HIERARCHY_BASE_URL` / `HIERARCHY_API_KEY` — 阶段 2。显式设 `HIERARCHY_MODEL=""` 或 `HIERARCHY_SKIP=true` 切换为两阶段模式。
- `DELTA_MODEL` / `DELTA_BASE_URL` / `DELTA_API_KEY` — 阶段 3（默认复用主力模型）。

相关开关：`DETAILS_ENRICHMENT_ENABLED`（把 AI 回复中的定义/解释条目化追加进节点 `details`）、`DEPTH_FIRST_ENABLED` / `MIN_TREE_DEPTH` / `MAX_SIBLINGS_PER_NODE`（深度优先生成策略）、`TREE_POSTPROCESS_ENABLED`（落库前的确定性结构修复：环检测切断、孤儿节点挂接、扁平树补层）。

管线通过 MCP 工具 `modify_mind_map_v2` 被调用；Web 路径上唯一调用方是编排层 `main.py`，`cli_pipeline.py` 与评估框架同样会调用。

## <a name="zh-25-mcp-服务器-8-个工具"></a>2.5 MCP 服务器 8 个工具

`mcp_server.py` 以子进程方式运行，经 MCP stdio 协议暴露 8 个工具；`mcp_client.py` 统一调度，带校验与重试（重试 1 次，仍失败则降级）。

| # | 工具 | 参数 | 返回 |
|---|---|---|---|
| 1 | `chat_generate` | `messages`（OpenAI 格式消息列表） | `{reply_text}` |
| 2 | `transcribe_audio` | `file_path` | `{raw_text, detected_language}` |
| 3 | `polish_text` | `raw_text`、`detected_language`、`session_ts?` | `{polished_text}` |
| 4 | `modify_mind_map` | `chat_history`、`current_map` | `{tree, nodes, links}` |
| 5 | `modify_mind_map_v2` | `chat_history`、`current_map`、`session_ts?` | `{tree, nodes, links}` |
| 6 | `annotate_terms` | `current_map`、`density_mode`、`detail_level`、`user_language`、`session_ts?` | `{status, annotations, detail_level}` |
| 7 | `get_definition` | `term`、`detail_level`、`language`、`session_ts?` | `{definition, wikipedia_definition, wikipedia_url, llm_definition, ipa, literal_meaning, source}` |
| 8 | `lookup_dictionary` | `term`、`session_ts?` | IPA + 字面含义字典 |

说明：

- `tree` 为 G6 嵌套树格式（前端直接消费）；`nodes`/`links` 为扁平格式，用于增量回传。
- `modify_mind_map_v2` = 三阶段管线；`modify_mind_map` = 单模型 ReAct（未配置专用模型时两者行为一致）。
- 连线类型（单一事实来源：`schema.py` 的 `LINK_TYPE_SCHEMA`，共 7 种）：`solid` 父子关系、`dashed` 间接关联、`containment` 包含、`dotted` 弱关联、`reference` 引用、`contrast` 对比、`causal` 因果；非法类型自动回退 `solid`。
- `get_definition` 链路：Wikipedia → LLM → IPA + 字面含义（`source` 字段标明实际命中来源）。

## <a name="zh-26-cli-管线-cli_pipelinepy"></a>2.6 CLI 管线（cli_pipeline.py）

无 Web 依赖的纯命令行管线（Whisper 转录 + LLM 导图生成），自动加载 `api.env`（override）。结果保存到 `maps/{map_id}.json`；日志走 stderr，结果走 stdout。

```bash
# 文本模式：文本 → 导图
./venv/bin/python cli_pipeline.py "机器学习的分支包括监督学习和无监督学习"

# 音频模式：音频 → Whisper → 润色 → 导图
./venv/bin/python cli_pipeline.py lecture.mp3 --audio --name "课堂笔记"

# 音频模式，跳过 LLM 润色（保留 Whisper 原始转录）
./venv/bin/python cli_pipeline.py lecture.mp3 --audio --skip-polish

# 交互模式：逐轮输入，导图增量构建（输入 /exit 或 Ctrl+C 退出）
./venv/bin/python cli_pipeline.py -i

# 仅依赖检查（不加载模型）
./venv/bin/python cli_pipeline.py --check-deps
```

首次运行需加载 Whisper `small`（约 10–30 秒）。管线优先走三阶段管线，失败自动降级单模型 Agent。

## <a id="zh-3-评估框架使用"></a>3. 评估框架使用

## <a id="zh-31-统一入口-evaluationrun_evaluationpy"></a>3.1 统一入口 evaluation/run_evaluation.py

通过项目 venv 运行；`api.env` 在 CLI 入口加载（真实密钥），`.env` 在导入时加载（HF 端点等）。

**交互式模式（默认）** —— 向导式菜单：选择评估方法 → 提供文件 → 逐音频转录/生成/评估 → 输出 Markdown 报告：

```bash
./venv/bin/python evaluation/run_evaluation.py
```

**批量模式** —— 对目录下全部音频按金标准评估：

```bash
./venv/bin/python evaluation/run_evaluation.py --batch \
  --audio-dir evaluation/data/audio \
  --gold-dir evaluation/data/gold \
  --methods label hierarchy efficiency
```

**离线重算（会话复用）** —— 直接读取已保存会话重算指标，跳过转录与 LLM 生成（评估侧修复后的零成本回归）：

```bash
./venv/bin/python evaluation/run_evaluation.py \
  --reuse-sessions 20260804_092828 \
  --methods label hierarchy \
  --prefer-gold GTC
```

**常用参数**

| 参数 | 含义 | 默认值 |
|---|---|---|
| `--batch` | 批量评估模式 | 关 |
| `--audio-dir` / `--gold-dir` | 批量模式的输入目录 | `evaluation/data/audio` / `evaluation/data/gold` |
| `--methods` | 空格分隔的方法列表，如 `label hierarchy qa` | 批量 `label hierarchy efficiency` / 重算 `label hierarchy` |
| `--repeat N` | 每配对独立运行次数，指标取平均 | 1 |
| `--reuse-sessions <ts>` | 离线重算指定会话目录 | 无 |
| `--model-name` | 语义对齐用嵌入模型 | `paraphrase-multilingual-MiniLM-L12-v2` |
| `--threshold` | 语义相似度阈值 τ | 0.70 |
| `--prefer-gold` | 首选金标准基准子目录（GTC / YQL） | 无（自动：root → GTC → YQL） |
| `--postprocess` | 重算时对存储导图应用树形后处理 | 关 |
| `--triple-report` | 生成中文命名的三元组对比报告（STT / Agent 树 / 人类树） | 关 |
| `--auto-install` | 自动 pip 安装缺失依赖 | 关 |
| `--ignore-missing-deps` | 忽略缺失依赖继续执行 | 关 |
| `--gold-example-transcript/json` | 示例演示模式的金标准示例对 | 无 |

注意事项：

- 嵌入模型离线运行时需本地缓存；离线环境请加前缀 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python ...`。
- 输入数据位于 `evaluation/data/`：`audio/`、`gold/`（可含 `GTC/`、`YQL/` 基准子目录）、`concepts/`、`questions/`、`timing/`、`multilingual/`、`human_scores/`、`sessions/`、`standards/`。

## <a name="zh-32-七个评估维度"></a>3.2 七个评估维度

| 方法 | 必需输入 | 核心指标 | 触发方式 |
|---|---|---|---|
| `label` — 节点标签 | gold、audio、concepts | Node-F1、LabelSim、Entity-Recall | 菜单选择 / `--methods` |
| `hierarchy` — 层级结构 | gold、audio | Edge-F1/P/R、UAS、PC-F1、LAR、nTED | 菜单选择 / `--methods` |
| `qa` — 下游 QA | audio | QA 得分（自动生成 20 题，每题 1–5 分） | 菜单选择 / `--methods` |
| `efficiency` — 效率与 STT | audio、timing、transcript、key_terms | WER、token 缩减等 | 菜单选择 / `--methods` |
| `multilingual` — 多语言 | audio、multilingual_results | cn/en/mixed + 噪声测试的 Max Δ Recall | 菜单选择 / `--methods` |
| `human_corr` — 人工对齐 | audio | 交互式 0–10 评分；ICC(3,k)、Kendall's W、overall_normalized | 菜单选择 |
| `full` — 全量报告 | 以上全部 | 全部方法 + 综合评分 | 菜单选择（自动展开为全部方法） |

- 语义对齐采用多语言嵌入的匈牙利匹配，默认 τ=0.7。
- 人工评分（每音频两个分：系统导图 / 人类标注导图，0–10 分）作为层级指标误判的补偿机制计入综合评分。
- 综合评分成分（出自 `evaluation/report/composite.py`）：node_f1 0.20、label_sim 0.10、entity_recall 0.10、edge_f1 0.15、uas 0.10、nted_inv 0.15、pc_f1 0.10，另有 qa/human 在可用时计入；缺失维度被排除后剩余权重重新归一化。解读区间：≥ 0.85 优秀、≥ 0.70 良好、< 0.70 需改进。

## <a name="zh-33-报告输出与阅读"></a>3.3 报告输出与阅读

每个配对生成一份 Markdown 报告，双轨保存：

1. `evaluation/data/sessions/{时间戳}/{配对名}/eval_report.md`（同一目录还保存会话全部中间 JSON）
2. `evaluation/eval_report_{配对名}_{时间戳}.md`（evaluation/ 根目录）

报告阅读方法（可参照任意 `evaluation/eval_report_*.md` 示例）：

- **摘要表**：每个维度一行——核心指标值、评级、PASS/FAIL 状态；综合评分行在最上方。
- **分维度章节**（1 节点标签、2 层级结构、3 QA、4 效率、5 多语言、6 人工、7 综合）：指标表带各指标阈值与评级；层级指标阈值如 Edge-F1 ≥ 0.80、UAS ≥ 0.85、PC-F1 ≥ 0.75、LAR ≥ 0.70、nTED ≤ 0.25；标签指标阈值如 Node-F1 ≥ 0.85、LabelSim ≥ 0.85、Entity-Recall ≥ 0.90。
- **详情块**：匈牙利匹配明细（金标准 vs 生成标签 + 相似度）、实体召回遗漏、边 TP/FP/FN 拆分。
- **综合评分章节**：各成分的值/权重/加权分，缺失维度时会注明权重重新归一化。
- **诊断建议章节**：针对不达标指标自动生成改进建议。

## <a id="zh-4-api-与环境配置"></a>4. API 与环境配置

## <a id="zh-41-env-与-apienv"></a>4.1 .env 与 api.env

两个环境文件并存（均被 gitignore，严禁提交真实密钥）：

- **`.env`** —— 由 `config.py` 在导入时加载（main.py、mcp_server.py、cli_pipeline.py、测试均适用）。推荐在此配置 `LLM_*` 变量与各类开关。示例：
  ```bash
  # 通用 OpenAI 兼容提供商（推荐）
  LLM_API_KEY=sk-xxxx
  LLM_BASE_URL=https://api.deepseek.com
  LLM_MODEL=deepseek-chat
  # 可选：三阶段管线的分阶段模型
  # CONCEPT_MODEL=deepseek-lite
  # HIERARCHY_MODEL=deepseek-lite
  # DELTA_MODEL=deepseek-chat
  ```
- **`api.env`** —— 真实密钥；由 `cli_pipeline.py` 以及 `evaluation/run_evaluation.py` 的 `main()`（仅 CLI 入口，不在导入时加载，避免污染宿主进程）以 `override=True` 加载。示例：
  ```bash
  DEEPSEEK_API_KEY=sk-xxxx
  DEEPSEEK_BASE_URL=https://api.deepseek.com
  DEEPSEEK_MODEL=deepseek-chat
  OPENAI_API_KEY=sk-your-openai-key-here
  ```
- `config.py` 的回退优先级：`LLM_*` 环境变量 → `DEEPSEEK_*` 环境变量 → 默认值（DeepSeek）。任意 OpenAI 兼容提供商均可无缝切换，无需改代码。

## <a name="zh-42-configpy-配置项参考"></a>4.2 config.py 配置项参考

全部配置由环境变量驱动并带默认值；`./venv/bin/python config.py` 可打印当前加载的 LLM 配置做校验。

| 分组 | 变量 | 默认值 / 含义 |
|---|---|---|
| LLM | `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | 回退链：`LLM_*` → `DEEPSEEK_*` → `OPENAI_API_KEY` / `https://api.deepseek.com` / `deepseek-chat` |
| LLM | `API_TIMEOUT` | 30 秒 |
| 润色 | `POLISH_MODEL` / `POLISH_BASE_URL` / `POLISH_API_KEY` / `POLISH_ITERATIONS` | 未配置 = 主力模型直接润色；配置后启用「轻量模型迭代 + 主力终审」混合模式（迭代 1–5，默认 3） |
| 阶段 1 | `CONCEPT_MODEL` / `CONCEPT_BASE_URL` / `CONCEPT_API_KEY` | 未配置 = `LLM_MODEL` |
| 阶段 2 | `HIERARCHY_MODEL` / `HIERARCHY_BASE_URL` / `HIERARCHY_API_KEY` | 未配置 = `LLM_MODEL`（三阶段模式）；`""` 或 `HIERARCHY_SKIP=true` = 两阶段模式 |
| 阶段 3 | `DELTA_MODEL` / `DELTA_BASE_URL` / `DELTA_API_KEY` | 默认复用主力模型 |
| 轻量 LLM | `LLM_LIGHT_MODEL` / `LLM_LIGHT_BASE_URL` / `LLM_LIGHT_API_KEY` / `LLM_LIGHT_ENABLED` | 用于低成本批量任务（定义回退、词典查询）；仅当 `LLM_LIGHT_MODEL` 已设置时启用 |
| MCP | `MCP_SERVER_SCRIPT` | 自动指向 `mcp_server.py`（无需手动配置） |
| 调试 | `DEBUG_OUTPUT_ENABLED` / `DEBUG_OUTPUT_DIR` | `true` / `debug_output/`（按会话目录保存各阶段中间结果） |
| Details 增强 | `DETAILS_ENRICHMENT_ENABLED` | `true` — AI 回复中的定义/解释条目化追加进节点 `details` |
| 深度优先 | `DEPTH_FIRST_ENABLED` / `MIN_TREE_DEPTH` / `MAX_SIBLINGS_PER_NODE` | `true` / 3 / 6 |
| 评估对齐 | `EVAL_STRUCTURE_ALIGN` / `MAX_CONCEPTS` / `EVAL_TARGET_DEPTH` / `EVAL_MAX_SIBLINGS` | `false` / 12 / 2 / 4 — 批量评估场景的紧凑层级 |
| 后处理 | `TREE_POSTPROCESS_ENABLED` | `true` — 落库前的确定性结构修复 |
| 标注 | `ANNOTATION_ENABLED` | `true` — 术语下划线标注 |
| Wikipedia | `WIKIPEDIA_LANGUAGE` / `WIKIPEDIA_TIMEOUT` / `WIKIPEDIA_USER_AGENT` / `WIKIPEDIA_RATE_LIMIT` | `en` / 5 秒 / 项目 UA / 1.0 请求每秒 |
| 词典 | `FREE_DICT_TIMEOUT` | 5 秒 |

## <a name="zh-43-gitignore-约定"></a>4.3 .gitignore 约定

仓库只提交源代码、文档与参考输入数据（金标准、音频）；运行产物一律不入版本控制：

- **密钥类**：`.env`、`*.env`、`.env.local`、`api.env` —— 严禁提交。
- **Python/venv**：`__pycache__/`、`*.py[cod]`、`venv/`、`env/`。
- **IDE**：`.vscode/*`（保留 `settings.json`、`tasks.json`）、`.idea/`。
- **模型缓存**：`.hf_cache/`。
- **调试输出**：`debug_output/`。
- **评估报告**：`evaluation/eval_report_*.md`、`evaluation/eval_report_example_*.md`、根目录 `Report_*.md`、`evaluation_audit_report.md`、`hungarian_label_evaluation.md`。
- **会话数据**：`evaluation/data/sessions/`。
- **生成产物**：`reference_example/`、`maps/`。

## <a id="zh-5-测试与维护"></a>5. 测试与维护

## <a id="zh-51-运行全部测试"></a>5.1 运行全部测试

在项目根目录用 venv Python 逐个运行：

```bash
./venv/bin/python test_core.py           # 核心管线纯函数（unittest）：state_merge、树展平往返、深度统计、JSON 解析
./venv/bin/python test_api.py            # OpenAI 兼容 API 连通性（需要可达的 API Key）
./venv/bin/python test_eval_fixes.py     # 回归：ICC(3,k) / Kendall's W / tree_utils 防御 / token_reduction
./venv/bin/python test_eval_hierarchy.py # 回归：Edge/层级指标——id 类型一致性、空 mu、nTED、PC-F1、阈值、多轮平均（unittest）
./venv/bin/python test_link_type.py      # link_type 在 flatten_to_tree ↔ flatten_from_tree 往返中不丢失
```

`test_core.py` 与 `test_eval_hierarchy.py` 是 `unittest` 套件（也可用 `./venv/bin/python -m unittest test_core test_eval_hierarchy` 运行）；其余为普通脚本直接运行。

## <a name="zh-52-scripts-工具脚本"></a>5.2 scripts/ 工具脚本

| 脚本 | 用途 | 用法 |
|---|---|---|
| `cleanup_debug.py` | 删除 `debug_output/` 中早于 N 天的会话目录（不自动挂入启动流程，手动运行） | `./venv/bin/python scripts/cleanup_debug.py --days 30 --dry-run` |
| `audit_edge_zero.py` | 边指标归零根因验证（临时脚本）——复现金标准加载路径（root → GTC → YQL）并做边集合比对 | `./venv/bin/python scripts/audit_edge_zero.py` |
| `audit_postprocess.py` | 验证生成侧树形后处理收益——逐配对对比原始图 vs 后处理图（Edge-F1/UAS/TP/FP/FN） | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python scripts/audit_postprocess.py [session_ts ...]` |
| `select_best_example.py` | 优质示例筛选第 1 步：在 GTC 与 YQL 双基准下按「表现最好且最稳定」排序录音 | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python scripts/select_best_example.py` |
| `inspect.sh` | MCP Inspector 一键启动：用官方 inspector 包装 `mcp_server.py`，浏览器提供交互式 JSON-RPC 调试界面（需 Node.js ≥ 18） | `bash scripts/inspect.sh` |

维护注意事项：

- `debug_output/` 会不断积累按会话划分的中间产物（转录、各阶段管线结果、生成图、标注缓存）；用 `cleanup_debug.py` 清理，它不会自动运行。
- `evaluation/data/sessions/` 下的会话目录可作为 `--reuse-sessions` 离线重算的输入；有计划做回归验证时请保留。
- `maps/` 存放 Web 界面与 CLI 保存的导图；`.gitignore` 已将其排除出版本控制。