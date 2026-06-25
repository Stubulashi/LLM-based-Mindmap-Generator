# /home/akku/ai-mindmap-agent/mindmap_agent.py
import json
import os
import sys
import logging
from datetime import datetime
from openai import OpenAI
from config import Config
from tools import get_mindmap_tools, get_concept_extraction_tools, get_hierarchy_planning_tools

# C: 日志输出到 stderr，避免污染 stdio 协议通道
# E: Log to stderr to avoid polluting the stdio protocol channel
logger = logging.getLogger("mindmap-agent")


# =========================================================
# C: 状态合并 — 将 LLM 输出的 delta 应用到当前导图
#    独立函数，供单模型和管线两种模式复用
# E: State Merge — apply LLM delta to current map
#    Standalone function, reusable by both single-model and pipeline modes
# =========================================================
def state_merge(delta: dict, current_map: dict) -> dict:
    nodes_dict = {str(n['id']): n for n in current_map.get('nodes', [])}
    links_list = list(current_map.get('links', []))

    # C: 添加新节点 / E: Add new nodes
    for n in delta.get('add_nodes', []):
        nodes_dict[str(n['id'])] = n

    # C: 更新旧节点 / E: Update existing nodes
    for u in delta.get('update_nodes', []):
        nid = str(u['id'])
        if nid in nodes_dict:
            if 'details' not in nodes_dict[nid]:
                nodes_dict[nid]['details'] = []
            nodes_dict[nid]['details'].extend(u.get('append_details', []))

    # C: 建立新连线 / E: Create new links
    for l in delta.get('add_links', []):
        if not any(
            el['source'] == l['source'] and el['target'] == l['target']
            for el in links_list
        ):
            links_list.append(l)

    # C: 处理删除 / E: Handle deletions
    for del_id in delta.get('delete_nodes', []):
        del_id_str = str(del_id)
        if del_id_str in nodes_dict:
            del nodes_dict[del_id_str]
        links_list = [
            l for l in links_list
            if str(l['source']) != del_id_str and str(l['target']) != del_id_str
        ]

    return {"nodes": list(nodes_dict.values()), "links": links_list}


# =========================================================
# C: Flat → G6 嵌套树转换
#    将 state_merge 产生的 flat nodes+links 转为 G6 可消费的嵌套树格式
# E: Flat → G6 nested tree conversion
#    Converts flat nodes+links from state_merge into G6-consumable nested tree
# =========================================================
def flatten_to_tree(nodes: list[dict], links: list[dict]) -> list[dict]:
    """C: 将扁平节点列表和连线列表转换为 G6 嵌套树结构。
    多根节点时自动包裹 _isVirtual 虚拟根节点确保树布局正常。
    E: Convert flat node list and link list into G6 nested tree structure.
    Auto-wraps multiple roots with _isVirtual virtual root for proper tree layout."""
    if not nodes:
        return []

    # C: 构建 children_map: parent_id → [child_node_dicts]
    # E: Build children_map: parent_id → [child_node_dicts]
    nodes_dict = {}
    for n in nodes:
        nid = str(n['id'])
        node_copy = {
            'id': nid,
            'label': n.get('label', ''),
            'color': n.get('color', '#e8f0fe'),
            'details': n.get('details', []),
            'parent_id': n.get('parent_id'),
            'collapsed': n.get('collapsed', False),
            'children': [],
            '_isVirtual': False,
            '_isRoot': False,
            '_depth': 0,
            '_hasChildren': False,
        }
        nodes_dict[nid] = node_copy

    # C: 建立父子关系
    # E: Build parent-child relationships
    child_ids_by_parent = {}
    for link in links:
        src = str(link['source'])
        tgt = str(link['target'])
        if src in nodes_dict and tgt in nodes_dict:
            if src not in child_ids_by_parent:
                child_ids_by_parent[src] = []
            child_ids_by_parent[src].append(tgt)
            # C: 同时设置 parent_id（如果节点没有的话）
            # E: Also set parent_id if node doesn't have one
            if not nodes_dict[tgt].get('parent_id'):
                nodes_dict[tgt]['parent_id'] = src

    # C: 递归构建 children 列表
    # E: Recursively build children list
    def build_children(nid):
        node = nodes_dict.get(nid)
        if not node:
            return
        child_ids = child_ids_by_parent.get(nid, [])
        if child_ids:
            node['_hasChildren'] = True
            for cid in child_ids:
                child_node = nodes_dict.get(cid)
                if child_node:
                    build_children(cid)
                    node['children'].append(child_node)

    # C: 找出根节点（无父节点、或父节点不在当前节点集内）
    # E: Find root nodes (no parent_id, or parent not in current node set)
    roots = []
    for nid, node in nodes_dict.items():
        pid = node.get('parent_id')
        if not pid or pid not in nodes_dict:
            build_children(nid)
            node['_isRoot'] = True
            roots.append(node)

    # C: 多根节点 → 包裹虚拟根
    # E: Multiple roots → wrap with virtual root
    if len(roots) > 1:
        virtual_root = {
            'id': '__virtual_root__',
            'label': '',
            'color': 'transparent',
            'details': [],
            'parent_id': None,
            'collapsed': False,
            'children': roots,
            '_isVirtual': True,
            '_isRoot': True,
            '_depth': -1,
            '_hasChildren': True,
        }
        mark_tree_meta([virtual_root], 0)
        return [virtual_root]
    elif len(roots) == 1:
        mark_tree_meta(roots, 0)
        return roots
    else:
        return []


def mark_tree_meta(roots: list[dict], depth: int) -> None:
    """C: 递归标记树节点的 _depth, _isRoot, _hasChildren 元数据。
    E: Recursively mark _depth, _isRoot, _hasChildren metadata on tree nodes."""
    for node in roots:
        node['_depth'] = depth
        children = node.get('children', [])
        if children:
            node['_hasChildren'] = True
            mark_tree_meta(children, depth + 1)
        else:
            node['_hasChildren'] = False


def flatten_from_tree(roots: list[dict]) -> tuple[list[dict], list[dict]]:
    """C: 从嵌套树反序列化为 flat nodes+links（用于 current_map 回传）。
    E: Deserialize nested tree back to flat nodes+links (for current_map round-trip)."""
    flat_nodes = []
    flat_links = []

    def traverse(node, parent_id=None):
        if node.get('_isVirtual'):
            for child in node.get('children', []):
                traverse(child, None)
            return
        n = {
            'id': node['id'],
            'label': node.get('label', ''),
            'color': node.get('color', '#e8f0fe'),
            'details': node.get('details', []),
            'parent_id': parent_id,
            'collapsed': node.get('collapsed', False),
        }
        flat_nodes.append(n)
        if parent_id:
            flat_links.append({
                'source': parent_id,
                'target': node['id'],
                'link_type': 'solid'
            })
        for child in node.get('children', []):
            traverse(child, node['id'])

    for root in roots:
        traverse(root, None)
    return flat_nodes, flat_links


# =========================================================
# C: state_merge_result — 合并 delta 并输出 flat + tree
#    替代原 state_merge，同时返回 G6 嵌套树
# E: state_merge_result — merge delta and output flat + tree
#    Replaces original state_merge, also returns G6 nested tree
# =========================================================
def state_merge_with_tree(delta: dict, current_map: dict) -> dict:
    """C: 执行 state_merge 并将结果转为 flat+tree 格式。
    E: Execute state_merge and convert result to flat+tree format."""
    merged = state_merge(delta, current_map)
    merged_nodes = merged.get('nodes', [])
    merged_links = merged.get('links', [])
    tree = flatten_to_tree(merged_nodes, merged_links)
    return {
        "tree": tree,
        "nodes": merged_nodes,
        "links": merged_links,
    }


