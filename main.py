from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
import logging
import tempfile
from datetime import datetime

from config import Config
from mcp_client import MCPMindMapClient  # C: MCP Client 封装 / E: MCP Client wrapper

# C: MCP Client 全局实例（在 lifespan 中启动）
# E: MCP Client global instance (started in lifespan)
mcp_client: MCPMindMapClient | None = None

# C: 配置日志
# E: Configure logging
logging.basicConfig(level=logging.INFO, format="[Orchestrator] %(levelname)s %(message)s")
logger = logging.getLogger("orchestrator")

MAX_RETRIES = 1  # C: 工具调用失败时的最大重试次数 / E: Max retries on tool call failure

# =========================================================
# C: 结果验证层 — 纯编排器逻辑
#    对每个 MCP 工具返回进行结构校验，不通过则降级或重试
# E: Result validation layer — pure orchestrator logic
#    Validates structure of each MCP tool result, degrades or retries on failure
# =========================================================

def _validate_chat_reply(result: dict) -> tuple[bool, str]:
    """C: 验证 chat_generate 返回。返回 (是否通过, reply_text)。
    E: Validate chat_generate result. Returns (passed, reply_text)."""
    if not isinstance(result, dict):
        logger.warning("C: [Validate] chat_generate 返回类型错误")
        logger.warning("E: [Validate] chat_generate returned wrong type")
        return False, "C: 抱歉，服务暂时不可用。\nE: Sorry, service is temporarily unavailable."
    reply = result.get("reply_text", "")
    if not reply or not isinstance(reply, str):
        logger.warning("C: [Validate] chat_generate reply_text 为空或无效")
        logger.warning("E: [Validate] chat_generate reply_text empty or invalid")
        return False, "C: 抱歉，无法生成回复。\nE: Sorry, unable to generate a reply."
    return True, reply


def _validate_map(result: dict) -> tuple[bool, dict]:
    """C: 验证 modify_mind_map 返回。返回 (是否通过, map_dict)。
    E: Validate modify_mind_map result. Returns (passed, map_dict)."""
    fallback = {"tree": [], "nodes": [], "links": []}
    if not isinstance(result, dict):
        logger.warning("C: [Validate] modify_mind_map 返回类型错误")
        logger.warning("E: [Validate] modify_mind_map returned wrong type")
        return False, fallback
    if "nodes" not in result or "links" not in result:
        logger.warning("C: [Validate] modify_mind_map 缺少 nodes/links 字段")
        logger.warning("E: [Validate] modify_mind_map missing nodes/links")
        return False, fallback
    if not isinstance(result["nodes"], list) or not isinstance(result["links"], list):
        logger.warning("C: [Validate] modify_mind_map nodes/links 类型错误")
        logger.warning("E: [Validate] modify_mind_map nodes/links wrong type")
        return False, fallback
    # C: tree 字段可选（向后兼容），不存在时补空列表
    # E: tree field optional (backward compat), fill empty list if missing
    if "tree" not in result:
        result["tree"] = []
    return True, result


def _validate_transcribe(result: dict) -> tuple[bool, dict]:
    """C: 验证 transcribe_audio 返回。返回 (是否通过, transcribe_dict)。
    E: Validate transcribe_audio result. Returns (passed, transcribe_dict)."""
    fallback = {"raw_text": "", "detected_language": "en"}
    if not isinstance(result, dict):
        logger.warning("C: [Validate] transcribe_audio 返回类型错误")
        logger.warning("E: [Validate] transcribe_audio returned wrong type")
        return False, fallback
    return True, result


def _validate_polish(result: dict) -> tuple[bool, dict]:
    """C: 验证 polish_text 返回。返回 (是否通过, polish_dict)。
    E: Validate polish_text result. Returns (passed, polish_dict)."""
    fallback = {"polished_text": ""}
    if not isinstance(result, dict):
        logger.warning("C: [Validate] polish_text 返回类型错误")
        logger.warning("E: [Validate] polish_text returned wrong type")
        return False, fallback
    if "polished_text" not in result:
        logger.warning("C: [Validate] polish_text 缺少 polished_text 字段")
        logger.warning("E: [Validate] polish_text missing polished_text")
        return False, fallback
    return True, result


