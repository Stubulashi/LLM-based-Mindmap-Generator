"""
E: §4 Generation Efficiency & STT Fidelity — Auto-instrumented Pipeline Timing
C: §4 生成效率与 STT 保真度 — 自动仪表化的管线计时

Evaluation_Schema.md §4.1~4.2

Features / 特性:
  - 4.1 End-to-End Latency Measurement (P50/P95) / 端到端延迟测量
  - Built-in performance standards comparison / 内置性能标准对比
  - Custom standards support (JSON file) / 自定义标准支持
  - Audio-only input (no gold standard required) / 仅需音频（无需金标准）
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable
import math
import json
import os
import time as time_module

# E: Lazy imports — auto-degrade when external libraries missing
# C: 延迟导入 — 外部库缺失时自动降级
_JIWER_AVAILABLE = False
_JIEBA_AVAILABLE = False
_SCIPY_AVAILABLE = False

try:
    import jiwer
    _JIWER_AVAILABLE = True
except ImportError:
    pass

try:
    import jieba
    _JIEBA_AVAILABLE = True
except ImportError:
    pass

try:
    import scipy
    from scipy.stats import pearsonr, spearmanr
    _SCIPY_AVAILABLE = True
except ImportError:
    pass


# ============================================================
# E: Default efficiency standards (embedded fallback)
# C: 默认效率标准（内嵌后备）
# ============================================================
DEFAULT_STANDARDS = {
    "stt":      {"p50_target": 30.0, "p95_target": 60.0},
    "concept":  {"p50_target": 5.0,  "p95_target": 10.0},
    "hierarchy":{"p50_target": 5.0,  "p95_target": 10.0},
    "delta":    {"p50_target": 5.0,  "p95_target": 10.0},
    "polish":   {"p50_target": 3.0,  "p95_target": 5.0},
    "map_gen":  {"p50_target": 18.0, "p95_target": 35.0},
    "total":    {"p50_target": 48.0, "p95_target": 95.0},
}


# ============================================================
# E: EfficiencyStandards — load from file or use defaults
# C: 效率标准 — 从文件加载或使用默认值
# ============================================================
class EfficiencyStandards:
    """
    E: Performance standards for pipeline stage timing
    C: 管线阶段计时的性能标准

    Usage / 用法:
        standards = EfficiencyStandars()  # defaults
        standards = EfficiencyStandards("path/to/custom.json")  # custom
    """

    def __init__(self, standards_path: Optional[str] = None):
        self.raw: dict = dict(DEFAULT_STANDARDS)
        if standards_path and os.path.isfile(standards_path):
            try:
                with open(standards_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data.get("standards", []):
                    stage = entry.get("stage")
                    if stage and "p50_target" in entry and "p95_target" in entry:
                        self.raw[stage] = {
                            "p50_target": float(entry["p50_target"]),
                            "p95_target": float(entry["p95_target"]),
                        }
                print(f"[Efficiency] Loaded standards from / 已从文件加载标准: {standards_path}")
            except Exception as e:
                print(f"[Efficiency] Failed to load standards / 加载标准失败: {e}, using defaults / 使用默认值")

    def get_p50_target(self, stage: str) -> float:
        return self.raw.get(stage, {}).get("p50_target", float('inf'))

    def get_p95_target(self, stage: str) -> float:
        return self.raw.get(stage, {}).get("p95_target", float('inf'))

    def check_p50(self, stage: str, value: float) -> tuple[bool, float]:
        """
        E: Check if P50 meets target / C: 检查 P50 是否达标
        Returns: (passed, target) / 返回：(是否达标, 目标值)
        """
        target = self.get_p50_target(stage)
        return value <= target, target

    def check_p95(self, stage: str, value: float) -> tuple[bool, float]:
        target = self.get_p95_target(stage)
        return value <= target, target

    def to_dict(self) -> dict:
        return dict(self.raw)


# ============================================================
# E: TimingSnapshot — timing data for a single pipeline run
# C: 计时快照 — 单次管线运行的计时数据
# ============================================================
@dataclass
class TimingSnapshot:
    """
    E: Captures start/end timestamps for each pipeline stage
    C: 捕获每个管线阶段的起止时间戳
    """
    stage_name: str
    start_time: float
    end_time: float

    @property
    def duration(self) -> float:
        return max(0, self.end_time - self.start_time)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage_name,
            "start": round(self.start_time, 4),
            "end": round(self.end_time, 4),
            "duration": round(self.duration, 4),
        }


# ============================================================
# E: run_timed_pipeline — wrap an async pipeline with timing
# C: run_timed_pipeline — 用计时包装异步管线
# ============================================================
async def run_timed_pipeline(
    stt_coro: Awaitable,
    map_gen_coro: Awaitable,
) -> tuple[dict, list[TimingSnapshot]]:
    """
    E: Run pipeline stages with automatic timing instrumentation
    C: 运行管线阶段并自动采集计时数据

    Args / 参数:
        stt_coro: Async coroutine for Speech-to-Text / STT 异步协程
        map_gen_coro: Async coroutine for mind map generation / 导图生成异步协程

    Returns / 返回:
        (pipeline_results_dict, timing_snapshots_list) / (管线结果字典, 计时快照列表)
    """
    snapshots = []
    pipeline_results = {}

    # E: Stage 1 — STT / C: 阶段 1 — 语音转录
    t0 = time_module.perf_counter()
    stt_result = await stt_coro
    t1 = time_module.perf_counter()
    snapshots.append(TimingSnapshot("stt", t0, t1))
    pipeline_results["stt_result"] = stt_result

    # E: Stage 2 — Map Generation (concept + hierarchy + delta + polish)
    # C: 阶段 2 — 导图生成（概念+层级+Delta+润色合并）
    t2 = time_module.perf_counter()
    map_result = await map_gen_coro
    t3 = time_module.perf_counter()
    snapshots.append(TimingSnapshot("map_gen", t2, t3))
    pipeline_results["map_result"] = map_result

    # E: Total snapshot (overall)
    # C: 总计时快照
    snapshots.append(TimingSnapshot("total", t0, t3))

    return pipeline_results, snapshots


# ============================================================
# E: Data structures
# C: 数据结构
# ============================================================
@dataclass
class EfficiencyMetrics:
    """
    E: Efficiency & STT evaluation results with standards comparison
    C: 效率与 STT 评估结果（含标准对比）
    """

    # E: 4.1 Latency / C: 4.1 延迟
    t_total_p50: float = 0.0
    t_total_p95: float = 0.0
    stt_ratio: float = 0.0
    staged_timing: dict = field(default_factory=dict)
    num_repetitions: int = 1

    # E: Per-stage standards comparison / C: 各阶段标准对比
    standards_comparison: dict = field(default_factory=dict)
    standards_used: str = "default"

    # E: 4.2 STT Quality / C: 4.2 STT 质量
    wer: float = 0.0
    ktrr: float = 0.0
    num_stt_samples: int = 0

    # E: 4.2.3 Correlation analysis / C: 4.2.3 关联分析
    correlation_r: float = 0.0
    correlation_rho: float = 0.0
    correlation_interpretation: str = ""

    # E: Dependency availability / C: 依赖可用状态
    wer_method: str = "unavailable"
    ktrr_method: str = "unavailable"

    # E: Raw timing snapshots for debugging / C: 原始计时快照（用于调试）
    raw_timing_logs: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            't_total_p50': round(self.t_total_p50, 2),
            't_total_p95': round(self.t_total_p95, 2),
            'stt_ratio': round(self.stt_ratio, 3),
            'staged_timing': self.staged_timing,
            'num_repetitions': self.num_repetitions,
            'standards_comparison': self.standards_comparison,
            'standards_used': self.standards_used,
            'wer': round(self.wer, 4),
            'ktrr': round(self.ktrr, 4),
            'num_stt_samples': self.num_stt_samples,
            'correlation_r': round(self.correlation_r, 4),
            'correlation_rho': round(self.correlation_rho, 4),
            'correlation_interpretation': self.correlation_interpretation,
            'wer_method': self.wer_method,
            'ktrr_method': self.ktrr_method,
            'raw_timing_logs': self.raw_timing_logs,
        }


# ============================================================
# E: Helper functions
# C: 辅助函数
# ============================================================
def _compute_percentile(values: list[float], pct: float) -> float:
    """E: Manually compute percentile (no numpy dependency)
    C: 手动计算百分位数（无 numpy 依赖）"""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * pct / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def _edit_distance(a: str, b: str) -> int:
    """E: Levenshtein edit distance / C: Levenshtein 编辑距离"""
    if not a:
        return len(b)
    if not b:
        return len(a)
    m, n = len(a), len(b)
    if m > n:
        a, b, m, n = b, a, n, m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[n]


# ============================================================
# E: 4.2.2 KTRR — Key Term Retention Rate
# C: 4.2.2 KTRR — 关键术语保留率
# ============================================================
def _compute_ktrr(key_terms: list[str], stt_text: str) -> float:
    """
    E: Compute Key Term Retention Rate
       Matching strategy: 1-character edit distance tolerance (Chinese fuzzy matching)
    C: 计算关键术语保留率
       匹配策略：允许 1 字符编辑距离的容错（中文容错）
    """
    if not key_terms or not stt_text:
        return 0.0
    matched = 0
    stt_lower = stt_text.lower()
    for term in key_terms:
        term_lower = term.lower()
        if term_lower in stt_lower:
            matched += 1
            continue
        found = False
        for i in range(len(stt_lower) - len(term_lower) + 1):
            window = stt_lower[i:i + len(term_lower)]
            if _edit_distance(term_lower, window) <= 1:
                found = True
                break
        if found:
            matched += 1
    return matched / len(key_terms) if key_terms else 0.0


# ============================================================
# E: 4.2.1 WER — Word Error Rate
# C: 4.2.1 WER — 词错率
# ============================================================
def _compute_wer(stt_text: str, ground_truth_text: str) -> tuple[float, str]:
    """
    E: Compute Word Error Rate
       Chinese text segmented by jieba first; English text computed directly
    C: 计算词错率
       中文文本先通过 jieba 分词再计算；英文文本直接计算
    """
    if not ground_truth_text:
        return 1.0, "empty_ground_truth"
    if not stt_text:
        return 1.0, "empty_stt"
    if not _JIWER_AVAILABLE:
        return 0.0, "jiwer_unavailable"
    try:
        zh_count = sum(1 for ch in ground_truth_text if '\u4e00' <= ch <= '\u9fff')
        is_chinese = zh_count > len(ground_truth_text) * 0.3
        if is_chinese and _JIEBA_AVAILABLE:
            stt_seg = " ".join(jieba.cut(stt_text))
            gt_seg = " ".join(jieba.cut(ground_truth_text))
            wer_val = jiwer.wer(gt_seg, stt_seg)
            method = "jieba_segmented"
        else:
            wer_val = jiwer.wer(ground_truth_text, stt_text)
            method = "direct"
        wer_val = max(0.0, min(1.0, wer_val))
        return wer_val, method
    except Exception as e:
        print(f"[Efficiency] WER compute failed / WER 计算失败: {e}")
        return 0.0, "error"


# ============================================================
# E: 4.1 — Latency computation from timing snapshots
# C: 4.1 — 从计时快照计算延迟
# ============================================================
def _compute_latency(timing_logs: list[dict]) -> dict:
    """
    E: Compute P50/P95 from per-stage timing logs
    C: 从各阶段计时日志计算 P50/P95
    """
    if not timing_logs:
        return {"t_total_p50": 0.0, "t_total_p95": 0.0, "stt_ratio": 0.0, "staged_timing": {}}

    stage_durations: dict[str, list[float]] = {}
    for log in timing_logs:
        stage = log.get('stage', 'unknown')
        duration = log.get('duration', 0)
        if stage not in stage_durations:
            stage_durations[stage] = []
        stage_durations[stage].append(duration)

    staged_timing = {}
    total_p50 = 0.0
    total_p95 = 0.0
    stt_durations = stage_durations.get('stt', [])

    for stage, durations in stage_durations.items():
        p50 = _compute_percentile(durations, 50)
        p95 = _compute_percentile(durations, 95)
        staged_timing[stage] = {"p50": round(p50, 2), "p95": round(p95, 2), "samples": len(durations)}
        if stage not in ('stt', 'total'):
            total_p50 += p50
            total_p95 += p95

    if stt_durations:
        stt_p50 = _compute_percentile(stt_durations, 50)
        stt_p95 = _compute_percentile(stt_durations, 95)
        total_p50 += stt_p50
        total_p95 += stt_p95

    stt_ratio = 0.0
    if total_p50 > 0 and stt_durations:
        stt_p50 = _compute_percentile(stt_durations, 50)
        stt_ratio = stt_p50 / total_p50

    return {"t_total_p50": total_p50, "t_total_p95": total_p95, "stt_ratio": stt_ratio, "staged_timing": staged_timing}


# ============================================================
# E: 4.2.3 — STT-to-Map correlation analysis
# C: 4.2.3 — STT-导图关联分析
# ============================================================
def _compute_correlation(
    wer_scores: list[float],
    entity_recall_scores: list[float],
) -> tuple[float, float, str]:
    """
    E: Analyze correlation between WER and Entity Recall
    C: 分析 WER 与 Entity Recall 之间的相关性
    """
    if not _SCIPY_AVAILABLE:
        return 0.0, 0.0, "scipy not installed / scipy 未安装"
    if len(wer_scores) < 3 or len(entity_recall_scores) < 3:
        return 0.0, 0.0, "insufficient samples, need at least 3 / 样本不足，至少需要 3 个"
    if len(wer_scores) != len(entity_recall_scores):
        return 0.0, 0.0, "sample count mismatch / 样本数不匹配"
    try:
        r, _ = pearsonr(wer_scores, entity_recall_scores)
        rho, _ = spearmanr(wer_scores, entity_recall_scores)
        if abs(rho) > 0.7:
            interpretation = "STT quality is a key bottleneck, prioritize STT optimization / STT 质量是重要瓶颈，应优先优化 STT 模块"
        elif abs(rho) < 0.3:
            interpretation = "Pipeline has inherent STT error tolerance / 管线自身具备一定的 STT 容错能力"
        else:
            interpretation = "Moderate correlation between STT quality and map quality / STT 质量与导图质量存在中等相关"
        return float(r), float(rho), interpretation
    except Exception as e:
        return 0.0, 0.0, f"computation failed / 计算失败: {e}"


# ============================================================
# E: Standards comparison
# C: 标准对比
# ============================================================
def _compare_with_standards(
    staged_timing: dict,
    standards: EfficiencyStandards,
) -> dict:
    """
    E: Compare each stage's P50/P95 against standards
    C: 将各阶段 P50/P95 与标准对比
    """
    comparison = {}
    for stage, timing in staged_timing.items():
        p50 = timing.get("p50", 0)
        p95 = timing.get("p95", 0)
        p50_ok, p50_target = standards.check_p50(stage, p50)
        p95_ok, p95_target = standards.check_p95(stage, p95)
        comparison[stage] = {
            "p50": p50,
            "p50_target": p50_target,
            "p50_passed": p50_ok,
            "p50_status": "✅ PASS" if p50_ok else "❌ FAIL",
            "p95": p95,
            "p95_target": p95_target,
            "p95_passed": p95_ok,
            "p95_status": "✅ PASS" if p95_ok else "❌ FAIL",
        }
    return comparison


# ============================================================
# E: Main entry
# C: 主入口
# ============================================================
def evaluate_efficiency(
    timing_snapshots: Optional[list[dict]] = None,
    stt_text: Optional[str] = None,
    ground_truth_text: Optional[str] = None,
    key_terms: Optional[list[str]] = None,
    entity_recall_scores: Optional[list[float]] = None,
    wer_scores_for_correlation: Optional[list[float]] = None,
    standards: Optional[EfficiencyStandards] = None,
    num_repetitions: int = 1,
) -> EfficiencyMetrics:
    """
    E: Evaluate generation efficiency & STT fidelity with standards comparison
    C: 评估生成效率与 STT 保真度（含标准对比）

    Args / 参数:
        timing_snapshots: Raw timing snapshots [{stage, start, end, duration}, ...]
                          原始计时快照
        stt_text: STT transcript text / STT 转录文本
        ground_truth_text: Ground-truth transcript / 人工转写标准文本
        key_terms: Key term list / 关键术语列表
        entity_recall_scores: Entity Recall scores per sample (for correlation)
        wer_scores_for_correlation: WER values per sample (for correlation)
        standards: EfficiencyStandards object / 效率标准对象
        num_repetitions: Number of pipeline repetitions / 管线重复次数

    Returns / 返回:
        EfficiencyMetrics
    """
    if standards is None:
        standards = EfficiencyStandards()

    # E: 4.1 Latency from snapshots / C: 4.1 从快照计算延迟
    latency = _compute_latency(timing_snapshots or [])

    # E: Standards comparison / C: 标准对比
    standards_comparison = _compare_with_standards(latency["staged_timing"], standards)

    # E: 4.2.1 WER / C: 4.2.1 WER
    wer_val = 0.0
    wer_method = "unavailable"
    if stt_text and ground_truth_text:
        wer_val, wer_method = _compute_wer(stt_text, ground_truth_text)

    # E: 4.2.2 KTRR / C: 4.2.2 KTRR
    ktrr_val = 0.0
    ktrr_method = "unavailable"
    if key_terms and stt_text:
        ktrr_val = _compute_ktrr(key_terms, stt_text)
        ktrr_method = "fuzzy_1char"
    elif key_terms:
        ktrr_method = "stt_text required / 待提供STT文本"

    # E: 4.2.3 Correlation / C: 4.2.3 关联分析
    r_val, rho_val, interpretation = _compute_correlation(
        wer_scores_for_correlation or [],
        entity_recall_scores or [],
    )

    return EfficiencyMetrics(
        t_total_p50=latency["t_total_p50"],
        t_total_p95=latency["t_total_p95"],
        stt_ratio=latency["stt_ratio"],
        staged_timing=latency["staged_timing"],
        num_repetitions=num_repetitions,
        standards_comparison=standards_comparison,
        standards_used="custom" if standards and os.path.isfile(getattr(standards, 'path', '')) else "default",
        wer=wer_val,
        ktrr=ktrr_val,
        num_stt_samples=1 if stt_text else 0,
        correlation_r=r_val,
        correlation_rho=rho_val,
        correlation_interpretation=interpretation,
        wer_method=wer_method,
        ktrr_method=ktrr_method,
        raw_timing_logs=timing_snapshots or [],
    )
