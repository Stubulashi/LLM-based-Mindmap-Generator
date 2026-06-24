# /home/akku/ai-mindmap-agent/mcp_server.py
# C: MCP Server — 将 LLM 聊天/润色/绘图、Whisper 转录封装为 MCP Tools
# E: MCP Server — encapsulates LLM chat/polish/drawing and Whisper transcription as MCP Tools
import os
import sys
import logging
from datetime import datetime

import whisper
from openai import OpenAI

from mcp.server.fastmcp import FastMCP

from config import Config
from mindmap_agent import (
    MindMapSpecialistAgent,
    ConceptExtractionAgent,
    HierarchyPlanningAgent,
    DeltaGenerationAgent,
    MindMapPipelineOrchestrator,
    write_debug_file,
)

# C: 日志输出到 stderr，避免污染 stdio 协议通道
# E: Log to stderr to avoid polluting the stdio protocol channel
logging.basicConfig(
    level=logging.INFO,
    format="[MCP-Server] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp-server")

# C: 创建 MCP Server 实例
# E: Create MCP Server instance
mcp = FastMCP(
    name="mindmap-mcp-server",
    instructions="C: 思维导图 MCP Server — 提供聊天生成、音频转录、文本润色、增量绘图四大工具\nE: Mind Map MCP Server — provides chat generation, audio transcription, text polishing, and incremental drawing tools",
)

# ---------------------------------------------------------
# C: 全局模型初始化（启动时加载一次）
# E: Global model initialization (loaded once at startup)
# ---------------------------------------------------------
whisper_model = None
llm_client = None
polish_client = None  # C: 润色专用轻量客户端（None = 未配置，使用主力模型） / E: Polish lightweight client (None=not configured, use main model)
map_agent = None
map_pipeline = None  # C: 多模型管线编排器（None = 未初始化） / E: Multi-model pipeline orchestrator (None=not initialized)


