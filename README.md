# 🧠 AI MindMap Agent

> **Real-time conversational mind mapping powered by multi-model AI collaboration.**

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## 🇬🇧 English

### 📖 Overview

**AI MindMap Agent** is an intelligent, voice-integrated mind mapping system that converts spoken or typed conversations into structured, hierarchical mind maps in real time. It combines **speech-to-text (Whisper)**, **multi-model LLM collaboration**, and an interactive **Vue.js canvas** to produce incrementally updated concept maps.

Whether you're in a lecture, brainstorming session, or meeting — simply speak or type, and the system will:

1. **Transcribe** your audio (Whisper STT)  
2. **Polish** the transcript with a hybrid review pipeline  
3. **Extract** core concepts via a lightweight LLM  
4. **Plan** hierarchical relationships via a medium-weight LLM  
5. **Generate** incremental delta updates to the visual mind map via a main LLM  

All orchestrated through the **Model Context Protocol (MCP)**, ensuring clean separation of concerns between the FastAPI orchestrator and the LLM toolchain.

---

### ✨ Core Features

| Feature | Description |
|---|---|
| 🎙️ **Voice-to-Map** | Record or upload audio → Whisper STT → transcript polishing → mind map generation |
| 🧩 **3-Stage Pipeline** | Concept Extraction → Hierarchy Planning → Delta Generation (each stage uses independently configurable models) |
| 🔄 **Incremental Updates** | Never rebuilds the entire map; only applies deltas (add / update / delete nodes & links) |
| 🤖 **Multi-Model Collaboration** | Each pipeline stage can use a different LLM (cloud, local Ollama, or any OpenAI-compatible API) |
| 📝 **Text Polishing (Hybrid Review)** | Lightweight model iteratively polishes transcripts → main model gives final ACCEPT / FIX / REJECT verdict |
| 🌐 **Vue.js Interactive Canvas** | Drag-to-pan, node drag, collapsible detail panels, real-time SVG links |
| 🔌 **MCP Protocol** | All LLM & tool interactions via MCP stdio, keeping the orchestrator pure and testable |
| 🗣️ **Multilingual** | Auto-detects input language (中文 / English / Deutsch / Français / 日本語 / Español …) and replies in the same language |
| 🐛 **Debug Output Pipeline** | Optional per-stage debug file saving for transparency and troubleshooting |

---

### 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Browser (Vue.js)                   │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐  │
│  │  Chat   │  │Transcript│  │   Mind Map Canvas    │  │
│  │   UI    │  │  Panel   │  │  (SVG + drag-to-pan) │  │
│  └────┬────┘  └────┬─────┘  └──────────┬──────────┘  │
└───────┼────────────┼───────────────────┼─────────────┘
        │            │                   │
   POST /chat   POST /upload_audio    GET /
        │            │                   │
┌───────┴────────────┴───────────────────┴─────────────┐
│               FastAPI Orchestrator (main.py)           │
│  - Pure orchestrator, NO LLM calls                     │
│  - Validation + retry for every MCP call               │
│  - Session memory management                           │
│  - Debug map output                                    │
└──────────────────────┬────────────────────────────────┘
                       │ MCP stdio
┌──────────────────────┴────────────────────────────────┐
│              MCP Client (mcp_client.py)                │
│  - Spawns MCP Server as subprocess                     │
│  - Unified call_tool() interface                       │
└──────────────────────┬────────────────────────────────┘
                       │ stdio
┌──────────────────────┴────────────────────────────────┐
│              MCP Server (mcp_server.py)                │
│                                                        │
│  Tools exposed:                                        │
│  ┌──────────────────────────────────────────────┐     │
│  │ chat_generate     → LLM conversational reply │     │
│  │ transcribe_audio  → Whisper STT              │     │
│  │ polish_text       → Hybrid review polishing  │     │
│  │ modify_mind_map   → Single-model ReAct draw  │     │
│  │ modify_mind_map_v2→ 3-stage pipeline draw    │     │
│  └──────────────────────────────────────────────┘     │
└──────────────────────┬────────────────────────────────┘
                       │
┌──────────────────────┴────────────────────────────────┐
│         MindMap Pipeline (mindmap_agent.py)            │
│                                                        │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │ Stage 1     │   │ Stage 2      │   │ Stage 3    │  │
│  │ Concept     │──▶│ Hierarchy    │──▶│ Delta      │  │
│  │ Extraction  │   │ Planning     │   │ Generation │  │
│  │ (lightweight)│  │ (medium)     │   │ (main LLM) │  │
│  └─────────────┘   └──────────────┘   └────────────┘  │
│                                                        │
│  Graceful degradation:                                 │
│  Stage 1 fail → single-model ReAct fallback            │
│  Stage 2 fail → skip hierarchy, continue to Stage 3    │
│  Stage 3 fail → return original map                    │
└────────────────────────────────────────────────────────┘
```

#### Degradation Chain

```
CONCEPT_MODEL not set?
  └─ All 3 stages use LLM_MODEL (single-model ReAct behavior)

