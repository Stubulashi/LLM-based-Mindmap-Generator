# /home/akku/ai-mindmap-agent/mcp_server.py
# C: MCP Server — 将 LLM 聊天/润色/绘图、Whisper 转录、词典下划线标注封装为 MCP Tools
#    任务5: 合并了原 dict_underline_server.py + dictionary_server.py 的能力
# E: MCP Server — encapsulates LLM chat/polish/drawing, Whisper transcription,
#    and dictionary underline annotation as MCP Tools
#    Task 5: merged from dict_underline_server.py + dictionary_server.py
import os
import sys
import json
import time
import logging
import threading
from datetime import datetime

import whisper
import httpx
import wikipediaapi
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
from tools import get_annotation_tools

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
# C: 任务4 — 低参数 LLM 客户端（用于 get_definition / lookup_dictionary）
# E: Task 4 — lightweight LLM client (for get_definition / lookup_dictionary)
light_llm_client = None
# C: 任务3 — Wikipedia 官方库实例
# E: Task 3 — Wikipedia official lib instance
_wiki_wiki = None
_wiki_rate_lock = None
_wiki_last_call_ts = 0.0


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
    #    - 阶段2 概念分组: HIERARCHY_MODEL（中等）
    #    - 阶段3 Delta生成: DELTA_MODEL（主力）
    # E: Initialize multi-model pipeline (3-stage collaborative map generation)
    #    All models independently configurable, auto-degrade to single-model ReAct when not set.
    #    - Stage 1 concept extraction: CONCEPT_MODEL (lightweight)
    #    - Stage 2 concept grouping: HIERARCHY_MODEL (medium)
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
        concept_agent = ConceptExtractionAgent(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            model=Config.LLM_MODEL
        )
        logger.info(
            f"C: 未配置 CONCEPT_MODEL，概念提取使用主力模型={Config.LLM_MODEL}"
        )
        logger.info(
            f"E: CONCEPT_MODEL not set, concept extraction uses main model={Config.LLM_MODEL}"
        )

    # C: 阶段2 — 概念分组 Agent（None = 跳过阶段2，管线降为两阶段）
    #    与阶段1一致：未配置 HIERARCHY_MODEL 时回退到 LLM_MODEL，默认启用三阶段模式。
    #    如需跳过阶段2，显式设置 HIERARCHY_MODEL="" 或环境变量 HIERARCHY_SKIP=true。
    # E: Stage 2 — Concept grouping agent (falls back to LLM_MODEL for full 3-stage by default)
    #    To skip stage 2, explicitly set HIERARCHY_MODEL="" or env HIERARCHY_SKIP=true.
    hierarchy_agent = None
    hierarchy_skip = (
        os.environ.get('HIERARCHY_SKIP', '').lower() in ('true', '1', 'yes')
        or os.environ.get('HIERARCHY_MODEL', '') == ''
    )
    if not hierarchy_skip:
        hierarchy_agent = HierarchyPlanningAgent(
            api_key=Config.HIERARCHY_API_KEY,
            base_url=Config.HIERARCHY_BASE_URL,
            model=Config.HIERARCHY_MODEL or Config.LLM_MODEL
        )
        logger.info(f"C: 概念分组 Agent 就绪，模型={Config.HIERARCHY_MODEL or Config.LLM_MODEL}")
        logger.info(f"E: Concept grouping agent ready, model={Config.HIERARCHY_MODEL or Config.LLM_MODEL}")
    else:
        logger.info(
            "C: HIERARCHY_SKIP=true 或 HIERARCHY_MODEL=''，跳过阶段2（两阶段模式）"
        )
        logger.info(
            "E: HIERARCHY_SKIP=true or HIERARCHY_MODEL='', skipping stage 2 (2-stage mode)"
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

    # ---------------------------------------------------------
    # C: 任务4 — 轻量 LLM 客户端（用于 get_definition / lookup_dictionary）
    # E: Task 4 — lightweight LLM client (for get_definition / lookup_dictionary)
    # ---------------------------------------------------------
    global light_llm_client
    if Config.LLM_LIGHT_ENABLED and Config.LLM_LIGHT_MODEL:
        light_llm_client = OpenAI(
            api_key=Config.LLM_LIGHT_API_KEY,
            base_url=Config.LLM_LIGHT_BASE_URL,
        )
        logger.info(
            f"C: 轻量 LLM 客户端就绪，模型={Config.LLM_LIGHT_MODEL}"
        )
        logger.info(
            f"E: Lightweight LLM client ready, model={Config.LLM_LIGHT_MODEL}"
        )
    else:
        light_llm_client = None
        logger.info("C: 未配置 LLM_LIGHT_MODEL → 轻量任务回退到主力模型")
        logger.info("E: LLM_LIGHT_MODEL not set → light tasks fallback to main model")

    # ---------------------------------------------------------
    # C: 任务3 — Wikipedia 官方库实例
    # E: Task 3 — Wikipedia official lib instance
    # ---------------------------------------------------------
    global _wiki_wiki, _wiki_rate_lock, _wiki_last_call_ts
    import threading as _th
    _wiki_rate_lock = _th.Lock()
    _wiki_last_call_ts = 0.0
    try:
        import wikipediaapi as _wikipediaapi
        _wiki_wiki = _wikipediaapi.Wikipedia(
            user_agent=Config.WIKIPEDIA_USER_AGENT,
            language=Config.WIKIPEDIA_LANGUAGE,
        )
        logger.info(
            f"C: Wikipedia 客户端就绪，lang={Config.WIKIPEDIA_LANGUAGE}, "
            f"ua={Config.WIKIPEDIA_USER_AGENT[:50]}"
        )
        logger.info(
            f"E: Wikipedia client ready, lang={Config.WIKIPEDIA_LANGUAGE}, "
            f"ua={Config.WIKIPEDIA_USER_AGENT[:50]}"
        )
    except Exception as e:
        logger.error(f"C: Wikipedia 客户端初始化失败: {e}")
        logger.error(f"E: Wikipedia client init failed: {e}")
        _wiki_wiki = None

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
    返回: {"tree": [...], "nodes": [...], "links": [...]} tree为G6嵌套树格式，nodes/links为扁平格式用于增量回传。
    E: Incrementally modify the mind map based on conversation context. Internally calls LLM function calling for delta, then performs State Merge on the backend.
    Args chat_history: Formatted text containing user message and AI reply.
    Args current_map: Current map state {"nodes": [...], "links": [...]}.
    Returns: {"tree": [...], "nodes": [...], "links": [...]} tree is G6 nested format, nodes/links are flat format for round-trip.
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
    返回: {"tree": [...], "nodes": [...], "links": [...]} tree为G6嵌套树格式（前端直接消费），nodes/links为扁平格式（增量回传）。
    E: Multi-model collaborative incremental map modification. Uses internal 3-stage pipeline (concept extraction→hierarchy planning→delta generation) to improve hierarchy clarity.
    Auto-degrades to single-model ReAct when specialized models not configured, identical behavior to modify_mind_map.
    Args chat_history: Formatted text containing user message and AI reply.
    Args current_map: Current map state {"nodes": [...], "links": [...]}.
    Args session_ts: Optional session timestamp (for cross-request debug dir sharing).
    Returns: {"tree": [...], "nodes": [...], "links": [...]} tree is G6 nested (frontend direct consumption), nodes/links are flat (round-trip).
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


# =========================================================
# C: 任务5 — 合并自 dict_underline_server.py / dictionary_server.py 的能力
#    以下章节为词典下划线标注、定义查询、IPA 查询的合并实现。
# E: Task 5 — Capabilities merged from dict_underline_server.py / dictionary_server.py
#    Following sections implement dictionary annotation, definition lookup, and IPA lookup.
# =========================================================


# ---------------------------------------------------------
# C: Helper — JSON 安全解析（从 dict_underline_server.py 移植）
# E: Helper — safe JSON parsing (ported from dict_underline_server.py)
# ---------------------------------------------------------
def _safe_json_parse(text: str) -> dict:
    """C: 安全 JSON 解析 — 提取 LLM 返回中的 JSON 对象。
    E: Safe JSON parse — extract JSON object from LLM response."""
    text_stripped = text.strip()
    try:
        return json.loads(text_stripped)
    except json.JSONDecodeError:
        pass
    import re
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    matches = re.findall(code_block_pattern, text_stripped, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    depth = 0
    start = -1
    for i, ch in enumerate(text_stripped):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text_stripped[start:i + 1])
                except json.JSONDecodeError:
                    start = -1
                    continue
    raise json.JSONDecodeError(
        f"Unable to parse JSON from: {text_stripped[:200]}...",
        text_stripped, 0,
    )


# ---------------------------------------------------------
# C: Helper — LLM function calling 封装（从 dict_underline_server.py 移植）
# E: Helper — LLM function calling wrapper (ported)
# ---------------------------------------------------------
def _call_llm_tool(system_prompt: str, user_prompt: str,
                   tools: list, tool_choice_name: str,
                   max_tokens: int = 4096,
                   client=None, model: str | None = None) -> dict:
    """C: 通用 LLM function calling 封装。默认 llm_client + LLM_MODEL。
    E: Generic LLM function calling wrapper. Defaults to llm_client + LLM_MODEL."""
    if client is None:
        client = llm_client
    if model is None:
        model = Config.LLM_MODEL

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": tool_choice_name}},
        max_tokens=max_tokens,
    )
    if not response.choices[0].message.tool_calls:
        # C: 重试一次，附加工具调用提醒
        # E: Retry once with tool-call reminder
        retry_user_prompt = user_prompt + "\n\n" + (
            "C: 【重要】你必须调用 annotate_terms 工具来提交结果，不能直接返回文本。\n"
            "E: [IMPORTANT] You MUST call the annotate_terms tool to submit results, do NOT return plain text."
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": retry_user_prompt},
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": tool_choice_name}},
            max_tokens=max_tokens,
        )
    if not response.choices[0].message.tool_calls:
        raise ValueError(
            "C: LLM 两次调用均未返回 tool_calls\n"
            "E: LLM returned no tool_calls in both attempts"
        )
    tool_call = response.choices[0].message.tool_calls[0]
    raw_args = tool_call.function.arguments
    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        try:
            return _safe_json_parse(raw_args)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"C: JSON 解析失败且无法修复: {e}\n原始: {raw_args[:500]}"
            ) from e


