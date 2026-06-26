# /home/akku/ai-mindmap-agent/dict_underline_server.py
# C: 词典术语下划线标注 MCP Server — 提供术语标注和定义查询两大工具
#    遵循 mcp_server.py 的架构模式：FastMCP + 全局模型初始化 + 工具注册 + stdio 启动
# E: Dictionary term underline annotation MCP Server — provides term annotation and definition lookup tools
#    Follows mcp_server.py architecture: FastMCP + global model init + tool registration + stdio startup
import json
import sys
import logging
from datetime import datetime

import httpx
from openai import OpenAI

from mcp.server.fastmcp import FastMCP

from config import Config
from tools import get_annotation_tools
from dictionary_server import lookup_dictionary
from mindmap_agent import write_debug_file

# C: 日志输出到 stderr，避免污染 stdio 协议通道
# E: Log to stderr to avoid polluting the stdio protocol channel
logging.basicConfig(
    level=logging.INFO,
    format="[Dict-Underline] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("dict-underline")

# C: 创建 MCP Server 实例
# E: Create MCP Server instance
mcp = FastMCP(
    name="dict-underline-server",
    instructions=(
        "C: 词典术语下划线标注 MCP Server — 提供术语标注（annotate_terms）和定义查询（get_definition）两大工具\n"
        "E: Dictionary Term Underline Annotation MCP Server — provides annotate_terms and get_definition tools"
    ),
)

# ---------------------------------------------------------
# C: 全局模型初始化
# E: Global model initialization
# ---------------------------------------------------------
llm_client = None


def _init_models():
    """C: 初始化 LLM 客户端。
    E: Initialize LLM client."""
    global llm_client
    llm_client = OpenAI(
        api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL
    )
    logger.info(f"C: Dict-Underline LLM 客户端就绪，模型={Config.LLM_MODEL}")
    logger.info(f"E: Dict-Underline LLM client ready, model={Config.LLM_MODEL}")


# =========================================================
# C: 辅助函数 — JSON 安全解析
# E: Helper — safe JSON parsing
# =========================================================
def _safe_json_parse(text: str) -> dict:
    """C: 安全 JSON 解析 — 提取 LLM 返回中的 JSON 对象。
    E: Safe JSON parse — extract JSON object from LLM response."""
    import re

    text_stripped = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text_stripped)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code block
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    matches = re.findall(code_block_pattern, text_stripped, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Strategy 3: Extract outermost {...} object
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
        text_stripped, 0
    )


# =========================================================
# C: 辅助函数 — 调用 LLM function calling
# E: Helper — LLM function calling
# =========================================================
def _call_llm_tool(system_prompt: str, user_prompt: str,
                   tools: list, tool_choice_name: str,
                   max_tokens: int = 4096) -> dict:
    """C: 通用 LLM function calling 封装。
    E: Generic LLM function calling wrapper."""
    response = llm_client.chat.completions.create(
        model=Config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": tool_choice_name}},
        max_tokens=max_tokens
    )

    # C: 检查 tool_calls
    # E: Check tool_calls
    if not response.choices[0].message.tool_calls:
        logger.warning(
            f"C: [_call_llm_tool] LLM 未返回 tool_calls，重试一次"
        )
        logger.warning(
            f"E: [_call_llm_tool] LLM returned no tool_calls, retrying once"
        )
        retry_user_prompt = (
            user_prompt + "\n\n"
            "C: 【重要】你必须调用 annotate_terms 工具来提交结果，不能直接返回文本。\n"
            "E: [IMPORTANT] You MUST call the annotate_terms tool to submit results, do NOT return plain text."
        )
        response = llm_client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": retry_user_prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": tool_choice_name}},
            max_tokens=max_tokens
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
        logger.warning(
            f"C: [_call_llm_tool] JSON 解析失败，尝试自动修复..."
        )
        logger.warning(
            f"E: [_call_llm_tool] JSON parse failed, attempting auto-repair..."
        )
        try:
            return _safe_json_parse(raw_args)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"C: JSON 解析失败且无法修复: {e}\n"
                f"原始响应: {raw_args[:500]}\n"
                f"E: JSON parse failed and unrepairable: {e}\n"
                f"Raw response: {raw_args[:500]}"
            ) from e


