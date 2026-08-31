# AI MindMap Agent — User Manual / 使用手册

> This manual is written for **users**. It explains how to install, configure, run and use every functional module of the system, without going into internal architecture, algorithm details, or implementation mechanisms. The manual contains a complete English version (Part I) followed by a complete Chinese version (Part II).
> 本文档面向**使用者**，说明如何安装、配置、运行和使用系统的每个功能模块，不涉及内部工作原理、算法细节或代码实现机制。本手册先在 Part I（第一部分）给出完整的英文版，随后在 Part II（第二部分）给出完整的中文版。

> **Companion docs / 配套文档**：`README.md` provides a quick start; this manual provides full usage. An older split-bilingual manual lives at `docs/manuals/USER_MANUAL.md`；旧版分离式双语手册见 `docs/manuals/USER_MANUAL.md`。

---

# Part I — English Version / 第一部分 英文版

## 目录 / Table of Contents (English)

- [Chapter 1 Quick Start](#en-sec-1-quick-start)
  - [1.1 What This Is](#en-sec-1-1-what-this-is)
  - [1.2 Module Responsibilities](#en-sec-1-2-modules)
  - [1.3 Minimal Runnable Example](#en-sec-1-3-minimal)
- [Chapter 2 Installation & Configuration](#en-sec-2-install)
  - [2.1 Environment Requirements](#en-sec-2-1-requirements)
  - [2.2 Install Dependencies](#en-sec-2-2-install)
  - [2.3 Config Files `.env` and `api.env`](#en-sec-2-3-config-files)
  - [2.4 Verify Configuration](#en-sec-2-4-verify)
- [Chapter 3 Web Application](#en-sec-3-web)
  - [3.1 Start the Backend](#en-sec-3-1-start)
  - [3.2 UI Features](#en-sec-3-2-ui)
  - [3.3 Voice Workflow](#en-sec-3-3-voice)
  - [3.4 HTTP API Reference](#en-sec-3-4-api)
- [Chapter 4 CLI Pipeline](#en-sec-4-cli)
  - [4.1 Text Mode](#en-sec-4-1-text)
  - [4.2 Audio Mode](#en-sec-4-2-audio)
  - [4.3 Interactive Mode](#en-sec-4-3-interactive)
  - [4.4 Dependency Check](#en-sec-4-4-check)
- [Chapter 5 MCP Server & Tools](#en-sec-5-mcp)
  - [5.1 About the MCP Server](#en-sec-5-1-about)
  - [5.2 The 8 Tools](#en-sec-5-2-tools)
  - [5.3 MCP Inspector](#en-sec-5-3-inspector)
- [Chapter 6 Evaluation Framework](#en-sec-6-evaluation)
  - [6.1 Overview](#en-sec-6-1-overview)
  - [6.2 Interactive Mode](#en-sec-6-2-interactive)
  - [6.3 Example Demo Mode](#en-sec-6-3-example)
  - [6.4 Batch Mode](#en-sec-6-4-batch)
  - [6.5 Gold-example Injection](#en-sec-6-5-gold-inject)
  - [6.6 Offline Re-computation](#en-sec-6-6-reuse)
  - [6.7 Triple Comparison Report](#en-sec-6-7-triple)
  - [6.8 All CLI Parameters](#en-sec-6-8-params)
  - [6.9 Seven Dimensions](#en-sec-6-9-dimensions)
  - [6.10 Reports](#en-sec-6-10-reports)
  - [6.11 Data Directories](#en-sec-6-11-data)
  - [6.12 Dependency Handling](#en-sec-6-12-deps)
- [Chapter 7 Testing & Maintenance](#en-sec-7-test)
  - [7.1 Unit Tests](#en-sec-7-1-tests)
  - [7.2 Helper Scripts](#en-sec-7-2-scripts)
  - [7.3 Experiment Directory](#en-sec-7-3-testdir)
  - [7.4 Maintenance Notes](#en-sec-7-4-maintenance)
- [Chapter 8 Troubleshooting](#en-sec-8-troubleshooting)
- [Chapter 9 Appendix](#en-sec-9-appendix)
  - [9.1 Environment Reference](#en-sec-9-1-env)
  - [9.2 Directory Structure](#en-sec-9-2-structure)
  - [9.3 Version Record](#en-sec-9-3-version)

> **Chinese version / 中文版本**：A complete Chinese translation follows below. Go to the [中文目录 / Chinese Table of Contents](#part-ii-zh)。
> 完整中文版位于下方，点击跳转至 [中文目录 / Chinese Table of Contents](#part-ii-zh)。

---

<a id="en-sec-1-quick-start"></a>

## Chapter 1 Quick Start

<a id="en-sec-1-1-what-this-is"></a>

### 1.1 What This Is

AI MindMap Agent is a mind-map tool that updates your map incrementally as you go. It takes whatever you type or say, looks at the map you already have, and auto-organizes the content into a layered structure through a few cooperating models, keeping things up to date all along.

Typical use cases are pretty obvious: lecture notes, meeting minutes, brainstorming. You talk or type, and the system snaps the main points into a clean hierarchy; keep going and the map just grows with every new round of input.

It also comes with a Web UI (you use it in a browser), a command-line pipeline for when you'd rather skip the browser, and a full set of quality-evaluation tools to measure how good the generated maps actually are.

<a id="en-sec-1-2-modules"></a>

### 1.2 Module Responsibilities

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI orchestration layer exposing HTTP APIs |
| `cli_pipeline.py` | Browser-free CLI pipeline: text/audio → mind map |
| `mindmap_agent.py` | Core agent that generates/updates the map (multi-stage collaboration) |
| `tools.py`, `schema.py` | Shared utilities and data structures (link types, graph shapes, etc.) |
| `mcp_server.py`, `mcp_client.py` | MCP server & client wrapping chat, transcription, map editing |
| `config.py` | All environment-driven configuration with defaults |
| `index.html` | Browser frontend (chat, canvas, link editor, bilingual UI) |
| `evaluation/run_evaluation.py` | Unified evaluation entry (interactive, batch, offline) |

<a id="en-sec-1-3-minimal"></a>

### 1.3 Minimal Runnable Example

These steps cover "install → set up your keys → fire up the web UI". For a more detailed look at the environment requirements, head to Chapter 2.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Edit .env / api.env and fill in LLM_API_KEY (or DEEPSEEK_API_KEY)
./venv/bin/python main.py
```

Once it's up, open `http:\/\/localhost:8000` in a browser to chat, drop in some audio, and watch the map being generated right in front of you.

> **Note:** The first run downloads the speech-recognition model (Whisper, cached in `~\/.cache\/whisper\/`) and the embedding model (cached in `.hf_cache\/`), which can take from tens of seconds up to a few minutes.

---

<a id="en-sec-2-install"></a>

## Chapter 2 Installation & Configuration

<a id="en-sec-2-1-requirements"></a>

### 2.1 Environment Requirements

- **Python ≥ 3.10**: development and runtime environment.
- **FFmpeg (optional)**: required only when uploading audio in non-WAV formats (e.g. mp3/m4a/ogg).
- **Node.js ≥ 18 (optional)**: required only to open the MCP Inspector debugging UI.

<a id="en-sec-2-2-install"></a>

### 2.2 Install Dependencies

Create a virtual environment and install dependencies in the project root:

```bash
cd /home/akku/ai-mindmap-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Always run commands through the project venv (`./venv/bin/python ...`), not the system Python.

The first run downloads models on its own: Whisper `small` (speech, cached in `~\/.cache\/whisper\/`) and an embedding model (cached in `.hf_cache\/`). If you're in an offline environment, prefix commands with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.

<a id="en-sec-2-3-config-files"></a>

### 2.3 Config Files `.env` and `api.env`

This project talks to an OpenAI-compatible LLM to actually generate the maps and replies. All settings live in environment variables, and there are two main config files (both git-ignored, so never commit real keys).

- **`.env`** — loaded automatically by `config.py` at import time; the recommended place for `LLM_*` variables and feature switches.
- **`api.env`** — holds the real keys, loaded at runtime (with override) by the CLI pipeline, the evaluation entry, and the web server (`main.py`).

Here's the key lookup order: `LLM_*` env vars → `DEEPSEEK_*` env vars → the defaults (DeepSeek). So filling in the `LLM_*` trio in `.env` is basically all you need to switch to any OpenAI-compatible provider.

```bash
# Minimal .env example
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

> **Note:** Keys are written as placeholder `sk-xxxx` here; replace with your real key. Real keys exist only in your local `.env`/`api.env`, never commit them to Git.

<a id="en-sec-2-4-verify"></a>

### 2.4 Verify Configuration

Run the command below to print the currently loaded LLM config and check for anything missing or mismatched (like an OpenAI key pointing at a DeepSeek endpoint).

```bash
./venv/bin/python config.py
```

Output shows the current model, Base URL and key source plus any warnings; fix them as suggested.

---

<a id="en-sec-3-web"></a>

## Chapter 3 Web Application

<a id="en-sec-3-1-start"></a>

### 3.1 Start the Backend

Start the web service:

```bash
./venv/bin/python main.py
```

The service listens on `0.0.0.0:8000`; open `http:\/\/localhost:8000` in a browser (the root path serves the frontend `index.html`). On startup the internal components (MCP server) are started automatically, so you don't have to do anything manually; if those fail to start, the service won't start either and will tell you why.

This is an internal tool with no login built in; CORS only allows `http:\/\/localhost:8000` and `http:\/\/127.0.0.1:8000`, so don't go exposing it to the public internet.

<a id="en-sec-3-2-ui"></a>

### 3.2 UI Features

The frontend is a single-page app (Vue3 + G6 canvas). Here's what it can do and how to actually use it.

**Chat (subtree conversation)**

1. Type a message in the input box and press Enter or click Send.
2. The system replies with text and adds/updates map nodes on the canvas automatically.
3. To attach new content under an existing node, start a "subtree conversation" from that node first, then continue typing — new nodes attach under it, and the conversation only sees that subtree.

**Audio transcription**

1. Click the upload button and choose an audio file (wav/mp3/m4a/ogg/flac).
2. The system transcribes (Whisper) and polishes it automatically; the result appears with speaker/timestamp in the transcript panel.
3. Each entry can be edited, deleted or re-downloaded; the transcript list serves as context for map generation.

**Canvas & link editor**

- Drag nodes, zoom with the wheel, collapse/expand branches; select a node to inspect its details, delete it, or open a subtree conversation.
- Click a link to change its **type** (7 types) or label, or delete it.

Link types (7) and their meaning:

| Type | Meaning |
|---|---|
| `solid` | direct parent-child |
| `dashed` | indirect relation |
| `containment` | containment |
| `dotted` | weak relation |
| `reference` | reference |
| `contrast` | contrast |
| `causal` | causal |

**Language switch**

In the settings panel select the UI language (English / 中文); all text switches instantly and link-type labels follow. Preferences persist in `localStorage`.

**Export / Import**

- Export PNG: download a screenshot of the current canvas.
- Export JSON: download the current map as `mindmap_YYYY-MM-DD.json`.
- Import JSON: load a `{nodes, links}` file to replace the canvas content.

**Map CRUD**

1. Save: name the current map and save to get an 8-char `map_id`.
2. Load: enter a `map_id` to restore it.
3. List: view all saved maps (most recently updated first).
4. Rename/Delete: rename or delete a given map.

Saved maps are stored as JSON under `maps/`.

**Term annotation & definition**

The system can underline key terms and look up their definitions:

1. After requesting annotation, key terms get underlines; clicking an underlined term opens a definition popup (Wikipedia first, LLM fallback, with IPA).
2. You can specify annotation density (low/medium/high), detail level (brief/medium/detailed) and language.

<a id="en-sec-3-3-voice"></a>

### 3.3 Voice Workflow

A typical "voice → mind map" workflow:

1. Upload audio → system transcribes and polishes it (see 3.2).
2. Confirm/edit the transcript, optionally toggle "include transcript as context".
3. Chat in the input box to build the map from it.
4. Review and organize the map on the canvas, then export or save if needed.

<a id="en-sec-3-4-api"></a>

### 3.4 HTTP API Reference

The HTTP endpoints behind the web UI (for integration or scripting).

| Method & Path | Purpose |
|---|---|
| `GET /` | Serve the frontend |
| `POST /chat` | Chat, returns updated map |
| `POST /upload_audio` | Upload audio for transcription |
| `POST /annotate` | Annotate terms |
| `POST /define` | Look up a term definition |
| `POST /save_map` | Save a map |
| `GET /load_map` | Load a map |
| `GET /list_maps` | List saved maps |
| `POST /rename_map` | Rename a map |
| `DELETE /delete_map` | Delete a map |

`POST /chat` request body:

```json
{"message": "补充机器学习的三类方法", "current_map": {"nodes": [], "links": []}}
```

The response contains `answer` (reply text) and `map` (updated `{tree, nodes, links}`).

---

<a id="en-sec-4-cli"></a>

## Chapter 4 CLI Pipeline

`cli_pipeline.py` is a browser-free way to run the pipeline: feed it text or audio and it spits out a mind-map JSON saved to `maps\/{map_id}.json` (logs run to stderr, results to stdout). It pulls the real keys from `api.env` with override.

<a id="en-sec-4-1-text"></a>

### 4.1 Text Mode

Pass a piece of text to generate a map:

```bash
./venv\/bin\/python cli_pipeline.py "机器学习的分支包括监督学习和无监督学习"
```

Output is a map JSON (written to `maps\/`) whose nodes are basically your input points plus their hierarchy.

<a id="en-sec-4-2-audio"></a>

### 4.2 Audio Mode

Pass an audio path with `--audio` to transcribe-and-polish before generating a map:

```bash
# audio → transcript → polish → map
./venv\/bin\/python cli_pipeline.py lecture.mp3 --audio --name "课堂笔记"
# skip LLM polishing, keep the raw Whisper transcript
./venv\/bin\/python cli_pipeline.py lecture.mp3 --audio --skip-polish
```

The first run loads Whisper `small` (~10–30 s). `--name` names the map (default `cli-mindmap`).

<a id="en-sec-4-3-interactive"></a>

### 4.3 Interactive Mode

Provide input round by round; the map grows incrementally:

```bash
./venv\/bin\/python cli_pipeline.py -i
```

Type `\/exit` or press `Ctrl+C` to quit.

<a id="en-sec-4-4-check"></a>

### 4.4 Dependency Check

Check dependencies only, without loading models:

```bash
./venv\/bin\/python cli_pipeline.py --check-deps
```

---

<a id="en-sec-5-mcp"></a>

## Chapter 5 MCP Server & Tools

<a id="en-sec-5-1-about"></a>

### 5.1 About the MCP Server

The MCP (Model Context Protocol) server runs as a background subprocess and wraps up chat, transcription, map editing, annotation and definition for the main program. **Regular users don't need to start or configure it at all** — the system launches it automatically in the background.

<a id="en-sec-5-2-tools"></a>

### 5.2 The 8 Tools

| Tool | Purpose | Key args | When triggered |
|---|---|---|---|
| `chat_generate` | Chat reply | `messages` | when chatting |
| `transcribe_audio` | Transcribe | `file_path` | on audio upload |
| `polish_text` | Polish text | `raw_text`, `detected_language` | after transcription |
| `modify_mind_map` | Update map | `chat_history`, `current_map` | map updates |
| `modify_mind_map_v2` | Multi-stage update | `chat_history`, `current_map` | default map updates |
| `annotate_terms` | Annotate terms | `current_map`, `density_mode`, `detail_level` | on annotate |
| `get_definition` | Term definition | `term`, `detail_level`, `language` | on term click |
| `lookup_dictionary` | Dictionary lookup | `term` | definition fallback |

> **Note:** `modify_mind_map_v2` is the multi-stage collaborative version (the default); `modify_mind_map` is the single-model version. They behave identically when no stage-specific models are configured.

<a id="en-sec-5-3-inspector"></a>

### 5.3 MCP Inspector

To view all tool calls interactively, run the MCP Inspector:

```bash
bash scripts\/inspect.sh
```

Then open `http:\/\/localhost:6274` in a browser for a JSON-RPC debugging UI (requires Node.js ≥ 18).

---

<a id="en-sec-6-evaluation"></a>

## Chapter 6 Evaluation Framework

The evaluation framework is what measures how good the maps the system produces actually are. Everything funnels through `evaluation\/run_evaluation.py`, which gives you several methods and several run modes. **Always run evaluation through the project venv.**

<a id="en-sec-6-1-overview"></a>

### 6.1 Overview

The entry supports five run paths: demo mode, interactive (default), batch, offline reuse, and triple comparison report.

Real keys live in `api.env`, which is loaded up by the CLI pipeline, the evaluation entry, and the web server (`main.py`); `.env` gets loaded at import time (e.g. HF endpoints).

<a id="en-sec-6-2-interactive"></a>

### 6.2 Interactive Mode

Interactive mode (the default) walks you through a wizard-style menu, which is handy for one or just a few audio files:

```bash
./venv\/bin\/python evaluation\/run_evaluation.py
```

Steps:

1. Choose the interface language (or pass `--lang zh` \/ `--lang en` directly).
2. Pick the dimensions to evaluate in the method menu (you may also pick §0 demo mode, see 6.3).
3. Choose the file mode: A automatically detects same-named pairs under `evaluation\/data\/`, or B lets you type file paths manually.
4. Per audio, transcription, generation and evaluation run, then a Markdown report is produced.

<a id="en-sec-6-3-example"></a>

### 6.3 Example Demo Mode

This is the **§0 demo mode** tucked away in the evaluation menu: it runs the whole evaluation flow on **built-in example data** so you can get the hang of how the framework works and what the output looks like, **without needing any input files**.

1. Pick §0 in the interactive menu.
2. The system uses built-in gold map, concept set, question set etc. and auto-runs the six-dimension evaluation.
3. A report marked with `**example**` is produced.

> **Note:** Demo mode is **mutually exclusive** with real evaluation — mixing is rejected. It does not truly evaluate your data.

<a id="en-sec-6-4-batch"></a>

### 6.4 Batch Mode

Batch-evaluate every audio file in a directory, one by one, against gold standards:

```bash
./venv\/bin\/python evaluation\/run_evaluation.py --batch \\
  --audio-dir evaluation\/data\/audio --gold-dir evaluation\/data\/gold \\
  --methods label hierarchy efficiency
```

Conventions:

- Audio lives in `--audio-dir` (default `evaluation\/data\/audio`), gold in `--gold-dir` (default `evaluation\/data\/gold`).
- Audio and gold are paired by matching file names.
- `--methods` selects methods; if omitted, default is `label hierarchy efficiency`.

> **Note:** `full` expands to all methods only in the **interactive** menu; in **batch mode it does not** expand, so list methods explicitly (e.g. `--methods label hierarchy qa efficiency multilingual human_corr`).

<a id="en-sec-6-5-gold-inject"></a>

### 6.5 Gold-example Injection

In batch mode you can hand over a "gold-example pair" so the model **copies that structural style** when it generates maps (few-shot prompting); this isn't an evaluation mode by itself:

```bash
./venv\/bin\/python evaluation\/run_evaluation.py --batch --audio-dir ... --gold-dir ... \\
  --gold-example-transcript example.txt --gold-example-json example.json
```

`--gold-example-transcript` and `--gold-example-json` **must be provided together**: the former is a transcript text, the latter the corresponding gold map JSON; together they form a style reference.

> **Note:** This is a **different mechanism** from the §0 demo in 6.3 — 6.3 demonstrates evaluation with built-in data; here your own example guides generation. Don't conflate them.

<a id="en-sec-6-6-reuse"></a>

### 6.6 Offline Re-computation

Read a saved evaluation session and **skip transcription and generation** entirely, recomputing the metrics from the session's stored maps and gold — a handy zero-cost regression run after you fix something on the evaluation side:

```bash
./venv\/bin\/python evaluation\/run_evaluation.py \\
  --reuse-sessions 20260804_092828 --methods label hierarchy --prefer-gold GTC
```

- `--reuse-sessions <ts>`: the session directory (e.g. `20260804_092828`).
- `--methods` defaults to `label hierarchy` when omitted.
- `--prefer-gold GTC`: which gold baseline subdir (GTC\/YQL) to prefer when several exist.
- `--postprocess`: apply tree postprocessing to stored maps during recomputation.

<a id="en-sec-6-7-triple"></a>

### 6.7 Triple Comparison Report

Generate a comparison report across "STT transcript \/ Agent-generated tree \/ human-labeled tree":

```bash
./venv\/bin\/python evaluation\/run_evaluation.py --triple-report \\
  --audio-dir evaluation\/data\/audio --gold-dir evaluation\/data\/gold
```

Output is a Chinese-named triple comparison report (sit at `evaluation\/`).

<a id="en-sec-6-8-params"></a>

### 6.8 All CLI Parameters

| Parameter | Meaning | Default |
|---|---|---|
| `--lang {zh,en}` | CLI language | asked at startup in interactive |
| `--batch` | Batch mode | off |
| `--audio-dir` | Audio dir | `evaluation\/data\/audio` |
| `--gold-dir` | Gold dir | `evaluation\/data\/gold` |
| `--methods` | methods list | batch `label hierarchy efficiency`\/reuse `label hierarchy` |
| `--repeat N` | runs per pair | **5** \/ pass `--repeat 1` to run once |
| `--reuse-sessions <ts>` | offline reuse | none |
| `--model-name` | embedding model | `paraphrase-multilingual-MiniLM-L12-v2` |
| `--threshold` | similarity threshold | 0.70 |
| `--prefer-gold` | preferred gold | auto: root → GTC → YQL |
| `--postprocess` | apply postprocess on reuse | off |
| `--triple-report` | triple report | off |
| `--auto-install` | auto-install deps | off |
| `--ignore-missing-deps` | ignore missing deps | off |
| `--gold-example-transcript` | gold-example transcript | none |
| `--gold-example-json` | gold-example map json | none |

<a id="en-sec-6-9-dimensions"></a>

### 6.9 Seven Dimensions

| Method | Required inputs | Key metrics | Trigger |
|---|---|---|---|
| `label` — node labels | gold, audio, concepts | Node-F1, LabelSim, Entity-Recall | menu \/ `--methods` |
| `hierarchy` — hierarchy | gold, audio | Edge-F1\/P\/R, UAS, PC-F1, LAR, nTED | menu \/ `--methods` |
| `qa` — downstream QA | audio | QA score (auto 20 questions, 1–5 each) | menu \/ `--methods` |
| `efficiency` — efficiency & STT | audio, timing, transcript, key_terms | WER, token reduction … | menu \/ `--methods` |
| `multilingual` — multilingual | audio, multilingual_results | Max Δ Recall (cn\/en\/mixed + noise) | menu \/ `--methods` |
| `human_corr` — human alignment | audio | interactive 0–10 scoring; ICC(3,k), Kendall's W, overall_normalized | menu \/ `--methods` |
| `full` — full report | all above | all methods + composite | interactive only |

Notes:

- Semantic alignment uses Hungarian matching on multilingual embeddings; default τ=0.7.
- Human scoring compensates hierarchy false negatives and enters the composite score.
- Composite weights: node_f1 0.20, edge_f1 0.08, label_sim 0.10, entity_recall 0.10, nted_inv 0.08, uas 0.07, pc_f1 0.07, qa_score 0.10, human_score 0.20; if a dimension is missing its weight gets dropped and the rest are renormalized. Reading the score: ≥0.85 excellent, ≥0.70 good, <0.70 needs work.

<a id="en-sec-6-10-reports"></a>

### 6.10 Reports

Each pair produces a Markdown report saved in **two places**:

1. `evaluation\/data\/sessions\/{timestamp}\/{pair}\/eval_report.md` (also holds all session intermediates)
2. `evaluation\/eval_report_{pair}_{timestamp}.md` (project `evaluation\/` root)

Report structure:

- **Summary table**: one row per dimension (key metric, grade, PASS\/FAIL), composite on top.
- **Dimension sections**: per-dimension metric tables with thresholds and grades.
- **Detail blocks**: Hungarian match details, entity-recall misses, edge TP\/FP\/FN breakdown.
- **Composite section**: per-component value\/weight\/weighted score.
- **Diagnostics**: auto-suggestions for under-performing metrics.

Key thresholds (for reading grades):

- Hierarchy: Edge-F1 ≥ 0.80, UAS ≥ 0.85, PC-F1 ≥ 0.75, LAR ≥ 0.70, nTED ≤ 0.25.
- Label: Node-F1 ≥ 0.85, LabelSim ≥ 0.85, Entity-Recall ≥ 0.90.

<a id="en-sec-6-11-data"></a>

### 6.11 Data Directories

Evaluation input data lives under `evaluation\/data\/`: audio, gold (with optional `GTC\/`, `YQL\/` baselines), concepts, questions, timing, multilingual, human_scores, sessions, standards.

- `audio\/`: audio files; `gold\/`: gold maps; `concepts\/`: concept sets; `questions\/`: question sets; `timing\/`: timing logs & key terms; `multilingual\/`: multilingual results; `human_scores\/`: human scoring data; `sessions\/`: saved sessions (for `--reuse-sessions`); `standards\/`: annotation standards.

<a id="en-sec-6-12-deps"></a>

### 6.12 Dependency Handling

Each method needs certain third-party packages. The system checks up front; if any are missing:

- pass `--auto-install` to let the system pip-install missing dependencies;
- or pass `--ignore-missing-deps` to continue with whatever can run.

Per-method deps: `label`→numpy, sentence-transformers; `hierarchy`→numpy, zss, sentence-transformers; `qa`→openai; `efficiency`→jiwer, jieba, scipy; `human_corr`→scipy; `full`→zss, jiwer, jieba, scipy, sentence-transformers, openai (it assumes numpy too, which is listed separately).

> **Note:** Running the embedding model offline needs a local cache; prefix commands with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.

---

<a id="en-sec-7-test"></a>

## Chapter 7 Testing & Maintenance

<a id="en-sec-7-1-tests"></a>

### 7.1 Unit Tests

Unit tests live in `tests\/` (six files). Run them from the project root with the venv Python:

```bash
./venv\/bin\/python tests\/test_core.py
./venv\/bin\/python tests\/test_api.py              # needs a reachable API key
./venv\/bin\/python tests\/test_eval_fixes.py
./venv\/bin\/python tests\/test_eval_hierarchy.py
./venv\/bin\/python tests\/test_link_type.py
./venv\/bin\/python tests\/test_compat_provider.py
```

`test_core.py` and `test_eval_hierarchy.py` are also `unittest` suites; you may run them as below, and all can run under `pytest`:

```bash
./venv\/bin\/python -m unittest tests.test_core tests.test_eval_hierarchy
pytest tests\/
```

What each file verifies:

- `test_core.py`: core pipeline pure functions (map merge, tree flatten round-trip, depth stats, JSON parsing).
- `test_api.py`: OpenAI-compatible API connectivity.
- `test_eval_fixes.py`: evaluation regressions (ICC, Kendall's W, token reduction, etc.).
- `test_eval_hierarchy.py`: hierarchy-metric regressions (Edge\/UAS, empty values, nTED, PC-F1, thresholds, multi-run averaging).
- `test_link_type.py`: link type preserved across tree round-trips.
- `test_compat_provider.py`: multi-provider config compatibility.

<a id="en-sec-7-2-scripts"></a>

### 7.2 Helper Scripts

Scripts under `scripts\/` are all **run by hand** — none of them are wired into startup:

| Script | Purpose | Example |
|---|---|---|
| `cleanup_debug.py` | clean old debug dirs | `./venv\/bin\/python scripts\/cleanup_debug.py --days 30 --dry-run` |
| `audit_edge_zero.py` | audit zero-edge | `./venv\/bin\/python scripts\/audit_edge_zero.py` |
| `audit_postprocess.py` | verify postprocess benefit | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv\/bin\/python scripts\/audit_postprocess.py [ts ...]` |
| `select_best_example.py` | select best example | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv\/bin\/python scripts\/select_best_example.py` |
| `inspect.sh` | launch MCP Inspector (see 5.3) | `bash scripts\/inspect.sh` |

<a id="en-sec-7-3-testdir"></a>

### 7.3 Experiment Directory

`test\/` (lowercase) is an **experiment directory**, not a set of unit tests; it's non-core stuff used only to reproduce the research experiments (see `test\/REPORT.md`).

- `run_experiment.py`: two-way QA comparison (map path vs full-text path).
- `llm_server.py`: a local OpenAI-compatible LLM serving script (e.g. `--port 8765`).
- `fetch_texts.py`: experiment corpus extraction.

<a id="en-sec-7-4-maintenance"></a>

### 7.4 Maintenance Notes

- `debug_output\/` accumulates intermediate outputs from every run; clean it periodically with `scripts\/cleanup_debug.py` (it never runs automatically).
- Session dirs under `evaluation\/data\/sessions\/` are inputs for `--reuse-sessions`; keep them if you plan regressions.
- `maps\/` holds maps saved by the web UI and CLI; `.gitignore` excludes it from version control.
- Generated reports, debug files and model caches are all git-ignored; no need to delete them manually (unless disk is tight).

---

<a id="en-sec-8-troubleshooting"></a>

## Chapter 8 Troubleshooting

| Issue | Cause & fix |
|---|---|
| LLM features unavailable | key unset; fill `LLM_API_KEY` in `.env` (see 2.3) |
| 401 \/ endpoint mismatch | key\/endpoint source mismatch (e.g. OpenAI key vs DeepSeek endpoint); run config.py, fix `LLM_BASE_URL`\/`LLM_MODEL` |
| model download slow\/fails | restricted network; offline cache or the offline flags `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` |
| missing-dependency prompt | use `--auto-install`, or `--ignore-missing-deps`. Note numpy is already declared in requirements.txt |
| port 8000 in use | stop the process or change the port |
| non-WAV audio fails | install FFmpeg (see 2.1) |
| `human_corr` fails | it needs human scores; score interactively or pre-save questionnaires |

---

<a id="en-sec-9-appendix"></a>

## Chapter 9 Appendix

<a id="en-sec-9-1-env"></a>

### 9.1 Environment Reference

Below are the main env-var groups this manual touches on (all optional; a default or fallback kicks in when unset). `config.py` is the final word.

| Group | Variables | Meaning |
|---|---|---|
| General LLM | `LLM_API_KEY`\/`LLM_BASE_URL`\/`LLM_MODEL` | main model trio; fallback `LLM_*` → `DEEPSEEK_*` → default DeepSeek |
| General LLM | `API_TIMEOUT` | timeout in s, default 30 |
| General LLM | `LLM_MAX_TOKENS` | max output tokens, default 8192 |
| General LLM | `LLM_JSON_FALLBACK` | plain-JSON fallback, default true |
| Polish | `POLISH_MODEL`\/`POLISH_BASE_URL`\/`POLISH_API_KEY`\/`POLISH_ITERATIONS` | polish mode; main model if unset |
| Stage 1 | `CONCEPT_MODEL`\/`CONCEPT_BASE_URL`\/`CONCEPT_API_KEY` | concept-extraction model |
| Stage 2 | `HIERARCHY_MODEL`\/`HIERARCHY_BASE_URL`\/`HIERARCHY_API_KEY` | hierarchy model; "" or `HIERARCHY_SKIP=true` = two-stage |
| Stage 3 | `DELTA_MODEL`\/`DELTA_BASE_URL`\/`DELTA_API_KEY` | delta-generation model, defaults to main model |
| Light LLM | `LLM_LIGHT_MODEL`\/`LLM_LIGHT_BASE_URL`\/`LLM_LIGHT_API_KEY`\/`LLM_LIGHT_ENABLED` | low-cost batch tasks (definition fallback, dictionary) |
| Debug | `DEBUG_OUTPUT_ENABLED`\/`DEBUG_OUTPUT_DIR` | per-stage intermediates; default true, `debug_output\/` |
| Details | `DETAILS_ENRICHMENT_ENABLED` | append AI reply definitions to node details; default true |
| Deep-first | `DEPTH_FIRST_ENABLED`\/`MIN_TREE_DEPTH`\/`MAX_SIBLINGS_PER_NODE` | dig-children preference; true, 3, 6 |
| Eval align | `EVAL_STRUCTURE_ALIGN`\/`MAX_CONCEPTS`\/`EVAL_TARGET_DEPTH`\/`EVAL_MAX_SIBLINGS` | compact hierarchy for batch eval; false, 12, 2, 4 |
| Postprocess | `TREE_POSTPROCESS_ENABLED` | deterministic repair before persist; default true |
| Annotation | `ANNOTATION_ENABLED` | term underline; default true |
| Wikipedia | `WIKIPEDIA_LANGUAGE`\/`WIKIPEDIA_TIMEOUT`\/`WIKIPEDIA_USER_AGENT`\/`WIKIPEDIA_RATE_LIMIT` | definition source params; en, 5s, project UA, 1.0 req\/s |
| Dictionary | `FREE_DICT_TIMEOUT` | dict API timeout, default 5 |

> **Note:** `MCP_SERVER_SCRIPT` automatically points to `mcp_server.py`; usually no manual config needed.

<a id="en-sec-9-2-structure"></a>

### 9.2 Directory Structure

```
ai-mindmap-agent\/
├── main.py                 # web backend
├── cli_pipeline.py         # CLI pipeline
├── mindmap_agent.py        # core map agent
├── config.py               # env config
├── schema.py \/ tools.py   # data structures & tools
├── mcp_server.py \/ mcp_client.py  # MCP server & client
├── index.html              # frontend
├── requirements.txt        # dependencies
├── .env \/ api.env         # config & real keys (git ignored)
├── evaluation\/             # evaluation framework
├── scripts\/                # manual helper scripts
├── tests\/                  # unit tests
├── test\/                   # experiment directory (non-core)
├── maps\/                   # saved maps (git ignored)
├── debug_output\/           # debug output (git ignored)
└── docs\/                   # docs (incl. submission instructions, old manual)
```

<a id="en-sec-9-3-version"></a>

### 9.3 Version Record

> This manual was last verified against the project on: 2026-08-30.

---

---

# Part II — Chinese Version / 第二部分 中文版

<a id="part-ii-zh"><\/a>

> Below is the complete Chinese translation of the same manual. 以下为同一手册的完整中文版。

---

## 中文目录 / Chinese Table of Contents

- [第 1 章 快速开始](#zh-sec-1-quick-start)
  - [1.1 系统是什么](#zh-sec-1-1-what-this-is)
  - [1.2 模块一句话职责](#zh-sec-1-2-modules)
  - [1.3 最小可运行示例](#zh-sec-1-3-minimal)
- [第 2 章 安装与配置](#zh-sec-2-install)
  - [2.1 环境要求](#zh-sec-2-1-requirements)
  - [2.2 安装依赖](#zh-sec-2-2-install)
  - [2.3 配置文件 `.env` 与 `api.env`](#zh-sec-2-3-config-files)
  - [2.4 校验配置](#zh-sec-2-4-verify)
- [第 3 章 Web 应用使用](#zh-sec-3-web)
  - [3.1 启动后端](#zh-sec-3-1-start)
  - [3.2 界面功能操作](#zh-sec-3-2-ui)
  - [3.3 语音流程](#zh-sec-3-3-voice)
  - [3.4 HTTP API 速查](#zh-sec-3-4-api)
- [第 4 章 命令行管线](#zh-sec-4-cli)
  - [4.1 文本模式](#zh-sec-4-1-text)
  - [4.2 音频模式](#zh-sec-4-2-audio)
  - [4.3 交互模式](#zh-sec-4-3-interactive)
  - [4.4 依赖检查](#zh-sec-4-4-check)
- [第 5 章 MCP 服务器与工具](#zh-sec-5-mcp)
  - [5.1 MCP 服务器说明](#zh-sec-5-1-about)
  - [5.2 八个工具速查](#zh-sec-5-2-tools)
  - [5.3 MCP Inspector 调试](#zh-sec-5-3-inspector)
- [第 6 章 评估框架](#zh-sec-6-evaluation)
  - [6.1 总览](#zh-sec-6-1-overview)
  - [6.2 交互式模式](#zh-sec-6-2-interactive)
  - [6.3 示例演示模式](#zh-sec-6-3-example)
  - [6.4 批量模式](#zh-sec-6-4-batch)
  - [6.5 金标准示例注入](#zh-sec-6-5-gold-inject)
  - [6.6 离线重算](#zh-sec-6-6-reuse)
  - [6.7 三元组对比报告](#zh-sec-6-7-triple)
  - [6.8 全部命令行参数](#zh-sec-6-8-params)
  - [6.9 七个评估维度](#zh-sec-6-9-dimensions)
  - [6.10 报告输出与阅读](#zh-sec-6-10-reports)
  - [6.11 数据目录约定](#zh-sec-6-11-data)
  - [6.12 依赖管理](#zh-sec-6-12-deps)
- [第 7 章 测试与维护](#zh-sec-7-test)
  - [7.1 单元测试](#zh-sec-7-1-tests)
  - [7.2 scripts/ 工具脚本](#zh-sec-7-2-scripts)
  - [7.3 test/ 实验目录](#zh-sec-7-3-testdir)
  - [7.4 维护注意事项](#zh-sec-7-4-maintenance)
- [第 8 章 常见问题与故障排查](#zh-sec-8-troubleshooting)
- [第 9 章 附录](#zh-sec-9-appendix)
  - [9.1 环境变量完整参考](#zh-sec-9-1-env)
  - [9.2 项目目录结构](#zh-sec-9-2-structure)
  - [9.3 版本记录](#zh-sec-9-3-version)

---

<a id="zh-sec-1-quick-start"></a>

## 第 1 章 快速开始

<a id="zh-sec-1-1-what-this-is"></a>

### 1.1 系统是什么

AI MindMap Agent 是一个可以逐步更新的思维导图工具。你打几个字或说几句话，它结合你手上已有的导图，通过几个模型一起配合，自动把你的内容整理成一层一层的结构，然后一直跟着更新。

用起来很直观，就是记笔记、做会议纪要、头脑风暴这种场景：你一边说或一边打字，它一边把重点理出清晰的结构；你继续说下去，导图就随着每一轮输入越长越饱满。

它另外还带一个 Web 界面（在浏览器里用）、一个不想开浏览器也能用的命令行管线，加上一套挺全的质量评估工具，专门用来看看系统生成的导图到底靠不靠谱。

<a id="zh-sec-1-2-modules"></a>

### 1.2 模块一句话职责

| 模块 | 作用 |
|---|---|
| `main.py` | Web 后端编排层，对外提供 HTTP 接口并调用内部组件 |
| `cli_pipeline.py` | 无需浏览器的命令行管线：文本/音频 → 导图 |
| `mindmap_agent.py` | 自动生成/更新导图的核心 Agent（多阶段协作） |
| `tools.py`、`schema.py` | 内部共享工具与数据结构定义（连线类型、图结构等） |
| `mcp_server.py`、`mcp_client.py` | MCP 服务端与客户端，封装聊天、转录、导图修改等能力 |
| `config.py` | 全部环境变量配置，带默认值 |
| `index.html` | 浏览器前端界面（聊天、画布、连线编辑、双语切换等） |
| `evaluation/run_evaluation.py` | 评估统一入口（交互式、批量、离线重算） |

<a id="zh-sec-1-3-minimal"></a>

### 1.3 最小可运行示例

下面这几步就搞定了「安装 → 配好密钥 → 把 Web 界面跑起来」。更细的环境要求放到第 2 章讲了。

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# 编辑 .env / api.env，填入 LLM_API_KEY（或 DEEPSEEK_API_KEY）
./venv/bin/python main.py
```

起来之后，浏览器打开 `http://localhost:8000` 就能在界面里聊天、传音频，还能看着导图实时蹦出来。

> **注意：** 首次运行会下载语音识别（Whisper，缓存在 `~/.cache/whisper/`）与词向量模型（缓存在 `.hf_cache/`），可能要花几十秒到几分钟。

---

<a id="zh-sec-2-install"></a>

## 第 2 章 安装与配置

<a id="zh-sec-2-1-requirements"></a>

### 2.1 环境要求

- **Python ≥ 3.10**：系统开发与运行环境。
- **FFmpeg（可选）**：仅当你会上传非 WAV 格式（如 mp3/m4a/ogg）的音频时必需。
- **Node.js ≥ 18（可选）**：仅当你需要开 MCP Inspector 调试界面时需要。

<a id="zh-sec-2-2-install"></a>

### 2.2 安装依赖

在项目根目录创建虚拟环境并安装依赖：

```bash
cd /home/akku/ai-mindmap-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

请始终通过项目虚拟环境运行命令（`./venv/bin/python ...`），不要使用系统 Python。

首次运行会自动下载模型：Whisper `small`（语音识别，缓存在 `~/.cache/whisper/`）和词向量模型（嵌入，缓存在 `.hf_cache/`）。若在离线环境运行，请为命令加前缀 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`。

<a id="zh-sec-2-3-config-files"></a>

### 2.3 配置文件 `.env` 与 `api.env`

项目是靠一个 OpenAI 兼容的大模型来生成导图和回复的。所有配置都走环境变量，主要有两个配置文件（都已经被 `.gitignore` 忽略了，千万别把真实密钥提交上去）。

- **`.env`**：由 `config.py` 在导入时自动加载，适合配置 `LLM_*` 变量与各类功能开关。
- **`api.env`**：存放真实密钥，由命令行管线（`cli_pipeline.py`）、评估入口以及 Web 服务（`main.py`）在运行时以「覆盖」方式加载。

密钥查找的先后次序是这样的：`LLM_*` 环境变量 → `DEEPSEEK_*` 环境变量 → 默认值（DeepSeek）。所以你只要在 `.env` 里把 `LLM_*` 那套填好，就能切到任意一个 OpenAI 兼容的厂商，改都不用改代码。

```bash
# .env 最小示例
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

> **注意：** 密钥一律以占位符 `sk-xxxx` 书写，请替换为你的真实密钥。真实密钥只存在于本地 `.env` / `api.env`，永远不要提交到 Git。

<a id="zh-sec-2-4-verify"></a>

### 2.4 校验配置

跑一下下面这条命令，就能把当前加载的 LLM 配置打印出来，顺便看看有没有缺的、或是不配套的地方（比如密钥用了 OpenAI 的，可端点还指在 DeepSeek）。

```bash
./venv/bin/python config.py
```

输出会显示当前模型名、Base URL 与密钥来源；若有警告会一并列出，请据其提示修正。

---

<a id="zh-sec-3-web"></a>

## 第 3 章 Web 应用使用

<a id="zh-sec-3-1-start"></a>

### 3.1 启动后端

启动 Web 服务：

```bash
./venv/bin/python main.py
```

服务监听 `0.0.0.0:8000`，浏览器访问 `http://localhost:8000`（根路径返回前端界面 `index.html`）。启动时系统会把内部组件（MCP 服务）自动拉起来，你什么都不用做；要是那些组件起不来，服务本身也不会启动，还会告诉你是啥原因。

这服务定位是内部工具，没做登录认证；CORS 只放行 `http://localhost:8000` 和 `http://127.0.0.1:8000` 这两个完整源（含端口），所以别直接丢到公网上去。

<a id="zh-sec-3-2-ui"></a>

### 3.2 界面功能操作

前端是个单页应用（Vue3 + G6 画布），下面说说它都能干啥、怎么上手。

**聊天（子话题对话）**

1. 在输入框输入一句话，回车或点击发送。
2. 系统返回回复文本，并在画布上自动新增/更新导图节点。
3. 若想让新内容挂到某个节点之下，先在该节点上开启「子话题对话」，再继续输入——新节点会挂到该节点下，且对话只参考该子树内容。

**音频转录**

1. 点击上传按钮选择一个音频文件（wav/mp3/m4a/ogg/flac）。
2. 系统自动（Whisper）转录并润色，结果带讲话人/时间显示在转录面板。
3. 每条转录可编辑、删除或重新下载；转录列表会作为「上下文」用于生成导图。

**画布与连线编辑**

- 拖拽节点、滚轮缩放、折叠/展开分支；选中节点可查看详细说明、删除节点、开启子话题对话。
- 点击一条连线可修改其**类型**（共 7 种）与标签，或删除该连线。

连线类型（7 种）与含义：

| 类型 | 含义 |
|---|---|
| `solid` | 直接父子关系 |
| `dashed` | 间接关联 |
| `containment` | 包含关系 |
| `dotted` | 弱关联 |
| `reference` | 引用 |
| `contrast` | 对比 |
| `causal` | 因果关系 |

**中英界面切换**

在设置面板选择界面语言（English / 中文），全部文案即时切换，画布连线类型标签跟随语言。偏好保存在浏览器 `localStorage`。

**导出 / 导入**

- 导出 PNG：将当前画布截图下载为图片。
- 导出 JSON：将当前导图下载为 `mindmap_YYYY-MM-DD.json`。
- 导入 JSON：选择一份 `{nodes, links}` 格式文件，替换画布内容。

**导图保存/加载/重命名/删除**

1. 保存：给当前导图命名并点击保存，获得一个 8 位 `map_id`。
2. 加载：输入 `map_id` 恢复对应导图。
3. 列表：查看所有已保存导图（按更新时间倒序）。
4. 重命名/删除：对指定导图改名或删除。

保存的导图以 JSON 存放在 `maps/` 目录。

**术语标注与定义**

系统能对导图里的关键术语加下划线标注，还能顺便查一下它的定义：

1. 请求标注后，关键术语会带上下划线；点击带下划线的词，弹出定义浮窗（Wikipedia 优先、LLM 兜底，附 IPA 音标）。
2. 标注密度（低/中/高）、详情层级（简/中/详）与语言可在请求时指定。

<a id="zh-sec-3-3-voice"></a>

### 3.3 语音流程

一个比较常见的「语音 → 导图」流程长这样:

1. 上传音频 → 系统转录并润色（见 3.2）。
2. 确认/编辑转录文本，必要时开启「转录作为上下文」。
3. 在聊天框交流或直接生成，让系统据此构建导图。
4. 光标在画布上查看、整理导图，必要时导出或保存。

<a id="zh-sec-3-4-api"></a>

### 3.4 HTTP API 速查

Web 界面背后的 HTTP 接口（供集成或脚本调用）。

| 方法与路径 | 作用 |
|---|---|
| `GET /` | 返回前端页面 |
| `POST /chat` | 聊天并返回更新后的导图 |
| `POST /upload_audio` | 上传音频转写 |
| `POST /annotate` | 术语标注 |
| `POST /define` | 查询术语定义 |
| `POST /save_map` | 保存导图 |
| `GET /load_map` | 按 `map_id` 加载导图 |
| `GET /list_maps` | 列出已存导图 |
| `POST /rename_map` | 重命名导图 |
| `DELETE /delete_map` | 删除导图 |

`POST /chat` 请求体格式：

```json
{"message": "补充机器学习的三类方法", "current_map": {"nodes": [], "links": []}}
```

返回包含 `answer`（回复文本）与 `map`（更新后的 `{tree, nodes, links}`）。

---

<a id="zh-sec-4-cli"></a>

## 第 4 章 命令行管线

`cli_pipeline.py` 是一个不开浏览器也能跑的命令行管线：给它文本或音频，它就直接生成导图 JSON 存到 `maps\/{map_id}.json`（日志走 stderr，结果走 stdout）。它会用「覆盖」方式自动去 `api.env` 里取真实密钥。

<a id="zh-sec-4-1-text"></a>

### 4.1 文本模式

直接传入一段文本生成导图：

```bash
./venv\/bin\/python cli_pipeline.py "机器学习的分支包括监督学习和无监督学习"
```

输出就是一条导图 JSON（写到 `maps\/` 里），里面的节点基本就是你的那些输入要点和它们的层级关系。

<a id="zh-sec-4-2-audio"></a>

### 4.2 音频模式

直接把音频文件路径和 `--audio` 一起传进去，系统会先转录、润色，再生成导图：

```bash
# 音频 → 转录 → 润色 → 导图
./venv\/bin\/python cli_pipeline.py lecture.mp3 --audio --name "课堂笔记"
# 跳过 LLM 润色，保留 Whisper 原始转录
./venv\/bin\/python cli_pipeline.py lecture.mp3 --audio --skip-polish
```

首次运行会加载 Whisper `small` 模型（大概 10–30 秒）。`--name` 用来给导图命名（默认是 `cli-mindmap`）。

<a id="zh-sec-4-3-interactive"></a>

### 4.3 交互模式

逐轮输入，导图随每一轮增量生长：

```bash
./venv\/bin\/python cli_pipeline.py -i
```

输入 `\/exit` 或按 `Ctrl+C` 退出。

<a id="zh-sec-4-4-check"></a>

### 4.4 依赖检查

只检查依赖是否齐全，不加载模型：

```bash
./venv\/bin\/python cli_pipeline.py --check-deps
```

---

<a id="zh-sec-5-mcp"></a>

## 第 5 章 MCP 服务器与工具

<a id="zh-sec-5-1-about"></a>

### 5.1 MCP 服务器说明

MCP（Model Context Protocol）服务器以子进程方式在后台跑，把聊天、转录、改导图、标注和定义这些能力都封装好，供主程序调用。**普通用户根本不用去手动启动或配置它**——系统会在后台自动把它拉起来。

<a id="zh-sec-5-2-tools"></a>

### 5.2 八个工具速查

| 工具 | 作用 | 主要参数 | 何时触发 |
|---|---|---|---|
| `chat_generate` | 生成对话回复 | `messages` 消息列表 | 聊天时 |
| `transcribe_audio` | 音频转录 | `file_path` | 上传音频时 |
| `polish_text` | 转录文本润色 | `raw_text`, `detected_language` | 转录后 |
| `modify_mind_map` | 单模型更新导图 | `chat_history`, `current_map` | 生成/更新导图 |
| `modify_mind_map_v2` | 多阶段协作更新导图 | `chat_history`, `current_map` | 生成/更新导图（默认走此） |
| `annotate_terms` | 术语标注 | `current_map`, `density_mode`, `detail_level` | 请求标注时 |
| `get_definition` | 术语定义 | `term`, `detail_level`, `language` | 点击术语时 |
| `lookup_dictionary` | 词典查询（IPA+字面义） | `term` | 定义兜底时 |

> **注意：** `modify_mind_map_v2` 是多阶段协作版本（系统默认使用），`modify_mind_map` 为单模型版本；当未配置分阶段专用模型时两者行为一致。

<a id="zh-sec-5-3-inspector"></a>

### 5.3 MCP Inspector 调试

如果你想用一种交互、可视化的方式看看所有工具调用，可以跑一下 MCP Inspector：

```bash
bash scripts\/inspect.sh
```

然后在浏览器打开 `http:\/\/localhost:6274` 即可用 JSON-RPC 界面调试（需要 Node.js ≥ 18）。

---

<a id="zh-sec-6-evaluation"></a>

## 第 6 章 评估框架

评估框架就是用来看看系统生成的导图到底有多好的。所有入口都统一到 `evaluation\/run_evaluation.py`，它提供好几套评估方法、好几种运行模式。**记住，所有评估命令都要用项目的虚拟环境跑**。

<a id="zh-sec-6-1-overview"></a>

### 6.1 总览

运行入口支持五条路径：示例演示、交互式（默认）、批量、离线重算，以及三元组报告。

真实密钥放在 `api.env`：命令行管线、评估入口和 Web 服务（`main.py`）在运行时都会去加载它；`.env` 则在模块导入时加载（如 HF 端点等）。

<a id="zh-sec-6-2-interactive"></a>

### 6.2 交互式模式

交互式模式（默认那个）会用一个向导菜单一步步带你走完整个评估，适合拿来搞一条或几条音频：

```bash
./venv\/bin\/python evaluation\/run_evaluation.py
```

操作步骤：

1. 选择界面语言（或直接传 `--lang zh` \/ `--lang en`）。
2. 在方法菜单中选择要评估的维度（也能选择 §0 示例演示模式，见 6.3）。
3. 选择文件方式：模式 A 自动检测 `evaluation\/data\/` 下同名配对，或模式 B 手动输入文件路径。
4. 逐条音频完成转录、生成、评估，最终生成 Markdown 报告。

<a id="zh-sec-6-3-example"></a>

### 6.3 示例演示模式

这是藏在评估菜单里的 **§0 示例演示模式**：拿**内置的示例数据**把整套评估流程跑一遍，让你快速知道这框架是干嘛的、输出长啥样，**一个输入文件都不用准备**。

1. 交互模式菜单中选择 §0。
2. 系统用内置的金标准导图、概念集、问题集等数据，自动执行六维评估。
3. 生成带 `**example**` 标记的报告。

> **注意：** 示例演示与正式评估**互斥**——混选时系统会提示并剔除。它并不会真正调用评测你的数据。

<a id="zh-sec-6-4-batch"></a>

### 6.4 批量模式

把目录下所有音频，一个一个对着金标准批量评估：

```bash
./venv\/bin\/python evaluation\/run_evaluation.py --batch \\
  --audio-dir evaluation\/data\/audio --gold-dir evaluation\/data\/gold \\
  --methods label hierarchy efficiency
```

约定：

- 音频文件放在 `--audio-dir`（默认 `evaluation\/data\/audio`），金标准放在 `--gold-dir`（默认 `evaluation\/data\/gold`）。
- 系统按「同名」自动配对音频与对应金标准。
- `--methods` 指定方法；未指定时默认 `label hierarchy efficiency`。

> **注意：** `full` 仅在**交互式**菜单会自动展开为全部方法；**批量模式下不会**展开，需要你显式列出方法名（如 `--methods label hierarchy qa efficiency multilingual human_corr`）。

<a id="zh-sec-6-5-gold-inject"></a>

### 6.5 金标准示例注入

批量模式下可以传一个「金标准示例对」进去，让模型**照着示例的结构风格来生成导图**（few-shot 引导），不过它本身不是一个评估模式：

```bash
./venv\/bin\/python evaluation\/run_evaluation.py --batch --audio-dir ... --gold-dir ... \\
  --gold-example-transcript example.txt --gold-example-json example.json
```

`--gold-example-transcript` 与 `--gold-example-json` **必须同时提供**：前者为一份转录文本，后者为对应的金标准导图 JSON，两者共同构成一个风格参考示例。

> **注意：** 这与 6.3 的示例演示模式是**两种不同机制**——6.3 用内置数据演示评估框架；这里是用你自己提供的示例引导模型生成，二者不要混淆。

<a id="zh-sec-6-6-reuse"></a>

### 6.6 离线重算

直接去读一套之前保存的评估会话，**把转录和生成都跳过**，只管用会话里已有的导图和金标准来重算指标——评估那边改完 bug 之后，这招用来做零成本的回归再合适不过：

```bash
./venv\/bin\/python evaluation\/run_evaluation.py \\
  --reuse-sessions 20260804_092828 --methods label hierarchy --prefer-gold GTC
```

- `--reuse-sessions <时间戳>`：指定会话目录（如 `20260804_092828`）。
- `--methods` 未指定时默认 `label hierarchy`。
- `--prefer-gold GTC`：金标准存在多个基准子目录（GTC\/YQL）时优先使用哪一个。
- `--postprocess`：重算时对会话中存储的导图应用树形结构后处理。

<a id="zh-sec-6-7-triple"></a>

### 6.7 三元组对比报告

生成一份「STT 转录 \/ Agent 生成树 \/ 人类标注树」三者的对比报告：

```bash
./venv\/bin\/python evaluation\/run_evaluation.py --triple-report \\
  --audio-dir evaluation\/data\/audio --gold-dir evaluation\/data\/gold
```

输出是一份中文命名的三元组对比报告（放在 `evaluation\/` 根目录下）。

<a id="zh-sec-6-8-params"></a>

### 6.8 全部命令行参数

| 参数 | 含义 | 默认值 |
|---|---|---|
| `--lang {zh,en}` | 界面语言 | 交互模式省略时启动询问 |
| `--batch` | 批量评估模式 | 关 |
| `--audio-dir` | 批量模式音频目录 | `evaluation\/data\/audio` |
| `--gold-dir` | 批量模式金标准目录 | `evaluation\/data\/gold` |
| `--methods` | 空格分隔方法列表 | 批量 `label hierarchy efficiency`\/重算 `label hierarchy` |
| `--repeat N` | 每配对独立运行次数取平均 | **5** \/ 传 `--repeat 1` 只跑一次 |
| `--reuse-sessions <ts>` | 离线重算指定会话 | 无 |
| `--model-name` | 语义对齐嵌入模型 | `paraphrase-multilingual-MiniLM-L12-v2` |
| `--threshold` | 语义相似度阈值 τ | 0.70 |
| `--prefer-gold` | 首选金标准基准子目录（GTC\/YQL） | 自动：root → GTC → YQL |
| `--postprocess` | 重算时应用树形后处理 | 关 |
| `--triple-report` | 生成三元组对比报告 | 关 |
| `--auto-install` | 自动 pip 安装缺失依赖 | 关 |
| `--ignore-missing-deps` | 忽略缺失依赖继续 | 关 |
| `--gold-example-transcript` | 金标准示例转录文本 | 无 |
| `--gold-example-json` | 金标准示例导图 JSON | 无 |

<a id="zh-sec-6-9-dimensions"></a>

### 6.9 七个评估维度

| 方法 | 必需输入 | 核心指标 | 触发 |
|---|---|---|---|
| `label` — 节点标签 | gold, audio, concepts | Node-F1、LabelSim、Entity-Recall | 菜单选择 \/ `--methods` |
| `hierarchy` — 层级结构 | gold, audio | Edge-F1\/P\/R、UAS、PC-F1、LAR、nTED | 菜单选择 \/ `--methods` |
| `qa` — 下游问答 | audio | QA 得分（自动 20 题，每题 1–5） | 菜单选择 \/ `--methods` |
| `efficiency` — 效率与转写 | audio, timing, transcript, key_terms | WER、token 缩减等 | 菜单选择 \/ `--methods` |
| `multilingual` — 多语言 | audio, multilingual_results | cn\/en\/mixed + 噪声的 Max Δ Recall | 菜单选择 \/ `--methods` |
| `human_corr` — 人工对齐 | audio | 交互 0–10 评分；ICC(3,k)、Kendall's W、overall_normalized | 菜单选择 \/ `--methods` |
| `full` — 全量报告 | 以上全部 | 全部方法 + 综合评分 | 交互菜单选择（自动展开） |

说明：

- 语义对齐采用多语言嵌入的匈牙利匹配；默认阈值 τ=0.7。
- 人工评分用作层级指标误判的补偿，计入综合评分。
- 综合评分成分权重：node_f1 0.20、edge_f1 0.08、label_sim 0.10、entity_recall 0.10、nted_inv 0.08、uas 0.07、pc_f1 0.07、qa_score 0.10、human_score 0.20；缺失维度被排除后剩余权重重新归一化。解读：≥0.85 优秀、≥0.70 良好、<0.70 需改进。

<a id="zh-sec-6-10-reports"></a>

### 6.10 报告输出与阅读

每对一个配对就会生成一份 Markdown 报告，而且会**同时存到两个地方**：

1. `evaluation\/data\/sessions\/{时间戳}\/{配对名}\/eval_report.md`（同时保存会话全部中间 JSON）
2. `evaluation\/eval_report_{配对名}_{时间戳}.md`（`evaluation\/` 根目录）

报告结构：

- **摘要表**：每个维度一行（核心指标、评级、PASS\/FAIL），综合评分行在最上方。
- **分维度章节**：各维度指标表带阈值与评级。
- **详情块**：匈牙利匹配明细、实体召回遗漏、边 TP\/FP\/FN 明细。
- **综合评分章节**：各成分值\/权重\/加权分。
- **诊断建议章节**：针对不达标指标自动给出改进建议。

关键的指标阈值在这里（帮你看懂报告里的评级是怎么打出来的）：

- 层级：Edge-F1 ≥ 0.80、UAS ≥ 0.85、PC-F1 ≥ 0.75、LAR ≥ 0.70、nTED ≤ 0.25。
- 标签：Node-F1 ≥ 0.85、LabelSim ≥ 0.85、Entity-Recall ≥ 0.90。

<a id="zh-sec-6-11-data"></a>

### 6.11 数据目录约定

评估相关的输入数据都在 `evaluation\/data\/` 下面：

| 目录 | 内容 |
|---|---|
| `audio\/` | 待评估音频 |
| `gold\/` | 金标准导图（可含 `GTC\/`、`YQL\/` 子基准） |
| `concepts\/` | 核心概念集 |
| `questions\/` | 问答问题集 |
| `timing\/` | 计时日志与关键术语 |
| `multilingual\/` | 多语言测试结果 |
| `human_scores\/` | 人工评分数据 |
| `sessions\/` | 已保存会话（供 `--reuse-sessions`） |
| `standards\/` | 标注标准 |

<a id="zh-sec-6-12-deps"></a>

### 6.12 依赖管理

每种评估方法都要用到不同的第三方包。跑之前系统会先检查一下；要是缺了：

- 加 `--auto-install` 让系统用 pip 自动安装缺失依赖；
- 或加 `--ignore-missing-deps` 忽略缺失的依赖、对能跑的部分继续执行。

各方法依赖概览：`label`→numpy、sentence-transformers；`hierarchy`→numpy、zss、sentence-transformers；`qa`→openai；`efficiency`→jiwer、jieba、scipy；`human_corr`→scipy；`full`→zss、jiwer、jieba、scipy、sentence-transformers、openai（另外也需要 numpy，它单独列出）。

> **注意：** 离线运行嵌入模型需要本地缓存；请在命令前加前缀 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`。

---

<a id="zh-sec-7-test"></a>

## 第 7 章 测试与维护

<a id="zh-sec-7-1-tests"></a>

### 7.1 单元测试

单元测试放在 `tests\/` 目录（一共 6 个文件）。记得在项目根目录用 venv 里的 Python 跑：

```bash
./venv\/bin\/python tests\/test_core.py
./venv\/bin\/python tests\/test_api.py              # 需可达的 API 密钥
./venv\/bin\/python tests\/test_eval_fixes.py
./venv\/bin\/python tests\/test_eval_hierarchy.py
./venv\/bin\/python tests\/test_link_type.py
./venv\/bin\/python tests\/test_compat_provider.py
```

`test_core.py` 与 `test_eval_hierarchy.py` 同时是 `unittest` 套件，也可用下面命令运行；全部文件可用 `pytest` 运行：

```bash
./venv\/bin\/python -m unittest tests.test_core tests.test_eval_hierarchy
pytest tests\/
```

各文件验证内容：

- `test_core.py`：核心管线纯函数（导图合并、树展平往返、深度统计、JSON 解析）。
- `test_api.py`：OpenAI 兼容 API 连通性。
- `test_eval_fixes.py`：评估回归（ICC、Kendall's W、token 缩减等）。
- `test_eval_hierarchy.py`：层级指标回归（Edge\/UAS、空值、nTED、PC-F1、阈值、多轮平均）。
- `test_link_type.py`：连线类型在树往返中不丢失。
- `test_compat_provider.py`：多提供商配置兼容性。

<a id="zh-sec-7-2-scripts"></a>

### 7.2 scripts/ 工具脚本

`scripts\/` 目录里的脚本都是**手动去跑**的，没有一个会自动挂进启动流程：

| 脚本 | 用途 | 示例 |
|---|---|---|
| `cleanup_debug.py` | 清理 `debug_output\/` 中早期会话目录 | `./venv\/bin\/python scripts\/cleanup_debug.py --days 30 --dry-run` |
| `audit_edge_zero.py` | 排查边指标归零根因（临时审计） | `./venv\/bin\/python scripts\/audit_edge_zero.py` |
| `audit_postprocess.py` | 验证树形后处理收益 | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv\/bin\/python scripts\/audit_postprocess.py [ts ...]` |
| `select_best_example.py` | 优质示例筛选 | `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv\/bin\/python scripts\/select_best_example.py` |
| `inspect.sh` | 一键启动 MCP Inspector（见 5.3） | `bash scripts\/inspect.sh` |

<a id="zh-sec-7-3-testdir"></a>

### 7.3 test/ 实验目录

`test\/`（小写）是个**实验目录**，不是单元测试，也不算核心功能；它只用来复现论文里的那些实验，具体可以看 `test\/REPORT.md`。

- `run_experiment.py`：导图路 vs 全文路的双路问答对比实验。
- `llm_server.py`：本地 OpenAI 兼容 LLM 推理服务（如 `--port 8765`）。
- `fetch_texts.py`：实验语料提取。

<a id="zh-sec-7-4-maintenance"></a>

### 7.4 维护注意事项

- `debug_output\/` 会持续积累每次运行的中间产物，用 `scripts\/cleanup_debug.py` 定期清理（它不会自动运行）。
- `evaluation\/data\/sessions\/` 下的会话目录可作为 `--reuse-sessions` 离线重算输入；若计划回归，请保留它们。
- `maps\/` 存放 Web 与 CLI 保存的导图，`.gitignore` 已排除出版本控制。
- 运行产出的报告、调试文件、模型缓存都不会被 git 跟踪，无需手动删除（除非空间紧张）。

---

<a id="zh-sec-8-troubleshooting"></a>

## 第 8 章 常见问题与故障排查

| 问题 | 可能原因与解决办法 |
|---|---|
| LLM 功能不可用 | 未设置密钥；在 `.env` 填 `LLM_API_KEY`（或 `DEEPSEEK_API_KEY`），见 2.3 |
| 请求报 401 / 端点混用 | 密钥与端点来源不一致（如 OpenAI 密钥配 DeepSeek 默认端点）；运行 `./venv\/bin\/python config.py` 看警告并修正 `LLM_BASE_URL`\/`LLM_MODEL` |
| Whisper 模型下载慢或失败 | 网络受限；用离线缓存或加 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` |
| 提示缺失依赖 | 用 `--auto-install` 自动安装，或 `--ignore-missing-deps` 忽略。注意 numpy 已在 requirements.txt 中显式声明 |
| 端口 8000 被占用 | 关闭占用进程或改端口 |
| 非 WAV 音频无法转录 | 需要安装 FFmpeg，见 2.1 |
| `human_corr` 无法运行 | 该维度需要人工评分；交互模式逐条评分，批量模式读取已保存问卷 |

---

<a id="zh-sec-9-appendix"></a>

## 第 9 章 附录

<a id="zh-sec-9-1-env"></a>

### 9.1 环境变量完整参考

下面这份手册里会提到的环境变量分组基本都在这了（全部可选，没配的时候会有默认值或自动回退）。最全的以 `config.py` 为准。

| 分组 | 变量 | 说明 |
|---|---|---|
| 通用 LLM | `LLM_API_KEY`\/`LLM_BASE_URL`\/`LLM_MODEL` | 主力模型三件套；回退 `LLM_*` → `DEEPSEEK_*` → 默认 DeepSeek |
| 通用 LLM | `API_TIMEOUT` | 请求超时（秒），默认 30 |
| 通用 LLM | `LLM_MAX_TOKENS` | 最大输出 token，默认 8192 |
| 通用 LLM | `LLM_JSON_FALLBACK` | 是否启用纯文本 JSON 降级，默认 true |
| 润色 | `POLISH_MODEL`\/`POLISH_BASE_URL`\/`POLISH_API_KEY`\/`POLISH_ITERATIONS` | 转录润色；未配时用主力模型直润 |
| 阶段 1 | `CONCEPT_MODEL`\/`CONCEPT_BASE_URL`\/`CONCEPT_API_KEY` | 概念提取专用模型 |
| 阶段 2 | `HIERARCHY_MODEL`\/`HIERARCHY_BASE_URL`\/`HIERARCHY_API_KEY` | 层级规划模型；设 `HIERARCHY_MODEL=""` 或 `HIERARCHY_SKIP=true` 切两阶段 |
| 阶段 3 | `DELTA_MODEL`\/`DELTA_BASE_URL`\/`DELTA_API_KEY` | Delta 生成模型，默认复用主力 |
| 轻量 LLM | `LLM_LIGHT_MODEL`\/`LLM_LIGHT_BASE_URL`\/`LLM_LIGHT_API_KEY`\/`LLM_LIGHT_ENABLED` | 低成本批量任务（定义兜底、词典） |
| 调试 | `DEBUG_OUTPUT_ENABLED`\/`DEBUG_OUTPUT_DIR` | 是否/往哪里写每阶段中间结果；默认 true、`debug_output\/` |
| Details 增强 | `DETAILS_ENRICHMENT_ENABLED` | 是否把 AI 回复定义追加入节点 details；默认 true |
| 深度优先 | `DEPTH_FIRST_ENABLED`\/`MIN_TREE_DEPTH`\/`MAX_SIBLINGS_PER_NODE` | 深挖子节点偏好；默认 true、3、6 |
| 评估对齐 | `EVAL_STRUCTURE_ALIGN`\/`MAX_CONCEPTS`\/`EVAL_TARGET_DEPTH`\/`EVAL_MAX_SIBLINGS` | 批量评估的紧凑层级；默认 false、12、2、4 |
| 后处理 | `TREE_POSTPROCESS_ENABLED` | 落库前确定性结构修复；默认 true |
| 标注 | `ANNOTATION_ENABLED` | 术语下划线标注；默认 true |
| Wikipedia | `WIKIPEDIA_LANGUAGE`\/`WIKIPEDIA_TIMEOUT`\/`WIKIPEDIA_USER_AGENT`\/`WIKIPEDIA_RATE_LIMIT` | 定义来源参数；默认 en、5s、项目 UA、1.0 req\/s |
| 词典 | `FREE_DICT_TIMEOUT` | 词典 API 超时；默认 5 |

> **注意：** `MCP_SERVER_SCRIPT` 由系统自动指向 `mcp_server.py`，通常无需手动配置。

<a id="zh-sec-9-2-structure"></a>

### 9.2 项目目录结构

```
ai-mindmap-agent\/
├── main.py                 # Web 后端
├── cli_pipeline.py         # 命令行管线
├── mindmap_agent.py        # 导图生成核心
├── config.py               # 环境变量配置
├── schema.py / tools.py    # 数据结构与工具
├── mcp_server.py / mcp_client.py  # MCP 服务端与客户端
├── index.html              # 前端界面
├── requirements.txt        # 依赖
├── .env / api.env          # 配置与真实密钥（git ignored）
├── evaluation\/             # 评估框架
├── scripts\/                # 手动工具脚本
├── tests\/                  # 单元测试
├── test\/                   # 实验目录（非核心）
├── maps\/                   # 保存的导图（git ignored）
├── debug_output\/           # 调试输出（git ignored）
└── docs\/                   # 文档（含提交说明、旧版手册）
```

<a id="zh-sec-9-3-version"></a>

### 9.3 版本记录

> 最后核对该手册内容所对应的项目版本：2026-08-30。

---

（完 / End）