# ---------------------------------------------------------
# C: Helper — 校验标注偏移量（从 dict_underline_server.py 移植）
# E: Helper — validate annotation offsets (ported)
# ---------------------------------------------------------
def _validate_annotations(raw_annotations: dict, current_map: dict) -> dict:
    """C: 校验标注的 char_start/char_end 偏移量是否在有效范围。
    E: Validate char_start/char_end offsets, filter invalid entries."""
    if not isinstance(raw_annotations, dict):
        return {}

    node_texts = {}
    for n in current_map.get('nodes', []):
        nid = str(n['id'])
        node_texts[nid] = {
            'label': n.get('label', ''),
            'details': n.get('details', []),
        }

    cleaned = {}
    for node_id, ann_list in raw_annotations.items():
        node_id_str = str(node_id)
        if node_id_str not in node_texts:
            continue
        if not isinstance(ann_list, list):
            continue
        nt = node_texts[node_id_str]
        valid_items = []
        for ann in ann_list:
            if not isinstance(ann, dict):
                continue
            source = ann.get('source', '')
            cs = ann.get('char_start')
            ce = ann.get('char_end')
            term = ann.get('term', '')
            if not isinstance(cs, int) or not isinstance(ce, int):
                continue
            if cs < 0 or ce <= cs:
                continue
            if source == 'label':
                src_text = nt['label']
            elif source == 'details':
                di = ann.get('detail_index')
                if not isinstance(di, int) or di < 0 or di >= len(nt['details']):
                    continue
                src_text = nt['details'][di]
            else:
                continue
            if ce > len(src_text):
                continue
            actual_substring = src_text[cs:ce]
            if actual_substring.lower() != term.lower():
                continue
            ann_copy = dict(ann)
            ann_copy['term'] = actual_substring
            valid_items.append(ann_copy)
        if valid_items:
            cleaned[node_id_str] = valid_items
    return cleaned