# =========================================================
# C: 基础 Agent — 封装 LLM 客户端初始化和 function calling 调用
# E: Base Agent — encapsulates LLM client init and function calling
# =========================================================
class _BaseAgent:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    @staticmethod
    def _safe_json_parse(text: str) -> dict:
        """C: 安全 JSON 解析 — 自动修复 LLM 返回的截断或格式错误的 JSON。
        修复策略（按优先级）:
          1. 直接解析（正常情况）
          2. 提取 markdown 代码块（```json ... ``` 或 ``` ... ```）
          3. 补全截断 JSON（缺失闭合括号/大括号）
          4. 正则提取完整 JSON 对象
          5. 暴力尝试各种闭合序列
        E: Safe JSON parsing — auto-repair truncated or malformed JSON from LLM.
        Repair strategies (by priority):
          1. Direct parse (normal case)
          2. Extract from markdown code blocks
          3. Complete truncated JSON (missing brackets/braces)
          4. Regex extract complete JSON objects
          5. Brute-force various closing sequences
        """
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

        # Strategy 3: Complete missing closing brackets/braces using LIFO stack
        # C: 模拟 JSON 解析器维护 LIFO 栈，确保闭合顺序正确
        #    关键修复：旧版将所有 } 排在所有 ] 前面（"}}]]"），
        #    但 JSON 要求后进先出（如 {"...[..."Mo → 应闭合为 "}]}]）
        # E: Simulate JSON parser maintaining LIFO stack for correct closing order
        #    Key fix: old version put all } before all ] ("}}]]"),
        #    but JSON requires LIFO (e.g. {"...[..."Mo → must close as "}]}])
        stack = []   # C: 未闭合定界符栈（{, [, "） / E: Unclosed delimiter stack
        in_str = False
        escaped = False

        for ch in text_stripped:
            if escaped:
                escaped = False
                continue
            if ch == '\\':
                escaped = True
                continue
            if ch == '"':
                if in_str:
                    # C: 闭合字符串 → 弹出栈顶 "
                    # E: Close string → pop stack
                    if stack and stack[-1] == '"':
                        stack.pop()
                else:
                    # C: 开启字符串 → 压栈
                    # E: Open string → push stack
                    stack.append('"')
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch in '{[':
                stack.append(ch)
            elif ch == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif ch == ']':
                if stack and stack[-1] == '[':
                    stack.pop()

        # C: 处理截断在字符串中间的情况（如 "Key Point: Mo）
        # E: Handle truncated mid-string case (e.g. "Key Point: Mo)
        if in_str:
            # C: 未闭合的字符串不在栈中则补入
            # E: Push unclosed string to stack if not already there
            if not stack or stack[-1] != '"':
                stack.append('"')

        if stack:
            # C: LIFO 逆序闭合：{→}  [→]  "→"
            # E: LIFO reverse close: {→}  [→]  "→"
            closer_map = {'{': '}', '[': ']', '"': '"'}
            closers = [closer_map[item] for item in reversed(stack)]
            repaired = text_stripped + ''.join(closers)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

            # C: 备选：尝试在末尾额外追加一层闭合（某些模型输出缺少最外层）
            # E: Fallback: try appending an extra closing layer
            for extra in ['}', ']', '"']:
                try:
                    return json.loads(text_stripped + ''.join(closers) + extra)
                except json.JSONDecodeError:
                    continue

        # Strategy 3b: Strip back incomplete trailing element before reapplying closers
        # C: 截断可能发生在对象/数组的中间位置（如 {"key 截断在键名中间），
        #    此时标准 LIFO 补全产生无效 JSON（{"key"} 键缺值）。
        #    策略：从末尾逐字符回溯，在逗号或结构边界处截断后重新补全。
        # E: Truncation may happen mid-element (e.g. {"key truncated mid-key),
        #    standard LIFO completion produces invalid JSON ({"key"} key without value).
        #    Strategy: backtrack from end, cut at comma/structure boundary, recomplete.
        cut_points = []  # C: 收集可截断位置（逗号或完整闭合处）/ E: Collect cuttable positions
        in_s = False
        esc = False
        s_depth = []
        for i, ch in enumerate(text_stripped):
            if esc:
                esc = False
                continue
            if ch == '\\':
                esc = True
                continue
            if ch == '"':
                in_s = not in_s
                continue
            if in_s:
                continue
            if ch == ',':
                # C: 逗号处说明上一个元素是完整的 / E: Comma means previous element is complete
                if not s_depth or s_depth[-1] in '{[':
                    cut_points.append(i + 1)  # C: 保留逗号 / E: Keep the comma
            elif ch in '{[':
                s_depth.append(ch)
            elif ch == '}':
                if s_depth and s_depth[-1] == '{':
                    s_depth.pop()
                    if not s_depth:
                        cut_points.append(i + 1)
            elif ch == ']':
                if s_depth and s_depth[-1] == '[':
                    s_depth.pop()
                    if not s_depth:
                        cut_points.append(i + 1)

        # C: 从最后的截断点向前尝试 / E: Try from last cut point backwards
        for cut in reversed(cut_points[-10:]):  # C: 最多尝试最后10个 / E: Try at most last 10
            truncated = text_stripped[:cut].rstrip(', \t\n\r')
            if not truncated:
                continue
            # C: 对截断后的文本重新计算 LIFO 闭合 / E: Recompute LIFO closers for truncated text
            s2 = []
            i2 = False
            e2 = False
            for ch in truncated:
                if e2:
                    e2 = False
                    continue
                if ch == '\\':
                    e2 = True
                    continue
                if ch == '"':
                    i2 = not i2
                    if i2:
                        s2.append('"')
                    elif s2 and s2[-1] == '"':
                        s2.pop()
                    continue
                if i2:
                    continue
                if ch in '{[':
                    s2.append(ch)
                elif ch == '}':
                    if s2 and s2[-1] == '{':
                        s2.pop()
                elif ch == ']':
                    if s2 and s2[-1] == '[':
                        s2.pop()
            if i2 and (not s2 or s2[-1] != '"'):
                s2.append('"')
            if s2:
                c2 = [closer_map[it] for it in reversed(s2)]
                try:
                    return json.loads(truncated + ''.join(c2))
                except json.JSONDecodeError:
                    continue

        # Strategy 4: Extract complete JSON objects from garbled text
        # C: 尝试匹配最外层 {...} 对象（含嵌套）
        # E: Try to match outermost {...} objects (including nested)
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

        # Strategy 5: Brute-force various closing sequences
        brute_closers = [
            ']', '}]', '"]', '"}]', '}]', '"}]', '}]",',
            '}]"', '}]}', '}"}]', '"}]",',
        ]
        for closer in brute_closers:
            try:
                return json.loads(text_stripped + closer)
            except json.JSONDecodeError:
                continue

        # Strategy 6: Find last complete JSON object by iterating backwards
        for cutoff in range(len(text_stripped) - 1, max(len(text_stripped) - 200, 0), -1):
            for appendix in ['}', '"]', '}]', '}"}]']:
                try:
                    return json.loads(text_stripped[:cutoff] + appendix)
                except json.JSONDecodeError:
                    continue

        raise json.JSONDecodeError(
            f"Unable to repair JSON after all strategies: {text_stripped[:300]}...",
            text_stripped, 0
        )

    def _call_llm_tool(self, system_prompt: str, user_prompt: str,
                       tools: list, tool_choice_name: str,
                       max_tokens: int = 8192, retry_on_json_error: bool = True) -> dict:
        """C: 通用 LLM function calling 封装，含 JSON 容错与自动重试。
        E: Generic LLM function calling wrapper with JSON resilience and auto-retry."""

        def _do_call():
            """C: 执行单次 LLM 调用 / E: Execute a single LLM call."""
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": tool_choice_name}},
                max_tokens=max_tokens
            )

        response = _do_call()

        # C: 检查 tool_calls 是否存在
        # E: Check if tool_calls exist
        if not response.choices[0].message.tool_calls:
            logger.warning(
                f"C: [_call_llm_tool] LLM 未返回 tool_calls，将重试"
            )
            logger.warning(
                f"E: [_call_llm_tool] LLM returned no tool_calls, will retry"
            )
            if retry_on_json_error:
                # C: 重试时提示 LLM 必须调用工具
                # E: Prompt LLM to call the tool on retry
                retry_user_prompt = (
                    user_prompt + "\n\n"
                    "C: 【重要】你必须调用 extract_concepts 工具来提交结果，不能直接返回文本。\n"
                    "E: [IMPORTANT] You MUST call the extract_concepts tool to submit results, do NOT return plain text."
                )
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": retry_user_prompt}
                    ],
                    tools=tools,
                    tool_choice={"type": "function", "function": {"name": tool_choice_name}},
                    max_tokens=max_tokens
                )

        # C: 二次检查 / E: Double-check
        if not response.choices[0].message.tool_calls:
            raise ValueError(
                f"C: LLM 两次调用均未返回 tool_calls\n"
                f"E: LLM returned no tool_calls in both attempts"
            )

        tool_call = response.choices[0].message.tool_calls[0]
        raw_args = tool_call.function.arguments

        # C: 尝试解析 JSON，失败时使用修复策略
        # E: Try JSON parse, use repair strategies on failure
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError as e:
            logger.warning(
                f"C: [_call_llm_tool] JSON 解析失败: {e}，尝试自动修复..."
            )
            logger.warning(
                f"E: [_call_llm_tool] JSON parse failed: {e}, attempting auto-repair..."
            )
            logger.info(
                f"C: [_call_llm_tool] 原始响应（前500字符）: {raw_args[:500]}"
            )
            logger.info(
                f"E: [_call_llm_tool] Raw response (first 500 chars): {raw_args[:500]}"
            )

            # C: 尝试自动修复
            # E: Attempt auto-repair
            try:
                repaired = self._safe_json_parse(raw_args)
                logger.info(
                    f"C: [_call_llm_tool] JSON 自动修复成功"
                )
                logger.info(
                    f"E: [_call_llm_tool] JSON auto-repair succeeded"
                )
                return repaired
            except json.JSONDecodeError as repair_error:
                logger.error(
                    f"C: [_call_llm_tool] JSON 自动修复也失败: {repair_error}"
                )
                logger.error(
                    f"E: [_call_llm_tool] JSON auto-repair also failed: {repair_error}"
                )

                if retry_on_json_error:
                    # C: 重试：告知 LLM 上次返回了非法 JSON，请其重新生成
                    # E: Retry: inform LLM that previous response was invalid JSON
                    retry_user_prompt = (
                        user_prompt + "\n\n"
                        f"C: 【错误反馈】上次你返回的 JSON 无法解析: {e}"
                        "\n请确保返回格式正确的 JSON，调用工具提交。\n"
                        f"E: [Error Feedback] Your previous JSON was unparseable: {e}"
                        "\nPlease ensure you return properly formatted JSON via the tool call."
                    )
                    response = self.client.chat.completions.create(
                        model=self.model,
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
                            f"C: 重试后 LLM 仍未返回 tool_calls\n"
                            f"E: LLM still returned no tool_calls after retry"
                        )

                    tool_call = response.choices[0].message.tool_calls[0]
                    raw_args_retry = tool_call.function.arguments

                    try:
                        return json.loads(raw_args_retry)
                    except json.JSONDecodeError as e2:
                        # C: 重试后仍失败，再试一次修复
                        # E: Still failed after retry, try repair one more time
                        try:
                            repaired = self._safe_json_parse(raw_args_retry)
                            logger.info(
                                f"C: [_call_llm_tool] 重试后 JSON 修复成功"
                            )
                            logger.info(
                                f"E: [_call_llm_tool] JSON repaired after retry"
                            )
                            return repaired
                        except json.JSONDecodeError:
                            raise ValueError(
                                f"C: LLM 重试后 JSON 仍无法解析: {e2}\n"
                                f"原始响应: {raw_args_retry[:500]}\n"
                                f"E: JSON still unparseable after LLM retry: {e2}\n"
                                f"Raw response: {raw_args_retry[:500]}"
                            ) from e2
                else:
                    raise ValueError(
                        f"C: JSON 解析失败（未启用重试）: {e}\n"
                        f"原始响应: {raw_args[:500]}\n"
                        f"E: JSON parse failed (retry disabled): {e}\n"
                        f"Raw response: {raw_args[:500]}"
                    ) from e