Stage 1 fails or returns 0 concepts?
  └─ Delegate to legacy MindMapSpecialistAgent (single-model ReAct)

Stage 2 fails?
  └─ Skip hierarchy; Stage 3 receives only concept hints

Stage 3 fails?
  └─ Return map unchanged
```

---

### 🚀 Quick Start

#### Prerequisites

- **Python** ≥ 3.10
- **pip** (or uv/poetry)
- An **OpenAI-compatible API key** (DeepSeek, OpenAI, local Ollama, etc.)
- (Optional) **FFmpeg** — if you plan to upload audio files in non-WAV formats

#### 1. Clone & Install

```bash
git clone https://github.com/your-username/ai-mindmap-agent.git
cd ai-mindmap-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

> **Note:** On first startup, Whisper will download the `small` model (~500 MB). Ensure you have sufficient disk space.

#### 2. Configure Environment

Copy the example configuration and fill in your API key:

```bash
cp api.env .env
```

Edit `.env`:

```env
# --- Generic LLM (recommended) ---
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# --- (Optional) Per-stage model overrides ---
# CONCEPT_MODEL=deepseek-lite
# HIERARCHY_MODEL=deepseek-lite
# DELTA_MODEL=deepseek-chat

# --- (Optional) Polish model ---
# POLISH_MODEL=deepseek-v4-flash
# POLISH_ITERATIONS=3
```

<details>
<summary>💡 Using local Ollama models (click to expand)</summary>

```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3

# Optional: use lighter models for early stages
CONCEPT_MODEL=qwen2.5:1.5b
HIERARCHY_MODEL=qwen2.5:3b
DELTA_MODEL=llama3
POLISH_MODEL=qwen2.5:0.5b
```

</details>

<details>
<summary>💡 Using OpenAI (click to expand)</summary>

```env
LLM_API_KEY=sk-your-openai-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

</details>

#### 3. Test the Connection

```bash
python test_api.py
```

Expected output:
```
✅ API connection successful!
  Model:  deepseek-chat
  URL:    https://api.deepseek.com
```

#### 4. Start the Server

```bash
python main.py
```

Open your browser at **http://localhost:8000**.

---

### ⚙️ Configuration Reference

All settings are managed through environment variables in `.env`.

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | *(required)* | API key for the main LLM |
| `LLM_BASE_URL` | `https://api.deepseek.com` | Base URL for OpenAI-compatible API |
| `LLM_MODEL` | `deepseek-chat` | Main model name |
| `CONCEPT_MODEL` | *(falls back to LLM_MODEL)* | Stage 1 — concept extraction model |
| `CONCEPT_BASE_URL` | *(falls back to LLM_BASE_URL)* | Stage 1 API endpoint |
| `CONCEPT_API_KEY` | *(falls back to LLM_API_KEY)* | Stage 1 API key |
| `HIERARCHY_MODEL` | *(falls back to LLM_MODEL)* | Stage 2 — hierarchy planning model |
| `HIERARCHY_BASE_URL` | *(falls back to LLM_BASE_URL)* | Stage 2 API endpoint |
| `HIERARCHY_API_KEY` | *(falls back to LLM_API_KEY)* | Stage 2 API key |
| `DELTA_MODEL` | *(falls back to LLM_MODEL)* | Stage 3 — delta generation model |
| `DELTA_BASE_URL` | *(falls back to LLM_BASE_URL)* | Stage 3 API endpoint |
| `DELTA_API_KEY` | *(falls back to LLM_API_KEY)* | Stage 3 API key |
| `POLISH_MODEL` | *(None = use LLM_MODEL)* | Lightweight model for transcript polishing |
| `POLISH_BASE_URL` | *(falls back to LLM_BASE_URL)* | Polish API endpoint |
| `POLISH_API_KEY` | *(falls back to LLM_API_KEY)* | Polish API key |
| `POLISH_ITERATIONS` | `3` | Max lightweight self-iterations (1–5) |
| `API_TIMEOUT` | `30` | API request timeout (seconds) |
| `DEBUG_OUTPUT_ENABLED` | `true` | Save per-stage debug files |
| `DEBUG_OUTPUT_DIR` | `./debug_output` | Debug output directory |
| `DETAILS_ENRICHMENT_ENABLED` | `true` | Enrich node details from AI replies |