# ---------------------------------------------------------
# C: Helper — Wikipedia 工具函数（任务3 wikipediaapi 集成版）
# E: Helper — Wikipedia utility functions (Task 3 wikipediaapi integrated)
# ---------------------------------------------------------
def _ensure_wiki(language: str):
    """C: 确保 _wiki_wiki 已初始化且语言匹配。
    E: Ensure _wiki_wiki initialized and language matches."""
    global _wiki_wiki
    if _wiki_wiki is None:
        _init_models()
    if _wiki_wiki is not None and _wiki_wiki.language != language:
        _wiki_wiki = wikipediaapi.Wikipedia(
            user_agent=Config.WIKIPEDIA_USER_AGENT,
            language=language,
        )
    return _wiki_wiki


def _throttle_wiki() -> None:
    """C: 简单速率限制 — 相邻请求间隔 ≥ 1 / WIKIPEDIA_RATE_LIMIT 秒。
    E: Simple rate limiter — interval ≥ 1 / WIKIPEDIA_RATE_LIMIT seconds."""
    global _wiki_last_call_ts
    if _wiki_rate_lock is None:
        return
    with _wiki_rate_lock:
        elapsed = time.time() - _wiki_last_call_ts
        wait = max(0.0, 1.0 / max(Config.WIKIPEDIA_RATE_LIMIT, 0.01) - elapsed)
        if wait > 0:
            time.sleep(wait)
        _wiki_last_call_ts = time.time()


def _fetch_wikipedia_page(term: str, language: str):
    """C: 返回 WikipediaPage 对象，用于获取 fullurl。
    E: Return WikipediaPage object for getting fullurl."""
    wiki = _ensure_wiki(language)
    _throttle_wiki()
    return wiki.page(term)


def _fetch_wikipedia_summary(term: str, language: str) -> str | None:
    """C: 通过 wikipediaapi 获取页面摘要。返回 extract，失败 None。
    E: Fetch page summary via wikipediaapi. Returns extract, None on failure."""
    try:
        page = _fetch_wikipedia_page(term, language)
    except wikipediaapi.WikipediaException as e:
        logger.warning(
            f"C: [Wikipedia] '{term}' → page() 异常: {type(e).__name__}: {e}"
        )
        logger.warning(
            f"E: [Wikipedia] '{term}' → page() error: {type(e).__name__}: {e}"
        )
        return None
    except Exception as e:
        logger.warning(
            f"C: [Wikipedia] '{term}' → page() 未预期异常: {e}"
        )
        logger.warning(
            f"E: [Wikipedia] '{term}' → page() unexpected: {e}"
        )
        return None

    try:
        if not page.exists():
            logger.info(f"C: [Wikipedia] '{term}' → 页面不存在")
            logger.info(f"E: [Wikipedia] '{term}' → page does not exist")
            return None
    except wikipediaapi.WikipediaException as e:
        logger.warning(
            f"C: [Wikipedia] '{term}' → exists() 异常: {type(e).__name__}: {e}"
        )
        logger.warning(
            f"E: [Wikipedia] '{term}' → exists() error: {type(e).__name__}: {e}"
        )
        return None

    try:
        extract = (page.summary or "").strip()
    except wikipediaapi.WikipediaException as e:
        logger.warning(
            f"C: [Wikipedia] '{term}' → summary() 异常: {type(e).__name__}: {e}"
        )
        logger.warning(
            f"E: [Wikipedia] '{term}' → summary() error: {type(e).__name__}: {e}"
        )
        return None
    if extract:
        logger.info(
            f"C: [Wikipedia] '{term}' → 获取成功 ({len(extract)} 字符)"
        )
        logger.info(
            f"E: [Wikipedia] '{term}' → success ({len(extract)} chars)"
        )
        return extract
    logger.info(
        f"C: [Wikipedia] '{term}' → summary 为空（可能 disambig 页）"
    )
    logger.info(
        f"E: [Wikipedia] '{term}' → summary empty (may be disambig)"
    )
    return None


# ---------------------------------------------------------
# C: Helper — Free Dictionary API 查询
# E: Helper — Free Dictionary API query
# ---------------------------------------------------------
def _fetch_free_dictionary(term: str) -> dict | None:
    """C: 通过 Free Dictionary API 获取 IPA 音标和定义。
    返回 {"ipa": str, "definition": str}，失败 None。
    E: Fetch IPA and definition via Free Dictionary API.
    Returns {"ipa": str, "definition": str}, None on failure."""
    url = (
        f"https://api.dictionaryapi.dev/api/v2/entries/en/"
        f"{term}"
    )
    try:
        response = httpx.get(
            url,
            timeout=Config.FREE_DICT_TIMEOUT,
            headers={"User-Agent": "AI-MindMap-Agent/1.0"},
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                ipa = ""
                for phonetic in entry.get('phonetics', []):
                    candidate = phonetic.get('text', '')
                    if candidate and '/' in candidate:
                        ipa = candidate.strip('/')
                        break
                if not ipa:
                    for phonetic in entry.get('phonetics', []):
                        candidate = phonetic.get('text', '')
                        if candidate:
                            ipa = candidate.strip('/')
                            break
                definition = ""
                meanings = entry.get('meanings', [])
                if meanings and meanings[0].get('definitions'):
                    definition = meanings[0]['definitions'][0].get('definition', '')
                if ipa or definition:
                    return {"ipa": ipa, "definition": definition}
        elif response.status_code == 404:
            pass
    except Exception as e:
        logger.warning(f"C: [FreeDict] '{term}' 异常: {e}")
        logger.warning(f"E: [FreeDict] '{term}' error: {e}")
    return None


# ---------------------------------------------------------
# C: Helper — LLM 客户端选择（任务4：light 优先）
# E: Helper — LLM client selector (Task 4: light-first)
# ---------------------------------------------------------
def _select_llm_client(prefer_light: bool = True) -> tuple:
    """C: 返回 (client, model, mode) 三元组。
    E: Return (client, model, mode) tuple."""
    if prefer_light and light_llm_client is not None:
        return light_llm_client, Config.LLM_LIGHT_MODEL, "light"
    return llm_client, Config.LLM_MODEL, "main"



# ---------------------------------------------------------
# C: Helper — 术语语言检测 / E: Helper — term language detection
# ---------------------------------------------------------
def _detect_term_language(term: str) -> str:
    """Detect writing system: 'zh'|'latin'|'other'."""
    if not term or not term.strip():
        return 'latin'
    zh_count = sum(1 for ch in term if '一' <= ch <= '鿿' or '㐀' <= ch <= '䶿')
    ja_count = sum(1 for ch in term if '぀' <= ch <= 'ゟ' or '゠' <= ch <= 'ヿ')
    ko_count = sum(1 for ch in term if '가' <= ch <= '힯' or 'ᄀ' <= ch <= 'ᇿ')
    cyrillic_count = sum(1 for ch in term if 'Ѐ' <= ch <= 'ӿ')
    ar_count = sum(1 for ch in term if '؀' <= ch <= 'ۿ')
    latin_count = sum(1 for ch in term if ('a' <= ch <= 'z' or 'A' <= ch <= 'Z' or
        'À' <= ch <= 'ɏ' or ch in ' -'))
    total = max(zh_count + ja_count + ko_count + cyrillic_count + ar_count + latin_count, 1)
    if zh_count / total > 0.3:
        return 'zh'
    if (ja_count + ko_count + cyrillic_count + ar_count) / total > 0.3:
        return 'other'
    return 'latin'


# ---------------------------------------------------------
# C: Helper — 拼音生成(LLM) / E: Helper — Pinyin generation (LLM)
# ---------------------------------------------------------
def _generate_pinyin_via_llm(term: str) -> str:
    if llm_client is None:
        return ""
    try:
        response = llm_client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{
                "role": "system",
                "content": "You are a Pinyin generator. Output ONLY Pinyin with tone marks for the Chinese term. No brackets, no explanation."
            }, {"role": "user", "content": f"Term: {term}"}],
            temperature=0.1, max_tokens=128,
        )
        pinyin = response.choices[0].message.content.strip()
        return pinyin.replace('(', '').replace(')', '').replace('\n', ' ').strip()
    except Exception as e:
        logger.warning(f"C: [Pinyin] '{term}' failed: {e}")
        return ""


