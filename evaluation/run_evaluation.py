#!/usr/bin/env python3
"""
E: AI MindMap Quality Evaluation Tool — Unified Entry (Interactive CLI + Batch Mode)
C: AI MindMap 质量评估工具 — 统一入口（交互式 CLI + 批量模式）

Usage / 用法:
    python evaluation/run_evaluation.py                        # Interactive CLI / 交互式 CLI
    python evaluation/run_evaluation.py --batch                # Batch evaluation / 批量评估模式
    python evaluation/run_evaluation.py --batch --audio-dir PATH --gold-dir PATH

Workflow / 工作流程:
    1. Audio upload (manual or auto-discover) / 上传音频（手动或自动发现）
    2. Select evaluation methods / 选择评估方法
    3. For each audio: Whisper transcription → Mind map generation → Quality evaluation
       / 对每段音频：Whisper 转录 → 导图生成 → 质量评估
    4. Generate detailed Markdown report / 生成详细 Markdown 报告
    5. Dual save: debug_output/ + evaluation/data/sessions/{timestamp}/
       / 双轨保存
"""
import sys
import os
import argparse
import glob
import json
import math
import asyncio
import shutil
import copy
import random
import importlib
import subprocess
import time as time_module
from datetime import datetime
from typing import Optional

# E: Ensure project root is importable
# C: 确保可以 import 项目根目录下的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# E: Load .env BEFORE importing modules that use huggingface
#    (sentence-transformers in aligner.py needs HF_ENDPOINT set before first import)
# C: 在导入使用 huggingface 的模块之前加载 .env
#    (aligner.py 中的 sentence-transformers 需要在首次导入前设置 HF_ENDPOINT)
try:
    from dotenv import load_dotenv
except ImportError:
    print("=" * 60)
    print("  [!] 缺少依赖 python-dotenv")
    print("      请使用虚拟环境运行本项目:")
    print("      ./venv/bin/python evaluation/run_evaluation.py")
    print("      或先安装依赖: pip install -r requirements.txt")
    print("=" * 60)
    raise SystemExit(1)
from pathlib import Path
_env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
load_dotenv(dotenv_path=_env_path)

# E: api.env (real keys) is intentionally NOT loaded at module import time — it
#    would override the process environment for any host importing this module
#    (tests, future library users). It is loaded in main() instead, keeping CLI
#    behaviour identical to cli_pipeline.py while removing the import side effect.
# C: api.env（真实 key）刻意不在模块导入时加载 — 否则会覆盖任何导入本模块的
#    宿主进程的环境变量（测试、未来的库调用方）。改为在 main() 中加载，
#    CLI 行为与 cli_pipeline.py 保持一致，同时消除 import 副作用。

# E: Config is imported lazily inside functions (it snapshots env values at
#    class-definition time, so it must be imported AFTER api.env is loaded).
# C: Config 改为函数内延迟导入（其在类定义时快照 env 值，必须在 api.env
#    加载之后导入）。

from evaluation.core.data_loader import DataLoader, MindMapData
from evaluation.core.aligner import HungarianAligner
from evaluation.utils.console_utils import (
    interactive_multiselect,
    prompt_float,
    prompt_str,
    ProgressTracker,
    print_results_table,
)
from evaluation.utils.io_utils import read_json, write_json, save_intermediate_result, timestamp
from evaluation.report.markdown_renderer import MarkdownReportRenderer
from evaluation.i18n import T, set_lang

# E: MCP Client for audio transcription and map generation
# C: MCP Client，用于音频转录和导图生成
from mcp_client import MCPMindMapClient

# E: Project root — derived from this file so relative paths resolve correctly
#    regardless of the current working directory.
# C: 项目根目录 — 基于本文件推导，保证相对路径在任意工作目录下均正确解析。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_project_path(path: str) -> str:
    """
    E: Resolve a relative path against the project root; absolute paths pass through.
    C: 相对路径基于项目根目录解析；绝对路径原样返回。
    """
    return path if os.path.isabs(path) else os.path.join(_PROJECT_ROOT, path)


# ============================================================
# E: Required input files for each evaluation method
# C: 每种评估方法所需的输入文件
# ============================================================
# E: (method_name -> list of required file categories)
# C: (方法名 -> 必需文件类别列表)
METHOD_REQUIRED_FILES: dict[str, list[str]] = {
    'label':       ['gold', 'audio', 'concepts'],
    'hierarchy':   ['gold', 'audio'],
    'qa':          ['audio'],   # E: questions auto-generated / C: 问题自动生成
    'efficiency':  ['audio', 'timing', 'transcript', 'key_terms'],
    'multilingual':['audio', 'multilingual_results'],
    'human_corr':  ['audio'],   # E: interactive scoring / C: 交互式评分
    'full':        ['gold', 'audio', 'concepts', 'timing', 'transcript', 'key_terms', 'multilingual_results'],
}

# ============================================================
# E: Python package dependencies for each evaluation method
# C: 每种评估方法所需的 Python 第三方包
# ============================================================
# E: (method_name -> list of importable package names)
# C: (方法名 -> 可 import 的包名列表)
METHOD_DEPENDENCIES: dict[str, list[str]] = {
    'label':       ['numpy', 'sentence_transformers'],
    'hierarchy':   ['numpy', 'zss', 'sentence_transformers'],
    'qa':          ['openai'],   # E: refactored flow needs only OpenAI / C: 新流程仅需 openai
    'efficiency':  ['jiwer', 'jieba', 'scipy'],
    'multilingual': [],
    'human_corr':  ['scipy'],
    'full':        ['zss', 'jiwer', 'jieba', 'scipy', 'sentence_transformers', 'openai'],
}

# E: Pip install names for dependency display / auto-install
# C: pip 安装名称映射（用于显示安装命令和自动安装）
_PIP_PACKAGE_NAMES: dict[str, str] = {
    'nltk': 'nltk',
    'rouge_score': 'rouge-score',
    'bert_score': 'bert-score',
    'zss': 'zss',
    'jiwer': 'jiwer',
    'jieba': 'jieba',
    'scipy': 'scipy',
    'numpy': 'numpy',
    'sentence_transformers': 'sentence-transformers',
    'openai': 'openai',
}

# E: Human-readable descriptions for each file category
# C: 每种文件类别的人类可读描述
FILE_CATEGORY_DESC: dict[str, str] = {
    'gold':               'Gold standard mind map JSON / 金标准导图 JSON',
    'audio':              'Audio file (wav/mp3/m4a/ogg/flac) / 音频文件',
    'concepts':           'Essential concepts set JSON / 核心概念集合 JSON',
    'questions':          'QA question set JSON / 问答问题集 JSON',
    'timing':             'Timing logs JSON / 计时日志 JSON',
    'transcript':         'Reference transcript TXT / 人工转写标准文本 TXT',
    'key_terms':          'Key terms list JSON / 关键术语列表 JSON',
    'multilingual_results':'Multilingual test results JSON / 多语言测试结果 JSON',
    'human_scores':       'Human scoring data JSON / 人工评分数据 JSON',
}

# E: Default file search paths for each category
# C: 每种文件类别的默认搜索路径
FILE_CATEGORY_PATHS: dict[str, str] = {
    'gold':               'evaluation/data/gold',
    'audio':              'evaluation/data/audio',
    'concepts':           'evaluation/data/concepts',
    'questions':          'evaluation/data/questions',
    'timing':             'evaluation/data/timing',
    'transcript':         'evaluation/data/timing',
    'key_terms':          'evaluation/data/timing',
    'multilingual_results':'evaluation/data/multilingual',
    'human_scores':       'evaluation/data/human_scores',
}


def _file_category_label(cat: str) -> str:
    """
    E: Show a file category description in the active CLI language.
    C: 按当前 CLI 语言显示文件类别描述。
    """
    desc = FILE_CATEGORY_DESC.get(cat, cat)
    parts = desc.split(' / ', 1)
    if len(parts) == 2:
        return T(parts[1], parts[0])
    return desc


def _prompt_audio_selection(audio_files: list[str], source_label: str) -> list[str]:
    """
    E: List audio files by number and let the user pick one or more
        (comma/space separated, 'all' or Enter = all). Invalid input loops.
    C: 按编号列出音频文件，允许用户选择一个或多个
        （逗号/空格分隔，'all' 或回车 = 全部）。非法输入循环重问。
    """
    if not audio_files:
        return []
    if len(audio_files) == 1:
        print(f"  ✓ {source_label}: {os.path.basename(audio_files[0])}")
        return audio_files
    print(T(
        f"  共发现 {len(audio_files)} 个音频文件，请选择要评估的：",
        f"  {len(audio_files)} audio files found, pick the ones to evaluate:",
    ))
    for i, p in enumerate(audio_files, 1):
        print(f"    [{i}] {os.path.basename(p)}")
    while True:
        raw = input(T(
            "  请选择（编号多选，如 1,3 或 1 3；输入 all 或回车选择全部）: ",
            "  Select (numbers like 1,3 or 1 3; 'all' or Enter = everything): ",
        )).strip()
        if not raw or raw.lower() == 'all':
            return audio_files
        selected = set()
        parts = raw.replace(',', ' ').split()
        valid = True
        for p in parts:
            try:
                idx = int(p)
                if 1 <= idx <= len(audio_files):
                    selected.add(idx - 1)
                else:
                    print(T(
                        f"  无效编号: {p}（范围 1-{len(audio_files)}）",
                        f"  Invalid number: {p} (range 1-{len(audio_files)})",
                    ))
                    valid = False
            except ValueError:
                print(T(
                    f"  无效输入: {p}",
                    f"  Invalid input: {p}",
                ))
                valid = False
        if valid and selected:
            return [audio_files[i] for i in sorted(selected)]


def _prompt_audio_manual() -> Optional[list[str]]:
    """
    E: Mode B audio input — accept a single file path or a directory path.
        Invalid paths / unsupported formats loop with a clear message;
        returns the picked (copied) audio list, or None when skipped.
    C: 模式 B 音频输入 — 接受单个文件路径或目录路径；
        无效路径/不支持格式循环重试并给出明确提示；
        返回选中的（已复制）音频列表，跳过时返回 None。
    """
    from evaluation.utils.io_utils import AUDIO_EXTS, discover_audio_files
    while True:
        raw_path = input(T(
            "  「音频」文件或目录路径（例如 evaluation/data/audio/Saarland University 1.m4a，"
            "或目录如 /home/user/my_audios；留空跳过）: ",
            "  Audio file or directory path (e.g. evaluation/data/audio/Saarland University 1.m4a, "
            "or a directory like /home/user/my_audios; empty to skip): ",
        )).strip()
        if not raw_path:
            return None
        if os.path.isdir(raw_path):
            dir_files = discover_audio_files(raw_path)
            if not dir_files:
                print(T(
                    f"  ✗ 目录中没有音频文件: {raw_path}",
                    f"  ✗ No audio files in directory: {raw_path}",
                ))
                continue
            picked = _prompt_audio_selection(dir_files, T("检测到音频", "Detected audio"))
            return [_copy_to_data_dir(p, 'audio') for p in picked]
        if os.path.isfile(raw_path):
            ext = os.path.splitext(raw_path)[1].lower()
            if ext not in AUDIO_EXTS:
                print(T(
                    f"  ✗ 不支持的音频格式: {ext}（支持 wav/mp3/m4a/ogg/flac）",
                    f"  ✗ Unsupported audio format: {ext} (supported: wav/mp3/m4a/ogg/flac)",
                ))
                continue
            return [_copy_to_data_dir(raw_path, 'audio')]
        print(T(
            f"  ✗ 路径不存在: {raw_path}",
            f"  ✗ Path not found: {raw_path}",
        ))


# ============================================================
# E: Statistical utilities
# C: 统计工具函数
# ============================================================
def _mean(values: list[float]) -> float:
    """E: Compute mean / C: 计算均值"""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stdev(values: list[float]) -> float:
    """E: Compute sample standard deviation / C: 计算样本标准差"""
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


# ============================================================
# E: Dependency check — verify all required packages before evaluation
# C: 依赖预检 — 在评估开始前验证所有必需的第三方包
# ============================================================
def check_dependencies(
    selected_methods: list[str],
    auto_install: bool = False,
    ignore_missing: bool = False,
) -> bool:
    """
    E: Unified dependency pre-check — verify all required third-party packages are installed
    C: 统一依赖预检 — 验证所有必需的第三方包已安装

    Args / 参数:
        selected_methods: List of selected evaluation methods / 选中的评估方法列表
        auto_install: Auto-install missing packages via pip / 自动通过 pip 安装缺失包
        ignore_missing: Continue despite missing packages / 忽略缺失继续执行

    Returns / 返回:
        True if dependencies are satisfied (or ignored), False if should abort
        True 表示依赖满足（或用户选择忽略），False 表示应终止流程
    """
    # E: Expand 'full' to all actual methods
    # C: 展开 'full' 为所有实际方法
    methods_to_check = list(selected_methods)
    if 'full' in methods_to_check:
        methods_to_check.remove('full')
        for m in METHOD_DEPENDENCIES:
            if m != 'full' and m not in methods_to_check:
                methods_to_check.append(m)

    if not methods_to_check:
        return True

    # E: Collect all unique required packages
    # C: 收集所有唯一必需的包名
    required_pkgs: set[str] = set()
    for method in methods_to_check:
        deps = METHOD_DEPENDENCIES.get(method, [])
        for pkg in deps:
            required_pkgs.add(pkg)

    if not required_pkgs:
        return True

    # E: Check each package
    # C: 逐一检查每个包
    missing_pkgs: list[str] = []
    for pkg_name in sorted(required_pkgs):
        try:
            importlib.import_module(pkg_name)
        except ImportError:
            missing_pkgs.append(pkg_name)

    if not missing_pkgs:
        return True

    # E: Format install command / C: 构建安装命令
    pip_names = []
    for pkg in missing_pkgs:
        pip_names.append(_PIP_PACKAGE_NAMES.get(pkg, pkg))
    pip_cmd = f"pip install {' '.join(pip_names)}"

    print()
    print("=" * 60)
    print(T("  [!] 缺少必需依赖", "  [!] Missing Required Dependencies"))
    print("=" * 60)
    print(T(
        "  以下包是所选评估方法必需的：",
        "  The following packages are required for the selected methods:",
    ))
    print()
    for pkg in missing_pkgs:
        pip_name = _PIP_PACKAGE_NAMES.get(pkg, pkg)
        print(f"    - {pkg} ({pip_name})")
    print()
    print(T(
        f"  请在新终端中运行: {pip_cmd}",
        f"  Please open a new terminal and run: {pip_cmd}",
    ))
    print()

    if auto_install:
        print(T("  正在尝试自动安装...", "  Attempting auto-install..."))
        success = True
        for pkg in missing_pkgs:
            pip_name = _PIP_PACKAGE_NAMES.get(pkg, pkg)
            try:
                print(T(
                    f"  正在安装 {pip_name}...",
                    f"  Installing {pip_name}...",
                ))
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install', pip_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(T(
                    f"    ✓ {pip_name} 已安装",
                    f"    ✓ {pip_name} installed",
                ))
            except Exception as e:
                print(T(
                    f"    ✗ {pip_name} 安装失败: {e}",
                    f"    ✗ Failed to install {pip_name}: {e}",
                ))
                success = False
        if success:
            print()
            print(T(
                "  所有缺失包已成功安装！",
                "  All missing packages installed successfully!",
            ))
            return True
        else:
            print()
            print(T(
                "  部分包安装失败，请手动安装。",
                "  Some packages failed to install. Please install manually.",
            ))
            return False

    if ignore_missing:
        print(T(
            "  已设置 --ignore-missing-deps，将继续执行。",
            "  --ignore-missing-deps is set, continuing despite missing packages.",
        ))
        print()
        return True

    print(T(
        "  使用 --auto-install 自动安装，或 --ignore-missing-deps 忽略缺失继续执行。",
        "  Use --auto-install to auto-install, or --ignore-missing-deps to continue.",
    ))
    print()
    return False


# ============================================================
# E: File management utilities
# C: 文件管理工具函数
# ============================================================
def _ensure_dir(path: str):
    """E: Create directory if it doesn't exist / C: 确保目录存在"""
    os.makedirs(path, exist_ok=True)


def _format_gold_example(transcript_path: str, gold_json_path: str, max_transcript_chars: int = 3000) -> Optional[str]:
    """
    E: Format a gold example (transcript + gold mind map) as an in-context example block.
        The formatted block is inserted into the beginning of chat_history to guide the model
        to generate a mind map that matches the structural style of the gold standard.
    C: 将黄金示例（转录文本 + 金标准导图）格式化为 in-context 示例块。
        该示例块插入到 chat_history 最前面，指导模型生成更符合金标准结构的导图。

    Args / 参数:
        transcript_path: Path to transcript .txt file / 转录文本 .txt 文件路径
        gold_json_path: Path to gold standard mind map .json file / 金标准导图 .json 文件路径
        max_transcript_chars: Max chars of transcript to include / 转录文本最大包含字符数

    Returns / 返回:
        Formatted gold example string, or None if files cannot be loaded
        格式化后的黄金示例字符串，文件无法加载时返回 None
    """
    # E: Validate files exist / C: 验证文件存在
    if not transcript_path or not os.path.isfile(transcript_path):
        print(T(
            f"  [Gold Example] 转录文件不存在: {transcript_path}",
            f"  [Gold Example] Transcript not found: {transcript_path}",
        ))
        return None
    if not gold_json_path or not os.path.isfile(gold_json_path):
        print(T(
            f"  [Gold Example] 金标准JSON不存在: {gold_json_path}",
            f"  [Gold Example] Gold JSON not found: {gold_json_path}",
        ))
        return None

    # E: Read transcript / C: 读取转录文本
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
    except Exception as e:
        print(T(
            f"  [Gold Example] 转录读取失败: {e}",
            f"  [Gold Example] Failed to read transcript: {e}",
        ))
        return None

    # E: Truncate transcript if too long / C: 文本过长则截断
    if len(transcript_text) > max_transcript_chars:
        transcript_text = transcript_text[:max_transcript_chars] + "\n... (truncated / 已截断)"

    # E: Read and parse gold JSON / C: 读取并解析金标准 JSON
    try:
        with open(gold_json_path, 'r', encoding='utf-8') as f:
            gold_data = json.load(f)
    except Exception as e:
        print(T(
            f"  [Gold Example] 金标准JSON解析失败: {e}",
            f"  [Gold Example] Failed to parse gold JSON: {e}",
        ))
        return None

    # E: Serialize gold map as indented tree text / C: 将金标准导图序列化为缩进文本树
    gold_nodes = gold_data.get('nodes', [])
    tree_lines = _serialize_gold_tree(gold_nodes)
    tree_text = '\n'.join(tree_lines)

    # E: Format the complete example block / C: 格式化完整示例块
    example_block = (
        f"C: 【黄金示例 / Gold Example】以下是先前课程的一个优秀思维导图生成案例，请仔细学习其结构风格。\n"
        f"E: [Gold Example] Below is an excellent mind map generation example from a previous lecture. Study its structural style carefully.\n\n"
        f"C: 【原始转录文本 / Original Transcript】\n{transcript_text}\n\n"
        f"C: 【对应的高质量思维导图 / Corresponding High-Quality Mind Map】\n{tree_text}\n\n"
        f"C: 【重要指令】请参照以上示例的结构风格和层级划分方式，对接下来提供的新音频转录生成思维导图。"
        f"请特别注意：1) 层级深度和分支数量与示例保持一致；2) 节点标签精炼程度与示例类似；3) 父子关系的组织逻辑参照示例。\n"
        f"E: [Important Instruction] Please refer to the structural style and hierarchy organization of the above example when generating the mind map for the new audio transcript below. "
        f"Pay special attention to: 1) Maintain similar depth and branching factor; 2) Keep node label conciseness comparable; 3) Follow the same parent-child organization logic.\n"
        f"---\n"
    )

    print(T(
        f"  ✓ 黄金示例已格式化 ({len(transcript_text)} 转录字符, {len(gold_nodes)} 金标准节点)",
        f"  ✓ Gold example formatted ({len(transcript_text)} transcript chars, {len(gold_nodes)} gold nodes)",
    ))
    return example_block