# =========================================================
# C: 辅助函数 — 校验标注偏移量
# E: Helper — validate annotation offsets
# =========================================================
def _validate_annotations(raw_annotations: dict, current_map: dict) -> dict:
    """C: 校验标注的 char_start/char_end 偏移量是否在有效范围内，
    过滤掉无效条目。返回清理后的 annotations。
    E: Validate char_start/char_end offsets, filter invalid entries.
    Returns cleaned annotations."""
    if not isinstance(raw_annotations, dict):
        return {}

    # C: 构建 node_id → {label, details[]} 的快速查找表
    # E: Build node_id → {label, details[]} lookup table
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
            logger.warning(
                f"C: [_validate_annotations] 未知节点ID '{node_id}'，跳过"
            )
            logger.warning(
                f"E: [_validate_annotations] Unknown node ID '{node_id}', skipped"
            )
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

            # C: 确定源文本并校验偏移量
            # E: Determine source text and validate offsets
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
                logger.warning(
                    f"C: [_validate_annotations] 偏移量越界 node={node_id}, "
                    f"source={source}, char_end={ce} > len={len(src_text)}"
                )
                logger.warning(
                    f"E: [_validate_annotations] Offset out of bounds node={node_id}, "
                    f"source={source}, char_end={ce} > len={len(src_text)}"
                )
                continue

            # C: 验证 term 与源文本中的子串匹配
            # E: Verify term matches substring in source text
            actual_substring = src_text[cs:ce]
            if actual_substring.lower() != term.lower():
                logger.warning(
                    f"C: [_validate_annotations] 术语不匹配 node={node_id}, "
                    f"expected='{term}' vs actual='{actual_substring}'"
                )
                logger.warning(
                    f"E: [_validate_annotations] Term mismatch node={node_id}, "
                    f"expected='{term}' vs actual='{actual_substring}'"
                )
                continue

            # C: 确保 term 字段与源文本大小写一致
            # E: Ensure term field matches source text casing
            ann_copy = dict(ann)
            ann_copy['term'] = actual_substring
            valid_items.append(ann_copy)

        if valid_items:
            cleaned[node_id_str] = valid_items

    return cleaned


