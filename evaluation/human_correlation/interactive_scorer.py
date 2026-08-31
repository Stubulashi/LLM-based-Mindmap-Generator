"""
E: §6 Interactive Human Scoring — questionnaire-based dual scoring (0-10)
C: §6 交互式人类评分 — 问卷式双评分（0-10 里克特量表）

Evaluation_Schema.md §6 重构流程 / Refactored flow:
1. 系统列出所有待评估音频文件名，明确提示"这是问卷一"（每份问卷由一位
   第三方评分者填写）/ List all pending audio files, announce "Questionnaire 1"
   (each questionnaire is filled by one third-party rater)
2. 对每个音频依次询问两个 0-10 分评分（10=完全符合，0=不符合；维度为
   树与音频内容的关联性 / 代表程度）：
   / For each audio, ask two 0-10 scores (10 = fully matching, 0 = not at all;
   dimension: relevance / representativeness of the tree to the audio):
   - 系统生成的 JSON 导图的评分 / system-generated JSON mind map score
   - 人类标注的 JSON 导图的评分（来源 GTC/YQL 择优）/ human-annotated JSON
     mind map score (best of GTC/YQL)
3. 支持多份问卷结果一起输入（交互逐份录入 + 问卷 JSON 文件批量导入），
   自动统计给出该项总得分并计入 evaluation 总分。
   / Multiple questionnaires may be entered together (interactive loop +
   JSON file import); scores are aggregated into the final evaluation total.

评分目的 / Purpose:
为 §2 层级结构正确率提供人工补偿，防止层级指标的 False Negative
（误判失败）主导最终总分，提升评分的鲁棒性。
Provides a human compensation mechanism for §2 Hierarchy Accuracy
robustness, preventing hierarchy False Negatives from dominating the
final composite score.
"""
import json
import os
from typing import Optional

from evaluation.i18n import T

# E: Project root — derived from this file so relative paths resolve correctly
#    regardless of the current working directory.
# C: 项目根目录 — 基于本文件推导，保证相对路径在任意工作目录下均正确解析。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# E: Score bounds — 0-10 Likert scale (10 = fully matching, 0 = not at all)
# C: 评分边界 — 0-10 李克特量表（10=完全符合，0=不符合）
MIN_SCORE = 0
MAX_SCORE = 10

# E: Chinese ordinal map for questionnaire titles / C: 问卷标题中文序号映射
_CN_NUM = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十'}


def _questionnaire_title(questionnaire_id: str) -> str:
    """
    E: Map 'Q1' → '问卷一' (Chinese ordinal title).
    C: 将 'Q1' 映射为 '问卷一'（中文序号标题）。
    """
    try:
        n = int(str(questionnaire_id).lstrip('Qq'))
        return f"问卷{_CN_NUM.get(n, n)}"
    except (ValueError, TypeError):
        return f"问卷 {questionnaire_id}"


def pick_best_human_tree(
    pair_name: str,
    gold_dir: str = "evaluation/data/gold",
) -> tuple[Optional[dict], Optional[str]]:
    """
    E: Pick the better human-annotated tree between GTC and YQL for an audio.
        Selection rule: the tree with more nodes wins; ties prefer GTC.
    C: 为某音频在 GTC 与 YQL 之间择优选取人类标注树。
        规则：节点数更多者优先；平局时取 GTC。

    Returns (tree_dict, source) — source in ('GTC', 'YQL', None).
    返回 (tree_dict, source) — source 为 'GTC' / 'YQL' / None。
    """
    gold_dir_resolved = os.path.join(_PROJECT_ROOT, gold_dir) if not os.path.isabs(gold_dir) else gold_dir
    candidates: list[tuple[str, dict]] = []
    for src in ('GTC', 'YQL'):
        path = os.path.join(gold_dir_resolved, src, f"{pair_name}.json")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                candidates.append((src, data))
            except Exception as e:
                print(T(
                    f"  ⚠ 人类标注树加载失败 ({src}/{pair_name}): {e}",
                    f"  ⚠ Human tree load failed ({src}/{pair_name}): {e}",
                ))
    if not candidates:
        return None, None

    def _node_count(data: dict) -> int:
        if isinstance(data, dict):
            nodes = data.get("nodes")
            if isinstance(nodes, list):
                return len(nodes)
            tree = data.get("tree")
            if isinstance(tree, list):
                return len(tree)
        return 0

    # E: Stable sort keeps GTC first on ties / C: 稳定排序保证平局时 GTC 优先
    candidates.sort(key=lambda item: -_node_count(item[1]))
    best_src, best_data = candidates[0]
    return best_data, best_src