class MindMapSpecialistAgent(_BaseAgent):
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None):
        # C: 继承 _BaseAgent，支持可选的模型配置覆盖（默认从 Config 读取）
        #    DeltaGenerationAgent 通过传入参数覆盖模型，MindMapSpecialistAgent 使用默认值
        # E: Extends _BaseAgent, supports optional model config override
        #    DeltaGenerationAgent overrides via params, MindMapSpecialistAgent uses defaults
        api_key = api_key or Config.LLM_API_KEY
        base_url = base_url or Config.LLM_BASE_URL
        model = model or Config.LLM_MODEL
        super().__init__(api_key, base_url, model)
        self.tools = get_mindmap_tools()

    def _get_system_prompt(self):
        # C: 返回系统提示词（中英双语），根据 DETAILS_ENRICHMENT_ENABLED 动态调整规则3
        # E: Return system prompt (bilingual CN/EN), dynamically adjusts rule 3 based on DETAILS_ENRICHMENT_ENABLED

        # C: 规则3 — 根据配置决定 AI 回复内容的使用策略
        # E: Rule 3 — determine AI reply content usage strategy based on config
        if Config.DETAILS_ENRICHMENT_ENABLED:
            rule3_cn = (
                "3. Details 层次化补充：【AI回复说】中对概念的定义、解释、关键点、举例等，"
                "可按条目化方式追加到对应节点的 details 数组中。"
                "每条以简洁前缀标识来源和类型（如 '定义:'、'关键点:'、'上下文:'、'用户原文:'），前缀文本语言必须与用户输入语言一致。"
                "严禁将 AI 的分析逻辑创建为独立节点（元节点）——AI 内容只能作为已有节点的 details 补充。"
            )
            rule3_en = (
                "3. Hierarchical Details Enrichment: Definitions, explanations, key points, and examples "
                "from [AI Replies] may be appended as structured entries to the corresponding node's details array. "
                "Prefix each entry with a concise source/type tag (e.g., 'Definition:', 'Key Point:', "
                "'Context:', 'User Input:'), and the tag language must match the user's input language. "
                "Strictly prohibit creating standalone nodes (meta-nodes) from AI analytical logic — "
                "AI content may only serve as details enrichment for existing nodes."
            )
        else:
            rule3_cn = (
                "3. 屏蔽 AI 发散：【AI回复说】的内容仅作为语境参考。"
                "你的图谱实体提取必须 100% 以用户提供的词汇为准。"
            )
            rule3_en = (
                "3. Block AI divergence: the content of [AI Replies] is for contextual reference only. "
                "Your graph entity extraction must be 100% based on the vocabulary provided by the user."
            )

        return f"""C: 你是一个专业的 MCP 思维导图绘图引擎，遵循 ReAct（Reasoning + Acting）模式工作。
你的任务是：根据对话历史，对当前导图进行【增量修改】，而非从头重建。
E: You are a professional MCP mind map drawing engine following the ReAct (Reasoning + Acting) mode.
Your task is to make incremental modifications to the current mind map based on conversation history, rather than rebuilding from scratch.

C: 【核心铁律 - 必须严格遵守】
1. 绝对服从用户：【用户说】的内容具有绝对的权威。即使用户的逻辑是荒诞的、无厘头的或违反常理的，你也必须严格按照用户的概念拓扑直接建图。
2. 严禁生成"元节点（Meta-nodes）"：绝对不要将 AI 的逻辑分析、说教或总结画进导图。画布只用来呈现用户指定的客观概念。
{rule3_cn}
E: [Core Iron Laws - Must Strictly Follow]
1. Absolute obedience to the user: the content of [User Says] has absolute authority. Even if the user's logic is absurd, nonsensical, or violates common sense, you must strictly build the map according to the user's conceptual topology.
2. Strictly prohibit generating meta-nodes: never draw AI's logical analysis, preaching, or summaries into the mind map. The canvas is only for presenting objective concepts specified by the user.
{rule3_en}

C: 【ReAct 工作流程 - 每轮调用前必须在心中完成】
步骤一（READ）：阅读当前导图全量结构。识别已有节点、它们的父子关系、以及各节点的 details 内容。
步骤二（REASON）：对照近期对话，推理需要做什么：
  - 对话中出现了哪些新概念？→ 用 add_nodes 创建，精简为原子化标签
  - 哪些概念是对已有节点的补充？→ 用 update_nodes 追加 details
  - 哪些新关系需要建立？→ 用 add_links 连接
  - 哪些内容已被推翻或冗余？→ 用 delete_nodes 移除
步骤三（ACT）：调用 modify_mind_map 工具，只传递增量差异（delta），不要重建整个 map。
E: [ReAct Workflow - Must Complete Internally Before Each Call]
Step 1 (READ): Read the full structure of the current mind map. Identify existing nodes, their parent-child relationships, and the details content of each node.
Step 2 (REASON): Compare with recent conversation and reason about what needs to be done:
  - What new concepts appeared in the conversation? → Use add_nodes to create them, condensed into atomic labels
  - Which concepts supplement existing nodes? → Use update_nodes to append details
  - What new relationships need to be established? → Use add_links to connect them
  - What content has been invalidated or is redundant? → Use delete_nodes to remove them
Step 3 (ACT): Call the modify_mind_map tool, only passing the incremental delta, do not rebuild the entire map.

C: 【原子化标签规则 - 必须严格遵守】
1. 节点 label 必须是精简的核心名词或短语，最多 2 个词。
2. 严禁使用完整句子作为 label！例如：
   -错误：'chicken has rabbies'
   - 正确：label='Rabies', details=['Discussed that chickens can have rabbies']
   - 错误：'I am a cat that likes fish'
   - 正确：label='Cat', details=['Likes fish', 'Self-identifies as a cat']
3. 所有解释性、描述性、逻辑性内容必须放入 details 数组。
E: [Atomic Label Rules - Must Strictly Follow]
1. Node labels must be concise core nouns or phrases, at most 2 words.
2. Strictly prohibit using full sentences as labels! Examples:
   - Wrong: 'chicken has rabbies'
   - Correct: label='Rabies', details=['Discussed that chickens can have rabbies']
   - Wrong: 'I am a cat that likes fish'
   - Correct: label='Cat', details=['Likes fish', 'Self-identifies as a cat']
3. All explanatory, descriptive, and logical content must be placed in the details array.

C: 【常规绘图规则】
4. 建立纵深与层级，使用 add_links 连接父子节点（source=父, target=子）。
5. 不要重复创建：如果节点已存在，使用 update_nodes 追加详情到其 details。
E: [General Drawing Rules]
4. Establish depth and hierarchy by using add_links to connect parent and child nodes (source=parent, target=child).
5. Do not create duplicates: if a node already exists, use update_nodes to append details to its details array.

C: 7. 关联更新机制与层级隔离（重点）：当用户为现有的某个概念（如节点A）添加特征、附属物或下级概念（如节点B）时，你必须同时进行两步操作：
   - 第一步：使用 add_nodes 创建新节点 B，并使用 add_links 将其与 A 连接。
   - 第二步：必须使用 update_nodes，将这个新特征的描述语句追加到直接相关节点（A）的 details 属性中。
   - 【禁止追溯原则】：绝对禁止向上追溯！只能更新直接父节点 A，绝对不允许将该细节跨层级更新到 A 的父节点、祖父节点等更上层级中。
E: 7. Associative Update Mechanism and Hierarchical Isolation (Important): When the user adds a feature, attachment, or subordinate concept (e.g., Node B) to an existing concept (e.g., Node A), you must perform two operations simultaneously:
   - Step 1: Use add_nodes to create the new Node B, and use add_links to connect it to A.
   - Step 2: Use update_nodes to append the descriptive statement of this new feature to the details property of the directly related node (A).
   - [No Upward Propagation Principle]: Absolutely prohibit upward propagation! Only update the direct parent Node A. It is absolutely forbidden to propagate this detail across levels to A's parent, grandparent, or higher levels.

C: 【语言规则 - 必须严格遵守】
8. 检测用户使用的语言（English, 中文, Deutsch, Français, Español, 日本語 等）。
9. 所有 label 和 details 必须与用户输入语言完全一致。
10. 绝对不要将节点内容切换为其他语言，包括中文。
E: [Language Rules - Must Strictly Follow]
8. Detect the language used by the user (English, 中文, Deutsch, Français, Español, 日本語, etc.).
9. All labels and details must exactly match the language of the user's input.
10. Never switch node content to any other language, including Chinese."""

    def _build_react_prompt(self, chat_history: str, current_map: dict,
                            extra_prefix: str = "") -> str:
        """C: 构建 ReAct 格式的用户提示词。
        extra_prefix 非空时（v2 管线：注入概念提取+层级规划结果），
        调整 ReAct 步骤描述以适应预规划模式。
        E: Build ReAct-formatted user prompt.
        When extra_prefix is non-empty (v2 pipeline: injects concept+hierarchy results),
        adjusts ReAct step descriptions to fit pre-planning mode."""
        nodes_json = json.dumps(current_map.get('nodes', []), ensure_ascii=False)
        links_json = json.dumps(current_map.get('links', []), ensure_ascii=False)

        if extra_prefix:
            # C: v2 管线模式 — ReAct 步骤提示包含预规划引用
            # E: v2 pipeline mode — ReAct step hints include pre-planning references
            step1_cn = "先阅读上方导图结构和预提取的概念/层级规划"
            step2_cn = "再根据对话内容推理需要的增量修改（以预规划为强参考，必要时可微调）"
            step1_en = "First read the mind map structure above and the pre-extracted concepts/hierarchy plan"
            step2_en = "Then reason about the incremental modifications needed (use the pre-plan as strong reference, fine-tune if necessary)"
        else:
            # C: v1 单模型模式 — 标准 ReAct 步骤
            # E: v1 single-model mode — standard ReAct steps
            step1_cn = "先阅读上方导图结构，理解现有节点和层级关系"
            step2_cn = "再根据对话内容推理需要的增量修改"
            step1_en = "First read the mind map structure above and understand the existing nodes and hierarchy"
            step2_en = "Then reason about the incremental modifications needed based on the conversation content"

        standard_prompt = f"""C: 【当前导图全量状态 - 请仔细阅读】
节点列表: {nodes_json}
连线列表: {links_json}

【最新对话上下文】
{chat_history}

---
请按照 ReAct 模式处理：
1. {step1_cn}
2. {step2_cn}
3. 最后调用 modify_mind_map 工具提交增量 delta
E: [Current Mind Map Full State - Please Read Carefully]
Nodes: {nodes_json}
Links: {links_json}

[Latest Conversation Context]
{chat_history}

---
Please process in ReAct mode:
1. {step1_en}
2. {step2_en}
3. Finally call the modify_mind_map tool to submit the incremental delta"""

        return extra_prefix + standard_prompt

    def _execute_and_merge(self, prompt: str, current_map: dict):
        """C: 执行 LLM function calling + state_merge_with_tree。
        返回 (delta_dict, tree_map_dict) 元组，其中 tree_map 包含 tree/nodes/links。
        继承 _BaseAgent._call_llm_tool 的 JSON 容错和重试能力。
        E: Execute LLM function calling + state_merge_with_tree.
        Returns (delta_dict, tree_map_dict) tuple, where tree_map contains tree/nodes/links.
        Inherits _BaseAgent._call_llm_tool's JSON resilience and retry capability."""
        delta = self._call_llm_tool(
            system_prompt=self._get_system_prompt(),
            user_prompt=prompt,
            tools=self.tools,
            tool_choice_name="modify_mind_map"
        )
        merged = state_merge_with_tree(delta, current_map)
        return delta, merged

    def generate_map_from_context(self, chat_history: str, current_map: dict) -> dict:
        # C: 构建 ReAct 式输入提示词并执行
        # E: Construct ReAct-style input prompt and execute
        prompt = self._build_react_prompt(chat_history, current_map)

        try:
            _delta, merged = self._execute_and_merge(prompt, current_map)
            return merged
        except Exception as e:
            logger.error(f"C: [MindMap Agent] 增量绘图失败: {e}")
            logger.error(f"E: [MindMap Agent] Incremental drawing failed: {e}")
            return current_map