def _serialize_gold_tree(nodes: list[dict]) -> list[str]:
    """
    E: Serialize gold standard nodes into an indented text tree representation.
    C: 将金标准节点序列化为缩进文本树表示。

    Args / 参数:
        nodes: List of node dicts with id, label, parent_id / 含 id, label, parent_id 的节点列表

    Returns / 返回:
        List of indented lines / 缩进文本行列表
    """
    # E: Build parent-child index / C: 构建父子索引
    children_map: dict[str, list[dict]] = {}
    root_nodes = []
    for n in nodes:
        pid = n.get('parent_id')
        if pid is None:
            root_nodes.append(n)
        else:
            children_map.setdefault(pid, []).append(n)

    lines = []

    def _render(node: dict, depth: int):
        indent = '  ' * depth
        label = node.get('label', '')
        lines.append(f"{indent}- {label}")
        # E: Include details if present (max 2) / C: 如果有详情，最多显示2条
        details = node.get('details', [])
        for d in details[:2]:
            lines.append(f"{indent}  [{d}]")
        children = sorted(children_map.get(node['id'], []), key=lambda x: x.get('label', ''))
        for child in children:
            _render(child, depth + 1)

    if root_nodes:
        _render(root_nodes[0], 0)

    return lines


def _copy_to_data_dir(src_path: str, category: str) -> str:
    """
    E: Copy file to the appropriate evaluation/data/ subdirectory
    C: 将文件复制到 evaluation/data/ 下对应的子目录

    Args / 参数:
        src_path: Source file path / 源文件路径
        category: File category (e.g., 'gold', 'audio', 'concepts') / 文件类别

    Returns / 返回:
        Destination path / 目标路径
    """
    dest_dir = os.path.join(os.getcwd(), FILE_CATEGORY_PATHS.get(category, 'evaluation/data'))
    _ensure_dir(dest_dir)
    base_name = os.path.basename(src_path)
    dest_path = os.path.join(dest_dir, base_name)

    if os.path.abspath(src_path) != os.path.abspath(dest_path):
        shutil.copy2(src_path, dest_path)
        print(T(
            f"  ✓ 已复制到: {dest_path}",
            f"  ✓ Copied to: {dest_path}",
        ))
    return dest_path


def _save_dual_output(
    pair_name: str,
    data: dict,
    data_type: str,
    session_dir: str,
    timestamp_str: str,
):
    """
    E: Save intermediate/final results to both debug_output/ and sessions/ directories
    C: 将中间/最终结果同时保存到 debug_output/ 和 sessions/ 目录

    Args / 参数:
        pair_name: Pair name for filename / 配对的名称
        data: Data dict to save / 要保存的数据字典
        data_type: Type label (e.g., 'transcription', 'map', 'eval') / 数据类型标签
        session_dir: Session subdirectory path / 会话子目录路径
        timestamp_str: Timestamp string for filename / 时间戳字符串
    """
    # E: Path 1: evaluation/data/sessions/{timestamp}/{pair_name}/
    # C: 路径 1：evaluation/data/sessions/{timestamp}/{pair_name}/
    pair_dir = os.path.join(session_dir, pair_name)
    _ensure_dir(pair_dir)
    session_path = os.path.join(pair_dir, f"{data_type}.json")
    write_json(session_path, data)
    print(T(
        f"  ✓ 已保存到会话: {session_path}",
        f"  ✓ Saved to session: {session_path}",
    ))

    # E: Path 2: debug_output/{data_type}_{pair_name}_{timestamp}.json
    # C: 路径 2：debug_output/{data_type}_{pair_name}_{timestamp}.json
    debug_dir = os.path.join(os.getcwd(), "debug_output")
    _ensure_dir(debug_dir)
    debug_filename = f"{data_type}_{pair_name}_{timestamp_str}.json"
    debug_path = os.path.join(debug_dir, debug_filename)
    write_json(debug_path, data)
    print(T(
        f"  ✓ 已保存到调试: {debug_path}",
        f"  ✓ Saved to debug: {debug_path}",
    ))


def _save_timing_log(
    pair_name: str,
    session_dir: str,
    timestamp_str: str,
    timing_snapshots: list[dict],
    wall_start: str,
    wall_end: str,
    anomalies: list[str],
    stt_status: str = "ok",
    num_repetitions: int = 1,
) -> str:
    """
    E: Persist the timing log to session + debug_output (dual-track, same
        convention as _save_dual_output). Returns the session-side path.
    C: 将计时日志双轨落盘（会话目录 + debug_output，与 _save_dual_output
        约定一致）。返回会话侧路径。

    Fields / 字段:
        wall_start/wall_end: ISO evaluation start/end timestamps / ISO 起止时间戳
        stages: per-stage {stage, start, end, duration, sub_stages} / 各阶段快照
        total_latency_s / p50 / p95 / staged_timing / stt_status / anomalies
    """
    from evaluation.efficiency.eval_efficiency import _compute_latency
    latency = _compute_latency(timing_snapshots or [])
    log_data = {
        "pair_name": pair_name,
        "wall_start": wall_start,
        "wall_end": wall_end,
        "stt_status": stt_status,
        "anomalies": anomalies,
        "num_repetitions": num_repetitions,
        "stages": timing_snapshots or [],
        "total_latency_s": latency.get("t_total_p50", 0.0),
        "p50": latency.get("t_total_p50", 0.0),
        "p95": latency.get("t_total_p95", 0.0),
        "staged_timing": latency.get("staged_timing", {}),
    }
    pair_dir = os.path.join(session_dir, pair_name)
    _ensure_dir(pair_dir)
    session_path = os.path.join(pair_dir, "timing_log.json")
    write_json(session_path, log_data)
    debug_dir = os.path.join(os.getcwd(), "debug_output")
    _ensure_dir(debug_dir)
    debug_path = os.path.join(debug_dir, f"timing_log_{pair_name}_{timestamp_str}.json")
    write_json(debug_path, log_data)
    return session_path


def _ensure_required_files(
    selected_methods: list[str],
    uploaded_files: dict[str, str],
) -> list[str]:
    """
    E: Check if all required files exist for selected methods
    C: 检查所选方法的所有必需文件是否存在

    Args / 参数:
        selected_methods: List of selected evaluation methods / 选中的评估方法列表
        uploaded_files: Dict of {category: file_path} already obtained / 已获得的 {类别: 文件路径} 字典

    Returns / 返回:
        List of missing file descriptions / 缺失的文件描述列表
    """
    needed_categories = set()
    for method in selected_methods:
        if method in METHOD_REQUIRED_FILES:
            for cat in METHOD_REQUIRED_FILES[method]:
                needed_categories.add(cat)

    missing = []
    for cat in sorted(needed_categories):
        if cat not in uploaded_files or not uploaded_files.get(cat):
            missing.append((cat, _file_category_label(cat)))
    return missing


def _collect_uploaded_files() -> dict[str, str]:
    """
    E: Interactive file collection from user
    C: 交互式文件收集（从用户处收集文件）

    Supports two modes:
    A) Batch prepare: user places all files in correct directories, auto-detect
    B) Step-by-step: user uploads each file individually

    Returns / 返回:
        Dict of {category: file_path} / {类别: 文件路径} 字典
    """
    uploaded: dict[str, str] = {}

    print(f"\n{'=' * 60}")
    print(T("  文件上传", "  File Upload"))
    print(f"{'=' * 60}")
    print(T(
        "  您可以选择：\n"
        "  A) 将所有必需文件放到 evaluation/data/ 对应子目录下，系统自动检测。\n"
        "     常用目录：金标准 evaluation/data/gold/、音频 evaluation/data/audio/、\n"
        "     概念集 evaluation/data/concepts/、计时日志 evaluation/data/timing/。\n"
        "  B) 跟随提示逐个输入文件路径。\n"
        "  上传的文件将自动复制到 evaluation/data/ 目录中备用。",
        "  You can:\n"
        "  A) Place all required files in the evaluation/data/ subdirectories and let the system auto-detect them.\n"
        "     Common dirs: gold evaluation/data/gold/, audio evaluation/data/audio/,\n"
        "     concepts evaluation/data/concepts/, timing logs evaluation/data/timing/.\n"
        "  B) Enter each file path manually following the prompts.\n"
        "  Files you upload will be automatically copied to the evaluation/data/ directory for future use.",
    ))
    print()

    mode = input(T(
        "  选择模式 [A/b]（A=自动检测，b=手动输入）: ",
        "  Select mode [A/b] (A=auto-detect, b=manual input): ",
    )).strip().lower()

    if mode in ('', 'a'):
        # E: Mode A — auto-detect from standard directories
        # C: 模式 A — 从标准目录自动检测
        print(T(
            "\n  模式 A：从标准目录自动检测文件...",
            "\n  Mode A: Auto-detecting files from standard directories...",
        ))

        # E: Audio — discover all candidates, list them by number, and let the
        #    user pick one or more. Missing audio is recoverable (switch to B).
        # C: 音频 — 发现全部候选，按编号列出，允许选择一个或多个；
        #    无音频时可恢复（可切换模式 B）。
        from evaluation.utils.io_utils import discover_audio_files
        audio_dir_default = _resolve_project_path("evaluation/data/audio")
        audio_candidates = discover_audio_files(audio_dir_default)
        if audio_candidates:
            selected_audios = _prompt_audio_selection(
                audio_candidates, T("检测到音频", "Detected audio"),
            )
            uploaded['audio_files'] = selected_audios
            uploaded['audio'] = selected_audios[0]
            print(T(
                f"  ✓ 已选择 {len(selected_audios)} 个音频",
                f"  ✓ Selected {len(selected_audios)} audio file(s)",
            ))
        else:
            print(T(
                f"  ✗ 未在 {audio_dir_default} 下找到音频文件（支持 wav/mp3/m4a/ogg/flac）。",
                f"  ✗ No audio files found under {audio_dir_default} (supported: wav/mp3/m4a/ogg/flac).",
            ))
            switch_b = input(T(
                "  是否切换为模式 B 手动输入音频路径？[y/N]: ",
                "  Switch to Mode B to enter an audio path manually? [y/N]: ",
            )).strip().lower()
            if switch_b in ('y', 'yes'):
                picked = _prompt_audio_manual()
                if picked:
                    uploaded['audio_files'] = picked
                    uploaded['audio'] = picked[0]

        # E: Gold detection — root (non-example) first with same-name pairing,
        #    then fall back to the best GTC/YQL tree of the detected audio.
        # C: 金标准检测 — 优先根目录（排除示例）且与音频同名配对，
        #    无匹配时回退到已检测音频在 GTC/YQL 下的择优树。
        gold_candidates = sorted(glob.glob("evaluation/data/gold/*.json"))
        gold_candidates = [f for f in gold_candidates if 'example' not in os.path.basename(f)]
        gold_path = None
        if gold_candidates:
            if uploaded.get('audio'):
                audio_base = os.path.splitext(os.path.basename(uploaded['audio']))[0]
                same_name = [f for f in gold_candidates
                             if os.path.splitext(os.path.basename(f))[0] == audio_base]
                if same_name:
                    gold_path = same_name[0]
            if gold_path is None:
                gold_path = gold_candidates[-1]
            uploaded['gold'] = gold_path
            print(f"  ✓ {T('检测到金标准', 'Detected gold')}: {os.path.basename(uploaded['gold'])}")
        elif uploaded.get('audio'):
            gold_base = os.path.splitext(os.path.basename(uploaded['audio']))[0]
            gold_path, source = _find_gold_auto(gold_base, "evaluation/data/gold")
            if gold_path:
                uploaded['gold'] = gold_path
                print(f"  ✓ {T('检测到金标准（GTC/YQL）', 'Detected gold (GTC/YQL)')}: "
                      f"{os.path.basename(gold_path)} ({source})")
            else:
                print(T(
                    "  ⚠ 未在根目录/GTC/YQL 找到金标准，依赖金标准的评估将无法执行。",
                    "  ⚠ No gold standard found in root/GTC/YQL — methods requiring gold will fail.",
                ))

        concept_candidates = sorted(glob.glob("evaluation/data/concepts/*.json"))
        concept_candidates = [f for f in concept_candidates if 'example' not in os.path.basename(f)]
        if concept_candidates:
            uploaded['concepts'] = concept_candidates[-1]
            print(f"  ✓ {T('检测到概念集', 'Detected concepts')}: {os.path.basename(uploaded['concepts'])}")

        q_candidates = sorted(glob.glob("evaluation/data/questions/*.json"))
        q_candidates = [f for f in q_candidates if 'example' not in os.path.basename(f)]
        if q_candidates:
            uploaded['questions'] = q_candidates[-1]
            print(f"  ✓ {T('检测到问题集', 'Detected questions')}: {os.path.basename(uploaded['questions'])}")

        timing_candidates = sorted(glob.glob("evaluation/data/timing/*.json"))
        timing_candidates = [f for f in timing_candidates if 'example' not in os.path.basename(f)]
        if timing_candidates:
            uploaded['timing'] = timing_candidates[-1]
            print(f"  ✓ {T('检测到计时日志', 'Detected timing logs')}: {os.path.basename(uploaded['timing'])}")

        # E: Key terms for KTRR — same timing dir, matched by filename containing
        #    'key_terms' (exclude example files).
        # C: KTRR 关键术语 — 位于计时目录，按文件名含 'key_terms' 匹配（排除示例）。
        kt_candidates = sorted(glob.glob("evaluation/data/timing/*key_terms*.json"))
        kt_candidates = [f for f in kt_candidates if 'example' not in os.path.basename(f)]
        if kt_candidates:
            uploaded['key_terms'] = kt_candidates[-1]
            print(f"  ✓ {T('检测到关键术语', 'Detected key terms')}: {os.path.basename(uploaded['key_terms'])}")

        transcript_candidates = sorted(glob.glob("evaluation/data/timing/*.txt"))
        transcript_candidates = [f for f in transcript_candidates if 'example' not in os.path.basename(f)]
        if transcript_candidates:
            uploaded['transcript'] = transcript_candidates[-1]
            print(f"  ✓ {T('检测到标准文本', 'Detected transcript')}: {os.path.basename(uploaded['transcript'])}")

        ml_candidates = sorted(glob.glob("evaluation/data/multilingual/*.json"))
        ml_candidates = [f for f in ml_candidates if 'example' not in os.path.basename(f)]
        if ml_candidates:
            uploaded['multilingual_results'] = ml_candidates[-1]
            print(f"  ✓ {T('检测到多语言数据', 'Detected multilingual data')}: {os.path.basename(uploaded['multilingual_results'])}")

        # E: Human scores — collect ALL questionnaire files (multi-questionnaire input)
        # C: 人工评分 — 收集全部问卷文件（多份问卷一起输入）
        hs_candidates = sorted(glob.glob("evaluation/data/human_scores/*.json"))
        hs_candidates = [f for f in hs_candidates if 'example' not in os.path.basename(f)]
        if hs_candidates:
            uploaded['human_scores'] = hs_candidates
            print(f"  ✓ {T('检测到', 'Detected')} {len(hs_candidates)} {T('份问卷文件', 'questionnaire file(s)')}")

    else:
        # E: Mode B — step-by-step upload (previously unreachable because the
        #    condition above covered 'b' as well; 'b' now lands here).
        # C: 模式 B — 逐步上传（此前条件把 'b' 也归入 A 路径导致本分支不可达；
        #    现在输入 'b' 会正确进入本分支）
        print(T(
            "\n  模式 B：逐步输入文件路径...",
            "\n  Mode B: Step-by-step file upload...",
        ))

        for cat, desc in FILE_CATEGORY_DESC.items():
            label = _file_category_label(cat)
            if cat == 'audio':
                # E: Audio accepts a single file OR a directory path (Mode B).
                # C: 音频类别接受单个文件路径或目录路径（模式 B）。
                picked = _prompt_audio_manual()
                if picked:
                    uploaded['audio_files'] = picked
                    uploaded['audio'] = picked[0]
                continue
            skip = input(T(
                f"\n  是否上传「{label}」？[Y/n]: ",
                f"\n  Upload {desc}? [Y/n]: ",
            )).strip().lower()
            if skip in ('', 'y', 'yes'):
                ext_hint = " (wav/mp3/m4a/ogg/flac)" if cat == 'audio' else " (JSON/TXT)"
                example = {
                    'gold': 'evaluation/data/gold/Saarland University 1.json',
                    'audio': 'evaluation/data/audio/Saarland University 1.wav',
                    'concepts': 'evaluation/data/concepts/essential_concepts.json',
                    'questions': 'evaluation/data/questions/qa_questions.json',
                    'timing': 'evaluation/data/timing/timing_logs.json',
                    'transcript': 'evaluation/data/timing/reference_transcript.txt',
                    'key_terms': 'evaluation/data/timing/key_terms.json',
                    'multilingual_results': 'evaluation/data/multilingual/cn_results.json',
                    'human_scores': 'evaluation/data/human_scores/human_scores_Q1.json',
                }.get(cat, FILE_CATEGORY_PATHS.get(cat, 'evaluation/data'))
                path = input(T(
                    f"  「{label}」文件路径（例如 {example}）: ",
                    f"  Enter file path for {desc} (e.g. {example}): ",
                )).strip()
                if path and os.path.isfile(path):
                    uploaded[cat] = _copy_to_data_dir(path, cat)
                else:
                    print(T(
                        f"  ✗ 文件不存在: {path or '(空)'}",
                        f"  ✗ File not found: {path or '(empty)'}",
                    ))
                    print(T(
                        f"    支持格式{ext_hint}",
                        f"    Supported formats{ext_hint}",
                    ))
                    print(T(
                        f"    推荐放置目录: {FILE_CATEGORY_PATHS.get(cat, 'evaluation/data')}",
                        f"    Recommended dir: {FILE_CATEGORY_PATHS.get(cat, 'evaluation/data')}",
                    ))
                    print(T("    已跳过", "    Skipped"))

    return uploaded


# ============================================================
# E: Audio-gold pair discovery
# C: 音频-金标准配对发现
# ============================================================
def _find_gold_auto(pair_name: str, gold_dir: str) -> tuple[Optional[str], Optional[str]]:
    """
    E: Locate the gold JSON for a pair across three sources — root (non-example),
        then the better of GTC/YQL (shared selection rule: more nodes wins, tie → GTC).
    C: 跨三个来源为配对定位金标准 — 根目录（非 example）优先，其次 GTC/YQL
        择优（共享择优规则：节点数多者优先，平局取 GTC）。

    Returns (gold_path, source); source in ('ROOT', 'GTC', 'YQL', None).
    返回 (gold_path, source)；source 为 'ROOT' / 'GTC' / 'YQL' / None。
    """
    gold_dir_resolved = _resolve_project_path(gold_dir)
    root = os.path.join(gold_dir_resolved, f"{pair_name}.json")
    if os.path.isfile(root):
        return root, "ROOT"
    from evaluation.human_correlation.interactive_scorer import pick_best_human_tree
    tree, source = pick_best_human_tree(pair_name, gold_dir_resolved)
    if tree is not None and source:
        return os.path.join(gold_dir_resolved, source, f"{pair_name}.json"), source
    return None, None