def _tree_summary(tree: Optional[dict], max_labels: int = 12) -> str:
    """
    E: Render a compact indented tree summary for the scorer's reference.
    C: 渲染树的紧凑缩进摘要，供评分者参考。
    """
    if not tree:
        return T("  (无可用人类标注树)", "  (no human tree available)")
    lines: list[str] = []
    tree_data = tree.get("tree") if isinstance(tree, dict) else None

    def _walk(node: dict, depth: int):
        label = str(node.get("label", node.get("id", "?")))
        lines.append("  " * (depth + 1) + f"- {label}")
        children = node.get("children")
        if isinstance(children, list) and depth < 3:
            for child in children[:max_labels]:
                _walk(child, depth + 1)

    if isinstance(tree_data, list):
        for node in tree_data[:max_labels]:
            _walk(node, 0)
    elif isinstance(tree_data, dict):
        _walk(tree_data, 0)
    else:
        # E: Flat nodes with parent_id / C: 扁平节点 + parent_id
        nodes = tree.get("nodes") if isinstance(tree, dict) else []
        if isinstance(nodes, list):
            by_parent: dict = {}
            for n in nodes:
                by_parent.setdefault(n.get("parent_id"), []).append(n)
            for r in by_parent.get(None, [])[:max_labels]:
                _walk(r, 0)
    return "\n".join(lines) if lines else "  (empty tree / 空树)"


def _prompt_score(audio: str, target_label: str) -> int:
    """
    E: Prompt a single 0-10 integer score with validation and re-entry.
    C: 询问单个 0-10 整数评分（带校验与重输提示）。
    """
    while True:
        raw = input(f"    {target_label} (0-10): ").strip()
        try:
            val = int(raw)
        except ValueError:
            print(T(
                f"    [!] 无效评分: {raw} — 请输入 0-10 整数",
                f"    [!] Invalid score: {raw} — enter an integer 0-10",
            ))
            continue
        if MIN_SCORE <= val <= MAX_SCORE:
            return val
        print(T(
            f"    [!] 评分超出范围: {val} — 必须在 {MIN_SCORE}-{MAX_SCORE} 之间",
            f"    [!] Score out of range: {val} — must be {MIN_SCORE}-{MAX_SCORE}",
        ))


