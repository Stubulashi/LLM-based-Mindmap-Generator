"""
C: videoplayback.m4a 专用评估 — 仅跑 §3 QA 与 §4 Efficiency（无金标准，无法跑 label/hierarchy）。
E: Dedicated evaluation for videoplayback.m4a — runs only §3 QA and §4 Efficiency.
   (No gold standard, so label/hierarchy cannot run on it.)

流程 / Flow:
  1. 启动 MCP Client（复用 mcp_server.py 的 transcribe_audio / modify_mind_map_v2）
  2. Whisper 转录 videoplayback.m4a（采集 stt 计时）
  3. 依据转录生成导图（采集 map_gen 计时）
  4. QAEvaluator.evaluate（question 缺省由独立 AI 依据转录自动生成 20 题）
  5. evaluate_efficiency（WER/KTRR 因无 reference transcript / key_terms 降级为不可用）
  6. 结果落盘到 evaluation/data/sessions/videoplayback_{ts}/ 并渲染独立 Markdown 小节

用法 / Usage:
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 venv/bin/python scripts/run_videoplayback_qa_eff.py
  # 充值后仅重跑 QA（复用已保存的 transcription.txt + generated_map.json）
  # Re-run QA only after recharging (reuse saved transcription + generated map):
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 venv/bin/python scripts/run_videoplayback_qa_eff.py --resume evaluation/data/sessions/videoplayback_20260831_151444
注意 / Note:
  需 api.env 提供 DEEPSEEK/MOONSHOT key（导图生成 + QA 均走 LLM），本地 Whisper 可用。
  因转录 97MB 长音频耗时，默认 repeat=1。
"""
import argparse
import os
import sys
import json
import time as time_module
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.getcwd())

# E: Load .env (HF env) and api.env (real LLM keys, override) BEFORE importing Config.
# C: 先加载 .env（HF 环境）与 api.env（真实 LLM key，override），再导入 Config。
from dotenv import load_dotenv
_PROJECT_ROOT = os.getcwd()
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, '.env'))
_api_env = Path(_PROJECT_ROOT) / 'api.env'
if _api_env.exists():
    load_dotenv(dotenv_path=_api_env, override=True)

from mcp_client import MCPMindMapClient
from evaluation.qa.eval_qa import QAEvaluator
from evaluation.efficiency.eval_efficiency import evaluate_efficiency, EfficiencyStandards

AUDIO_PATH = os.path.join(_PROJECT_ROOT, "videoplayback.m4a")
SESSION_TMPL = os.path.join(_PROJECT_ROOT, "evaluation", "data", "sessions", "videoplayback_{ts}")


def _save(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)


def _render_report(qa_dict: dict, eff_dict: dict, duration_sec) -> str:
    """C: 渲染 videoplayback 独立 Markdown 小节。
    E: Render the videoplayback standalone Markdown section."""
    qa_score = qa_dict.get("qa_score", 0)
    num_q = qa_dict.get("num_questions", 0)
    tot_p50 = eff_dict.get("t_total_p50")
    tot_p95 = eff_dict.get("t_total_p95")
    dur_str = f"({duration_sec}s)" if isinstance(duration_sec, (int, float)) else "(时长未知 / unknown)"
    lines = [
        "# videoplayback — QA 与 Efficiency 评估报告",
        "",
        f"**评估时间 / Time**: {datetime.now().isoformat()}",
        f"**音频 / Audio**: videoplayback.m4a {dur_str}",
        f"**方法 / Methods**: qa + efficiency（无金标准，未跑 label/hierarchy）",
        "",
        "> 说明：该 pair 为通用长音频样本。QA 由独立 AI 依据转录自动生成 20 题并 1-5 评分；",
        "> efficiency 的 WER / KTRR 因未提供 reference transcript 与 key_terms 而标记为不可用（属预期）。",
        "",
        "## QA 评估（§3）",
        "",
        f"- 题目数 / Questions: {num_q}",
        f"- qa_score (归一化 / normalized): {qa_score}",
        f"- 平均原始分 / avg raw (1-5): {qa_dict.get('avg_raw_score')}",
        "",
        "## Efficiency 评估（§4）",
        "",
        f"- Total P50: {tot_p50}s",
        f"- Total P95: {tot_p95}s",
        f"- STT Ratio: {eff_dict.get('stt_ratio')}",
        f"- WER: {eff_dict.get('wer', 'N/A')} ({eff_dict.get('wer_method')})",
        f"- KTRR: {eff_dict.get('ktrr', 'N/A')} ({eff_dict.get('ktrr_method')})",
        f"- STT status: {eff_dict.get('stt_status')}",
        "",
        "## 结果文件 / Artifacts",
        "",
        "- `transcription.txt`",
        "- `generated_map.json`",
        "- `qa_result.json`",
        "- `efficiency_result.json`",
        "",
    ]
    return "\n".join(lines)