def discover_pairs(
    audio_dir: str = "evaluation/data/audio",
    gold_dir: str = "evaluation/data/gold",
) -> list[tuple[str, str, str]]:
    """
    E: Auto-discover audio file and gold JSON file pairs
    C: 自动发现音频文件与金标准 JSON 文件的配对

    Pairing rule / 配对规则:
        Strip audio file extension → locate matching gold JSON in the root,
        GTC or YQL gold directories (best tree wins).
        / 音频文件名去掉后缀 → 在根目录、GTC 或 YQL 金标准目录中定位同名 JSON
        （取最优树）。

    Args / 参数:
        audio_dir: Audio directory / 音频目录
        gold_dir: Gold standard root dir / 金标准根目录

    Returns / 返回:
        [(pair_name, audio_path, gold_path), ...]
    """
    pairs = []

    audio_dir_resolved = _resolve_project_path(audio_dir)
    gold_dir_resolved = _resolve_project_path(gold_dir)

    if not os.path.isdir(audio_dir_resolved):
        print(T(
            f"[Batch] 音频目录不存在: {audio_dir_resolved}",
            f"[Batch] Audio directory not found: {audio_dir_resolved}",
        ))
        return []

    # E: Shared audio discovery (same rule as interactive Mode A / triple report)
    # C: 共享音频发现（与交互模式 A / 三元组报告同一规则）
    from evaluation.utils.io_utils import discover_audio_files
    audio_candidates = discover_audio_files(audio_dir_resolved)

    if not audio_candidates:
        print(T(
            f"[Batch] 未找到音频文件: {audio_dir}",
            f"[Batch] No audio files found: {audio_dir}",
        ))
        return []

    missing_hint = T(
        f"  请将金标准 JSON 放入 {os.path.join(gold_dir_resolved, 'GTC')} 或 "
        f"{os.path.join(gold_dir_resolved, 'YQL')} 下，文件名与音频同名"
        f"（<音频名>.json）。",
        f"  Place the gold JSON under GTC/ or YQL/ with the same basename as the audio.",
    )

    for apath in audio_candidates:
        base = os.path.splitext(os.path.basename(apath))[0]
        gold_path, source = _find_gold_auto(base, gold_dir_resolved)
        if gold_path:
            pairs.append((base, apath, gold_path))
        else:
            print(T(
                f"[Batch] 警告：未找到金标准: {base}",
                f"[Batch] Warning: no gold file found: {base}",
            ))
            print(missing_hint)

    pairs.sort(key=lambda x: x[0])
    return pairs


# ============================================================
# E: Evaluation runner for a single pair
# C: 单配对评估执行器
# ============================================================
def _run_evaluation_for_pair(
    gold_path: str,
    gen_data: dict,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    threshold: float = 0.70,
    essential_concepts: Optional[list[str]] = None,
    selected_methods: Optional[list[str]] = None,
    transcript_text: str = "",
    questions: Optional[list[dict]] = None,
    timing_snapshots: Optional[list[dict]] = None,
    multilingual_input: Optional[dict | list] = None,
    human_scores: Optional[list[dict]] = None,
    key_terms: Optional[list[str]] = None,
    ground_truth_text: Optional[str] = None,
) -> dict:
    """
    E: Execute all selected evaluation methods for a single pair
    C: 对单个配对执行所选的所有评估方法

    Args / 参数:
        gold_path: Gold standard file path / 金标准文件路径
        gen_data: Generated map dict / 生成导图的字典
        model_name: Embedding model name / Embedding 模型名称
        threshold: Similarity threshold / 相似度阈值
        essential_concepts: Essential concepts for Entity Recall / 核心概念集合
        selected_methods: List of evaluation methods to run / 要运行的评估方法列表
        questions: Quiz questions for §3 QA / §3 QA 的测验题
        timing_snapshots: Timing logs for §4 Efficiency / §4 效率的计时日志
        multilingual_input: §5 multilingual data (dict with cn/en/mixed keys or list) / §5 多语言数据
        human_scores: §6 human scores / §6 人工评分数据
        key_terms: Key term list for §4 KTRR / §4 KTRR 的关键术语列表
        ground_truth_text: Reference transcript for §4 WER / §4 WER 的人工转写标准文本

    Returns / 返回:
        Evaluation results dict / 评估结果字典
    """
    if selected_methods is None:
        selected_methods = ['label', 'hierarchy', 'efficiency']

    from evaluation.core.data_loader import DataLoader
    from evaluation.core.aligner import HungarianAligner

    gold_map = DataLoader.from_map_file(gold_path)
    if gold_map is None:
        return {"error": "Gold standard load failed / 金标准加载失败"}

    gen_map = DataLoader.from_flat_dict(gen_data)
    if gen_map is None or gen_map.node_count == 0:
        return {"error": "Generated map load failed / 生成图加载失败"}

    aligner = HungarianAligner(model_name=model_name, threshold=threshold)

    # E: §1.1 Shared alignment — computed ONCE and reused by both label and
    #    hierarchy metrics (spec §1.1: all edge-level metrics share the same M_τ).
    #    Previously label and hierarchy each ran a full Hungarian alignment,
    #    doubling embedding cost.
    # C: §1.1 共享对齐 — 只计算一次，label 与 hierarchy 指标复用同一结果
    #    （规范 §1.1：所有边级指标共享同一 M_τ）。此前两者各执行一次完整
    #    匈牙利匹配，embedding 开销翻倍。
    alignment = aligner.align(gold_map.nodes, gen_map.nodes)
    results = {}

    # E: §1 Label Quality / C: 标签质量评估
    if 'label' in selected_methods:
        from evaluation.label.eval_label import evaluate_label_quality
        try:
            label_result = evaluate_label_quality(gold_map, gen_map, aligner, essential_concepts, alignment=alignment)
            results['label'] = label_result.to_dict()
        except Exception as e:
            results['label'] = {"error": str(e)}

    # E: §2 Hierarchy / C: 层级结构评估
    if 'hierarchy' in selected_methods:
        from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
        try:
            hier_result = evaluate_hierarchy_quality(
                gold_map, gen_map, alignment, similarity_threshold=threshold,
            )
            results['hierarchy'] = hier_result.to_dict()
        except Exception as e:
            results['hierarchy'] = {"error": str(e)}

    # E: §3 QA / C: 下游 QA 评估（重构：问题自动生成 + 逐题 1-5 评分）
    if 'qa' in selected_methods:
        from evaluation.qa.eval_qa import QAEvaluator
        try:
            qa_eval = QAEvaluator()
            # E: questions may be None — the refactored flow auto-generates 20
            #    questions via an independent AI from the transcript.
            # C: questions 可为 None — 重构流程会由独立 AI 依据转录自动生成 20 题。
            qa_result = qa_eval.evaluate(transcript_text, gen_map.nodes, questions)
            results['qa'] = qa_result.to_dict()
        except Exception as e:
            results['qa'] = {"error": str(e)}

    # E: §4 Efficiency / C: 效率与 STT 评估
    if 'efficiency' in selected_methods:
        from evaluation.efficiency.eval_efficiency import evaluate_efficiency
        try:
            eff_result = evaluate_efficiency(
                timing_snapshots=timing_snapshots,
                stt_text=transcript_text or None,
                ground_truth_text=ground_truth_text or None,
                key_terms=key_terms,
            )
            results['efficiency'] = eff_result.to_dict()
        except Exception as e:
            results['efficiency'] = {"error": str(e)}

    # E: §5 Multilingual / C: 多语言评估
    if 'multilingual' in selected_methods:
        from evaluation.multilingual.eval_multilingual import evaluate_multilingual
        try:
            multi_kwargs = {}
            if isinstance(multilingual_input, dict):
                for k in ('cn_results', 'en_results', 'mixed_results', 'noise_test_results', 'noise_source_text'):
                    if k in multilingual_input:
                        multi_kwargs[k] = multilingual_input[k]
            elif isinstance(multilingual_input, list):
                multi_kwargs['noise_test_results'] = multilingual_input
            multi_result = evaluate_multilingual(**multi_kwargs)
            results['multilingual'] = multi_result.to_dict()
        except Exception as e:
            results['multilingual'] = {"error": str(e)}

    # E: §6 Human Correlation / C: 人工评估（交互式双评分）
    if 'human_corr' in selected_methods:
        from evaluation.human_correlation.eval_human_correlation import (
            evaluate_human_scores, evaluate_human_correlation,
        )
        try:
            if human_scores:
                # E: New interactive dual-scoring format / C: 新交互式双评分格式
                if isinstance(human_scores, list) and human_scores and (
                    'gen_score' in human_scores[0] or 'human_score' in human_scores[0]
                ):
                    hc_result = evaluate_human_scores(human_scores)
                    results['human_corr'] = hc_result if isinstance(hc_result, dict) else hc_result.to_dict()
                else:
                    # E: Legacy correlation format / C: 旧相关性格式
                    hc_result = evaluate_human_correlation(human_scores=human_scores)
                    results['human_corr'] = hc_result.to_dict()
            else:
                results['human_corr'] = {"error": "requires interactive scoring / 需要交互式评分"}
        except Exception as e:
            results['human_corr'] = {"error": str(e)}

    return results


# ============================================================
# E: Average multiple evaluation run results into one result
# C: 将多次评估运行的结果取平均值
# ============================================================
def _average_eval_results(run_results: list[dict]) -> dict:
    """
    E: Average multiple independent evaluation run results.
        Each run_result is the dict returned by _run_evaluation_for_pair.
        All numeric metric values are averaged; non-numeric fields from the
        first result are deep-copied so originals are never mutated.
    C: 对多次独立评估运行结果取平均值。
        每次 run_result 是 _run_evaluation_for_pair 返回的字典。
        所有数值型指标取平均值；非数值字段使用第一次运行的深拷贝。
    """
    if not run_results:
        return {}
    if len(run_results) == 1:
        return copy.deepcopy(run_results[0])

    # E: Collect all (dim_key, metric_key) pairs that are numeric across all runs
    # C: 收集在所有运行中均为数值型的 (dim_key, metric_key) 对
    all_keys: dict[tuple[str, str], list[float]] = {}
    for rr in run_results:
        for dim_key, dim_data in rr.items():
            if isinstance(dim_data, dict) and 'error' not in dim_data:
                for metric_key, metric_val in dim_data.items():
                    if isinstance(metric_val, (int, float)):
                        key = (dim_key, metric_key)
                        if key not in all_keys:
                            all_keys[key] = []
                        all_keys[key].append(metric_val)

    # E: Count fields are averaged as rounded integers so counts stay consistent
    #    with the detail tables (e.g. tp=1.5 with 3 match rows would be confusing).
    # C: 计数类字段平均后取整，保证计数与明细表一致（如 tp=1.5 却有三行匹配明细会令人困惑）。
    COUNT_KEYS = {'tp', 'fp', 'fn', 'edge_tp', 'edge_fp', 'edge_fn', 'pc_tp',
                  'entity_total', 'gold_count', 'gen_count'}

    # E: Build averaged result, starting from a deep copy of the first run
    # C: 构建平均值结果，从第一次运行的深拷贝开始
    averaged = copy.deepcopy(run_results[0])
    for (dim_key, metric_key), values in all_keys.items():
        if dim_key in averaged and isinstance(averaged[dim_key], dict):
            avg_val = sum(values) / len(values)
            if metric_key in COUNT_KEYS:
                avg_val = int(round(avg_val))
            averaged[dim_key][metric_key] = avg_val

    # E: nTED may be None in some runs (zss failure) — if any run misses it,
    #    mark the averaged value unavailable instead of silently keeping the
    #    first run's value.
    # C: nTED 可能在某轮为 None（zss 失败）— 若存在缺失轮次，将平均值标记为
    #    不可用，而非静默沿用首轮值。
    hier_nted_missing = 0
    hier_nted_present = 0
    for rr in run_results:
        hier = rr.get('hierarchy', {})
        if isinstance(hier, dict) and 'error' not in hier and 'nted' in hier:
            if hier['nted'] is None:
                hier_nted_missing += 1
            else:
                hier_nted_present += 1
    if hier_nted_missing > 0 and hier_nted_present > 0:
        if 'hierarchy' in averaged and isinstance(averaged['hierarchy'], dict):
            averaged['hierarchy']['nted'] = None
            averaged['hierarchy']['nted_partial'] = True

    return averaged


