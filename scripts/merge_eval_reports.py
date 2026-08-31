"""
C: 合并两批次评估报告为单一完整报告。
E: Merge the two batch evaluation reports into a single consolidated report.

输入 / Inputs:
  --saarland-summary <path>  批次1汇总报告（9 个 Saarland pair：label/hierarchy/human_corr）
                             Batch1 summary (9 Saarland pairs).
  --vp-session <dir>        批次2 videoplayback 会话目录（含 videoplayback_report.md /
                            qa_result.json / efficiency_result.json）
                            Batch2 session dir.

输出 / Output:
  evaluation/data/sessions/merged_{ts}/merged_full_report.md

合并规则 / Merge rules:
  - 报告开头显著标注方法差异：仅 videoplayback 运行 qa/efficiency；
    9 个 Saarland pair 运行 label/hierarchy/human_corr（未跑 qa/efficiency）。
  - Saarland 9 个 pair 无 qa 分量；videoplayback 无 label/hierarchy/human 分量。
  - 综合评分在各自可用分量上归一化展示。

用法 / Usage:
  venv/bin/python scripts/merge_eval_reports.py \
    --saarland-summary evaluation/data/sessions/<ts1>/summary_report.md \
    --vp-session evaluation/data/sessions/videoplayback_<ts>
"""
import os
import sys
import json
import argparse
from datetime import datetime

_PROJECT_ROOT = os.getcwd()
OUT_TMPL = os.path.join(_PROJECT_ROOT, "evaluation", "data", "sessions", "merged_{ts}")


def _read_or_default(path: str, default: str) -> str:
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return default


def _vp_block(vp_session: str) -> tuple[str, dict, dict]:
    """E: Read videoplayback report + qa/efficiency JSON; return (markdown, qa, eff).
    C: 读取 videoplayback 报告与 qa/efficiency JSON；返回 (markdown 小节, qa, eff)。"""
    report = _read_or_default(
        os.path.join(vp_session, "videoplayback_report.md"),
        f"*videoplayback 报告缺失 / missing: {vp_session}*",
    )
    qa = {}
    eff = {}
    try:
        with open(os.path.join(vp_session, "qa_result.json"), encoding="utf-8") as f:
            qa = json.load(f)
    except Exception:
        qa = {}
    try:
        with open(os.path.join(vp_session, "efficiency_result.json"), encoding="utf-8") as f:
            eff = json.load(f)
    except Exception:
        eff = {}
    return report, qa, eff


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge batch evaluation reports")
    parser.add_argument("--saarland-summary", required=True,
                        help="Batch1 Saarland summary_report.md path")
    parser.add_argument("--vp-session", required=True,
                        help="Batch2 videoplayback session dir")
    args = parser.parse_args()

    saarland_md = _read_or_default(args.saarland_summary, "*(saarland summary missing)*")
    vp_md, qa, eff = _vp_block(args.vp_session)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUT_TMPL.format(ts=ts)
    os.makedirs(out_dir, exist_ok=True)

    # E: Compute a lightweight aggregate table illustrating per-pair method coverage.
    # C: 生成轻量聚合表，说明各 pair 的方法覆盖情况。
    coverage = (
        "| Pair / 配对 | label | hierarchy | qa | efficiency | human_corr |\n"
        "|---|---:|---|---:|---|---:|---:|\n"
        "| Saarland University 1..9 | ✓ | ✓ | — | — | ✓ |\n"
        "| videoplayback.m4a | — | — | ✓ | ✓ | — |\n"
    )

    summary = f"""# 完整 Evaluation 汇总报告 (Merged Full Evaluation Report)

**合并时间 / Merged at**: {datetime.now().isoformat()}

## 重要说明 / Important Methodology Note

本次评估分两个批次，方法覆盖不同，务必对照理解结果：

- **9 个 Saarland pair**（`Saarland University 1`…`9`）：运行 **label + hierarchy + human_corr**。
  它们**未运行 qa / efficiency**，因为它们有对应的人工标注金标准树（GTC/YQL），
  用于标签保真 / 结构正确率 / 人工效度评估。
- **videoplayback.m4a**：运行 **qa + efficiency**。
  它是长音频通用样本，**无对应金标准**，故无法运行 label / hierarchy / human_corr；
  其 qa 由独立 AI 依据转录自动生成 20 题并 1-5 评分，efficiency 采集管线计时。

因此综合评分并非所有 pair 全分量可比：Saarland 侧无 qa 分量、videoplayback 侧无 label/hierarchy/human 分量，
各 pair 的 composite 仅在其可用分量上归一化。

### 方法覆盖 / Method Coverage
{coverage}

---

"""
    vp_merged_md = f"""---

## 批次 2 / Batch 2 — videoplayback.m4a（qa + efficiency）

{vp_md}

"""
    report = summary + "# 批次 1 / Batch 1 — 9 个 Saarland pair（label + hierarchy + human_corr）\n\n" \
        + saarland_md + "\n\n" + vp_merged_md

    out_path = os.path.join(out_dir, "merged_full_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[merge] 合并报告已生成: {out_path}")
    print(f"[merge]   - 来自批次1: {args.saarland_summary}")
    print(f"[merge]   - 来自批次2: {args.vp_session}")


if __name__ == "__main__":
    main()