---

### 📡 API Reference

#### `GET /`

Serves the Vue.js frontend application.

---

#### `POST /chat`

Main conversation and mind map generation endpoint.

**Request Body:**

```json
{
  "message": "Tell me about machine learning",
  "current_map": {
    "nodes": [],
    "links": []
  },
  "transcript_context": "(optional) previously transcribed audio text"
}
```

**Response:**

```json
{
  "answer": "Machine learning is a subset of artificial intelligence...",
  "map": {
    "nodes": [
      {
        "id": "node_ml",
        "label": "Machine Learning",
        "color": "var(--node-blue)",
        "details": ["💡 Definition: A subset of AI..."],
        "x": 400,
        "y": 200
      }
    ],
    "links": [
      { "source": "node_ml", "target": "node_supervised", "type": "solid" }
    ]
  }
}
```

---

#### `POST /upload_audio`

Upload audio for speech-to-text transcription and polishing.  
Accepts `multipart/form-data` with field name `file`.

**Response:**

```json
{
  "status": "success",
  "raw_text": "um machine learning is kind of like teaching computers",
  "polished_text": "Machine learning is like teaching computers to learn from data.",
  "detected_language": "en"
}
```

---

### 🖥️ Frontend Interface

The frontend is a single-file Vue.js 3 application (`index.html`) featuring:

| Component | Description |
|---|---|
| **Audio Player** | Play uploaded/recorded audio with real-time waveform visualization |
| **Chat Panel** | Type or view AI conversation; supports Markdown rendering |
| **Transcript Panel** | View, edit, search, and filter transcribed audio segments |
| **Mind Map Canvas** | SVG-based draggable canvas with auto-layout and collision avoidance |
| **Node Detail Panel** | Click any node to view its hierarchical details |
| **Settings Modal** | Language (English/中文), font family, interface scale, sync toggle |

---

### 🧪 Evaluation Framework

See [`Evaluation_Schema.md`](./Evaluation_Schema.md) for the complete evaluation methodology, which covers:

1. **Hierarchical Accuracy** — alignment with ground-truth lecture outlines (Tree Edit Distance)
2. **Entity Recall** — how many "must-know" concepts are captured in the generated map
3. **Downstream QA Utility** — answering quiz questions using only the mind map vs. full transcript (cost & accuracy comparison)
4. **End-to-End Generation Time** — total latency from audio upload to final map output
5. **Transcription Content Retention** — STT fidelity for key academic concepts

---

### 📂 Project Structure

```
ai-mindmap-agent/
├── main.py                 # FastAPI orchestrator (pure, no LLM calls)
├── mcp_server.py           # MCP Server (5 tools for LLM, Whisper, polish, drawing)
├── mcp_client.py           # MCP Client wrapper (stdio lifecycle management)
├── mindmap_agent.py        # Core: 3-stage pipeline + ReAct agents + debug manager
├── config.py               # Configuration class (all env vars)
├── tools.py                # Function-calling JSON schemas for all agent stages
├── schema.py               # Pydantic models (Node, Link, MindMapData)
├── agent.py                # Legacy single-model agent (deprecated, kept for reference)
├── test_api.py             # Quick API connection test
├── index.html              # Vue.js 3 + Tailwind CSS frontend
├── requirements.txt        # Python dependencies
├── .env.example            # (create your own .env from this template)
├── Evaluation_Schema.md    # Quality evaluation criteria (bilingual)
└── debug_output/           # Per-request debug files (auto-generated)
```

---

### 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

### 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

### 🙏 Acknowledgements

