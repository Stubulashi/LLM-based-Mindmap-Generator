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

from evaluation.core.data_loader import DataLoader, MindMapData
from evaluation.core.aligner import HungarianAligner
from evaluation.utils.console_utils import (
    interactive_multiselect,
    prompt_file,
    prompt_float,
    prompt_str,
    auto_detect_files,
    ProgressTracker,
    print_results_table,
)
from evaluation.utils.io_utils import read_json, write_json, save_intermediate_result, timestamp
from evaluation.report.markdown_renderer import MarkdownReportRenderer

# E: MCP Client for audio transcription and map generation
# C: MCP Client，用于音频转录和导图生成
from mcp_client import MCPMindMapClient


# ============================================================
# E: Required input files for each evaluation method
# C: 每种评估方法所需的输入文件
# ============================================================
# E: (method_name -> list of required file categories)
# C: (方法名 -> 必需文件类别列表)
METHOD_REQUIRED_FILES: dict[str, list[str]] = {
    'label':       ['gold', 'audio', 'concepts'],
    'hierarchy':   ['gold', 'audio'],
    'qa':          ['audio', 'questions'],
    'efficiency':  ['audio', 'timing', 'transcript', 'key_terms'],
    'multilingual':['audio', 'multilingual_results'],
    'human_corr':  ['audio', 'human_scores'],
    'full':        ['gold', 'audio', 'concepts', 'questions', 'timing', 'transcript', 'key_terms', 'multilingual_results', 'human_scores'],
}