# ---------------------------------------------------------
# C: Helper — 罗马化生成(LLM) / E: Helper — Romanization (LLM)
# ---------------------------------------------------------
def _generate_romanization_via_llm(term: str, language_hint: str = "other") -> str:
    if llm_client is None:
        return ""
    try:
        response = llm_client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{
                "role": "system",
                "content": "You are a multilingual transliteration assistant. Output ONLY romanization (Latin alphabet) for the given term. Use Hepburn for Japanese, Revised Romanization for Korean, ISO 9 for Russian. No brackets, no explanation."
            }, {"role": "user", "content": f"Term: {term}"}],
            temperature=0.1, max_tokens=128,
        )
        rom = response.choices[0].message.content.strip()
        return rom.replace('(', '').replace(')', '').replace('\n', ' ').strip()
    except Exception as e:
        logger.warning(f"C: [Romanization] '{term}' failed: {e}")
        return ""


# ---------------------------------------------------------
# C: Helper — LLM 定义生成（任务4：light 优先 + fallback 到 main）
# E: Helper — LLM definition generation (Task 4: light-first + main fallback)
# ---------------------------------------------------------
def _generate_llm_definition(term: str, detail_level: str,
                              language: str = "en") -> str:
    """C: 使用 LLM 生成术语定义（任务4：light 优先）。
    E: Generate term definition via LLM (Task 4: light-first)."""
    if language == "zh":
        detail_prompts = {
            "brief": "请用一句话简要定义该术语。",
            "medium": "请用 2-3 句话定义该术语，包含基本含义和关键特征。",
            "detailed": "请详细定义该术语，包含其含义、背景、关键特征和典型用例（约一个段落）。",
        }
        system_prompt = "你是一个专业的术语词典助手。提供清晰、准确的定义。"
        user_instruction = "请只输出定义文本，不要输出任何额外内容。"
    else:
        detail_prompts = {
            "brief": "Please define the term in one concise sentence.",
            "medium": "Please define the term in 2-3 sentences, covering basic meaning and key features.",
            "detailed": "Please define the term in detail, covering meaning, background, key features, and typical use cases (about a paragraph).",
        }
        system_prompt = "You are a professional terminology dictionary assistant. Provide clear, accurate definitions."
        user_instruction = "Please output only the definition text, no extra content."

    detail_instruction = detail_prompts.get(detail_level, detail_prompts["medium"])

    def _call_llm(client, model):
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Term: {term}\n{detail_instruction}\n\n{user_instruction}"
                )},
            ],
            temperature=0.2,
            max_tokens=512,
        )

    client, model, mode = _select_llm_client(prefer_light=True)
    logger.info(
        f"C: [_generate_llm_definition] '{term}' → model={model} (mode={mode})"
    )
    logger.info(
        f"E: [_generate_llm_definition] '{term}' → model={model} (mode={mode})"
    )

    try:
        response = _call_llm(client, model)
        definition = response.choices[0].message.content.strip()
        logger.info(
            f"C: [LLM Definition/{mode}] '{term}' → 成功 ({len(definition)} 字符)"
        )
        logger.info(
            f"E: [LLM Definition/{mode}] '{term}' → success ({len(definition)} chars)"
        )
        return definition
    except Exception as e:
        logger.error(
            f"C: [LLM Definition/{mode}] '{term}' 失败: {e}"
        )
        logger.error(
            f"E: [LLM Definition/{mode}] '{term}' failed: {e}"
        )
        if mode == "light" and llm_client is not None:
            try:
                response = _call_llm(llm_client, Config.LLM_MODEL)
                definition = response.choices[0].message.content.strip()
                return definition
            except Exception as e2:
                logger.error(
                    f"C: [LLM Definition/fallback] '{term}' 失败: {e2}"
                )
        return "Definition unavailable."