def _init_models():
    global whisper_model, llm_client, polish_client, map_agent, map_pipeline
    logger.info("C: 正在加载 Whisper 模型 (small)...")
    logger.info("E: Loading Whisper model (small)...")
    whisper_model = whisper.load_model("small")
    logger.info(
        f"C: Whisper 就绪，运行设备: {next(whisper_model.parameters()).device}"
    )
    logger.info(
        f"E: Whisper ready on device: {next(whisper_model.parameters()).device}"
    )

    # C: 初始化 LLM 客户端（兼容 OpenAI API 的任意提供商）
    # E: Initialize LLM client (compatible with any OpenAI API provider)
    llm_client = OpenAI(
        api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL
    )
    logger.info(f"C: LLM 客户端就绪，模型={Config.LLM_MODEL}")
    logger.info(f"E: LLM client ready, model={Config.LLM_MODEL}")

    # C: 如果配置了独立润色模型，创建轻量客户端
    # E: If separate polish model configured, create lightweight client
    if Config.POLISH_MODEL:
        polish_client = OpenAI(
            api_key=Config.POLISH_API_KEY,
            base_url=Config.POLISH_BASE_URL
        )
        logger.info(
            f"C: 润色轻量客户端就绪，模型={Config.POLISH_MODEL}，迭代次数={Config.POLISH_ITERATIONS}"
        )
        logger.info(
            f"E: Polish lightweight client ready, model={Config.POLISH_MODEL}, iterations={Config.POLISH_ITERATIONS}"
        )
    else:
        logger.info("C: 未配置 POLISH_MODEL，润色将直接使用主力模型")
        logger.info("E: POLISH_MODEL not set, polish will use main model directly")

    # C: 初始化绘图 Agent（复用现有 State Merge 逻辑）
    # E: Initialize drawing Agent (reuse existing State Merge logic)
    map_agent = MindMapSpecialistAgent()

    # ---------------------------------------------------------
    # C: 初始化多模型管线（三阶段协作导图生成）
    #    所有模型均可独立配置，未配置时自动降级为单模型 ReAct。
    #    - 阶段1 概念提取: CONCEPT_MODEL（轻量）
    #    - 阶段2 层级规划: HIERARCHY_MODEL（中等）
    #    - 阶段3 Delta生成: DELTA_MODEL（主力）
    # E: Initialize multi-model pipeline (3-stage collaborative map generation)
    #    All models independently configurable, auto-degrade to single-model ReAct when not set.
    #    - Stage 1 concept extraction: CONCEPT_MODEL (lightweight)
    #    - Stage 2 hierarchy planning: HIERARCHY_MODEL (medium)
    #    - Stage 3 delta generation: DELTA_MODEL (main)
    # ---------------------------------------------------------

    # C: 阶段1 — 概念提取 Agent（None = 未配置，管线会降级到 legacy）
    # E: Stage 1 — Concept extraction agent (None = not configured, pipeline degrades to legacy)
    concept_agent = None
    if Config.CONCEPT_MODEL:
        concept_agent = ConceptExtractionAgent(
            api_key=Config.CONCEPT_API_KEY,
            base_url=Config.CONCEPT_BASE_URL,
            model=Config.CONCEPT_MODEL
        )
        logger.info(f"C: 概念提取 Agent 就绪，模型={Config.CONCEPT_MODEL}")
        logger.info(f"E: Concept extraction agent ready, model={Config.CONCEPT_MODEL}")
    else:
        concept_model_name = Config.LLM_MODEL
        concept_agent = ConceptExtractionAgent(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            model=concept_model_name
        )
        logger.info(
            f"C: 未配置 CONCEPT_MODEL，概念提取使用主力模型={concept_model_name}"
        )
        logger.info(
            f"E: CONCEPT_MODEL not set, concept extraction uses main model={concept_model_name}"
        )

    # C: 阶段2 — 层级规划 Agent（None = 跳过阶段2）
    # E: Stage 2 — Hierarchy planning agent (None = skip stage 2)
    hierarchy_agent = None
    if Config.HIERARCHY_MODEL:
        hierarchy_agent = HierarchyPlanningAgent(
            api_key=Config.HIERARCHY_API_KEY,
            base_url=Config.HIERARCHY_BASE_URL,
            model=Config.HIERARCHY_MODEL
        )
        logger.info(f"C: 层级规划 Agent 就绪，模型={Config.HIERARCHY_MODEL}")
        logger.info(f"E: Hierarchy planning agent ready, model={Config.HIERARCHY_MODEL}")
    else:
        hierarchy_model_name = Config.LLM_MODEL
        hierarchy_agent = HierarchyPlanningAgent(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            model=hierarchy_model_name
        )
        logger.info(
            f"C: 未配置 HIERARCHY_MODEL，层级规划使用主力模型={hierarchy_model_name}"
        )
        logger.info(
            f"E: HIERARCHY_MODEL not set, hierarchy planning uses main model={hierarchy_model_name}"
        )

    # C: 阶段3 — Delta 生成 Agent（始终配置，默认复用主力模型）
    # E: Stage 3 — Delta generation agent (always configured, defaults to main model)
    delta_agent = DeltaGenerationAgent(
        api_key=Config.DELTA_API_KEY,
        base_url=Config.DELTA_BASE_URL,
        model=Config.DELTA_MODEL
    )
    logger.info(f"C: Delta 生成 Agent 就绪，模型={Config.DELTA_MODEL}")
    logger.info(f"E: Delta generation agent ready, model={Config.DELTA_MODEL}")

    # C: 组装管线编排器
    # E: Assemble pipeline orchestrator
    map_pipeline = MindMapPipelineOrchestrator(
        concept_agent=concept_agent,
        hierarchy_agent=hierarchy_agent,
        delta_agent=delta_agent,
        legacy_agent=map_agent
    )
    logger.info("C: 多模型导图管线编排器就绪")
    logger.info("E: Multi-model map pipeline orchestrator ready")

    logger.info("C: MCP Server 模型全部就绪")
    logger.info("E: MCP Server all models ready")