# ---------------------------------------------------------
# C: MCP Tool 1: annotate_terms — 术语标注
# E: MCP Tool 1: annotate_terms — term annotation
# ---------------------------------------------------------
@mcp.tool()
def annotate_terms(current_map: dict, density_mode: str = "medium",
                   detail_level: str = "medium",
                   session_ts: str | None = None) -> dict:
    """C: 分析导图节点标签和详情，识别需要添加下划线标注的关键术语。
    参数 current_map: 当前导图 {"nodes": [...], "links": [...]}。
    参数 density_mode: 标注密度 "low"/"medium"/"high"（每节点约 1/2-3/4-6 个术语）。
    参数 detail_level: 定义详细程度 "brief"/"medium"/"detailed"（传递给后续 get_definition）。
    参数 session_ts: 可选的会话时间戳（用于跨请求共享调试目录）。
    返回: {"status": "success", "annotations": {node_id: [{term, source, detail_index, char_start, char_end}]}, "detail_level": str}
    E: Analyze mind map node labels and details, identify key terms for underline annotation.
    Args current_map: Current mind map {"nodes": [...], "links": [...]}.
    Args density_mode: Annotation density "low"/"medium"/"high" (~1 / 2-3 / 4-6 terms per node).
    Args detail_level: Definition detail "brief"/"medium"/"detailed" (passed to subsequent get_definition).
    Args session_ts: Optional session timestamp (for cross-request debug dir sharing).
    Returns: {"status": "success", "annotations": {node_id: [{term, source, detail_index, char_start, char_end}]}, "detail_level": str}
    """
    logger.info(
        f"C: [annotate_terms] 开始标注，节点数={len(current_map.get('nodes', []))}，"
        f"密度={density_mode}，详细度={detail_level}"
    )
    logger.info(
        f"E: [annotate_terms] Starting, nodes={len(current_map.get('nodes', []))}, "
        f"density={density_mode}, detail={detail_level}"
    )

    nodes = current_map.get('nodes', [])
    if not nodes:
        logger.info("C: [annotate_terms] 空导图，返回空标注")
        logger.info("E: [annotate_terms] Empty map, returning empty annotations")
        return {"status": "success", "annotations": {}, "detail_level": detail_level}

    # C: 保存标注输入用于调试
    # E: Save annotation input for debugging
    write_debug_file(
        filename="06_annotate_terms_input.json",
        content=current_map,
        session_ts=session_ts,
        is_json=True,
    )

    # C: 构建 LLM prompt
    # E: Build LLM prompt
    density_descriptions = {
        "low": (
            "C: 每节点只标注最多 1 个最关键的术语。\n"
            "E: Annotate at most 1 key term per node."
        ),
        "medium": (
            "C: 每节点标注 2-3 个关键术语。\n"
            "E: Annotate 2-3 key terms per node."
        ),
        "high": (
            "C: 每节点标注 4-6 个关键术语，尽可能全面地覆盖领域概念。\n"
            "E: Annotate 4-6 key terms per node, cover domain concepts as comprehensively as possible."
        ),
    }
    density_instruction = density_descriptions.get(
        density_mode, density_descriptions["medium"]
    )

    # C: 构建节点文本摘要供 LLM 分析
    # E: Build node text summary for LLM analysis
    node_summaries = []
    for n in nodes:
        nid = str(n['id'])
        label = n.get('label', '')
        details = n.get('details', [])
        summary = f"Node [{nid}]: label=\"{label}\""
        if details:
            detail_lines = "\n".join(
                f"  details[{i}]: \"{d}\"" for i, d in enumerate(details)
            )
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
        f"C: 【导图节点文本 - 请识别关键术语】\n\n"
        f"{node_text_block}\n\n"
        f"---\n"
        f"请调用 annotate_terms 工具提交标注结果。\n"
        f"---\n\n"
        f"E: [Mind Map Node Text - Please Identify Key Terms]\n\n"
        f"{node_text_block}\n\n"
        f"---\n"
        f"Please call the annotate_terms tool to submit the annotation results."
    )

    try:
        # C: 调用 LLM function calling
        # E: Call LLM function calling
        tools = get_annotation_tools()
        result = _call_llm_tool(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            tool_choice_name="annotate_terms",
            max_tokens=4096,
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

    # C: 校验和清理标注结果
    # E: Validate and clean annotation results
    cleaned = _validate_annotations(raw_annotations, current_map)

    total_terms = sum(len(v) for v in cleaned.values())
    logger.info(
        f"C: [annotate_terms] 校验后：{len(cleaned)} 个节点，{total_terms} 个术语"
    )
    logger.info(
        f"E: [annotate_terms] After validation: {len(cleaned)} nodes, {total_terms} terms"
    )

    # C: 保存标注输出用于调试
    # E: Save annotation output for debugging
    output = {
        "status": "success",
        "annotations": cleaned,
        "detail_level": detail_level,
        "density_mode": density_mode,
        "raw_annotations_node_count": len(raw_annotations),
        "validated_node_count": len(cleaned),
        "total_terms": total_terms,
    }
    write_debug_file(
        filename="06_annotate_terms_output.json",
        content=output,
        session_ts=session_ts,
        is_json=True,
    )

    return output


# =========================================================
# C: 辅助函数 — Wikipedia API 查询
# E: Helper — Wikipedia API query
# =========================================================
def _fetch_wikipedia_summary(term: str, language: str) -> str | None:
    """C: 通过 Wikipedia REST API 获取页面摘要。
    返回 extract 文本，失败返回 None。
    E: Fetch page summary via Wikipedia REST API.
    Returns extract text, None on failure."""
    url = (
        f"https://{language}.wikipedia.org/api/rest_v1/page/summary/"
        f"{httpx.URL(term).path.lstrip('/')}"
    )
    try:
        response = httpx.get(
            url,
            timeout=Config.WIKIPEDIA_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "AI-MindMap-Agent/1.0"},
        )
        if response.status_code == 200:
            data = response.json()
            extract = data.get('extract', '').strip()
            if extract:
                logger.info(
                    f"C: [Wikipedia] '{term}' → 获取成功 ({len(extract)} 字符)"
                )
                logger.info(
                    f"E: [Wikipedia] '{term}' → success ({len(extract)} chars)"
                )
                return extract
            else:
                logger.info(
                    f"C: [Wikipedia] '{term}' → extract 为空"
                )
                logger.info(
                    f"E: [Wikipedia] '{term}' → extract is empty"
                )
        elif response.status_code == 404:
            logger.info(
                f"C: [Wikipedia] '{term}' → 404 未找到"
            )
            logger.info(
                f"E: [Wikipedia] '{term}' → 404 not found"
            )
        else:
            logger.warning(
                f"C: [Wikipedia] '{term}' → HTTP {response.status_code}"
            )
            logger.warning(
                f"E: [Wikipedia] '{term}' → HTTP {response.status_code}"
            )
    except httpx.TimeoutException:
        logger.warning(
            f"C: [Wikipedia] '{term}' → 超时 ({Config.WIKIPEDIA_TIMEOUT}s)"
        )
        logger.warning(
            f"E: [Wikipedia] '{term}' → timeout ({Config.WIKIPEDIA_TIMEOUT}s)"
        )
    except Exception as e:
        logger.warning(
            f"C: [Wikipedia] '{term}' → 请求异常: {e}"
        )
        logger.warning(
            f"E: [Wikipedia] '{term}' → request error: {e}"
        )

    return None