# ============================================================
# E: Single pipeline: audio → transcription → map → evaluation
# C: 单条管线：音频 → 转录 → 导图 → 评估
# ============================================================
async def _run_single_pipeline(
    pair_name: str,
    audio_path: str,
    gold_path: Optional[str],
    mcp_client: Optional[MCPMindMapClient],
    session_dir: str,
    timestamp_str: str,
    selected_methods: list[str],
    model_name: str,
    threshold: float,
    essential_concepts: Optional[list[str]] = None,
    gold_example_context: Optional[str] = None,
    questions_path: Optional[str] = None,
    repeat_count: int = 1,
    human_scores: Optional[list] = None,
    key_terms: Optional[list[str]] = None,
    multilingual_input: Optional[dict | list] = None,
    ground_truth_text: Optional[str] = None,
) -> dict:
    """
    E: Execute the full pipeline for a single audio pair
        Supports repeated independent runs with metric averaging.
    C: 对单个音频配对执行完整管线
        支持多次独立运行并取指标平均值。

    Steps / 步骤:
    1. Whisper transcription / Whisper 转录 (repeated per run)
    2. Mind map generation / 导图生成 (repeated per run)
    3. Quality evaluation / 质量评估 (run once per generated map)
    4. Metric averaging across runs / 多次运行的指标取平均
    5. Auto-report generation / 自动生成报告
    6. Dual output save / 双轨输出保存
    """
    result = {
        "pair_name": pair_name,
        "audio_path": audio_path,
        "gold_path": gold_path,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "transcription": "",
        "generated_map": None,
        "eval_result": None,
        "error": None,
        "repeat_count": repeat_count,
        "repeat_results": [],
    }

    # E: Timing snapshots collected during pipeline execution
    # C: 管线执行过程中采集的计时快照
    timing_snapshots = []
    # E: Wall-clock evaluation window + anomaly markers (schema §4.1)
    # C: 墙钟评估窗口 + 异常标记（schema §4.1）
    wall_start = datetime.now().isoformat()
    anomalies: list[str] = []
    stt_status = "ok"

    print(f"\n{'=' * 60}")
    print(T(
        f"  处理配对: {pair_name}",
        f"  Processing pair: {pair_name}",
    ))
    if repeat_count > 1:
        print(T(
            f"  重复次数: {repeat_count}",
            f"  Repeat count: {repeat_count}",
        ))
    print(f"{'=' * 60}")

    if mcp_client is None:
        result["error"] = "MCP Client not started / MCP Client 未启动"
        return result

    # E: Load questions for QA evaluation if path provided / C: 如有QA问题集路径则加载
    questions: Optional[list[dict]] = None
    if questions_path and os.path.isfile(questions_path):
        try:
            with open(questions_path, "r", encoding="utf-8") as f:
                qdata = json.load(f)
            questions = qdata.get("questions", [])
            print(T(
                f"  ✓ 问题集已加载: {len(questions)} 个问题",
                f"  ✓ Questions loaded: {len(questions)} questions",
            ))
        except Exception as e:
            print(T(
                f"  ⚠ 问题集加载失败: {e}",
                f"  ⚠ Questions load failed: {e}",
            ))

    # E: Track timing and accumulated results across repeats

    # ============================================================
    # E: Run the full pipeline repeat_count times independently
    # C: 独立执行完整管线 repeat_count 次
    # ============================================================
    all_eval_results: list[dict] = []
    all_generated_maps: list[dict] = []
    all_transcriptions: list[str] = []

    for run_idx in range(repeat_count):
        if repeat_count > 1:
            print(f"\n  --- {T('第', 'Run')} {run_idx + 1}/{repeat_count} ---")

        try:
            # -------------------------------------------------
            # E: Step 1: Whisper transcription
            # C: 步骤 1: Whisper 转录
            # -------------------------------------------------
            print(T(
                f"  [1/3] 转录音频...",
                f"  [1/3] Transcribing audio...",
            ))

            t0 = time_module.perf_counter()
            transcribe_result = await mcp_client.call_tool(
                "transcribe_audio", {"file_path": os.path.abspath(audio_path)}
            )
            t1 = time_module.perf_counter()

            raw_text = ""
            duration_sec = None
            sub_stages = None
            mcp_warning = None
            if isinstance(transcribe_result, dict):
                raw_text = transcribe_result.get("raw_text", "").strip()
                duration_sec = transcribe_result.get("duration_sec")
                sub_stages = transcribe_result.get("timing")
                mcp_warning = transcribe_result.get("warning")

            timing_snapshots.append({
                "stage": "stt", "start": t0, "end": t1, "duration": t1 - t0,
                "sub_stages": sub_stages,
                "audio_duration_sec": duration_sec,
                "stt_chars": len(raw_text),
            })

            # E: Explicit anomaly detection — never silently drop data.
            # C: 显式异常检测 — 绝不静默丢弃数据。
            if mcp_warning:
                print(T(
                    f"  ⚠ 转录服务警告: {mcp_warning}",
                    f"  ⚠ Transcription service warning: {mcp_warning}",
                ))
                anomalies.append(f"mcp_warning ({pair_name} run {run_idx + 1})")
            if duration_sec is not None and duration_sec > 1200:
                print(T(
                    f"  ⚠ 超长音频（{duration_sec:.0f} 秒），转录耗时可能显著增加",
                    f"  ⚠ Long audio ({duration_sec:.0f}s), transcription may be slow",
                ))
                anomalies.append(f"long_audio_{duration_sec:.0f}s ({pair_name})")

            if not raw_text:
                stt_status = "empty"
                reason = "silent_or_unrecognizable" if (duration_sec or 0) > 0 else "empty_transcription"
                anomalies.append(f"{reason} ({pair_name} run {run_idx + 1})")
                print(T(
                    f"  ⚠ 转录为空（{reason}）— 已记录标记，本次 run 不计入指标",
                    f"  ⚠ Empty transcription ({reason}) — flagged, this run is excluded from metrics",
                ))
                if repeat_count > 1 and run_idx < repeat_count - 1:
                    continue  # E: Try next run / C: 尝试下一次运行
                result["stt_status"] = stt_status
                result["anomalies"] = anomalies
                result["error"] = "Empty transcription / 空转录"
                wall_end = datetime.now().isoformat()
                result["timing_log_path"] = _save_timing_log(
                    pair_name, session_dir, timestamp_str, timing_snapshots,
                    wall_start, wall_end, anomalies, stt_status, repeat_count,
                )
                return result

            run_suffix = f"_run{run_idx + 1}" if repeat_count > 1 else ""
            # E: Save transcription / C: 保存转录文本
            trans_path = os.path.join(session_dir, pair_name, f"transcription{run_suffix}.txt")
            _ensure_dir(os.path.dirname(trans_path))
            with open(trans_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
            print(T(
                f"  ✓ 转录已保存 ({len(raw_text)} 字符)",
                f"  ✓ Transcription saved ({len(raw_text)} chars)",
            ))

            # E: Keep first run's transcription for result summary
            # C: 保留第一次运行的转录作为结果摘要
            if run_idx == 0:
                result["transcription"] = raw_text
            all_transcriptions.append(raw_text)

            # -------------------------------------------------
            # E: Step 2: Mind map generation
            # C: 步骤 2: 导图生成
            # -------------------------------------------------
            print(T(
                "  [2/3] 生成导图...",
                "  [2/3] Generating mind map...",
            ))

            chat_history = (
                f"C: 【最高优先级指令】请根据以下语音转录文本生成思维导图。\n"
                f"提取其中所有关键概念，并按层级组织。\n"
                f"E: [Highest Priority Instruction] Please generate a mind map from the speech transcript below.\n"
                f"Extract all key concepts and organize them hierarchically.\n\n"
                f"C: 【转录文本 / Transcript】\n{raw_text}\n---\n"
                f"E: [Transcript Text]\n{raw_text}\n---"
            )

            # E: Prepend gold example context if provided / C: 如果有黄金示例则插入到最前面
            if gold_example_context:
                chat_history = gold_example_context + "\n" + chat_history
                if run_idx == 0:
                    print(T(
                        "  ✓ 黄金示例已注入生成 prompt",
                        "  ✓ Gold example injected into generation prompt",
                    ))

            t0 = time_module.perf_counter()
            gen_result = await mcp_client.call_tool(
                "modify_mind_map_v2",
                {
                    "chat_history": chat_history,
                    "current_map": {"nodes": [], "links": []},
                    "session_ts": f"{timestamp_str}_{pair_name}{run_suffix}",
                },
            )
            t1 = time_module.perf_counter()
            timing_snapshots.append({
                "stage": "map_gen", "start": t0, "end": t1, "duration": t1 - t0,
            })

            if not isinstance(gen_result, dict):
                raise RuntimeError(f"Invalid map generation result / 导图生成返回无效: {type(gen_result)}")

            # E: Save generated map / C: 保存生成导图
            data_type_suffix = f"generated_map{run_suffix}" if repeat_count > 1 else "generated_map"
            _save_dual_output(pair_name, gen_result, data_type_suffix, session_dir, timestamp_str)
            node_count = len(gen_result.get("nodes", []))
            print(T(
                f"  ✓ 导图已生成 ({node_count} 个节点)",
                f"  ✓ Map generated ({node_count} nodes)",
            ))

            all_generated_maps.append(gen_result)

            # -------------------------------------------------
            # E: Step 3: Evaluation
            # C: 步骤 3: 运行评估
            # -------------------------------------------------
            print(T(
                "  [3/3] 运行评估...",
                "  [3/3] Running evaluation...",
            ))

            eval_result = _run_evaluation_for_pair(
                gold_path=gold_path,
                gen_data=gen_result,
                model_name=model_name,
                threshold=threshold,
                essential_concepts=essential_concepts,
                selected_methods=selected_methods,
                transcript_text=raw_text,
                questions=questions,
                timing_snapshots=timing_snapshots,
                human_scores=human_scores,
                key_terms=key_terms,
                ground_truth_text=ground_truth_text,
                multilingual_input=multilingual_input,
            )

            if "error" in eval_result:
                print(T(
                    f"  ✗ 评估失败: {eval_result['error']}",
                    f"  ✗ Evaluation failed: {eval_result['error']}",
                ))
                if repeat_count > 1 and run_idx < repeat_count - 1:
                    continue  # E: Try next run / C: 尝试下一次运行
                result["error"] = eval_result["error"]
                return result

            # E: Save per-run evaluation result / C: 保存每次运行的评估结果
            evalu_data_type = f"eval_result{run_suffix}" if repeat_count > 1 else "eval_result"
            _save_dual_output(pair_name, eval_result, evalu_data_type, session_dir, timestamp_str)

            all_eval_results.append(eval_result)

        except Exception as e:
            print(T(
                f"  ✗ 第 {run_idx + 1} 次运行失败: {e}",
                f"  ✗ Run {run_idx + 1} failed: {e}",
            ))
            import traceback
            traceback.print_exc()
            if repeat_count > 1 and run_idx < repeat_count - 1:
                continue  # E: Try next run / C: 尝试下一次运行
            result["error"] = str(e)
            return result

    # ============================================================
    # E: Post-loop: average metrics and generate report
    # C: 循环后：取指标平均值并生成报告
    # ============================================================
    if not all_eval_results:
        result["error"] = "All runs failed / 所有运行均失败"
        return result

    # E: Average evaluation results across runs / C: 对多次运行的评估结果取平均
    if len(all_eval_results) > 1:
        print(T(
            f"\n  正在对 {len(all_eval_results)} 次运行的指标取平均...",
            f"\n  Averaging metrics across {len(all_eval_results)} runs...",
        ))
    averaged_eval = _average_eval_results(all_eval_results)

    eval_result_with_timing = dict(averaged_eval)
    eval_result_with_timing['timing_snapshots'] = timing_snapshots
    eval_result_with_timing['__repeat_count'] = repeat_count
    eval_result_with_timing['__successful_runs'] = len(all_eval_results)
    # E: Declare metric semantics version so persisted results stay comparable
    #    across evaluation-side changes (empty-mu now scores 0.0, not 1.0).
    # C: 声明指标语义版本，保证持久化结果在评估侧变更后可对比（空对齐现为 0.0 而非 1.0）
    eval_result_with_timing['_semantics'] = 'empty_mu_zero'

    # E: Run stand-alone efficiency evaluation with timing data / C: 用计时数据运行效率评估
    if 'efficiency' in selected_methods:
        if not timing_snapshots:
            # E: No timing data collected — explicit error instead of placeholder zeros
            #    that would render as WER 0.000 ✅PASS.
            # C: 未采集到计时数据 — 显式 error 而非占位零值（零值会被渲染为 WER 0.000 ✅PASS）
            eval_result_with_timing['efficiency'] = {"error": "no timing data / 无计时数据"}
            print(T(
                "  [Efficiency] 无计时快照，跳过效率评估",
                "  [Efficiency] No timing snapshots collected, skipping",
            ))
        else:
            try:
                from evaluation.efficiency.eval_efficiency import evaluate_efficiency, EfficiencyStandards
                st = EfficiencyStandards()
                custom_stds = os.path.join(os.getcwd(), 'evaluation', 'data', 'standards', 'custom_standards.json')
                if os.path.isfile(custom_stds):
                    st = EfficiencyStandards(custom_stds)
                eff_result = evaluate_efficiency(
                    timing_snapshots=timing_snapshots,
                    stt_text=result.get('transcription', '') or None,
                    ground_truth_text=ground_truth_text or None,
                    key_terms=key_terms,
                    standards=st,
                    num_repetitions=repeat_count,
                )
                eval_result_with_timing['efficiency'] = eff_result.to_dict()
                print(f"    ✓ {T('效率评估完成', 'Efficiency evaluation complete')}: "
                      f"Total P50={eff_result.t_total_p50:.2f}s")
            except Exception as e:
                print(f"    [Efficiency] {T('自动效率评估失败', 'Auto-eval failed')}: {e}")

    # E: Save final evaluation result / C: 保存最终评估结果
    _save_dual_output(pair_name, eval_result_with_timing, "eval_result", session_dir, timestamp_str)

    # E: Persist the timing log (wall window + stages + anomalies), schema §4.1
    # C: 落盘计时日志（墙钟窗口 + 各阶段 + 异常标记），schema §4.1
    wall_end = datetime.now().isoformat()
    result["timing_log_path"] = _save_timing_log(
        pair_name, session_dir, timestamp_str, timing_snapshots,
        wall_start, wall_end, anomalies, stt_status, repeat_count,
    )
    result["anomalies"] = anomalies
    result["stt_status"] = stt_status

    result["eval_result"] = eval_result_with_timing
    result["timing_snapshots"] = timing_snapshots
    result["generated_map"] = all_generated_maps[0] if all_generated_maps else None
    result["repeat_results"] = all_eval_results
    result["success"] = True

    # ============================================================
    # E: Auto-generate per-pair Markdown report
    # C: 自动生成每配对的 Markdown 报告
    # ============================================================
    try:
        from evaluation.core.data_loader import DataLoader
        gold_map = DataLoader.from_map_file(gold_path) if gold_path else None
        gen_map = DataLoader.from_flat_dict(result["generated_map"]) if result["generated_map"] else None

        config_info = {
            'pipeline': f"embedding={model_name}, τ={threshold}",
            'audio': os.path.basename(audio_path),
            'methods': ', '.join(selected_methods),
            'repeat_count': str(repeat_count),
            'successful_runs': str(len(all_eval_results)),
        }

        renderer = MarkdownReportRenderer(embedding_model=model_name, threshold=threshold)
        report = renderer.render(
            gold_map, gen_map, averaged_eval,
            inclusion_list=selected_methods,
            config_info=config_info,
        )

        # E: Save report to session dir / C: 保存报告到会话目录
        pair_report_dir = os.path.join(session_dir, pair_name)
        _ensure_dir(pair_report_dir)
        report_path_session = os.path.join(pair_report_dir, "eval_report.md")
        with open(report_path_session, "w", encoding="utf-8") as f:
            f.write(report)
        print(T(
            f"  ✓ 配对报告已保存: {report_path_session}",
            f"  ✓ Per-pair report saved: {report_path_session}",
        ))

        # E: Also save to evaluation/ root / C: 同时保存到 evaluation/ 根目录
        report_path_root = os.path.join(
            os.getcwd(), "evaluation",
            f"eval_report_{pair_name}_{timestamp_str}.md"
        )
        with open(report_path_root, "w", encoding="utf-8") as f:
            f.write(report)
        print(T(
            f"  ✓ 报告已保存: {report_path_root}",
            f"  ✓ Report saved: {report_path_root}",
        ))

    except Exception as report_err:
        print(T(
            f"  ⚠ 报告生成失败: {report_err}",
            f"  ⚠ Report generation failed: {report_err}",
        ))

    # E: Print summary / C: 打印摘要
    label_data = averaged_eval.get('label', {})
    hier_data = averaged_eval.get('hierarchy', {})
    nf1 = label_data.get('node_f1', 0) if isinstance(label_data, dict) else 0
    ef1 = hier_data.get('edge_f1', 0) if isinstance(hier_data, dict) else 0
    repeat_info = T(
        f"，已平均 {len(all_eval_results)} 次运行",
        f", averaged over {len(all_eval_results)} runs",
    ) if repeat_count > 1 else ""
    print(T(
        f"  ✓ 评估完成: Node-F1={nf1:.4f}, Edge-F1={ef1:.4f}{repeat_info}",
        f"  ✓ Evaluation complete: Node-F1={nf1:.4f}, Edge-F1={ef1:.4f}{repeat_info}",
    ))

    return result


# ============================================================
# E: Batch Evaluator — manages complete batch evaluation lifecycle
# C: 批量评估器 — 管理批量评估的完整生命周期
# ============================================================
class BatchEvaluator:
    """
    E: Batch Evaluator — manages the complete batch evaluation lifecycle
    C: 批量评估器 — 管理批量评估的完整生命周期

    Pipeline / 管线:
        1. Discover audio-gold pairs / 发现音频-金标准配对
        2. For each pair: Whisper → Map Gen → Evaluation / 对每对：转录→生成→评估
        3. Generate summary report / 生成汇总报告
        4. Dual output save / 双轨保存
    """

    def __init__(
        self,
        audio_dir: str = "evaluation/data/audio",
        gold_dir: str = "evaluation/data/gold",
        session_base: str = "evaluation/data/sessions",
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        threshold: float = 0.70,
        selected_methods: Optional[list[str]] = None,
        gold_example_transcript: Optional[str] = None,
        gold_example_json: Optional[str] = None,
        repeat_count: int = 1,
    ):
        self.audio_dir = audio_dir
        self.gold_dir = gold_dir
        self.session_base = session_base
        self.model_name = model_name
        self.threshold = threshold
        self.selected_methods = selected_methods or ['label', 'hierarchy', 'efficiency']
        self.gold_example_transcript = gold_example_transcript
        self.gold_example_json = gold_example_json
        self.repeat_count = repeat_count

        self.mcp_client: Optional[MCPMindMapClient] = None
        self.session_ts: str = ""
        self.session_dir: str = ""
        self.all_results: list[dict] = []
        self.pairs: list[tuple[str, str, str]] = []

    async def start_mcp(self):
        """E: Start MCP Server subprocess and connect MCP Client
        C: 启动 MCP Server 子进程并连接 MCP Client"""
        print(T(
            "[Batch] 正在启动 MCP Client...",
            "[Batch] Starting MCP Client...",
        ))

        server_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server.py"
        )
        server_script = os.path.abspath(server_script)

        self.mcp_client = MCPMindMapClient(server_script)
        try:
            await self.mcp_client.start()
            print(T(
                "[Batch] MCP Client 启动完成",
                "[Batch] MCP Client started",
            ))
        except Exception as e:
            print(T(
                f"[Batch] MCP Client 启动失败: {e}",
                f"[Batch] MCP Client start failed: {e}",
            ))
            self.mcp_client = None
            raise

    def discover(self) -> list[tuple[str, str, str]]:
        """E: Discover all audio-gold pairs / C: 发现所有音频-金标准配对"""
        self.pairs = discover_pairs(self.audio_dir, self.gold_dir)

        if self.pairs:
            print(T(
                f"[Batch] 发现 {len(self.pairs)} 个配对",
                f"[Batch] Discovered {len(self.pairs)} pairs",
            ))
            for name, apath, gpath in self.pairs:
                print(f"  - {name}")
        else:
            print(T(
                "[Batch] 未发现任何配对",
                "[Batch] No pairs discovered",
            ))

        return self.pairs

    async def run_all(self):
        """E: Iterate all pairs and execute full batch evaluation
        C: 遍历所有配对，执行完整批量评估"""
        # E: Create session directory / C: 创建会话目录
        self.session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(os.getcwd(), self.session_base, self.session_ts)
        _ensure_dir(self.session_dir)

        print("=" * 60)
        print(T(
            "  批量评估开始",
            "  Batch Evaluation Started",
        ))
        print(f"  Session: {self.session_ts}")
        print(f"  Session Dir: {self.session_dir}")
        print(T(
            f"  模型: {self.model_name}",
            f"  Model: {self.model_name}",
        ))
        print(T(
            f"  阈值: {self.threshold}",
            f"  Threshold: {self.threshold}",
        ))
        print(T(
            f"  方法: {', '.join(self.selected_methods)}",
            f"  Methods: {', '.join(self.selected_methods)}",
        ))
        if self.repeat_count > 1:
            print(T(
                f"  重复次数: {self.repeat_count}",
                f"  Repeat Count: {self.repeat_count}",
            ))
        print("=" * 60)

        # E: Discover pairs / C: 发现配对
        self.discover()

        if not self.pairs:
            print(T(
                "[Batch] 没有可处理的配对，退出",
                "[Batch] No pairs to process, exiting",
            ))
            return

        # E: Start MCP / C: 启动 MCP
        await self.start_mcp()

        # E: Format gold example context for batch mode / C: 批量模式下格式化黄金示例
        gold_example_context = None
        if self.gold_example_transcript and self.gold_example_json:
            gold_example_context = _format_gold_example(
                self.gold_example_transcript, self.gold_example_json
            )
            if gold_example_context:
                print(T(
                    "  ✓ 黄金示例将注入批量生成 prompt",
                    "  ✓ Gold example will be injected into batch generation prompts",
                ))

        # E: Load essential concepts for each pair / C: 加载每个配对的核心概念
        concepts_base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "evaluation", "data", "concepts",
        )
        questions_base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "evaluation", "data", "questions",
        )

        # E: Load ALL questionnaire files (multi-questionnaire input; batch mode
        #    does not prompt — reuse every saved non-example questionnaire).
        # C: 批量模式不交互评分 — 读取全部已保存的非示例问卷文件（多份一起输入）。
        human_scores = None
        hs_files = sorted(glob.glob(os.path.join("evaluation", "data", "human_scores", "*.json")))
        hs_files = [f for f in hs_files if 'example' not in os.path.basename(f)]
        if hs_files:
            from evaluation.human_correlation.interactive_scorer import load_questionnaires
            try:
                human_scores = load_questionnaires(hs_files)
                print(T(
                    f"[Batch] ✓ 已加载 {len(human_scores)} 条问卷评分",
                    f"[Batch] ✓ Loaded {len(human_scores)} questionnaire samples",
                ))
            except Exception as e:
                print(T(
                    f"[Batch] ⚠ 问卷加载失败: {e}",
                    f"[Batch] ⚠ Questionnaire load failed: {e}",
                ))
                human_scores = None

        # E: Load §4/§5 shared inputs (key terms, multilingual results, reference
        #    transcript) once — same files apply to every pair in this batch.
        # C: 一次性加载 §4/§5 共享输入（关键术语、多语言结果、标准转录文本），
        #    同一批次的每个配对共用。
        batch_key_terms: Optional[list[str]] = None
        kt_files = sorted(glob.glob(os.path.join("evaluation", "data", "timing", "*key_terms*.json")))
        kt_files = [f for f in kt_files if 'example' not in os.path.basename(f)]
        if kt_files:
            try:
                with open(kt_files[-1], "r", encoding="utf-8") as f:
                    kt_data = json.load(f)
                batch_key_terms = kt_data.get("key_terms", kt_data) if isinstance(kt_data, dict) else kt_data
                print(f"[Batch] ✓ {T('已加载关键术语', 'Key terms loaded')}: {len(batch_key_terms)} terms")
            except Exception as e:
                print(f"[Batch] ⚠ {T('关键术语加载失败', 'Key terms load failed')}: {e}")

        batch_multilingual_input = None
        ml_files = sorted(glob.glob(os.path.join("evaluation", "data", "multilingual", "*.json")))
        ml_files = [f for f in ml_files if 'example' not in os.path.basename(f)]
        if ml_files:
            try:
                with open(ml_files[-1], "r", encoding="utf-8") as f:
                    mdata = json.load(f)
                batch_multilingual_input = mdata.get("results", mdata) if isinstance(mdata, dict) else mdata
                print(f"[Batch] ✓ {T('已加载多语言测试数据', 'Multilingual test data loaded')}")
            except Exception as e:
                print(f"[Batch] ⚠ {T('多语言数据加载失败', 'Multilingual data load failed')}: {e}")

        batch_ground_truth = None
        gt_files = sorted(glob.glob(os.path.join("evaluation", "data", "timing", "*.txt")))
        gt_files = [f for f in gt_files if 'example' not in os.path.basename(f)]
        if gt_files:
            try:
                with open(gt_files[-1], "r", encoding="utf-8") as f:
                    batch_ground_truth = f.read()
                print(f"[Batch] ✓ {T('已加载标准转录文本', 'Reference transcript loaded')}: "
                      f"{os.path.basename(gt_files[-1])}")
            except Exception as e:
                print(f"[Batch] ⚠ {T('标准转录文本加载失败', 'Reference transcript load failed')}: {e}")

        # E: Process each pair / C: 遍历处理
        self.all_results = []
        for pair_name, audio_path, gold_path in self.pairs:
            # E: Try to load paired essential concepts / C: 尝试加载配对的核心概念集合
            concepts_path = os.path.join(concepts_base_dir, f"{pair_name}_concepts.json")
            batch_essential_concepts = None
            if os.path.isfile(concepts_path):
                try:
                    with open(concepts_path, "r", encoding="utf-8") as f:
                        concepts_data = json.load(f)
                    loaded = concepts_data.get("concepts", [])
                    if loaded:
                        batch_essential_concepts = loaded
                        print(T(
                            f"  ✓ 已加载核心概念: {len(loaded)} 项",
                            f"  ✓ Loaded essential concepts: {len(loaded)} items",
                        ))
                except Exception as e:
                    print(T(
                        f"  ⚠ 概念文件加载失败: {e}",
                        f"  ⚠ Concepts file load failed: {e}",
                    ))

            # E: Try to load paired questions / C: 尝试加载配对的问题集
            qpath = os.path.join(questions_base_dir, f"{pair_name}_questions.json")
            questions_path_in_batch = qpath if os.path.isfile(qpath) else None

            result = await _run_single_pipeline(
                pair_name=pair_name,
                audio_path=audio_path,
                gold_path=gold_path,
                mcp_client=self.mcp_client,
                session_dir=self.session_dir,
                timestamp_str=self.session_ts,
                selected_methods=self.selected_methods,
                model_name=self.model_name,
                threshold=self.threshold,
                essential_concepts=batch_essential_concepts,
                gold_example_context=gold_example_context,
                questions_path=questions_path_in_batch,
                repeat_count=self.repeat_count,
                human_scores=human_scores,
                key_terms=batch_key_terms,
                multilingual_input=batch_multilingual_input,
                ground_truth_text=batch_ground_truth,
            )
            self.all_results.append(result)

        # E: Close MCP / C: 关闭 MCP
        await self.close()

        # E: Generate summary report / C: 生成汇总报告
        report = self.generate_summary_report()
        report_path = os.path.join(self.session_dir, "summary_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(T(
            f"\n✓ 汇总报告已保存: {report_path}",
            f"\n✓ Summary report saved: {report_path}",
        ))

        # E: Print terminal summary / C: 打印终端摘要
        self._print_terminal_summary()

    def generate_summary_report(self) -> str:
        """E: Generate summary Markdown report for all pairs
        C: 生成包含所有配对的汇总 Markdown 报告"""
        if not self.all_results:
            return "# Batch Evaluation Summary Report\n\n*No results to report*"

        lines = []
        lines.append("# Batch Evaluation Summary Report")
        lines.append("")
        lines.append(f"**Batch Timestamp / 批次时间**: {self.session_ts}")
        lines.append(f"**Total Pairs / 总配对数**: {len(self.all_results)}")
        lines.append(f"**Embedding Model**: {self.model_name}")
        lines.append(f"**Threshold τ**: {self.threshold}")
        lines.append(f"**Methods / 评估方法**: {', '.join(self.selected_methods)}")
        lines.append("")

        successful = [r for r in self.all_results if r.get("success")]

        # E: Per-pair results table / C: 每对结果表格
        lines.append("---")
        lines.append("## Per-Pair Results / 每对结果")
        lines.append("")

        # E: Collect all metric keys from results / C: 从结果中收集所有指标键
        all_metric_keys = set()
        for r in successful:
            er = r.get("eval_result", {})
            for dim_key, dim_data in er.items():
                if isinstance(dim_data, dict):
                    for metric_key, metric_val in dim_data.items():
                        if isinstance(metric_val, (int, float)):
                            all_metric_keys.add(f"{dim_key}.{metric_key}")

        # E: Build table header / C: 构建表头
        header_cols = ["Pair / 配对"]
        for mk in sorted(all_metric_keys):
            short_name = mk.split('.')[-1]
            header_cols.append(short_name)
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("|" + "---|" * len(header_cols))

        for r in self.all_results:
            pair_name = r.get("pair_name", "?")
            er = r.get("eval_result", {})
            if r.get("success") and er:
                row = [pair_name]
                for mk in sorted(all_metric_keys):
                    dim_key, metric_key = mk.split('.', 1)
                    dim_data = er.get(dim_key, {})
                    if isinstance(dim_data, dict):
                        val = dim_data.get(metric_key)
                        if val is not None and isinstance(val, (int, float)):
                            row.append(f"{val:.3f}")
                        else:
                            row.append("N/A")
                    else:
                        row.append("N/A")
                lines.append("| " + " | ".join(row) + " |")
            else:
                # E: Keep the first column as the pure pair name and escape '|'
                #    in the error text, so the table structure stays parseable.
                # C: 第一列保持纯配对名，错误文本中的 '|' 做转义，保证表格结构可解析。
                err = (r.get("error") or "Unknown error / 未知错误")[:60].replace('|', '\\|')
                row = [pair_name]
                if len(header_cols) > 1:
                    row.append(f"FAIL: {err}")
                    row += ["-"] * (len(header_cols) - 2)
                else:
                    row.append(f"FAIL: {err}")
                lines.append("| " + " | ".join(row) + " |")

        lines.append("")

        # E: Summary statistics / C: 汇总统计
        if successful:
            lines.append("---")
            lines.append("## Summary Statistics / 汇总统计")
            lines.append("")

            lines.append("| Metric / 指标 | Mean / 均值 | Std / 标准差 | Min / 最小 | Max / 最大 |")
            lines.append("|---|---|---|---|---|")

            for mk in sorted(all_metric_keys):
                dim_key, metric_key = mk.split('.', 1)
                values = []
                for r in successful:
                    er = r.get("eval_result", {})
                    dim_data = er.get(dim_key, {})
                    if isinstance(dim_data, dict):
                        v = dim_data.get(metric_key)
                        if v is not None and isinstance(v, (int, float)):
                            values.append(v)
                if values:
                    avg = _mean(values)
                    std = _stdev(values)
                    min_v = min(values)
                    max_v = max(values)
                    lines.append(f"| {mk} | {avg:.4f} | {std:.4f} | {min_v:.4f} | {max_v:.4f} |")

            lines.append("")

            # E: Best / Worst cases / C: 最优与最差案例
            lines.append("---")
            lines.append("## Best / Worst Cases / 最优与最差案例")
            lines.append("")

            for mk in sorted(all_metric_keys):
                scored = []
                for r in successful:
                    er = r.get("eval_result", {})
                    dim_key, metric_key = mk.split('.', 1)
                    dim_data = er.get(dim_key, {})
                    if isinstance(dim_data, dict):
                        v = dim_data.get(metric_key)
                        if v is not None and isinstance(v, (int, float)):
                            scored.append((v, r["pair_name"]))
                if scored:
                    scored.sort(key=lambda x: x[0], reverse=True)
                    best_val, best_name = scored[0]
                    worst_val, worst_name = scored[-1]
                    lines.append(f"- **{mk}**")
                    lines.append(f"  - Best / 最优: {best_name} ({best_val:.4f})")
                    lines.append(f"  - Worst / 最差: {worst_name} ({worst_val:.4f})")

        # E: Failed pairs / C: 失败案例
        failed = [r for r in self.all_results if not r.get("success")]
        if failed:
            lines.append("")
            lines.append("---")
            lines.append("## Failed Pairs / 失败配对")
            lines.append("")
            for r in failed:
                lines.append(f"- {r['pair_name']}: {r.get('error', 'Unknown error / 未知错误')}")

        # E: Timing log summary — per-pair latency + anomalies + log reference
        # C: 计时日志摘要 — 每配对延迟 + 异常标记 + 计时日志引用
        timing_rows = []
        for r in self.all_results:
            if not r.get("success"):
                continue
            er = r.get("eval_result", {})
            eff = er.get("efficiency", {}) if isinstance(er, dict) else {}
            if not isinstance(eff, dict) or not eff:
                continue
            staged = eff.get("staged_timing", {}) if isinstance(eff.get("staged_timing"), dict) else {}
            timing_rows.append({
                "name": r.get("pair_name", "?"),
                "stt_p50": staged.get("stt", {}).get("p50"),
                "gen_p50": staged.get("map_gen", {}).get("p50"),
                "total": eff.get("t_total_p50"),
                "anomalies": eff.get("anomalies") or [],
                "log": r.get("timing_log_path", ""),
            })
        if timing_rows:
            lines.append("")
            lines.append("---")
            lines.append("## Timing Log Summary / 计时日志摘要")
            lines.append("")
            lines.append("| Pair / 配对 | STT P50 (s) | Map Gen P50 (s) | Total P50 (s) | Anomalies / 异常 |")
            lines.append("|---|---|---|---|---|")

            def _fmt_timing(v):
                return f"{v:.2f}" if isinstance(v, (int, float)) else "—"

            for tr in timing_rows:
                lines.append(
                    f"| {tr['name']} | {_fmt_timing(tr['stt_p50'])} | {_fmt_timing(tr['gen_p50'])} "
                    f"| {_fmt_timing(tr['total'])} | {', '.join(tr['anomalies']) if tr['anomalies'] else '—'} |"
                )
            lines.append("")
            lines.append("**Timing logs / 计时日志**:")
            for tr in timing_rows:
                if tr["log"]:
                    lines.append(f"- `{tr['name']}`: `{tr['log']}`")

        lines.append("")
        lines.append("---")
        lines.append(f"*Report Generated / 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def _print_terminal_summary(self):
        """E: Print batch evaluation summary to terminal
        C: 在终端打印批量评估摘要"""
        successful = [r for r in self.all_results if r.get("success")]
        failed = [r for r in self.all_results if not r.get("success")]

        print(f"\n{'=' * 60}")
        print(T(
            "  批量评估完成",
            "  Batch Evaluation Complete",
        ))
        print("=" * 60)
        print(T(
            f"  总配对数: {len(self.all_results)}",
            f"  Total pairs: {len(self.all_results)}",
        ))
        print(T(
            f"  成功: {len(successful)}",
            f"  Succeeded: {len(successful)}",
        ))
        print(T(
            f"  失败: {len(failed)}",
            f"  Failed: {len(failed)}",
        ))
        print(T(
            f"  会话目录: {self.session_dir}",
            f"  Session dir: {self.session_dir}",
        ))

        if successful:
            nf1_values = []
            for r in successful:
                er = r.get("eval_result", {})
                if isinstance(er, dict):
                    label_data = er.get('label', {})
                    if isinstance(label_data, dict):
                        v = label_data.get('node_f1')
                        if v is not None:
                            nf1_values.append(v)
            if nf1_values:
                print(T(
                    f"  Node-F1 均值: {_mean(nf1_values):.4f}",
                    f"  Node-F1 Mean: {_mean(nf1_values):.4f}",
                ))

    async def close(self):
        """E: Close MCP Client / C: 关闭 MCP Client"""
        if self.mcp_client is not None:
            try:
                await self.mcp_client.close()
                print(T(
                    "[Batch] MCP Client 已关闭",
                    "[Batch] MCP Client closed",
                ))
            except Exception as e:
                print(T(
                    f"[Batch] 关闭异常: {e}",
                    f"[Batch] Close error: {e}",
                ))
            finally:
                self.mcp_client = None


# ============================================================
# E: Example demo mode — runs full pipeline with built-in example data
# C: 示例演示模式 — 使用内置示例数据走通全流程
# ============================================================
def _run_example_demo(auto_install: bool = False, ignore_missing: bool = False):
    """
    E: Example demo mode — runs full pipeline with built-in example data, no user input
    C: 示例演示模式 — 使用内置示例数据走通全流程，无需用户输入

    Steps / 自动执行步骤:
    1. Load gold map, essential concepts, question sets / 加载金标准导图、核心概念、问题集
    2. Perturb gold node labels to simulate generated map / 对金标准节点 label 做轻微扰动
    3. Execute label / hierarchy / qa / efficiency / multilingual / human_corr evaluation
       / 完整执行所有维度评估
    4. Generate report with **example** markers / 生成带 **example** 标记的报告
    """
    import json
    import copy
    import random

    # E: Check dependencies before proceeding
    # C: 依赖预检
    all_dims = ['label', 'hierarchy', 'qa', 'efficiency', 'multilingual', 'human_corr']
    if not check_dependencies(all_dims, auto_install=auto_install, ignore_missing=ignore_missing):
        print(T(
            "\n  [!] 请安装缺失的依赖后重试。",
            "\n  [!] Please install missing dependencies and try again.",
        ))
        return

    print("=" * 60)
    print(T(
        "  §0 示例演示模式",
        "  §0 Example Demo Mode",
    ))
    print("=" * 60)
    print(T(
        "  使用内置示例数据自动执行完整评估流程",
        "  Running full evaluation with built-in example data",
    ))
    print()

    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    threshold = 0.70

    # E: Step 1 — Load all example data / C: 加载所有示例数据
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(base_dir), "evaluation", "data")

    gold_path = os.path.join(data_dir, "gold", "gold_example.json")
    gold_map = DataLoader.from_map_file(gold_path)
    if gold_map is None:
        print(T(
            "  ✗ 金标准加载失败",
            "  ✗ Gold load failed",
        ))
        return
    print(T(
        f"  ✓ 金标准加载成功: {gold_map.node_count} 个节点",
        f"  ✓ Gold loaded: {gold_map.node_count} nodes",
    ))

    concepts_path = os.path.join(data_dir, "concepts", "example_essential_concepts.json")
    essential_concepts = None
    if os.path.isfile(concepts_path):
        with open(concepts_path) as f:
            concepts_data = json.load(f)
        essential_concepts = concepts_data.get("concepts", [])
        print(T(
            f"  ✓ 核心概念加载成功: {len(essential_concepts)} 项",
            f"  ✓ Concepts loaded: {len(essential_concepts)} items",
        ))

    print(T(
        "  正在生成模拟导图...",
        "  Generating simulated map...",
    ))
    gen_dict = _generate_example_map(gold_map)
    gen_map = DataLoader.from_flat_dict(gen_dict)
    print(T(
        f"  ✓ 模拟导图已生成: {gen_map.node_count} 个节点",
        f"  ✓ Simulated map generated: {gen_map.node_count} nodes",
    ))

    aligner = HungarianAligner(model_name=model_name, threshold=threshold)

    # E: Step 2 — Execute all dimension evaluations / C: 执行所有维度评估
    results = {}
    selected_dims = ["label", "hierarchy", "qa", "efficiency", "multilingual", "human_corr"]
    progress = ProgressTracker(total=len(selected_dims))

    # E: §1 Label Quality / C: 节点标签质量
    progress.start(T("节点标签质量", "Node Label Quality"))
    try:
        from evaluation.label.eval_label import evaluate_label_quality
        label_result = evaluate_label_quality(gold_map, gen_map, aligner, essential_concepts)
        results["label"] = label_result.to_dict()
        print(f"    Node-F1: {label_result.node_f1:.4f}")
        progress.complete(T("节点标签质量", "Node Label Quality"))
    except Exception as e:
        print(T(f"    [错误] {e}", f"    [Error] {e}"))
        progress.complete(T("节点标签质量", "Node Label Quality"), status=T("失败", "Failed"))

    # E: §2 Hierarchy / C: 层级结构
    progress.start(T("层级结构正确率", "Hierarchy Accuracy"))
    try:
        from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
        alignment = aligner.align(gold_map.nodes, gen_map.nodes)
        hier_result = evaluate_hierarchy_quality(gold_map, gen_map, alignment)
        results["hierarchy"] = hier_result.to_dict()
        print(f"    Edge-F1: {hier_result.edge_f1:.4f}")
        progress.complete(T("层级结构正确率", "Hierarchy Accuracy"))
    except Exception as e:
        print(T(f"    [错误] {e}", f"    [Error] {e}"))
        progress.complete(T("层级结构正确率", "Hierarchy Accuracy"), status=T("失败", "Failed"))

    # E: §3 QA / C: 下游 QA
    progress.start(T("下游 QA 测试", "Downstream QA"))
    try:
        questions_path = os.path.join(data_dir, "questions", "example_questions.json")
        questions = []
        if os.path.isfile(questions_path):
            with open(questions_path) as f:
                qdata = json.load(f)
            questions = qdata.get("questions", [])
        from evaluation.qa.eval_qa import QAEvaluator
        qa_eval = QAEvaluator()
        qa_result = qa_eval.evaluate("", gen_map.nodes, questions)
        results["qa"] = qa_result.to_dict()
        print(f"    QA Score: {qa_result.qa_score:.4f}")
        progress.complete(T("下游 QA 测试", "Downstream QA"))
    except Exception as e:
        print(T(f"    [错误] {e}", f"    [Error] {e}"))
        progress.complete(T("下游 QA 测试", "Downstream QA"), status=T("失败", "Failed"))

    # E: §4 Efficiency / C: 效率与 STT
    progress.start(T("效率与 STT 保真度", "Efficiency & STT"))
    try:
        from evaluation.efficiency.eval_efficiency import evaluate_efficiency
        timing_logs = None
        key_terms = None
        timing_path = os.path.join(data_dir, "timing", "example_timing_logs.json")
        terms_path = os.path.join(data_dir, "timing", "example_key_terms.json")
        if os.path.isfile(timing_path):
            with open(timing_path) as f:
                td = json.load(f)
            timing_logs = []
            for run in td.get("runs", []):
                for stage in run.get("stages", []):
                    timing_logs.append({
                        "stage": stage["stage"],
                        "start": stage["start"],
                        "end": stage["end"],
                        "duration": stage.get("duration", stage["end"] - stage["start"]),
                    })
        if os.path.isfile(terms_path):
            with open(terms_path) as f:
                kd = json.load(f)
            key_terms = kd.get("key_terms", [])
        eff_result = evaluate_efficiency(
            timing_snapshots=timing_logs,
            stt_text="This is an example transcription for STT evaluation demo",
            ground_truth_text="This is an example transcription for STT evaluation demo",
            key_terms=key_terms,
        )
        results["efficiency"] = eff_result.to_dict()
        wer_txt = f"{eff_result.wer:.4f}" if eff_result.wer is not None else "N/A"
        print(f"    WER: {wer_txt}")
        progress.complete(T("效率与 STT 保真度", "Efficiency & STT"))
    except Exception as e:
        print(T(f"    [错误] {e}", f"    [Error] {e}"))
        progress.complete(T("效率与 STT 保真度", "Efficiency & STT"), status=T("失败", "Failed"))

    # E: §5 Multilingual / C: 多语言与鲁棒性
    progress.start(T("多语言与鲁棒性", "Multilingual & Robustness"))
    try:
        from evaluation.multilingual.eval_multilingual import evaluate_multilingual
        cn_data = en_data = mixed_data = noise_data = None
        def _load_results(fp):
            if os.path.isfile(fp):
                with open(fp) as f:
                    d = json.load(f)
                return d.get("results", [])
            return None
        m_dir = os.path.join(data_dir, "multilingual")
        cn_data = _load_results(os.path.join(m_dir, "example_cn_results.json"))
        en_data = _load_results(os.path.join(m_dir, "example_en_results.json"))
        mixed_data = _load_results(os.path.join(m_dir, "example_mixed_results.json"))
        noise_data = _load_results(os.path.join(m_dir, "example_noise_results.json"))

        cn_avg = {"entity_recall": 0, "label_sim": 0, "pc_f1": 0} if cn_data else None
        if cn_data:
            cn_avg = {k: sum(d[k] for d in cn_data)/len(cn_data) for k in ["entity_recall","label_sim","pc_f1"]}
        en_avg = {"entity_recall": 0, "label_sim": 0, "pc_f1": 0} if en_data else None
        if en_data:
            en_avg = {k: sum(d[k] for d in en_data)/len(en_data) for k in ["entity_recall","label_sim","pc_f1"]}
        mx_avg = {"entity_recall": 0, "label_sim": 0, "pc_f1": 0} if mixed_data else None
        if mixed_data:
            # E: Denominator must be the sample count len(mixed_data) — len(mx_avg)
            #    would be the dict key count (3) and silently skew the averages.
            # C: 分母必须为样本数 len(mixed_data) — len(mx_avg) 是字典键数（恒为 3），
            #    会静默扭曲平均值。
            mx_avg = {k: sum(d[k] for d in mixed_data)/len(mixed_data) for k in ["entity_recall","label_sim","pc_f1"]}

        multi_result = evaluate_multilingual(
            cn_results=cn_avg, en_results=en_avg, mixed_results=mx_avg,
            noise_test_results=noise_data,
        )
        results["multilingual"] = multi_result.to_dict()
        print(f"    max_delta_recall: {multi_result.max_delta_recall:.4f}")
        progress.complete(T("多语言与鲁棒性", "Multilingual & Robustness"))
    except Exception as e:
        print(T(f"    [错误] {e}", f"    [Error] {e}"))
        progress.complete(T("多语言与鲁棒性", "Multilingual & Robustness"), status=T("失败", "Failed"))

    # E: §6 Human Correlation / C: 人工评估
    progress.start(T("人工评估相关性", "Human Evaluation Correlation"))
    try:
        human_path = os.path.join(data_dir, "human_scores", "example_human_scores.json")
        human_scores_list = None
        if os.path.isfile(human_path):
            with open(human_path) as f:
                hdata = json.load(f)
            human_scores_list = hdata.get("samples", [])

        from evaluation.human_correlation.eval_human_correlation import evaluate_human_correlation
        # NOTE: Per-sample automated scores not available yet;
        # passing None avoids creating constant arrays from aggregate
        # values that would trigger ConstantInputWarning.
        auto_scores_list = None

        hc_result = evaluate_human_correlation(automated_scores=auto_scores_list, human_scores=human_scores_list)
        results["human_corr"] = hc_result.to_dict()
        print(f"    Pearson r: {hc_result.node_f1_readability_r:.4f}")
        progress.complete(T("人工评估相关性", "Human Evaluation Correlation"))
    except Exception as e:
        print(T(f"    [错误] {e}", f"    [Error] {e}"))
        progress.complete(T("人工评估相关性", "Human Evaluation Correlation"), status=T("失败", "Failed"))

    # E: Step 3 — Generate report with **example** markers / C: 生成带标记的报告
    print()
    print("=" * 60)
    print(T(
        "  生成评估报告",
        "  Generating Evaluation Report",
    ))
    print("=" * 60)

    config_info = {"pipeline": f"embedding={model_name}, threshold={threshold} (Example Demo / 示例演示)"}
    renderer = MarkdownReportRenderer(embedding_model=model_name, threshold=threshold)
    report = renderer.render(
        gold_map, gen_map, results,
        inclusion_list=selected_dims,
        config_info=config_info,
        example_mode=True,
    )

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join("evaluation", f"eval_report_example_{timestamp_str}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  ✓ {T('报告已保存', 'Report saved')}: {report_path}")

    print()
    print("=" * 60)
    print(T(
        "  示例演示已完成",
        "  Example Demo Complete",
    ))
    print(T(
        f"  报告文件: {report_path}",
        f"  Report file: {report_path}",
    ))
    print("=" * 60)
    print()
    print(T("  说明:", "  Notes:"))
    print(T(
        "  1. 演示使用内置示例数据，结果仅供参考",
        "  1. Demo uses built-in example data, results are for reference only",
    ))
    print(T(
        "  2. 报告中所有数值均标记为 **example**，以区别于正式评估",
        "  2. All values in the report are marked **example** to distinguish from formal evaluations",
    ))
    print(T(
        "  3. 上传真实数据后，通过交互式或批量模式获得正式评估结果",
        "  3. Upload real data for formal evaluations via interactive or batch mode",
    ))
    print()