# ---------------------------------------------------------
# C: MCP Tool 0: 对话生成 (LLM Chat)
# E: MCP Tool 0: Chat generation (LLM Chat)
# ---------------------------------------------------------
@mcp.tool()
def chat_generate(messages: list) -> dict:
    """C: 使用 LLM 模型进行对话生成。接收完整的 messages 列表（含 system prompt 和历史），返回 AI 回复。
    参数 messages: OpenAI 格式的消息列表 [{"role": "system|user|assistant", "content": "..."}, ...]。
    返回: {"reply_text": "AI 的回复文本"}
    E: Generate conversational reply using LLM model. Receives complete messages list (with system prompt and history), returns AI reply.
    Args messages: OpenAI-format message list [{"role": "system|user|assistant", "content": "..."}, ...].
    Returns: {"reply_text": "AI reply text"}
    """
    logger.info(
        f"C: [chat_generate] 收到 {len(messages)} 条消息，模型={Config.LLM_MODEL}"
    )
    logger.info(
        f"E: [chat_generate] Received {len(messages)} messages, model={Config.LLM_MODEL}"
    )

    response = llm_client.chat.completions.create(
        model=Config.LLM_MODEL,
        messages=messages
    )
    reply_text = response.choices[0].message.content

    logger.info(
        f"C: [chat_generate] 回复长度={len(reply_text)}"
    )
    logger.info(
        f"E: [chat_generate] Reply len={len(reply_text)}"
    )

    return {"reply_text": reply_text}


# ---------------------------------------------------------
# C: MCP Tool 1: 音频转录 (Whisper STT)
# E: MCP Tool 1: Audio transcription (Whisper STT)
# ---------------------------------------------------------
@mcp.tool()
def transcribe_audio(file_path: str) -> dict:
    """C: 使用 Whisper 模型将音频文件转录为文本，自动检测语言。
    参数 file_path: 音频文件的绝对路径。
    返回: {"raw_text": "转录文本", "detected_language": "zh"}
    E: Transcribe an audio file to text using Whisper model, auto-detect language.
    Args file_path: Absolute path to the audio file.
    Returns: {"raw_text": "transcribed text", "detected_language": "en"}
    """
    logger.info(f"C: [transcribe_audio] 开始转录: {file_path}")
    logger.info(f"E: [transcribe_audio] Starting transcription: {file_path}")

    # C: Whisper 未加载时优雅报错（Inspector 调试模式）
    # E: Graceful error when Whisper not loaded (Inspector debug mode)
    if whisper_model is None:
        msg_cn = "Whisper 模型未加载（SKIP_HEAVY_INIT 调试模式）。请通过完整服务（python main.py）使用转录功能。"
        msg_en = "Whisper model not loaded (SKIP_HEAVY_INIT debug mode). Use full service (python main.py) for transcription."
        logger.warning(f"C: [transcribe_audio] {msg_cn}")
        logger.warning(f"E: [transcribe_audio] {msg_en}")
        return {"raw_text": "", "detected_language": "en", "warning": f"{msg_cn} | {msg_en}"}

    result = whisper_model.transcribe(file_path)
    raw_text = result["text"].strip()
    detected_language = result.get("language", "en")

    logger.info(
        f"C: [transcribe_audio] 转录完成，语言={detected_language}，文本长度={len(raw_text)}"
    )
    logger.info(
        f"E: [transcribe_audio] Done, lang={detected_language}, text_len={len(raw_text)}"
    )

    return {"raw_text": raw_text, "detected_language": detected_language}