# =========================================================
# C: 辅助函数 — LLM 定义生成
# E: Helper — LLM definition generation
# =========================================================
def _generate_llm_definition(term: str, detail_level: str) -> str:
    """C: 使用 LLM 生成术语定义。
    E: Generate term definition using LLM."""
    detail_prompts = {
        "brief": (
            "C: 请用一句话简要定义该术语。\n"
            "E: Please define the term in one concise sentence."
        ),
        "medium": (
            "C: 请用 2-3 句话定义该术语，包含基本含义和关键特征。\n"
            "E: Please define the term in 2-3 sentences, covering basic meaning and key features."
        ),
        "detailed": (
            "C: 请详细定义该术语，包含其含义、背景、关键特征和典型用例（约一个段落）。\n"
            "E: Please define the term in detail, covering meaning, background, key features, and typical use cases (about a paragraph)."
        ),
    }
    detail_instruction = detail_prompts.get(detail_level, detail_prompts["medium"])

    try:
        response = llm_client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "C: 你是一个专业的术语词典助手。提供清晰、准确的定义。\n"
                        "E: You are a professional terminology dictionary assistant. Provide clear, accurate definitions."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"C: 术语: {term}\n{detail_instruction}\n\n"
                        f"请只输出定义文本，不要输出任何额外内容。\n"
                        f"---\n"
                        f"E: Term: {term}\n{detail_instruction}\n\n"
                        f"Please output only the definition text, no extra content."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=512,
        )
        definition = response.choices[0].message.content.strip()
        logger.info(
            f"C: [LLM Definition] '{term}' → 生成成功 ({len(definition)} 字符)"
        )
        logger.info(
            f"E: [LLM Definition] '{term}' → success ({len(definition)} chars)"
        )
        return definition
    except Exception as e:
        logger.error(f"C: [LLM Definition] '{term}' 失败: {e}")
        logger.error(f"E: [LLM Definition] '{term}' failed: {e}")
        return "Definition unavailable."