def _generate_example_map(gold_map) -> dict:
    """
    E: Slightly perturb the gold standard map to generate a simulated map
    C: 对金标准导图做轻微扰动，生成模拟的生成导图

    Perturbation strategy / 扰动策略:
    - 30% chance to replace Chinese characters with nearby ones
    - 20% chance to delete or add a word
    - Preserve node structure and hierarchy
    """
    random.seed(42)
    nodes = []
    for n in gold_map.nodes:
        new_node = copy.deepcopy(n)
        label = new_node.get("label", "")
        if label:
            chars = []
            for ch in label:
                if "\u4e00" <= ch <= "\u9fff" and random.random() < 0.3:
                    offset = random.choice([-1, 1, -2, 2])
                    new_ch = chr(ord(ch) + offset)
                    if "\u4e00" <= new_ch <= "\u9fff":
                        chars.append(new_ch)
                    else:
                        chars.append(ch)
                else:
                    chars.append(ch)
            new_label = "".join(chars)
            if new_label != label and random.random() < 0.5:
                new_label = new_label + " " if random.random() < 0.5 else new_label
            new_node["label"] = new_label
        nodes.append(new_node)

    links = []
    for n in nodes:
        pid = n.get("parent_id")
        if pid:
            links.append({"source": pid, "target": n["id"]})

    tree_nodes = _build_nested_tree(nodes)
    return {"nodes": nodes, "links": links, "tree": tree_nodes}