# =========================================================
# C: 阶段1 — 概念提取 Agent（轻量模型）
#    从对话中提取原子化概念，仅关注"用户说了什么"
# E: Stage 1 — Concept Extraction Agent (lightweight model)
#    Extracts atomic concepts from conversation, focusing only on user input
# =========================================================
class ConceptExtractionAgent(_BaseAgent):
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(api_key, base_url, model)
        self.tools = get_concept_extraction_tools()

    def _get_system_prompt(self) -> str:
        # C: 根据 DETAILS_ENRICHMENT_ENABLED 动态调整概念提取策略
        # E: Dynamically adjust concept extraction strategy based on DETAILS_ENRICHMENT_ENABLED
        if Config.DETAILS_ENRICHMENT_ENABLED:
            rule1_cn = (
                "1. 绝对服从用户：节点的 label 必须基于【用户说】中的客观概念。"
                "AI 回复中对该概念的定义、解释、关键点等可作为 details 的补充来源，"
                "按条目化方式追加（每条以 '定义:'、'关键点:' 等前缀标识），前缀文本语言必须与用户输入语言一致。"
                "严禁将 AI 的分析总结创建为独立节点。"
            )
            rule1_en = (
                "1. Absolute obedience to user: node labels must be based on objective concepts "
                "from [User Says]. Definitions, explanations, and key points from AI replies "
                "may serve as supplementary details, appended as structured entries "
                "(prefixed with 'Definition:', 'Key Point:', etc.), and the tag language must match the user's input language. "
                "Strictly prohibit creating standalone nodes from AI analysis."
            )
        else:
            rule1_cn = (
                "1. 绝对服从用户：只提取【用户说】中的客观概念，严禁提取 AI 回复中的分析、总结或说教。"
            )
            rule1_en = (
                "1. Absolute obedience to user: only extract objective concepts from [User Says], "
                "strictly prohibit extracting AI's analysis, summaries, or preaching."
            )

        return f"""C: 你是一个专业的概念提取器。你的任务是：从对话中提取用户提及的核心概念。
E: You are a professional concept extractor. Your task: extract core concepts mentioned by the user.

C: 【核心铁律 - 必须严格遵守】
{rule1_cn}
2. 原子化标签：每个概念的 label 必须是精简的核心名词或短语（≤2词）。
   - 错误：'I think machine learning is important'
   - 正确：label='Machine Learning', details=['User emphasized its importance']
3. 所有解释性、描述性内容必须放入 details 数组。
4. 不要重复：如果某个概念已经存在于当前导图中，不要再次提取。
5. 语言一致性：所有 label 和 details 必须与用户输入语言完全一致。
E: [Core Iron Laws - Must Strictly Follow]
{rule1_en}
2. Atomic labels: each concept label must be a concise core noun or phrase (≤2 words).
   - Wrong: 'I think machine learning is important'
   - Correct: label='Machine Learning', details=['User emphasized its importance']
3. All explanatory and descriptive content must be placed in the details array.
4. No duplicates: if a concept already exists in the current mind map, do not extract it again.
5. Language consistency: all labels and details must match the user's input language exactly."""

    def extract(self, chat_history: str, current_map: dict) -> list[dict]:
        """C: 从对话中提取概念列表。
        E: Extract concept list from conversation."""
        existing_ids = {str(n['id']) for n in current_map.get('nodes', [])}
        existing_labels = {str(n.get('label', '')).lower() for n in current_map.get('nodes', [])}

        # C: 根据 DETAILS_ENRICHMENT_ENABLED 决定对话内容的处理方式
        # E: Determine conversation processing based on DETAILS_ENRICHMENT_ENABLED
        if Config.DETAILS_ENRICHMENT_ENABLED:
            chat_instruction_cn = (
                "C: 【对话内容 - 从用户消息提取概念 label，从 AI 回复提炼 details 条目】\n"
            )
            chat_instruction_en = (
                "E: [Conversation - Extract concept labels from user messages, "
                "refine details entries from AI reply]\n"
            )
            final_instruction_cn = (
                "C: 请提取用户提及的新概念（排除已存在的节点），同时从 AI 回复中提炼"
                "与各概念相关的定义、解释、关键点作为 details 条目。调用 extract_concepts 工具提交。\n"
            )
            final_instruction_en = (
                "E: Please extract new concepts mentioned by the user (exclude existing nodes), "
                "and refine definitions, explanations, and key points from AI replies "
                "as details entries. Call the extract_concepts tool."
            )
        else:
            chat_instruction_cn = (
                "C: 【对话内容 - 仅从\"用户说\"部分提取概念】\n"
            )
            chat_instruction_en = (
                "E: [Conversation - Extract concepts only from user messages]\n"
            )
            final_instruction_cn = (
                "C: 请提取用户提及的新概念（排除已存在的节点），调用 extract_concepts 工具提交。\n"
            )
            final_instruction_en = (
                "E: Please extract new concepts mentioned by the user (exclude existing nodes), "
                "call the extract_concepts tool."
            )

        prompt = f"""C: 【当前导图已有节点 - 避免重复提取】
节点: {json.dumps([{'id': n['id'], 'label': n['label']} for n in current_map.get('nodes', [])], ensure_ascii=False)}

{chat_instruction_cn}
{chat_history}

---
{final_instruction_cn}
{chat_instruction_en}
{chat_history}

---
{final_instruction_en}"""

        logger.info(
            f"C: [ConceptExtraction] 开始提取，当前节点数={len(existing_ids)}，模型={self.model}"
        )
        logger.info(
            f"E: [ConceptExtraction] Starting extraction, existing nodes={len(existing_ids)}, model={self.model}"
        )

        result = self._call_llm_tool(
            system_prompt=self._get_system_prompt(),
            user_prompt=prompt,
            tools=self.tools,
            tool_choice_name="extract_concepts"
        )
        concepts = result.get('concepts', [])

        logger.info(
            f"C: [ConceptExtraction] 提取完成，新概念数={len(concepts)}"
        )
        logger.info(
            f"E: [ConceptExtraction] Done, new concepts={len(concepts)}"
        )
        return concepts


