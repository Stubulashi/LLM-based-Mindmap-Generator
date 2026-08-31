"""
C: 将「未命名的表单.csv」转换为 questionnaire 问卷 JSON 文件（§6 人工评分双评分）。
E: Convert the Google-Forms-style CSV into questionnaire JSON files (§6 human dual scoring).

CSV 结构 / CSV layout:
  每行 = 一份问卷（一位评分者）; 每列 Section {X}-A / {X}-B（X=1..9）:
    - Section {X}-A = 音频 X 系统生成树的 0-10 得分  (gen_score)
    - Section {X}-B = 音频 X 金标准树的 0-10 得分     (human_score)
  Row order maps to questionnaire_id Q1..Q6.

输出 / Output:
  evaluation/data/human_scores/saarland_human_q{1..6}.json, 兼容
  evaluation.human_correlation.interactive_scorer.load_questionnaires(
      {"samples":[{audio, gen_score, human_score, gold_source, questionnaire_id}]}).

用法 / Usage:
  venv/bin/python scripts/csv_to_questionnaires.py
"""
import os
import sys
import csv
import json

sys.path.insert(0, os.getcwd())

from evaluation.human_correlation.interactive_scorer import pick_best_human_tree

PROJECT_ROOT = os.getcwd()
CSV_PATH = os.path.join(PROJECT_ROOT, "未命名的表单.csv")
OUT_DIR = os.path.join(PROJECT_ROOT, "evaluation", "data", "human_scores")
GOLD_DIR = os.path.join("evaluation", "data", "gold")

# E: 9 Saarland pairs / C: 9 个 Saarland 配对
NUM_SECTIONS = 9
PAIR_PREFIX = "Saarland University"


def build_samples(row: dict, questionnaire_id: str) -> list[dict]:
    """E: Convert one questionnaire row into gen/human samples for each section.
    C: 将一行问卷转换为每个 section 的 gen/human 评分样本。"""
    samples = []
    for x in range(1, NUM_SECTIONS + 1):
        gen_col = f"Section {x}-A"
        human_col = f"Section {x}-B"
        if gen_col not in row or human_col not in row:
            continue
        pair_name = f"{PAIR_PREFIX} {x}"
        gen_score = int(float(row[gen_col].strip()))
        human_score = int(float(row[human_col].strip()))
        if not (0 <= gen_score <= 10 and 0 <= human_score <= 10):
            print(f"  ⚠ 越界评分 ({pair_name} {questionnaire_id}): "
                  f"A={gen_score}, B={human_score}，移除该样本")
            continue
        _, gold_source = pick_best_human_tree(pair_name, GOLD_DIR)
        samples.append({
            "audio": pair_name,
            "gen_score": gen_score,
            "human_score": human_score,
            "gold_source": gold_source,
            "questionnaire_id": questionnaire_id,
        })
    return samples


def main() -> None:
    # E: Read CSV with UTF-8 BOM handling (Google Forms export). / C: 读取 CSV（处理 BOM）。
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"[CSV>问卷] 未读取到数据行: {CSV_PATH}")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    written = []
    for idx, row in enumerate(rows, start=1):
        qid = f"Q{idx}"
        samples = build_samples(row, qid)
        if not samples:
            print(f"  ⚠ {qid} 无有效样本，跳过")
            continue
        payload = {
            "__purpose": "问卷式人工评分 — 逐音频 0-10 双评分（系统导图 gen / 人类标注树 human），"
                         "维度：树与音频内容的关联性/代表程度",
            "__purpose_en": "Questionnaire human scoring — per-audio 0-10 dual scores "
                            "(system gen / human gold); dimension: relevance/representativeness",
            "scale": "0-10",
            "questionnaire_id": qid,
            "samples": samples,
        }
        out_path = os.path.join(OUT_DIR, f"saarland_human_{qid.lower()}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        written.append((out_path, len(samples)))

    print(f"[CSV>问卷] 完成：共 {len(rows)} 行问卷 -> {len(written)} 个 JSON 文件")
    for path, n in written:
        print(f"  ✓ {os.path.basename(path)} ({n} samples)")
    if not written:
        sys.exit(1)


if __name__ == "__main__":
    main()