def _build_nested_tree(nodes: list) -> list:
    """E: Build nested tree from flat nodes / C: 将扁平节点列表构建为 G6 嵌套树格式"""
    node_map = {n["id"]: dict(n) for n in nodes}
    root_nodes = []
    for nid, node in node_map.items():
        pid = node.get("parent_id")
        if pid is None:
            root_nodes.append(node)
        node["children"] = []
    for nid, node in node_map.items():
        pid = node.get("parent_id")
        if pid and pid in node_map:
            node_map[pid]["children"].append(node)
    for nid, node in node_map.items():
        node["children"].sort(key=lambda x: x.get("label", ""))
    for nid, node in node_map.items():
        for key in ["__note", "__note_en", "details", "metadata", "parent_id"]:
            node.pop(key, None)
    return root_nodes


async def _execute_single_audio(
    pair_name: str,
    audio_path: str,
    gold_path: Optional[str],
    session_dir: str,
    session_ts: str,
    selected: list[str],
    model_name: str,
    threshold: float,
    essential_concepts: Optional[list[str]],
    gold_example_context: Optional[str],
    questions_path: Optional[str],
    human_scores: Optional[list],
    key_terms: Optional[list[str]],
    multilingual_input: Optional[dict | list],
    ground_truth_text: Optional[str],
) -> dict:
    """
    E: Start MCP Client and run the single-audio pipeline, then close it.
    C: 启动 MCP Client 执行单音频管线，随后关闭。
    """
    server_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server.py"
    )
    server_script = os.path.abspath(server_script)
    mcp_client = MCPMindMapClient(server_script)
    try:
        await mcp_client.start()
        return await _run_single_pipeline(
            pair_name=pair_name,
            audio_path=audio_path,
            gold_path=gold_path,
            mcp_client=mcp_client,
            session_dir=session_dir,
            timestamp_str=session_ts,
            selected_methods=selected,
            model_name=model_name,
            threshold=threshold,
            essential_concepts=essential_concepts,
            gold_example_context=gold_example_context,
            questions_path=questions_path,
            human_scores=human_scores,
            key_terms=key_terms,
            multilingual_input=multilingual_input,
            ground_truth_text=ground_truth_text,
        )
    finally:
        await mcp_client.close()


def _render_single_eval_report(
    pair_name: str,
    audio_path: str,
    gold_path: Optional[str],
    result: dict,
    model_name: str,
    threshold: float,
    selected: list[str],
    session_ts: str,
    session_dir: str,
) -> Optional[str]:
    """
    E: Render and save the per-pair eval report under the existing convention
        (evaluation/eval_report_{pair}_{ts}.md + session copy). Returns the
        report path, or None when the result failed.
    C: 按现有约定渲染并保存单配对评估报告（evaluation/eval_report_{pair}_{ts}.md
        + 会话目录副本）。返回报告路径；结果失败时返回 None。
    """
    if not (result.get("success") and result.get("eval_result")):
        return None
    gold_map = None
    if gold_path:
        gold_map = DataLoader.from_map_file(gold_path)
    gen_data = result.get("generated_map")
    gen_map = None
    if gen_data:
        gen_map = DataLoader.from_flat_dict(gen_data)

    config_info = {
        'pipeline': f"embedding={model_name}, τ={threshold}",
        'audio': os.path.basename(audio_path),
        'methods': ', '.join(selected),
        'session': session_ts,
    }
    renderer = MarkdownReportRenderer(embedding_model=model_name, threshold=threshold)
    report = renderer.render(
        gold_map, gen_map, result["eval_result"],
        inclusion_list=selected,
        config_info=config_info,
    )

    report_path = os.path.join("evaluation", f"eval_report_{pair_name}_{session_ts}.md")
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(T(
            f"\n  ✓ 报告已保存: {report_path}",
            f"\n  ✓ Report saved: {report_path}",
        ))
    except Exception as e:
        print(T(
            f"\n  ✗ 报告写入失败: {e}",
            f"\n  ✗ Report write failed: {e}",
        ))
        report_path = None

    # E: Also save a copy to session dir / C: 在会话目录中也保存一份
    session_report_path = os.path.join(session_dir, "eval_report.md")
    try:
        with open(session_report_path, 'w', encoding='utf-8') as f:
            f.write(report)
    except Exception as e:
        print(T(
            f"  ⚠ 会话目录报告写入失败: {e}",
            f"  ⚠ Session report write failed: {e}",
        ))
    return report_path