# =========================================================
# C: 阶段2 — 层级规划 Agent（中等模型）
#    将新概念与已有节点组织为有深度的层级树
# E: Stage 2 — Hierarchy Planning Agent (medium model)
#    Organizes new concepts with existing nodes into a deep hierarchy tree
# =========================================================
class HierarchyPlanningAgent(_BaseAgent):
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(api_key, base_url, model)
        self.tools = get_hierarchy_planning_tools()

    def _get_system_prompt(self) -> str:
        return """C: 你是一个专业的层级结构规划器。你的任务是：将新概念与已有节点组织为有深度的树状层级。
E: You are a professional hierarchy planner. Your task: organize new concepts with existing nodes into a deep tree hierarchy.

C: 【层级规划铁律 - 必须严格遵守】
1. 建立纵深：严禁将所有新节点平铺在同一层级。必须构建至少 2-3 层的树状结构。
2. 语义挂载：优先将新概念挂载到语义最相关的已有节点下。根级概念可挂载为顶级节点（无 parent）。
3. 父子关系清晰：每个新概念必须明确其父节点（parent_id）。如果找不到合适的已有父节点，选择最相关的同级概念作为兄弟节点。
4. 连线类型：直接从属用 solid，间接相关或参考用 dashed。
5. 只能引用存在的 ID：parent_id 和 child_id 必须来自「已有节点 + 新概念」的 ID 集合。
E: [Hierarchy Planning Iron Laws - Must Strictly Follow]
1. Build depth: strictly prohibit flattening all new nodes at the same level. Must build at least 2-3 layers of tree structure.
2. Semantic attachment: prioritize attaching new concepts under the most semantically relevant existing nodes. Root-level concepts can be top-level nodes (no parent).
3. Clear parent-child: each new concept must have an explicit parent (parent_id). If no suitable existing parent, choose the most relevant sibling concept.
4. Link types: solid for direct subordination, dashed for indirect relation or reference.
5. Only reference existing IDs: parent_id and child_id must come from the set of [existing nodes + new concepts] IDs."""

    def plan(self, concepts: list[dict], current_map: dict) -> list[dict]:
        """C: 为概念规划层级关系。
        E: Plan hierarchy for concepts."""
        existing_nodes = current_map.get('nodes', [])
        existing_links = current_map.get('links', [])

        concept_summary = json.dumps([
            {'id': c['id'], 'label': c['label']} for c in concepts
        ], ensure_ascii=False)
        existing_summary = json.dumps([
            {'id': n['id'], 'label': n['label']} for n in existing_nodes
        ], ensure_ascii=False)

        prompt = f"""C: 【新概念列表 - 需要规划层级】
{concept_summary}

【当前导图已有节点与连线 - 作为挂载参考】
节点: {existing_summary}
连线: {json.dumps(existing_links, ensure_ascii=False)}

---
请为所有新概念规划父子层级关系，调用 plan_hierarchy 工具提交。
E: [New Concepts - Need Hierarchy Planning]
{concept_summary}

[Existing Nodes and Links - For Attachment Reference]
Nodes: {existing_summary}
Links: {json.dumps(existing_links, ensure_ascii=False)}

---
Please plan parent-child hierarchy for all new concepts, call the plan_hierarchy tool."""

        logger.info(
            f"C: [HierarchyPlanning] 开始规划，新概念={len(concepts)}，已有节点={len(existing_nodes)}，模型={self.model}"
        )
        logger.info(
            f"E: [HierarchyPlanning] Starting, new concepts={len(concepts)}, existing nodes={len(existing_nodes)}, model={self.model}"
        )

        result = self._call_llm_tool(
            system_prompt=self._get_system_prompt(),
            user_prompt=prompt,
            tools=self.tools,
            tool_choice_name="plan_hierarchy"
        )
        relations = result.get('relations', [])

        logger.info(
            f"C: [HierarchyPlanning] 规划完成，关系数={len(relations)}"
        )
        logger.info(
            f"E: [HierarchyPlanning] Done, relations={len(relations)}"
        )
        return relations