# ============================================================
# E: Python package dependencies for each evaluation method
# C: 每种评估方法所需的 Python 第三方包
# ============================================================
# E: (method_name -> list of importable package names)
# C: (方法名 -> 可 import 的包名列表)
METHOD_DEPENDENCIES: dict[str, list[str]] = {
    'label':       ['numpy'],
    'hierarchy':   ['numpy', 'zss'],
    'qa':          ['nltk', 'rouge_score', 'bert_score'],
    'efficiency':  ['jiwer', 'jieba', 'scipy'],
    'multilingual': [],
    'human_corr':  ['scipy'],
    'full':        ['nltk', 'rouge_score', 'bert_score', 'zss', 'jiwer', 'jieba', 'scipy'],
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
    print("  [!] Missing Required Dependencies / 缺少必需依赖")
    print("=" * 60)
    print("  The following packages are required for the selected methods:")
    print("  以下包是所选评估方法必需的：")
    print()
    for pkg in missing_pkgs:
        pip_name = _PIP_PACKAGE_NAMES.get(pkg, pkg)
        print(f"    - {pkg} ({pip_name} 可通过 pip 安装)")
    print()
    print(f"  Please open a new terminal and run / 请开启一个新的 terminal 运行:")
    print(f"    {pip_cmd}")
    print()
    print(f"  Or install all evaluation dependencies / 或安装所有评估依赖:")
    print(f"    pip install nltk rouge-score bert-score zss jiwer jieba scipy")
    print()

    if auto_install:
        print("  Attempting auto-install / 正在尝试自动安装...")
        success = True
        for pkg in missing_pkgs:
            pip_name = _PIP_PACKAGE_NAMES.get(pkg, pkg)
            try:
                print(f"  Installing {pip_name}...")
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install', pip_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"    ✓ {pip_name} installed / 已安装")
            except Exception as e:
                print(f"    ✗ Failed to install {pip_name}: {e}")
                success = False
        if success:
            print()
            print("  All missing packages installed successfully! / 所有缺失包已成功安装！")
            return True
        else:
            print()
            print("  Some packages failed to install. Please install manually.")
            print("  部分包安装失败，请手动安装。")
            return False

    if ignore_missing:
        print("  --ignore-missing-deps is set, continuing despite missing packages.")
        print("  已设置 --ignore-missing-deps，将继续执行。")
        print()
        return True

    print("  Use --auto-install to auto-install, or --ignore-missing-deps to continue.")
    print("  使用 --auto-install 自动安装，或 --ignore-missing-deps 忽略缺失继续执行。")
    print()
    return False


# ============================================================
# E: File management utilities
# C: 文件管理工具函数
# ============================================================
def _ensure_dir(path: str):
    """E: Create directory if it doesn't exist / C: 确保目录存在"""
    os.makedirs(path, exist_ok=True)


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
        print(f"  ✓ Copied to / 已复制到: {dest_path}")
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
    print(f"  ✓ Saved to session / 已保存到会话: {session_path}")

    # E: Path 2: debug_output/{data_type}_{pair_name}_{timestamp}.json
    # C: 路径 2：debug_output/{data_type}_{pair_name}_{timestamp}.json
    debug_dir = os.path.join(os.getcwd(), "debug_output")
    _ensure_dir(debug_dir)
    debug_filename = f"{data_type}_{pair_name}_{timestamp_str}.json"
    debug_path = os.path.join(debug_dir, debug_filename)
    write_json(debug_path, data)
    print(f"  ✓ Saved to debug / 已保存到调试: {debug_path}")


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
            missing.append(f"  - {FILE_CATEGORY_DESC.get(cat, cat)}")
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
    print("  File Upload / 文件上传")
    print(f"{'=' * 60}")
    print("  You can:")
    print("  A) Place all required files in the evaluation/data/ subdirectories and let the system auto-detect them.")
    print("  B) Upload files one by one following the prompts.")
    print("  Files you upload will be automatically copied to the evaluation/data/ directory for future use.")
    print()
    print("  您可以选择：")
    print("  A) 将所有必需文件放到 evaluation/data/ 子目录下，系统自动检测。")
    print("  B) 跟随提示逐个上传文件。")
    print("  上传的文件将自动复制到 evaluation/data/ 目录中备用。")
    print()

    mode = input("  Select mode / 选择模式 [A/b]: ").strip().lower()

    if mode in ('', 'a', 'b'):
        # E: Mode A — auto-detect from standard directories
        # C: 模式 A — 从标准目录自动检测
        print("\n  Mode A: Auto-detecting files from standard directories...")
        print("  模式 A：从标准目录自动检测文件...")

        gold_candidates = sorted(glob.glob("evaluation/data/gold/*.json"))
        if gold_candidates:
            uploaded['gold'] = gold_candidates[-1]
            print(f"  ✓ Detected gold / 检测到金标准: {os.path.basename(uploaded['gold'])}")

        audio_extensions = (".wav", ".mp3", ".m4a", ".ogg", ".flac")
        audio_candidates = []
        for ext in audio_extensions:
            audio_candidates.extend(glob.glob(f"evaluation/data/audio/*{ext}"))
        if audio_candidates:
            uploaded['audio'] = sorted(audio_candidates)[0]
            print(f"  ✓ Detected audio / 检测到音频: {os.path.basename(uploaded['audio'])}")

        concept_candidates = sorted(glob.glob("evaluation/data/concepts/*.json"))
        concept_candidates = [f for f in concept_candidates if 'example' not in os.path.basename(f)]
        if concept_candidates:
            uploaded['concepts'] = concept_candidates[-1]
            print(f"  ✓ Detected concepts / 检测到概念集: {os.path.basename(uploaded['concepts'])}")

        q_candidates = sorted(glob.glob("evaluation/data/questions/*.json"))
        q_candidates = [f for f in q_candidates if 'example' not in os.path.basename(f)]
        if q_candidates:
            uploaded['questions'] = q_candidates[-1]
            print(f"  ✓ Detected questions / 检测到问题集: {os.path.basename(uploaded['questions'])}")

        timing_candidates = sorted(glob.glob("evaluation/data/timing/*.json"))
        timing_candidates = [f for f in timing_candidates if 'example' not in os.path.basename(f)]
        if timing_candidates:
            uploaded['timing'] = timing_candidates[-1]
            print(f"  ✓ Detected timing logs / 检测到计时日志: {os.path.basename(uploaded['timing'])}")

        transcript_candidates = sorted(glob.glob("evaluation/data/timing/*.txt"))
        if transcript_candidates:
            uploaded['transcript'] = transcript_candidates[-1]
            print(f"  ✓ Detected transcript / 检测到标准文本: {os.path.basename(uploaded['transcript'])}")

        ml_candidates = sorted(glob.glob("evaluation/data/multilingual/*.json"))
        ml_candidates = [f for f in ml_candidates if 'example' not in os.path.basename(f)]
        if ml_candidates:
            uploaded['multilingual_results'] = ml_candidates[-1]
            print(f"  ✓ Detected multilingual data / 检测到多语言数据: {os.path.basename(uploaded['multilingual_results'])}")

        hs_candidates = sorted(glob.glob("evaluation/data/human_scores/*.json"))
        hs_candidates = [f for f in hs_candidates if 'example' not in os.path.basename(f)]
        if hs_candidates:
            uploaded['human_scores'] = hs_candidates[-1]
            print(f"  ✓ Detected human scores / 检测到人工评分: {os.path.basename(uploaded['human_scores'])}")

        if mode == 'b':
            # E: Mode B was selected but went through A path, ask if user wants to supplement
            # C: 选择了模式 B 但走了 A 路径，询问是否补充
            pass
    else:
        # E: Mode B — step-by-step upload (also triggered if auto-detect mode was used)
        # C: 模式 B — 逐步上传
        print("\n  Mode B: Step-by-step file upload...")
        print("  模式 B：逐步上传文件...")

        for cat, desc in FILE_CATEGORY_DESC.items():
            skip = input(f"\n  Upload {desc}? [Y/n]: ").strip().lower()
            if skip in ('', 'y', 'yes'):
                path = input(f"  Enter file path / 输入文件路径: ").strip()
                if path and os.path.isfile(path):
                    uploaded[cat] = _copy_to_data_dir(path, cat)
                else:
                    print("  Skipped / 跳过：文件不存在或路径为空")

    return uploaded


# ============================================================
# E: Audio-gold pair discovery
# C: 音频-金标准配对发现
# ============================================================
def discover_pairs(
    audio_dir: str = "evaluation/data/audio",
    gold_dir: str = "evaluation/data/gold",
) -> list[tuple[str, str, str]]:
    """
    E: Auto-discover audio file and gold JSON file pairs
    C: 自动发现音频文件与金标准 JSON 文件的配对

    Pairing rule / 配对规则:
        Strip audio file extension → find matching .json in gold/ directory
        / 音频文件名去掉后缀 → 在 gold/ 目录中查找同名 .json 文件

    Args / 参数:
        audio_dir: Audio directory / 音频目录
        gold_dir: Gold standard directory / 金标准目录

    Returns / 返回:
        [(pair_name, audio_path, gold_path), ...]
    """
    pairs = []

    audio_dir_resolved = os.path.join(os.getcwd(), audio_dir) if not os.path.isabs(audio_dir) else audio_dir
    gold_dir_resolved = os.path.join(os.getcwd(), gold_dir) if not os.path.isabs(gold_dir) else gold_dir

    if not os.path.isdir(audio_dir_resolved):
        print(f"[Batch] Audio directory not found / 音频目录不存在: {audio_dir_resolved}")
        return []

    audio_extensions = (".wav", ".mp3", ".m4a", ".ogg", ".flac")
    audio_candidates = []
    for ext in audio_extensions:
        audio_candidates.extend(glob.glob(os.path.join(audio_dir_resolved, f"*{ext}")))
    audio_candidates = sorted(set(audio_candidates))

    if not audio_candidates:
        print(f"[Batch] No audio files found / 未找到音频文件: {audio_dir}")
        return []

    gold_candidates = sorted(glob.glob(os.path.join(gold_dir_resolved, "*.json")))
    gold_index: dict[str, str] = {}
    for gpath in gold_candidates:
        base = os.path.splitext(os.path.basename(gpath))[0]
        if 'example' not in base:
            gold_index[base] = gpath

    for apath in audio_candidates:
        base = os.path.splitext(os.path.basename(apath))[0]
        if base in gold_index:
            pairs.append((base, apath, gold_index[base]))
        else:
            print(f"[Batch] Warning: no gold file found for / 警告：未找到金标准: {base}")

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
    results = {}

    # E: §1 Label Quality / C: 标签质量评估
    if 'label' in selected_methods:
        from evaluation.label.eval_label import evaluate_label_quality
        try:
            label_result = evaluate_label_quality(gold_map, gen_map, aligner, essential_concepts)
            results['label'] = label_result.to_dict()
        except Exception as e:
            results['label'] = {"error": str(e)}

    # E: §2 Hierarchy / C: 层级结构评估
    if 'hierarchy' in selected_methods:
        from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
        try:
            alignment = aligner.align(gold_map.nodes, gen_map.nodes)
            hier_result = evaluate_hierarchy_quality(gold_map, gen_map, alignment)
            results['hierarchy'] = hier_result.to_dict()
        except Exception as e:
            results['hierarchy'] = {"error": str(e)}

    # E: §3 QA / C: 下游 QA 评估
    if 'qa' in selected_methods:
        from evaluation.qa.eval_qa import QAEvaluator
        try:
            qa_eval = QAEvaluator()
            qa_result = qa_eval.evaluate("", gen_map.nodes, [])
            results['qa'] = qa_result.to_dict()
        except Exception as e:
            results['qa'] = {"error": str(e)}

    # E: §4 Efficiency / C: 效率与 STT 评估
    if 'efficiency' in selected_methods:
        from evaluation.efficiency.eval_efficiency import evaluate_efficiency
        try:
            eff_result = evaluate_efficiency()
            results['efficiency'] = eff_result.to_dict()
        except Exception as e:
            results['efficiency'] = {"error": str(e)}

    # E: §5 Multilingual / C: 多语言评估
    if 'multilingual' in selected_methods:
        from evaluation.multilingual.eval_multilingual import evaluate_multilingual
        try:
            multi_result = evaluate_multilingual()
            results['multilingual'] = multi_result.to_dict()
        except Exception as e:
            results['multilingual'] = {"error": str(e)}

    # E: §6 Human Correlation / C: 人工评估
    if 'human_corr' in selected_methods:
        from evaluation.human_correlation.eval_human_correlation import evaluate_human_correlation
        try:
            hc_result = evaluate_human_correlation()
            results['human_corr'] = hc_result.to_dict()
        except Exception as e:
            results['human_corr'] = {"error": str(e)}

    return results


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
) -> dict:
    """
    E: Execute the full pipeline for a single audio pair
    C: 对单个音频配对执行完整管线

    Steps / 步骤:
    1. Whisper transcription / Whisper 转录
    2. Mind map generation / 导图生成
    3. Quality evaluation / 质量评估
    4. Dual output save / 双轨输出保存
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
    }

    print(f"\n{'=' * 60}")
    print(f"  Processing pair / 处理配对: {pair_name}")
    print(f"{'=' * 60}")

    try:
        # -------------------------------------------------
        # E: Step 1: Whisper transcription
        # C: 步骤 1: Whisper 转录
        # -------------------------------------------------
        print(f"  [1/3] Transcribing audio / 转录音频...")
        if mcp_client is None:
            raise RuntimeError("MCP Client not started / MCP Client 未启动")

        transcribe_result = await mcp_client.call_tool(
            "transcribe_audio", {"file_path": os.path.abspath(audio_path)}
        )
        raw_text = ""
        if isinstance(transcribe_result, dict):
            raw_text = transcribe_result.get("raw_text", "").strip()

        if not raw_text:
            print(f"  [Skip / 跳过] Transcription is empty / 转录为空")
            result["error"] = "Empty transcription / 空转录"
            return result

        # E: Save transcription / C: 保存转录文本
        trans_path = os.path.join(session_dir, pair_name, "transcription.txt")
        _ensure_dir(os.path.dirname(trans_path))
        with open(trans_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
        print(f"  ✓ Transcription saved / 转录已保存 ({len(raw_text)} chars / 字符)")

        result["transcription"] = raw_text

        # -------------------------------------------------
        # E: Step 2: Mind map generation
        # C: 步骤 2: 导图生成
        # -------------------------------------------------
        print(f"  [2/3] Generating mind map / 生成导图...")

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
                "session_ts": f"{timestamp_str}_{pair_name}",
            },
        )

        if not isinstance(gen_result, dict):
            raise RuntimeError(f"Invalid map generation result / 导图生成返回无效: {type(gen_result)}")

        # E: Save generated map / C: 保存生成导图
        _save_dual_output(pair_name, gen_result, "generated_map", session_dir, timestamp_str)
        node_count = len(gen_result.get("nodes", []))
        print(f"  ✓ Map generated / 导图已生成 ({node_count} nodes / 节点)")

        result["generated_map"] = gen_result

        # -------------------------------------------------
        # E: Step 3: Evaluation
        # C: 步骤 3: 运行评估
        # -------------------------------------------------
        print(f"  [3/3] Running evaluation / 运行评估...")

        eval_result = _run_evaluation_for_pair(
            gold_path=gold_path,
            gen_data=gen_result,
            model_name=model_name,
            threshold=threshold,
            essential_concepts=essential_concepts,
            selected_methods=selected_methods,
        )

        if "error" in eval_result:
            print(f"  ✗ Evaluation failed / 评估失败: {eval_result['error']}")
            result["error"] = eval_result["error"]
            return result

        # E: Save evaluation result including timing / C: 保存评估结果（含计时）
        eval_result_with_timing = dict(eval_result)
        eval_result_with_timing['timing_snapshots'] = timing_snapshots

        # E: Run stand-alone efficiency evaluation with timing data / C: 用计时数据运行效率评估
        if 'efficiency' in selected_methods:
            try:
                from evaluation.efficiency.eval_efficiency import evaluate_efficiency, EfficiencyStandards
                st = EfficiencyStandards()
                custom_stds = os.path.join(os.getcwd(), 'evaluation', 'data', 'standards', 'custom_standards.json')
                if os.path.isfile(custom_stds):
                    st = EfficiencyStandards(custom_stds)
                eff_result = evaluate_efficiency(
                    timing_snapshots=timing_snapshots,
                    stt_text=result.get('transcription', ''),
                    key_terms=None,
                    standards=st,
                )
                eval_result_with_timing['efficiency'] = eff_result.to_dict()
                print(f"    ✓ Efficiency evaluation complete / 效率评估完成: Total P50={eff_result.t_total_p50:.2f}s")
            except Exception as e:
                print(f"    [Efficiency] Auto-eval failed / 自动效率评估失败: {e}")

        # E: Save evaluation result / C: 保存评估结果
        _save_dual_output(pair_name, eval_result_with_timing, "eval_result", session_dir, timestamp_str)

        result["eval_result"] = eval_result_with_timing
        result["timing_snapshots"] = timing_snapshots
        result["success"] = True

        # E: Print summary / C: 打印摘要
        nf1 = eval_result.get('label', {}).get('node_f1', 0) if isinstance(eval_result.get('label'), dict) else 0
        ef1 = eval_result.get('hierarchy', {}).get('edge_f1', 0) if isinstance(eval_result.get('hierarchy'), dict) else 0
        print(f"  ✓ Evaluation complete / 评估完成: Node-F1={nf1:.4f}, Edge-F1={ef1:.4f}")

    except Exception as e:
        print(f"  ✗ Pipeline failed / 管线失败: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)

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
    ):
        self.audio_dir = audio_dir
        self.gold_dir = gold_dir
        self.session_base = session_base
        self.model_name = model_name
        self.threshold = threshold
        self.selected_methods = selected_methods or ['label', 'hierarchy', 'efficiency']

        self.mcp_client: Optional[MCPMindMapClient] = None
        self.session_ts: str = ""
        self.session_dir: str = ""
        self.all_results: list[dict] = []
        self.pairs: list[tuple[str, str, str]] = []

    async def start_mcp(self):
        """E: Start MCP Server subprocess and connect MCP Client
        C: 启动 MCP Server 子进程并连接 MCP Client"""
        print("[Batch] Starting MCP Client...")
        print("[Batch] 正在启动 MCP Client...")

        server_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server.py"
        )
        server_script = os.path.abspath(server_script)

        self.mcp_client = MCPMindMapClient(server_script)
        try:
            await self.mcp_client.start()
            print("[Batch] MCP Client started / 启动完成")
        except Exception as e:
            print(f"[Batch] MCP Client start failed / 启动失败: {e}")
            self.mcp_client = None
            raise

    def discover(self) -> list[tuple[str, str, str]]:
        """E: Discover all audio-gold pairs / C: 发现所有音频-金标准配对"""
        self.pairs = discover_pairs(self.audio_dir, self.gold_dir)

        if self.pairs:
            print(f"[Batch] Discovered {len(self.pairs)} pairs / 发现 {len(self.pairs)} 个配对")
            for name, apath, gpath in self.pairs:
                print(f"  - {name}")
        else:
            print("[Batch] No pairs discovered / 未发现任何配对")

        return self.pairs

    async def run_all(self):
        """E: Iterate all pairs and execute full batch evaluation
        C: 遍历所有配对，执行完整批量评估"""
        # E: Create session directory / C: 创建会话目录
        self.session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(os.getcwd(), self.session_base, self.session_ts)
        _ensure_dir(self.session_dir)

        print("=" * 60)
        print("  Batch Evaluation Started / 批量评估开始")
        print(f"  Session: {self.session_ts}")
        print(f"  Session Dir: {self.session_dir}")
        print(f"  Model / 模型: {self.model_name}")
        print(f"  Threshold / 阈值: {self.threshold}")
        print(f"  Methods / 方法: {', '.join(self.selected_methods)}")
        print("=" * 60)

        # E: Discover pairs / C: 发现配对
        self.discover()

        if not self.pairs:
            print("[Batch] No pairs to process, exiting / 没有可处理的配对，退出")
            return

        # E: Start MCP / C: 启动 MCP
        await self.start_mcp()

        # E: Load essential concepts for each pair / C: 加载每个配对的核心概念
        concepts_base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "evaluation", "data", "concepts",
        )

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
                        print(f"  ✓ Loaded essential concepts / 已加载核心概念: {len(loaded)} items / 项")
                except Exception as e:
                    print(f"  ⚠ Concepts file load failed / 概念文件加载失败: {e}")

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
            )
            self.all_results.append(result)

        # E: Close MCP / C: 关闭 MCP
        await self.close()

        # E: Generate summary report / C: 生成汇总报告
        report = self.generate_summary_report()
        report_path = os.path.join(self.session_dir, "summary_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✓ Summary report saved / 汇总报告已保存: {report_path}")

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
                row = [pair_name] + ["FAIL"] * (len(header_cols) - 1)
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
        print("  Batch Evaluation Complete / 批量评估完成")
        print("=" * 60)
        print(f"  Total pairs / 总配对数: {len(self.all_results)}")
        print(f"  Succeeded / 成功: {len(successful)}")
        print(f"  Failed / 失败: {len(failed)}")
        print(f"  Session dir / 会话目录: {self.session_dir}")

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
                print(f"  Node-F1 Mean / 均值: {_mean(nf1_values):.4f}")

    async def close(self):
        """E: Close MCP Client / C: 关闭 MCP Client"""
        if self.mcp_client is not None:
            try:
                await self.mcp_client.close()
                print("[Batch] MCP Client closed / 已关闭")
            except Exception as e:
                print(f"[Batch] Close error / 关闭异常: {e}")
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
        print("\n  [!] Please install missing dependencies and try again.")
        print("  [!] 请安装缺失的依赖后重试。")
        return

    print("=" * 60)
    print("  §0 Example Demo Mode / 示例演示模式")
    print("=" * 60)
    print("  Running full evaluation with built-in example data")
    print("  使用内置示例数据自动执行完整评估流程")
    print()

    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    threshold = 0.70

    # E: Step 1 — Load all example data / C: 加载所有示例数据
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(base_dir), "evaluation", "data")

    gold_path = os.path.join(data_dir, "gold", "gold_example.json")
    gold_map = DataLoader.from_map_file(gold_path)
    if gold_map is None:
        print("  ✗ Gold load failed / 金标准加载失败")
        return
    print(f"  ✓ Gold loaded / 金标准加载成功: {gold_map.node_count} nodes / 节点")

    concepts_path = os.path.join(data_dir, "concepts", "example_essential_concepts.json")
    essential_concepts = None
    if os.path.isfile(concepts_path):
        with open(concepts_path) as f:
            concepts_data = json.load(f)
        essential_concepts = concepts_data.get("concepts", [])
        print(f"  ✓ Concepts loaded / 核心概念加载成功: {len(essential_concepts)} items / 项")

    print("  Generating simulated map...")
    gen_dict = _generate_example_map(gold_map)
    gen_map = DataLoader.from_flat_dict(gen_dict)
    print(f"  ✓ Simulated map generated / 模拟导图已生成: {gen_map.node_count} nodes / 节点")

    aligner = HungarianAligner(model_name=model_name, threshold=threshold)

    # E: Step 2 — Execute all dimension evaluations / C: 执行所有维度评估
    results = {}
    selected_dims = ["label", "hierarchy", "qa", "efficiency", "multilingual", "human_corr"]
    progress = ProgressTracker(total=len(selected_dims))

    # E: §1 Label Quality / C: 节点标签质量
    progress.start("Node Label Quality / 节点标签质量")
    try:
        from evaluation.label.eval_label import evaluate_label_quality
        label_result = evaluate_label_quality(gold_map, gen_map, aligner, essential_concepts)
        results["label"] = label_result.to_dict()
        print(f"    Node-F1: {label_result.node_f1:.4f}")
        progress.complete("Node Label Quality / 节点标签质量")
    except Exception as e:
        print(f"    [Error / 错误] {e}")
        progress.complete("Node Label Quality / 节点标签质量", status="Failed / 失败")

    # E: §2 Hierarchy / C: 层级结构
    progress.start("Hierarchy Accuracy / 层级结构正确率")
    try:
        from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
        alignment = aligner.align(gold_map.nodes, gen_map.nodes)
        hier_result = evaluate_hierarchy_quality(gold_map, gen_map, alignment)
        results["hierarchy"] = hier_result.to_dict()
        print(f"    Edge-F1: {hier_result.edge_f1:.4f}")
        progress.complete("Hierarchy Accuracy / 层级结构正确率")
    except Exception as e:
        print(f"    [Error / 错误] {e}")
        progress.complete("Hierarchy Accuracy / 层级结构正确率", status="Failed / 失败")

    # E: §3 QA / C: 下游 QA
    progress.start("Downstream QA / 下游 QA 测试")
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
        print(f"    QA Retention: {qa_result.qa_retention:.4f}")
        progress.complete("Downstream QA / 下游 QA 测试")
    except Exception as e:
        print(f"    [Error / 错误] {e}")
        progress.complete("Downstream QA / 下游 QA 测试", status="Failed / 失败")

    # E: §4 Efficiency / C: 效率与 STT
    progress.start("Efficiency & STT / 效率与 STT 保真度")
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
                    })
        if os.path.isfile(terms_path):
            with open(terms_path) as f:
                kd = json.load(f)
            key_terms = kd.get("key_terms", [])
        eff_result = evaluate_efficiency(
            timing_logs=timing_logs,
            stt_text="This is an example transcription for STT evaluation demo",
            ground_truth_text="This is an example transcription for STT evaluation demo",
            key_terms=key_terms,
        )
        results["efficiency"] = eff_result.to_dict()
        print(f"    WER: {eff_result.wer:.4f}")
        progress.complete("Efficiency & STT / 效率与 STT 保真度")
    except Exception as e:
        print(f"    [Error / 错误] {e}")
        progress.complete("Efficiency & STT / 效率与 STT 保真度", status="Failed / 失败")

    # E: §5 Multilingual / C: 多语言与鲁棒性
    progress.start("Multilingual & Robustness / 多语言与鲁棒性")
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
            mx_avg = {k: sum(d[k] for d in mixed_data)/len(mx_avg) for k in ["entity_recall","label_sim","pc_f1"]}

        multi_result = evaluate_multilingual(
            cn_results=cn_avg, en_results=en_avg, mixed_results=mx_avg,
            noise_test_results=noise_data,
        )
        results["multilingual"] = multi_result.to_dict()
        print(f"    max_delta_recall: {multi_result.max_delta_recall:.4f}")
        progress.complete("Multilingual & Robustness / 多语言与鲁棒性")
    except Exception as e:
        print(f"    [Error / 错误] {e}")
        progress.complete("Multilingual & Robustness / 多语言与鲁棒性", status="Failed / 失败")

    # E: §6 Human Correlation / C: 人工评估
    progress.start("Human Evaluation Correlation / 人工评估相关性")
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
        progress.complete("Human Evaluation Correlation / 人工评估相关性")
    except Exception as e:
        print(f"    [Error / 错误] {e}")
        progress.complete("Human Evaluation Correlation / 人工评估相关性", status="Failed / 失败")

    # E: Step 3 — Generate report with **example** markers / C: 生成带标记的报告
    print()
    print("=" * 60)
    print("  Generating Evaluation Report / 生成评估报告")
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
    print(f"\n  ✓ Report saved / 报告已保存: {report_path}")

    print()
    print("=" * 60)
    print("  Example Demo Complete / 示例演示已完成")
    print(f"  Report file / 报告文件: {report_path}")
    print("=" * 60)
    print()
    print("  Notes / 说明:")
    print("  1. Demo uses built-in example data, results are for reference only")
    print("  1. 演示使用内置示例数据，结果仅供参考")
    print("  2. All values in the report are marked **example** to distinguish from formal evaluations")
    print("  2. 报告中所有数值均标记为 **example**，以区别于正式评估")
    print("  3. Upload real data for formal evaluations via interactive or batch mode")
    print("  3. 上传真实数据后，通过交互式或批量模式获得正式评估结果")
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
    print("  AI MindMap Quality Evaluation Tool v2.0")
    print("  AI MindMap 质量评估工具 v2.0")
    print("=" * 60)

    # E: Step 1: Select evaluation methods
    # C: 步骤 1: 选择评估方法
    available_metrics = {
        'example': '§0 Example Demo Mode / 示例演示模式 (uses built-in example data / 使用内置示例数据)',
        'label': '§1 Node Label Quality / 节点标签质量 (Node-P/R/F1, LabelSim, Entity Recall)',
        'hierarchy': '§2 Hierarchy Accuracy / 层级结构正确率 (Edge-P/R/F1, UAS, nTED, PC-F1, LAR)',
        'qa': '§3 Downstream QA / 下游 QA 测试 (requires question set / 需要预置问题集)',
        'efficiency': '§4 Efficiency & STT / 效率与 STT 保真度 (latency/WER/KTRR, requires timing logs / 需要计时日志)',
        'multilingual': '§5 Multilingual & Robustness / 多语言与鲁棒性 (requires multilingual test sets / 需要多语言测试集)',
        'human_corr': '§6 Human Evaluation Correlation / 人工评估相关性 (requires human scoring data / 需要人工评分数据)',
        'full': '§7 Full Report / 全量报告 (all methods + composite score / 所有方法 + 综合评分)',
    }

    selected = interactive_multiselect("Step 1: Select Evaluation Methods", available_metrics)

    # E: Example demo mode — standalone
    # C: 示例演示模式 — 独立处理
    if 'example' in selected:
        _run_example_demo(auto_install=auto_install, ignore_missing=ignore_missing)
        return

    if 'full' in selected:
        selected = [k for k in available_metrics if k not in ('full', 'example')]

    if not selected:
        print("\n[!] No evaluation method selected, exiting / 未选择任何评估方法，退出")
        sys.exit(0)

    # E: Check dependencies before proceeding
    # C: 依赖预检
    if not check_dependencies(selected, auto_install=auto_install, ignore_missing=ignore_missing):
        print("\n  [!] Please install missing dependencies and try again.")
        print("  [!] 请安装缺失的依赖后重试。")
        sys.exit(1)

    print(f"\n  Selected / 已选择: {', '.join(selected)}")

    # E: Step 2: File upload
    # C: 步骤 2: 文件上传
    print(f"\n{'=' * 60}")
    print("  Step 2: File Upload / 文件上传")
    print(f"{'=' * 60}")

    uploaded_files = _collect_uploaded_files()

    # E: Check for missing required files
    # C: 检查是否缺少必需文件
    missing = _ensure_required_files(selected, uploaded_files)
    if missing:
        print(f"\n  [!] Missing required files / 缺少必需文件:")
        for m in missing:
            print(m)
        print("\n  Please upload the missing files and try again.")
        print("  请上传缺失的文件后重试。")
        print("  Note: Place files in evaluation/data/ subdirectories for auto-detection.")
        print("  提示：将文件放入 evaluation/data/ 下对应子目录即可自动检测。")
        sys.exit(1)

    # E: Ensure we have an audio file
    # C: 确保有音频文件
    audio_path = uploaded_files.get('audio')
    if not audio_path or not os.path.isfile(audio_path):
        print("\n[!] Audio file is required for all evaluation methods (except example).")
        print("  所有评估方法（除示例外）都需要音频文件。")
        sys.exit(1)

    gold_path = uploaded_files.get('gold')

    # E: Step 3: Configuration
    # C: 步骤 3: 配置
    print(f"\n{'=' * 60}")
    print("  Evaluation Configuration / 评估配置")
    print(f"{'=' * 60}")

    model_name = prompt_str("Embedding Model Name / Embedding 模型名称",
                            default="paraphrase-multilingual-MiniLM-L12-v2")
    threshold = prompt_float("Similarity Threshold τ / 相似度阈值 τ", default=0.70, min_val=0.0, max_val=1.0)

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
                print(f"  ✓ Essential concepts loaded / 核心概念已加载: {len(essential_concepts)} items / 项")
            except Exception as e:
                print(f"  ⚠ Concepts load failed / 概念加载失败: {e}")
                print("  Will auto-extract from gold node labels / 将使用金标准节点 label 自动提取")

    # E: Step 4: Execute pipeline
    # C: 步骤 4: 执行管线
    print(f"\n{'=' * 60}")
    print("  Step 3: Execute Evaluation Pipeline / 执行评估管线")
    print(f"{'=' * 60}")

    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(os.getcwd(), "evaluation", "data", "sessions", session_ts)
    _ensure_dir(session_dir)

    # E: Start MCP Client for this session
    # C: 启动 MCP Client
    print("\n  Starting MCP Client for transcription and map generation...")
    print("  启动 MCP Client 进行转录和导图生成...")

    pair_name = os.path.splitext(os.path.basename(audio_path))[0]

    async def _run_async():
        server_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server.py"
        )
        server_script = os.path.abspath(server_script)
        mcp_client = MCPMindMapClient(server_script)
        try:
            await mcp_client.start()
            result = await _run_single_pipeline(
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
            )
            return result
        finally:
            await mcp_client.close()

    result = asyncio.run(_run_async())

    # E: Step 5: Generate report
    # C: 步骤 5: 生成报告
    print(f"\n{'=' * 60}")
    print("  Step 4: Generate Evaluation Report / 生成评估报告")
    print(f"{'=' * 60}")

    if result.get("success") and result.get("eval_result"):
        # E: Load gold map for report rendering
        # C: 加载金标准导图用于报告渲染
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
            print(f"\n  ✓ Report saved / 报告已保存: {report_path}")
        except Exception as e:
            print(f"\n  ✗ Report write failed / 报告写入失败: {e}")

        # E: Also save a copy to session dir
        # C: 在会话目录中也保存一份
        session_report_path = os.path.join(session_dir, "eval_report.md")
        try:
            with open(session_report_path, 'w', encoding='utf-8') as f:
                f.write(report)
        except Exception:
            pass

        # E: Show summary / C: 显示摘要
        show_summary = input("\n  Show report summary in terminal? / 在终端显示报告摘要？ [Y/n]: ").strip().lower()
        if show_summary in ('', 'y', 'yes'):
            print_results_table(result["eval_result"])

        print(f"\n{'=' * 60}")
        print("  Evaluation Complete! / 评估完成！")
        print(f"  Report file / 报告文件: {report_path}")
        print(f"  Session dir / 会话目录: {session_dir}")
        print(f"{'=' * 60}")
    else:
        print(f"\n  ✗ Evaluation failed / 评估失败: {result.get('error', 'Unknown error / 未知错误')}")


# ============================================================
# E: Batch mode entry
# C: 批量模式入口
# ============================================================
async def _run_batch(audio_dir: str, gold_dir: str, selected_methods: Optional[list[str]] = None,
                    auto_install: bool = False, ignore_missing: bool = False):
    """
    E: Batch evaluation mode entry — start BatchEvaluator
    C: 批量评估模式入口 — 启动 BatchEvaluator

    Args / 参数:
        audio_dir: Audio file directory / 音频文件目录
        gold_dir: Gold standard directory / 金标准文件目录
        selected_methods: Evaluation methods to run / 要运行的评估方法
        auto_install: Auto-install missing dependencies / 自动安装缺失依赖
        ignore_missing: Continue despite missing dependencies / 忽略缺失继续执行
    """
    print("=" * 60)
    print("  AI MindMap Batch Evaluation Mode v2.0")
    print("  AI MindMap 批量评估模式 v2.0")
    print("=" * 60)
    print(f"  Audio dir / 音频目录: {audio_dir}")
    print(f"  Gold dir / 金标准目录: {gold_dir}")
    print()

    methods = selected_methods or ['label', 'hierarchy', 'efficiency']

    # E: Check dependencies before proceeding
    # C: 依赖预检
    if not check_dependencies(methods, auto_install=auto_install, ignore_missing=ignore_missing):
        print("[!] Dependency check failed, exiting / 依赖检查未通过，退出")
        sys.exit(1)

    evaluator = BatchEvaluator(
        audio_dir=audio_dir,
        gold_dir=gold_dir,
        selected_methods=methods,
    )
    await evaluator.run_all()


# ============================================================
# E: Main entry point
# C: 主入口
# ============================================================
def main():
    """E: Main entry — parse args and dispatch to interactive or batch mode
    C: 主入口 — 解析参数并分发到交互式或批量模式"""
    parser = argparse.ArgumentParser(
        description="AI MindMap Quality Evaluation Tool / AI MindMap 质量评估工具"
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

    args = parser.parse_args()

    if args.batch:
        # E: Batch evaluation mode / C: 批量评估模式
        selected_methods = args.methods or ['label', 'hierarchy', 'efficiency']
        import asyncio
        asyncio.run(_run_batch(
            args.audio_dir, args.gold_dir, selected_methods,
            auto_install=args.auto_install, ignore_missing=args.ignore_missing_deps,
        ))
    else:
        # E: Interactive CLI mode (default) / C: 交互式 CLI 模式（默认）
        _interactive_workflow(auto_install=args.auto_install, ignore_missing=args.ignore_missing_deps)


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
C: AI MindMap 质量评估工具 — 统一入口 (交互式 CLI + 批量模式)
E: AI MindMap Quality Evaluation Tool — Unified Entry (Interactive CLI + Batch Mode)

用法 / Usage:
    cd /home/akku/ai-mindmap-agent
    python evaluation/run_evaluation.py            # 交互式 CLI / Interactive CLI
    python evaluation/run_evaluation.py --batch    # 批量评估模式 / Batch evaluation mode

工作流程 / Workflow:
    1. 提示用户选择评估方法（多选）/ Prompt user to select evaluation methods (multi-select)
    2. 自动检测 / 手动输入文件路径 / Auto-detect or manually enter file paths
    3. 执行评估（带进度条）/ Execute evaluation (with progress bar)
    4. 输出详细 Markdown 报告 / Output detailed Markdown report
"""
import sys
import os
import argparse