# ---------------------------------------------------------
# C: MCP Tool 2: 文本润色 — 混合审查模式
#    配置 POLISH_MODEL: 轻量模型迭代润色 + 主力模型终审
#    未配置 POLISH_MODEL: 主力模型直接润色（零额外开销）
# E: MCP Tool 2: Text polishing — hybrid review mode
#    POLISH_MODEL set: lightweight iteration + main model final review
#    POLISH_MODEL not set: main model direct polish (zero overhead)
# ---------------------------------------------------------
@mcp.tool()
def polish_text(raw_text: str, detected_language: str,
               session_ts: str | None = None) -> dict:
    """C: 对 STT 转录文本进行润色。支持混合审查模式。
    参数 raw_text: Whisper 原始转录文本。
    参数 detected_language: 检测到的语言代码（如 "zh", "en"）。
    参数 session_ts: 可选的会话时间戳（用于跨请求共享调试目录）。
    返回: {"polished_text": "润色后的文本"}
    E: Polish STT transcript. Supports hybrid review mode.
    Args raw_text: Raw Whisper transcript.
    Args detected_language: Detected language code (e.g., "zh", "en").
    Args session_ts: Optional session timestamp (for cross-request debug dir sharing).
    Returns: {"polished_text": "polished text"}
    """
    logger.info(
        f"C: [polish_text] 开始，语言={detected_language}，"
        f"润色模式={'混合审查' if polish_client else '主力直润'}，"
        f"模型={Config.POLISH_MODEL or Config.LLM_MODEL}"
    )
    logger.info(
        f"E: [polish_text] Starting, lang={detected_language}, "
        f"mode={'hybrid' if polish_client else 'direct'}, "
        f"model={Config.POLISH_MODEL or Config.LLM_MODEL}"
    )

    # ---------------------------------------------------------
    # C: 路径 A：未配置轻量模型 → 主力模型直接润色（当前行为）
    # E: Path A: No lightweight model → main model direct polish
    # ---------------------------------------------------------
    if polish_client is None:
        return _polish_direct(
            client=llm_client,
            model=Config.LLM_MODEL,
            raw_text=raw_text,
            detected_language=detected_language,
            label="direct"
        )

    # ---------------------------------------------------------
    # C: 路径 B：混合审查模式
    #    阶段一 — 轻量模型迭代润色 + 自审查
    #    阶段二 — 主力模型终审（ACCEPT / FIX / REJECT）
    # E: Path B: Hybrid review mode
    #    Phase 1 — lightweight iterative polish + self-review
    #    Phase 2 — main model final review (ACCEPT / FIX / REJECT)
    # ---------------------------------------------------------

    # — 阶段一：轻量迭代 —
    candidate = raw_text
    accepted_iterations = 0
    for i in range(Config.POLISH_ITERATIONS):
        logger.info(f"C: [polish_text] 轻量迭代 {i+1}/{Config.POLISH_ITERATIONS}")
        logger.info(f"E: [polish_text] Lightweight iteration {i+1}/{Config.POLISH_ITERATIONS}")

        prev = candidate
        result = _polish_direct(
            client=polish_client,
            model=Config.POLISH_MODEL,
            raw_text=candidate,
            detected_language=detected_language,
            label=f"iter{i+1}"
        )
        candidate = result["polished_text"]

        # C: 调试输出 — 保存每次迭代的候选文本
        # E: Debug output — save candidate text of each iteration
        _debug_save_polish_iteration(
            iteration=i + 1,
            previous=prev,
            candidate=candidate,
            session_ts=session_ts
        )

        # 自审查：计算编辑距离比率
        edit_ratio = _edit_distance_ratio(prev, candidate)
        if edit_ratio < 0.05:  # 变化 < 5%，认为收敛
            logger.info(
                f"C: [polish_text] 迭代收敛 (edit_ratio={edit_ratio:.3f})"
            )
            logger.info(
                f"E: [polish_text] Iteration converged (edit_ratio={edit_ratio:.3f})"
            )
            accepted_iterations = i + 1
            break
        accepted_iterations = i + 1

    logger.info(
        f"C: [polish_text] 轻量迭代完成，共 {accepted_iterations} 次"
    )
    logger.info(
        f"E: [polish_text] Lightweight iterations done, count={accepted_iterations}"
    )

    # — 阶段二：主力模型终审 —
    logger.info("C: [polish_text] 提交主力模型终审...")
    logger.info("E: [polish_text] Submitting to main model for final review...")
    verdict = _judge_by_main_model(
        client=llm_client,
        model=Config.LLM_MODEL,
        raw_text=raw_text,
        candidate=candidate,
        detected_language=detected_language
    )

    # C: 根据裁决构建返回结果
    # E: Build result based on verdict
    if verdict["action"] == "ACCEPT":
        logger.info("C: [polish_text] 终审 ACCEPT → 返回候选文本")
        logger.info("E: [polish_text] Final review ACCEPT → returning candidate")
        result = {
            "polished_text": candidate,
            "confidence": "high",
            "iterations": accepted_iterations
        }
    elif verdict["action"] == "FIX":
        logger.info("C: [polish_text] 终审 FIX → 返回主模型修正文本")
        logger.info("E: [polish_text] Final review FIX → returning corrected text")
        result = {
            "polished_text": verdict.get("fixed_text", candidate),
            "confidence": "medium",
            "iterations": accepted_iterations
        }
    else:  # REJECT
        logger.warning(
            f"C: [polish_text] 终审 REJECT: {verdict.get('reason', '未知原因')} → 降级返回原文"
        )
        logger.warning(
            f"E: [polish_text] Final review REJECT: {verdict.get('reason', 'unknown')} → degraded to raw"
        )
        result = {
            "polished_text": raw_text,
            "confidence": "low",
            "warning": verdict.get("reason", "主模型审核未通过")
        }

    # C: 调试输出 — 保存终审摘要
    # E: Debug output — save final review summary
    _debug_save_polish_summary(
        verdict=verdict,
        iterations=accepted_iterations,
        final_candidate=candidate,
        raw_text=raw_text,
        session_ts=session_ts
    )

    return result


