"""
E: Triple Comparison Report — STT transcript × Agent JSON tree × Human-annotated tree
C: 三元组对比报告 — STT 转录 × Agent 生成 JSON 导图 × 人类标注导图

为 9 个测试音频生成中文命名的 Markdown 对比报告：
Generates a Chinese-named Markdown comparison report for the 9 test audios:
1. 对每个音频执行完整管线（Whisper STT → MindMap AI 生成 JSON tree）
   Run the full pipeline (Whisper STT → MindMap AI JSON tree) per audio
2. 从 GTC/YQL 择优选择对应的人类标注树
   Pick the better human-annotated tree between GTC/YQL per audio
3. 以 Mermaid 尽可能完整地还原每棵树的形式
   Render each tree as Mermaid to faithfully reproduce its structure

输出 / Output:
    evaluation/三元组对比报告_<session_ts>.md（中文命名，唯一落点）
"""
import json
import os
import re
from datetime import datetime
from typing import Optional

from evaluation.i18n import T

# E: Project root — derived from this file so all artifacts land correctly
#    regardless of the current working directory.
# C: 项目根目录 — 基于本文件推导，保证任意工作目录下产物均正确落位。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# E: Hard requirement — final report must land in the evaluation/ root directory.
# C: 硬性规定 — 最终报告必须落盘到 evaluation/ 根目录。
_EVAL_ROOT = os.path.join(_PROJECT_ROOT, "evaluation")


def _resolve_project_path(path: str) -> str:
    """
    E: Resolve a relative path against the project root; absolute paths pass through.
    C: 相对路径基于项目根目录解析；绝对路径原样返回。
    """
    return path if os.path.isabs(path) else os.path.join(_PROJECT_ROOT, path)


def _discover_audio_pairs(audio_dir: str) -> list[tuple[str, str]]:
    """
    E: Discover audio files (basename, path), sorted by name.
    C: 发现音频文件（basename, path），按名称排序。
    """
    from evaluation.utils.io_utils import discover_audio_files
    audio_dir_resolved = os.path.join(os.getcwd(), audio_dir) if not os.path.isabs(audio_dir) else audio_dir
    if not os.path.isdir(audio_dir_resolved):
        print(T(
            f"[Triple] 音频目录不存在: {audio_dir_resolved}",
            f"[Triple] Audio directory not found: {audio_dir_resolved}",
        ))
        return []
    pairs: list[tuple[str, str]] = []
    for apath in discover_audio_files(audio_dir_resolved):
        base = os.path.splitext(os.path.basename(apath))[0]
        pairs.append((base, apath))
    pairs.sort(key=lambda item: item[0])
    return pairs


def _safe_mermaid_id(node_id: str) -> str:
    """
    E: Sanitize a node id for Mermaid (alphanumeric + underscore only).
    C: 清理节点 id 供 Mermaid 使用（仅保留字母数字与下划线）。
    """
    safe = re.sub(r"[^A-Za-z0-9_]", "_", str(node_id))
    return safe or "node"


