#!/usr/bin/env python3
"""C: debug_output 清理脚本 — 删除早于 N 天的会话目录。
   不自动挂入启动流程，需手动运行，避免误删最近调试产物。
E: debug_output cleanup script — remove session dirs older than N days.
   Not wired into startup; run manually to avoid deleting recent debug artifacts.

Usage / 用法:
    python scripts/cleanup_debug.py                 # 默认保留 30 天
    python scripts/cleanup_debug.py --days 7        # 保留最近 7 天
    python scripts/cleanup_debug.py --dry-run       # 仅列出待删项，不实际删除
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEBUG_DIR = ROOT / "debug_output"

# C: 会话目录命名形如 20260616_151358 / 20260730_083711_Saarland University 1
# E: Session dirs look like 20260616_151358 / 20260730_083711_Saarland University 1
_SESSION_RE = re.compile(r"^\d{8}_\d{6}")


def parse_args():
    parser = argparse.ArgumentParser(description="Clean up old debug_output session dirs")
    parser.add_argument("--days", type=int, default=30, help="Keep session dirs newer than N days (default 30)")
    parser.add_argument("--dry-run", action="store_true", help="List candidates without deleting")
    parser.add_argument("--debug-dir", type=str, default=str(DEFAULT_DEBUG_DIR), help="Root debug output dir")
    return parser.parse_args()


def main():
    args = parse_args()
    debug_dir = Path(args.debug_dir)
    if not debug_dir.is_dir():
        print(f"Debug dir not found / 调试目录不存在: {debug_dir}")
        sys.exit(1)

    cutoff = time.time() - args.days * 86400
    candidates = []
    for entry in sorted(debug_dir.iterdir()):
        if not entry.is_dir() or not _SESSION_RE.match(entry.name):
            continue
        try:
            # C: 以目录名中的时间戳判断（优于 mtime，避免文件被触摸）
            # E: Judge by the timestamp in the dir name (better than mtime)
            ts = time.mktime(time.strptime(entry.name[:15], "%Y%m%d_%H%M%S"))
        except (ValueError, OSError):
            continue
        if ts < cutoff:
            candidates.append(entry)

    if not candidates:
        print(f"No session dirs older than {args.days} days / 无早于 {args.days} 天的会话目录")
        return

    print(f"Found {len(candidates)} session dir(s) older than {args.days} days / 发现 {len(candidates)} 个超期会话目录")
    for c in candidates:
        print(f"  - {c.name}")

    if args.dry_run:
        print("Dry run — nothing deleted / 仅预览，未删除任何目录")
        return

    confirm = input("Delete these dirs? / 确认删除这些目录？ [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted / 已取消")
        return

    freed = 0
    for c in candidates:
        try:
            size = sum(f.stat().st_size for f in c.rglob("*") if f.is_file())
            for f in c.rglob("*"):
                if f.is_file():
                    f.unlink()
            c.rmdir()
            # C: 递归删除可能留下的空子目录 / E: remove any leftover empty subdirs
            for sub in sorted(c.rglob("*"), reverse=True):
                if sub.is_dir():
                    try:
                        sub.rmdir()
                    except OSError:
                        pass
            freed += size
            print(f"  ✓ Deleted / 已删除: {c.name} ({size / 1024:.0f} KB)")
        except OSError as e:
            print(f"  ✗ Failed / 失败: {c.name}: {e}")

    print(f"\nDone / 完成. Freed / 释放空间: {freed / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()