def collect_human_scores(
    audio_list: list[str],
    gold_dir: str = "evaluation/data/gold",
    questionnaire_id: str = "Q1",
) -> list[dict]:
    """
    E: Interactive per-audio scoring for ONE questionnaire — announce the
        questionnaire title, then collect two 0-10 scores (system map /
        human-annotated map) for every audio.
    C: 单份问卷的交互式逐音频评分 — 开头明确提示问卷标题（"这是问卷一"），
        随后对每个音频收集两个 0-10 评分（系统导图 / 人类标注导图）。

    Args / 参数:
        audio_list: List of pair names (audio basename) / 配对名列表（音频文件名去后缀）
        gold_dir: Gold standard root dir / 金标准根目录
        questionnaire_id: e.g. 'Q1', 'Q2' / 问卷编号，如 'Q1'、'Q2'

    Returns / 返回:
        [{audio, gen_score, human_score, gold_source, questionnaire_id}, ...]
    """
    title = _questionnaire_title(questionnaire_id)
    print()
    print("=" * 60)
    print(T(
        f"  §6 人工评估 — {title}",
        f"  §6 Human Evaluation — {title}",
    ))
    print(T(
        f"  这是{title}（{questionnaire_id}）",
        f"  This is {title} ({questionnaire_id})",
    ))
    print("=" * 60)
    print(T("  评分说明:", "  Scoring rubric:"))
    print(T(
        f"    {MIN_SCORE}-{MAX_SCORE} 分制（{MAX_SCORE}=完全符合，{MIN_SCORE}=不符合）",
        f"    {MIN_SCORE}-{MAX_SCORE} scale (10 = fully matching, 0 = not at all)",
    ))
    print(T(
        "    评分维度: 树与音频内容的关联性 / 代表程度",
        "    Dimension: relevance & representativeness of the tree to the audio",
    ))
    print(T(
        "    - 系统生成 JSON 导图评分",
        "    - System-generated JSON mind map score",
    ))
    print(T(
        "    - 人类标注 JSON 导图评分",
        "    - Human-annotated JSON mind map score",
    ))
    print()
    print(T(
        f"  待评估音频清单 ({len(audio_list)}):",
        f"  Pending audio files ({len(audio_list)}):",
    ))
    for i, audio in enumerate(audio_list, 1):
        print(f"    {i}. {audio}")
    print()

    samples: list[dict] = []
    for audio in audio_list:
        print(f"  --- {audio} ---")
        human_tree, source = pick_best_human_tree(audio, gold_dir)
        if source:
            print(T(
                f"    人类标注树来源: {source}",
                f"    Human tree source: {source}",
            ))
            print(T(
                "    人类标注树预览:",
                "    Human tree preview:",
            ))
            print(_tree_summary(human_tree))
        else:
            print(T(
                "    ⚠ 未找到人类标注树 (GTC/YQL)",
                "    ⚠ No human-annotated tree found (GTC/YQL)",
            ))
        print()
        gen_score = _prompt_score(audio, T("系统生成 JSON 导图评分", "System-generated JSON mind map score"))
        human_score = _prompt_score(audio, T("人类标注 JSON 导图评分", "Human-annotated JSON mind map score"))
        samples.append({
            "audio": audio,
            "gen_score": gen_score,
            "human_score": human_score,
            "gold_source": source,
            "questionnaire_id": questionnaire_id,
        })
        print()

    return samples


def collect_questionnaires_loop(
    audio_list: list[str],
    gold_dir: str = "evaluation/data/gold",
) -> list[dict]:
    """
    E: Loop over questionnaires — after each one, ask whether to continue with
        the next questionnaire or generate the report from current data.
    C: 问卷循环 — 每录完一份问卷询问"继续录入下一份问卷 / 直接基于现有数据
        生成报告"；返回全部问卷的合并样本列表。
    """
    all_samples: list[dict] = []
    n = 1
    while True:
        qid = f"Q{n}"
        samples = collect_human_scores(audio_list, gold_dir, questionnaire_id=qid)
        all_samples.extend(samples)
        print(T(
            f"  ✓ {_questionnaire_title(qid)} 完成（{len(samples)} 条）",
            f"  ✓ {qid} complete ({len(samples)} samples)",
        ))
        choice = input(T(
            "  是否继续录入下一份问卷？[y/N]（回车=否）: ",
            "  Continue with the next questionnaire? [y/N]: ",
        )).strip().lower()
        if choice in ('y', 'yes'):
            n += 1
            continue
        break
    return all_samples


