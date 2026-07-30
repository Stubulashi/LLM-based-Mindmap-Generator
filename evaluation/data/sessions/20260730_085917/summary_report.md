# Batch Evaluation Summary Report

**Batch Timestamp / 批次时间**: 20260730_085917
**Total Pairs / 总配对数**: 9
**Embedding Model**: paraphrase-multilingual-MiniLM-L12-v2
**Threshold τ**: 0.7
**Methods / 评估方法**: label, hierarchy

---
## Per-Pair Results / 每对结果

| Pair / 配对 | edge_f1 | edge_fn | edge_fp | edge_precision | edge_recall | edge_tp | lar | nted | pc_f1 | pc_precision | pc_recall | pc_tp | raw_ted | uas | entity_recall | entity_total | fn | fp | gen_count | gold_count | label_sim | node_f1 | node_precision | node_recall | threshold | tp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Saarland University 1 | 0.000 | 2.000 | 5.000 | 0.000 | 0.000 | 0.000 | 0.333 | 0.286 | 0.000 | 1.000 | 0.000 | 0.000 | 2.000 | 0.000 | 1.000 | 3.000 | 0.000 | 4.000 | 7.000 | 3.000 | 0.848 | 0.600 | 0.429 | 1.000 | 0.700 | 3.000 |
| Saarland University 2 | 0.000 | 3.000 | 3.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 1.000 | 0.500 | 4.000 | 3.000 | 3.000 | 4.000 | 4.000 | 0.732 | 0.250 | 0.250 | 0.250 | 0.700 | 1.000 |
| Saarland University 3 | 0.000 | 3.000 | 5.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.800 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.500 | 4.000 | 2.000 | 3.000 | 5.000 | 4.000 | 0.864 | 0.444 | 0.400 | 0.500 | 0.700 | 2.000 |
| Saarland University 4 | 0.444 | 1.000 | 4.000 | 0.333 | 0.667 | 2.000 | 0.333 | 0.667 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 1.000 | 0.750 | 4.000 | 1.000 | 3.000 | 6.000 | 4.000 | 0.752 | 0.600 | 0.500 | 0.750 | 0.700 | 3.000 |
| Saarland University 5 | 0.000 | 4.000 | 4.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.000 | 0.800 | 5.000 | 1.000 | 1.000 | 5.000 | 5.000 | 0.983 | 0.800 | 0.800 | 0.800 | 0.700 | 4.000 |
| Saarland University 6 | 0.400 | 2.000 | 1.000 | 0.500 | 0.333 | 1.000 | 0.500 | 0.750 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 1.000 | 0.750 | 4.000 | 2.000 | 1.000 | 3.000 | 4.000 | 1.000 | 0.571 | 0.667 | 0.500 | 0.700 | 2.000 |
| Saarland University 7 | 0.333 | 2.000 | 2.000 | 0.333 | 0.333 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.500 | 0.500 | 4.000 | 2.000 | 2.000 | 4.000 | 4.000 | 0.990 | 0.500 | 0.500 | 0.500 | 0.700 | 2.000 |
| Saarland University 8 | 0.000 | 4.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.000 | 0.400 | 5.000 | 3.000 | 2.000 | 4.000 | 5.000 | 0.962 | 0.444 | 0.500 | 0.400 | 0.700 | 2.000 |
| Saarland University 9 | 0.444 | 4.000 | 1.000 | 0.667 | 0.333 | 2.000 | 0.333 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 7.000 | 1.000 | 0.429 | 7.000 | 4.000 | 1.000 | 4.000 | 7.000 | 0.900 | 0.545 | 0.750 | 0.429 | 0.700 | 3.000 |

---
## Summary Statistics / 汇总统计