def _tree_to_mermaid(tree: Optional[dict]) -> str:
    """
    E: Convert a {nodes, links} (or nested tree) JSON into a Mermaid
        flowchart TD block that reproduces the tree structure as completely
        as possible.
    C: 将 {nodes, links}（或嵌套 tree）JSON 转换为 Mermaid flowchart TD
        代码块，尽可能完整地还原树的形态。

    Edge priority / 边优先级: nodes[].parent_id → links (source→target).
    """
    if not isinstance(tree, dict):
        return "```mermaid\nflowchart TD\n    missing[\"missing tree / 树缺失\"]\n```"

    nodes = tree.get("nodes") if isinstance(tree.get("nodes"), list) else []
    links = tree.get("links") if isinstance(tree.get("links"), list) else []
    if not nodes:
        # E: Fall back to nested tree structure / C: 回退到嵌套 tree 结构
        nested = tree.get("tree")
        flat: list[dict] = []

        def _flatten(node: dict, parent: Optional[str]):
            nid = str(node.get("id", f"n{len(flat)}"))
            label = str(node.get("label", nid))
            flat.append({"id": nid, "label": label, "parent_id": parent})
            for child in node.get("children", []) or []:
                _flatten(child, nid)

        if isinstance(nested, list):
            for node in nested:
                _flatten(node, None)
        elif isinstance(nested, dict):
            _flatten(nested, None)
        nodes = flat

    node_map = {str(n.get("id")): str(n.get("label", n.get("id", "?"))) for n in nodes if n.get("id") is not None}

    edges: list[tuple[str, str]] = []
    # E: Method 1 — parent_id / C: 方式 1 — parent_id
    for n in nodes:
        pid = n.get("parent_id")
        nid = str(n.get("id"))
        if pid not in (None, "", "None", "null") and str(pid) in node_map and nid in node_map:
            edges.append((str(pid), nid))
    # E: Method 2 — links (source → target), only fills missing hierarchy
    # C: 方式 2 — links（source → target），仅补充未出现的层级关系
    if not edges:
        for link in links:
            src, tgt = str(link.get("source")), str(link.get("target"))
            if src in node_map and tgt in node_map:
                edges.append((src, tgt))

    lines = ["```mermaid", "flowchart TD"]
    for nid, label in node_map.items():
        safe_label = str(label).replace('"', "'").replace("\n", " ")
        lines.append(f'    {_safe_mermaid_id(nid)}["{safe_label}"]')
    for src, tgt in edges:
        lines.append(f"    {_safe_mermaid_id(src)} --> {_safe_mermaid_id(tgt)}")
    lines.append("```")
    return "\n".join(lines)


def _pick_best_human_tree(pair_name: str, gold_dir: str):
    """
    E: Pick the better human-annotated tree between GTC and YQL (more nodes
        wins, ties prefer GTC). Reuses the §6 scorer selection rule.
    C: 在 GTC 与 YQL 之间择优选取人类标注树（节点数多者优先，平局取 GTC）。
        复用 §6 评分器的择优规则，保证任务 1 与任务 2 选树一致。
    """
    from evaluation.human_correlation.interactive_scorer import pick_best_human_tree
    return pick_best_human_tree(pair_name, gold_dir)


def _render_markdown(triples: list[dict], session_ts: str) -> str:
    """
    E: Render the full Chinese-named Markdown triple report.
    C: 渲染完整的中文三元组对比 Markdown 报告。

    triples: [{pair_name, transcript, gen_tree, human_tree, gold_source, error}]
    """
    lines = [
        "# 三元组对比报告",
        "",
        "> **说明 / Note**: 每个音频包含一个三元组 — **STT 转录结果** → "
        "**Agent 生成 JSON 导图** → **人类标注 JSON 导图**（来源 GTC/YQL 择优）。",
        "> **Report generated / 报告生成时间**: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        f"> **Session / 会话**: {session_ts}",
        f"> **Audio count / 音频数量**: {len(triples)}",
        "",
    ]
    for idx, t in enumerate(triples, 1):
        pair = t["pair_name"]
        lines.append(f"---")
        lines.append("")
        lines.append(f"## {idx}. {pair}")
        lines.append("")

        # E: STT transcript / C: STT 转录
        lines.append(f"### STT 转录结果 / STT Transcript")
        lines.append("")
        transcript = t.get("transcript") or ""
        if transcript:
            # E: Quote block — escape '>' prefixes / C: 引用块 — 转义 '>' 前缀
            quoted = transcript.replace("\n>", "\n> >")
            lines.append("> " + quoted.replace("\n", "\n> "))
        else:
            lines.append("> _（转录为空 / transcript empty）_")
        lines.append("")

        # E: Agent generated tree / C: Agent 生成导图
        lines.append(f"### Agent 生成 JSON 导图 / Agent-Generated JSON Tree")
        lines.append("")
        gen_tree = t.get("gen_tree")
        if gen_tree:
            node_count = len(gen_tree.get("nodes", [])) if isinstance(gen_tree, dict) else 0
            lines.append(f"**节点数 / Node count**: {node_count}")
            lines.append("")
            lines.append(_tree_to_mermaid(gen_tree))
        else:
            lines.append(f"_（生成失败 / generation failed: {t.get('error')}）_")
        lines.append("")

        # E: Human annotated tree / C: 人类标注导图
        source = t.get("gold_source") or "—"
        lines.append(f"### 人类标注 JSON 导图 / Human-Annotated JSON Tree（来源 / Source: {source}）")
        lines.append("")
        human_tree = t.get("human_tree")
        if human_tree:
            node_count = len(human_tree.get("nodes", [])) if isinstance(human_tree, dict) else 0
            lines.append(f"**节点数 / Node count**: {node_count}")
            lines.append("")
            lines.append(_tree_to_mermaid(human_tree))
        else:
            lines.append("_（未找到人类标注树 / no human-annotated tree found）_")
        lines.append("")

    lines.append("---")
    lines.append(f"*三元组对比报告 / Triple Comparison Report — {session_ts}*")
    return "\n".join(lines)