# =========================================================
# C: 阶段3 — Delta 生成 Agent（主力模型，扩展自 MindMapSpecialistAgent）
#    接收前两阶段的概念和层级规划，生成最终增删改指令
# E: Stage 3 — Delta Generation Agent (main model, extends MindMapSpecialistAgent)
#    Receives concepts and hierarchy from stages 1 & 2, generates final CRUD instructions
# =========================================================
class DeltaGenerationAgent(MindMapSpecialistAgent):
    def __init__(self, api_key: str, base_url: str, model: str):
        # C: 通过父类 MindMapSpecialistAgent 初始化，参数化模型配置
        # E: Initialize via parent MindMapSpecialistAgent with parameterized model config
        super().__init__(api_key=api_key, base_url=base_url, model=model)

    def generate(self, chat_history: str, concepts: list[dict],
                 hierarchy: list[dict] | None, current_map: dict) -> dict:
        """C: 基于预提取的概念和层级规划生成 delta。
        返回 {"delta": raw_delta_dict, "merged_map": {tree/nodes/links}}
        如果 hierarchy 为 None（阶段2失败），则仅注入概念提示。
        merged_map 包含 tree（G6嵌套树）、nodes（扁平列表）、links（扁平列表）。
        E: Generate delta based on pre-extracted concepts and hierarchy plan.
        Returns {"delta": raw_delta_dict, "merged_map": {tree/nodes/links}}
        If hierarchy is None (stage 2 failed), only inject concept hints.
        merged_map contains tree (G6 nested), nodes (flat), links (flat)."""

        # C: 构建前缀块（概念 + 层级），共享 _build_react_prompt 的 ReAct 模板
        # E: Build prefix blocks (concepts + hierarchy), share _build_react_prompt's ReAct template
        extra_parts = []

        if concepts:
            concept_summary = json.dumps([
                {'id': c['id'], 'label': c['label'], 'details': c.get('details', [])}
                for c in concepts
            ], ensure_ascii=False)
            extra_parts.append(
                f"C: 【预提取的新概念 - 请使用这些概念创建节点，可微调 label 和 details】\n"
                f"{concept_summary}\n"
                f"---\n"
                f"E: [Pre-extracted New Concepts - Use these to create nodes, may fine-tune labels and details]\n"
                f"{concept_summary}\n"
                f"---\n"
            )

        if hierarchy:
            hierarchy_summary = json.dumps(hierarchy, ensure_ascii=False)
            extra_parts.append(
                f"C: 【预规划的层级关系 - 请按此结构建立 add_links，可微调连线类型】\n"
                f"{hierarchy_summary}\n"
                f"---\n"
                f"E: [Pre-planned Hierarchy - Establish add_links following this structure, may fine-tune link types]\n"
                f"{hierarchy_summary}\n"
                f"---\n"
            )

        extra_prefix = "".join(extra_parts)

        # C: 使用父类的 _build_react_prompt（注入前缀）和 _execute_and_merge
        # E: Use parent's _build_react_prompt (with prefix) and _execute_and_merge
        prompt = self._build_react_prompt(chat_history, current_map, extra_prefix=extra_prefix)

        logger.info(
            f"C: [DeltaGeneration] 开始生成，预提取概念={len(concepts)}，预规划关系={len(hierarchy) if hierarchy else 0}，模型={self.model}"
        )
        logger.info(
            f"E: [DeltaGeneration] Starting, concepts={len(concepts)}, hierarchy={len(hierarchy) if hierarchy else 0}, model={self.model}"
        )

        try:
            delta, merged = self._execute_and_merge(prompt, current_map)
            return {"delta": delta, "merged_map": merged}
        except Exception as e:
            logger.error(f"C: [DeltaGeneration] 生成失败: {e}")
            logger.error(f"E: [DeltaGeneration] Failed: {e}")
            return {"delta": {}, "merged_map": current_map}