# ---------------------------------------------------------
# C: MCP Tool 2: get_definition — 术语定义查询
# E: MCP Tool 2: get_definition — term definition lookup
# ---------------------------------------------------------
@mcp.tool()
def get_definition(term: str, detail_level: str = "medium",
                   language: str = "en",
                   session_ts: str | None = None) -> dict:
    """C: 获取术语定义。优先 Wikipedia API，失败时回退到 LLM。始终附加 IPA 音标和字面含义。
    IPA 和字面含义不受 detail_level 影响，作为独立的不可变基础信息层。
    参数 term: 要查询的术语。
    参数 detail_level: 定义详细程度 "brief"/"medium"/"detailed"（仅影响定义正文长度）。
    参数 language: Wikipedia 语言代码（如 "en", "zh"）。
    参数 session_ts: 可选的会话时间戳。
    返回: {"definition": str, "ipa": str, "literal_meaning": str, "source": "wikipedia"|"llm"|"none"}
    E: Get term definition. Wikipedia API first, LLM fallback. Always appends IPA and literal meaning.
    IPA and literal meaning are NOT affected by detail_level — they are an independent immutable info layer.
    Args term: The term to look up.
    Args detail_level: Definition detail "brief"/"medium"/"detailed" (affects definition length only).
    Args language: Wikipedia language code (e.g., "en", "zh").
    Args session_ts: Optional session timestamp.
    Returns: {"definition": str, "ipa": str, "literal_meaning": str, "source": "wikipedia"|"llm"|"none"}
    """
    logger.info(
        f"C: [get_definition] 查询 '{term}'，详细度={detail_level}，语言={language}"
    )
    logger.info(
        f"E: [get_definition] Looking up '{term}', detail={detail_level}, lang={language}"
    )

    # ---------------------------------------------------------
    # C: 阶段1 — 获取定义正文（Wikipedia → LLM 降级）
    # E: Phase 1 — Get definition text (Wikipedia → LLM fallback)
    # ---------------------------------------------------------
    definition = None
    source = "none"

    # C: 尝试 Wikipedia
    # E: Try Wikipedia
    wiki_extract = _fetch_wikipedia_summary(term, language)
    if wiki_extract:
        definition = wiki_extract
        source = "wikipedia"

    # C: Wikipedia 失败 → LLM 回退
    # E: Wikipedia failed → LLM fallback
    if definition is None:
        definition = _generate_llm_definition(term, detail_level)
        source = "llm" if definition != "Definition unavailable." else "none"

    # ---------------------------------------------------------
    # C: 阶段2 — 获取 IPA + 字面含义（固定基础信息层）
    #    detail_level 不影响此层
    # E: Phase 2 — Get IPA + literal meaning (fixed base info layer)
    #    detail_level does NOT affect this layer
    # ---------------------------------------------------------
    try:
        dict_result = lookup_dictionary(term, llm_client=llm_client,
                                        session_ts=session_ts)
        ipa = dict_result.get('ipa', '')
        literal_meaning = dict_result.get('literal_meaning', '')
    except Exception as e:
        logger.error(f"C: [get_definition] 词典查询失败: {e}")
        logger.error(f"E: [get_definition] Dictionary lookup failed: {e}")
        ipa = ""
        literal_meaning = ""

    # ---------------------------------------------------------
    # C: 阶段3 — 组装最终结果
    # E: Phase 3 — Assemble final result
    # ---------------------------------------------------------
    result = {
        "definition": definition,
        "ipa": ipa,
        "literal_meaning": literal_meaning,
        "source": source,
    }

    # C: 调试输出
    # E: Debug output
    debug_output = {
        "term": term,
        "detail_level": detail_level,
        "language": language,
        "definition": definition[:300] if definition else "",
        "definition_length": len(definition) if definition else 0,
        "ipa": ipa,
        "literal_meaning": literal_meaning,
        "source": source,
        "timestamp": datetime.now().isoformat(),
    }
    write_debug_file(
        filename="07_get_definition.json",
        content=debug_output,
        session_ts=session_ts,
        is_json=True,
    )

    logger.info(
        f"C: [get_definition] '{term}' → source={source}, "
        f"def_len={len(definition) if definition else 0}, "
        f"ipa={'✓' if ipa else '✗'}, lm={'✓' if literal_meaning else '✗'}"
    )
    logger.info(
        f"E: [get_definition] '{term}' → source={source}, "
        f"def_len={len(definition) if definition else 0}, "
        f"ipa={'✓' if ipa else '✗'}, lm={'✓' if literal_meaning else '✗'}"
    )

    return result


# ---------------------------------------------------------
# C: 启动入口 — stdio 传输模式
# E: Entry point — stdio transport mode
# ---------------------------------------------------------
if __name__ == "__main__":
    _init_models()
    logger.info("C: Dict-Underline MCP Server 启动 (stdio 模式)")
    logger.info("E: Dict-Underline MCP Server starting (stdio mode)")
    mcp.run(transport="stdio")