async def run_triple_report(
    audio_dir: str = "evaluation/data/audio",
    gold_dir: str = "evaluation/data/gold",
    session_base: str = "evaluation/data/sessions",
) -> str:
    """
    E: Run the full pipeline per audio (Whisper STT → MindMap AI generation),
        pair each with the better human-annotated tree, and write the Chinese-
        named Markdown triple report to the evaluation/ root directory.
    C: 对每个音频执行完整管线（Whisper STT → MindMap AI 生成），与择优的
        人类标注树配对，并在 evaluation/ 根目录生成中文命名的 Markdown
        三元组对比报告。

    Returns the report path / 返回报告路径。
    """
    from mcp_client import MCPMindMapClient

    # E: Resolve audio/gold dirs against the project root (cwd-independent)
    # C: 音频/金标准目录基于项目根解析（与当前工作目录无关）
    audio_dir = _resolve_project_path(audio_dir)
    gold_dir = _resolve_project_path(gold_dir)

    pairs = _discover_audio_pairs(audio_dir)
    if not pairs:
        print(T(
            "[Triple] 未找到音频文件",
            "[Triple] No audio files found",
        ))
        return ""

    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(_resolve_project_path(session_base), session_ts)
    os.makedirs(session_dir, exist_ok=True)

    # E: Resolve MCP server script at project root / C: 定位项目根的 MCP Server 脚本
    server_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "mcp_server.py",
    )
    server_script = os.path.abspath(server_script)

    triples: list[dict] = []
    mcp_client = MCPMindMapClient(server_script)
    try:
        await mcp_client.start()
        print(T(
            f"[Triple] 处理 {len(pairs)} 个音频...",
            f"[Triple] Processing {len(pairs)} audios...",
        ))

        for pair_name, audio_path in pairs:
            print(f"\n{'=' * 60}")
            print(f"  {pair_name}")
            print(f"{'=' * 60}")
            entry: dict = {"pair_name": pair_name, "transcript": "", "gen_tree": None,
                           "human_tree": None, "gold_source": None, "error": None}
            try:
                # E: Step 1 — Whisper STT / 步骤 1 — Whisper 转录
                print(T(
                    "  [1/2] 转录音频...",
                    "  [1/2] Transcribing audio...",
                ))
                transcribe_result = await mcp_client.call_tool(
                    "transcribe_audio", {"file_path": os.path.abspath(audio_path)}
                )
                raw_text = ""
                if isinstance(transcribe_result, dict):
                    raw_text = transcribe_result.get("raw_text", "").strip()
                if not raw_text:
                    raise RuntimeError("Empty transcription / 空转录")
                entry["transcript"] = raw_text
                pair_dir = os.path.join(session_dir, pair_name)
                os.makedirs(pair_dir, exist_ok=True)
                with open(os.path.join(pair_dir, "transcription.txt"), "w", encoding="utf-8") as f:
                    f.write(raw_text)
                print(T(
                    f"  ✓ 转录已保存 ({len(raw_text)} 字符)",
                    f"  ✓ Transcript saved ({len(raw_text)} chars)",
                ))

                # E: Step 2 — MindMap AI generation / 步骤 2 — MindMap AI 生成
                print(T(
                    "  [2/2] 生成导图...",
                    "  [2/2] Generating mind map...",
                ))
                chat_history = (
                    f"C: 【最高优先级指令】请根据以下语音转录文本生成思维导图。\n"
                    f"提取其中所有关键概念，并按层级组织。\n"
                    f"E: [Highest Priority Instruction] Please generate a mind map from the speech transcript below.\n"
                    f"Extract all key concepts and organize them hierarchically.\n\n"
                    f"C: 【转录文本 / Transcript】\n{raw_text}\n---\n"
                    f"E: [Transcript Text]\n{raw_text}\n---"
                )
                gen_result = await mcp_client.call_tool(
                    "modify_mind_map_v2",
                    {
                        "chat_history": chat_history,
                        "current_map": {"nodes": [], "links": []},
                        "session_ts": f"{session_ts}_{pair_name}",
                    },
                )
                if not isinstance(gen_result, dict):
                    raise RuntimeError(f"Invalid map generation result / 导图生成返回无效: {type(gen_result)}")
                entry["gen_tree"] = gen_result
                with open(os.path.join(pair_dir, "generated_map.json"), "w", encoding="utf-8") as f:
                    json.dump(gen_result, f, ensure_ascii=False, indent=2)
                node_count = len(gen_result.get("nodes", []))
                print(T(
                    f"  ✓ 导图已生成 ({node_count} 个节点)",
                    f"  ✓ Map generated ({node_count} nodes)",
                ))

                # E: Step 3 — pick the better human tree (GTC/YQL) / 步骤 3 — 择优人类标注树
                human_tree, source = _pick_best_human_tree(pair_name, gold_dir)
                entry["human_tree"] = human_tree
                entry["gold_source"] = source
                print(T(
                    f"  ✓ 人类标注树来源: {source}",
                    f"  ✓ Human tree source: {source}",
                ))

            except Exception as e:
                entry["error"] = str(e)
                print(T(
                    f"  ✗ 失败: {e}",
                    f"  ✗ Failed: {e}",
                ))
            triples.append(entry)
    finally:
        await mcp_client.close()

    # E: Render and save the report — hard requirement: the final artifact must
    #    land directly in the evaluation/ root directory (not only inside a
    #    nested session subdirectory). A session copy is optional extra.
    # C: 渲染并保存报告 — 硬性规定：最终产物必须直接落盘到 evaluation/ 根目录
    #    （不能仅存放在嵌套的会话子目录中）；会话目录副本仅为额外留存。
    report = _render_markdown(triples, session_ts)
    report_path = os.path.abspath(os.path.join(_EVAL_ROOT, f"三元组对比报告_{session_ts}.md"))
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    # E: Optional session copy — the root artifact above is the final landing point
    # C: 会话目录可选副本 — 上述根目录产物才是最终落点
    session_copy = os.path.join(session_dir, "三元组对比报告.md")
    with open(session_copy, "w", encoding="utf-8") as f:
        f.write(report)

    ok = sum(1 for t in triples if t.get("gen_tree") and t.get("human_tree"))
    print("\n" + "=" * 60)
    print(T(
        f"  三元组报告完成: {ok}/{len(triples)} 个完整三元组",
        f"  Triple report complete: {ok}/{len(triples)} full triples",
    ))
    print(T(
        f"  ✓ 根目录落点: {report_path}",
        f"  ✓ Root location: {report_path}",
    ))
    print("=" * 60)
    return report_path
