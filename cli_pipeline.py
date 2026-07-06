#!/usr/bin/env python3
"""C: 纯命令行思维导图生成管线。无 FastAPI/Web/前端依赖。
   直接调用 Whisper 转录 + LLM 导图生成，适合 WSL/Linux 终端使用。
E: CLI-only mind map generation pipeline. No FastAPI/Web/frontend.
   Direct Whisper transcription + LLM map generation for WSL/Linux terminals."""

# C: 在导入 config 之前先加载 api.env（确保 Config 类能读取到 API Key）
# E: Load api.env BEFORE importing config (ensures Config reads API Key)
import os
import sys
from pathlib import Path

_api_env_path = Path(__file__).parent / "api.env"
if _api_env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_api_env_path, override=True)

# =========================================================
# C: 导入依赖
# E: Import dependencies
# =========================================================
import argparse
import json
import logging
import uuid
from datetime import datetime

import whisper
from openai import OpenAI

from config import Config
from mindmap_agent import (
    MindMapSpecialistAgent,
    MindMapPipelineOrchestrator,
    ConceptExtractionAgent,
    HierarchyPlanningAgent,
    DeltaGenerationAgent,
    compute_depth_stats,
)

# C: 日志 -> stderr，结果 -> stdout
# E: Logs to stderr, results to stdout
logging.basicConfig(
    level=logging.INFO,
    format="[CLI] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("cli-pipeline")

# =========================================================
# C: 常量
# E: Constants
# =========================================================
MAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")


# =========================================================
# C: 模型初始化 — 等价于 mcp_server._init_models() 但不启动 MCP
# E: Model init — equivalent to mcp_server._init_models() without MCP
# =========================================================
def init_models() -> dict:
    """C: 初始化所有模型和 Agent。
    - Whisper (small) 语音识别模型
    - OpenAI LLM 客户端
    - 润色客户端（可选）
    - 单模型 MindMapSpecialistAgent（降级兜底）
    - 三阶段管线编排器（概念提取 + 层级规划 + Delta 生成）
    返回包含所有实例的字典。
    E: Initialize all models and agents.
    - Whisper (small) speech recognition model
    - OpenAI LLM client
    - Polish client (optional)
    - Single-model MindMapSpecialistAgent (fallback)
    - 3-stage pipeline orchestrator (concept + hierarchy + delta)
    Returns dict with all instances."""
    logger.info("C: 正在加载 Whisper 模型 (small)...")
    logger.info("E: Loading Whisper model (small)...")
    whisper_model = whisper.load_model("small")
    logger.info(
        f"C: Whisper 就绪，设备: {next(whisper_model.parameters()).device}"
    )
    logger.info(
        f"E: Whisper ready on: {next(whisper_model.parameters()).device}"
    )

    # C: LLM 客户端
    # E: LLM client
    llm_client = OpenAI(
        api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL
    )
    logger.info(f"C: LLM 客户端就绪，模型={Config.LLM_MODEL}")
    logger.info(f"E: LLM client ready, model={Config.LLM_MODEL}")

    # C: 润色客户端（可选）
    # E: Polish client (optional)
    polish_client = None
    if Config.POLISH_MODEL:
        polish_client = OpenAI(
            api_key=Config.POLISH_API_KEY,
            base_url=Config.POLISH_BASE_URL,
        )
        logger.info(
            f"C: 润色客户端就绪，模型={Config.POLISH_MODEL}"
        )
        logger.info(
            f"E: Polish client ready, model={Config.POLISH_MODEL}"
        )

    # C: 单模型 Agent（始终初始化，管线降级兜底）
    # E: Single-model agent (always init, pipeline fallback)
    map_agent = MindMapSpecialistAgent()

    # C: 阶段1 — 概念提取 Agent
    # E: Stage 1 — Concept extraction agent
    if Config.CONCEPT_MODEL:
        concept_agent = ConceptExtractionAgent(
            api_key=Config.CONCEPT_API_KEY,
            base_url=Config.CONCEPT_BASE_URL,
            model=Config.CONCEPT_MODEL,
        )
        logger.info(
            f"C: 概念提取 Agent 就绪，模型={Config.CONCEPT_MODEL}"
        )
        logger.info(
            f"E: Concept extraction agent ready, model={Config.CONCEPT_MODEL}"
        )
    else:
        concept_agent = ConceptExtractionAgent(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            model=Config.LLM_MODEL,
        )
        logger.info(
            f"C: 概念提取使用主力模型={Config.LLM_MODEL}"
        )
        logger.info(
            f"E: Concept extraction uses main model={Config.LLM_MODEL}"
        )

    # C: 阶段2 — 层级规划 Agent（可能为 None = 两阶段模式）
    # E: Stage 2 — Hierarchy planning agent (None = 2-stage mode)
    hierarchy_skip = (
        os.environ.get("HIERARCHY_SKIP", "").lower() in ("true", "1", "yes")
        or os.environ.get("HIERARCHY_MODEL", "") == ""
    )
    hierarchy_agent = None
    if not hierarchy_skip:
        hierarchy_agent = HierarchyPlanningAgent(
            api_key=Config.HIERARCHY_API_KEY,
            base_url=Config.HIERARCHY_BASE_URL,
            model=Config.HIERARCHY_MODEL or Config.LLM_MODEL,
        )
        logger.info(
            f"C: 概念分组 Agent 就绪，模型={Config.HIERARCHY_MODEL or Config.LLM_MODEL}"
        )
        logger.info(
            f"E: Concept grouping agent ready, model={Config.HIERARCHY_MODEL or Config.LLM_MODEL}"
        )
    else:
        logger.info("C: 跳过阶段2（两阶段模式）")
        logger.info("E: Skipping stage 2 (2-stage mode)")

    # C: 阶段3 — Delta 生成 Agent（始终配置）
    # E: Stage 3 — Delta generation agent (always configured)
    delta_agent = DeltaGenerationAgent(
        api_key=Config.DELTA_API_KEY,
        base_url=Config.DELTA_BASE_URL,
        model=Config.DELTA_MODEL,
    )
    logger.info(f"C: Delta 生成 Agent 就绪，模型={Config.DELTA_MODEL}")
    logger.info(f"E: Delta generation agent ready, model={Config.DELTA_MODEL}")

    # C: 组装管线编排器
    # E: Assemble pipeline orchestrator
    map_pipeline = MindMapPipelineOrchestrator(
        concept_agent=concept_agent,
        hierarchy_agent=hierarchy_agent,
        delta_agent=delta_agent,
        legacy_agent=map_agent,
    )
    logger.info("C: 多模型导图管线编排器就绪")
    logger.info("E: Multi-model map pipeline orchestrator ready")

    return {
        "whisper_model": whisper_model,
        "llm_client": llm_client,
        "polish_client": polish_client,
        "map_agent": map_agent,
        "map_pipeline": map_pipeline,
        "concept_agent": concept_agent,
        "hierarchy_agent": hierarchy_agent,
        "delta_agent": delta_agent,
    }


# =========================================================
# C: 音频转录 — 直接调用 Whisper
# E: Audio transcription — direct Whisper call
# =========================================================
def transcribe(whisper_model, file_path: str) -> dict:
    """C: 使用 Whisper 转录音频文件。
    返回 {"raw_text": "...", "detected_language": "zh"}。
    E: Transcribe audio file using Whisper.
    Returns {"raw_text": "...", "detected_language": "en"}."""
    logger.info(f"C: 开始转录: {file_path}")
    logger.info(f"E: Starting transcription: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"C: 文件不存在: {file_path}")
        logger.error(f"E: File not found: {file_path}")
        return {"raw_text": "", "detected_language": "en"}

    result = whisper_model.transcribe(file_path)
    raw_text = result["text"].strip()
    detected_language = result.get("language", "en")

    logger.info(
        f"C: 转录完成，语言={detected_language}，文本长度={len(raw_text)}"
    )
    logger.info(
        f"E: Transcribe done, lang={detected_language}, text_len={len(raw_text)}"
    )
    return {"raw_text": raw_text, "detected_language": detected_language}


# =========================================================
# C: 润色 — 主力模型直接润色（复用 mcp_server.py _polish_direct 逻辑）
# E: Polish — main model direct polish (reusing mcp_server.py _polish_direct)
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


def polish_text(
    llm_client: OpenAI,
    raw_text: str,
    detected_language: str,
    model: str | None = None,
) -> str:
    """C: 对 STT 转录文本进行主力模型直接润色。
    E: Polish STT transcript with main model direct polish."""
    if not raw_text:
        return ""

    prompt = _get_polish_prompt(detected_language)
    response = llm_client.chat.completions.create(
        model=model or Config.LLM_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.2,
    )
    polished = response.choices[0].message.content
    logger.info(f"C: 润色完成，长度={len(polished)}")
    logger.info(f"E: Polish done, len={len(polished)}")
    return polished


# =========================================================
# C: 构建绘图上下文 — 模仿 main.py 的 formatted_history
# E: Build drawing context — mimics main.py's formatted_history
# =========================================================
def build_formatted_history(user_msg: str, transcript_context: str = "") -> str:
    """C: 构建绘图上下文。包含转录内容（如有）和用户指令。
    E: Build drawing context. Includes transcript (if any) and user instruction."""
    transcript_block = ""
    if transcript_context:
        transcript_block = (
            f"C: 【用户提供的语音转录内容 - 请从中提取核心概念绘制导图】\n"
            f"{transcript_context}\n"
            f"---\n"
            f"E: [User-provided speech transcript - extract core concepts for mind map]\n"
            f"{transcript_context}\n"
            f"---\n"
        )

    formatted = (
        transcript_block
        + f"C: 【最高优先级指令】用户说：{user_msg}\n"
        + f"E: [Highest Priority Instruction] User says: {user_msg}\n"
    )
    return formatted


# =========================================================
# C: 导图生成 — 优先三阶段管线，降级单模型
# E: Map generation — 3-stage pipeline first, degrade to single-model
# =========================================================
def generate_mindmap(
    map_pipeline: MindMapPipelineOrchestrator,
    map_agent: MindMapSpecialistAgent,
    formatted_history: str,
    current_map: dict | None = None,
) -> dict:
    """C: 生成思维导图。优先管线，失败降级单模型。
    E: Generate mind map. Pipeline first, degrade to single-model on failure."""
    if current_map is None:
        current_map = {"nodes": [], "links": []}

    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # C: 优先使用三阶段管线
    # E: Prefer 3-stage pipeline
    try:
        logger.info("C: 开始管线生成...")
        logger.info("E: Starting pipeline generation...")
        result = map_pipeline.generate(
            chat_history=formatted_history,
            current_map=current_map,
            session_ts=session_ts,
        )
        logger.info("C: 管线生成完成")
        logger.info("E: Pipeline generation complete")
        return result
    except Exception as e:
        logger.error(f"C: 管线生成失败: {e}，降级到单模型")
        logger.error(f"E: Pipeline failed: {e}, degrading to single-model")
        try:
            result = map_agent.generate_map_from_context(
                chat_history=formatted_history,
                current_map=current_map,
            )
            logger.info("C: 单模型生成完成")
            logger.info("E: Single-model generation complete")
            return result
        except Exception as e2:
            logger.error(f"C: 单模型也失败: {e2}")
            logger.error(f"E: Single-model also failed: {e2}")
            return current_map


# =========================================================
# C: 保存导图 — 匹配 main.py /save_map 格式
# E: Save map — matches main.py /save_map format
# =========================================================
def save_map(map_data: dict, name: str = "cli-mindmap") -> str:
    """C: 保存导图到 maps/ 目录。返回 map_id。
    E: Save map to maps/ directory. Returns map_id."""
    os.makedirs(MAPS_DIR, exist_ok=True)

    map_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    node_count = len(map_data.get("nodes", []))
    link_count = len(map_data.get("links", []))

    # C: 仅保留 nodes + links 持久化，清理内部元数据
    # E: Persist only nodes + links, clean internal metadata
    clean_data = {
        "nodes": map_data.get("nodes", []),
        "links": map_data.get("links", []),
    }

    payload = {
        "map_id": map_id,
        "name": name,
        "created_at": timestamp,
        "updated_at": timestamp,
        "node_count": node_count,
        "link_count": link_count,
        "data": clean_data,
    }

    filepath = os.path.join(MAPS_DIR, f"{map_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(
        f"C: 已保存 map_id={map_id}, nodes={node_count}, 路径={filepath}"
    )
    logger.info(
        f"E: Saved map_id={map_id}, nodes={node_count}, path={filepath}"
    )

    # C: 输出到 stdout（用户可见）
    # E: Output to stdout (user-visible)
    print(f"\nC: 导图已保存 / Map Saved")
    print(f"  map_id: {map_id}")
    print(f"  path:   {filepath}")
    print(f"  nodes:  {node_count}")
    print(f"  links:  {link_count}")

    return map_id


# =========================================================
# C: 终端展示 — 输出导图摘要
# E: Terminal display — print map summary
# =========================================================
def print_summary(result: dict, name: str, elapsed: float):
    """C: 在终端展示导图摘要。
    E: Display mind map summary in terminal."""
    nodes = result.get("nodes", [])
    links = result.get("links", [])
    timing = result.get("_timing", {})
    degradation = result.get("_degradation", {})
    depth_stats = result.get("_depth_stats", {})
    tree = result.get("tree", [])

    # C: 根节点名称（从 tree 或 nodes 推断）
    # E: Root node name (from tree or nodes)
    root_name = ""
    if tree:
        root_name = tree[0].get("label", "")
    elif nodes:
        # C: 找 parent_id 为 None 的节点
        # E: Find node with parent_id=None
        root_candidates = [n for n in nodes if n.get("parent_id") is None]
        if root_candidates:
            root_name = root_candidates[0].get("label", "")
        else:
            root_name = nodes[0].get("label", "")

    print("\n" + "=" * 60)
    print(f"  C: 思维导图生成完成 / E: Mind Map Generated")
    print(f"  C: 名称 / E: Name:      {name}")
    print(f"  C: 节点数 / E: Nodes:     {len(nodes)}")
    print(f"  C: 连线数 / E: Links:     {len(links)}")
    if root_name:
        print(f"  C: 根节点 / E: Root:      {root_name}")
    print(f"  C: 耗时 / E: Time:      {elapsed:.1f}s")

    if timing:
        total_t = timing.get("total", 0)
        s1 = timing.get("stage1", 0)
        s2 = timing.get("stage2", 0)
        s3 = timing.get("stage3", 0)
        print(f"  C: 管线耗时 / E: Pipeline Timing:")
        print(f"    Stage 1 (C: 概念提取 / E: Concept):       {s1:.1f}s")
        if s2 > 0:
            print(f"    Stage 2 (C: 层级规划 / E: Hierarchy):    {s2:.1f}s")
        print(f"    Stage 3 (C: Delta生成 / E: Delta):       {s3:.1f}s")
        if total_t > 0:
            print(f"    C: 总计 / E: Total:               {total_t:.1f}s")
            # C: 除总时间的其余开销（数据合并、调试IO等）
            # E: Overhead (merge, debug IO, etc.)
            overhead = total_t - s1 - s2 - s3
            if overhead > 0.5:
                print(f"    C: 其他开销 / E: Overhead:         {overhead:.1f}s")

    if degradation and any(degradation.values()):
        print(f"  !! C: 降级发生 / E: Degradation Occurred:")
        for k, v in degradation.items():
            if v:
                print(f"     - {k}: {v}")

    if depth_stats:
        print(f"  C: 深度统计 / E: Depth Stats:")
        print(f"    C: 最大深度 / E: Max Depth:       {depth_stats.get('max_depth', 0)}")
        print(f"    C: 平均深度 / E: Avg Depth:       {depth_stats.get('avg_depth', 0)}")
        print(f"    C: 深度分布 / E: Distribution:    {depth_stats.get('depth_distribution', {})}")

    if nodes:
        preview_count = min(15, len(nodes))
        print(f"  C: 节点预览 / E: Node Preview ({preview_count}/{len(nodes)}):")
        for i, n in enumerate(nodes[:preview_count]):
            nid = n.get("id", "?")
            label = n.get("label", "(C: 无标签 / E: no label)")
            print(f"    [{nid}] {label}")
        if len(nodes) > preview_count:
            print(f"    ... C: 还有 / E: and {len(nodes) - preview_count} C: 个节点 / E: more")

    print("=" * 60 + "\n")


# =========================================================
# C: 完整音频管线 — 音频 → 转录 → 润色 → 导图
# E: Full audio pipeline — audio → transcribe → polish → map
# =========================================================
def audio_to_mindmap(
    models: dict,
    audio_path: str,
    name: str = "audio-mindmap",
    skip_polish: bool = False,
) -> dict:
    """C: 完整管线：音频 → Whisper 转录 → LLM 润色 → 导图生成 → 保存。
    E: Full pipeline: audio → Whisper transcribe → LLM polish → map generation → save."""
    t_start = datetime.now()

    # C: 1. 转录音频
    # E: 1. Transcribe audio
    print(f"C: 正在转录 / E: Transcribing: {audio_path}")
    sys.stdout.flush()
    transcribe_result = transcribe(models["whisper_model"], audio_path)
    raw_text = transcribe_result["raw_text"]
    detected_lang = transcribe_result["detected_language"]

    if not raw_text:
        logger.warning("C: 转录结果为空")
        logger.warning("E: Empty transcript")
        print("C: 警告：转录结果为空 / E: Warning: Empty transcript")
        return {"nodes": [], "links": []}

    # C: 显示转录文本摘要
    # E: Show transcript summary
    transcript_preview = raw_text[:300]
    if len(raw_text) > 300:
        transcript_preview += "..."
    print(f"\nC: 转录文本 / E: Transcript ({detected_lang}):")
    print(f"  {transcript_preview}")
    print(f"  C: 全文长度 / E: Full length: {len(raw_text)} C: 字符 / E: chars")
    sys.stdout.flush()

    # C: 2. 润色文本（可选）
    # E: 2. Polish text (optional)
    transcript_context = raw_text
    if not skip_polish:
        print(f"\nC: 正在润色 / E: Polishing...")
        sys.stdout.flush()
        polished = polish_text(
            models["llm_client"],
            raw_text,
            detected_lang,
        )
        if polished and polished != raw_text:
            transcript_context = polished
            polished_preview = polished[:300]
            if len(polished) > 300:
                polished_preview += "..."
            print(f"C: 润色后 / E: Polished:")
            print(f"  {polished_preview}")
            sys.stdout.flush()

    # C: 3. 构建绘图上下文
    # E: 3. Build drawing context
    print(f"\nC: 正在生成思维导图 / E: Generating mind map...")
    sys.stdout.flush()
    formatted_history = build_formatted_history(
        user_msg=transcript_context,
        transcript_context=raw_text,
    )

    # C: 4. 生成导图
    # E: 4. Generate mind map
    result = generate_mindmap(
        models["map_pipeline"],
        models["map_agent"],
        formatted_history,
    )

    elapsed = (datetime.now() - t_start).total_seconds()

    # C: 5. 保存并展示
    # E: 5. Save and display
    save_map(result, name=name)
    print_summary(result, name, elapsed)

    return result


# =========================================================
# C: 纯文本模式 — 文本 → 导图
# E: Text-only mode — text → map
# =========================================================
def text_to_mindmap(
    models: dict,
    text: str,
    name: str = "text-mindmap",
) -> dict:
    """C: 纯文本模式：文本 → 导图生成 → 保存。
    E: Text-only mode: text → map generation → save."""
    t_start = datetime.now()

    print(f"C: 正在处理文本 / E: Processing text ({len(text)} C: 字符 / E: chars)")
    print(f"C: 正在生成思维导图 / E: Generating mind map...")
    sys.stdout.flush()

    formatted_history = build_formatted_history(user_msg=text)

    result = generate_mindmap(
        models["map_pipeline"],
        models["map_agent"],
        formatted_history,
    )

    elapsed = (datetime.now() - t_start).total_seconds()

    save_map(result, name=name)
    print_summary(result, name, elapsed)

    return result


# =========================================================
# C: 交互模式 — 逐轮输入文本，增量构建导图
# E: Interactive mode — incremental text input, incremental map build
# =========================================================
def run_interactive(models: dict):
    """C: 交互模式 — 逐轮输入，增量构建导图。
    E: Interactive mode — incremental input, incremental map building."""
    print("\n" + "=" * 50)
    print("C: 交互式导图生成模式")
    print("E: Interactive Mind Map Generation Mode")
    print("C: 输入内容后回车。输入 /exit 或 Ctrl+C 退出。")
    print("E: Enter content and press Enter. /exit or Ctrl+C to quit.")
    print("=" * 50 + "\n")

    current_map = {"nodes": [], "links": []}
    round_num = 1

    try:
        while True:
            user_input = input(f"[R{round_num}] >>> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("/exit", "/quit", ":q", "exit"):
                break

            formatted = build_formatted_history(user_msg=user_input)
            logger.info(f"C: 第 {round_num} 轮生成中...")
            logger.info(f"E: Round {round_num} generating...")
            print(f"C: 生成中 / E: Generating...")
            sys.stdout.flush()

            # C: 优先管线，失败降级单模型
            # E: Pipeline first, degrade to single-model
            try:
                result = models["map_pipeline"].generate(
                    chat_history=formatted,
                    current_map=current_map,
                    session_ts=datetime.now().strftime("%Y%m%d_%H%M%S"),
                )
            except Exception as e:
                logger.error(f"C: 管线失败: {e}, 降级单模型")
                logger.error(f"E: Pipeline failed: {e}, degrade single-model")
                result = models["map_agent"].generate_map_from_context(
                    chat_history=formatted,
                    current_map=current_map,
                )

            current_map = {
                "nodes": result.get("nodes", current_map.get("nodes", [])),
                "links": result.get("links", current_map.get("links", [])),
            }
            node_count = len(current_map["nodes"])
            link_count = len(current_map["links"])
            print(f"  >> C: 当前 / E: Current: {node_count} C: 节点 / E: nodes, {link_count} C: 连线 / E: links")
            round_num += 1

    except KeyboardInterrupt:
        print("\n")

    # C: 最终保存
    # E: Final save
    if current_map.get("nodes"):
        save_map(current_map, name="interactive-mindmap")
        print_summary(current_map, "interactive-mindmap", 0)
    else:
        print("C: 无节点生成，未保存")
        print("E: No nodes generated, nothing saved")


# =========================================================
# C: 依赖检查 — 检查核心依赖是否可用
# E: Dependency check — verify core dependencies
# =========================================================
def check_dependencies():
    """C: 检查核心依赖是否已安装。缺失时提示安装。
    E: Check if core dependencies are installed. Prompt install if missing."""
    required = [
        ("openai", "openai"),
        ("whisper", "openai-whisper"),
        ("httpx", "httpx"),
    ]
    missing = []
    for mod_name, pip_name in required:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        print("C: 以下依赖缺失 / E: Missing dependencies:")
        for m in missing:
            print(f"  - {m}")
        print(f"\nC: 请运行 / E: Please run:")
        print(f"  pip install {' '.join(missing)}")
        return False
    return True


# =========================================================
# C: 命令行入口
# E: CLI entry point
# =========================================================
def main():
    parser = argparse.ArgumentParser(
        description=(
            "CLI Mind Map Generator — 纯命令行思维导图生成管线\n"
            "C: 支持音频转录和纯文本输入，调用 AI 生成思维导图并保存为 JSON。\n"
            "E: Supports audio transcription and text input, generates mind maps via AI and saves as JSON."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "C: 使用示例 / E: Usage examples:\n"
            "  %(prog)s \"机器学习的分支包括监督学习和无监督学习\"\n"
            "  %(prog)s lecture.mp3 --audio --name \"课堂笔记\"\n"
            "  %(prog)s lecture.mp3 --audio --skip-polish\n"
            "  %(prog)s -i\n"
            "  %(prog)s --check-deps"
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        help=(
            "C: 输入文本或音频文件路径\n"
            "E: Input text or audio file path"
        ),
    )
    parser.add_argument(
        "--audio",
        "-a",
        action="store_true",
        help="C: 将 input 视为音频文件路径（使用 Whisper 转录）\nE: Treat input as audio file path (use Whisper transcription)",
    )
    parser.add_argument(
        "--name",
        "-n",
        default="cli-mindmap",
        help=(
            "C: 导图名称（默认: cli-mindmap）\n"
            "E: Map name (default: cli-mindmap)"
        ),
    )
    parser.add_argument(
        "--skip-polish",
        action="store_true",
        help="C: 跳过 LLM 文本润色（保留 Whisper 原始转录）\nE: Skip LLM text polishing (keep Whisper raw transcript)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help=(
            "C: 交互模式（逐条输入文本，增量构建导图）\n"
            "E: Interactive mode (enter text incrementally, build map iteratively)"
        ),
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help=(
            "C: 仅检查依赖是否已安装，不启动模型\n"
            "E: Only check if dependencies are installed, do not load models"
        ),
    )

    args = parser.parse_args()

    # C: 仅检查依赖
    # E: Check dependencies only
    if args.check_deps:
        ok = check_dependencies()
        sys.exit(0 if ok else 1)

    # C: 无参数时显示帮助
    # E: No args, show help
    if not args.input and not args.interactive:
        parser.print_help()
        print(
            "\nC: 提示：请提供输入文本或音频文件路径，或使用 -i 进入交互模式。"
            "\nE: Hint: provide input text/audio path, or use -i for interactive mode."
        )
        sys.exit(1)

    # C: 初始化模型（耗时操作：加载 Whisper + Agent）
    # E: Initialize models (heavy: Whisper + Agent loading)
    logger.info("C: 正在初始化模型（首次加载约 10-30 秒）...")
    logger.info("E: Initializing models (first load ~10-30s)...")
    models = init_models()
    logger.info("C: 模型初始化完成")
    logger.info("E: Model initialization complete")

    if args.interactive:
        run_interactive(models)
    elif args.input:
        if args.audio:
            audio_to_mindmap(models, args.input, name=args.name, skip_polish=args.skip_polish)
        else:
            text_to_mindmap(models, args.input, name=args.name)


if __name__ == "__main__":
    main()