# =========================================================
# C: polish_text 辅助函数
# E: polish_text helper functions
# =========================================================

def _get_polish_prompt(detected_language: str) -> str:
    """C: 根据语言返回润色 system prompt。
    E: Return polish system prompt based on language."""
    if detected_language == "zh":
        return (
            "你是一个专业的语音识别文本校对助手。"
            "请将以下STT粗糙文本进行润色：修复错别字、添加标点符号、"
            "去除'嗯''啊'等语气词。只输出润色后的纯文本，不要输出任何解释。"
        )
    else:
        return (
            "You are a professional speech-to-text proofreading assistant. "
            "Polish the following rough transcript: fix typos, add punctuation, "
            "remove filler words (um, uh, like, you know). "
            "Output only the polished text, no explanations."
        )


def _polish_direct(client, model: str, raw_text: str,
                   detected_language: str, label: str = "") -> dict:
    """C: 执行单次润色调用。
    E: Execute a single polish call."""
    prompt = _get_polish_prompt(detected_language)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.2,
    )
    polished = response.choices[0].message.content
    tag = f"[{label}] " if label else ""
    logger.info(f"C: [polish_text] {tag}润色完成，长度={len(polished)}")
    logger.info(f"E: [polish_text] {tag}Done, len={len(polished)}")
    return {"polished_text": polished}


def _edit_distance_ratio(a: str, b: str) -> float:
    """C: 计算两个字符串的归一化编辑距离比率 (0.0~1.0)。
    0.0 = 完全相同，1.0 = 完全不同。
    E: Compute normalized edit distance ratio (0.0~1.0).
    0.0 = identical, 1.0 = completely different."""
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    # 简易 Levenshtein
    m, n = len(a), len(b)
    if m > n:
        a, b, m, n = b, a, n, m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[n] / max(m, n)


def _judge_by_main_model(client, model: str, raw_text: str,
                          candidate: str, detected_language: str) -> dict:
    """C: 主力模型终审。返回 {"action": "ACCEPT|FIX|REJECT", ...}。
    E: Main model final review. Returns {"action": "ACCEPT|FIX|REJECT", ...}."""
    if detected_language == "zh":
        judge_prompt = (
            "你是文本润色的最终审核者。请判断候选润色结果是否可接受。\n\n"
            f"【原始转录】\n{raw_text}\n\n"
            f"【润色候选】\n{candidate}\n\n"
            "请严格按以下格式回复（只回复一个词 + 可选内容）:\n"
            "1. 如果质量合格，回复: ACCEPT\n"
            "2. 如果存在小问题但你可以直接修正，回复: FIX: <修正后的完整文本>\n"
            "3. 如果存在严重问题（语义错误/关键信息丢失），回复: REJECT: <简短原因>\n\n"
            "评估标准:\n"
            "- 原转录中的事实性陈述和专业术语必须保留\n"
            "- 标点符号应正确添加\n"
            "- 口语填充词应已移除\n"
            "- 语义不得有任何偏移"
        )
    else:
        judge_prompt = (
            "You are the final reviewer of text polishing. Determine if the candidate is acceptable.\n\n"
            f"[Original Transcript]\n{raw_text}\n\n"
            f"[Polished Candidate]\n{candidate}\n\n"
            "Reply strictly in this format (one word + optional content):\n"
            "1. If quality is acceptable, reply: ACCEPT\n"
            "2. If minor issues exist but you can fix directly, reply: FIX: <corrected full text>\n"
            "3. If serious issues (semantic errors/key info lost), reply: REJECT: <brief reason>\n\n"
            "Criteria:\n"
            "- Factual statements and technical terms from the original must be preserved\n"
            "- Punctuation should be correctly added\n"
            "- Filler words should be removed\n"
            "- No semantic drift allowed"
        )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": judge_prompt}],
            temperature=0.0,
            max_tokens=1024,
        )
        verdict_text = response.choices[0].message.content.strip()

        if verdict_text.startswith("ACCEPT"):
            return {"action": "ACCEPT"}
        elif verdict_text.startswith("FIX:"):
            fixed = verdict_text[4:].strip()
            return {"action": "FIX", "fixed_text": fixed or candidate}
        elif verdict_text.startswith("REJECT:"):
            reason = verdict_text[7:].strip()
            return {"action": "REJECT", "reason": reason}
        else:
            # 无法解析 → 安全降级为 ACCEPT
            logger.warning(f"C: [polish_text] 终审返回无法解析: {verdict_text[:80]}")
            logger.warning(f"E: [polish_text] Unparseable review verdict: {verdict_text[:80]}")
            return {"action": "ACCEPT"}
    except Exception as e:
        logger.error(f"C: [polish_text] 终审异常: {e} → 降级 ACCEPT")
        logger.error(f"E: [polish_text] Review error: {e} → degrading to ACCEPT")
        return {"action": "ACCEPT"}


