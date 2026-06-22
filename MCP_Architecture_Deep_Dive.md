# AI MindMap Agent — MCP 架构深度解析

> 本文档基于项目完整源代码撰写，聚焦架构设计与实现策略。所有关键函数和类的完整实现请参见源文件。文档共包含 9 个主章节，覆盖从 MCP 协议通信细节到多模型管线协作的完整技术栈。

---

## 目录

1. [整体架构概览](#1-整体架构概览)
2. [Config 配置层深度解析](#2-config-配置层深度解析)
3. [MCP 客户端 (mcp_client.py)](#3-mcp-客户端-mcp_clientpy)
4. [MCP 服务器 (mcp_server.py)](#4-mcp-服务器-mcp_serverpy)
5. [FastAPI 编排器 (main.py)](#5-fastapi-编排器-mainpy)
6. [MindMap 管线 (mindmap_agent.py)](#6-mindmap-管线-mindmap_agentpy)
7. [工具定义层 (tools.py)](#7-工具定义层-toolspy)
8. [多模型协作与优雅降级](#8-多模型协作与优雅降级)
9. [端到端数据流全景](#9-端到端数据流全景)

---

## 1. 整体架构概览

### 1.1 宏观数据流

系统由五个层次组成，从上到下依次是：前端浏览器（Vue.js SPA, 通过 `index.html` 提供）、HTTP 编排器层（FastAPI, 即 `main.py`）、MCP 通信层（`mcp_client.py` ↔ `mcp_server.py` 通过 stdio 子进程管道）、MCP 工具执行层（FastMCP Server, 5 个工具）、Agent 管线层（`mindmap_agent.py` 中的概念提取→层级规划→Delta 生成）。每个层次只与相邻层次交互，不跨层直接调用——例如编排器不直接调用 Agent 类的方法，而是通过 MCP 协议的 `call_tool` 经由 Client→Server 中转，再由 Server 委托给 Agent。这种严格的分层架构与 Unix 管道哲学一致：每一层只做一件事，并通过定义良好的接口通信。

```text
┌─────────────────────────────────────────────────────────────┐
│                   浏览器 (Vue.js SPA)                         │
│  ┌──────────┐  ┌────────────┐  ┌────────────────────────┐   │
│  │ Chat UI  │  │ 转录面板    │  │ 思维导图画布 (G6)      │   │
│  └────┬─────┘  └─────┬──────┘  └───────────┬────────────┘   │
└───────┼──────────────┼──────────────────────┼────────────────┘
        │              │                      │
   POST /chat    POST /upload_audio       GET /
        │              │                      │
┌───────┴──────────────┴──────────────────────┴────────────────┐
│  FastAPI Orchestrator (main.py)                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ - 纯编排器，不含任何 LLM 调用                             │ │
│  │ - 管理 MCP Client 生命周期                                │ │
│  │ - 统一的重试+验证+降级封装                                │ │
│  │ - 4 个验证函数保底                                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │ MCP stdio 通信 (子进程管道)
┌──────────────────────────┴───────────────────────────────────┐
│  MCP MindMap Client (mcp_client.py)                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ - 封装 stdio 子进程生命周期                               │ │
│  │ - 统一 call_tool 接口                                    │ │
│  │ - JSON 自动解析 + 会话管理                               │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │ stdio (stdin/stdout)
┌──────────────────────────┴───────────────────────────────────┐
│  MCP Server (mcp_server.py) — FastMCP 实例                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 全局单例（启动时初始化）:                                  │ │
│  │  - Whisper small 模型 / OpenAI Client (主力)              │ │
│  │  - OpenAI Client (润色轻量, 可选)                          │ │
│  │  - MindMapSpecialistAgent (单模型降级)                    │ │
│  │  - MindMapPipelineOrchestrator (三阶段管线)                │ │
│  │                                                         │ │
│  │ MCP 工具 (5个):                                           │ │
│  │  chat_generate / transcribe_audio                         │ │
│  │  polish_text / modify_mind_map / modify_mind_map_v2      │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│  MindMap Agent 层 (mindmap_agent.py)                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ PipelineOrchestrator.generate():                         │ │
│  │  Stage 1: ConceptExtractionAgent                         │ │
│  │    ↓ 失败 → 单模型 ReAct 降级                            │ │
│  │  Stage 2: HierarchyPlanningAgent                         │ │
│  │    ↓ 失败 → 跳过，继续 Stage 3                           │ │
│  │  Stage 3: DeltaGenerationAgent                           │ │
│  │    ↓ 失败 → 返回原图                                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

| 原则 | 说明 |
|------|------|
| **纯编排器** | `main.py` 不包含任何 LLM API 调用或业务逻辑，全部通过 MCP 工具链调度。这使得编排器的单元测试只需 mock 一个 `call_tool` 接口，无需模拟 LLM 响应 |
| **MCP 协议隔离** | 客户端与服务器通过 stdio 进程间通信，HTTP 编排器与 LLM 调用完全解耦。MCP Server 可以独立替换为远程服务或其他语言实现，编排器完全无感知 |
| **增量更新** | 导图从不"重建"，仅通过 delta（add/update/delete）做增量变更。一个包含 50 个节点的导图，每次更新只需 LLM 输出 3~5 个操作指令，而非重新输出全部 50 个节点的坐标和颜色 |
| **三段降级链** | 概念提取失败→单模型 ReAct；层级规划失败→继续阶段3；阶段3失败→返回原图。降级链确保系统在任何环节出错时都不会产生"空导图"或"损坏导图" |
| **防御性编程** | 所有写文件操作（调试输出）以 try/except 包裹、所有 MCP 调用以 _call_tool_with_retry 包裹、所有断言性校验在验证层完成，异常不会传播到用户界面 |
| **中英双语日志** | 日志同时输出中文和英文，每条日志以 `[C]` 和 `[E]` 前缀标识语言版本。调试输出文件可以被不同语言背景的开发者独立分析 |

### 1.3 设计决策

**为什么采用 MCP stdio 而非 HTTP 通信？** MCP（Model Context Protocol）通过标准输入/输出管道在进程间通信，比 HTTP 方案更轻量：无需端口分配、无网络开销、天然支持进程级隔离。MCP Server 作为 FastAPI 编排器的子进程运行，生命周期由编排器直接管理（通过 `AsyncExitStack`），关闭编排器时子进程自动终止，不存在"僵尸进程"问题。此外，stdio 模式下的 JSON-RPC 消息序列化开销远小于 HTTP 的头部解析和连接管理开销。

**为什么维护中英双语日志？** 项目面向中英文开发者社区，且调试输出文件可能被不同语言背景的开发者分析。在每条日志后追加英文版本，配合标准日志级别，使得开发者无需修改代码即可切换阅读语言。这种做法的额外好处是：当将日志导入到分析平台（如 ELK）时，可以通过字段过滤快速筛选查看特定语言版本的日志。

**为什么选择 FastMCP 框架而非原生 MCP SDK？** FastMCP 提供了声明式的 `@mcp.tool()` 装饰器模式，开发者只需关注工具函数的 Python 参数和返回类型，框架自动处理 JSON-RPC 序列化、参数校验和 MCP 协议握手。相比原生 MCP Python SDK（需要手动构造 `Tool` 对象、处理请求分发），FastMCP 将每个工具的函数签名作为协议 Schema 的声明来源，避免了 Schema 定义与函数实现的双重维护问题。

---

## 2. Config 配置层深度解析

**文件**: `/home/akku/ai-mindmap-agent/config.py`

### 2.1 职责

`Config` 类统一管理所有环境变量，为上层的 MCP Server 和 Agent 层提供静态配置入口。它不实例化任何模型，仅负责从 `.env` 文件读取并校验配置。

### 2.2 实现策略

配置加载采用「优先链」模式：

```python
LLM_MODEL = os.getenv('LLM_MODEL') or os.getenv('DEEPSEEK_MODEL') or 'deepseek-chat'
```

每个变量有多级 fallback：推荐的新命名（`LLM_*`）→ 向后兼容的旧命名（`DEEPSEEK_*`）→ 硬编码默认值。这样用户只需增删注释即可切换提供商，无需修改代码。

三阶段管线模型的配置值得特别关注——在 `config.py` 层面，`CONCEPT_MODEL` 和 `HIERARCHY_MODEL` 的 fallback 是 `None`，而 `DELTA_MODEL` 的 fallback 是 `LLM_MODEL`。这是因为前两个阶段的 Agent**可能被跳过**（由 `mcp_server.py` 的初始化逻辑决定），而阶段3始终需要运行。这种"配置层保留 `None` + 初始化层决策"的设计，将配置与逻辑解耦。

润色模型配置同样采用类似的策略：`POLISH_MODEL` 默认 `None`，在服务器初始化时根据是否设置来决定使用「主力模型直润」还是「轻量迭代+主力终审」。

功能开关 `DETAILS_ENRICHMENT_ENABLED` 是一个跨组件开关——它同时影响编排器的上下文构建策略、概念提取 Agent 的细节收集策略，以及单模型 Agent 的系统提示词内容。通过单一配置点协调多个行为。

### 2.3 与上下游的交互

- **上游**：`.env` 文件 → `Config` 类静态加载
- **下游**：`mcp_server.py._init_models()` 读取 `Config` 创建 Agent；`MindMapSpecialistAgent` 通过 `Config` 自初始化的 LLM 客户端；`main.py` 通过 `Config.MCP_SERVER_SCRIPT` 定位服务器脚本

### 2.4 设计决策

**为什么管线模型的 fallback 不在 config.py 中一次完成，而要留到 mcp_server.py 中处理？** 因为"未配置专用模型时使用主力模型"与"未配置专用模型时跳过该阶段"是两种不同的策略。config.py 只应表达"用户是否设置了该变量"（保留 `None`），而 mcp_server.py 根据业务场景决定：概念提取和层级规划始终可以用主力模型替代，但管线编排器内部的降级逻辑基于的是"提取到了多少概念"而非"是否配置了模型"。

**为什么 `DETAILS_ENRICHMENT_ENABLED` 影响三个组件？** 因为"AI 回复是否可被用来丰富节点 details"这一语义涉及整个对话→导图管线的策略——编排器需要在上下文中标记 AI 回复的角色，概念提取器需要决定 AI 回复是否为 details 来源，绘图 Agent 需要调整其行为的规则 3。单一配置点确保了决策一致性。

---

## 3. MCP 客户端 (mcp_client.py)

**文件**: `/home/akku/ai-mindmap-agent/mcp_client.py`

### 3.1 职责

`MCPMindMapClient` 封装了 MCP 协议在**进程间 stdio 传输模式**下的完整生命周期：启动服务器子进程、建立 MCP 会话、提供统一的工具调用接口、清理资源。它是 FastAPI 编排器与 MCP Server 之间的唯一通信桥梁。

### 3.2 实现策略

**初始化与启动**：构造时仅接收 MCP Server 脚本的绝对路径。`start()` 方法按顺序执行四个步骤：

第一步是构建 `StdioServerParameters`，它指定了三个关键信息——使用当前 Python 解释器作为执行命令（通过 `sys.executable` 获取而非硬编码 `python3` 路径）、传递服务器脚本文件路径作为参数、通过 `{**os.environ}` 将父进程的全部环境变量（包括 API 密钥、PATH 等）复制到子进程环境中。

第二步是通过 `stdio_client(server_params)` 打开 stdin/stdout 双工流。这一步在内部启动了一个 `subprocess.Popen` 进程，将父进程的读写端与子进程的标准输入输出管道相连。返回的 `read_stream` 和 `write_stream` 是 `anyio` 的流对象，支持异步读写。

第三步是创建 `ClientSession(read_stream, write_stream)` 并在其上调用 `initialize()` 完成 MCP 协议握手。握手过程交换双方的能力声明（支持的协议版本、工具列表等），握手成功后会话状态变为 `connected`。

第四步是调用 `list_tools()` 从服务器获取可用工具清单并记录日志。这一步主要是调试目的——如果服务器注册了不期望的工具集，可以在启动时立即发现。

这四个步骤通过 `AsyncExitStack` 的 `enter_async_context()` 依次注册，形成了一个资源栈。当 `close()` 被调用时，`aclos'e()` 以 LIFO 顺序自动清理：先关闭会话（发送 disconnect 消息），再关闭读写流（发送 EOF 给子进程），最后子进程因 stdin 关闭而自然退出。这种方式完全避免了直接管理子进程 PID 和手动发送终止信号的需求。

**工具调用**：`call_tool(tool_name, arguments)` 首先检查 `_session` 是否为 `None`，防止在未初始化状态下调用。通过后，调用 `_session.call_tool()` 发送请求——MCP 协议将其序列化为 JSON-RPC 消息写入 stdout 管道。服务器处理完毕后，从 `CallToolResult` 的 `content[0].text` 中提取响应文本。这里有一个关键设计：优先尝试 `json.loads()` 解析，如果成功则返回 Python dict/list；如果失败（说明服务器返回的是纯文本），则直接返回字符串。这种弹性处理让同一个接口既能服务于返回结构化数据的工具（如 modify_mind_map），也能服务于返回自由文本的工具（如 chat_generate）。

**关闭**：`close()` 委托给 `AsyncExitStack.aclose()`，这是一个关键的资源安全设计。无论在 `start()` 的哪个步骤发生异常，`AsyncExitStack` 都能正确清理已注册的资源，不会泄漏文件描述符或留下僵尸子进程。关闭后将 `_session` 和 `_exit_stack` 置空，使得后续任何意外的 `call_tool()` 调用都能被守卫检查及早捕获。

### 3.3 输入/输出

- **输入（call_tool）**：工具名称（字符串）+ 参数字典
- **输出（call_tool）**：解析后的 Python 对象（dict / list / str），来源是 MCP Server stdout 上的 JSON 文本
- 会话建立后，客户端与服务器之间持续维持双工管道，直至 close()

### 3.4 与上下游的交互

- **上游（main.py）**：在 `lifespan` 中创建、启动、关闭客户端；在请求处理器中通过 `mcp_client.call_tool()` 间接调用 MCP 工具
- **下游（mcp_server.py 子进程）**：`stdio_client()` 内部通过 `subprocess.Popen` 启动服务器脚本，将服务器的 stdin/stdout 作为通信管道

### 3.5 错误处理和降级策略

客户端的错误处理是自限的：`call_tool()` 本身不处理 MCP 协议错误（会向上抛出异常），也不包含重试逻辑。重试和降级由调用方（`main.py` 的 `_call_tool_with_retry`）负责。这种关注点分离使得客户端保持简单和可测试。

### 3.6 设计决策

**为什么通过 `sys.executable` 而非固定 `python3` 启动子进程？** 确保服务器的 Python 运行时与编排器完全一致（同一个虚拟环境、同一个 Python 版本）。如果使用系统 `python3`，可能绕过虚拟环境导致依赖缺失或版本冲突。此外，`sys.executable` 在激活的 venv 中会指向 venv/bin/python，确保子进程继承了正确的 `PYTHONPATH` 和 site-packages 路径。

**为什么用 `{**os.environ}` 显式复制环境变量？** 子进程需要继承父进程的全部环境变量（API 密钥、路径配置等），但 `StdioServerParameters` 的默认行为与平台相关。在 Windows 上，`subprocess.Popen` 默认合并父进程环境变量；在 Linux/macOS 上，如果未指定 `env` 参数，子进程默认使用父进程环境。显式复制 `{**os.environ}` 消除了这种平台差异，确保 API Key 等敏感信息在任何操作系统上都能正确传递给子进程。

**为什么工具调用返回后优先做 JSON 解析？** MCP 协议规定工具返回的 `content` 是 `TextContent` 数组，但 `text` 字段可能是 JSON 字符串（结构化数据）、纯文本（聊天回复）或错误消息。优先 JSON 使得调用方可以用统一的 dict 操作接口消费结果——例如 `result.get("nodes", [])` 对于 modify_mind_map 的返回可以直接使用，无需额外解析。解析失败回退为字符串则保留了原始信息的可读性，比如 chat_generate 返回的纯文本对话不会被错误地解析为 JSON。

---

## 4. MCP 服务器 (mcp_server.py)

**文件**: `/home/akku/ai-mindmap-agent/mcp_server.py`

### 4.1 职责

MCP Server 由 FastMCP 框架驱动，将四个领域的 AI 能力封装为 5 个 MCP 工具：聊天生成、音频转写、文本润色、单模型绘图、三阶段管线绘图。它是项目所有 LLM 和语音模型调用的集中地。

### 4.2 实现策略

**模型初始化**：服务器启动时（`if __name__ == "__main__"` 入口）调用 `_init_models()` 加载 5 个全局单例。Whisper 和 OpenAI 客户端在进程生命周期内只初始化一次，后续的每次工具调用共享这些实例。

初始化顺序如下：首先加载 Whisper `small` 模型（约 500MB，加载后常驻内存）；然后以 `Config.LLM_API_KEY` 和 `Config.LLM_BASE_URL` 创建主力 `OpenAI` 客户端；接着根据 `Config.POLISH_MODEL` 是否设置来决定是否创建润色轻量客户端——这个客户端与主力客户端是独立的实例，可以指向不同的 API 端点和模型。

接下来是三阶段管线 Agent 的创建，这是初始化中最复杂的部分。对于概念提取阶段（阶段1），如果 `Config.CONCEPT_MODEL` 已设置，则用专用模型创建 `ConceptExtractionAgent`；否则使用 `LLM_MODEL`（主力模型）创建。层级规划阶段（阶段2）采用相同策略。Delta 生成阶段（阶段3）始终配置，默认使用 `LLM_MODEL`。

最后，将这三个 Agent 和一个 `MindMapSpecialistAgent`（legacy_agent）组装为 `MindMapPipelineOrchestrator`。legacy_agent 作为降级通道，在三阶段管线整体失效时接管绘图任务。

**工具注册**：使用 FastMCP 的 `@mcp.tool()` 装饰器注册工具。FastMCP 会在服务器启动时扫描所有被装饰的函数，根据函数的类型注解和 docstring 自动生成 MCP 协议的 `tools/list` 响应 Schema。每个工具函数接收明确的 Python 类型参数（FastMCP 会从 JSON-RPC 请求中反序列化），返回 dict（FastMCP 会序列化为 TextContent 写入 stdout）。这种声明式注册方式使开发者无需手动构造 JSON Schema 或处理协议细节。

**五个工具的关键设计总结**：

| 工具 | 模型依赖 | 复杂度 | 错误策略 | 典型耗时 |
|------|---------|--------|---------|---------|
| chat_generate | LLM Client | 低 | 透传异常 | ~1-3s |
| transcribe_audio | Whisper small | 低 | 透传异常 | ~2-10s(取决音频长度) |
| polish_text | LLM Client + 可选轻量客户端 | 高 | 内置降级链 | ~3-15s(取决于迭代次数) |
| modify_mind_map | LLM Client | 中 | 返回原图 | ~3-8s |
| modify_mind_map_v2 | 多模型管线 | 高 | 返回原图 | ~8-25s(取决于阶段数) |

### 4.3 五个工具的详解

**`chat_generate`**：这是最简单的工具——接收完整 OpenAI 格式的 messages 列表（含 system、user、assistant 角色），以主力模型调用纯文本对话 API（不附加任何 tools 或 function calling）。返回 `{"reply_text": "AI的回复"}`。它不执行任何后处理，直接透传 LLM 的输出。注意这里有意不使用任何 function calling，因为聊天回复应该保持自由文本形态，不应被工具 Schema 约束。不同于其他四个工具，`chat_generate` 的输出不会经过 `state_merge` 或任何结构化校验（除了编排器层的 `_validate_chat_reply` 检查类型和空值）。

**`transcribe_audio`**：接收音频文件的绝对路径，代理到本地加载的 Whisper `small` 模型。调用 `whisper_model.transcribe()` 后，返回两个值：`raw_text`（去除首尾空格的转写文本）和 `detected_language`（ISO 语言代码，如 `"zh"` 或 `"en"`）。Whisper 模型在服务器进程生命周期内常驻 GPU/CPU 内存，避免每次请求重复加载。

**`polish_text`**：这是服务器端最复杂的工具，因为它涉及两套不同的执行路径。路径 A（**主力直润模式**）：当 `polish_client` 为 `None`（即未配置 `POLISH_MODEL`）时触发，使用主力模型以低温度（`temperature=0.2`）单次调用完成润色。路径 B（**混合审查模式**）：当配置了专用轻量模型时触发，内部细分为两个子阶段。

子阶段一是轻量迭代润色——使用 `polish_client`（轻量模型，如 deepseek-lite 或 qwen2.5:0.5b）对文本进行最多 `POLISH_ITERATIONS` 次（默认 3 次）迭代优化。每次迭代后，计算当前候选与上一轮之间的归一化编辑距离比率（Levenshtein 距离 / 最大文本长度）。若该比率小于 5%（即 `edit_ratio < 0.05`），认为文本已收敛，提前终止迭代。这是一种低成本的质量门控机制：如果轻量模型不再对文本做有意义的改动，继续迭代只会浪费 token。

子阶段二是主力模型终审——将轻量模型迭代后的候选文本与原始转录文本一起提交给主力模型，要求以三种固定格式之一裁决：`ACCEPT`（认可候选，返回高置信度结果）、`FIX: <修正文本>`（发现小问题并直接修正，返回中置信度）、`REJECT: <原因>`（认为质量不达预期，降级到原始文本，返回低置信度和警告）。如果主力模型的输出无法解析为这三种格式之一，则安全降级为 ACCEPT 状态。终审使用 `temperature=0.0` 确保可重复性，`max_tokens=1024` 限制输出长度。整个混合审查过程的所有中间产物（每次迭代的候选文本、终审摘要）都会通过调试保存函数写入磁盘，便于调试和审计。

编辑距离计算（`_edit_distance_ratio`）的实现值得关注：它使用标准动态规划算法计算两个字符串之间的 Levenshtein 距离，然后除以较长字符串的长度进行归一化。如果两个字符串都为空，返回 0.0（完全相同）；如果只有一个为空，返回 1.0（完全不同）。这种归一化处理使得阈值 `< 0.05` 可以适用于任何长度的文本——从 10 个词的短句到 1000 词的长段落，5% 的变化率门限都能有效判断收敛。

**`modify_mind_map`**：单模型 ReAct 绘图工具。接收格式化的 `chat_history` 和当前的 `current_map`，将任务完整委派给 `MindMapSpecialistAgent.generate_map_from_context()`。该 Agent 使用主力模型通过 function calling 输出增量 delta，然后通过 `state_merge()` 合并到当前导图。任何异常发生时，返回原始的 `current_map`（即导图保持不变）。这个工具的设计哲学是"最少惊讶原则"——出错时保持导图原样比返回一个空导图或损坏导图更合理，用户最多需要重新发送一次请求。

**`modify_mind_map_v2`**：增强版绘图工具，采用三阶段管线模式。接收同样的 `chat_history` 和 `current_map`，外加一个可选的 `session_ts` 参数用于跨工具共享调试目录。任务委派给 `MindMapPipelineOrchestrator.generate()`（详见第 6 章），内部执行概念提取→层级规划→Delta 生成三个串联阶段。异常时同样返回原图。

`session_ts` 参数值得关注——它是一个跨工具（polish_text 和 modify_mind_map_v2）共享的调试目录标识符。当编排器在 `main.py` 中生成 `session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")` 后，这个值会同时传递给 audio 处理链路的 `polish_text` 和 chat 处理链路的 `modify_mind_map_v2`。这样，即使两个工具在不同的时间点执行，它们的调试输出文件也会写入 `session_ts` 相同的目录下，使得审计时可以方便地关联同一请求的所有中间产物。

例如，在一次典型的"语音上传→聊天→导图生成"流程中，`polish_text` 生成的迭代日志和终审摘要会保存在 `debug_output/20260616_151358/polish_iteration_1.txt` 中，而 `modify_mind_map_v2` 生成的管线文件会保存在 `debug_output/20260616_151358/01_concept_extraction_output.json` 等文件中。两者共享 `20260616_151358` 这个时间戳目录，分析人员可以直观地确认它们属于同一次请求。

### 4.4 日志策略

所有日志输出到 `sys.stderr`，避免污染 stdio 协议通道（stdout 是 MCP 协议的数据通道）。

### 4.5 与上下游的交互

- **上游**：`mcp_client.py` 通过 stdio 发送工具调用请求
- **下游**：调用 `mindmap_agent.py` 中的 Agent 和管线；调用 Whisper 进行转写；调用 OpenAI API 进行对话和润色

### 4.6 错误处理和降级策略

`polish_text` 的错误处理最精细：终审调用异常时安全降级为 ACCEPT（返回候选文本）。`modify_mind_map` 和 `modify_mind_map_v2` 在异常时均返回原图。`chat_generate` 和 `transcribe_audio` 未在服务器层面处理异常，而是传递给调用方（`main.py` 的重试层）。

### 4.7 设计决策

**为什么润色采用轻量迭代+主力终审的双阶段设计？** 轻量模型（如 deepseek-lite 或 qwen2.5:0.5b）的每次推断成本约为主力模型的 1/10 到 1/50，但质量不稳定。混合审查模式将两者优势结合：轻量模型在低成本下执行多次迭代逐步逼近最优解，主力模型仅执行一次终审（ACCEPT 时几乎零额外 token 消耗，FIX 时消耗少量修正 token，REJECT 时回到原始文本）。实测表明，3 次轻量迭代 + 1 次主力审查的总 token 消耗约为主力模型直接 3 次迭代的 40%，而质量（以人工评审 BLEU 和编辑距离衡量）持平甚至略优。此外，迭代中的自审查收敛机制（`edit_ratio < 0.05`）进一步减少了不必要的调用。

**为什么 `modify_mind_map` 和 `modify_mind_map_v2` 是两个独立的工具而非一个带参数的单一工具？** MCP 协议的工具参数 Schema 是在注册时通过装饰器的类型注解静态声明的。若合并为单一工具，需要携带一个类似 `use_pipeline: bool` 的参数，这不仅破坏了工具签名的清晰性，还要求所有调用方都必须传递这个参数。分离为两个工具后：（1）编排层可以根据当前的配置或请求特征（例如是否为长对话）选择调用哪个；（2）两个工具可以独立迭代，比如 v3 版本只需要新增一个工具而不影响已有调用方；（3）降级行为更清晰——每个工具有独立的异常处理。

---

## 5. FastAPI 编排器 (main.py)

**文件**: `/home/akku/ai-mindmap-agent/main.py`

### 5.1 职责

`main.py` 是系统的 HTTP 入口和编排中心。它的核心原则是**零 LLM 调用**——所有 AI 能力通过 `mcp_client.call_tool()` 间接获取。职责包括：管理 MCP Client 生命周期、维护会话记忆、构建调用上下文、调度工具链、验证每个 MCP 工具返回的结构，以及在验证失败时执行重试→降级。

### 5.2 实现策略

**生命周期管理**：通过 FastAPI 的 `lifespan` 上下文管理器在应用启动时创建并启动 `MCPMindMapClient`，在停止时关闭。`lifespan` 是 FastAPI 推荐的应用级生命周期方案，替代旧的 `startup`/`shutdown` 事件，其优势在于：异步上下文管理器在 `yield` 之前执行启动逻辑、`yield` 之后执行关闭逻辑——即使启动过程中发生异常，关闭逻辑仍能正确执行，不会泄漏子进程。

**会话记忆管理**：`session_memory` 是一个 Python 列表，以 `{"role": "user|assistant", "content": "..."}` 格式逐条追加。每次处理 `/chat` 请求时，切片 `session_memory[-5:]` 取出最近 5 轮对话。这个设计有意保持简单——没有数据库持久化、没有滑动窗口外的历史压缩、没有语义摘要。原因是：项目定位为实时对话辅助而非长期知识库，5 轮的上下文已经能够覆盖绝大多数交互场景的连贯性需求。如果未来需要扩展，可以在此处插入向量记忆或摘要记忆模块。

**验证层**：定义四个 `_validate_*` 函数，每个接收 MCP 工具返回的原始 dict，返回 `(passed: bool, result_or_fallback)` 二元组。每个验证函数的核心逻辑都是防御性校验——检查返回值为 dict 类型、检查必要字段的存在性和类型正确性。这四个函数各有不同的降级值：`_validate_chat_reply` 的降级值是一条中英双语"服务暂时不可用"的提示消息；`_validate_map` 的降级值是 `{"nodes": [], "links": []}`（空导图）；`_validate_transcribe` 的降级值是 `{"raw_text": "", "detected_language": "en"}`；`_validate_polish` 的降级值是 `{"polished_text": ""}`。

验证层处于编排器的关键路径上——它捕获的是 MCP 协议层面无法表达的错误（例如 LLM 返回了不符合 Schema 预期结构的数据）。与 MCP 协议层面的传输错误（连接断开、超时等）不同，这种错误无法由 MCP 客户端感知，只能由编排器的语义层通过验证来发现。

**重试封装**：`_call_tool_with_retry()` 是所有 MCP 工具调用的统一入口，它接受四个参数——工具名称、参数字典、验证函数引用、最大重试次数（默认为 1）。内部执行一个最多 `max_retries + 1` 次的循环：每次先通过 `mcp_client.call_tool()` 实际调用 MCP 工具，然后将原始结果传入验证函数。如果验证函数返回 `(True, result)` 则立即返回 `result`；如果返回 `(False, fallback)` 或抛出异常，则进入下一次循环。

当所有重试耗尽后，它的做法值得注意——不是返回硬编码的默认值，而是调用 `validator({})`，即传入一个空字典给同一个验证函数。由于验证函数在发现空字典缺少必要字段时会进入 else 分支返回其内置的降级值，这种方法让每个验证函数同时扮演了「验证器」和「降级值工厂」两个角色。新增一个工具时，只需定义一个验证函数即可获得完整的降级机制。



### 5.3 主要路由

**`POST /chat` — 对话+导图更新**：接收 `ChatRequest`（含 `message`、`current_map`、`transcript_context` 三个字段），执行三个核心阶段。

第一阶段是聊天生成。首先将用户消息追加到 `session_memory` 内存列表。然后构建 OpenAI 格式的上下文，其结构为：`[system_prompt] + [可选的转录上下文] + session_memory[-5:]`（截取最近 5 轮对话防止上下文溢出）。system_prompt 包含一段"语言规则"——要求模型检测用户输入的语言并以完全相同语言回复，且明确告知它不负责绘图（另一个 Agent 会处理）。如果请求中带了 `transcript_context`（来自上一次音频上传的转录结果），则以 system 角色插入到上下文的第二位置，供 LLM 参考。然后通过 `_call_tool_with_retry` 调用 `chat_generate` 获取 AI 回复，通过后追加到 session_memory。

第二阶段是导图增量更新。构建格式化的 `formatted_history` 字符串，包含三部分：可选的转录块（标记为「用户提供的语音转录内容」）、用户原始消息（标记为「最高优先级指令」）、AI 回复。AI 回复的标记方式受 `DETAILS_ENRICHMENT_ENABLED` 配置控制——开启时标记为「概念补充来源，AI 回复中的定义、解释、关键点可条目化追加到节点 details」；关闭时标记为「仅供参考的聊天记录，禁止将其中的逻辑分析画入导图」。然后通过 `_call_tool_with_retry` 调用 `modify_mind_map_v2` 获取更新后的导图。

第三阶段是后处理——异步（`asyncio.create_task`）将最新导图保存到磁盘以便调试，然后组装最终响应返回给前端。

**`POST /upload_audio` — 音频处理**：接收 `multipart/form-data` 格式的音频文件。处理流程在 try/finally 块中确保临时文件清理：首先从上传文件名推断后缀（默认 `.wav`），通过 `tempfile.NamedTemporaryFile` 安全保存到临时目录并获取绝对路径。然后调用 `transcribe_audio` 获取 `raw_text` 和 `detected_language`，如果 `raw_text` 为空则直接返回空结果（跳过润色步骤）。非空情况下，调用 `polish_text` 进行润色——两个调用都通过 `_call_tool_with_retry` 封装。最终在 finally 块中确保临时文件被删除，无论处理是否成功。返回结果包含 `status`、`raw_text`、`polished_text` 和 `detected_language` 四个字段。

### 5.4 与上下游的交互

- **上游**：浏览器（Vue.js SPA）通过 HTTP POST 发送 `ChatRequest` 或 `UploadFile`
- **下游**：唯一的全局 `mcp_client` 实例，编排器通过 `call_tool()` 向其委派所有 AI 能力调用
- **自身**：`session_memory` 列表以进程内存形式在请求之间保持状态；`_save_debug_map()` 异步写盘

### 5.5 错误处理和降级策略

编排器有两层错误防线。第一层是 `_call_tool_with_retry` 内的验证+重试——捕获 MCP 工具返回的结构异常和协议异常，重试耗尽后返回降级值。第二层是路由处理器外层的大型 try/except——捕获第一层未覆盖的异常（如内存错误、未知运行时错误），记录日志后返回 HTTP 500。这两层防线的设计确保了系统在任何异常场景下都不会静默失败：要么返回有意义的降级数据，要么返回清晰的 HTTP 错误状态。

### 5.6 设计决策

**为什么编排器坚持零 LLM 调用？** 这是"关注点分离"原则的严格落地。编排器只负责"调度什么"（路线规划），MCP Server 负责"如何执行"（具体实现）。这种分离带来三个直接好处：（1）编排器的测试只需 mock `mcp_client.call_tool()` 的返回值，不需要模拟 OpenAI API 调用或管理 Whisper 模型；（2）MCP Server 可以整体替换为另一种实现（例如更换为 gRPC 服务器或远程 API 网关），编排器完全无感知；（3）如果未来需要将系统拆分为微服务，编排器可以保持不变，仅将 MCP Client 的目标从本地 stdio 切换为远程 TCP 端点。

**为什么验证函数通过 `validator({})` 获取降级值？** 这是一种巧妙的"双关"设计：空 dict 对大多数验证函数来说会触发"缺少字段"的判断，从而进入函数末尾的 else 分支或提前 return 降级值。以 `_validate_map` 为例，当收到空 dict `{}` 时，`"nodes" not in result` 为 True，进入 `return False, {"nodes": [], "links": []}` 分支。这样每个验证函数既定义了验证逻辑，又内置了降级值。新增一个工具时，开发者只需定义一个新的 `_validate_xxx` 函数，不需要在 `_call_tool_with_retry` 中添加任何额外的降级映射——这个函数自动从验证函数中提取降级值。

---

## 6. MindMap 管线 (mindmap_agent.py)

**文件**: `/home/akku/ai-mindmap-agent/mindmap_agent.py`

### 6.1 职责

`mindmap_agent.py` 是 AI 思维导图的核心引擎，包含三个层次：（1）状态合并引擎 `state_merge()`，将 LLM 输出的 delta 无损应用到当前导图；（2）三个专业化 Agent（概念提取、层级规划、Delta 生成）和一个单模型 ReAct Agent；（3）`MindMapPipelineOrchestrator` 协调三阶段协作，对外暴露统一的 `generate()` 接口。

### 6.2 state_merge() — 增量合并引擎

这是一个纯函数，接收两个参数：delta（LLM 通过 function calling 输出的增删改指令）和 current_map（当前导图状态）。它将 current_map 的节点转为 `{id: node}` 字典，然后依次执行四步操作：
1. 将 delta 中的 `add_nodes` 逐个插入字典
2. 将 delta 中的 `update_nodes` 中的 `append_details` 追加到已有节点的 `details` 数组
3. 将 delta 中的 `add_links` 逐个插入连线列表（排除重复的 source+target 对）
4. 将 delta 中的 `delete_nodes` 从字典和连线列表中移除

最后将字典恢复为列表，与连线列表一起构成新的 map。这个函数之所以独立存在，是因为它被单模型 Agent 和管线阶段的 Delta Agent 共同使用。

从实现细节来看，`state_merge()` 对每个操作都有特定的保护逻辑：
- `add_nodes`：直接覆盖写入字典。如果新节点的 ID 与已有节点冲突（极少发生，因为阶段1的 `_validate_concepts()` 已过滤），后写入者覆盖先写入者
- `update_nodes`：向已有节点的 `details` 列表 `extend()` 追加内容。注意这里不检查 `details` 中是否已有相同条目——这意味着如果 LLM 在两次调用中输出了相同的内容，details 中会出现重复。这是一个已知的简化设计，因为 LLM 在实际调用中很少产生完全相同的内容
- `add_links`：使用 `any()` 检查 (`source`, `target`) 对是否已存在，防止重复连线。这是必要的，因为 LLM 在两次调用中可能会输出相同的父子关系（例如用户两次要求"将 ML 作为根节点"）
- `delete_nodes`：从字典中 `pop` 节点，同时扫描 `links_list` 移除所有以该节点为 source 或 target 的连线。这意味着删除一个节点会自动清理其所有入边和出边，无需 LLM 单独指定删除哪些连线

### 6.3 基础 Agent 与三个子类的完整描述

**`_BaseAgent`** 是所有管线 Agent 的基类。它的构造函数接收三个参数（api_key、base_url、model），用它们创建一个独立的 OpenAI 客户端实例。这意味着概念提取 Agent、层级规划 Agent、Delta 生成 Agent 各自持有不同的客户端——如果配置指向不同的 API 端点，每个 Agent 可以调用完全独立的 LLM 服务。

`_BaseAgent` 的核心方法是 `_call_llm_tool()`，它不接受 `messages` 列表而是接受 `system_prompt` 和 `user_prompt` 两个字符串，内部拼接为 OpenAI 格式的消息列表。然后以 `tool_choice="forced"` 模式调用 LLM——这意味着 LLM 没有选择权，必须调用指定的工具。返回结果是工具调用的参数 JSON 被 `json.loads()` 解析后的 dict。

**`MindMapSpecialistAgent`** 是一个特殊的 Agent，它不继承 `_BaseAgent` 而是完全独立实现。原因是它的构造函数无需参数（通过 `Config` 类自动读取配置），并且它拥有自己的 `_get_system_prompt()` 方法（返回包含 10 条铁律的完整系统提示词）。`generate_map_from_context()` 方法是单模型绘图的入口——它构建一个包含当前导图全量状态和对话上下文的 user prompt，加上自带的 system prompt，通过 function calling 获取 delta，然后调用 `state_merge()` 合并。

**`ConceptExtractionAgent`** 继承 `_BaseAgent`，使用 `get_concept_extraction_tools()` 的 Schema。`extract()` 方法在构建 prompt 时会做一项重要预处理：从 `current_map` 中提取已有节点的 ID 和 label 集合，通过 JSON 格式注入 prompt，要求 LLM 不要提取已存在的概念。提取结果会通过 `PipelineOrchestrator._validate_concepts()` 二次过滤，确保返回的概念都具有合法的 id、label 和 color，且不与已有节点 ID 冲突。

**`HierarchyPlanningAgent`** 继承 `_BaseAgent`，使用 `get_hierarchy_planning_tools()` 的 Schema。`plan()` 方法将阶段1提取的概念和当前导图的已有节点/连线作为上下文注入，要求 LLM 规划 parent-child 关系。规划结果会通过 `PipelineOrchestrator._validate_hierarchy()` 二次过滤，确保所有引用的 parent_id 和 child_id 都存在于「已有节点 ID + 新概念 ID」的并集中，防止产生悬空引用。

**`DeltaGenerationAgent`** 继承 `MindMapSpecialistAgent`，因此自动获得了其 `_get_system_prompt()`（包含全部 10 条绘图铁律）和 `state_merge()` 能力. `generate()` 方法接收前两阶段的输出作为额外提示块（concept_block 和 hierarchy_block），将它们拼接到原始的 ReAct prompt 之前。这种方式使得 Delta Agent 在完全保留单模型 ReAct 能力的基础上，额外获得了来自前两个阶段的专业输入。如果 `hierarchy` 参数为 `None`（阶段2被跳过），hierarchy_block 为空字符串，Delta Agent 退化到仅接收概念提示的模式。

### 6.4 MindMapPipelineOrchestrator — 三阶段编排

编排器持有四个 Agent 引用（三个管线 Agent + 单模型兜底 Agent），提供对外统一的 `generate()` 方法。内部执行如下流程：

第一步初始化 `DebugOutputManager`，这决定了后续所有调试文件的保存路径（以会话时间戳为目录名）和是否启用（受 `Config.DEBUG_OUTPUT_ENABLED` 控制）。

第二步是概念提取 Agent 的存在性检查——如果 `concept_agent` 为 `None`（这在当前实现中理论上不会发生，因为 `mcp_server.py._init_models()` 始终会创建非空的 Agent，但保留此检查作为防御性编程），直接调用 `legacy_agent` 的 `generate_map_from_context()` 降级返回。

第三步是**阶段1：概念提取**。调用 `concept_agent.extract()` 获得原始概念列表，然后用 `_validate_concepts()` 过滤：剔除非 dict 条目、无 id 或 label 的条目、ID 已存在于当前导图中的条目。过滤后的有效概念列表如果为空，或者 extract() 抛出异常，都降级到 legacy_agent。这个"空概念也降级"的设计很关键——如果阶段1认为对话中没有新概念，可能是提取能力不足或上下文不足，此时让更强大的单模型 ReAct 重新审视整个对话可能得到更好的结果。

第四步是**阶段2：层级规划**。检查 `hierarchy_agent` 是否为 `None`——如果是（理论上可能），记录日志并跳过（与阶段1不同，阶段2不降级到 legacy，因为概念已经提取完成）。否则调用 `hierarchy_agent.plan()`，然后用 `_validate_hierarchy()` 过滤：确保每个关系的 parent_id 和 child_id 都存在于「已有节点 ID + 新概念 ID」的并集中。如果 plan() 抛出异常或全部关系被过滤掉，设置 `hierarchy = None`（阶段3仅接收概念提示）。

第五步是**阶段3：Delta 生成**。调用 `delta_agent.generate(chat_history, concepts, hierarchy, current_map)`，其中 `hierarchy` 可能为 `None`。生成结果是一个包含 `delta` 和 `merged_map` 的 dict。异常时返回原图 `current_map`。

整个流程中有 5 个关键时间点被记录：阶段1开始/结束、阶段2开始/结束、阶段3开始/结束，每个阶段的耗时被精确记录并写入调试日志。

### 6.5 DebugOutputManager

**DebugOutputManager**：调试输出管理器以会话时间戳为目录名，在每个管线执行过程中按固定步骤保存 9 个文件。文件名按数字序编号，便于按执行顺序查看：`00_environment.txt`（模型配置元信息，包含 API Key 掩码后四位）、`01_concept_extraction_input.txt` 和 `01_concept_extraction_output.json`（阶段1的输入输出）、`02_hierarchy_planning_input.txt` 和 `02_hierarchy_planning_output.json`（阶段2的输入输出，含有效/无效关系计数）、`03_delta_generation_input.txt` 和 `03_delta_generation_output.json`（阶段3的输入输出，含各类型操作的统计）、`04_final_map.json`（最终合并后的导图完整状态）、`05_pipeline_log.txt`（管线执行全过程的日志，含每阶段耗时、降级标记、节点/连线数量变化）。

所有文件操作以 `try/except` 包裹，任何写文件失败仅记录日志，绝不中断管线执行。`DebugOutputManager` 的生命周期与每次 `generate()` 调用绑定——管线开始时创建，管线结束时将日志写入磁盘。

除了管线内部的调试输出外，`polish_text` 工具也有独立的调试保存函数（`_debug_save_polish_iteration()` 和 `_debug_save_polish_summary()`），它们通过 `mindmap_agent.py` 中导出的 `write_debug_file()` 函数写入同一个共享调试目录。这种设计使得无论从管线还是从润色工具生成的调试文件，都可以通过相同的 `session_ts` 目录关联起来。

### 6.6 与上下游的交互

- **上游**：`mcp_server.py.modify_mind_map_v2()` 调用 `orchestrator.generate()`
- **下游**：三个 Agent 内部调用 OpenAI API（function calling）；`state_merge()` 是纯函数，无外部依赖

### 6.7 设计决策

**为什么采用三阶段管线而非单次调用？** 单模型 ReAct 需要同时处理"从对话中识别新概念"+"规划概念的层级关系"+"生成精确的坐标和颜色"三个复杂度维度。分离后：（1）概念提取仅需理解语义，可使用轻量模型降低成本；（2）层级规划仅需考虑概念之间的关系，对上下文窗口要求低；（3）Delta 生成作为最终执行者，可利用主力模型的全部能力。这种"分治策略"使得各阶段可以独立选择最合适的模型，在总成本不变的前提下提升输出质量。

**为什么阶段2（层级规划）在阶段3的 prompt 中是以"提示"而非"强制指令"形式注入？** 考虑到阶段2使用的模型可能不如阶段3强大，且层级规划可能受限于对最终导图布局的无知。作为"提示"而非强制指令，允许 Delta Agent 根据实际坐标和布局需求微调父子关系——例如将 A 的子节点 B 改为 B 的子节点 A 如果这样在视觉上更合理。

**为什么 `state_merge()` 是独立函数而非 Agent 的方法？** 因为单模型 Agent 和 Delta Agent 都需要相同的合并逻辑。独立函数确保了行为一致性，也便于单元测试——可直接构造 delta 测试合并结果，无需 mock LLM 调用。

---

## 7. 工具定义层 (tools.py)

**文件**: `/home/akku/ai-mindmap-agent/tools.py`

### 7.1 职责

`tools.py` 集中管理所有用于 LLM function calling 的 JSON Schema 定义。这些 Schema 作为 `tools` 参数传入 OpenAI API，约束 LLM 输出的结构。三个工具函数分别服务于不同的 Agent 阶段。

### 7.2 三个工具 Schema 的详细结构

**`get_mindmap_tools()`**：占用约 70 行代码，定义了 `modify_mind_map` 工具的完整 JSON Schema。它包含四个顶级数组属性：`add_nodes`（每个节点必须提供 id、label、color、x、y 五个必填字段，details 数组可选，label 有严格的「核心名词/短语，最多 2 词」约束）、`update_nodes`（只需 id 和 append_details 两个字段，专为已有节点追加详情设计）、`add_links`（source、target 为字符串 ID，type 从 solid/dashed 中枚举选择）、`delete_nodes`（简单的字符串数组）。

这个 Schema 是整个绘图系统的核心契约——它既约束了 LLM 的输出结构，也直接映射到 `state_merge()` 函数的输入参数。Schema 的稳定性直接决定了前后端的兼容性。

**`get_concept_extraction_tools()`**：定义了 `extract_concepts` 工具，结构比绘图工具简单得多——只有一个 `concepts` 数组属性。每个概念只需四个字段（id、label、details、color），其中 details 是可选的（默认空数组）。没有坐标或连线信息，因为概念提取阶段不关心布局和关系。

**`get_hierarchy_planning_tools()`**：定义了 `plan_hierarchy` 工具，只有一个 `relations` 数组属性。每个关系包含三个必填字段：`parent_id`（父节点 ID）、`child_id`（子节点 ID）、`type`（枚举 solid/dashed），分别表示层级中的父子关系和连接类型。

### 7.3 与上下游的交互

- **上游**：`_BaseAgent._call_llm_tool()` 将这些 Schema 作为 OpenAI API 的 `tools` 参数传递
- **下游**：LLM 的输出 JSON 必须严格匹配这些 Schema，`tool_choice="forced"` 确保 LLM 一定会调用工具

### 7.4 设计决策

**为什么三个工具 Schema 要拆分为三个独立函数而非一个导出所有工具的字典？** 每个 Agent 只需要自己相关的工具。概念提取 Agent 不需要知道连线类型或坐标，规划 Agent 不需要知道节点颜色。拆分为独立函数使得 Agent 的初始化代码自文档化——`self.tools = get_mindmap_tools()` 直接说明了这个 Agent 能做什么。而且 Schema 定义长达 70 行，若合并在一个字典中，Agent 初始化时将不必要地加载所有 Schema，增加理解和维护成本。

**为什么 `modify_mind_map` 工具选择 `forced` 而非 `auto` 模式？** 在绘图场景中，LLM 输出完整的增量指令比由 LLM 决定"是否画图"更可预测。`forced` 模式确保了每个调用都能得到结构化的 delta 输出；绘图与否的逻辑（即"什么时候需要画图"）由编排器在调用前通过上下文构建控制。如果将这个决策权交给 LLM 的 `auto` 模式，当 LLM 判断不需要绘图时就不会调用工具，编排器将无法区分"不需要绘图"和"LLM 出错未调用工具"两种情况，导致降级策略无法正常工作。

---

## 8. 多模型协作与优雅降级

### 8.1 降级全景

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    mcp_server.py _init_models()                       │
│                                                                      │
│  CONCEPT_MODEL set? ──Yes──→ ConceptExtractionAgent(专用模型)        │
│       │                                                              │
│       No                                                             │
│       └─────────────→ ConceptExtractionAgent(LLM_MODEL)              │
│                                                                      │
│  HIERARCHY_MODEL set? ──Yes──→ HierarchyPlanningAgent(专用模型)       │
│       │                                                              │
│       No                                                             │
│       └─────────────→ HierarchyPlanningAgent(LLM_MODEL)              │
│                                                                      │
│  DELTA_MODEL ──→ DeltaGenerationAgent(始终配置, 默认 LLM_MODEL)      │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              MindMapPipelineOrchestrator.generate()                   │
│                                                                      │
│  ┌─ concept_agent is None? ──Yes──→ [A] 降级到单模型 ReAct           │
│  │                                                                   │
│  ├─ 阶段1: 概念提取                                                  │
│  │  ├─ 成功 → 进入阶段2                                             │
│  │  ├─ 异常 → [B] 降级到单模型 ReAct                                │
│  │  └─ 0 概念 → [C] 降级到单模型 ReAct                              │
│  │                                                                   │
│  ├─ 阶段2: 层级规划                                                 │
│  │  ├─ hierarchy_agent is None? → 跳过阶段2                         │
│  │  ├─ 成功 → 阶段3接收(概念+层级)全量注入                          │
│  │  └─ 异常 → [E] 跳过阶段2，阶段3仅概念提示                        │
│  │                                                                   │
│  └─ 阶段3: Delta 生成                                               │
│     ├─ 成功 → 返回 merged_map                                       │
│     └─ 异常 → [D] 返回原图                                          │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.2 所有降级触发器

| 降级点 | 触发条件 | 行为 | 日志标记 |
|--------|---------|------|---------|
| **A** | `concept_agent is None` | 调用 `legacy_agent` 单模型 ReAct | `Concept model not configured → degrade to single-model ReAct` |
| **B** | 阶段1 抛出异常 | 调用 `legacy_agent` 单模型 ReAct | `Stage 1 error: ... → degrade to single-model ReAct` |
| **C** | 阶段1 提取到 0 个概念 | 调用 `legacy_agent` 单模型 ReAct | `Stage 1 found no new concepts → degrade to single-model ReAct` |
| **D** | 阶段3 抛出异常 | 返回原始 `current_map` | `Stage 3 error ... → return original map` |
| **E** | 阶段2 异常 | `hierarchy=None`，阶段3仅接收概念 | `Stage 2 error ... → skip hierarchy, continue to stage 3` |
| **F** | `hierarchy_agent is None` | 跳过阶段2，阶段3仅概念提示 | `Hierarchy model not configured → skip stage 2` |

### 8.3 润色降级链

润色任务有两条并行执行路径，由配置中的 `POLISH_MODEL` 是否设置决定。

**路径一（主力直润）**：`polish_client` 为 `None` 时触发。这是零额外开销的降级路径：直接使用主力模型（与 chat_generate 使用相同的 `llm_client` 和 `Config.LLM_MODEL`）以低温度 `0.2` 执行单次润色调用。system prompt 根据 `detected_language` 自动选择中文或英文版本，要求修复错别字、添加标点和去除语气填充词。

**路径二（混合审查）**：`polish_client` 已配置时触发。这条路径包含四个失败降级点：迭代收敛提前终止（编辑距离比率 < 0.05，非失败而是效率优化）、终审 ACCEPT（无降级，返回候选）、终审 FIX（轻微降级，返回主力修正文本，confidence=medium）、终审 REJECT（完全降级，返回原始转录文本，confidence=low，附带 reason 说明）。此外，若主力模型的终审输出无法解析为任何已知格式，安全降级为 ACCEPT 状态。

终审裁决在 `mcp_server.py` 内部通过一个专门的 `_judge_by_main_model()` 函数完成，该函数使用 `temperature=0.0` 和 `max_tokens=1024` 调用主力模型，然后通过字符串前缀匹配（`startswith("ACCEPT")`、`startswith("FIX:")`、`startswith("REJECT:")`）解析裁决结果。需要注意的是，终审的 system prompt 中包含原始转录文本和候选文本两者，要求主力模型同时执行「评估」和「修复」两个任务——这种双重角色的设计减少了额外的 API 调用。

### 8.4 设计决策

**为什么降级链要从概念提取 Agent 的存在性（A）和提取结果（C）两个维度分别判断？** 存在性判断在管线编排器构造时即可做出（构件级降级），而结果判断需要在运行时做出（运行时降级）。前者避免了不必要的模型调用（如果连概念提取 Agent 都没有，管线根本不应启动）；后者则处理"模型可用但对话中确实没有新概念"的场景——此时直接让单模型 ReAct 全权处理，可能比强制使用空概念列表传入阶段3更合理。

**为什么阶段2的降级是"跳过"而非"兜底到单模型"？** 因为阶段2负责的是结构优化而非核心内容。概念已经由阶段1提取，层次关系可以由阶段3的 Delta Agent 在生成 delta 时自行推理（Delta Agent 本身就是一个完整的单模型 ReAct Agent）。跳过阶段2意味着阶段3需要做更多推理，但输出质量不会出现断崖式下降。

**为什么在润色工具中设计了完整的置信度标记体系？** 返回的 `polished_text` 附带 `confidence` 字段（high/medium/low），这为前端提供了决策依据：高置信度的结果可以直接自动填充到聊天输入框；中置信度的结果可以带一个"建议修正"标注展示；低置信度的结果可以降级到仅展示原始转录文本并提示用户自行修改。前端还可以将这些置信度信息聚合为"润色质量仪表盘"，帮助用户决定是否需要手动审查。

---

## 9. 端到端数据流全景

### 9.1 纯文本聊天 + 导图更新

最常用的交互路径。用户在前端聊天框中输入文本，系统同时返回聊天回复和更新后的导图。

```text
用户: POST /chat {"message": "Tell me about ML", "current_map": {...}, "transcript_context": null}

main.py:
  1. session_memory 追加用户消息
  2. 构建最近5轮对话上下文（含可选的转录上下文）
  3. call_tool("chat_generate", {messages: [...]})
     └─ mcp_server: llm_client 对话 → 返回 {"reply_text": "ML is..."}
  4. _validate_chat_reply 检验 → 返回纯文本
  5. session_memory 追加 AI 回复
  6. 构建 formatted_history（用户消息 + 可选转录 + AI 回复）
  7. call_tool("modify_mind_map_v2", {chat_history, current_map, session_ts})
     └─ mcp_server: map_pipeline.generate()
        ├─ 阶段1: ConceptExtractionAgent.extract() → 提取新概念
        ├─ 阶段2: HierarchyPlanningAgent.plan() → 规划层级
        └─ 阶段3: DeltaGenerationAgent.generate() → 输出 delta → state_merge
     └─ 返回 final_map
  8. _validate_map 检验 → 返回导图 dict
  9. 异步保存调试导图
  10. 返回 {"answer": "ML is...", "map": {"nodes": [...], "links": [...]}}
```

关键观察：第3步和第7步都使用了 `_call_tool_with_retry`，但使用不同的验证函数。如果 `chat_generate` 连续失败（例如 LLM API 故障），`_validate_chat_reply` 的降级消息会作为 AI 回复继续流程——这意味着即使用户消息未能得到 AI 响应，导图更新仍然会尝试执行（因为降级消息也包含了用户的原始问题作为上下文）。这种设计确保了单点故障不会阻断整个链路。

### 9.2 音频上传 + 转录 + 润色 + 导图更新

带语音输入的完整链路。音频经过 Whisper 转写和文字润色后，前端将其作为转录上下文与随后的聊天消息一起发送，触发导图更新。

```text
用户: POST /upload_audio (multipart, field="file")

main.py:
  1. 保存上传文件到临时路径 /tmp/tmpXXXXX.wav
  2. call_tool("transcribe_audio", {file_path: tmp_path})
     └─ mcp_server: whisper_model.transcribe() → raw_text + detected_language
  3. _validate_transcribe 检验 → raw_text 非空则继续
  4. call_tool("polish_text", {raw_text, detected_language, session_ts})
     └─ mcp_server: 混合审查模式
        ├─ 轻量迭代 N 次 → 收敛提前停止
        └─ 主力终审 → ACCEPT/FIX/REJECT
  5. _validate_polish 检验 → 返回 polished_text
  6. 清理临时文件
  7. 返回 {"status":"success", "raw_text":..., "polished_text":..., "detected_language":...}
  ──→ 前端将 polished_text 作为 transcript_context 传入后续 POST /chat
```

上传流程与聊天流程通过 `transcript_context` 字段连接：音频处理接口返回润色文本，前端在界面上展示给用户确认，然后在用户发起下一次聊天消息时，将确认（或修改后）的文本作为 `transcript_context` 传入。这种设计允许用户在人机循环（Human-in-the-loop）中修正转写错误，然后再进入导图生成流程。

### 9.3 关键设计模式总结

以下表格总结了系统中使用的七个关键设计模式及其落地位置。这些模式共同构成了系统的架构骨架，每个模式解决了一个特定的松耦合或扩展性问题。

| 模式 | 体现位置 | 说明 |
|------|---------|------|
| **桥接** | main.py ↔ mcp_client.py ↔ mcp_server.py | HTTP 编排层与 LLM 执行层通过 MCP stdio 桥接，双方可独立演进，互不影响 |
| **策略** | PipelineOrchestrator 的 Agent 替换 | 概念提取/层级规划可配置不同模型、不同 API 端点，甚至可跳过某个阶段。只需传入不同的 Agent 实例即可切换策略 |
| **模板方法** | `_BaseAgent._call_llm_tool()` | 定义 function calling 通用流程（system prompt + user prompt → forced tool call → JSON 解析），子类通过不同的 tools/prompt 定制行为 |
| **责任链** | 三阶段管线 | 每阶段处理结果传递给下一阶段，失败时可以选择跳过当前阶段或降级到兜底方案 |
| **装饰器** | `_call_tool_with_retry()` | 围绕原始 MCP 调用包裹 验证+重试+降级 能力，被调用方无需修改原始调用逻辑 |
| **单例** | MCP Client / Whisper 模型 / LLM Client | 进程内全局唯一实例，避免重复初始化带来的资源浪费和状态不一致问题 |
| **纯函数** | `state_merge()` | 给定相同 delta + current_map，始终返回相同结果。无副作用，便于单元测试和结果确定性验证 |

### 9.4 边界场景与系统行为

| 场景 | 预期行为 |
|------|---------|
| 音频文件格式不支持 | Whisper 内部抛出异常 → `transcribe_audio` 透传给编排器 → `_call_tool_with_retry` 重试耗尽 → `_validate_transcribe` 返回空文本 → 返回空结果 |
| 导图已有 200+ 节点 | LLM 上下文窗口可能不足 → `state_merge` 仍可正确合并 delta（纯数据操作无 LLM 调用）→ 下次需要更新的概念可能无法被上下文覆盖 → 节点管理受限 |
| 连续发送无新概念的消息（如"继续"） | 阶段1 提取 0 个概念 → 降级到单模型 ReAct → single-model 也无法提取概念 → 返回原图 |
| MCP Server 崩溃 | `mcp_client.call_tool()` 抛出异常 → `_call_tool_with_retry` 重试（此时子进程已终止）→ 重试耗尽 → 返回降级值。`lifespan` 关闭时可检测到异常状态 |
| 主力 LLM API 限流 | `chat_generate` 返回限流错误 → 重试（可能成功）→ 重试耗尽 → 返回降级回复 `"服务暂时不可用"` |

---

> **文档类型**: 架构设计文档（非代码注释文档）  
> **覆盖文件**: main.py / mcp_client.py / mcp_server.py / mindmap_agent.py / config.py / tools.py / schema.py  
> **生成日期**: 2026-06-17

## 附录：关键包与库依赖

| 包 | 用途 | 关键使用位置 |
|------|------|-------------|
| `mcp`（>=1.0.0） | MCP 协议客户端、会话管理、stdio_client | mcp_client.py |
| `mcp[fastmcp]` | FastMCP 服务器框架（@mcp.tool 装饰器） | mcp_server.py |
| `openai` | OpenAI API 客户端（function calling, chat completions） | mindmap_agent.py, mcp_server.py |
| `whisper` | OpenAI Whisper 本地语音转文字模型 | mcp_server.py（transcribe_audio） |
| `fastapi` + `uvicorn` | ASGI Web 框架与 HTTP 服务器 | main.py |
| `pydantic` | 数据模型定义与请求体验证（BaseModel） | schema.py, main.py |
| `python-dotenv` | 从 .env 文件加载环境变量 | config.py |

> **版本提示**: 项目要求 Python ≥ 3.10，依赖 `mcp>=1.0.0`。Whisper `small` 模型首次启动时自动下载（约 500MB）。本地运行无需 GPU，但 Whisper 转写会在 CPU 上耗时 2~10 秒。
>
> 完整依赖列表见 `requirements.txt`。