# ============================================================
# E: Interactive workflow entry
# C: 交互式工作流入口
# ============================================================
def _interactive_workflow(auto_install: bool = False, ignore_missing: bool = False):
    """
    E: Interactive evaluation workflow with audio-driven pipeline
    C: 交互式评估工作流（音频驱动管线）

    Steps / 步骤:
    1. Select evaluation methods / 选择评估方法
    2. Upload files (auto-detect or step-by-step) / 上传文件（自动检测或逐步上传）
    3. For each audio: Whisper → Map Gen → Evaluation → Report
       / 对每段音频：录音→生成→评估→报告
    """
    print("=" * 60)
    print(T(
        "  AI MindMap 质量评估工具 v2.0",
        "  AI MindMap Quality Evaluation Tool v2.0",
    ))
    print("=" * 60)

    # E: Step 1: Select evaluation methods
    # C: 步骤 1: 选择评估方法
    available_metrics = {
        'example': T(
            '§0 示例演示模式（使用内置示例数据）',
            '§0 Example Demo Mode (uses built-in example data)',
        ),
        'label': T(
            '§1 节点标签质量（Node-P/R/F1, LabelSim, Entity Recall）',
            '§1 Node Label Quality (Node-P/R/F1, LabelSim, Entity Recall)',
        ),
        'hierarchy': T(
            '§2 层级结构正确率（Edge-P/R/F1, UAS, nTED, PC-F1, LAR）',
            '§2 Hierarchy Accuracy (Edge-P/R/F1, UAS, nTED, PC-F1, LAR)',
        ),
        'qa': T(
            '§3 下游 QA 测试（自动生成 20 题，AI 1-5 评分）',
            '§3 Downstream QA (auto-generates 20 questions, AI-graded 1-5)',
        ),
        'efficiency': T(
            '§4 效率与 STT 保真度（latency/WER/KTRR，需要计时日志）',
            '§4 Efficiency & STT (latency/WER/KTRR, requires timing logs)',
        ),
        'multilingual': T(
            '§5 多语言与鲁棒性（需要多语言测试集）',
            '§5 Multilingual & Robustness (requires multilingual test sets)',
        ),
        'human_corr': T(
            '§6 人工评估（交互式逐音频双评分 0-10）',
            '§6 Human Evaluation (interactive per-audio dual scoring 0-10)',
        ),
        'full': T(
            '§7 全量报告（所有方法 + 综合评分）',
            '§7 Full Report (all methods + composite score)',
        ),
    }

    selected = interactive_multiselect(T(
        "步骤 1：选择评估方法",
        "Step 1: Select Evaluation Methods",
    ), available_metrics)

    # E: Example demo mode — standalone; mixing example with real methods is
    #    contradictory, so drop it with a clear message instead of silently
    #    switching to the demo.
    # C: 示例演示模式 — 独立运行；与正式评估混选是矛盾的，剔除并明确提示，
    #    而不是静默切换到演示。
    if 'example' in selected:
        if selected == ['example']:
            _run_example_demo(auto_install=auto_install, ignore_missing=ignore_missing)
            return
        selected = [k for k in selected if k != 'example']
        print(T(
            "  [!] 示例演示与正式评估互斥，已忽略 example，继续正式评估。",
            "  [!] Example demo is mutually exclusive with real evaluation; "
            "example ignored, continuing with the selected methods.",
        ))

    if 'full' in selected:
        selected = [k for k in available_metrics if k not in ('full', 'example')]

    if not selected:
        print(T("\n[!] 未选择任何评估方法，退出", "\n[!] No evaluation method selected, exiting"))
        sys.exit(0)

    # E: Check dependencies before proceeding
    # C: 依赖预检
    if not check_dependencies(selected, auto_install=auto_install, ignore_missing=ignore_missing):
        print(T(
            "\n  [!] 请安装缺失的依赖后重试。",
            "\n  [!] Please install missing dependencies and try again.",
        ))
        sys.exit(1)

    print(T(
        f"\n  已选择: {', '.join(selected)}",
        f"\n  Selected: {', '.join(selected)}",
    ))

    # E: Step 2: File upload
    # C: 步骤 2: 文件上传
    print(f"\n{'=' * 60}")
    print(T("  步骤 2：文件上传", "  Step 2: File Upload"))
    print(f"{'=' * 60}")

    uploaded_files = _collect_uploaded_files()

    # E: Check for missing required files
    # C: 检查是否缺少必需文件
    missing = _ensure_required_files(selected, uploaded_files)
    multi_audio = len(uploaded_files.get('audio_files') or []) > 1
    if multi_audio:
        # E: In multi-audio mode gold is paired per audio later; a missing gold
        #    only skips gold-dependent methods for that audio, not the whole run.
        # C: 多音频模式下金标准稍后按音频逐个配对；缺失只跳过该音频
        #    依赖金标准的方法，不阻断整个流程。
        missing = [m for m in missing if m[0] != 'gold']
        print(T(
            "  ℹ 多音频模式下，金标准将按音频逐个配对；无金标准的音频会跳过依赖金标准的方法。",
            "  ℹ In multi-audio mode gold is paired per audio; audios without gold "
            "skip gold-dependent methods.",
        ))
    if missing:
        print(T(
            f"\n  [!] 缺少必需文件:",
            f"\n  [!] Missing required files:",
        ))
        for cat, desc in missing:
            rec = FILE_CATEGORY_PATHS.get(cat, 'evaluation/data')
            if cat == 'gold':
                rec += T("（也可放入 GTC/ 或 YQL/ 子目录）", " (or GTC/ YQL/ subdirs)")
            print(f"    - {desc}")
            print(T(
                f"      推荐放置目录: {rec}",
                f"      Recommended dir: {rec}",
            ))
        print(T(
            "\n  请补全缺失文件后重新运行；或将文件放入 evaluation/data/ 对应子目录后选择模式 A 自动检测。",
            "\n  Please provide the missing files and rerun, or use Mode A auto-detection.",
        ))
        sys.exit(1)

    # E: Ensure we have an audio file
    # C: 确保有音频文件
    audio_path = uploaded_files.get('audio')
    if not audio_path or not os.path.isfile(audio_path):
        print(T(
            "\n[!] 所有评估方法（除示例外）都需要音频文件。",
            "\n[!] Audio file is required for all evaluation methods (except example).",
        ))
        sys.exit(1)

    # E: Interactive mode evaluates ONE audio per run — tell the user how many
    #    were detected and how to evaluate the rest.
    # C: 交互模式每次运行只评估一个音频 — 告知用户检测到几个、本次评估哪个、
    #    其余如何评估。
    audio_exts = (".wav", ".mp3", ".m4a", ".ogg", ".flac")
    all_audios = sorted(
        p for ext in audio_exts
        for p in glob.glob(os.path.join("evaluation", "data", "audio", f"*{ext}"))
    )
    if len(all_audios) > 1:
        print(T(
            f"  ℹ 共检测到 {len(all_audios)} 个音频，本次仅评估第 1 个："
            f"{os.path.basename(audio_path)}；其余可运行批量模式（--batch）评估。",
            f"  ℹ {len(all_audios)} audio files detected; this run evaluates only the first one: "
            f"{os.path.basename(audio_path)}. Use batch mode (--batch) for the rest.",
        ))

    gold_path = uploaded_files.get('gold')

    # E: Step 3: Configuration
    # C: 步骤 3: 配置
    print(f"\n{'=' * 60}")
    print(T("  步骤 3：评估配置", "  Step 3: Evaluation Configuration"))
    print(f"{'=' * 60}")

    model_name = prompt_str(T("嵌入模型名称", "Embedding Model Name"),
                            default="paraphrase-multilingual-MiniLM-L12-v2")
    threshold = prompt_float(T("相似度阈值 τ", "Similarity Threshold τ"),
                             default=0.70, min_val=0.0, max_val=1.0)

    # E: Load essential concepts if label is selected
    # C: 如果选择了 label，加载核心概念集合
    essential_concepts = None
    if 'label' in selected:
        concepts_path = uploaded_files.get('concepts')
        if concepts_path and os.path.isfile(concepts_path):
            try:
                with open(concepts_path, "r", encoding="utf-8") as f:
                    concepts_data = json.load(f)
                essential_concepts = concepts_data.get("concepts", [])
                print(T(
                    f"  ✓ 核心概念已加载: {len(essential_concepts)} 项",
                    f"  ✓ Essential concepts loaded: {len(essential_concepts)} items",
                ))
            except Exception as e:
                print(T(
                    f"  ⚠ 概念加载失败: {e}",
                    f"  ⚠ Concepts load failed: {e}",
                ))
                print(T(
                    "  将使用金标准节点 label 自动提取",
                    "  Will auto-extract from gold node labels",
                ))

    # E: Gold example injection — optionally inject gold example into generation prompts
    # C: 黄金示例注入 — 可选地将黄金示例注入到生成 prompt 中
    gold_example_context = None
    print(f"\n{'=' * 60}")
    print(T("  黄金示例优化", "  Gold Example Optimization"))
    print(f"{'=' * 60}")
    print(T(
        "  黄金示例对（转录文本 + 金标准导图）可注入到生成 prompt 中，指导模型产出"
        "更符合金标准结构的导图。",
        "  A gold example pair (transcript + gold mind map) can be injected into the "
        "generation prompt to guide the model toward producing maps with a similar structure.",
    ))
    print()
    use_gold = input(T(
        "  是否使用黄金示例优化生成？[y/N]: ",
        "  Use gold example for generation optimization? [y/N]: ",
    )).strip().lower()
    if use_gold in ('y', 'yes'):
        print()
        transcript_path = input(T(
            "  请输入转录文本文件路径（例如 results/transcript.txt）: ",
            "  Enter transcript file path (e.g., results/transcript.txt): ",
        )).strip()
        if transcript_path:
            gold_json_path = input(T(
                "  请输入金标准导图 JSON 文件路径（例如 evaluation/data/gold/gold_example.json）: ",
                "  Enter gold mind map JSON file path (e.g., evaluation/data/gold/gold_example.json): ",
            )).strip()
            if gold_json_path:
                gold_example_context = _format_gold_example(transcript_path, gold_json_path)
                if gold_example_context:
                    print(T(
                        "  ✓ 黄金示例将注入生成 prompt",
                        "  ✓ Gold example will be injected into generation prompts",
                    ))
                else:
                    print(T(
                        "  ⚠ 格式化失败，将不使用黄金示例",
                        "  ⚠ Gold example formatting failed, proceeding without it",
                    ))

    # E: Step 4: Execute pipeline
    # C: 步骤 4: 执行管线
    print(f"\n{'=' * 60}")
    print(T("  步骤 4：执行评估管线", "  Step 4: Execute Evaluation Pipeline"))
    print(f"{'=' * 60}")

    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(os.getcwd(), "evaluation", "data", "sessions", session_ts)
    _ensure_dir(session_dir)

    # E: §6 Interactive human scoring — list all pending audio files, then ask
    #    two 0-10 Likert scores per audio (system map / human map). The scores
    #    are aggregated into the final evaluation total as a §2-hierarchy
    #    compensation component.
    # C: §6 交互式人工评分 — 列出全部待评估音频，逐音频询问两个 0-10 评分
    #    （系统导图 / 人类标注导图）。评分汇总后作为 §2 层级结构的补偿
    #    分量计入评估总分。
    human_scores = None
    if 'human_corr' in selected:
        from evaluation.human_correlation.interactive_scorer import (
            collect_questionnaires_loop, load_questionnaires,
            save_human_scores, aggregate_human_scores,
        )
        pending_audio: list[str] = sorted({
            os.path.splitext(os.path.basename(p))[0]
            for ext in audio_exts
            for p in glob.glob(os.path.join("evaluation", "data", "audio", f"*{ext}"))
        })
        if not pending_audio:
            print(T(
                "  [!] 未找到用于人工评分的音频",
                "  [!] No audio files found for human scoring",
            ))
        else:
            # E: Files already uploaded in Mode A/B are reused first — do not
            #    ask the user to enter the same paths again.
            # C: 优先复用模式 A/B 已上传的问卷文件 — 不再要求用户重复输入路径。
            pre_uploaded = uploaded_files.get('human_scores')
            if isinstance(pre_uploaded, list) and pre_uploaded:
                try:
                    human_scores = load_questionnaires(pre_uploaded)
                    if human_scores:
                        agg = aggregate_human_scores(human_scores)
                        print(T(
                            f"  ✓ 已使用刚上传的 {len(pre_uploaded)} 份问卷文件，共 {agg['num_samples']} 条评分"
                            f"（归一化 {agg['overall_normalized']:.4f}）",
                            f"  ✓ Reusing the {len(pre_uploaded)} uploaded questionnaire file(s): "
                            f"{agg['num_samples']} samples, "
                            f"overall_normalized={agg['overall_normalized']:.4f}",
                        ))
                except Exception as e:
                    print(T(
                        f"  ⚠ 已上传问卷解析失败: {e}",
                        f"  ⚠ Uploaded questionnaire(s) failed to parse: {e}",
                    ))
                    human_scores = None

            if human_scores is None:
                print(T(
                    "\n  §6 人工评估 — 问卷模式",
                    "\n  §6 Human Evaluation — questionnaire mode",
                ))
                print(T(
                    "  1) 录入新问卷（问卷一、问卷二……）",
                    "  1) Enter new questionnaire(s) (Q1, Q2, ...)",
                ))
                print(T(
                    "  2) 导入已有问卷文件（可多份一起输入）",
                    "  2) Import questionnaire file(s)",
                ))
                print(T(
                    "  3) 跳过",
                    "  3) Skip",
                ))
                choice = input(T(
                    "  请选择 [1/2/3]（1=录入 2=导入 3=跳过）: ",
                    "  Choose [1/2/3] (1=enter, 2=import, 3=skip): ",
                )).strip()
                if choice == '2':
                    paths_input = input(T(
                        "  问卷文件路径（多个用逗号分隔，例如 a.json,b.json）: ",
                        "  Questionnaire file path(s), comma-separated (e.g. a.json,b.json): ",
                    )).strip()
                    if paths_input:
                        paths = [p.strip() for p in paths_input.split(',') if p.strip()]
                        human_scores = load_questionnaires(paths)
                        if human_scores:
                            agg = aggregate_human_scores(human_scores)
                            print(T(
                                f"  ✓ 汇总: {agg['num_samples']} 条样本，{agg['num_questionnaires']} 份问卷，"
                                f"归一化 {agg['overall_normalized']:.4f}",
                                f"  ✓ Aggregated: {agg['num_samples']} samples, "
                                f"{agg['num_questionnaires']} questionnaires, "
                                f"overall_normalized={agg['overall_normalized']:.4f}",
                            ))
                elif choice in ('', '1'):
                    samples = collect_questionnaires_loop(pending_audio, gold_dir="evaluation/data/gold")
                    if samples:
                        # E: Save each questionnaire separately / C: 每份问卷单独落盘
                        by_q: dict[str, list[dict]] = {}
                        for s in samples:
                            by_q.setdefault(s.get('questionnaire_id', 'Q1'), []).append(s)
                        for qid, qs in by_q.items():
                            hs_path = os.path.join(
                                "evaluation", "data", "human_scores",
                                f"human_scores_{session_ts}_{qid}.json",
                            )
                            save_human_scores(qs, hs_path)
                            print(T(
                                f"  ✓ {qid} 已保存: {hs_path}",
                                f"  ✓ {qid} saved: {hs_path}",
                            ))
                        agg = aggregate_human_scores(samples)
                        print(T(
                            f"  ✓ 汇总: {agg['num_samples']} 条样本，{agg['num_questionnaires']} 份问卷，"
                            f"归一化 {agg['overall_normalized']:.4f}",
                            f"  ✓ Aggregated: {agg['num_samples']} samples, "
                            f"{agg['num_questionnaires']} questionnaires, "
                            f"overall_normalized={agg['overall_normalized']:.4f}",
                        ))
                        human_scores = samples
                    else:
                        print(T(
                            "  [!] 未收集到评分，跳过人工评估",
                            "  [!] No scores collected, human_corr will be skipped",
                        ))
                else:
                    print(T(
                        "  ℹ 输入无效，已跳过人工评分。",
                        "  ℹ Invalid choice, human evaluation skipped.",
                    ))

    # E: Start MCP Client for this session
    # C: 启动 MCP Client
    print(T(
        "\n  正在启动 MCP Client 进行转录和导图生成...",
        "\n  Starting MCP Client for transcription and map generation...",
    ))

    # E: Load §4/§5 inputs detected or uploaded above (key terms, multilingual
    #    results, reference transcript) so they actually reach the evaluators.
    # C: 加载上方检测/上传的 §4/§5 输入（关键术语、多语言结果、标准转录文本），
    #    确保真正传入评估器。
    key_terms: Optional[list[str]] = None
    kt_path = uploaded_files.get('key_terms')
    if kt_path and os.path.isfile(kt_path):
        try:
            with open(kt_path, "r", encoding="utf-8") as f:
                kt_data = json.load(f)
            key_terms = kt_data.get("key_terms", kt_data) if isinstance(kt_data, dict) else kt_data
            print(f"  ✓ {T('关键术语已加载', 'Key terms loaded')}: {len(key_terms)} terms")
        except Exception as e:
            print(f"  ⚠ {T('关键术语加载失败', 'Key terms load failed')}: {e}")

    multilingual_input = None
    ml_path = uploaded_files.get('multilingual_results')
    if ml_path and os.path.isfile(ml_path):
        try:
            with open(ml_path, "r", encoding="utf-8") as f:
                mdata = json.load(f)
            multilingual_input = mdata.get("results", mdata) if isinstance(mdata, dict) else mdata
            print(f"  ✓ {T('多语言测试数据已加载', 'Multilingual test data loaded')}")
        except Exception as e:
            print(f"  ⚠ {T('多语言数据加载失败', 'Multilingual data load failed')}: {e}")

    ground_truth_text = None
    gt_path = uploaded_files.get('transcript')
    if gt_path and os.path.isfile(gt_path):
        try:
            with open(gt_path, "r", encoding="utf-8") as f:
                ground_truth_text = f.read()
            print(f"  ✓ {T('标准转录文本已加载', 'Reference transcript loaded')}: {os.path.basename(gt_path)}")
        except Exception as e:
            print(f"  ⚠ {T('标准转录文本加载失败', 'Reference transcript load failed')}: {e}")

    pair_name = os.path.splitext(os.path.basename(audio_path))[0]

    # E: Multi-audio mode — evaluate every selected audio, default to a full
    #    summary report, optionally per-audio reports (schema §4 reporting).
    # C: 多音频模式 — 逐个评估选中的音频，默认生成全量汇总报告，
    #    可选生成每音频单独报告（schema §4 报告要求）。
    audio_files = uploaded_files.get('audio_files') or [audio_path]
    audio_files = [a for a in audio_files if a and os.path.isfile(a)]

    if len(audio_files) > 1:
        multi_results: list[dict] = []
        needs_gold = any(m in ('label', 'hierarchy') for m in selected)
        for i, apath in enumerate(audio_files, 1):
            base = os.path.splitext(os.path.basename(apath))[0]
            print(f"\n{'=' * 60}")
            print(T(
                f"  [{i}/{len(audio_files)}] 正在评估: {base}",
                f"  [{i}/{len(audio_files)}] Evaluating: {base}",
            ))
            print(f"{'=' * 60}")
            gold_for_audio = None
            if needs_gold:
                gold_for_audio, _gsrc = _find_gold_auto(base, "evaluation/data/gold")
                if gold_for_audio is None:
                    print(T(
                        f"  ⚠ 该音频无对应金标准（根目录/GTC/YQL），已跳过 label/hierarchy；"
                        f"效率等不依赖金标准的评估照常进行。",
                        f"  ⚠ No gold standard found for this audio (root/GTC/YQL); "
                        f"label/hierarchy skipped, gold-independent methods continue.",
                    ))
            res = asyncio.run(_execute_single_audio(
                pair_name=base, audio_path=apath, gold_path=gold_for_audio,
                session_dir=session_dir, session_ts=session_ts,
                selected=selected, model_name=model_name, threshold=threshold,
                essential_concepts=essential_concepts,
                gold_example_context=gold_example_context,
                questions_path=uploaded_files.get('questions'),
                human_scores=human_scores, key_terms=key_terms,
                multilingual_input=multilingual_input,
                ground_truth_text=ground_truth_text,
            ))
            multi_results.append(res)
            if res.get("success"):
                print(T(
                    f"  ✓ 完成: {base}（计时日志: {res.get('timing_log_path', 'N/A')}）",
                    f"  ✓ Done: {base} (timing log: {res.get('timing_log_path', 'N/A')})",
                ))
            else:
                print(T(
                    f"  ✗ 失败: {base} — {res.get('error', '未知错误')}",
                    f"  ✗ Failed: {base} — {res.get('error', 'Unknown error')}",
                ))

        ok_n = sum(1 for r in multi_results if r.get("success"))

        # E: Full summary report — reuses BatchEvaluator.generate_summary_report
        # C: 全量汇总报告 — 复用 BatchEvaluator.generate_summary_report
        print(f"\n{'=' * 60}")
        print(T(
            "  生成全量汇总报告...",
            "  Generating full summary report...",
        ))
        print(f"{'=' * 60}")
        evaluator = BatchEvaluator.__new__(BatchEvaluator)
        evaluator.session_ts = session_ts
        evaluator.all_results = multi_results
        evaluator.model_name = model_name
        evaluator.threshold = threshold
        evaluator.selected_methods = selected
        summary = evaluator.generate_summary_report()
        summary_path_session = os.path.join(session_dir, "summary_report.md")
        with open(summary_path_session, "w", encoding="utf-8") as f:
            f.write(summary)
        summary_path_root = os.path.join("evaluation", f"summary_report_{session_ts}.md")
        with open(summary_path_root, "w", encoding="utf-8") as f:
            f.write(summary)
        print(T(
            f"  ✓ 全量汇总报告已保存: {summary_path_root}",
            f"  ✓ Full summary report saved: {summary_path_root}",
        ))
        print(T(
            f"  ✓ 会话目录副本: {summary_path_session}",
            f"  ✓ Session copy: {summary_path_session}",
        ))

        # E: Optional per-audio reports / C: 可选每音频单独报告
        make_single = input(T(
            "  是否额外为每个音频生成单独报告？[y/N]: ",
            "  Generate a separate report per audio as well? [y/N]: ",
        )).strip().lower()
        single_paths: list[str] = []
        if make_single in ('y', 'yes'):
            for res in multi_results:
                if not res.get("success"):
                    continue
                sp = _render_single_eval_report(
                    res.get("pair_name", "?"),
                    res.get("audio_path", ""),
                    res.get("gold_path"),
                    res, model_name, threshold, selected, session_ts, session_dir,
                )
                if sp:
                    single_paths.append(sp)

        print(f"\n{'=' * 60}")
        print(T("  评估完成！", "  Evaluation Complete!"))
        print(T(
            f"  成功: {ok_n}/{len(multi_results)}",
            f"  Succeeded: {ok_n}/{len(multi_results)}",
        ))
        print(T(
            f"  全量汇总报告: {summary_path_root}",
            f"  Full summary report: {summary_path_root}",
        ))
        if single_paths:
            print(T(
                "  单独报告:",
                "  Per-audio reports:",
            ))
            for sp in single_paths:
                print(f"    - {sp}")
        print(T(
            f"  会话目录: {session_dir}",
            f"  Session dir: {session_dir}",
        ))
        print(f"{'=' * 60}")
        return

    # E: Single-audio mode — existing flow / C: 单音频模式 — 现有流程
    result = asyncio.run(_execute_single_audio(
        pair_name=pair_name, audio_path=audio_path, gold_path=gold_path,
        session_dir=session_dir, session_ts=session_ts,
        selected=selected, model_name=model_name, threshold=threshold,
        essential_concepts=essential_concepts,
        gold_example_context=gold_example_context,
        questions_path=uploaded_files.get('questions'),
        human_scores=human_scores, key_terms=key_terms,
        multilingual_input=multilingual_input,
        ground_truth_text=ground_truth_text,
    ))

    # E: Step 5: Generate report
    # C: 步骤 5: 生成报告
    print(f"\n{'=' * 60}")
    print(T("  步骤 5：生成评估报告", "  Step 5: Generate Evaluation Report"))
    print(f"{'=' * 60}")

    report_path = _render_single_eval_report(
        pair_name, audio_path, gold_path, result,
        model_name, threshold, selected, session_ts, session_dir,
    )

    if report_path:
        # E: Show summary / C: 显示摘要
        show_summary = input(T(
            "\n  在终端显示报告摘要？[Y/n]: ",
            "\n  Show report summary in terminal? [Y/n]: ",
        )).strip().lower()
        if show_summary in ('', 'y', 'yes'):
            print_results_table(result["eval_result"])

        print(f"\n{'=' * 60}")
        print(T("  评估完成！", "  Evaluation Complete!"))
        print(T(
            f"  报告文件: {report_path}",
            f"  Report file: {report_path}",
        ))
        if result.get("timing_log_path"):
            print(T(
                f"  计时日志: {result['timing_log_path']}",
                f"  Timing log: {result['timing_log_path']}",
            ))
        print(T(
            f"  会话目录: {session_dir}",
            f"  Session dir: {session_dir}",
        ))
        print(f"{'=' * 60}")
    else:
        print(T(
            f"\n  ✗ 评估失败: {result.get('error', '未知错误')}",
            f"\n  ✗ Evaluation failed: {result.get('error', 'Unknown error')}",
        ))