# =========================================================
# C: polish_text 调试输出辅助函数
# E: polish_text debug output helper functions
# =========================================================

def _debug_save_polish_iteration(iteration: int, previous: str,
                                  candidate: str,
                                  session_ts: str | None = None) -> None:
    """C: 保存润色迭代的候选文本到调试文件。
    E: Save polish iteration candidate text to debug file."""
    try:
        edit_ratio = _edit_distance_ratio(previous, candidate)
        content = (
            f"=== Polish Iteration {iteration} ===\n"
            f"Edit distance ratio: {edit_ratio:.4f}\n\n"
            f"--- Previous ---\n{previous}\n\n"
            f"--- Candidate ---\n{candidate}\n"
        )
        write_debug_file(
            filename=f"polish_iteration_{iteration}.txt",
            content=content,
            session_ts=session_ts,
            is_json=False
        )
        logger.info(
            f"C: [polish_text] 调试: 迭代{iteration}已保存 (edit_ratio={edit_ratio:.4f})"
        )
        logger.info(
            f"E: [polish_text] Debug: iteration {iteration} saved (edit_ratio={edit_ratio:.4f})"
        )
    except Exception as e:
        logger.error(f"C: [polish_text] 调试保存迭代{iteration}失败: {e}")
        logger.error(f"E: [polish_text] Debug save iteration {iteration} failed: {e}")


def _debug_save_polish_summary(verdict: dict, iterations: int,
                                final_candidate: str, raw_text: str,
                                session_ts: str | None = None) -> None:
    """C: 保存润色终审摘要到调试文件。
    E: Save polish final review summary to debug file."""
    try:
        summary = {
            "verdict": verdict.get("action", "UNKNOWN"),
            "reason": verdict.get("reason", ""),
            "fixed_text": verdict.get("fixed_text", ""),
            "iterations": iterations,
            "final_candidate_length": len(final_candidate),
            "raw_text_length": len(raw_text),
            "edit_from_raw": round(_edit_distance_ratio(raw_text, final_candidate), 4),
            "polish_model": Config.POLISH_MODEL,
            "review_model": Config.LLM_MODEL,
            "timestamp": datetime.now().isoformat(),
        }
        write_debug_file(
            filename="polish_final_summary.json",
            content=summary,
            session_ts=session_ts,
            is_json=True
        )
        logger.info(
            f"C: [polish_text] 调试: 终审摘要已保存 (裁决={verdict.get('action')})"
        )
        logger.info(
            f"E: [polish_text] Debug: final summary saved (verdict={verdict.get('action')})"
        )
    except Exception as e:
        logger.error(f"C: [polish_text] 调试保存终审摘要失败: {e}")
        logger.error(f"E: [polish_text] Debug save final summary failed: {e}")


