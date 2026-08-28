"""
E: Threshold definitions — excellent/good/needs-improvement boundaries for all metrics
C: 阈值定义 — 所有指标的优秀/良好/需改进边界值
"""
from dataclasses import dataclass
from enum import Enum


class Grade(Enum):
    EXCELLENT = "🏆 Excellent / 优秀"
    GOOD = "👍 Good / 良好"
    NEEDS_IMPROVEMENT = "⚠️ Needs Improvement / 需改进"


@dataclass
class ThresholdBand:
    """E: Threshold band — lower bounds for excellent and good / C: 阈值带 — 含优秀和良好的下限"""
    excellent: float
    good: float
    higher_is_better: bool = True

    def grade(self, value: float) -> Grade:
        if self.higher_is_better:
            if value >= self.excellent:
                return Grade.EXCELLENT
            elif value >= self.good:
                return Grade.GOOD
            else:
                return Grade.NEEDS_IMPROVEMENT
        else:
            # lower is better (e.g., nTED, WER)
            if value <= self.excellent:
                return Grade.EXCELLENT
            elif value <= self.good:
                return Grade.GOOD
            else:
                return Grade.NEEDS_IMPROVEMENT

    def pass_fail(self, value: float) -> str:
        """E: Return ✅PASS/❌FAIL / C: 返回 ✅PASS/❌FAIL"""
        g = self.grade(value)
        if g in (Grade.EXCELLENT, Grade.GOOD):
            return "✅ PASS"
        return "❌ FAIL"


# E: §1 Node Label Quality / C: §1 节点标签质量
NODE_F1 = ThresholdBand(excellent=0.85, good=0.70)
NODE_P = ThresholdBand(excellent=0.80, good=0.65)
NODE_R = ThresholdBand(excellent=0.85, good=0.70)
LABEL_SIM = ThresholdBand(excellent=0.85, good=0.75)
ENTITY_RECALL = ThresholdBand(excellent=0.90, good=0.75)

# E: §2 Hierarchy Structure Accuracy / C: §2 层级结构正确率
EDGE_F1 = ThresholdBand(excellent=0.80, good=0.65)
UAS = ThresholdBand(excellent=0.85, good=0.70)
# E: Spec §2.3-§2.5 define single thresholds — anything below the excellent
#    boundary is FAIL. The good band is intentionally identical to excellent,
#    so PASS/FAIL matches the spec exactly (previously self-invented good bands
#    made e.g. LAR=0.500 display ✅PASS while the threshold column said ≥0.70).
# C: 规范 §2.3-§2.5 为单一阈值 — 低于优秀边界即 FAIL。good 带与优秀边界保持
#    一致，使 PASS/FAIL 与规范完全一致（此前自造的 good 带会让 LAR=0.500
#    显示 ✅PASS，而阈值列却标注 ≥0.70，自相矛盾）。
NTED = ThresholdBand(excellent=0.25, good=0.25, higher_is_better=False)
PC_F1 = ThresholdBand(excellent=0.75, good=0.75)
LAR = ThresholdBand(excellent=0.70, good=0.70)

# E: §4 STT Quality / C: §4 STT 质量
WER = ThresholdBand(excellent=0.15, good=0.30, higher_is_better=False)
KTRR = ThresholdBand(excellent=0.90, good=0.80)

# E: §3 Downstream QA / C: §3 下游 QA
QA_RETENTION = ThresholdBand(excellent=0.90, good=0.75)

# E: §4 Efficiency / C: §4 效率
T_TOTAL_P50 = ThresholdBand(excellent=30, good=60, higher_is_better=False)
T_TOTAL_P95 = ThresholdBand(excellent=60, good=120, higher_is_better=False)
STT_RATIO = ThresholdBand(excellent=0.40, good=0.50, higher_is_better=False)

# E: §4 Per-stage timing thresholds / C: §4 各阶段计时阈值
STT_STAGE_P50 = ThresholdBand(excellent=30, good=45, higher_is_better=False)
STT_STAGE_P95 = ThresholdBand(excellent=60, good=90, higher_is_better=False)
CONCEPT_STAGE_P50 = ThresholdBand(excellent=5, good=8, higher_is_better=False)
HIERARCHY_STAGE_P50 = ThresholdBand(excellent=5, good=8, higher_is_better=False)
DELTA_STAGE_P50 = ThresholdBand(excellent=5, good=8, higher_is_better=False)
POLISH_STAGE_P50 = ThresholdBand(excellent=3, good=5, higher_is_better=False)
MAP_GEN_STAGE_P50 = ThresholdBand(excellent=18, good=30, higher_is_better=False)

# E: §5 Robustness / C: §5 鲁棒性
RECALL_DROP = ThresholdBand(excellent=0.10, good=0.25, higher_is_better=False)

# E: §6 Alignment Validity / C: §6 对齐效度
PEARSON_R = ThresholdBand(excellent=0.70, good=0.40)
SPEARMAN_RHO = ThresholdBand(excellent=0.70, good=0.40)

# E: §6 Inter-rater Reliability / C: §6 评分者信度
ICC = ThresholdBand(excellent=0.70, good=0.50)
KENDALL_W = ThresholdBand(excellent=0.70, good=0.50)

# E: Quick lookup dict by metric name / C: 速查字典 — 按指标名访问
THRESHOLD_MAP: dict[str, ThresholdBand] = {
    'node_f1': NODE_F1,
    'node_p': NODE_P,
    'node_r': NODE_R,
    'label_sim': LABEL_SIM,
    'entity_recall': ENTITY_RECALL,
    'edge_f1': EDGE_F1,
    'uas': UAS,
    'nted': NTED,
    'pc_f1': PC_F1,
    'lar': LAR,
    'wer': WER,
    'ktrr': KTRR,
    'pearson_r': PEARSON_R,
    'spearman_rho': SPEARMAN_RHO,
    'qa_retention': QA_RETENTION,
    't_total_p50': T_TOTAL_P50,
    't_total_p95': T_TOTAL_P95,
    'stt_ratio': STT_RATIO,
    'stt_stage_p50': STT_STAGE_P50,
    'stt_stage_p95': STT_STAGE_P95,
    'concept_stage_p50': CONCEPT_STAGE_P50,
    'hierarchy_stage_p50': HIERARCHY_STAGE_P50,
    'delta_stage_p50': DELTA_STAGE_P50,
    'polish_stage_p50': POLISH_STAGE_P50,
    'map_gen_stage_p50': MAP_GEN_STAGE_P50,
    'recall_drop': RECALL_DROP,
    'icc': ICC,
    'kendall_w': KENDALL_W,
}