async def _call_tool_with_retry(tool_name: str, arguments: dict, validator, max_retries: int = MAX_RETRIES):
    """C: 带验证和重试的工具调用封装。
    调用 MCP 工具 → 验证结果 → 不通过则重试 → 仍失败则返回降级值。
    E: Tool call wrapper with validation and retry.
    Calls MCP tool → validates result → retries on failure → returns degraded on exhaustion.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.warning(
                    f"C: [Retry] 重试 {tool_name} (第 {attempt}/{max_retries} 次)"
                )
                logger.warning(
                    f"E: [Retry] Retrying {tool_name} (attempt {attempt}/{max_retries})"
                )
            raw_result = await mcp_client.call_tool(tool_name, arguments)
            passed, result = validator(raw_result)
            if passed:
                if attempt > 0:
                    logger.info(f"C: [Retry] {tool_name} 重试成功")
                    logger.info(f"E: [Retry] {tool_name} retry succeeded")
                return result
            last_error = f"validation failed: {result}"
        except Exception as e:
            last_error = str(e)
            logger.error(f"C: [Retry] {tool_name} 调用异常 (尝试 {attempt}): {e}")
            logger.error(f"E: [Retry] {tool_name} call error (attempt {attempt}): {e}")
    
    # C: 重试耗尽，使用降级值
    # E: Retries exhausted, use degraded value
    logger.error(f"C: [Degrade] {tool_name} 所有重试失败: {last_error}")
    logger.error(f"E: [Degrade] {tool_name} all retries failed: {last_error}")
    # C: 返回 validator 的 fallback（通过一次假调用获取）
    # E: Return validator's fallback (obtained via a dummy call)
    _, degraded = validator({})
    return degraded


# C: 在内存中维护一下近期的对话上下文（简单版 Memory）
# E: Maintain recent conversation context in memory (simple version of Memory)
session_memory = []


# ---------------------------------------------------------
# C: FastAPI Lifespan — 管理 MCP Client 生命周期
#    使用 `async with` 模式：start / close 严格在同一个 asyncio task 中，
#    避免 anyio cancel scope 跨 task 报错。
# E: FastAPI Lifespan — manage MCP Client lifecycle
#    Use `async with` so start/close strictly run in the same asyncio task,
#    preventing anyio cancel-scope cross-task errors.
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_client
    logger.info("C: 正在启动 MCP Client（连接 MCP Server 子进程）...")
    logger.info("E: Starting MCP Client (connecting to MCP Server subprocess)...")

    # C: 必须在 `async with` 中启动，保证 enter / exit 在同一 task
    # E: Must start inside `async with` so enter/exit run in the same task
    client = MCPMindMapClient(Config.MCP_SERVER_SCRIPT)
    try:
        await client.start()
    except Exception as e:
        # C: 启动失败时保证全局变量是 None，避免后续请求误用
        # E: On startup failure, ensure global is None to prevent misuse
        logger.error(f"C: MCP Client 启动失败: {e}")
        logger.error(f"E: MCP Client startup failed: {e}")
        mcp_client = None
        raise
    else:
        mcp_client = client
        logger.info("C: MCP Client 就绪，服务启动完成")
        logger.info("E: MCP Client ready, server startup complete")
        try:
            yield
        finally:
            # C: close() 与 start() 在同一个 lifespan task 中执行
            # E: close() runs in the same lifespan task as start()
            try:
                if mcp_client is not None:
                    await mcp_client.close()
            except Exception as e:
                logger.error(f"C: 关闭 MCP Client 异常: {e}")
                logger.error(f"E: Error closing MCP Client: {e}")
            finally:
                mcp_client = None
                logger.info("C: MCP Client 已关闭")
                logger.info("E: MCP Client closed")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_index():
    return FileResponse('index.html')

class ChatRequest(BaseModel):
    message: str
    current_map: Optional[Dict[str, Any]] = None
    transcript_context: Optional[str] = None

@app.post("/chat")
async def handle_multimodal_chat(request: ChatRequest):
    """C: 纯编排器 — 不包含任何 LLM API 调用或业务逻辑。
    流程: 构建上下文 → MCP chat_generate → 验证 → MCP modify_mind_map_v2 → 验证 → 组装返回。
    modify_mind_map_v2 内部使用三阶段多模型管线（概念提取→层级规划→Delta生成）提升层级结构清晰度。
    E: Pure orchestrator — contains no LLM API calls or business logic.
    Flow: Build context → MCP chat_generate → validate → MCP modify_mind_map_v2 → validate → assemble response.
    modify_mind_map_v2 internally uses 3-stage multi-model pipeline (concept extraction→hierarchy planning→delta generation) for better hierarchy clarity."""
    global session_memory
    try:
        # C: 生成当前请求的会话时间戳（用于跨工具共享调试目录）
        # E: Generate session timestamp for this request (for cross-tool debug dir sharing)
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        user_msg = request.message
        current_map = request.current_map or {"nodes": [], "links": []}

        # C: 将用户的话加入记忆
        # E: Add user message to memory
        session_memory.append({"role": "user", "content": user_msg})

        # ---------------------------------------------------------
        # C: 阶段一：编排聊天上下文，调度到 MCP chat_generate 工具
        # E: Phase 1: Orchestrate chat context, dispatch to MCP chat_generate tool
        # ---------------------------------------------------------
        chat_sys_prompt = """C: 你是一个亲切的 AI 助手。我们正在一起构建一个思维导图。请回答用户的问题。