# ---------------------------------------------------------
# C: Helper — IPA + 字面含义查询（任务4：light 优先）
# E: Helper — IPA + literal meaning lookup (Task 4: light-first)
# ---------------------------------------------------------
def _lookup_dictionary_impl(term: str,
                            llm_client_override=None,
                            model_override=None,
                            session_ts=None) -> dict:
    """C: 使用 LLM 生成 IPA 和字面含义（任务4：light 优先）。
    E: Generate IPA + literal meaning via LLM (Task 4: light-first)."""
    if llm_client_override is not None:
        client = llm_client_override
    elif light_llm_client is not None:
        client = light_llm_client
    else:
        client = llm_client

    if model_override is not None:
        model = model_override
    elif client is light_llm_client:
        model = Config.LLM_LIGHT_MODEL or Config.LLM_MODEL
    else:
        model = Config.LLM_MODEL

    system_prompt = (
        "C: 你是一个专业的词典编纂助手。对于给定的术语，请提供其 IPA 国际音标和字面含义。\n"
        "E: You are a professional lexicography assistant. Provide IPA transcription and literal meaning for the given term.\n\n"
        "C: 【输出格式 - 必须严格遵守】\n"
        "1. IPA 必须使用真实的国际音标符号（非近似拼写）。\n"
        "2. 字面含义必须极度简洁、直观（一个短语即可）。\n"
        "3. 请严格按以下 JSON 格式回复（不要输出任何额外文字）：\n"
        '{"ipa": "/.../", "literal_meaning": "..."}\n\n'
        "E: [Output Format - Must Strictly Follow]\n"
        "1. IPA must use actual IPA symbols (not approximate spelling).\n"
        "2. Literal meaning must be extremely concise and intuitive (a short phrase).\n"
        "3. Reply strictly in the following JSON format (no extra text):\n"
        '{"ipa": "/.../", "literal_meaning": "..."}\n'
    )
    try:
        logger.info(
            f"C: [lookup_dictionary] '{term}' → model={model} (mode={'light' if client is light_llm_client else 'main'})"
        )
        logger.info(
            f"E: [lookup_dictionary] '{term}' → model={model} (mode={'light' if client is light_llm_client else 'main'})"
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Term: {term}"},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        raw_text = response.choices[0].message.content.strip()
        try:
            result = _safe_json_parse(raw_text)
        except json.JSONDecodeError:
            logger.warning(
                f"C: [lookup_dictionary] JSON 解析失败: {raw_text[:100]}"
            )
            result = {"ipa": "", "literal_meaning": ""}

        ipa = result.get("ipa", "").strip()
        literal_meaning = result.get("literal_meaning", "").strip()
        write_debug_file(
            filename="dictionary_lookup.json",
            content={
                "term": term,
                "ipa": ipa,
                "literal_meaning": literal_meaning,
                "raw_response": raw_text[:500],
            },
            session_ts=session_ts,
            is_json=True,
        )
        logger.info(
            f"C: [lookup_dictionary] '{term}' → IPA={ipa[:40]}, LM={literal_meaning[:40]}"
        )
        return {"ipa": ipa, "literal_meaning": literal_meaning}
    except Exception as e:
        logger.error(f"C: [lookup_dictionary] '{term}' 失败: {e}")
        return {"ipa": "", "literal_meaning": ""}


# =========================================================
# C: MCP Tool 5: annotate_terms — 术语标注（任务2 预取 + 任务5 合并）
# E: MCP Tool 5: annotate_terms — term annotation
# =========================================================
@mcp.tool()
def annotate_terms(current_map: dict, density_mode: str = "medium",
                   detail_level: str = "medium",
                   user_language: str = "en",
                   session_ts: str | None = None) -> dict:
    """C: 分析导图节点标签和详情，识别需要下划线标注的关键术语。
    任务2: 在标注完成后预取所有术语的完整定义，写入本地缓存。
    任务5: 从 dict_underline_server.py 合并而来，由 mcp_server.py 单进程提供。
    参数 current_map: 当前导图 {"nodes": [...], "links": [...]}。
    参数 density_mode: "low"/"medium"/"high"。
    参数 detail_level: "brief"/"medium"/"detailed"。
    参数 user_language: "zh"/"en"。
    参数 session_ts: 可选的会话时间戳。
    返回: {"status": "success", "annotations": {...}, "prefetched_cache": {...}, ...}
    E: Analyze mind map nodes, identify key terms for underline annotation.
    Task 2: prefetch all terms' full definitions into local cache.
    Task 5: merged from dict_underline_server.py, single-process in mcp_server.py.
    Returns: {"status": "success", "annotations": {...}, "prefetched_cache": {...}, ...}
    """
    logger.info(
        f"C: [annotate_terms] 开始标注，节点数={len(current_map.get('nodes', []))}, "
        f"密度={density_mode}, 详细度={detail_level}"
    )
    logger.info(
        f"E: [annotate_terms] Starting, nodes={len(current_map.get('nodes', []))}, "
        f"density={density_mode}, detail={detail_level}"
    )

    nodes = current_map.get('nodes', [])
    if not nodes:
        return {
            "status": "success", "annotations": {},
            "detail_level": detail_level, "prefetched_cache": {}
        }

    write_debug_file(
        filename="06_annotate_terms_input.json",
        content=current_map,
        session_ts=session_ts,
        is_json=True,
    )

    # C: 构建 LLM prompt
    # E: Build LLM prompt
    density_descriptions = {
        "low": ("C: 每节点最多 1 个最关键的术语。\nE: Annotate at most 1 key term per node."),
        "medium": ("C: 每节点标注 2-3 个关键术语。\nE: Annotate 2-3 key terms per node."),
        "high": ("C: 每节点标注 4-6 个关键术语。\nE: Annotate 4-6 key terms per node."),
    }
    density_instruction = density_descriptions.get(density_mode, density_descriptions["medium"])

    node_summaries = []
    for n in nodes:
        nid = str(n['id'])
        label = n.get('label', '')
        details = n.get('details', [])
        summary = f"Node [{nid}]: label=\"{label}\""
        if details:
            detail_lines = "\n".join(f"  details[{i}]: \"{d}\"" for i, d in enumerate(details))
            summary += f"\n{detail_lines}"
        node_summaries.append(summary)
    node_text_block = "\n\n".join(node_summaries)

    system_prompt = (
        "C: 你是一个专业的术语识别器。你的任务是：从思维导图节点中识别值得下划线标注的关键术语。\n"
        "E: You are a professional term identifier. Your task: identify key terms worth underlining annotation.\n\n"
        "C: 【标注铁律 - 必须严格遵守】\n"
        "1. 只标注领域术语、专有名词、技术概念、专业缩写。\n"
        "2. 严禁标注常见词汇：冠词(a/an/the)、介词(of/in/on)、连词(and/but)、基础动词(be/have/do)。\n"
        "3. 对于中文节点：标注学科术语、专有名词、概念性词汇。\n"
        "4. char_start 和 char_end 必须精确（按 Unicode 码点计数，0-based）。\n"
        "5. term 字段必须与原文中的子串完全一致（大小写敏感）。\n"
        "6. 如果某节点没有值得标注的术语，不要为该节点添加条目。\n"
        f"{density_instruction}\n\n"
        "E: [Annotation Rules - Must Strictly Follow]\n"
        "1. Only annotate domain terminology, proper nouns, technical concepts, professional abbreviations.\n"
        "2. Strictly prohibit annotating common words (articles, prepositions, conjunctions, basic verbs).\n"
        "3. For Chinese nodes: annotate academic terms, proper nouns, conceptual vocabulary.\n"
        "4. char_start and char_end must be precise (Unicode code points, 0-based).\n"
        "5. The term field must exactly match the substring in the source text (case-sensitive).\n"
        "6. If a node has no terms worth annotating, do NOT add an entry for that node.\n"
    )
    user_prompt = (
        f"C: 【导图节点文本 - 请识别关键术语】\n\n{node_text_block}\n\n---\n"
        f"请调用 annotate_terms 工具提交标注结果。\n---\n\n"
        f"E: [Mind Map Node Text - Please Identify Key Terms]\n\n{node_text_block}\n\n---\n"
        f"Please call the annotate_terms tool to submit the annotation results."
    )

    try:
        # C: 任务5 — 使用主模型（术语识别对质量要求高）
        # E: Task 5 — use main model (annotation needs quality)
        result = _call_llm_tool(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=get_annotation_tools(),
            tool_choice_name="annotate_terms",
            max_tokens=4096,
            client=llm_client,
            model=Config.LLM_MODEL,
        )
        raw_annotations = result.get('annotations', {})
        logger.info(
            f"C: [annotate_terms] LLM 返回 {len(raw_annotations)} 个节点的标注"
        )
        logger.info(
            f"E: [annotate_terms] LLM returned annotations for {len(raw_annotations)} nodes"
        )
    except Exception as e:
        logger.error(f"C: [annotate_terms] LLM 调用失败: {e}")
        logger.error(f"E: [annotate_terms] LLM call failed: {e}")
        raw_annotations = {}

    cleaned = _validate_annotations(raw_annotations, current_map)
    total_terms = sum(len(v) for v in cleaned.values())
    logger.info(
        f"C: [annotate_terms] 校验后：{len(cleaned)} 个节点，{total_terms} 个术语"
    )
    logger.info(
        f"E: [annotate_terms] After validation: {len(cleaned)} nodes, {total_terms} terms"
    )

    # C: 任务2 — 预取所有唯一术语的完整定义
    # E: Task 2 — Prefetch all unique terms' full definitions
    all_terms: set[str] = set()
    for ann_list in cleaned.values():
        for ann in ann_list:
            term = ann.get('term')
            if term:
                all_terms.add(term)

    cache_index: dict[str, dict] = {}
    if all_terms:
        logger.info(
            f"C: [annotate_terms] 预取 {len(all_terms)} 个术语的完整定义..."
        )
        logger.info(
            f"E: [annotate_terms] Prefetching {len(all_terms)} terms..."
        )
        for term in sorted(all_terms):
            try:
                defn = get_definition(
                    term=term,
                    detail_level=detail_level,
                    language=user_language,
                    session_ts=session_ts,
                )
                cache_index[term] = {
                    "wikipedia_definition": defn.get("wikipedia_definition"),
                    "wikipedia_url": defn.get("wikipedia_url"),
                    "llm_definition": defn.get("llm_definition"),
                    "ipa": defn.get("ipa", ""),
                    "ipa_narrow": defn.get("ipa_narrow", ""),
                    "ipa_broad": defn.get("ipa_broad", ""),
                    "literal_meaning": defn.get("literal_meaning", ""),
                    "source": defn.get("source", "unknown"),
                    "term_language": defn.get("term_language", "latin"),
                    "pinyin": defn.get("pinyin", ""),
                    "romanization": defn.get("romanization", ""),
                }
            except Exception as e:
                logger.error(
                    f"C: [annotate_terms] 预取 '{term}' 失败: {e}"
                )
                cache_index[term] = {
                    "wikipedia_definition": None,
                    "wikipedia_url": None,
                    "llm_definition": None,
                    "ipa": "",
                    "ipa_narrow": "",
                    "ipa_broad": "",
                    "literal_meaning": "",
                    "source": "error",
                    "term_language": "latin",
                    "pinyin": "",
                    "romanization": "",
                }

    # C: 写入二级菜单缓存目录
    # E: Write underline cache directory
    if session_ts and cache_index:
        cache_dir = os.path.join(
            Config.DEBUG_OUTPUT_DIR, session_ts, "underline_cache"
        )
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "underline_cache.json")
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_ts": session_ts,
                    "user_language": user_language,
                    "detail_level": detail_level,
                    "node_count": len(cleaned),
                    "term_count": len(cache_index),
                    "by_term": cache_index,
                    "by_node": {
                        nid: [a["term"] for a in anns if a.get("term")]
                        for nid, anns in cleaned.items()
                    },
                }, f, ensure_ascii=False, indent=2)
            logger.info(
                f"C: [annotate_terms] 术语缓存已写入 {cache_path}"
            )
        except Exception as e:
            logger.error(
                f"C: [annotate_terms] 写入术语缓存失败: {e}"
            )

    write_debug_file(
        filename="06_underline_cache.json",
        content={
            "session_ts": session_ts,
            "term_count": len(cache_index),
            "by_term": cache_index,
        },
        session_ts=session_ts,
        is_json=True,
    )

    output = {
        "status": "success",
        "annotations": cleaned,
        "detail_level": detail_level,
        "density_mode": density_mode,
        "user_language": user_language,
        "raw_annotations_node_count": len(raw_annotations),
        "validated_node_count": len(cleaned),
        "total_terms": total_terms,
        "prefetched_cache": cache_index,
    }
    write_debug_file(
        filename="06_annotate_terms_output.json",
        content=output,
        session_ts=session_ts,
        is_json=True,
    )
    return output