# ---------------------------------------------------------
# C: MCP Tool 3: 增量修改思维导图 (LLM + State Merge)
# E: MCP Tool 3: Incremental mind map modification (LLM + State Merge)
# ---------------------------------------------------------
@mcp.tool()
def modify_mind_map(chat_history: str, current_map: dict) -> dict:
    """C: 根据对话上下文对思维导图进行增量修改。内部调用 LLM function calling 获取 delta，再在后端执行 State Merge。
    参数 chat_history: 包含用户消息和 AI 回复的格式化文本。
    参数 current_map: 当前导图状态 {"nodes": [...], "links": [...]}。
    返回: {"nodes": [...], "links": [...]} 更新后的导图。
    E: Incrementally modify the mind map based on conversation context. Internally calls LLM function calling for delta, then performs State Merge on the backend.
    Args chat_history: Formatted text containing user message and AI reply.
    Args current_map: Current map state {"nodes": [...], "links": [...]}.
    Returns: {"nodes": [...], "links": [...]} Updated map.
    """
    logger.info(
        f"C: [modify_mind_map] 开始增量绘图，当前节点数={len(current_map.get('nodes', []))}"
    )
    logger.info(
        f"E: [modify_mind_map] Starting incremental drawing, current nodes={len(current_map.get('nodes', []))}"
    )

    try:
        # C: 完全复用 MindMapSpecialistAgent 的 generate_map_from_context 方法
        # E: Fully reuse MindMapSpecialistAgent.generate_map_from_context method
        updated_map = map_agent.generate_map_from_context(
            chat_history=chat_history, current_map=current_map
        )
        logger.info(
            f"C: [modify_mind_map] 绘图完成，节点数={len(updated_map.get('nodes', []))}"
        )
        logger.info(
            f"E: [modify_mind_map] Done, nodes={len(updated_map.get('nodes', []))}"
        )
        return updated_map
    except Exception as e:
        logger.error(f"C: [modify_mind_map] 失败: {e}")
        logger.error(f"E: [modify_mind_map] Failed: {e}")
        # C: 返回原图作为降级方案
        # E: Return original map as fallback
        return current_map


# ---------------------------------------------------------
# C: MCP Tool 4: 多模型协作增量绘图 (v2 管线)
#    内部三阶段管线：概念提取 → 层级规划 → Delta 生成
#    每阶段失败时自动降级，兜底到单模型 ReAct
# E: MCP Tool 4: Multi-model collaborative incremental drawing (v2 pipeline)
#    Internal 3-stage pipeline: concept extraction → hierarchy planning → delta generation
#    Auto-degrades on each stage failure, fallback to single-model ReAct
# ---------------------------------------------------------
@mcp.tool()
def modify_mind_map_v2(chat_history: str, current_map: dict,
                       session_ts: str | None = None) -> dict:
    """C: 多模型协作版增量导图修改。内部通过三阶段管线（概念提取→层级规划→Delta生成）提升层级结构清晰度。
    未配置专用模型时自动降级为单模型 ReAct 模式，行为与 modify_mind_map 完全一致。
    参数 chat_history: 包含用户消息和 AI 回复的格式化文本。
    参数 current_map: 当前导图状态 {"nodes": [...], "links": [...]}。
    参数 session_ts: 可选的会话时间戳（用于跨请求共享调试目录）。
    返回: {"nodes": [...], "links": [...]} 更新后的导图。
    E: Multi-model collaborative incremental map modification. Uses internal 3-stage pipeline (concept extraction→hierarchy planning→delta generation) to improve hierarchy clarity.
    Auto-degrades to single-model ReAct when specialized models not configured, identical behavior to modify_mind_map.
    Args chat_history: Formatted text containing user message and AI reply.
    Args current_map: Current map state {"nodes": [...], "links": [...]}.
    Args session_ts: Optional session timestamp (for cross-request debug dir sharing).
    Returns: {"nodes": [...], "links": [...]} Updated map.
    """
    logger.info(
        f"C: [modify_mind_map_v2] 开始多模型管线绘图，当前节点数={len(current_map.get('nodes', []))}"
    )
    logger.info(
        f"E: [modify_mind_map_v2] Starting multi-model pipeline, current nodes={len(current_map.get('nodes', []))}"
    )

    try:
        updated_map = map_pipeline.generate(
            chat_history=chat_history, current_map=current_map,
            session_ts=session_ts
        )
        logger.info(
            f"C: [modify_mind_map_v2] 绘图完成，节点数={len(updated_map.get('nodes', []))}"
        )
        logger.info(
            f"E: [modify_mind_map_v2] Done, nodes={len(updated_map.get('nodes', []))}"
        )
        return updated_map
    except Exception as e:
        logger.error(f"C: [modify_mind_map_v2] 失败: {e}")
        logger.error(f"E: [modify_mind_map_v2] Failed: {e}")
        return current_map


