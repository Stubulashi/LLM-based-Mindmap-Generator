"""
E: CLI utilities — multiselect, file prompt, progress tracking
C: 交互式 CLI 辅助 — 多选、文件提示、进度追踪
"""
import sys
import os
import glob
from typing import Optional


def interactive_multiselect(title: str, options: dict[str, str]) -> list[str]:
    """
    E: Interactive multiselect — type number(s) separated by comma/space, supports 'all'
    C: 交互式多选 — 终端键入编号（逗号/空格分隔），支持 'all'
    """
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    items = list(options.items())

    print("  (输入 'all' 选择全部 / Type 'all' to select all, 输入编号如 / numbers like '1,2,3' 或 / or '1 3 5' 多选 / multi-select)")
    for idx, (key, desc) in enumerate(items, 1):
        print(f"  [{idx}] {desc}")

    while True:
        raw = input("\n> 请选择 / Select: ").strip()
        if not raw:
            print("  输入不能为空，请重新选择。/ Input cannot be empty, please try again.")
            continue
        if raw.lower() == 'all':
            return [k for k, _ in items]
        # E: Parse comma/space separated numbers / C: 解析逗号/空格分隔的编号
        selected = set()
        parts = raw.replace(',', ' ').split()
        valid = True
        for p in parts:
            try:
                idx = int(p)
                if 1 <= idx <= len(items):
                    selected.add(idx - 1)
                else:
                    print(f"  无效编号 / Invalid number: {p} (范围 / range 1-{len(items)})")
                    valid = False
            except ValueError:
                print(f"  无效输入 / Invalid input: {p}")
                valid = False
        if valid and selected:
            return [items[i][0] for i in sorted(selected)]


def prompt_file(label: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    E: Prompt user for file path
    C: 提示用户输入文件路径
    """
    if default:
        print(f"\n[{label}] 检测到候选路径 / Detected candidate path: {default}")
        use_default = input(f"  使用此路径？/ Use this path? [Y/n]: ").strip().lower()
        if use_default in ('', 'y', 'yes'):
            return default

    while True:
        path = input(f"\n[{label}] 请输入文件路径 / Enter file path (或留空跳过 / or leave empty to skip): ").strip()
        if not path:
            if required:
                print("  [错误 / Error] 此项为必填，请提供有效路径。/ This field is required, please provide a valid path.")
                continue
            return None
        if os.path.isfile(path):
            return path
        print(f"  文件不存在 / File not found: {path}")


def prompt_float(label: str, default: float = 0.70,
                 min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    E: Prompt user for float value
    C: 提示用户输入浮点数
    用法 / Usage:
    prompt_float("Similarity Threshold τ / 相似度阈值 τ", default=0.70)
    """
    while True:
        raw = input(f"\n[{label}] 默认 / Default {default} [{min_val}-{max_val}]: ").strip()
        if not raw:
            return default
        try:
            val = float(raw)
            if min_val <= val <= max_val:
                return val
            print(f"  范围 / Range: [{min_val}, {max_val}]")
        except ValueError:
            print("  请输入有效数字。/ Please enter a valid number.")


def prompt_str(label: str, default: str = "") -> str:
    """
    E: Prompt user for string
    C: 提示用户输入字符串
    用法 / Usage:
    prompt_str("Model Name / 模型名称", default="...")
    """
    raw = input(f"\n[{label}] 默认 / Default '{default}': ").strip()
    return raw if raw else default


def auto_detect_files() -> tuple[Optional[str], Optional[str]]:
    """
    E: Auto-detect input files
        Gold standard: evaluation/data/gold/*.json
        Generated map: maps/*.json or debug_output/*/map_final.json
    C: 自动检测输入文件
        金标准: evaluation/data/gold/*.json
        生成导图: maps/*.json 或 debug_output/*/map_final.json
    """
    # E: Gold standard / C: 金标准
    gold_candidates = sorted(glob.glob("evaluation/data/gold/*.json"))
    gold_path = gold_candidates[-1] if gold_candidates else None

    # E: Generated map — prefer maps/ / C: 生成导图 — 优先 maps/
    maps = sorted(glob.glob("maps/*.json"))
    gen_path = maps[-1] if maps else None

    # E: Fallback — latest session from debug_output / C: 备选 — debug_output 中最新 session
    if not gen_path:
        debug_dirs = sorted(glob.glob("debug_output/*/"), reverse=True)
        for d in debug_dirs:
            finals = sorted(glob.glob(os.path.join(d, "*.json")))
            if finals:
                gen_path = finals[-1]
                break

    return gold_path, gen_path


class ProgressTracker:
    """E: Simple progress tracker / C: 简单进度追踪"""

    def __init__(self, total: int):
        self.total = total
        self.current = 0

    def start(self, name: str):
        self.current += 1
        print(f"\n[{'█' * self.current}{'░' * (self.total - self.current)}] "
              f"({self.current}/{self.total}) {name}...")

    def complete(self, name: str, status: str = "完成 / Done"):
        print(f"  ✓ {name} {status}")


def print_results_table(results: dict):
    """E: Print result summary to terminal / C: 在终端打印结果摘要"""
    print("\n" + "=" * 60)
    print("  评估结果摘要 / Evaluation Result Summary")
    print("=" * 60)
    for dim, metrics in results.items():
        if isinstance(metrics, dict):
            print(f"\n  [{dim}]")
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")