# =========================================================
# C: MCP Tool 6: get_definition — 术语定义查询（任务5 合并）
# E: MCP Tool 6: get_definition — term definition lookup (Task 5 merged)
# =========================================================
@mcp.tool()
def get_definition(term: str, detail_level: str = "medium",
                   language: str = "en",
                   session_ts: str | None = None) -> dict:
    """C: 获取术语定义（任务5：从 dict_underline_server.py 合并）。
    Wikipedia 优先 → LLM 回退 → IPA + 字面含义。
    E: Get term definition (Task 5: merged from dict_underline_server.py).
    Wikipedia first → LLM fallback → IPA + literal meaning.
    """
    logger.info(
        f"C: [get_definition] 查询 '{term}', detail={detail_level}, lang={language}"
    )
    logger.info(
        f"E: [get_definition] '{term}', detail={detail_level}, lang={language}"
    )

    wikipedia_definition = None
    wikipedia_url = None
    llm_definition = None
    source = "none"

    # C: 阶段1 — Wikipedia 优先
    # E: Phase 1 — Wikipedia first
    wiki_extract = _fetch_wikipedia_summary(term, language)
    if wiki_extract:
        wikipedia_definition = wiki_extract
        try:
            page_obj = _fetch_wikipedia_page(term, language)
            if isinstance(page_obj, wikipediaapi.WikipediaPage) and page_obj.exists():
                wikipedia_url = page_obj.fullurl
            else:
                wikipedia_url = f"https://{language}.wikipedia.org/wiki/{term.replace(' ', '_')}"
        except Exception:
            wikipedia_url = f"https://{language}.wikipedia.org/wiki/{term.replace(' ', '_')}"
        source = "wikipedia"

    # C: 阶段1b — LLM 定义（任务4：light 优先）
    # E: Phase 1b — LLM definition (Task 4: light-first)
    llm_def = _generate_llm_definition(term, detail_level, language)
    if llm_def != "Definition unavailable.":
        llm_definition = llm_def
        if source == "none":
            source = "llm"

    definition = wikipedia_definition or llm_definition

    # C: 阶段2 — IPA + 字面含义
    #    修复: 始终调用 _lookup_dictionary_impl 获取 literal_meaning（即使 FreeDict 已返回 IPA）
    #    FreeDict IPA 优先（更权威），literal_meaning 始终来自 LLM
    # E: Phase 2 — IPA + literal meaning
    #    Fix: Always call _lookup_dictionary_impl for literal_meaning (even if FreeDict has IPA)
    #    FreeDict IPA takes priority (more authoritative), literal_meaning always from LLM
    ipa = ""
    literal_meaning = ""

    if language == "en":
        free_dict_result = _fetch_free_dictionary(term)
        if free_dict_result:
            ipa = free_dict_result.get('ipa', '')
            if definition is None and free_dict_result.get('definition'):
                definition = free_dict_result['definition']
                source = "free_dictionary"

    # C: 始终请求 LLM 生成 literal_meaning（+ IPA 回退）
    # E: Always request LLM for literal_meaning (+ IPA fallback)
    try:
        if light_llm_client is not None:
            dict_result = _lookup_dictionary_impl(
                term,
                llm_client_override=light_llm_client,
                model_override=Config.LLM_LIGHT_MODEL,
                session_ts=session_ts,
            )
        else:
            dict_result = _lookup_dictionary_impl(
                term, session_ts=session_ts
            )
        # C: FreeDict IPA 优先（更权威），LLM 作为回退
        # E: FreeDict IPA takes priority (more authoritative), LLM as fallback
        if not ipa:
            ipa = dict_result.get('ipa', '')
        literal_meaning = dict_result.get('literal_meaning', '')
    except Exception as e:
        logger.error(f"C: [get_definition] 词典查询失败: {e}")
        logger.error(f"E: [get_definition] Dictionary lookup failed: {e}")
        # C: 如果 IPA 也没有，尝试从 LLM 回退获取 / E: If no IPA either, try LLM fallback
        if not ipa and light_llm_client is None:
            try:
                dict_result = _lookup_dictionary_impl(term, session_ts=session_ts)
                if not ipa:
                    ipa = dict_result.get('ipa', '')
                literal_meaning = dict_result.get('literal_meaning', '')
            except Exception:
                pass

    # C: 阶段3 — 语言检测 + 拼音/罗马化/双IPA
    # E: Phase 3 — language detection + pinyin/romanization/dual IPA
    term_language = _detect_term_language(term)
    pinyin = ""
    romanization = ""
    ipa_narrow = ipa  # C: 现有 IPA（严式音标） / E: existing IPA (narrow transcription)
    ipa_broad = ""

    if term_language == 'zh':
        # C: 中文 → 拼音 + IPA（严式+宽式）
        # E: Chinese → Pinyin + IPA (narrow + broad)
        pinyin = _generate_pinyin_via_llm(term)
        if not ipa_narrow:
            # C: 通过 LLM 生成 IPA（含严式和宽式）
            # E: Generate IPA via LLM (narrow + broad)
            try:
                ipa_resp = llm_client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[{
                        "role": "system",
                        "content": "You are an IPA phonetics expert. For the given Chinese term, output JSON: {\"ipa_narrow\": \"...\", \"ipa_broad\": \"...\"}. Narrow uses full tone diacritics, broad uses tone numbers. No extra text."
                    }, {"role": "user", "content": f"Term: {term}"}],
                    temperature=0.1, max_tokens=200,
                )
                ipa_data = _safe_json_parse(ipa_resp.choices[0].message.content.strip())
                ipa_narrow = ipa_data.get("ipa_narrow", "").replace("/", "")
                ipa_broad = ipa_data.get("ipa_broad", "").replace("/", "")
            except Exception as e:
                logger.warning(f"C: [IPA/ZH] '{term}' failed: {e}")
    elif term_language == 'other':
        # C: 非拉丁 → 罗马化 + IPA
        # E: Non-Latin → Romanization + IPA
        romanization = _generate_romanization_via_llm(term)
        if not ipa_narrow:
            try:
                ipa_resp = llm_client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[{
                        "role": "system",
                        "content": "You are an IPA phonetics expert. For the given non-Latin term, output JSON: {\"ipa_narrow\": \"...\", \"ipa_broad\": \"...\", \"romanization\": \"...\"}. No extra text."
                    }, {"role": "user", "content": f"Term: {term}"}],
                    temperature=0.1, max_tokens=200,
                )
                ipa_data = _safe_json_parse(ipa_resp.choices[0].message.content.strip())
                ipa_narrow = ipa_data.get("ipa_narrow", "").replace("/", "")
                ipa_broad = ipa_data.get("ipa_broad", "").replace("/", "")
                if not romanization:
                    romanization = ipa_data.get("romanization", "").replace("/", "")
            except Exception as e:
                logger.warning(f"C: [IPA/Other] '{term}' failed: {e}")
    elif term_language == 'latin':
        # C: 拉丁 → 仅双IPA（严式+宽式）
        # E: Latin → Dual IPA only (narrow + broad)
        if not ipa_broad:
            try:
                ipa_resp = llm_client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[{
                        "role": "system",
                        "content": "You are an IPA phonetics expert. For the given Latin-script term, output JSON: {\"ipa_narrow\": \"...\", \"ipa_broad\": \"...\"}. Narrow uses precise diacritics, broad is simplified. No extra text."
                    }, {"role": "user", "content": f"Term: {term}"}],
                    temperature=0.1, max_tokens=200,
                )
                ipa_data = _safe_json_parse(ipa_resp.choices[0].message.content.strip())
                ipa_narrow = ipa_data.get("ipa_narrow", ipa_narrow).replace("/", "")
                ipa_broad = ipa_data.get("ipa_broad", "").replace("/", "")
            except Exception as e:
                logger.warning(f"C: [IPA/Latin] '{term}' failed: {e}")

    result = {
        "definition": definition,
        "wikipedia_definition": wikipedia_definition,
        "wikipedia_url": wikipedia_url,
        "llm_definition": llm_definition,
        "ipa": ipa_narrow,
        "ipa_narrow": ipa_narrow,
        "ipa_broad": ipa_broad,
        "literal_meaning": literal_meaning,
        "source": source,
        "term_language": term_language,
        "pinyin": pinyin,
        "romanization": romanization,
    }

    write_debug_file(
        filename="07_get_definition.json",
        content={
            "term": term,
            "detail_level": detail_level,
            "language": language,
            "definition": definition[:300] if definition else "",
            "definition_length": len(definition) if definition else 0,
            "ipa": ipa,
            "literal_meaning": literal_meaning,
            "source": source,
            "timestamp": datetime.now().isoformat(),
        },
        session_ts=session_ts,
        is_json=True,
    )

    logger.info(
        f"C: [get_definition] '{term}' → source={source}, def_len={len(definition) if definition else 0}, "
        f"ipa={'✓' if ipa else '✗'}, lm={'✓' if literal_meaning else '✗'}"
    )
    return result


