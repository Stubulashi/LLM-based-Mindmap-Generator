"""
E: Markdown report renderer — outputs evaluation report per §7.3 template
C: Markdown 报告渲染器 — 按 §7.3 模板输出评估报告

Evaluation_Schema.md §7.3
"""
from datetime import datetime
from typing import Optional

from evaluation.core.thresholds import (
    THRESHOLD_MAP, Grade, ThresholdBand
)
from evaluation.core.data_loader import MindMapData
from evaluation.report.composite import compute_composite_score


class MarkdownReportRenderer:
    """E: Markdown report renderer / C: Markdown 报告渲染器"""

    def __init__(self, embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 threshold: float = 0.70):
        self.embedding_model = embedding_model
        self.threshold = threshold

    def render(self, gold_map: Optional[MindMapData],
               gen_map: MindMapData,
               results: dict,
               inclusion_list: Optional[list[str]] = None,
               config_info: Optional[dict] = None,
               example_mode: bool = False) -> str:
        """E: Render full Markdown report / C: 渲染完整 Markdown 报告"""
        sections = []
        sections.append(self._render_header(gold_map, gen_map, config_info, example_mode))
        sections.append(self._render_summary(results, inclusion_list, example_mode))

        if not inclusion_list or 'label' in inclusion_list:
            sections.append(self._render_label_section(results.get('label')))
        if not inclusion_list or 'hierarchy' in inclusion_list:
            sections.append(self._render_hierarchy_section(results.get('hierarchy')))
        if not inclusion_list or 'qa' in inclusion_list:
            sections.append(self._render_qa_section(results.get('qa')))
        if not inclusion_list or 'efficiency' in inclusion_list:
            sections.append(self._render_efficiency_section(results.get('efficiency')))
        if not inclusion_list or 'multilingual' in inclusion_list:
            sections.append(self._render_multilingual_section(results.get('multilingual')))
        if not inclusion_list or 'human_corr' in inclusion_list:
            sections.append(self._render_correlation_section(results.get('human_corr')))

        sections.append(self._render_composite_section(results))
        sections.append(self._render_diagnostics(results))
        sections.append(self._render_footer())

        report = '\n\n'.join(sections)
        if example_mode:
            report = self._apply_example_markers(report)
        return report

    def _apply_example_markers(self, report: str) -> str:
        """
        E: In example demo mode, add **example** markers to table values and grades
        C: 在示例演示模式下，给表格中的数值和评级添加 **example** 标记
        """
        lines = report.split('\n')
        marked = []
        for line in lines:
            if line.startswith('|'):
                cells = line.split('|')
                new_cells = [cells[0]]
                for cell in cells[1:]:
                    stripped = cell.strip()
                    # E: Skip separator lines (|---|) and already-marked content
                    # C: 跳过表头分隔线（|---|）和已标记内容
                    if stripped and not stripped.startswith('**example**') and stripped != '' and '---' not in stripped:
                        new_cells.append(f' **example** {stripped} ')
                    else:
                        new_cells.append(cell)
                line = '|'.join(new_cells)
            marked.append(line)
        return '\n'.join(marked)

    def _graded_cell(self, metric_key: str, value: float) -> str:
        """
        E: Generate table cell with grading (utility method)
        C: 生成带评级的表格单元格（备用工具方法）
        Note / 注意: Not currently used in render methods, kept for external calls.
        """
        band = THRESHOLD_MAP.get(metric_key)
        if band is None:
            return f"{value:.3f} | — | —"
        grade = band.grade(value)
        status = band.pass_fail(value)
        return f"{value:.3f} | {grade.value} | **{status}**"

    def _threshold_str(self, metric_key: str) -> str:
        """E: Return threshold string / C: 返回阈值字符串"""
        band = THRESHOLD_MAP.get(metric_key)
        if band is None:
            return "—"
        op = "≥" if band.higher_is_better else "≤"
        return f"{op} {band.excellent:.2f}"

    def _render_header(self, gold_map, gen_map, config_info, example_mode: bool = False) -> str:
        lines = [
            "# 🎯 Mind Map Generation Quality Report",
            "# 思维导图生成质量报告",
            "",
        ]
        if example_mode:
            lines.insert(2, "# (Example Demo / 示例演示)")
            lines.insert(3, "")

        # E: Only render Map/Map ID rows when real metadata exists — checking
        #    concrete keys instead of truthiness of the whole dict, because
        #    DataLoader now always records source_file into metadata (which would
        #    otherwise produce misleading 'N/A' rows for every map).
        # C: 仅当存在真实元数据时才渲染 Map/Map ID 行 — 按具体键判断而非整个字典
        #    的真值，因为 DataLoader 现在总会把 source_file 记入 metadata
        #    （否则每张图都会多出误导性的 N/A 行）。
        if gen_map and gen_map.metadata and ('name' in gen_map.metadata or 'map_id' in gen_map.metadata):
            meta = gen_map.metadata
            lines.append(f"**Map / 导图**: {meta.get('name', 'N/A')}")
            lines.append(f"**Map ID**: {meta.get('map_id', 'N/A')}")
        lines.append(f"**Date / 日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if config_info:
            lines.append(f"**Pipeline Config / 管线配置**: {config_info.get('pipeline', 'N/A')}")
            for k, v in config_info.items():
                if k != 'pipeline':
                    lines.append(f"**{k}**: {v}")
        lines.append(f"**Embedding Model**: {self.embedding_model}")
        lines.append(f"**Threshold τ**: {self.threshold}")
        if gold_map:
            lines.append(f"**Gold Nodes / 金标准节点数**: {gold_map.node_count}")
            lines.append(f"**Gold Links / 金标准边数**: {gold_map.link_count}")
            src = gold_map.metadata.get('source_file') if gold_map.metadata else None
            if src:
                lines.append(f"**Gold Source / 金标准来源**: {src}")
        lines.append(f"**Generated Nodes / 生成节点数**: {gen_map.node_count if gen_map else 0}")
        if gen_map and gen_map.node_count == 0:
            deg = gen_map.metadata.get('_degradation') if gen_map.metadata else None
            lines.append("**⚠ Empty generated map / 空生成图**: pipeline degraded, no nodes produced (\u964d\u7ea7\u65e0\u8282\u70b9)")
            if isinstance(deg, dict) and deg:
                lines.append(f"**Degradation / \u964d\u7ea7\u60c5\u51b5**: {deg}")
        return '\n'.join(lines)

    def _render_summary(self, results: dict, inclusion_list, example_mode: bool = False) -> str:
        lines = [
            "---",
            "## 📋 Summary / 摘要",
            "",
            "| Dimension / 维度 | Key Metric / 核心指标 | Value / 值 | Grade / 评级 | Status / 状态 |",
            "|---|---|---|---|---|",
        ]

        # E: Composite score first / C: 综合评分优先
        if results:
            label_dict = results.get('label')
            if isinstance(label_dict, dict) and 'node_f1' not in label_dict:
                label_dict = None
            hierarchy_dict = results.get('hierarchy')
            if isinstance(hierarchy_dict, dict) and 'edge_f1' not in hierarchy_dict:
                hierarchy_dict = None
            qa_dict = results.get('qa')
            human_dict = results.get('human_corr')
            if isinstance(human_dict, dict) and 'overall_normalized' not in human_dict:
                human_dict = None
            score, detail = compute_composite_score(label_dict, hierarchy_dict, qa_dict, human_dict)
            if score > 0:
                lines.append(
                    f"| Composite / 综合 | Score / 评分 | {score:.4f} | — | — |"
                )

        dims = [
            ('label', 'Node Label / 节点标签', 'node_f1', 'Node-F1'),
            ('hierarchy', 'Hierarchy / 层级结构', 'edge_f1', 'Edge-F1'),
            ('qa', 'QA / 问答', 'qa_score', 'QA Score'),
            ('efficiency', 'Efficiency / 效率', 'wer', 'WER'),
            ('multilingual', 'Multilingual / 多语言', 'max_delta_recall', 'Max Δ Recall'),
            ('human_corr', 'Human / 人工补偿', 'overall_normalized', 'Human Score'),
        ]
        for dim_key, dim_name, metric_key, metric_label in dims:
            if dim_key in results:
                m = results[dim_key]
                val = m.get(metric_key)
                if val is not None and isinstance(val, (int, float)):
                    grade_str = (THRESHOLD_MAP[metric_key].grade(val).value
                                 if metric_key in THRESHOLD_MAP else '—')
                    status_str = (THRESHOLD_MAP[metric_key].pass_fail(val)
                                  if metric_key in THRESHOLD_MAP else '—')
                    lines.append(
                        f"| {dim_name} | {metric_label} | {val:.3f} | {grade_str} | **{status_str}** |"
                    )
                else:
                    lines.append(f"| {dim_name} | {metric_label} | N/A | — | — |")

        return '\n'.join(lines)

    def _render_label_section(self, metrics: Optional[dict]) -> str:
        if not metrics:
            return "## 1. Node Label Quality / 节点标签质量\n\n*Not executed / 未执行*"

        lines = [
            "---",
            "## 🏷️ 1. Node Label Quality / 节点标签质量",
            "",
            "| Metric / 指标 | Value / 值 | Threshold / 阈值 | Grade / 评级 | Status / 状态 |",
            "|---|---|---|---|---|",
        ]

        rows = [
            ('node_f1', 'Node-F1'),
            ('node_p', 'Node-P'),
            ('node_r', 'Node-R'),
            ('label_sim', 'LabelSim'),
            ('entity_recall', 'Entity Recall'),
        ]
        for key, name in rows:
            val = metrics.get(key)
            if val is not None:
                band = THRESHOLD_MAP.get(key)
                if band:
                    g = band.grade(val)
                    s = band.pass_fail(val)
                    lines.append(
                        f"| {name} | {val:.3f} | {self._threshold_str(key)} | {g.value} | **{s}** |"
                    )
                else:
                    lines.append(f"| {name} | {val:.3f} | — | — | — |")

        # E: Hungarian Alignment Details / C: 匈牙利匹配详情
        lines.extend([
            "",
            "**Hungarian Alignment Details / 匈牙利匹配详情**:",
            f"- Gold nodes / 金标准节点数: {metrics.get('gold_count', '?')}",
            f"- Gen nodes / 生成节点数: {metrics.get('gen_count', '?')}",
            f"- High-quality matches (τ={self.threshold}) / 高质量匹配对: {metrics.get('tp', 0)}",
            f"- FP (Unmatched generated nodes) / 误报 FP: {metrics.get('fp', 0)}",
            f"- FN (Unmatched gold nodes) / 漏报 FN: {metrics.get('fn', 0)}",
        ])

        matches = metrics.get('matches', [])
        if matches:
            lines.extend([
                "",
                "**Match Details / 匹配明细**:",
                "",
                "| Gold Label / 金标准标签 | Gen Label / 生成标签 | Similarity / 相似度 |",
                "|---|---|---|",
            ])
            for m in matches[:20]:
                lines.append(
                    f"| {m.get('gold_label', '?')} | {m.get('gen_label', '?')} | {m['similarity']:.4f} |"
                )
            if len(matches) > 20:
                lines.append(f"| ... ({len(matches)} pairs total, showing top 20) / ... (共 {len(matches)} 对，仅显示前20) | ... | ... |")

        # E: Entity Recall Details / C: Entity Recall 详情
        misses = metrics.get('entity_misses', [])
        hits = metrics.get('entity_hits', [])
        if metrics.get('entity_total', 0) > 0:
            lines.extend([
                "",
                f"**Entity Recall Details / Entity Recall 详情**:",
                f"- Total core concepts / 核心概念总数: {metrics['entity_total']}",
                f"- Hits / 命中: {len(hits)}",
                f"- Misses / 遗漏: {len(misses)}",
            ])
            if misses:
                lines.append(f"- Missed concepts / 遗漏概念: {', '.join(misses)}")

        # E: Anomaly records / C: 异常记录
        if metrics.get('error'):
            lines.extend([
                "",
                "**Anomaly / 异常**:",
                f"- {metrics['error']}",
            ])

        return '\n'.join(lines)

    def _render_hierarchy_section(self, metrics: Optional[dict]) -> str:
        if not metrics:
            return "---\n## 2. Hierarchy Accuracy / 层级结构正确率\n\n*Not executed / 未执行*"
        if isinstance(metrics, dict) and metrics.get('error'):
            # E: Exception path — surface the error instead of a misleading all-zero table
            # C: 异常路径 — 展示错误信息，而非误导性的全零表格
            return (
                "---\n## 2. Hierarchy Accuracy / 层级结构正确率\n\n"
                f"**Anomaly / 异常**: {metrics['error']}\n\n*Not executed / 未执行*"
            )

        lines = [
            "---",
            "## 🌳 2. Hierarchy Accuracy / 层级结构正确率",
            "",
            "| Metric / 指标 | Value / 值 | Threshold / 阈值 | Grade / 评级 | Status / 状态 |",
            "|---|---|---|---|---|",
        ]

        rows = [
            ('edge_f1', 'Edge-F1'),
            ('edge_precision', 'Edge-P'),
            ('edge_recall', 'Edge-R'),
            ('uas', 'UAS'),
            ('pc_f1', 'PC-F1'),
            ('lar', 'LAR'),
        ]
        for key, name in rows:
            val = metrics.get(key)
            if val is not None and val >= 0:
                band = THRESHOLD_MAP.get(key)
                if band:
                    g = band.grade(val)
                    s = band.pass_fail(val)
                    lines.append(
                        f"| {name} | {val:.3f} | {self._threshold_str(key)} | {g.value} | **{s}** |"
                    )
                else:
                    # E: Edge-P/R have no spec threshold (§7.1 defines Edge-F1 only) —
                    #    say so explicitly instead of a bare '—' triple.
                    # C: Edge-P/R 无规范阈值（§7.1 仅定义 Edge-F1）— 明确标注而非空三连“—”。
                    lines.append(f"| {name} | {val:.3f} | —（规范未定义） | — | — |")

        # E: nTED (special: lower is better) / C: nTED（特殊处理：越低越好）
        nted = metrics.get('nted')
        if nted is not None:
            g = THRESHOLD_MAP['nted'].grade(nted)
            s = THRESHOLD_MAP['nted'].pass_fail(nted)
            lines.append(
                f"| nTED | {nted:.3f} | ≤ 0.25 | {g.value} | **{s}** |"
            )
            lines.append(f"| Raw TED | {metrics.get('raw_ted', 0):.2f} | — | — | — |")
        else:
            lines.append("| nTED | N/A (zss not installed / zss 未安装) | ≤ 0.25 | — | — |")

        lines.extend([
            "",
            "**Edge Metric Details / 边级指标详情**:",
            f"- Gold edges / 金标准边数: {metrics.get('edge_tp', 0) + metrics.get('edge_fn', 0)}",
            f"- Gen edges / 生成边数: {metrics.get('edge_tp', 0) + metrics.get('edge_fp', 0)}",
            f"- Correct edges TP / 正确边 TP: {metrics.get('edge_tp', 0)}",
            f"- Extra edges FP / 多余边 FP: {metrics.get('edge_fp', 0)}",
            f"- Missing edges FN / 缺失边 FN: {metrics.get('edge_fn', 0)}",
        ])

        return '\n'.join(lines)

    def _render_qa_section(self, metrics: Optional[dict]) -> str:
        if not metrics:
            return "---\n## 3. Downstream QA / 下游问答测试\n\n*Not executed / 未执行（requires audio transcript and LLM API）*"
        lines = [
            "---",
            "## ❓ 3. Downstream QA / 下游问答测试",
            "",
            "| Metric / 指标 | Value / 值 |",
            "|---|---|",
            f"| QA Score / QA 评分（归一化） | {metrics.get('qa_score', 0):.4f} |",
            f"| Avg Raw Score / 平均原始分 | {metrics.get('avg_raw_score', 0):.2f} / 5.00 |",
            f"| Questions / 问题数 | {metrics.get('num_questions', 0)} |",
            f"| Total Tokens / 总 Token 消耗 | {metrics.get('total_tokens', 0)} |",
        ]
        per_q = metrics.get('per_question')
        if per_q:
            lines.extend([
                "",
                "| # | Difficulty / 难度 | Question / 问题 | Answer / 回答 | Score / 得分 |",
                "|---|---|---|---|---|",
            ])
            for item in per_q:
                answer = str(item.get('answer', '')).replace('|', '\\|')[:80]
                question = str(item.get('question', '')).replace('|', '\\|')[:60]
                lines.append(
                    f"| {item.get('id', '?')} | {item.get('difficulty', '?')} | {question} | {answer} | {item.get('score', '?')} |"
                )
        if metrics.get('error'):
            lines.append(f"\n**Anomaly / 异常**: {metrics['error']}")
        return '\n'.join(lines)

    def _render_efficiency_section(self, metrics: Optional[dict]) -> str:
        if not metrics:
            return "---\n## 4. Efficiency & STT / 效率与语音转录\n\n*Not executed / 未执行（requires timing logs and STT data）*"
        lines = [
            "---",
            "## ⏱️ 4. Efficiency & STT / 效率与语音转录",
            "",
            "### 4.1 Pipeline Latency / 管线延迟",
            "",
        ]

        # E: Per-stage timing table with standards comparison
        # C: 各阶段计时表（含标准对比）
        staged = metrics.get('staged_timing', {})
        comparison = metrics.get('standards_comparison', {})

        if staged:
            # E: Fallback total row for persisted results recorded before the
            #    synthetic 'total' stage existed — derive it from raw logs.
            # C: 对合成 'total' 阶段出现前持久化的历史结果做回退 — 从原始日志推导总延迟。
            if 'total' not in staged:
                raw_logs = metrics.get('raw_timing_logs') or []
                starts = [l.get('start') for l in raw_logs if l.get('start') is not None]
                ends = [l.get('end') for l in raw_logs if l.get('end') is not None]
                if starts and ends:
                    total_dur = round(max(ends) - min(starts), 2)
                    staged = dict(staged)
                    staged['total'] = {'p50': total_dur, 'p95': total_dur, 'samples': len(raw_logs)}

            lines.append("| Stage / 阶段 | P50 (s) | P95 (s) | P50 Target | P50 Status | P95 Target | P95 Status |")
            lines.append("|---|---|---|---|---|---|---|")
            for stage_name in ['stt', 'map_gen', 'total']:
                timing = staged.get(stage_name, {})
                if timing:
                    p50 = timing.get('p50', 0)
                    p95 = timing.get('p95', 0)
                    comp = comparison.get(stage_name, {})
                    p50_target = comp.get('p50_target', '—')
                    p50_status = comp.get('p50_status', '—')
                    p95_target = comp.get('p95_target', '—')
                    p95_status = comp.get('p95_status', '—')
                    stage_label = {'stt': 'STT / 语音转录', 'map_gen': 'Map Gen / 导图生成', 'total': '**Total / 总延迟**'}.get(stage_name, stage_name)
                    lines.append(f"| {stage_label} | {p50:.2f} | {p95:.2f} | {p50_target} | {p50_status} | {p95_target} | {p95_status} |")

            lines.append("")
            lines.append(f"**STT Ratio / STT 占比**: {metrics.get('stt_ratio', 0):.1%}")
            lines.append(f"**Repetitions / 重复次数**: {metrics.get('num_repetitions', 1)}")
            lines.append(f"**Standards Used / 使用标准**: {metrics.get('standards_used', 'default')}")
        else:
            # E: Fallback to simple metrics display
            # C: 回退到简单指标显示
            lines.append("| Metric / 指标 | Value / 值 | Threshold / 阈值 | Status / 状态 |")
            lines.append("|---|---|---|---|")
            for key, name, tkey in [
                ('t_total_p50', 'T_total P50', None),
                ('wer', 'WER', 'wer'),
                ('ktrr', 'KTRR', 'ktrr'),
            ]:
                val = metrics.get(key)
                if val is not None:
                    band = THRESHOLD_MAP.get(tkey) if tkey else None
                    if band:
                        lines.append(f"| {name} | {val:.3f} | {self._threshold_str(tkey)} | **{band.pass_fail(val)}** |")
                    else:
                        lines.append(f"| {name} | {val:.3f} | — | — |")
                else:
                    # E: Missing value (e.g. WER without ground truth) — explicit N/A
                    # C: 值缺失（如无 ground truth 的 WER）— 显式 N/A，不显示 0.000 ✅PASS
                    lines.append(f"| {name} | N/A | — | — |")

        # E: 4.2 STT Quality / C: 4.2 STT 质量
        lines.extend([
            "",
            "### 4.2 STT Quality / STT 质量",
            "",
            "| Metric / 指标 | Value / 值 | Threshold / 阈值 | Status / 状态 |",
            "|---|---|---|---|",
        ])
        for key, name, tkey in [
            ('wer', 'WER / 词错率', 'wer'),
            ('ktrr', 'KTRR / 关键术语保留率', 'ktrr'),
        ]:
            val = metrics.get(key)
            if val is not None:
                band = THRESHOLD_MAP.get(tkey) if tkey else None
                if band:
                    lines.append(f"| {name} | {val:.4f} | {self._threshold_str(tkey)} | **{band.pass_fail(val)}** |")
                else:
                    lines.append(f"| {name} | {val:.4f} | — | — |")
            else:
                lines.append(f"| {name} | N/A | — | — |")

        lines.append(f"| WER Method / 计算方法 | {metrics.get('wer_method', 'N/A')} | — | — |")
        lines.append(f"| Samples / 样本数 | {metrics.get('num_stt_samples', 0)} | — | — |")

        # E: Anomaly / STT status markers — explicit, never silently dropped
        # C: 异常 / STT 状态标记 — 显式呈现，绝不静默丢弃
        stt_status = metrics.get('stt_status', 'ok')
        anomalies = metrics.get('anomalies') or []
        if stt_status != 'ok' or anomalies:
            lines.append(f"| STT Status / STT 状态 | {stt_status} | — | — |")
            lines.append(f"| Anomalies / 异常标记 | {', '.join(anomalies) if anomalies else '—'} | — | — |")

        # E: 4.2.3 Correlation / C: 4.2.3 关联分析
        cr = metrics.get('correlation_r', 0)
        if cr:
            lines.extend([
                "",
                "### 4.3 STT-to-Map Correlation / STT-导图关联分析",
                "",
                f"**Pearson r**: {cr:.4f}",
                f"**Spearman ρ**: {metrics.get('correlation_rho', 0):.4f}",
                f"**Interpretation / 解读**: {metrics.get('correlation_interpretation', 'N/A')}",
            ])

        if metrics.get('error'):
            lines.append(f"\n**Anomaly / 异常**: {metrics['error']}")

        return '\n'.join(lines)

    def _render_multilingual_section(self, metrics: Optional[dict]) -> str:
        if not metrics:
            return "---\n## 5. Multilingual & Robustness / 多语言与鲁棒性\n\n*Not executed / 未执行（requires multilingual test sets）*"
        lines = [
            "---",
            "## 🌐 5. Multilingual & Robustness / 多语言与鲁棒性",
            "",
            "| Metric / 指标 | CN | EN | Mixed / 混合 | Max Δ |",
            "|---|---|---|---|---|",
            f"| Entity Recall | {metrics.get('cn_entity_recall', 0):.3f} | "
            f"{metrics.get('en_entity_recall', 0):.3f} | "
            f"{metrics.get('mixed_entity_recall', 0):.3f} | "
            f"{metrics.get('max_delta_recall', 0):.3f} |",
        ]
        return '\n'.join(lines)

    def _render_correlation_section(self, metrics: Optional[dict]) -> str:
        if not metrics:
            return "---\n## 6. Human Evaluation / 人工评估（补偿）\n\n*Not executed / 未执行（requires interactive human scoring）*"
        if isinstance(metrics, dict) and metrics.get('error'):
            # E: Exception path — surface the error instead of a misleading zero table
            # C: 异常路径 — 展示错误信息，而非误导性的零值表格
            return (
                "---\n## 6. Human Evaluation / 人工评估（补偿）\n\n"
                f"**Anomaly / 异常**: {metrics['error']}\n\n*Not executed / 未执行*"
            )
        lines = [
            "---",
            "## 👤 6. Human Evaluation / 人工评估（§2 层级结构补偿）",
            "",
        ]
        # E: New interactive dual-scoring format / C: 新交互式双评分格式
        if 'overall_normalized' in metrics:
            lines.extend([
                "| Metric / 指标 | Value / 值 |",
                "|---|---|",
                f"| Questionnaires / 问卷份数 | {metrics.get('num_questionnaires', 0)} |",
                f"| Samples / 评分条数 | {metrics.get('num_samples', 0)} |",
                f"| System Map Mean / 系统导图平均分 | {metrics.get('gen_mean', 0):.2f} / 10 |",
                f"| Human Map Mean / 人类标注平均分 | {metrics.get('human_mean', 0):.2f} / 10 |",
                f"| Overall Mean / 综合平均分 | {metrics.get('overall_mean', 0):.2f} / 10 |",
                f"| Overall Normalized / 归一化 | {metrics.get('overall_normalized', 0):.4f} |",
                "",
                "> **Scale / 量表**: 0-10 分（10=完全符合，0=不符合），维度为树与音频内容的",
                "> 关联性 / 代表程度；每音频两个分（系统导图 / 人类标注导图）。",
                "> **Role / 作用**: §6 人工评分作为 §2 层级结构正确率的补偿机制计入综合评分，",
                "> 降低层级指标 False Negative 对总分的误伤。",
            ])
            per_audio = metrics.get('per_audio')
            if per_audio:
                lines.extend([
                    "",
                    "| Audio / 音频 | Gen Mean / 系统均值 | Human Mean / 人类均值 | Source / 来源 | Ratings / 评次 |",
                    "|---|---|---|---|---|",
                ])
                for item in per_audio:
                    lines.append(
                        f"| {item.get('audio', '?')} | {item.get('gen_mean', 0):.2f} | "
                        f"{item.get('human_mean', 0):.2f} | {item.get('gold_source', '—')} | "
                        f"{item.get('ratings', 0)} |"
                    )
            return '\n'.join(lines)
        # E: Legacy correlation format / C: 旧相关性格式
        lines.extend([
            "| Metric / 指标 | Value / 值 | Threshold / 阈值 | Status / 状态 |",
            "|---|---|---|---|",
            f"| Pearson r (Node-F1 vs Readability) | {metrics.get('node_f1_readability_r', 0):.3f} | ≥ 0.70 | **{'Valid / 有效' if metrics.get('node_f1_readability_r', 0) >= 0.70 else 'Needs Improvement / 需改进'}** |",
            f"| Spearman ρ (Node-F1 vs Readability) | {metrics.get('node_f1_readability_rho', 0):.3f} | ≥ 0.70 | **{'Valid / 有效' if metrics.get('node_f1_readability_rho', 0) >= 0.70 else 'Needs Improvement / 需改进'}** |",
        ])
        return '\n'.join(lines)

    def _render_composite_section(self, results: dict) -> str:
        """E: Render composite score / C: 渲染综合评分"""
        lines = [
            "---",
            "## 📊 7. Overall / 综合评分",
            "",
        ]

        label_dict = results.get('label')
        if isinstance(label_dict, dict) and 'node_f1' not in label_dict:
            label_dict = None
        hierarchy_dict = results.get('hierarchy')
        if isinstance(hierarchy_dict, dict) and 'edge_f1' not in hierarchy_dict:
            hierarchy_dict = None
        qa_dict = results.get('qa')
        human_dict = results.get('human_corr')
        if isinstance(human_dict, dict) and 'overall_normalized' not in human_dict:
            human_dict = None

        score, detail = compute_composite_score(label_dict, hierarchy_dict, qa_dict, human_dict)

        lines.append(f"**Composite Score / 综合评分**: {score:.4f} / 1.00")
        lines.append("")
        lines.append("| Component / 成分 | Value / 值 | Weight / 权重 | Weighted / 加权分 |")
        lines.append("|---|---|---|---|")

        for key, comp in detail.get('components', {}).items():
            lines.append(
                f"| {key} | {comp['value']:.4f} | {comp['weight']:.2f} | {comp['weighted']:.4f} |"
            )

        # E: Normalization note / C: 归一化说明
        used_weights = sum(c['weight'] for c in detail.get('components', {}).values())
        if used_weights < 1.0:
            lines.extend([
                "",
                f"> **Note / 说明**: Only {used_weights:.0%} of total weight was evaluated. "
                f"Missing dimensions have been excluded and remaining weights renormalized. / "
                f"仅评估了 {used_weights:.0%} 的权重分量，缺失维度已排除并重新归一化。",
            ])

        # E: Interpretation guide / C: 解读指南
        lines.extend([
            "",
            "**Interpretation Guide / 解读指南**:",
            f"- Score ≥ 0.85: Excellent overall quality / 整体质量优秀",
            f"- Score ≥ 0.70: Good quality, minor improvements possible / 整体质量良好，有改进空间",
            f"- Score < 0.70: Needs improvement in key areas / 关键领域需要改进",
        ])

        return '\n'.join(lines)

    def _render_diagnostics(self, results: dict) -> str:
        """E: Auto-generate diagnostic suggestions / C: 自动生成诊断建议"""
        lines = [
            "---",
            "## 🔍 8. Diagnostics / 诊断建议",
            "",
        ]

        suggestions = []

        # E: Node label diagnostics / C: 节点标签诊断
        label = results.get('label')
        if label:
            nf1 = label.get('node_f1')
            if nf1 is not None:
                if nf1 < 0.70:
                    suggestions.append(
                        "> **⚠️ Node-F1 Needs Improvement ({:.3f}) / 节点F1需改进**. ".format(nf1)
                        + "Node labels have low match rate with gold standard. Check concept extraction for missed concepts and LLM output for redundant nodes. / "
                        + "节点标签与金标准匹配率低。检查概念抽取是否有遗漏，以及 LLM 输出是否有多余节点。"
                    )
                elif nf1 < 0.85:
                    suggestions.append(
                        "> **👍 Node-F1 Good ({:.3f}) / 节点F1良好**. ".format(nf1)
                        + "Labels mostly match. Check FP/FN distribution: reduce redundancy if FP is high, improve coverage if FN is high. / "
                        + "标签基本匹配。检查 FP/FN 分布：FP 高则减少冗余，FN 高则提高覆盖率。"
                    )
                else:
                    suggestions.append(
                        "> **🏆 Node-F1 Excellent ({:.3f}) / 节点F1优秀**. ".format(nf1)
                        + "Labels closely match gold standard. / 标签与金标准高度匹配。"
                    )

            er = label.get('entity_recall')
            if er is not None and er > 0:
                if er < 0.75:
                    misses_joined = ', '.join(label.get('entity_misses', [])[:5])
                    suggestions.append(
                        "> **⚠️ Entity Recall Needs Improvement ({:.3f}) / 实体召回率需改进**. ".format(er)
                        + "Key concepts missing / 关键概念缺失: {}. ".format(misses_joined)
                        + "Check STT transcription for these terms. / 检查这些术语的 STT 转录。"
                    )
                elif er < 0.90:
                    misses = label.get('entity_misses', [])
                    if misses:
                        misses_joined = ', '.join(misses[:3])
                        suggestions.append(
                            "> **👍 Entity Recall Good ({:.3f}) / 实体召回率良好**. ".format(er)
                            + "Minor secondary concepts missed / 次要概念遗漏: {}. ".format(misses_joined)
                        )

            fp = label.get('fp', 0)
            if fp > 2:
                suggestions.append(
                    f"> **⚠️ High FP ({fp}) / FP 过高**. "
                    + "Generated map has redundant nodes. Tighten concept extraction threshold or reduce LLM over-generation. / "
                    + "生成图存在冗余节点。建议收紧概念抽取阈值或减少 LLM 过度生成。"
                )

        # E: Hierarchy diagnostics / C: 层级结构诊断
        hierarchy = results.get('hierarchy')
        if hierarchy:
            ef1 = hierarchy.get('edge_f1')
            if ef1 is not None and ef1 < 0.65:
                suggestions.append(
                    "> **⚠️ Edge-F1 Needs Improvement ({:.3f}) / 边F1需改进**. ".format(ef1)
                    + "Hierarchy has significant deviations. Check hierarchy planning stage for correct parent-child relationships. / "
                    + "层级结构存在显著偏差。检查层级规划阶段父子关系是否正确。"
                )

            uas_val = hierarchy.get('uas')
            if uas_val is not None and uas_val < 0.70:
                if uas_val == 0.0 and hierarchy.get('aligned_count', 0) == 0:
                    # E: Zero alignment — the diagnosis is label matching, not parenting
                    # C: 零对齐 — 诊断应指向标签匹配而非父级分配
                    suggestions.append(
                        "> **⚠️ UAS is 0 ({:.3f}) / UAS 为 0**. ".format(uas_val)
                        + "No aligned nodes — check label matching quality. / "
                        + "无对齐节点，建议检查标签匹配质量。"
                    )
                else:
                    suggestions.append(
                        "> **⚠️ UAS Needs Improvement ({:.3f}) / UAS 需改进**. ".format(uas_val)
                        + "Multiple nodes have incorrect parent assignments. Check hierarchy planning quality. / "
                        + "多个节点的父级分配错误。检查层级规划质量。"
                    )

            nted_val = hierarchy.get('nted')
            if nted_val is not None:
                if nted_val <= 0.25:
                    suggestions.append(
                        "> **🏆 nTED Excellent ({:.3f}) / nTED 优秀**. ".format(nted_val)
                        + "Tree structure closely matches gold standard. / 树结构与金标准高度匹配。"
                    )
                elif nted_val <= 0.40:
                    suggestions.append(
                        "> **👍 nTED Good ({:.3f}) / nTED 良好**. ".format(nted_val)
                        + "Tree structure has minor deviations. / 树结构有轻微偏差。"
                    )

        # E: QA diagnostics / C: QA 诊断
        qa = results.get('qa')
        if qa:
            qs = qa.get('qa_score')
            if qs is not None and qs < 0.75:
                suggestions.append(
                    "> **⚠️ QA Score Needs Improvement ({:.3f}) / QA 评分需改进**. ".format(qs)
                    + "The generated map does not preserve sufficient information for downstream QA tasks. / "
                    + "生成导图未能为下游 QA 任务保留足够信息。"
                )

        # E: STT diagnostics / C: STT 诊断
        efficiency = results.get('efficiency')
        if efficiency:
            wer = efficiency.get('wer')
            if wer is not None and wer > 0.15:
                suggestions.append(
                    "> **⚠️ WER Too High ({:.3f}) / WER 过高**. ".format(wer)
                    + "STT accuracy needs improvement. Check audio quality or try a different model. / "
                    + "STT 准确率需改进。检查音频质量或尝试不同模型。"
                )

        if not suggestions:
            suggestions.append(
                "> Insufficient data for diagnostic suggestions. Upload a gold standard tree for full diagnosis. / "
                + "数据不足，无法提供诊断建议。请上传金标准树以进行完整诊断。"
            )

        lines.extend(suggestions)
        return '\n'.join(lines)

    def _render_footer(self) -> str:
        lines = [
            "---",
            f"*Report Generated / 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "*Generated by AI MindMap Evaluation Tool v1.0*",
            "*Reference / 依据: Evaluation_Schema.md v1.5*",
        ]
        return '\n'.join(lines)