async def _run_qa_only(session_dir: str) -> None:
    """C: 充值后仅重跑 QA — 复用会话中已保存的转录与导图，不再转录/生成。
    E: Re-run QA only after recharge — reuse saved transcription & generated map."""
    trans_path = os.path.join(session_dir, "transcription.txt")
    map_path = os.path.join(session_dir, "generated_map.json")
    if not (os.path.isfile(trans_path) and os.path.isfile(map_path)):
        print(f"[videoplayback] 恢复所需文件缺失:")
        print(f"    {trans_path}")
        print(f"    {map_path}")
        return
    with open(trans_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    with open(map_path, "r", encoding="utf-8") as f:
        gen_result = json.load(f)
    nodes = gen_result.get("nodes", []) if isinstance(gen_result, dict) else []
    print(f"[videoplayback] 恢复会话: {session_dir}")
    print(f"[videoplayback]   转录 {len(raw_text)} 字符, 导图 {len(nodes)} 节点")
    # C: 重新采集计时（仅 QA 阶段的墙钟），供报告的 Efficiency 展示保留历史值。
    # E: Track wall clock for the QA phase; keep historical eff value in report.
    qa_eval = QAEvaluator()
    qa_metrics = qa_eval.evaluate(raw_text, nodes, questions=None)
    qa_dict = qa_metrics.to_dict()
    _save(os.path.join(session_dir, "qa_result.json"), qa_dict)
    # C: 读取历史 efficiency 结果并追加标注（QA 重算不改 efficiency）
    # E: Load historical efficiency result (unchanged by QA rerun).
    eff_dict = {}
    eff_path = os.path.join(session_dir, "efficiency_result.json")
    if os.path.isfile(eff_path):
        with open(eff_path, "r", encoding="utf-8") as f:
            eff_dict = json.load(f)
    qa_score = qa_dict.get("qa_score", 0)
    num_q = qa_dict.get("num_questions", 0)
    report = _render_report(qa_dict, eff_dict, None)
    _save(os.path.join(session_dir, "videoplayback_report.md"), report)
    print("[videoplayback] QA 重跑完成")
    print(f"  QA: qa_score={qa_score}, questions={num_q}")
    print(f"  报告: {session_dir}/videoplayback_report.md")


async def main() -> None:
    parser = argparse.ArgumentParser(description="videoplayback QA+Efficiency evaluation")
    parser.add_argument("--resume", type=str, default=None,
                        help="Re-run QA only reusing a saved videoplayback session dir")
    args = parser.parse_args()

    if args.resume:
        await _run_qa_only(args.resume)
        return

    if not os.path.isfile(AUDIO_PATH):
        print(f"[videoplayback] 音频不存在: {AUDIO_PATH}")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = SESSION_TMPL.format(ts=ts)
    os.makedirs(session_dir, exist_ok=True)
    print(f"[videoplayback] Session dir: {session_dir}")

    server_script = os.path.join(_PROJECT_ROOT, "mcp_server.py")
    client = MCPMindMapClient(server_script)
    timing_snapshots = []

    try:
        print("[videoplayback] 启动 MCP Client...")
        await client.start()

        # -------------------------------------------------
        # Step 1: Whisper 转录
        # -------------------------------------------------
        print("[videoplayback] [1/3] 转录音频...")
        t0 = time_module.perf_counter()
        transcribe_result = await client.call_tool(
            "transcribe_audio", {"file_path": os.path.abspath(AUDIO_PATH)}
        )
        t1 = time_module.perf_counter()
        raw_text = ""
        duration_sec = None
        if isinstance(transcribe_result, dict):
            raw_text = (transcribe_result.get("raw_text") or "").strip()
            duration_sec = transcribe_result.get("duration_sec")
        timing_snapshots.append({
            "stage": "stt", "start": t0, "end": t1, "duration": t1 - t0,
            "sub_stages": None,
            "audio_duration_sec": duration_sec,
            "stt_chars": len(raw_text),
        })
        print(f"[videoplayback] 转录完成: {len(raw_text)} 字符, 音频 {duration_sec}s")
        if not raw_text:
            print("[videoplayback] 转录为空，无法继续。")
            _save(os.path.join(session_dir, "error.json"),
                  {"error": "empty_transcription"})
            return
        _save(os.path.join(session_dir, "transcription.txt"), raw_text)

        # -------------------------------------------------
        # Step 2: 导图生成
        # -------------------------------------------------
        print("[videoplayback] [2/3] 生成导图...")
        chat_history = (
            f"C: 【最高优先级指令】请根据以下语音转录文本生成思维导图。\n"
            f"提取其中所有关键概念，并按层级组织。\n"
            f"E: [Highest Priority Instruction] Please generate a mind map from the speech transcript below.\n"
            f"Extract all key concepts and organize them hierarchically.\n\n"
            f"C: 【转录文本 / Transcript】\n{raw_text}\n---\n"
            f"E: [Transcript Text]\n{raw_text}\n---"
        )
        t2 = time_module.perf_counter()
        gen_result = await client.call_tool(
            "modify_mind_map_v2",
            {
                "chat_history": chat_history,
                "current_map": {"nodes": [], "links": []},
                "session_ts": f"{ts}_videoplayback",
            },
        )
        t3 = time_module.perf_counter()
        timing_snapshots.append({
            "stage": "map_gen", "start": t2, "end": t3, "duration": t3 - t2,
        })
        if not isinstance(gen_result, dict):
            print(f"[videoplayback] 导图生成返回无效类型: {type(gen_result)}")
            return
        nodes = gen_result.get("nodes", [])
        print(f"[videoplayback] 导图生成完成: {len(nodes)} 个节点")
        _save(os.path.join(session_dir, "generated_map.json"), gen_result)

        # -------------------------------------------------
        # Step 3: QA 评估（问题由独立 AI 依据转录自动生成）
        # -------------------------------------------------
        print("[videoplayback] [3/3] 运行 QA + Efficiency 评估...")
        qa_eval = QAEvaluator()
        qa_metrics = qa_eval.evaluate(raw_text, nodes, questions=None)
        qa_dict = qa_metrics.to_dict()
        _save(os.path.join(session_dir, "qa_result.json"), qa_dict)

        # -------------------------------------------------
        # Step 4: Efficiency 评估（WER/KTRR 无参考，降级不可用）
        # -------------------------------------------------
        st = EfficiencyStandards()
        custom_stds = os.path.join(_PROJECT_ROOT, "evaluation", "data", "standards",
                                   "custom_standards.json")
        if os.path.isfile(custom_stds):
            st = EfficiencyStandards(custom_stds)
        eff_metrics = evaluate_efficiency(
            timing_snapshots=timing_snapshots,
            stt_text=raw_text or None,
            ground_truth_text=None,   # 无人工转写 → WER 不可用
            key_terms=None,           # 无关键术语 → KTRR 不可用
            standards=st,
            num_repetitions=1,
        )
        eff_dict = eff_metrics.to_dict()
        _save(os.path.join(session_dir, "efficiency_result.json"), eff_dict)

        # -------------------------------------------------
        # Step 5: 渲染独立 Markdown 小节
        # -------------------------------------------------
        report = _render_report(qa_dict, eff_dict, duration_sec)
        _save(os.path.join(session_dir, "videoplayback_report.md"), report)
        qa_score = qa_dict.get("qa_score", 0)
        num_q = qa_dict.get("num_questions", 0)
        tot_p50 = eff_dict.get("t_total_p50")
        print("[videoplayback] 评估完成")
        print(f"  QA: qa_score={qa_score}, questions={num_q}")
        print(f"  Efficiency: Total P50={tot_p50}s, WER={eff_dict.get('wer')}"
              f" (method={eff_dict.get('wer_method')})")
        print(f"  报告: {session_dir}/videoplayback_report.md")

    finally:
        try:
            await client.close()
        except Exception as e:
            print(f"[videoplayback] 关闭 MCP 失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