def load_questionnaires(paths: list[str]) -> list[dict]:
    """
    E: Batch-import questionnaire files — supports:
        1. a single file with {"questionnaires": [q1, q2, ...]};
        2. a single file with {"samples": [...]} or a bare list (one questionnaire);
        3. multiple files, each as above.
        Only samples carrying gen_score/human_score are kept; samples without a
        questionnaire_id get one assigned by import order.
    C: 批量导入问卷文件 — 支持：
        1. 单文件含 {"questionnaires": [问卷1, 问卷2, ...]}；
        2. 单文件 {"samples": [...]} 或裸列表（一份问卷）；
        3. 多文件混合。
        仅保留含 gen_score/human_score 的样本；无 questionnaire_id 的样本
        按导入顺序自动分配编号。
    """
    imported: list[dict] = []
    for path in paths:
        if not os.path.isfile(path):
            print(T(
                f"  ⚠ 问卷文件不存在: {path}",
                f"  ⚠ Questionnaire file not found: {path}",
            ))
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(T(
                f"  ⚠ 问卷加载失败 ({path}): {e}",
                f"  ⚠ Questionnaire load failed ({path}): {e}",
            ))
            continue
        chunks: list[dict] = []
        if isinstance(data, dict) and isinstance(data.get("questionnaires"), list):
            chunks = data["questionnaires"]
        elif isinstance(data, dict) and isinstance(data.get("samples"), list):
            chunks = [data]
        elif isinstance(data, list):
            chunks = [{"samples": data}]
        for ch in chunks:
            if not isinstance(ch, dict):
                continue
            samples = ch.get("samples", [])
            if not isinstance(samples, list):
                continue
            qid = ch.get("questionnaire_id") or ch.get("id") or f"Q{len(imported) + 1}"
            for s in samples:
                if isinstance(s, dict) and ('gen_score' in s or 'human_score' in s):
                    s.setdefault("questionnaire_id", qid)
                    imported.append(s)
    print(T(
        f"  ✓ 已从 {len(paths)} 个文件导入 {len(imported)} 条评分",
        f"  ✓ Imported {len(imported)} samples from {len(paths)} file(s)",
    ))
    return imported


def aggregate_human_scores(samples: list[dict]) -> dict:
    """
    E: Aggregate per-audio scores across questionnaires into summary statistics
        (normalized to [0,1]). Per-audio means are computed across all
        questionnaire ratings; overall = mean(gen, human).
    C: 跨问卷将逐音频评分聚合为汇总统计（归一化到 [0,1]）。每音频均值
        跨全部问卷评分计算；总分 = mean(gen, human)。

    Returns / 返回:
        {num_samples, num_questionnaires, gen_mean, human_mean, overall_mean,
         overall_normalized, per_audio:[{audio, gen_mean, human_mean, gold_source, ratings}]}
    """
    if not samples:
        return {
            "num_samples": 0,
            "num_questionnaires": 0,
            "gen_mean": 0.0,
            "human_mean": 0.0,
            "overall_mean": 0.0,
            "overall_normalized": 0.0,
            "per_audio": [],
        }
    n = len(samples)
    gen_mean = sum(s.get("gen_score", 0) for s in samples) / n
    human_mean = sum(s.get("human_score", 0) for s in samples) / n
    overall_mean = (gen_mean + human_mean) / 2.0

    qids = {s.get("questionnaire_id", "Q1") for s in samples}
    num_questionnaires = len(qids) or 1

    # E: Per-audio means across all questionnaire ratings / C: 每音频跨问卷均值
    by_audio: dict[str, list[dict]] = {}
    for s in samples:
        by_audio.setdefault(s.get("audio", "?"), []).append(s)
    per_audio = []
    for audio in sorted(by_audio):
        ss = by_audio[audio]
        per_audio.append({
            "audio": audio,
            "gen_mean": round(sum(x.get("gen_score", 0) for x in ss) / len(ss), 2),
            "human_mean": round(sum(x.get("human_score", 0) for x in ss) / len(ss), 2),
            "gold_source": ss[0].get("gold_source"),
            "ratings": len(ss),
        })

    return {
        "num_samples": n,
        "num_questionnaires": num_questionnaires,
        "gen_mean": round(gen_mean, 4),
        "human_mean": round(human_mean, 4),
        "overall_mean": round(overall_mean, 4),
        "overall_normalized": round(overall_mean / MAX_SCORE, 4),
        "per_audio": per_audio,
    }


def save_human_scores(samples: list[dict], out_path: str) -> str:
    """
    E: Persist questionnaire samples to JSON (compatible with data/human_scores layout).
    C: 将问卷评分样本持久化到 JSON（兼容 data/human_scores 目录约定）。

    Returns the output path / 返回输出路径。
    """
    dirname = os.path.dirname(out_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    payload = {
        "__purpose": "问卷式人工评分 — 逐音频 0-10 双评分（系统导图 / 人类标注导图，维度：关联性/代表程度）",
        "__purpose_en": "Questionnaire-based human scoring — per-audio 0-10 dual scores (system map / human map; dimension: relevance/representativeness)",
        "scale": f"{MIN_SCORE}-{MAX_SCORE}",
        "samples": samples,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path