# =========================================================
# C: 通用调试文件写入函数 — 供 mindmap_agent 和 mcp_server 共用
#    所有写文件操作均捕获异常，绝不中断主流程
# E: Shared debug file writer — used by both mindmap_agent and mcp_server
#    All file operations catch exceptions, never interrupt the main flow
# =========================================================
def write_debug_file(filename: str, content: str | dict | list,
                     session_ts: str | None = None,
                     is_json: bool = False) -> str | None:
    """C: 安全写入调试文件到会话目录。
    参数:
      filename: 文件名（如 'polish_iteration_1.txt'）
      content: 文件内容（字符串 或 JSON 可序列化对象）
      session_ts: 会话时间戳（None = 使用当前时间）
      is_json: 是否以 JSON 格式写入
    返回: 会话目录路径（用于链式调用），失败返回 None
    E: Safely write a debug file to the session directory.
    Args:
      filename: File name (e.g., 'polish_iteration_1.txt')
      content: File content (string or JSON-serializable object)
      session_ts: Session timestamp (None = use current time)
      is_json: Whether to write as JSON
    Returns: Session directory path (for chaining), None on failure
    """
    if not Config.DEBUG_OUTPUT_ENABLED:
        return None
    try:
        if session_ts is None:
            session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(Config.DEBUG_OUTPUT_DIR, session_ts)
        os.makedirs(session_dir, exist_ok=True)
        path = os.path.join(session_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            if is_json and isinstance(content, (dict, list)):
                json.dump(content, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(content))
        return session_dir
    except Exception as e:
        logger.error(f"C: [Debug] 写入 {filename} 失败: {e}")
        logger.error(f"E: [Debug] Failed to write {filename}: {e}")
        return None


# =========================================================
# C: 调试输出管理器 — 保存管线每阶段的中间结果到文件
#    所有写文件操作均捕获异常，绝不中断主流程
# E: Debug Output Manager — saves per-stage intermediate results to files
#    All file operations catch exceptions, never interrupt the main flow
# =========================================================
class DebugOutputManager:
    def __init__(self, enabled: bool, root_dir: str,
                 session_ts: str | None = None):
        self.enabled = enabled
        self.root_dir = root_dir
        self._external_session_ts = session_ts
        self.session_dir: str | None = None
        self._log_lines: list[str] = []

    def _ensure_session(self) -> bool:
        """C: 确保会话文件夹已创建。返回是否可用。
        E: Ensure session directory exists. Returns whether usable."""
        if not self.enabled:
            return False
        if self.session_dir is not None:
            return True
        try:
            timestamp = self._external_session_ts or datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(self.root_dir, timestamp)
            os.makedirs(self.session_dir, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"C: [Debug] 无法创建调试文件夹: {e}")
            logger.error(f"E: [Debug] Cannot create debug directory: {e}")
            self.enabled = False
            return False

    def _write_file(self, filename: str, content: str,
                    is_json: bool = False) -> None:
        """C: 安全写入文件。
        E: Safely write a file."""
        if not self._ensure_session():
            return
        try:
            path = os.path.join(self.session_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                if is_json and isinstance(content, (dict, list)):
                    json.dump(content, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(content))
        except Exception as e:
            logger.error(f"C: [Debug] 写入 {filename} 失败: {e}")
            logger.error(f"E: [Debug] Failed to write {filename}: {e}")

    def add_log(self, line: str) -> None:
        """C: 追加日志行。
        E: Append a log line."""
        self._log_lines.append(line)

    # =========================================================
    # C: 各阶段保存方法
    # E: Per-stage save methods
    # =========================================================

    def save_environment(self) -> None:
        """C: 保存 00_environment.txt — 模型配置元信息。
        E: Save 00_environment.txt — model configuration metadata."""
        if not self.enabled:
            return
        info_lines = [
            f"Timestamp: {datetime.now().isoformat()}",
            f"",
            f"=== LLM Configuration ===",
            f"LLM_MODEL:        {Config.LLM_MODEL}",
            f"LLM_BASE_URL:     {Config.LLM_BASE_URL}",
            f"LLM_API_KEY:      {'***' + Config.LLM_API_KEY[-4:] if Config.LLM_API_KEY else 'NOT SET'}",
            f"",
            f"CONCEPT_MODEL:    {Config.CONCEPT_MODEL or '(not set, using LLM_MODEL)'}",
            f"CONCEPT_BASE_URL: {Config.CONCEPT_BASE_URL}",
            f"",
            f"HIERARCHY_MODEL:  {Config.HIERARCHY_MODEL or '(not set, using LLM_MODEL)'}",
            f"HIERARCHY_BASE_URL: {Config.HIERARCHY_BASE_URL}",
            f"",
            f"DELTA_MODEL:      {Config.DELTA_MODEL}",
            f"DELTA_BASE_URL:   {Config.DELTA_BASE_URL}",
            f"",
            f"POLISH_MODEL:     {Config.POLISH_MODEL or '(not set)'}",
            f"POLISH_ITERATIONS: {Config.POLISH_ITERATIONS}",
            f"",
            f"API_TIMEOUT:      {Config.API_TIMEOUT}",
            f"MCP_SERVER_SCRIPT: {Config.MCP_SERVER_SCRIPT}",
        ]
        self._write_file("00_environment.txt", "\n".join(info_lines))

    def save_stage1_input(self, chat_history: str, current_map: dict) -> None:
        """C: 保存 01_concept_extraction_input.txt — 阶段1的输入。
        E: Save 01_concept_extraction_input.txt — stage 1 input."""
        content = (
            f"=== Chat History ===\n{chat_history}\n\n"
            f"=== Current Map Nodes ({len(current_map.get('nodes', []))}) ===\n"
            f"{json.dumps([{'id': n['id'], 'label': n.get('label', '')} for n in current_map.get('nodes', [])], ensure_ascii=False, indent=2)}\n\n"
            f"=== Current Map Links ({len(current_map.get('links', []))}) ===\n"
            f"{json.dumps(current_map.get('links', []), ensure_ascii=False, indent=2)}"
        )
        self._write_file("01_concept_extraction_input.txt", content)

    def save_stage1_output(self, raw_concepts: list,
                           validated_concepts: list) -> None:
        """C: 保存 01_concept_extraction_output.json — 阶段1的输出。
        E: Save 01_concept_extraction_output.json — stage 1 output."""
        output = {
            "raw_concepts": raw_concepts,
            "validated_concepts": validated_concepts,
            "raw_count": len(raw_concepts) if isinstance(raw_concepts, list) else 0,
            "validated_count": len(validated_concepts),
            "filtered_out": (
                len(raw_concepts) - len(validated_concepts)
                if isinstance(raw_concepts, list) else 0
            ),
        }
        self._write_file("01_concept_extraction_output.json", output, is_json=True)

    def save_stage2_input(self, concepts: list, current_map: dict) -> None:
        """C: 保存 02_hierarchy_planning_input.txt — 阶段2的输入。
        E: Save 02_hierarchy_planning_input.txt — stage 2 input."""
        content = (
            f"=== Concepts to Plan ({len(concepts)}) ===\n"
            f"{json.dumps([{'id': c['id'], 'label': c.get('label', '')} for c in concepts], ensure_ascii=False, indent=2)}\n\n"
            f"=== Existing Nodes ({len(current_map.get('nodes', []))}) ===\n"
            f"{json.dumps([{'id': n['id'], 'label': n.get('label', '')} for n in current_map.get('nodes', [])], ensure_ascii=False, indent=2)}\n\n"
            f"=== Existing Links ({len(current_map.get('links', []))}) ===\n"
            f"{json.dumps(current_map.get('links', []), ensure_ascii=False, indent=2)}"
        )
        self._write_file("02_hierarchy_planning_input.txt", content)

    def save_stage2_output(self, raw_relations: list,
                           validated_relations: list) -> None:
        """C: 保存 02_hierarchy_planning_output.json — 阶段2的输出。
        E: Save 02_hierarchy_planning_output.json — stage 2 output."""
        output = {
            "raw_relations": raw_relations,
            "validated_relations": validated_relations,
            "raw_count": len(raw_relations) if isinstance(raw_relations, list) else 0,
            "validated_count": len(validated_relations),
            "filtered_out": (
                len(raw_relations) - len(validated_relations)
                if isinstance(raw_relations, list) else 0
            ),
        }
        self._write_file("02_hierarchy_planning_output.json", output, is_json=True)

    def save_stage3_input(self, concepts: list, hierarchy: list | None,
                          chat_history: str, current_map: dict) -> None:
        """C: 保存 03_delta_generation_input.txt — 阶段3的输入。
        E: Save 03_delta_generation_input.txt — stage 3 input."""
        content = (
            f"=== Injected Concepts ({len(concepts)}) ===\n"
            f"{json.dumps(concepts, ensure_ascii=False, indent=2)}\n\n"
            f"=== Injected Hierarchy Plan ===\n"
            f"{json.dumps(hierarchy, ensure_ascii=False, indent=2) if hierarchy else '(none - skipped)'}\n\n"
            f"=== Chat History ===\n{chat_history}\n\n"
            f"=== Current Map Nodes ({len(current_map.get('nodes', []))}) ===\n"
            f"{json.dumps(current_map.get('nodes', []), ensure_ascii=False, indent=2)}\n\n"
            f"=== Current Map Links ({len(current_map.get('links', []))}) ===\n"
            f"{json.dumps(current_map.get('links', []), ensure_ascii=False, indent=2)}"
        )
        self._write_file("03_delta_generation_input.txt", content)

    def save_stage3_output(self, raw_delta: dict,
                           merged_map: dict) -> None:
        """C: 保存 03_delta_generation_output.json — 阶段3的原始 delta。
        E: Save 03_delta_generation_output.json — stage 3 raw delta."""
        output = {
            "raw_delta": raw_delta,
            "add_nodes_count": len(raw_delta.get('add_nodes', [])),
            "update_nodes_count": len(raw_delta.get('update_nodes', [])),
            "add_links_count": len(raw_delta.get('add_links', [])),
            "delete_nodes_count": len(raw_delta.get('delete_nodes', [])),
            "merged_nodes_count": len(merged_map.get('nodes', [])),
            "merged_links_count": len(merged_map.get('links', [])),
        }
        self._write_file("03_delta_generation_output.json", output, is_json=True)

    def save_final_map(self, merged_map: dict) -> None:
        """C: 保存 04_final_map.json — 最终导图。
        E: Save 04_final_map.json — final mind map."""
        self._write_file("04_final_map.json", merged_map, is_json=True)

    def flush_logs(self) -> None:
        """C: 保存 05_pipeline_log.txt — 管线执行日志。
        E: Save 05_pipeline_log.txt — pipeline execution log."""
        if not self.enabled or not self._log_lines:
            return
        self._write_file("05_pipeline_log.txt", "\n".join(self._log_lines))
        self._log_lines.clear()


# =========================================================
# C: 多模型管线编排器 — 协调三阶段 Agent 协作
#    提供统一的 generate() 接口，对外表现为单一能力
# E: Multi-model Pipeline Orchestrator — coordinates 3-stage agent collaboration
#    Provides unified generate() interface, appears as a single capability externally
# =========================================================
class MindMapPipelineOrchestrator:
    def __init__(self, concept_agent: ConceptExtractionAgent | None,
                 hierarchy_agent: HierarchyPlanningAgent | None,
                 delta_agent: DeltaGenerationAgent,
                 legacy_agent: MindMapSpecialistAgent):
        """C: 初始化管线编排器。
        参数:
          concept_agent: 阶段1 概念提取 Agent（None = 跳过阶段1，直接用 legacy）
          hierarchy_agent: 阶段2 层级规划 Agent（None = 跳过阶段2）
          delta_agent: 阶段3 Delta 生成 Agent（必需）
          legacy_agent: 降级兜底用的单模型 Agent
        E: Initialize pipeline orchestrator.
        Args:
          concept_agent: Stage 1 concept extraction agent (None = skip stage 1, use legacy directly)
          hierarchy_agent: Stage 2 hierarchy planning agent (None = skip stage 2)
          delta_agent: Stage 3 delta generation agent (required)
          legacy_agent: Fallback single-model agent for degradation
        """
        self.concept_agent = concept_agent
        self.hierarchy_agent = hierarchy_agent
        self.delta_agent = delta_agent
        self.legacy_agent = legacy_agent

    @staticmethod
    def _validate_concepts(concepts: list, current_map: dict) -> list:
        """C: 验证概念列表结构，过滤无效条目。
        E: Validate concept list structure, filter invalid entries."""
        if not isinstance(concepts, list):
            return []
        existing_ids = {str(n['id']) for n in current_map.get('nodes', [])}
        valid = []
        for c in concepts:
            if not isinstance(c, dict):
                continue
            cid = str(c.get('id', ''))
            if not cid or not c.get('label'):
                continue
            if cid in existing_ids:
                logger.warning(
                    f"C: [Validate] 概念 '{cid}' 已存在，跳过"
                )
                logger.warning(
                    f"E: [Validate] Concept '{cid}' already exists, skipped"
                )
                continue
            valid.append(c)
        return valid

    @staticmethod
    def _validate_hierarchy(relations: list, concepts: list,
                            current_map: dict) -> list:
        """C: 验证层级关系，确保引用的 ID 都存在。
        E: Validate hierarchy, ensure all referenced IDs exist."""
        if not isinstance(relations, list):
            return []
        valid_ids = {str(c['id']) for c in concepts}
        valid_ids |= {str(n['id']) for n in current_map.get('nodes', [])}
        valid = []
        for r in relations:
            if not isinstance(r, dict):
                continue
            src = str(r.get('parent_id', ''))
            tgt = str(r.get('child_id', ''))
            if not src or not tgt:
                continue
            if src not in valid_ids:
                logger.warning(
                    f"C: [Validate] 层级规划引用了未知父节点 '{src}'，跳过"
                )
                logger.warning(
                    f"E: [Validate] Hierarchy references unknown parent '{src}', skipped"
                )
                continue
            if tgt not in valid_ids:
                logger.warning(
                    f"C: [Validate] 层级规划引用了未知子节点 '{tgt}'，跳过"
                )
                logger.warning(
                    f"E: [Validate] Hierarchy references unknown child '{tgt}', skipped"
                )
                continue
            valid.append(r)
        return valid

    def generate(self, chat_history: str, current_map: dict,
                 session_ts: str | None = None) -> dict:
        """C: 执行三阶段管线，每阶段失败时自动降级。
        参数 session_ts: 外部指定的会话时间戳（用于跨请求共享调试目录）
        降级链路:
          阶段1 失败 → 跳过阶段1+2，直接用 legacy 单模型
          阶段2 失败 → 跳过阶段2，阶段3 仅接收概念提示
          阶段3 失败 → 返回原图
        E: Execute 3-stage pipeline with automatic degradation.
        Degradation chain:
          Stage 1 fails → skip stages 1+2, use legacy single-model directly
          Stage 2 fails → skip stage 2, stage 3 receives only concept hints
          Stage 3 fails → return original map
        """
        # C: 初始化调试输出管理器
        # E: Initialize debug output manager
        debug = DebugOutputManager(
            enabled=Config.DEBUG_OUTPUT_ENABLED,
            root_dir=Config.DEBUG_OUTPUT_DIR,
            session_ts=session_ts
        )
        t_start = datetime.now()
        debug.add_log(f"[Pipeline Start] {t_start.isoformat()}")
        debug.add_log(f"Chat history length: {len(chat_history)} chars")
        debug.add_log(f"Current map nodes: {len(current_map.get('nodes', []))}, links: {len(current_map.get('links', []))}")
        debug.save_environment()

        # C: 如果没有配置概念提取 Agent，直接降级到 legacy
        # E: If concept agent not configured, degrade to legacy directly
        if self.concept_agent is None:
            msg = "C: [Pipeline] 未配置概念提取模型 → 降级到单模型 ReAct"
            msg_en = "E: [Pipeline] Concept model not configured → degrade to single-model ReAct"
            logger.info(msg)
            logger.info(msg_en)
            debug.add_log(f"[Degrade] {msg}")
            result = self.legacy_agent.generate_map_from_context(
                chat_history, current_map
            )
            debug.save_final_map(result)
            debug.add_log(f"[Pipeline End] Duration: {(datetime.now() - t_start).total_seconds():.2f}s (legacy fallback)")
            debug.flush_logs()
            return result

        # ========================
        # C: 阶段1 — 概念提取
        # E: Stage 1 — Concept extraction
        # ========================
        logger.info("C: [Pipeline] === 阶段1: 概念提取 ===")
        logger.info("E: [Pipeline] === Stage 1: Concept Extraction ===")
        debug.add_log(f"[Stage 1 Start] {datetime.now().isoformat()}")
        debug.save_stage1_input(chat_history, current_map)
        t1_start = datetime.now()
        try:
            raw_concepts = self.concept_agent.extract(chat_history, current_map)
            concepts = self._validate_concepts(raw_concepts, current_map)
        except Exception as e:
            msg = f"C: [Pipeline] 阶段1 异常: {e} → 降级到单模型 ReAct"
            msg_en = f"E: [Pipeline] Stage 1 error: {e} → degrade to single-model ReAct"
            logger.error(msg)
            logger.error(msg_en)
            debug.add_log(f"[Stage 1 ERROR] {msg}")
            debug.flush_logs()
            return self.legacy_agent.generate_map_from_context(
                chat_history, current_map
            )

        t1_elapsed = (datetime.now() - t1_start).total_seconds()
        debug.save_stage1_output(
            raw_concepts if isinstance(raw_concepts, list) else [],
            concepts
        )
        debug.add_log(
            f"[Stage 1 Done] {t1_elapsed:.2f}s | "
            f"raw={len(raw_concepts) if isinstance(raw_concepts, list) else 0}, "
            f"valid={len(concepts)}"
        )

        if not concepts:
            msg = "C: [Pipeline] 阶段1 未提取到新概念 → 降级到单模型 ReAct"
            msg_en = "E: [Pipeline] Stage 1 found no new concepts → degrade to single-model ReAct"
            logger.info(msg)
            logger.info(msg_en)
            debug.add_log(f"[Degrade] {msg}")
            result = self.legacy_agent.generate_map_from_context(
                chat_history, current_map
            )
            debug.save_final_map(result)
            debug.add_log(f"[Pipeline End] Duration: {(datetime.now() - t_start).total_seconds():.2f}s (empty concepts → legacy)")
            debug.flush_logs()
            return result

        # ========================
        # C: 阶段2 — 层级规划
        # E: Stage 2 — Hierarchy planning
        # ========================
        logger.info("C: [Pipeline] === 阶段2: 层级规划 ===")
        logger.info("E: [Pipeline] === Stage 2: Hierarchy Planning ===")
        debug.add_log(f"[Stage 2 Start] {datetime.now().isoformat()}")
        hierarchy = None
        raw_relations = []
        if self.hierarchy_agent is not None:
            debug.save_stage2_input(concepts, current_map)
            t2_start = datetime.now()
            try:
                raw_relations = self.hierarchy_agent.plan(concepts, current_map)
                hierarchy = self._validate_hierarchy(
                    raw_relations, concepts, current_map
                )
            except Exception as e:
                msg = f"C: [Pipeline] 阶段2 异常: {e} → 跳过层级规划，继续阶段3"
                msg_en = f"E: [Pipeline] Stage 2 error: {e} → skip hierarchy, continue to stage 3"
                logger.error(msg)
                logger.error(msg_en)
                debug.add_log(f"[Stage 2 ERROR] {msg}")
                hierarchy = None

            t2_elapsed = (datetime.now() - t2_start).total_seconds()
            debug.save_stage2_output(
                raw_relations if isinstance(raw_relations, list) else [],
                hierarchy if hierarchy else []
            )
            debug.add_log(
                f"[Stage 2 Done] {t2_elapsed:.2f}s | "
                f"raw={len(raw_relations) if isinstance(raw_relations, list) else 0}, "
                f"valid={len(hierarchy) if hierarchy else 0}"
            )
        else:
            logger.info(
                "C: [Pipeline] 未配置层级规划模型 → 跳过阶段2"
            )
            logger.info(
                "E: [Pipeline] Hierarchy model not configured → skip stage 2"
            )
            debug.add_log("[Stage 2 Skipped] Hierarchy agent not configured")

        # ========================
        # C: 阶段3 — Delta 生成
        # E: Stage 3 — Delta generation
        # ========================
        logger.info(
            f"C: [Pipeline] === 阶段3: Delta 生成 ===（概念={len(concepts)}，层级关系={len(hierarchy) if hierarchy else 0}）"
        )
        logger.info(
            f"E: [Pipeline] === Stage 3: Delta Generation === (concepts={len(concepts)}, relations={len(hierarchy) if hierarchy else 0})"
        )
        debug.add_log(f"[Stage 3 Start] {datetime.now().isoformat()}")
        debug.save_stage3_input(concepts, hierarchy, chat_history, current_map)
        t3_start = datetime.now()
        try:
            gen_result = self.delta_agent.generate(
                chat_history, concepts, hierarchy, current_map
            )
            # C: gen_result 现在是 {"delta": ..., "merged_map": ...}
            # E: gen_result is now {"delta": ..., "merged_map": ...}
            raw_delta = gen_result.get("delta", {})
            final_map = gen_result.get("merged_map", current_map)

            t3_elapsed = (datetime.now() - t3_start).total_seconds()
            debug.save_stage3_output(raw_delta, final_map)
            debug.save_final_map(final_map)
            debug.add_log(
                f"[Stage 3 Done] {t3_elapsed:.2f}s | "
                f"add_nodes={len(raw_delta.get('add_nodes', []))}, "
                f"update_nodes={len(raw_delta.get('update_nodes', []))}, "
                f"add_links={len(raw_delta.get('add_links', []))}, "
                f"delete_nodes={len(raw_delta.get('delete_nodes', []))} | "
                f"final nodes={len(final_map.get('nodes', []))}"
            )

            total_elapsed = (datetime.now() - t_start).total_seconds()
            debug.add_log(
                f"[Pipeline Success] Total duration: {total_elapsed:.2f}s"
            )
            debug.flush_logs()

            logger.info(
                f"C: [Pipeline] 三阶段管线完成，最终节点数={len(final_map.get('nodes', []))}"
            )
            logger.info(
                f"E: [Pipeline] 3-stage pipeline complete, final nodes={len(final_map.get('nodes', []))}"
            )
            return final_map
        except Exception as e:
            t3_elapsed = (datetime.now() - t3_start).total_seconds()
            msg = f"C: [Pipeline] 阶段3 异常: {e} → 返回原图"
            msg_en = f"E: [Pipeline] Stage 3 error: {e} → return original map"
            logger.error(msg)
            logger.error(msg_en)
            debug.add_log(f"[Stage 3 ERROR after {t3_elapsed:.2f}s] {msg}")
            debug.add_log(f"[Pipeline Failed] Returning original map unchanged")
            debug.flush_logs()
            return current_map