- [OpenAI Whisper](https://github.com/openai/whisper) — speech recognition
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [Vue.js](https://vuejs.org/) — frontend framework
- [Tailwind CSS](https://tailwindcss.com/) — utility-first CSS
- [Anthropic MCP](https://modelcontextprotocol.io/) — Model Context Protocol

---

<a name="中文"></a>
## 🇨🇳 中文

### 📖 项目简介

**AI MindMap Agent** 是一个集成语音转文字与多模型协作的智能思维导图系统，能够将语音或文本对话实时转化为结构化的层级思维导图。系统融合了 **Whisper 语音识别**、**多模型 LLM 协作管线**以及 **Vue.js 交互式画布**，实现思维的即时可视化。

无论你是在上课、头脑风暴还是开会——只需说话或打字，系统便会：

1. **转写** 音频（Whisper STT）  
2. **润色** 转录文本（混合审查模式）  
3. **提取** 核心概念（轻量级 LLM）  
4. **规划** 层级关系（中等权重 LLM）  
5. **生成** 增量 Delta 更新到可视画布（主力 LLM）  

全程通过 **MCP 协议（Model Context Protocol）** 进行编排，确保 FastAPI 编排器与 LLM 工具链之间的清晰解耦。

---

### ✨ 核心功能

| 功能 | 说明 |
|---|---|
| 🎙️ **语音转导图** | 录音或上传音频 → Whisper STT → 转录润色 → 思维导图生成 |
| 🧩 **三阶段管线** | 概念提取 → 层级规划 → Delta 生成（每阶段可独立配置模型） |
| 🔄 **增量更新** | 绝不重建整张导图，仅应用 Delta（新增/修改/删除节点与连线） |
| 🤖 **多模型协作** | 每阶段可用不同 LLM（云端、本地 Ollama 或任何兼容 OpenAI 的 API） |
| 📝 **混合审查润色** | 轻量模型迭代润色 → 主力模型终审裁决（ACCEPT / FIX / REJECT） |
| 🌐 **Vue.js 交互画布** | 拖拽平移、节点拖拽、可折叠详情面板、实时 SVG 连线 |
| 🔌 **MCP 协议** | 所有 LLM 与工具交互通过 MCP stdio，编排器保持纯净可测 |
| 🗣️ **多语言支持** | 自动检测输入语言（中文 / English / Deutsch / Français / 日本語 …）并以相同语言回复 |
| 🐛 **调试输出管线** | 可选逐阶段保存调试文件，便于排错与分析 |

---

### 🏗️ 技术架构

```
┌──────────────────────────────────────────────────────┐
│                    浏览器 (Vue.js)                     │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐  │
│  │ 聊天界面 │  │ 转录面板 │  │   思维导图画布       │  │
│  │   UI    │  │  Panel   │  │ (SVG + 拖拽平移)    │  │
│  └────┬────┘  └────┬─────┘  └──────────┬──────────┘  │
└───────┼────────────┼───────────────────┼─────────────┘
        │            │                   │
   POST /chat   POST /upload_audio    GET /
        │            │                   │
┌───────┴────────────┴───────────────────┴─────────────┐
│              FastAPI 编排器 (main.py)                  │
│  - 纯编排器，不包含任何 LLM 调用                        │
│  - 每次 MCP 调用含验证 + 重试                          │
│  - 会话记忆管理                                        │
│  - 调试导图输出                                        │
└──────────────────────┬────────────────────────────────┘
                       │ MCP stdio
┌──────────────────────┴────────────────────────────────┐
│              MCP Client (mcp_client.py)                │
└──────────────────────┬────────────────────────────────┘
                       │ stdio
┌──────────────────────┴────────────────────────────────┐
│              MCP Server (mcp_server.py)                │
│  提供工具: chat_generate / transcribe_audio            │
│           polish_text / modify_mind_map                │
│           modify_mind_map_v2                           │
└──────────────────────┬────────────────────────────────┘
                       │
┌──────────────────────┴────────────────────────────────┐
│          导图管线 (mindmap_agent.py)                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│  │ 阶段1    │   │ 阶段2    │   │ 阶段3    │          │
│  │ 概念提取 │──▶│ 层级规划 │──▶│ Delta生成│          │
│  │ (轻量)   │   │ (中等)   │   │ (主力)   │          │
│  └──────────┘   └──────────┘   └──────────┘          │
│                                                        │
│  优雅降级: 阶段1失败→单模型ReAct兜底                     │
│            阶段2失败→跳过层级,继续阶段3                   │
│            阶段3失败→返回原图                            │
└────────────────────────────────────────────────────────┘
```

---

### 🚀 快速开始

#### 环境要求

- **Python** ≥ 3.10
- **pip**
- 一个 **兼容 OpenAI API 的密钥**（DeepSeek / OpenAI / 本地 Ollama 等）
- （可选）**FFmpeg** — 如需上传非 WAV 格式音频

#### 1. 克隆安装

```bash
git clone https://github.com/your-username/ai-mindmap-agent.git
cd ai-mindmap-agent

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

> **注意：** 首次启动时，Whisper 将自动下载 `small` 模型（约 500 MB），请确保磁盘空间充足。

#### 2. 配置环境

```bash
cp api.env .env
```

编辑 `.env`，填写你的 API Key：

```env
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

#### 3. 测试连接

```bash
python test_api.py
```

预期输出：
```
✅ API 连接成功！
  Model:  deepseek-chat
  URL:    https://api.deepseek.com
```

#### 4. 启动服务

```bash
python main.py
```

浏览器打开 **http://localhost:8000**。

---

### ⚙️ 配置项详解

所有配置通过 `.env` 环境变量管理：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_API_KEY` | *(必填)* | 主力 LLM 的 API Key |
| `LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容 API 地址 |
| `LLM_MODEL` | `deepseek-chat` | 主力模型名称 |
| `CONCEPT_MODEL` | *(回退到 LLM_MODEL)* | 阶段1 — 概念提取模型 |
| `HIERARCHY_MODEL` | *(回退到 LLM_MODEL)* | 阶段2 — 层级规划模型 |
| `DELTA_MODEL` | *(回退到 LLM_MODEL)* | 阶段3 — Delta 生成模型 |
| `POLISH_MODEL` | *(None = 使用主力模型)* | 润色专用轻量模型 |
| `POLISH_ITERATIONS` | `3` | 轻量模型自迭代最大次数 (1–5) |
| `API_TIMEOUT` | `30` | API 请求超时（秒） |
| `DEBUG_OUTPUT_ENABLED` | `true` | 是否启用逐阶段调试输出 |
| `DETAILS_ENRICHMENT_ENABLED` | `true` | 是否从 AI 回复中丰富节点详情 |

---

### 📡 API 接口文档

#### `POST /chat`

对话与导图生成主接口。

**请求体：**
```json
{
  "message": "请介绍一下机器学习",
  "current_map": { "nodes": [], "links": [] },
  "transcript_context": "(可选) 转录上下文"
}
```

**响应：**
```json
{
  "answer": "机器学习是人工智能的一个分支...",
  "map": {
    "nodes": [{ "id": "node_ml", "label": "机器学习", ... }],
    "links": [{ "source": "node_ml", "target": "node_sl", ... }]
  }
}
```

#### `POST /upload_audio`

上传音频进行 STT 转录与润色。`multipart/form-data`，字段名 `file`。

**响应：**
```json
{
  "status": "success",
  "raw_text": "机器学习就是让计算机从数据中学习",
  "polished_text": "机器学习就是让计算机从数据中学习。",
  "detected_language": "zh"
}
```

---

### 🖥️ 前端界面

前端为单文件 Vue.js 3 应用 (`index.html`)，包含：

| 组件 | 说明 |
|---|---|
| **音频播放器** | 播放上传/录制的音频，实时波形可视化 |
| **聊天面板** | 输入或查看 AI 对话，支持 Markdown 渲染 |
| **转录面板** | 查看、编辑、搜索、筛选转录条目 |
| **导图画布** | 基于 SVG 的可拖拽画布，自动布局与碰撞检测 |
| **节点详情** | 点击节点查看层次化详情条目 |
| **设置面板** | 语言切换、字体选择、界面缩放、同步开关 |

---

### 🧪 评估与测试

详见 [`Evaluation_Schema.md`](./Evaluation_Schema.md)，评估体系包含五大维度：

1. **层级准确率** — 与真实大纲的结构对齐（树编辑距离）
2. **核心概念召回率** — 必知必会概念的捕获比例
3. **下游问答效能** — 基于导图 vs. 原始逐字稿答题的准确率与成本对比
4. **端到端生成时间** — 从音频上传到导图输出的总延迟
5. **语音转录内容保存率** — STT 环节对关键概念的保真度

---

### 📂 项目结构

```
ai-mindmap-agent/
├── main.py                 # FastAPI 编排器（纯编排，无 LLM 调用）
├── mcp_server.py           # MCP Server（5个工具）
├── mcp_client.py           # MCP Client 封装
├── mindmap_agent.py        # 核心：三阶段管线 + ReAct Agent + 调试管理器
├── config.py               # 配置管理类
├── tools.py                # Function-calling JSON Schema
├── schema.py               # Pydantic 数据模型
├── agent.py                # 旧版单模型 Agent（已废弃，保留参考）
├── test_api.py             # API 连接测试脚本
├── index.html              # Vue.js 3 + Tailwind CSS 前端
├── requirements.txt        # Python 依赖
├── Evaluation_Schema.md    # 质量评估标准（中英双语）
└── debug_output/           # 调试输出文件（自动生成）
```

---

### 🤝 贡献指南

欢迎贡献！请通过 Issue 或 Pull Request 参与：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

---

### 📄 许可证

本项目采用 MIT 许可证。

---

### 🙏 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) — 语音识别
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP 服务框架
- [Vue.js](https://vuejs.org/) — 前端框架
- [Tailwind CSS](https://tailwindcss.com/) — CSS 框架
- [Anthropic MCP](https://modelcontextprotocol.io/) — 模型上下文协议