| Metric / 指标 | Mean / 均值 | Std / 标准差 | Min / 最小 | Max / 最大 |
|---|---|---|---|---|
| hierarchy.edge_f1 | 0.1802 | 0.2161 | 0.0000 | 0.4444 |
| hierarchy.edge_fn | 2.7778 | 1.0929 | 1.0000 | 4.0000 |
| hierarchy.edge_fp | 2.7778 | 1.8559 | 0.0000 | 5.0000 |
| hierarchy.edge_precision | 0.3148 | 0.3579 | 0.0000 | 1.0000 |
| hierarchy.edge_recall | 0.1852 | 0.2422 | 0.0000 | 0.6667 |
| hierarchy.edge_tp | 0.6667 | 0.8660 | 0.0000 | 2.0000 |
| hierarchy.lar | 0.2778 | 0.3333 | 0.0000 | 1.0000 |
| hierarchy.nted | 0.8336 | 0.2436 | 0.2857 | 1.0000 |
| hierarchy.pc_f1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_precision | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| hierarchy.pc_recall | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_tp | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.raw_ted | 4.2222 | 1.3944 | 2.0000 | 7.0000 |
| hierarchy.uas | 0.5000 | 0.5000 | 0.0000 | 1.0000 |
| label.entity_recall | 0.6254 | 0.2057 | 0.4000 | 1.0000 |
| label.entity_total | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.fn | 2.0000 | 1.2247 | 0.0000 | 4.0000 |
| label.fp | 2.2222 | 1.0929 | 1.0000 | 4.0000 |
| label.gen_count | 4.6667 | 1.2247 | 3.0000 | 7.0000 |
| label.gold_count | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.label_sim | 0.8924 | 0.1015 | 0.7321 | 1.0000 |
| label.node_f1 | 0.5284 | 0.1494 | 0.2500 | 0.8000 |
| label.node_precision | 0.5328 | 0.1761 | 0.2500 | 0.8000 |
| label.node_recall | 0.5698 | 0.2335 | 0.2500 | 1.0000 |
| label.threshold | 0.7000 | 0.0000 | 0.7000 | 0.7000 |
| label.tp | 2.4444 | 0.8819 | 1.0000 | 4.0000 |

---
## Best / Worst Cases / 最优与最差案例

- **hierarchy.edge_f1**
  - Best / 最优: Saarland University 4 (0.4444)
  - Worst / 最差: Saarland University 8 (0.0000)
- **hierarchy.edge_fn**
  - Best / 最优: Saarland University 5 (4.0000)
  - Worst / 最差: Saarland University 4 (1.0000)
- **hierarchy.edge_fp**
  - Best / 最优: Saarland University 1 (5.0000)
  - Worst / 最差: Saarland University 8 (0.0000)
- **hierarchy.edge_precision**
  - Best / 最优: Saarland University 8 (1.0000)
  - Worst / 最差: Saarland University 5 (0.0000)
- **hierarchy.edge_recall**
  - Best / 最优: Saarland University 4 (0.6667)
  - Worst / 最差: Saarland University 8 (0.0000)
- **hierarchy.edge_tp**
  - Best / 最优: Saarland University 4 (2.0000)
  - Worst / 最差: Saarland University 8 (0.0000)
- **hierarchy.lar**
  - Best / 最优: Saarland University 2 (1.0000)
  - Worst / 最差: Saarland University 8 (0.0000)
- **hierarchy.nted**
  - Best / 最优: Saarland University 2 (1.0000)
  - Worst / 最差: Saarland University 1 (0.2857)
- **hierarchy.pc_f1**
  - Best / 最优: Saarland University 1 (0.0000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.pc_precision**
  - Best / 最优: Saarland University 1 (1.0000)
  - Worst / 最差: Saarland University 9 (1.0000)
- **hierarchy.pc_recall**
  - Best / 最优: Saarland University 1 (0.0000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.pc_tp**
  - Best / 最优: Saarland University 1 (0.0000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.raw_ted**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (2.0000)
- **hierarchy.uas**
  - Best / 最优: Saarland University 2 (1.0000)
  - Worst / 最差: Saarland University 8 (0.0000)
- **label.entity_recall**
  - Best / 最优: Saarland University 1 (1.0000)
  - Worst / 最差: Saarland University 8 (0.4000)
- **label.entity_total**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.fn**
  - Best / 最优: Saarland University 9 (4.0000)
  - Worst / 最差: Saarland University 1 (0.0000)
- **label.fp**
  - Best / 最优: Saarland University 1 (4.0000)
  - Worst / 最差: Saarland University 9 (1.0000)
- **label.gen_count**
  - Best / 最优: Saarland University 1 (7.0000)
  - Worst / 最差: Saarland University 6 (3.0000)
- **label.gold_count**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.label_sim**
  - Best / 最优: Saarland University 6 (1.0000)
  - Worst / 最差: Saarland University 2 (0.7321)
- **label.node_f1**
  - Best / 最优: Saarland University 5 (0.8000)
  - Worst / 最差: Saarland University 2 (0.2500)
- **label.node_precision**
  - Best / 最优: Saarland University 5 (0.8000)
  - Worst / 最差: Saarland University 2 (0.2500)
- **label.node_recall**
  - Best / 最优: Saarland University 1 (1.0000)
  - Worst / 最差: Saarland University 2 (0.2500)
- **label.threshold**
  - Best / 最优: Saarland University 1 (0.7000)
  - Worst / 最差: Saarland University 9 (0.7000)
- **label.tp**
  - Best / 最优: Saarland University 5 (4.0000)
  - Worst / 最差: Saarland University 2 (1.0000)

---
*Report Generated / 报告生成时间: 2026-07-30 09:02:02*