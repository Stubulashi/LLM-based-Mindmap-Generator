"""
E: CLI utilities — multiselect, file prompt, progress tracking
C: 交互式 CLI 辅助 — 多选、文件提示、进度追踪
"""
import os
from typing import Optional

from evaluation.i18n import T


def interactive_multiselect(title: str, options: dict[str, str]) -> list[str]:
    """
    E: Interactive multiselect — type number(s) separated by comma/space, supports 'all'
    C: 交互式多选 — 终端键入编号（逗号/空格分隔），支持 'all'
    """
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    items = list(options.items())

    print(T(
        "  （输入 'all' 选择全部；输入编号多选，如 '1,2,3' 或 '1 3 5'）",
        "  (Type 'all' to select everything, or numbers like '1,2,3' / '1 3 5')",
    ))
    for idx, (key, desc) in enumerate(items, 1):
        print(f"  [{idx}] {desc}")

    while True:
        raw = input(T("\n> 请选择: ", "\n> Select: ")).strip()
        if not raw:
            print(T("  输入不能为空，请重新选择。", "  Input cannot be empty, please try again."))
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
                    print(T(
                        f"  无效编号: {p}（范围 1-{len(items)}）",
                        f"  Invalid number: {p} (range 1-{len(items)})",
                    ))
                    valid = False
            except ValueError:
                print(T(
                    f"  无效输入: {p}",
                    f"  Invalid input: {p}",
                ))
                valid = False
        if valid and selected:
            return [items[i][0] for i in sorted(selected)]


def prompt_file(label: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    E: Prompt user for file path
    C: 提示用户输入文件路径
    """
    if default:
        print(T(
            f"\n[{label}] 检测到候选路径: {default}",
            f"\n[{label}] Detected candidate path: {default}",
        ))
        use_default = input(T("  使用此路径？[Y/n]: ", "  Use this path? [Y/n]: ")).strip().lower()
        if use_default in ('', 'y', 'yes'):
            return default

    while True:
        path = input(T(
            f"\n[{label}] 请输入文件路径（留空跳过）: ",
            f"\n[{label}] Enter file path (leave empty to skip): ",
        )).strip()
        if not path:
            if required:
                print(T(
                    "  [错误] 此项为必填，请提供有效路径。",
                    "  [Error] This field is required, please provide a valid path.",
                ))
                continue
            return None
        if os.path.isfile(path):
            return path
        print(T(
            f"  文件不存在: {path}",
            f"  File not found: {path}",
        ))


def prompt_float(label: str, default: float = 0.70,
                 min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    E: Prompt user for float value
    C: 提示用户输入浮点数
    """
    while True:
        raw = input(T(
            f"\n[{label}] 默认值 {default}（范围 [{min_val}-{max_val}]）: ",
            f"\n[{label}] Default {default} [{min_val}-{max_val}]: ",
        )).strip()
        if not raw:
            return default
        try:
            val = float(raw)
            if min_val <= val <= max_val:
                return val
            print(T(
                f"  范围: [{min_val}, {max_val}]",
                f"  Range: [{min_val}, {max_val}]",
            ))
        except ValueError:
            print(T("  请输入有效数字。", "  Please enter a valid number."))


def prompt_str(label: str, default: str = "") -> str:
    """
    E: Prompt user for string
    C: 提示用户输入字符串
    """
    raw = input(T(
        f"\n[{label}] 默认值 '{default}': ",
        f"\n[{label}] Default '{default}': ",
    )).strip()
    return raw if raw else default


class ProgressTracker:
    """E: Simple progress tracker / C: 简单进度追踪"""

    def __init__(self, total: int):
        self.total = total
        self.current = 0

    def start(self, name: str):
        self.current += 1
        print(f"\n[{'█' * self.current}{'░' * (self.total - self.current)}] "
              f"({self.current}/{self.total}) {name}...")

    def complete(self, name: str, status: str = None):
        status = status or T("完成", "Done")
        print(f"  ✓ {name} {status}")


def print_results_table(results: dict):
    """E: Print result summary to terminal / C: 在终端打印结果摘要"""
    print("\n" + "=" * 60)
    print(T("  评估结果摘要", "  Evaluation Result Summary"))
    print("=" * 60)
    for dim, metrics in results.items():
        if isinstance(metrics, dict):
            print(f"\n  [{dim}]")
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")