# C: 确保可以 import 项目根目录下的模块
# E: Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from evaluation.core.data_loader import DataLoader, MindMapData
from evaluation.core.aligner import HungarianAligner
from evaluation.utils.console_utils import (
    interactive_multiselect,
    prompt_file,
    prompt_float,
    prompt_str,
    auto_detect_files,
    ProgressTracker,
    print_results_table,
)
from evaluation.report.markdown_renderer import MarkdownReportRenderer


def _run_example_demo():
    """
    C: 示例演示模式 — 使用内置示例数据走通全流程，无需用户输入
    E: Example demo mode — runs full pipeline with built-in example data, no user input

    自动执行以下步骤 / Automatically executes:
    1. 加载金标准导图、核心概念、问题集等所有示例数据
    2. 对金标准节点 label 做轻微扰动以模拟生成导图
    3. 完整执行 label / hierarchy / qa / efficiency / multilingual / human_corr 评估
    4. 生成带 **example** 标记的 Markdown 评估报告
    """
    import json
    import copy
    import random
    import os
    from evaluation.core.data_loader import DataLoader
    from evaluation.core.aligner import HungarianAligner
    from evaluation.report.markdown_renderer import MarkdownReportRenderer

    print("=" * 60)
    print("  §0 示例演示模式 / Example Demo Mode")
    print("=" * 60)
    print("  使用内置示例数据自动执行完整评估流程")
    print("  Running full evaluation with built-in example data")
    print()

    # C: 固定配置参数 / E: Fixed config
    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    threshold = 0.70

    # =========================================================
    # C: 步骤 1 — 加载所有示例数据
    # E: Step 1 — Load all example data
    # =========================================================
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(base_dir), "evaluation", "data")

    # C: 金标准导图 / E: Gold standard map
    gold_path = os.path.join(data_dir, "gold", "gold_example.json")
    gold_map = DataLoader.from_map_file(gold_path)
    if gold_map is None:
        print("  ✗ 金标准加载失败，请确认 evaluation/data/gold/gold_example.json 存在")
        return
    print(f"  ✓ 金标准加载成功 / Gold loaded: {gold_map.node_count} 节点/nodes")

    # C: 核心概念集合 / E: Essential concepts
    concepts_path = os.path.join(data_dir, "concepts", "example_essential_concepts.json")
    essential_concepts = None
    if os.path.isfile(concepts_path):
        with open(concepts_path) as f:
            concepts_data = json.load(f)
        essential_concepts = concepts_data.get("concepts", [])
        print(f"  ✓ 核心概念加载成功 / Concepts loaded: {len(essential_concepts)} 项/items")

    # C: 生成模拟导图（对金标准节点 label 做轻微扰动）
    # E: Generate simulated map (slightly perturb gold node labels)
    print("  正在生成模拟导图 / Generating simulated map...")
    gen_dict = _generate_example_map(gold_map)
    gen_map = DataLoader.from_flat_dict(gen_dict)
    print(f"  ✓ 模拟导图已生成 / Simulated map generated: {gen_map.node_count} 节点/nodes")

    aligner = HungarianAligner(model_name=model_name, threshold=threshold)

    # =========================================================
    # C: 步骤 2 — 执行所有维度评估
    # E: Step 2 — Execute all dimension evaluations
    # =========================================================
    results = {}
    selected_dims = ["label", "hierarchy", "qa", "efficiency", "multilingual", "human_corr"]
    progress = ProgressTracker(total=len(selected_dims))

    # --- §1 节点标签质量 ---
    progress.start("节点标签质量 / Node Label Quality")
    try:
        from evaluation.label.eval_label import evaluate_label_quality
        label_result = evaluate_label_quality(gold_map, gen_map, aligner, essential_concepts)
        results["label"] = label_result.to_dict()
        print(f"    Node-F1: {label_result.node_f1:.4f}  Node-P: {label_result.node_precision:.4f}")
        progress.complete("节点标签质量 / Node Label Quality")
    except Exception as e:
        print(f"    [错误 / Error] {e}")
        progress.complete("节点标签质量 / Node Label Quality", status="失败 / Failed")

    # --- §2 层级结构 ---
    progress.start("层级结构正确率 / Hierarchy Accuracy")
    try:
        from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
        alignment = aligner.align(gold_map.nodes, gen_map.nodes)
        hier_result = evaluate_hierarchy_quality(gold_map, gen_map, alignment)
        results["hierarchy"] = hier_result.to_dict()
        print(f"    Edge-F1: {hier_result.edge_f1:.4f}  UAS: {hier_result.uas:.4f}")
        progress.complete("层级结构正确率 / Hierarchy Accuracy")
    except Exception as e:
        print(f"    [错误 / Error] {e}")
        progress.complete("层级结构正确率 / Hierarchy Accuracy", status="失败 / Failed")

    # --- §3 下游 QA ---
    progress.start("下游 QA 测试 / Downstream QA")
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
        print(f"    QA Retention: {qa_result.qa_retention:.4f}")
        progress.complete("下游 QA 测试 / Downstream QA")
    except Exception as e:
        print(f"    [错误 / Error] {e}")
        progress.complete("下游 QA 测试 / Downstream QA", status="失败 / Failed")

    # --- §4 效率与 STT ---
    progress.start("效率与 STT 保真度 / Efficiency & STT Fidelity")
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
                    })
        if os.path.isfile(terms_path):
            with open(terms_path) as f:
                kd = json.load(f)
            key_terms = kd.get("key_terms", [])
        eff_result = evaluate_efficiency(
            timing_logs=timing_logs,
            stt_text="这是一个示例转录文本，用于演示 STT 评估功能",
            ground_truth_text="这是一个示例转录文本，用于演示 STT 评估功能",
            key_terms=key_terms,
        )
        results["efficiency"] = eff_result.to_dict()
        print(f"    WER: {eff_result.wer:.4f}  KTRR: {eff_result.ktrr:.4f}")
        progress.complete("效率与 STT 保真度 / Efficiency & STT Fidelity")
    except Exception as e:
        print(f"    [错误 / Error] {e}")
        progress.complete("效率与 STT 保真度 / Efficiency & STT Fidelity", status="失败 / Failed")

    # --- §5 多语言与鲁棒性 ---
    progress.start("多语言与鲁棒性 / Multilingual & Robustness")
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
            mx_avg = {k: sum(d[k] for d in mixed_data)/len(mx_avg) for k in ["entity_recall","label_sim","pc_f1"]}

        multi_result = evaluate_multilingual(
            cn_results=cn_avg, en_results=en_avg, mixed_results=mx_avg,
            noise_test_results=noise_data,
        )
        results["multilingual"] = multi_result.to_dict()
        print(f"    max_delta_recall: {multi_result.max_delta_recall:.4f}")
        progress.complete("多语言与鲁棒性 / Multilingual & Robustness")
    except Exception as e:
        print(f"    [错误 / Error] {e}")
        progress.complete("多语言与鲁棒性 / Multilingual & Robustness", status="失败 / Failed")

    # --- §6 人工评估 ---
    progress.start("人工评估相关性 / Human Evaluation Correlation")
    try:
        human_path = os.path.join(data_dir, "human_scores", "example_human_scores.json")
        human_scores_list = None
        if os.path.isfile(human_path):
            with open(human_path) as f:
                hdata = json.load(f)
            human_scores_list = hdata.get("samples", [])
            print(f"  ✓ 人工评分数据加载成功: {len(human_scores_list)} 样本/samples")

        from evaluation.human_correlation.eval_human_correlation import evaluate_human_correlation
        # NOTE: Per-sample automated scores not available yet;
        # passing None avoids creating constant arrays from aggregate
        # values that would trigger ConstantInputWarning.
        auto_scores_list = None

        hc_result = evaluate_human_correlation(automated_scores=auto_scores_list, human_scores=human_scores_list)
        results["human_corr"] = hc_result.to_dict()
        print(f"    Pearson r: {hc_result.node_f1_readability_r:.4f}")
        progress.complete("人工评估相关性 / Human Evaluation Correlation")
    except Exception as e:
        print(f"    [错误 / Error] {e}")
        progress.complete("人工评估相关性 / Human Evaluation Correlation", status="失败 / Failed")

    # =========================================================
    # C: 步骤 3 — 生成带 **example** 标记的报告
    # E: Step 3 — Generate report with **example** markers
    # =========================================================
    print()
    print("=" * 60)
    print("  生成评估报告 / Generating Evaluation Report")
    print("=" * 60)

    config_info = {"pipeline": f"embedding={model_name}, threshold={threshold} (示例演示 / Example Demo)"}
    renderer = MarkdownReportRenderer(embedding_model=model_name, threshold=threshold)
    report = renderer.render(
        gold_map, gen_map, results,
        inclusion_list=selected_dims,
        config_info=config_info,
        example_mode=True,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join("evaluation", f"eval_report_example_{timestamp}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  ✓ 报告已保存 / Report saved: {report_path}")

    # =========================================================
    # C: 步骤 4 — 打印完成信息
    # E: Step 4 — Print completion info
    # =========================================================
    print()
    print("=" * 60)
    print("  示例演示已完成 / Example Demo Complete")
    print(f"  报告文件 / Report file: {report_path}")
    print("=" * 60)
    print()
    print("  📋 说明 / Notes:")
    print("    1. 演示使用内置示例数据，结果仅供参考")
    print("    1. Demo uses built-in example data, results are for reference only")
    print("    2. 报告中所有数值均标记为 **example**，以区别于正式评估")
    print("    2. All values in the report are marked **example** to distinguish from formal evaluations")
    print("    3. 上传真实数据后，通过交互式或批量模式获得正式评估结果")
    print("    3. Upload real data for formal evaluations via interactive or batch mode")
    print()


def _generate_example_map(gold_map) -> dict:
    import random
    import copy
    """
    C: 对金标准导图做轻微扰动，生成模拟的生成导图
    E: Slightly perturb the gold standard map to generate a simulated map

    扰动策略 / Perturbation strategy:
    - 30% 概率替换中文字符为相近字
    - 20% 概率删除或添加一个词
    - 保留节点结构和层级关系
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
                    # C: 替换为相近的中文字符 / E: Replace with nearby Chinese char
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
    """C: 将扁平节点列表构建为 G6 嵌套树格式 / E: Build nested tree from flat nodes"""
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
    # C: 排序子节点 / E: Sort children
    for nid, node in node_map.items():
        node["children"].sort(key=lambda x: x.get("label", ""))
    # C: 清理临时字段 / E: Clean up temporary fields
    for nid, node in node_map.items():
        for key in ["__note", "__note_en", "details", "metadata", "parent_id"]:
            node.pop(key, None)
    return root_nodes
def main():
    print("=" * 60)
    print("  AI MindMap 质量评估工具 v1.0 / AI MindMap Quality Evaluation Tool v1.0")
    print("=" * 60)

    # C: 步骤 1: 选择评估方法 / E: Step 1: Select evaluation methods
    # =========================================================
    available_metrics = {
        'example': '§0 示例演示模式 / Example Demo Mode (使用内置示例数据走通全流程)',
        'label': '§1 节点标签质量 / Node Label Quality (Node-P/R/F1, LabelSim, Entity Recall)',
        'hierarchy': '§2 层级结构正确率 / Hierarchy Accuracy (Edge-P/R/F1, UAS, nTED, PC-F1, LAR)',
        'qa': '§3 下游 QA 测试 / Downstream QA (需要预置问题集 / requires question set)',
        'efficiency': '§4 效率与 STT 保真度 / Efficiency & STT Fidelity (延迟/WER/KTRR, 需要计时日志 / requires timing logs)',
        'multilingual': '§5 多语言与鲁棒性 / Multilingual & Robustness (需要多语言测试集 / requires multilingual test sets)',
        'human_corr': '§6 人工评估相关性 / Human Evaluation Correlation (需要人工评分数据 / requires human scoring data)',
        'full': '§7 全量报告 / Full Report (汇总以上所有 + 综合评分 / summarize all + composite score)',
    }

    selected = interactive_multiselect("步骤 1: 选择评估方法 / Step 1: Select Evaluation Methods", available_metrics)

    # C: 示例演示模式 — 独立处理，自动走完全部维度
    # E: Example demo mode — standalone, runs all dimensions automatically
    if 'example' in selected:
        _run_example_demo()
        return

    if 'full' in selected:
        selected = [k for k in available_metrics if k != 'full']

    if not selected:
        print("\n[!] 未选择任何评估方法，退出。/ No evaluation method selected, exiting.")
        sys.exit(0)

    print(f"\n  已选择 / Selected: {', '.join(selected)}")

    # C: 步骤 2: 输入文件检测 / E: Step 2: Input File Detection
    # =========================================================
    print(f"\n{'=' * 60}")
    print("  步骤 2: 输入文件检测 / Step 2: Input File Detection")
    print(f"{'=' * 60}")

    gold_path, gen_path = auto_detect_files()

    need_gold = any(k in selected for k in ('label', 'hierarchy'))
    need_gen = True

    if need_gold:
        gold_path = prompt_file("金标准导图 / Gold Tree", gold_path, required=True)
    else:
        print("\n[金标准导图 / Gold Tree] 当前选择无需金标准，跳过。/ Gold standard not required for current selection, skipping.")

    gen_path = prompt_file("生成导图 / Generated Map", gen_path, required=True)

    # C: 加载数据 / E: Load data
    gold_map = None
    if gold_path:
        gold_map = DataLoader.from_map_file(gold_path)
        if gold_map:
            print(f"  ✓ 金标准加载成功 / Gold loaded successfully: {gold_map.node_count} 节点/nodes, {gold_map.link_count} 边/edges")
        else:
            print(f"  ✗ 金标准加载失败 / Gold load failed: {gold_path}")
            if need_gold:
                print("  [!] 金标准为必需，退出。/ Gold standard required, exiting.")
                sys.exit(1)

    gen_map = None
    if gen_path:
        gen_map = DataLoader.from_map_file(gen_path)
        if gen_map:
            print(f"  ✓ 生成导图加载成功 / Generated map loaded: {gen_map.node_count} 节点/nodes, {gen_map.link_count} 边/edges")
        else:
            print(f"  ✗ 生成导图加载失败 / Generated map load failed: {gen_path}")
            sys.exit(1)

    if gen_map is None or gen_map.node_count == 0:
        print("\n[!] 生成导图为空，退出。/ Generated map is empty, exiting.")
        sys.exit(1)

    # C: 额外参数 / E: Additional parameters
    essential_concepts = None
    if 'label' in selected:
        print()
        print("  [Entity Recall] 核心概念集合 Es / Essential Concepts Set")
        print("  " + "=" * 52)
        print("  输入概念列表（逗号分隔），用于 §1.4 Entity Recall 评估。")
        print("  Enter a comma-separated list of concepts for §1.4 Entity Recall.")
        print("  建议使用 evaluation/data/concepts/ 下的标准 Es.json 文件内容。")
        print("  Recommended: use content from a standard Es.json file in evaluation/data/concepts/.")
        print("  留空则自动从金标准节点 label 提取作为后备。")
        print("  Leave empty to auto-extract from gold standard node labels as fallback.")
        print("  " + "=" * 52)
        raw = input("  > 概念 / Concepts: ").strip()
        if raw:
            essential_concepts = [c.strip() for c in raw.split(',') if c.strip()]
            print(f"  已接收 {len(essential_concepts)} 个概念 / Received {len(essential_concepts)} concepts")
        else:
            print("  未输入，将使用金标准节点 label 自动提取")
            print("  No input, will auto-extract from gold standard node labels")

    # C: 配置共享基础设施 / E: Configure shared infrastructure
    # =========================================================
    print(f"\n{'=' * 60}")
    print("  评估配置 / Evaluation Configuration")
    print(f"{'=' * 60}")

    model_name = prompt_str("Embedding 模型名称 / Embedding Model Name",
                            default="paraphrase-multilingual-MiniLM-L12-v2")
    threshold = prompt_float("相似度阈值 τ / Similarity Threshold τ", default=0.70, min_val=0.0, max_val=1.0)

    aligner = HungarianAligner(model_name=model_name, threshold=threshold)

    # C: 步骤 3: 执行评估 / E: Step 3: Execute Evaluation
    # =========================================================
    print(f"\n{'=' * 60}")
    print("  步骤 3: 执行评估 / Step 3: Execute Evaluation")
    print(f"{'=' * 60}")

    progress = ProgressTracker(total=len(selected))
    results = {}

    # C: --- §1 节点标签质量 / §1 Node Label Quality ---
    if 'label' in selected and gold_map:
        progress.start('label')
        try:
            from evaluation.label.eval_label import evaluate_label_quality
            label_result = evaluate_label_quality(gold_map, gen_map, aligner, essential_concepts)
            results['label'] = label_result.to_dict()
            print(f"    Node-F1: {label_result.node_f1:.4f}  "
                  f"Node-P: {label_result.node_precision:.4f}  "
                  f"Node-R: {label_result.node_recall:.4f}")
            print(f"    LabelSim: {label_result.label_sim:.4f}  "
                  f"Entity Recall: {label_result.entity_recall:.4f}")
            progress.complete('节点标签质量 / Node Label Quality')
        except Exception as e:
            print(f"    [错误 / Error] {e}")
            progress.complete('节点标签质量 / Node Label Quality', status='失败 / Failed')

    elif 'label' in selected and not gold_map:
        print("\n  [跳过 / Skip] §1 需要金标准树。/ §1 requires gold tree.")

    # C: --- §2 层级结构正确率 / §2 Hierarchy Structure Accuracy ---
    if 'hierarchy' in selected and gold_map:
        progress.start('hierarchy')
        try:
            alignment = None
            if 'label' in results:
                # 复用 label 评估的对齐结果
                label_metrics_module = results['label']
                from evaluation.core.aligner import AlignmentResult
                # 如果没有缓存 alignment，需要重新对齐
                alignment = aligner.align(gold_map.nodes, gen_map.nodes)
            else:
                alignment = aligner.align(gold_map.nodes, gen_map.nodes)

            from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality
            hier_result = evaluate_hierarchy_quality(gold_map, gen_map, alignment)
            results['hierarchy'] = hier_result.to_dict()
            print(f"    Edge-F1: {hier_result.edge_f1:.4f}  "
                  f"UAS: {hier_result.uas:.4f}  "
                  f"nTED: {hier_result.nted:.4f}" if hier_result.nted is not None else f"nTED: N/A")
            progress.complete('层级结构正确率 / Hierarchy Accuracy')
        except Exception as e:
            print(f"    [错误 / Error] {e}")
            import traceback
            traceback.print_exc()
            progress.complete('层级结构正确率 / Hierarchy Accuracy', status='失败 / Failed')

    elif 'hierarchy' in selected and not gold_map:
        print("\n  [跳过 / Skip] §2 需要金标准树。/ §2 requires gold tree.")

    # C: --- §3 下游 QA / §3 Downstream QA ---
    if 'qa' in selected:
        progress.start('qa')
        print()
        print("  [§3 下游 QA / Downstream QA]")
        print("  " + "=" * 52)
        print("  需要上传预置问答问题集（questions_*.json）至 evaluation/data/questions/")
        print("  Requires uploading a question set (questions_*.json) to evaluation/data/questions/")
        print("  参见示例文件 / See example: evaluation/data/questions/example_questions.json")
        print("  " + "=" * 52)
        try:
            from evaluation.qa.eval_qa import QAEvaluator
            qa_eval = QAEvaluator()
            # C: 需要 transcript 和 questions，目前使用默认值执行（不中断）
            # E: Requires transcript and questions, using defaults (non-blocking)
            qa_result = qa_eval.evaluate("", gen_map.nodes, [])
            results['qa'] = qa_result.to_dict()
            progress.complete('下游 QA 测试 / Downstream QA', status='已执行（需预置问题集）/ Executed (question set required)')
        except Exception as e:
            print(f"    [错误 / Error] {e}")
            progress.complete('下游 QA 测试 / Downstream QA', status='失败 / Failed')

    # C: --- §4 效率与 STT / §4 Efficiency & STT ---
    if 'efficiency' in selected:
        progress.start('efficiency')
        print()
        print("  [§4 效率与 STT / Efficiency & STT]")
        print("  " + "=" * 52)
        print("  可上传以下文件至 evaluation/data/timing/ 以获得完整评估：")
        print("  Upload the following to evaluation/data/timing/ for full evaluation:")
        print("    1. timing_logs.json — 分阶段计时日志 / Per-stage timing logs")
        print("    2. reference_transcript.txt — 人工转写标准文本 / Reference transcript")
        print("    3. key_terms.json — 关键术语列表 / Key terms list")
        print("  未提供时使用默认值运行，不中断流程。")
        print("  Runs with defaults if not provided, will not interrupt.")
        print("  参见示例文件 / See examples: evaluation/data/timing/")
        print("  " + "=" * 52)
        try:
            from evaluation.efficiency.eval_efficiency import evaluate_efficiency
            eff_result = evaluate_efficiency()
            results['efficiency'] = eff_result.to_dict()
            progress.complete('效率与 STT 保真度 / Efficiency & STT Fidelity', status='已执行（默认值）/ Executed (defaults)')
        except Exception as e:
            print(f"    [错误 / Error] {e}")
            progress.complete('效率与 STT 保真度 / Efficiency & STT Fidelity', status='失败 / Failed')

    # C: --- §5 多语言 / §5 Multilingual ---
    if 'multilingual' in selected:
        progress.start('multilingual')
        print()
        print("  [§5 多语言与鲁棒性 / Multilingual & Robustness]")
        print("  " + "=" * 52)
        print("  可上传以下文件至 evaluation/data/multilingual/：")
        print("  Upload the following to evaluation/data/multilingual/:")
        print("    1. cn_results.json — 纯中文测试集结果 / Chinese-only results")
        print("    2. en_results.json — 纯英文测试集结果 / English-only results")
        print("    3. mixed_results.json — 中英混合测试集结果 / Mixed results")
        print("    4. noise_results.json — 噪声测试结果 / Noise test results")
        print("  未提供时使用默认值运行，不中断流程。")
        print("  Runs with defaults if not provided, will not interrupt.")
        print("  参见示例文件 / See examples: evaluation/data/multilingual/")
        print("  " + "=" * 52)
        try:
            from evaluation.multilingual.eval_multilingual import evaluate_multilingual
            multi_result = evaluate_multilingual()
            results['multilingual'] = multi_result.to_dict()
            progress.complete('多语言与鲁棒性 / Multilingual & Robustness', status='已执行（默认值）/ Executed (defaults)')
        except Exception as e:
            print(f"    [错误 / Error] {e}")
            progress.complete('多语言与鲁棒性 / Multilingual & Robustness', status='失败 / Failed')

    # C: --- §6 人工评估 / §6 Human Evaluation ---
    if 'human_corr' in selected:
        progress.start('human_corr')
        print()
        print("  [§6 人工评估对齐 / Human Evaluation Alignment]")
        print("  " + "=" * 52)
        print("  需要上传人工评分数据至 evaluation/data/human_scores/")
        print("  Requires uploading human scoring data to evaluation/data/human_scores/")
        print("  包含 / Contains: readability, hierarchy_intuitiveness, information_density 等维度")
        print("  参见示例文件 / See example: evaluation/data/human_scores/example_human_scores.json")
        print("  未提供时使用默认值运行，不中断流程。")
        print("  Runs with defaults if not provided, will not interrupt.")
        print("  " + "=" * 52)
        try:
            from evaluation.human_correlation.eval_human_correlation import evaluate_human_correlation
            hc_result = evaluate_human_correlation()
            results['human_corr'] = hc_result.to_dict()
            progress.complete('人工评估相关性 / Human Evaluation Correlation', status='已执行（默认值）/ Executed (defaults)')
        except Exception as e:
            print(f"    [错误 / Error] {e}")
            progress.complete('人工评估相关性 / Human Evaluation Correlation', status='失败 / Failed')

    # C: 步骤 4: 生成报告 / E: Step 4: Generate Report
    # =========================================================
    print(f"\n{'=' * 60}")
    print("  步骤 4: 生成评估报告 / Step 4: Generate Evaluation Report")
    print(f"{'=' * 60}")

    config_info = {
        'pipeline': f"embedding={model_name}, τ={threshold}",
    }

    renderer = MarkdownReportRenderer(embedding_model=model_name, threshold=threshold)
    report = renderer.render(gold_map, gen_map, results,
                             inclusion_list=selected,
                             config_info=config_info)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join("evaluation", f"eval_report_{timestamp}.md")
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n  ✓ 报告已保存 / Report saved: {report_path}")
    except Exception as e:
        print(f"\n  ✗ 报告写入失败 / Report write failed: {e}")

    # C: 终端显示摘要 / E: Show summary in terminal
    show_summary = input("\n  在终端显示报告摘要？/ Show report summary in terminal? [Y/n]: ").strip().lower()
    if show_summary in ('', 'y', 'yes'):
        print_results_table(results)

    # C: 输出摘要指标 / E: Output summary metrics
    print(f"\n{'=' * 60}")
    print("  评估完成！/ Evaluation Complete!")
    print(f"  报告文件 / Report file: {report_path}")
    print(f"{'=' * 60}")

    # C: 推荐下一步 / E: Recommended next steps
    print("\n  📋 推荐下一步 / Recommended Next Steps:")
    if not gold_path:
        print("    1. 将金标准导图放入 evaluation/data/gold/ 目录，以便自动检测 / Place gold map in evaluation/data/gold/ for auto-detection")
    print("    2. 查看生成的 Markdown 评估报告 / Review the generated Markdown evaluation report")
    print("    3. 上传金标准树集合后，可执行完整评估并获得诊断建议 / Upload gold tree set for complete evaluation with diagnostic suggestions")
    print()


# C: 批量评估模式入口 / E: Batch evaluation mode entry
def _run_batch(audio_dir: str, gold_dir: str):
    """
    C: 批量评估模式入口 — 启动 BatchEvaluator
    E: Batch evaluation mode entry — start BatchEvaluator
    """
    import asyncio
    from evaluation.batch_evaluate import BatchEvaluator

    print("=" * 60)
    print("  AI MindMap 批量评估模式 v1.0")
    print("  AI MindMap Batch Evaluation Mode")
    print("=" * 60)
    print(f"  音频目录 / Audio dir: {audio_dir}")
    print(f"  金标准目录 / Gold dir: {gold_dir}")
    print()

    evaluator = BatchEvaluator(
        audio_dir=audio_dir,
        gold_dir=gold_dir,
    )
    asyncio.run(evaluator.run_all())


if __name__ == '__main__':
    # C: 解析命令行参数 / E: Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI MindMap 质量评估工具 / AI MindMap Quality Evaluation Tool"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量评估模式 / Batch evaluation mode",
    )
    parser.add_argument(
        "--audio-dir",
        type=str,
        default="evaluation/data/audio",
        help="音频文件目录（--batch 模式下使用）/ Audio file directory (used in --batch mode)",
    )
    parser.add_argument(
        "--gold-dir",
        type=str,
        default="evaluation/data/gold",
        help="金标准文件目录（--batch 模式下使用）/ Gold standard directory (used in --batch mode)",
    )

    args = parser.parse_args()

    if args.batch:
        # C: 批量评估模式 / E: Batch evaluation mode
        _run_batch(args.audio_dir, args.gold_dir)
    else:
        # C: 交互式 CLI 模式（默认）/ E: Interactive CLI mode (default)
        main()


# C: 示例演示模式入口 / E: Example demo mode entry