# ============================================================
# E: Offline re-evaluation mode — recompute metrics from a saved session
# C: 离线重算模式 — 从已保存的会话重算指标（跳过转录与 LLM 生成）
# ============================================================
def _find_gold_for_pair(pair_name: str, gold_dir: str = "evaluation/data/gold",
                        prefer: Optional[str] = None) -> Optional[str]:
    """
    E: Locate gold JSON for a pair across gold subdirectories (root/GTC/YQL)
    C: 在 gold 子目录（根/GTC/YQL）中定位配对的金标准 JSON

    Args / 参数:
        pair_name: Pair name (audio basename) / 配对名（音频文件名去后缀）
        gold_dir: Gold standard root dir / 金标准根目录
        prefer: Optional subdir to prefer first ('GTC' or 'YQL'); when None, keeps
                root->GTC->YQL order for backward compatibility.
                可选优先命中的子目录（'GTC' 或 'YQL'）；为 None 时保持 根->GTC->YQL
                顺序以向后兼容。
            → 用于固定同一套 ground truth，避免 GTC/YQL 两套结构冲突导致结果漂移。
    """
    gold_dir_resolved = os.path.join(os.getcwd(), gold_dir) if not os.path.isabs(gold_dir) else gold_dir
    if prefer:
        # E: Only the preferred subdir (single authoritative ground truth) / C: 仅优先子目录（单一 authoritative ground truth）
        preferred = os.path.join(gold_dir_resolved, prefer, f"{pair_name}.json")
        if os.path.isfile(preferred):
            return preferred
        # E: Fall back to root file / C: 回退到根目录文件
        root = os.path.join(gold_dir_resolved, f"{pair_name}.json")
        if os.path.isfile(root):
            return root
        return None
    candidates = [
        os.path.join(gold_dir_resolved, f"{pair_name}.json"),
        os.path.join(gold_dir_resolved, "GTC", f"{pair_name}.json"),
        os.path.join(gold_dir_resolved, "YQL", f"{pair_name}.json"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def run_reuse_sessions(
    session_ts: str,
    selected_methods: Optional[list[str]] = None,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    threshold: float = 0.70,
    gold_dir: str = "evaluation/data/gold",
    session_base: str = "evaluation/data/sessions",
    prefer_gold: Optional[str] = None,
    postprocess: bool = False,
) -> dict:
    """
    E: Offline re-evaluation — read saved gold + generated_map.json from a session
        and recompute all selected metrics, skipping audio transcription and LLM
        generation (zero-cost regression for evaluation-side fixes).
    C: 离线重算 — 直接读取会话保存的 gold 与 generated_map.json 重算全部指标，
        跳过音频转录与 LLM 生成（评估侧修复的零成本回归）。

    Args / 参数:
        session_ts: Session timestamp dir name / 会话时间戳目录名
        selected_methods: Evaluation methods / 评估方法

    Returns / 返回:
        {"session_ts", "results", "summary_report"} / 汇总结果字典
    """
    methods = selected_methods or ['label', 'hierarchy']
    session_dir = os.path.join(os.getcwd(), session_base, session_ts)
    if not os.path.isdir(session_dir):
        print(T(
            f"[Reuse] 会话目录不存在: {session_dir}",
            f"[Reuse] Session directory not found: {session_dir}",
        ))
        return {"error": f"Session not found / 会话不存在: {session_ts}", "results": [], "summary_report": ""}

    print("=" * 60)
    print(T(
        "  离线重算模式",
        "  Offline Re-Evaluation",
    ))
    print(T(
        f"  会话: {session_ts}",
        f"  Session: {session_ts}",
    ))
    print(T(
        f"  方法: {', '.join(methods)}",
        f"  Methods: {', '.join(methods)}",
    ))
    print(T(
        f"  模型: {model_name}, 阈值 τ: {threshold}",
        f"  Model: {model_name}, Threshold τ: {threshold}",
    ))
    print("=" * 60)

    # E: Discover per-pair subdirectories / C: 发现每对配对的子目录
    pair_dirs = sorted(
        d for d in glob.glob(os.path.join(session_dir, "*"))
        if os.path.isdir(d)
    )
    if not pair_dirs:
        print(T(
            f"[Reuse] 未找到配对子目录: {session_dir}",
            f"[Reuse] No pair subdirectories found: {session_dir}",
        ))
        return {"error": "No pair subdirectories / 无配对子目录", "results": [], "summary_report": ""}

    concepts_base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "evaluation", "data", "concepts",
    )

    all_results: list[dict] = []
    for pair_dir in pair_dirs:
        pair_name = os.path.basename(pair_dir)
        print(f"\n{'=' * 60}")
        print(T(
            f"  重算配对: {pair_name}",
            f"  Re-evaluating pair: {pair_name}",
        ))
        print(f"{'=' * 60}")

        gold_path = _find_gold_for_pair(pair_name, gold_dir, prefer=prefer_gold)
        if gold_path is None:
            print(T(
                f"  ✗ 未找到金标准: {pair_name}",
                f"  ✗ Gold standard not found: {pair_name}",
            ))
            all_results.append({
                "pair_name": pair_name, "success": False,
                "error": f"Gold standard not found / 未找到金标准",
                "eval_result": None,
            })
            continue

        # E: Collect all generated map files (supports repeat runs) / C: 收集所有生成导图文件（支持多运行）
        gen_files = sorted(glob.glob(os.path.join(pair_dir, "generated_map*.json")))
        if not gen_files:
            print(T(
                f"  ✗ 未找到生成导图: {pair_name}",
                f"  ✗ No generated_map.json found: {pair_name}",
            ))
            all_results.append({
                "pair_name": pair_name, "success": False,
                "error": "No generated_map.json / 无生成导图文件",
                "eval_result": None,
            })
            continue

        # E: Load essential concepts if available / C: 加载核心概念（若存在）
        essential_concepts = None
        concepts_path = os.path.join(concepts_base_dir, f"{pair_name}_concepts.json")
        if os.path.isfile(concepts_path):
            try:
                with open(concepts_path, "r", encoding="utf-8") as f:
                    essential_concepts = json.load(f).get("concepts", []) or None
            except Exception:
                essential_concepts = None

        # E: Load transcript if available (for QA method) / C: 加载转录文本（供 QA 方法使用）
        transcript_text = ""
        trans_files = sorted(glob.glob(os.path.join(pair_dir, "transcription*.txt")))
        if trans_files:
            try:
                with open(trans_files[0], "r", encoding="utf-8") as f:
                    transcript_text = f.read()
            except Exception as e:
                print(T(
                    f"  ⚠ 转录文本加载失败: {e}",
                    f"  ⚠ Transcript load failed: {e}",
                ))

        run_eval_results = []
        last_error = None
        for gen_file in gen_files:
            try:
                with open(gen_file, "r", encoding="utf-8") as f:
                    gen_data = json.load(f)
            except Exception as e:
                last_error = f"generated_map load failed / 生成图加载失败: {e}"
                print(f"  ✗ {last_error}: {gen_file}")
                continue

            # C: 评估侧可选树形后处理 — 默认关闭：重算应忠实反映会话存储的原图，
            #    避免“重算数字 = 后处理 + 新边提取 + 0.0 标记”多重漂移叠加。
            #    通过 --postprocess 显式开启，使历史会话受益于生成侧修复。
            # E: Optional eval-side tree postprocessing — OFF by default so reuse
            #    reflects the stored map faithfully; enable explicitly via
            #    --postprocess to replay generated-side repairs on historical sessions.
            if postprocess and isinstance(gen_data, dict) and gen_data.get('nodes'):
                try:
                    from mindmap_agent import postprocess_map_structure
                    from config import Config
                    if getattr(Config, 'TREE_POSTPROCESS_ENABLED', False):
                        gen_data = postprocess_map_structure(gen_data)
                except Exception as pp_err:
                    print(T(
                        f"  ⚠ [Reuse] 树形后处理失败: {pp_err}",
                        f"  ⚠ [Reuse] Tree postprocess failed: {pp_err}",
                    ))

            if not isinstance(gen_data, dict) or not gen_data.get("nodes"):
                last_error = f"Empty generated map / 空生成图 ({os.path.basename(gen_file)})"
                print(f"  ✗ {last_error}")
                # C: 为空图配对生成一份显式降级报告（不再残留误导性空真值报告）
                # E: Emit an explicit degradation report for the empty-map pair
                try:
                    gold_map = DataLoader.from_map_file(gold_path) if gold_path else None
                    deg = gen_data.get("_degradation") or {}
                    gen_map = MindMapData(
                        nodes=[], links=[], tree=[],
                        metadata={"_degradation": deg, "error": gen_data.get("error")},
                    )
                    renderer = MarkdownReportRenderer(embedding_model=model_name, threshold=threshold)
                    report = renderer.render(gold_map, gen_map, {}, inclusion_list=methods,
                                             config_info={"pipeline": f"embedding={model_name}, \u03c4={threshold}",
                                                         "session": session_ts, "pair": pair_name})
                    empty_report_dir = os.path.join(session_dir, pair_name)
                    os.makedirs(empty_report_dir, exist_ok=True)
                    # E: Never overwrite the original eval_report.md — write a
                    #    distinctly named reuse report instead.
                    # C: 绝不覆盖原始 eval_report.md — 写入独立命名的重算报告。
                    with open(os.path.join(empty_report_dir, "eval_report_reuse.md"), "w", encoding="utf-8") as f:
                        f.write(report)
                except Exception as rep_err:
                    print(T(
                        f"  ⚠ 空图报告生成失败: {rep_err}",
                        f"  ⚠ Empty-map report generation failed: {rep_err}",
                    ))
                continue

            # E: Auto-load §3-§6 inputs from data dirs (skip example files)
            # C: 自动加载 §3-§6 输入（跳过示例文件）
            questions = None
            qa_files = sorted(glob.glob(os.path.join("evaluation", "data", "questions", "*.json")))
            qa_files = [f for f in qa_files if 'example' not in os.path.basename(f)]
            if qa_files:
                try:
                    with open(qa_files[-1], "r", encoding="utf-8") as f:
                        qa_data = json.load(f)
                    questions = qa_data.get("questions", qa_data) if isinstance(qa_data, dict) else qa_data
                except Exception:
                    questions = None

            timing_snapshots = None
            timing_files = sorted(glob.glob(os.path.join("evaluation", "data", "timing", "*.json")))
            timing_files = [f for f in timing_files if 'example' not in os.path.basename(f)]
            if timing_files:
                try:
                    with open(timing_files[-1], "r", encoding="utf-8") as f:
                        tdata = json.load(f)
                    timing_snapshots = tdata.get("runs", tdata) if isinstance(tdata, dict) else tdata
                except Exception:
                    timing_snapshots = None

            multilingual_input = None
            ml_files = sorted(glob.glob(os.path.join("evaluation", "data", "multilingual", "*.json")))
            ml_files = [f for f in ml_files if 'example' not in os.path.basename(f)]
            if ml_files:
                try:
                    with open(ml_files[-1], "r", encoding="utf-8") as f:
                        mdata = json.load(f)
                    multilingual_input = mdata.get("results", mdata) if isinstance(mdata, dict) else mdata
                except Exception:
                    multilingual_input = None

            key_terms = None
            kt_files = sorted(glob.glob(os.path.join("evaluation", "data", "timing", "*key_terms*.json")))
            kt_files = [f for f in kt_files if 'example' not in os.path.basename(f)]
            if kt_files:
                try:
                    with open(kt_files[-1], "r", encoding="utf-8") as f:
                        kt_data = json.load(f)
                    key_terms = kt_data.get("key_terms", kt_data) if isinstance(kt_data, dict) else kt_data
                except Exception:
                    key_terms = None

            ground_truth_text = None
            gt_files = sorted(glob.glob(os.path.join("evaluation", "data", "timing", "*.txt")))
            gt_files = [f for f in gt_files if 'example' not in os.path.basename(f)]
            if gt_files:
                try:
                    with open(gt_files[-1], "r", encoding="utf-8") as f:
                        ground_truth_text = f.read()
                except Exception:
                    ground_truth_text = None

            human_scores = None
            hs_files = sorted(glob.glob(os.path.join("evaluation", "data", "human_scores", "*.json")))
            hs_files = [f for f in hs_files if 'example' not in os.path.basename(f)]
            if hs_files:
                from evaluation.human_correlation.interactive_scorer import load_questionnaires
                try:
                    human_scores = load_questionnaires(hs_files)
                except Exception:
                    human_scores = None

            eval_result = _run_evaluation_for_pair(
                gold_path=gold_path,
                gen_data=gen_data,
                model_name=model_name,
                threshold=threshold,
                essential_concepts=essential_concepts,
                selected_methods=methods,
                transcript_text=transcript_text,
                questions=questions,
                timing_snapshots=timing_snapshots,
                multilingual_input=multilingual_input,
                human_scores=human_scores,
                key_terms=key_terms,
                ground_truth_text=ground_truth_text,
            )
            if "error" in eval_result:
                last_error = eval_result["error"]
                print(T(
                    f"  ✗ 评估失败: {last_error}",
                    f"  ✗ Evaluation failed: {last_error}",
                ))
                continue
            run_eval_results.append(eval_result)

        if not run_eval_results:
            err = last_error or "All runs failed / 所有运行均失败"
            print(T(
                f"  ✗ 配对失败: {err}",
                f"  ✗ Pair failed: {err}",
            ))
            all_results.append({
                "pair_name": pair_name, "success": False,
                "error": err, "eval_result": None,
            })
            continue

        averaged = _average_eval_results(run_eval_results)
        all_results.append({
            "pair_name": pair_name,
            "gold_path": gold_path,
            "success": True,
            "error": None,
            "eval_result": averaged,
            "__maps_reused": len(run_eval_results),
        })
        hier = averaged.get('hierarchy', {})
        label = averaged.get('label', {})
        nf1 = label.get('node_f1', 0) if isinstance(label, dict) else 0
        ef1 = hier.get('edge_f1', 0) if isinstance(hier, dict) else 0
        print(T(
            f"  ✓ 重算完成: Node-F1={nf1:.4f}, Edge-F1={ef1:.4f}",
            f"  ✓ Re-evaluated: Node-F1={nf1:.4f}, Edge-F1={ef1:.4f}",
        ))

        # C: 同步将本基准（GTC/YQL）重算结果写入该对报告，保证报告与计算基准一致、可追溯
        # E: Persist re-computed report (under current gold baseline) so the report stays
        #    traceable and consistent with the baseline actually used.
        try:
            gold_map = DataLoader.from_map_file(gold_path) if gold_path else None
            gen_data_0 = None
            if gen_files:
                with open(gen_files[0], "r", encoding="utf-8") as gf:
                    gen_data_0 = json.load(gf)
            gen_map = DataLoader.from_flat_dict(gen_data_0) if gen_data_0 else None
            renderer = MarkdownReportRenderer(embedding_model=model_name, threshold=threshold)
            config_info = {
                'pipeline': f"embedding={model_name}, τ={threshold}",
                'methods': ', '.join(methods),
                'baseline': os.path.basename(os.path.dirname(gold_path)) if gold_path else '?',
                'reuse_session': session_ts,
                'input_transformed': 'postprocess' if postprocess else 'none',
                '_semantics': 'empty_mu_zero',
            }
            rep = renderer.render(gold_map, gen_map, averaged, inclusion_list=methods, config_info=config_info)
            # E: Never overwrite the original eval_report.md — write a distinctly
            #    named reuse report so historical evidence stays intact.
            # C: 绝不覆盖原始 eval_report.md — 写入独立命名的重算报告，保留历史证据。
            with open(os.path.join(pair_dir, "eval_report_reuse.md"), "w", encoding="utf-8") as rf:
                rf.write(rep)
        except Exception as rep_err:
            print(T(
                f"  ⚠ 报告同步失败: {rep_err}",
                f"  ⚠ Reuse report sync failed: {rep_err}",
            ))

    # E: Generate summary report / C: 生成汇总报告
    evaluator = BatchEvaluator.__new__(BatchEvaluator)
    evaluator.session_ts = session_ts
    evaluator.all_results = all_results
    evaluator.model_name = model_name
    evaluator.threshold = threshold
    evaluator.selected_methods = methods
    report = evaluator.generate_summary_report()

    report_path = os.path.join(session_dir, "reuse_summary_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(T(
        f"\n✓ 重算汇总报告已保存: {report_path}",
        f"\n✓ Reuse summary report saved: {report_path}",
    ))

    ok = sum(1 for r in all_results if r.get("success"))
    fail = len(all_results) - ok
    print(T(
        f"\n  总配对数: {len(all_results)}",
        f"\n  Total pairs: {len(all_results)}",
    ))
    print(T(
        f"  成功: {ok}",
        f"  Succeeded: {ok}",
    ))
    print(T(
        f"  失败: {fail}",
        f"  Failed: {fail}",
    ))
    if fail:
        for r in all_results:
            if not r.get("success"):
                print(f"    - {r['pair_name']}: {r.get('error', 'Unknown')}")

    return {"session_ts": session_ts, "results": all_results, "summary_report": report}


# ============================================================
# E: Batch mode entry
# C: 批量模式入口
# ============================================================
async def _run_batch(audio_dir: str, gold_dir: str, selected_methods: Optional[list[str]] = None,
                    auto_install: bool = False, ignore_missing: bool = False,
                    gold_example_transcript: Optional[str] = None,
                    gold_example_json: Optional[str] = None,
                    repeat_count: int = 1):
    """
    E: Batch evaluation mode entry — start BatchEvaluator
    C: 批量评估模式入口 — 启动 BatchEvaluator

    Args / 参数:
        audio_dir: Audio file directory / 音频文件目录
        gold_dir: Gold standard directory / 金标准文件目录
        selected_methods: Evaluation methods to run / 要运行的评估方法
        auto_install: Auto-install missing dependencies / 自动安装缺失依赖
        ignore_missing: Continue despite missing dependencies / 忽略缺失继续执行
        gold_example_transcript: Gold example transcript path / 黄金示例转录文本路径
        gold_example_json: Gold example mind map JSON path / 黄金示例导图JSON路径
        repeat_count: Number of independent runs per pair for averaging / 每配对独立运行次数取平均值
    """
    print("=" * 60)
    print(T(
        "  AI MindMap 批量评估模式 v2.0",
        "  AI MindMap Batch Evaluation Mode v2.0",
    ))
    print("=" * 60)
    print(T(
        f"  音频目录: {audio_dir}",
        f"  Audio dir: {audio_dir}",
    ))
    print(T(
        f"  金标准目录: {gold_dir}",
        f"  Gold dir: {gold_dir}",
    ))
    if gold_example_transcript:
        print(T(
            f"  黄金示例转录: {gold_example_transcript}",
            f"  Gold example transcript: {gold_example_transcript}",
        ))
    if gold_example_json:
        print(T(
            f"  黄金示例JSON: {gold_example_json}",
            f"  Gold example JSON: {gold_example_json}",
        ))
    print()

    methods = selected_methods or ['label', 'hierarchy', 'efficiency']

    # E: Check dependencies before proceeding
    # C: 依赖预检
    if not check_dependencies(methods, auto_install=auto_install, ignore_missing=ignore_missing):
        print(T(
            "[!] 依赖检查未通过，退出",
            "[!] Dependency check failed, exiting",
        ))
        sys.exit(1)

    evaluator = BatchEvaluator(
        audio_dir=audio_dir,
        gold_dir=gold_dir,
        selected_methods=methods,
        gold_example_transcript=gold_example_transcript,
        gold_example_json=gold_example_json,
        repeat_count=repeat_count,
    )
    await evaluator.run_all()


# ============================================================
# E: Main entry point
# C: 主入口
# ============================================================
def main():
    """E: Main entry — parse args and dispatch to interactive or batch mode
    C: 主入口 — 解析参数并分发到交互式或批量模式"""
    # E: Load api.env (real keys, override) only at the CLI entry point — same
    #    behaviour as cli_pipeline.py, but without the import-time process-wide
    #    side effect on hosts that merely import this module.
    # C: 仅在 CLI 入口加载 api.env（真实 key，override）— 与 cli_pipeline.py
    #    行为一致，同时避免 import 本模块时污染宿主进程环境变量。
    _api_env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'api.env'
    if _api_env_path.exists():
        load_dotenv(dotenv_path=_api_env_path, override=True)

    parser = argparse.ArgumentParser(
        description="AI MindMap Quality Evaluation Tool / AI MindMap 质量评估工具"
    )
    parser.add_argument(
        "--lang",
        choices=['zh', 'en'],
        default=None,
        help="CLI interface language: zh (Chinese) or en (English); "
             "interactive mode asks at startup when omitted "
             "/ CLI 界面语言：zh（中文）或 en（英语）；交互模式未指定时启动时询问",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch evaluation mode / 批量评估模式",
    )
    parser.add_argument(
        "--audio-dir",
        type=str,
        default="evaluation/data/audio",
        help="Audio file directory (used in --batch mode) / 音频文件目录（--batch 模式下使用）",
    )
    parser.add_argument(
        "--gold-dir",
        type=str,
        default="evaluation/data/gold",
        help="Gold standard directory (used in --batch mode) / 金标准文件目录（--batch 模式下使用）",
    )
    parser.add_argument(
        "--methods",
        type=str,
        nargs='+',
        default=None,
        help="Evaluation methods for batch mode (e.g., --methods label hierarchy qa) / 批量模式下的评估方法",
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Auto-install missing dependencies via pip / 自动通过 pip 安装缺失依赖",
    )
    parser.add_argument(
        "--ignore-missing-deps",
        action="store_true",
        help="Continue despite missing dependencies / 忽略缺失依赖继续执行",
    )
    parser.add_argument(
        "--gold-example-transcript",
        type=str,
        default=None,
        help="Gold example transcript .txt path (for batch mode) / 黄金示例转录文本路径（批量模式）",
    )
    parser.add_argument(
        "--gold-example-json",
        type=str,
        default=None,
        help="Gold example mind map .json path (for batch mode) / 黄金示例导图JSON路径（批量模式）",
    )
    parser.add_argument(
        "--triple-report",
        action="store_true",
        help="Generate the Chinese-named triple comparison report (STT / agent tree / human tree) / 生成中文命名的三元组对比报告（STT / Agent 树 / 人类树）",
    )
    parser.add_argument(
        "--reuse-sessions",
        type=str,
        default=None,
        help="Offline re-evaluation of a saved session (e.g., --reuse-sessions 20260730_130242), "
             "skipping audio transcription and LLM generation / 离线重算已保存会话的指标"
             "（跳过转录与生成，零成本回归）",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=5,
        help="Number of independent runs per pair for metric averaging "
             "(schema §4.1 default 5 for P50/P95; pass --repeat 1 to run once) "
             "/ 每配对独立运行次数取平均值（schema §4.1 默认 5 次以计算 P50/P95；"
             "可用 --repeat 1 只跑一次）",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="paraphrase-multilingual-MiniLM-L12-v2",
        help="Embedding model name (used in --reuse-sessions mode) / 嵌入模型名（--reuse-sessions 模式使用）",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.70,
        help="Semantic similarity threshold tau (used in --reuse-sessions mode) / 语义相似度阈值（--reuse-sessions 模式使用）",
    )
    parser.add_argument(
        "--prefer-gold",
        type=str,
        default=None,
        help="Preferred gold baseline subdirectory name, e.g. GTC or YQL (--reuse-sessions) / 首选金标准基准子目录名（--reuse-sessions）",
    )
    parser.add_argument(
        "--postprocess",
        action="store_true",
        help="Apply tree postprocessing to stored maps during reuse re-evaluation (--reuse-sessions) / 重算时对存储导图应用树形后处理（--reuse-sessions）",
    )

    args = parser.parse_args()

    # E: Language selection — explicit --lang wins; interactive mode asks the
    #    user first (before any CLI text is printed); batch/reuse/triple default
    #    to Chinese when --lang is omitted.
    # C: 语言选择 — 显式 --lang 优先；交互模式在最开始询问用户（打印任何
    #    CLI 文案之前）；batch/reuse/triple 未指定时默认中文。
    if args.lang:
        set_lang(args.lang)
    elif not (args.batch or args.reuse_sessions or args.triple_report):
        while True:
            choice = input(
                "\n请选择界面语言 / Select interface language — 1=中文 / Chinese, 2=English: "
            ).strip()
            if choice == '1':
                set_lang('zh')
                break
            if choice == '2':
                set_lang('en')
                break
            print("  输入无效，请输入 1 或 2 / Invalid choice, please enter 1 or 2.")
    else:
        set_lang('zh')

    if args.triple_report:
        # E: Triple comparison report mode / C: 三元组对比报告模式
        import asyncio
        from evaluation.report.triple_report import run_triple_report
        asyncio.run(run_triple_report(audio_dir=args.audio_dir, gold_dir=args.gold_dir))
    elif args.reuse_sessions:
        # E: Offline re-evaluation mode / C: 离线重算模式
        run_reuse_sessions(
            args.reuse_sessions,
            selected_methods=args.methods or ['label', 'hierarchy'],
            model_name=args.model_name,
            threshold=args.threshold,
            gold_dir=args.gold_dir,
            prefer_gold=args.prefer_gold,
            postprocess=args.postprocess,
        )
    elif args.batch:
        # E: Batch evaluation mode / C: 批量评估模式
        selected_methods = args.methods or ['label', 'hierarchy', 'efficiency']
        import asyncio
        asyncio.run(_run_batch(
            args.audio_dir, args.gold_dir, selected_methods,
            auto_install=args.auto_install, ignore_missing=args.ignore_missing_deps,
            gold_example_transcript=args.gold_example_transcript,
            gold_example_json=args.gold_example_json,
            repeat_count=args.repeat,
        ))
    else:
        # E: Interactive CLI mode (default) / C: 交互式 CLI 模式（默认）
        _interactive_workflow(auto_install=args.auto_install, ignore_missing=args.ignore_missing_deps)


if __name__ == '__main__':
    main()