注意：你只负责聊天，另一个专业的 Agent 会负责画图，所以你不需要在对话中输出 JSON 代码。
E: You are a friendly AI assistant. We are building a mind map together. Please answer the user's questions.
Note: You are only responsible for chatting. Another professional Agent will handle drawing, so you do not need to output JSON code in the conversation.

C: 【语言规则 - 必须严格遵守】
1. 检测用户输入的语言（如 English, 中文, Deutsch, Français, Español, 日本語 等）。
2. 强制使用与用户输入完全相同的语言进行回复。
3. 如果用户使用英语，你必须用英语回复；用户使用德语，你必须用德语回复；以此类推。
4. 绝对不要将回复语言切换为其他语言，包括中文。
E: [Language Rules - Must Strictly Follow]
1. Detect the language of the user's input (e.g., English, 中文, Deutsch, Français, Español, 日本語, etc.).
2. You must reply in exactly the same language as the user's input.
3. If the user uses English, you must reply in English; if the user uses German, you must reply in German; and so on.
4. Never switch the reply language to any other language, including Chinese."""

        # C: 截取最近 5 轮对话，防止上下文过长
        # E: Truncate to the last 5 rounds to prevent context overflow
        recent_context = [{"role": "system", "content": chat_sys_prompt}] + session_memory[-5:]

        # C: 如果前端传了转录上下文，以 system 角色注入
        # E: If transcript context is provided, inject as system role
        if request.transcript_context:
            recent_context.insert(1, {
                "role": "system",
                "content": f"C: 【转录上下文 - 供参考】以下是用户提供的语音转录内容，可从中提取关键信息用于回答：\n{request.transcript_context}\n---\nE: [Transcript Context - For Reference] Below is the speech transcription provided by the user. Extract key information from it to assist in your response:\n{request.transcript_context}\n---"
            })

        # C: 通过 MCP 调用聊天生成工具（带验证+重试）
        # E: Call chat generation tool via MCP (with validation+retry)
        logger.info("C: [Orchestrator] 调度 chat_generate 任务...")
        logger.info("E: [Orchestrator] Dispatching chat_generate task...")
        ai_reply = await _call_tool_with_retry(
            "chat_generate",
            {"messages": recent_context},
            _validate_chat_reply
        )
        logger.info("C: [Orchestrator] chat_generate 完成")
        logger.info("E: [Orchestrator] chat_generate complete")

        # C: 将 AI 的回复也加入记忆
        # E: Add AI reply to memory
        session_memory.append({"role": "assistant", "content": ai_reply})

        # ---------------------------------------------------------
        # C: 阶段二：调度绘图任务到 MCP modify_mind_map 工具
        # E: Phase 2: Dispatch drawing task to MCP modify_mind_map tool
        # ---------------------------------------------------------
        # C: 构建绘图上下文 — 转录内容标记为「用户提供」，含具体概念可被画图
        # E: Build drawing context — transcript marked as "user-provided" for concept extraction
        transcript_block = ""
        if request.transcript_context:
            transcript_block = (
                f"C: 【用户提供的语音转录内容 - 请从中提取核心概念绘制导图】\n"
                f"{request.transcript_context}\n"
                f"---\n"
                f"E: [User-provided speech transcript - extract core concepts for mind map]\n"
                f"{request.transcript_context}\n"
                f"---\n"
            )

        # C: 根据 DETAILS_ENRICHMENT_ENABLED 决定 AI 回复的角色
        # E: Determine AI reply role based on DETAILS_ENRICHMENT_ENABLED
        if Config.DETAILS_ENRICHMENT_ENABLED:
            ai_reply_marker_cn = (
                "C: 【概念补充来源 - 请将AI回复中与各概念相关的定义、解释、关键点、"
                "举例等，按条目化方式追加到对应节点的 details 数组中。"
                "每条建议以简洁前缀标识来源（如 '定义:'、'关键点:'、'上下文:'），前缀文本语言与用户输入语言一致。"
                "禁止将AI的分析逻辑创建为独立节点】AI回复说："
            )
            ai_reply_marker_en = (
                "E: [Concept Enrichment Source - Extract definitions, explanations, key points, "
                "and examples related to each concept from the AI reply, and append them as "
                "structured entries to the corresponding node's details array. "
                "Prefix each entry with a concise source tag (e.g., 'Definition:', "
                "'Key Point:', 'Context:'), and the tag language must match the user's input language. "
                "Do NOT create standalone nodes from AI's analytical logic] AI replied: "
            )
        else:
            ai_reply_marker_cn = (
                "C: 【仅供参考的聊天记录，禁止将其中的逻辑分析画入导图】AI回复说："
            )
            ai_reply_marker_en = (
                "E: [Chat log for reference only, do not draw its logical analysis into the mind map] AI replied: "
            )

        formatted_history = (
            transcript_block +
            f"C: 【最高优先级指令】用户说：{user_msg}\n"
            f"E: [Highest Priority Instruction] User says: {user_msg}\n"
            f"{ai_reply_marker_cn}{ai_reply}\n"
            f"{ai_reply_marker_en}{ai_reply}"
        )

        logger.info("C: [Orchestrator] 调度 modify_mind_map_v2 任务...")
        logger.info("E: [Orchestrator] Dispatching modify_mind_map_v2 task...")
        updated_map = await _call_tool_with_retry(
            "modify_mind_map_v2",
            {"chat_history": formatted_history, "current_map": current_map,
             "session_ts": session_ts},
            _validate_map
        )
        logger.info("C: [Orchestrator] modify_mind_map_v2 完成")
        logger.info("E: [Orchestrator] modify_mind_map_v2 complete")

        # ---------------------------------------------------------
        # C: 阶段三：质量验收通过，组装结果返回
        # E: Phase 3: Quality check passed, assemble and return
        # ---------------------------------------------------------
        return {
            "answer": ai_reply,
            "map": updated_map
        }

    except Exception as e:
        logger.error(f"C: 系统运行错误: {e}")
        logger.error(f"E: System runtime error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# C: 音频上传 + MCP Whisper STT + MCP LLM 润色 路由
# E: Audio upload + MCP Whisper STT + MCP LLM polishing route
# ---------------------------------------------------------
@app.post("/upload_audio")
async def handle_audio_upload(file: UploadFile = File(...)):
    """C: 纯编排器 — 文件保存后全部通过 MCP 工具链处理，含验证。
    流程: 保存临时文件 → MCP transcribe_audio → 验证 → MCP polish_text → 验证 → 组装返回。
    E: Pure orchestrator — after file save, everything via MCP toolchain with validation.
    Flow: Save temp file → MCP transcribe_audio → validate → MCP polish_text → validate → assemble response."""
    # C: 先初始化 tmp_path = None，避免 file.read() 失败时 finally 触发 NameError
    # E: Initialize tmp_path = None first, to avoid NameError in finally if file.read() raises
    tmp_path = None
    try:
        # C: 1. 安全保存临时文件
        # E: 1. Safely save temporary file
        suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # C: 生成当前请求的会话时间戳（用于跨工具共享调试目录）
        # E: Generate session timestamp for this request (for cross-tool debug dir sharing)
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # C: 2. 通过 MCP 调用 Whisper 转录（带验证+重试）
        # E: 2. Call Whisper transcription via MCP (with validation+retry)
        logger.info("C: [Orchestrator] 调度 transcribe_audio 任务...")
        logger.info("E: [Orchestrator] Dispatching transcribe_audio task...")
        transcribe_result = await _call_tool_with_retry(
            "transcribe_audio",
            {"file_path": tmp_path},
            _validate_transcribe
        )
        raw_text = transcribe_result.get("raw_text", "").strip()
        detected_lang = transcribe_result.get("detected_language", "en")
        logger.info("C: [Orchestrator] transcribe_audio 完成")
        logger.info("E: [Orchestrator] transcribe_audio complete")

        if not raw_text:
            return {"status": "success", "raw_text": "", "polished_text": "", "detected_language": detected_lang}

        # C: 3. 通过 MCP 调用 LLM 润色（带验证+重试）
        # E: 3. Call LLM polishing via MCP (with validation+retry)
        logger.info("C: [Orchestrator] 调度 polish_text 任务...")
        logger.info("E: [Orchestrator] Dispatching polish_text task...")
        polish_result = await _call_tool_with_retry(
            "polish_text",
            {"raw_text": raw_text, "detected_language": detected_lang,
             "session_ts": session_ts},
            _validate_polish
        )
        polished_text = polish_result.get("polished_text", "")
        logger.info("C: [Orchestrator] polish_text 完成")
        logger.info("E: [Orchestrator] polish_text complete")

        return {
            "status": "success",
            "raw_text": raw_text,
            "polished_text": polished_text,
            "detected_language": detected_lang
        }
    except Exception as e:
        logger.error(f"C: [Whisper] 处理出错: {e}")
        logger.error(f"E: [Whisper] Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
    finally:
        # C: 安全清理临时文件 — 容忍文件被占用或已删除的情况
        # E: Safely clean up temp file — tolerate file-locked or already-deleted cases
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as e:
                logger.warning(f"C: 清理临时文件失败 {tmp_path}: {e}")
                logger.warning(f"E: Failed to remove temp file {tmp_path}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
