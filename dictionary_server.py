# /home/akku/ai-mindmap-agent/dictionary_server.py
# C: 词典 Agent — 使用 LLM 生成 IPA 国际音标和字面含义
#    既可作为独立 MCP 服务运行（python dictionary_server.py），
#    也可作为模块导入（from dictionary_server import lookup_dictionary）
# E: Dictionary Agent — generates IPA transcription and literal meaning via LLM
#    Can run as standalone MCP server (python dictionary_server.py),
#    or imported as module (from dictionary_server import lookup_dictionary)
import json
import sys
import logging

from openai import OpenAI
from mcp.server.fastmcp import FastMCP

from config import Config
from mindmap_agent import write_debug_file

# C: 日志输出到 stderr，避免污染 stdio 协议通道
# E: Log to stderr to avoid polluting the stdio protocol channel
logging.basicConfig(
    level=logging.INFO,
    format="[Dictionary-Agent] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("dictionary-agent")

# C: MCP Server 实例
# E: MCP Server instance
mcp = FastMCP(
    name="dictionary-agent-server",
    instructions=(
        "C: 词典 Agent MCP Server — 提供术语的 IPA 国际音标和字面含义查询\n"
        "E: Dictionary Agent MCP Server — provides IPA transcription and literal meaning lookup"
    ),
)

# C: 全局 LLM 客户端
# E: Global LLM client
_llm_client: OpenAI | None = None


def _ensure_client():
    """C: 确保 LLM 客户端已初始化（懒加载）。
    E: Ensure LLM client is initialized (lazy loading)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAI(
            api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL
        )
        logger.info(f"C: 词典 Agent LLM 客户端就绪，模型={Config.LLM_MODEL}")
        logger.info(f"E: Dictionary Agent LLM client ready, model={Config.LLM_MODEL}")


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


def lookup_dictionary(term: str, llm_client: OpenAI | None = None,
                      session_ts: str | None = None) -> dict:
    """C: 使用 LLM 生成 IPA 国际音标和字面含义。
    参数:
      term: 要查询的术语
      llm_client: OpenAI 客户端（None = 使用全局客户端）
      session_ts: 会话时间戳（用于调试输出）
    返回: {"ipa": str, "literal_meaning": str}
    E: Generate IPA transcription and literal meaning via LLM.
    Args:
      term: The term to look up
      llm_client: OpenAI client (None = use global client)
      session_ts: Session timestamp (for debug output)
    Returns: {"ipa": str, "literal_meaning": str}
    """
    client = llm_client
    if client is None:
        _ensure_client()
        client = _llm_client

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
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
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
            # C: 降级 — 手动提取（有些模型可能不在 JSON 中包裹 IPA）
            # E: Degrade — manual extraction (some models may not wrap IPA in JSON)
            logger.warning(
                f"C: [lookup_dictionary] JSON 解析失败，尝试降级提取: {raw_text[:100]}"
            )
            logger.warning(
                f"E: [lookup_dictionary] JSON parse failed, attempting degradation: {raw_text[:100]}"
            )
            result = {"ipa": "", "literal_meaning": ""}

        ipa = result.get("ipa", "").strip()
        literal_meaning = result.get("literal_meaning", "").strip()

        # C: 调试输出
        # E: Debug output
        debug_result = {
            "term": term,
            "ipa": ipa,
            "literal_meaning": literal_meaning,
            "raw_response": raw_text[:500],
        }
        write_debug_file(
            filename="dictionary_lookup.json",
            content=debug_result,
            session_ts=session_ts,
            is_json=True,
        )

        logger.info(
            f"C: [lookup_dictionary] '{term}' → IPA={ipa[:40]}, LM={literal_meaning[:40]}"
        )
        logger.info(
            f"E: [lookup_dictionary] '{term}' → IPA={ipa[:40]}, LM={literal_meaning[:40]}"
        )

        return {"ipa": ipa, "literal_meaning": literal_meaning}

    except Exception as e:
        logger.error(f"C: [lookup_dictionary] '{term}' 失败: {e}")
        logger.error(f"E: [lookup_dictionary] '{term}' failed: {e}")
        return {"ipa": "", "literal_meaning": ""}


# ---------------------------------------------------------
# C: MCP Tool: lookup_dictionary
#    通过 MCP 协议暴露，方便 MCP Inspector 独立测试
# E: MCP Tool: lookup_dictionary
#    Exposed via MCP protocol for MCP Inspector standalone testing
# ---------------------------------------------------------
@mcp.tool()
def lookup_dictionary(term: str) -> dict:
    """C: 查询术语的 IPA 国际音标和字面含义。
    参数 term: 要查询的术语。
    返回: {"ipa": "国际音标", "literal_meaning": "字面含义"}
    E: Look up IPA transcription and literal meaning for a term.
    Args term: The term to look up.
    Returns: {"ipa": "IPA transcription", "literal_meaning": "literal meaning"}
    """
    logger.info(f"C: [MCP] lookup_dictionary 被调用: '{term}'")
    logger.info(f"E: [MCP] lookup_dictionary called: '{term}'")
    _ensure_client()
    return lookup_dictionary(term, llm_client=_llm_client)


# ---------------------------------------------------------
# C: 启动入口 — stdio 传输模式
# E: Entry point — stdio transport mode
# ---------------------------------------------------------
if __name__ == "__main__":
    _ensure_client()
    logger.info("C: 词典 Agent MCP Server 启动 (stdio 模式)")
    logger.info("E: Dictionary Agent MCP Server starting (stdio mode)")
    mcp.run(transport="stdio")