# =========================================================
# C: MCP Tool 7: lookup_dictionary — IPA + 字面含义（任务5 合并自 dictionary_server.py）
# E: MCP Tool 7: lookup_dictionary — IPA + literal meaning (Task 5 merged)
# =========================================================
@mcp.tool()
def lookup_dictionary(term: str, session_ts: str | None = None) -> dict:
    """C: 查询术语的 IPA 和字面含义（任务4：light 优先）。
    E: Look up IPA + literal meaning (Task 4: light-first)."""
    logger.info(f"C: [MCP] lookup_dictionary 被调用: '{term}'")
    logger.info(f"E: [MCP] lookup_dictionary called: '{term}'")
    return _lookup_dictionary_impl(term=term, session_ts=session_ts)


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
        hierarchy_skip = (
            os.environ.get('HIERARCHY_SKIP', '').lower() in ('true', '1', 'yes')
            or os.environ.get('HIERARCHY_MODEL', '') == ''
        )
        if not hierarchy_skip:
            hierarchy_agent = HierarchyPlanningAgent(
                api_key=Config.HIERARCHY_API_KEY,
                base_url=Config.HIERARCHY_BASE_URL,
                model=Config.HIERARCHY_MODEL or Config.LLM_MODEL
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
        # C: 任务4 — Inspector 模式也初始化轻量 LLM
        # E: Task 4 — Inspector mode also inits light LLM
        if Config.LLM_LIGHT_ENABLED and Config.LLM_LIGHT_MODEL:
            light_llm_client = OpenAI(
                api_key=Config.LLM_LIGHT_API_KEY,
                base_url=Config.LLM_LIGHT_BASE_URL,
            )
        else:
            light_llm_client = None
        # C: 任务3 — Inspector 模式也初始化 Wikipedia 客户端
        # E: Task 3 — Inspector mode also inits Wikipedia client
        _wiki_rate_lock = threading.Lock()
        _wiki_last_call_ts = 0.0
        try:
            _wiki_wiki = wikipediaapi.Wikipedia(
                user_agent=Config.WIKIPEDIA_USER_AGENT,
                language=Config.WIKIPEDIA_LANGUAGE,
            )
        except Exception as e:
            logger.error(f"C: Inspector 模式 Wikipedia 初始化失败: {e}")
            logger.error(f"E: Inspector mode Wikipedia init failed: {e}")
            _wiki_wiki = None
        whisper_model = None  # C: 标记为未加载 / E: Mark as not loaded
        logger.info("C: MCP Server Inspector 调试模式就绪（无 Whisper）")
        logger.info("E: MCP Server Inspector debug mode ready (no Whisper)")
    else:
        _init_models()
    logger.info("C: MCP Server 启动 (stdio 模式)")
    logger.info("E: MCP Server starting (stdio mode)")
    mcp.run(transport="stdio")