# ---------------------------------------------------------
# C: 启动入口 — stdio 传输模式
# E: Entry point — stdio transport mode
# ---------------------------------------------------------
if __name__ == "__main__":
    # C: SKIP_HEAVY_INIT 环境变量 — 用于 MCP Inspector 等外部调试工具
    #    跳过 Whisper 模型加载（30s+），使 stdio 握手立即完成。
    #    transcribe_audio 工具在无 Whisper 时会正常报错。
    # E: SKIP_HEAVY_INIT env var — for MCP Inspector and other external debug tools
    #    Skips Whisper model loading (30s+) so stdio handshake completes immediately.
    #    transcribe_audio tool will gracefully error without Whisper.
    skip_heavy = os.environ.get("SKIP_HEAVY_INIT", "").lower() in ("1", "true", "yes")
    if skip_heavy:
        logger.info("C: SKIP_HEAVY_INIT=1 → 跳过 Whisper 模型加载（Inspector 调试模式）")
        logger.info("E: SKIP_HEAVY_INIT=1 → skipping Whisper model load (Inspector debug mode)")
        # C: 仅初始化 LLM 客户端，跳过 Whisper
        # E: Only init LLM clients, skip Whisper
        llm_client = OpenAI(
            api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL
        )
        logger.info(f"C: LLM 客户端就绪（Inspector 模式），模型={Config.LLM_MODEL}")
        logger.info(f"E: LLM client ready (Inspector mode), model={Config.LLM_MODEL}")
        if Config.POLISH_MODEL:
            polish_client = OpenAI(
                api_key=Config.POLISH_API_KEY,
                base_url=Config.POLISH_BASE_URL
            )
            logger.info(f"C: 润色客户端就绪（Inspector 模式），模型={Config.POLISH_MODEL}")
            logger.info(f"E: Polish client ready (Inspector mode), model={Config.POLISH_MODEL}")
        map_agent = MindMapSpecialistAgent()
        # C: 组装管线编排器（与 _init_models 逻辑相同）
        # E: Assemble pipeline orchestrator (same logic as _init_models)
        from mindmap_agent import (
            MindMapPipelineOrchestrator,
            ConceptExtractionAgent,
            HierarchyPlanningAgent,
            DeltaGenerationAgent,
        )
        concept_agent = None
        if Config.CONCEPT_MODEL:
            concept_agent = ConceptExtractionAgent(
                api_key=Config.CONCEPT_API_KEY,
                base_url=Config.CONCEPT_BASE_URL,
                model=Config.CONCEPT_MODEL
            )
        else:
            concept_agent = ConceptExtractionAgent(
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_BASE_URL,
                model=Config.LLM_MODEL
            )
        hierarchy_agent = None
        if Config.HIERARCHY_MODEL:
            hierarchy_agent = HierarchyPlanningAgent(
                api_key=Config.HIERARCHY_API_KEY,
                base_url=Config.HIERARCHY_BASE_URL,
                model=Config.HIERARCHY_MODEL
            )
        else:
            hierarchy_agent = HierarchyPlanningAgent(
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_BASE_URL,
                model=Config.LLM_MODEL
            )
        delta_agent = DeltaGenerationAgent(
            api_key=Config.DELTA_API_KEY,
            base_url=Config.DELTA_BASE_URL,
            model=Config.DELTA_MODEL
        )
        map_pipeline = MindMapPipelineOrchestrator(
            concept_agent=concept_agent,
            hierarchy_agent=hierarchy_agent,
            delta_agent=delta_agent,
            legacy_agent=map_agent
        )
        whisper_model = None  # C: 标记为未加载 / E: Mark as not loaded
        logger.info("C: MCP Server Inspector 调试模式就绪（无 Whisper）")
        logger.info("E: MCP Server Inspector debug mode ready (no Whisper)")
    else:
        _init_models()
    logger.info("C: MCP Server 启动 (stdio 模式)")
    logger.info("E: MCP Server starting (stdio mode)")
    mcp.run(transport="stdio")
