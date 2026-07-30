# Batch Evaluation Summary Report

**Batch Timestamp / 批次时间**: 20260730_123948
**Total Pairs / 总配对数**: 9
**Embedding Model**: paraphrase-multilingual-MiniLM-L12-v2
**Threshold τ**: 0.7
**Methods / 评估方法**: label, hierarchy

---
## Per-Pair Results / 每对结果

| Pair / 配对 | edge_f1 | edge_fn | edge_fp | edge_precision | edge_recall | edge_tp | lar | nted | pc_f1 | pc_precision | pc_recall | pc_tp | raw_ted | uas | entity_recall | entity_total | fn | fp | gen_count | gold_count | label_sim | node_f1 | node_precision | node_recall | threshold | tp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Saarland University 1 | 0.000 | 2.000 | 8.200 | 0.000 | 0.000 | 0.000 | 0.500 | 0.321 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 0.000 | 0.733 | 3.000 | 1.000 | 7.400 | 9.400 | 3.000 | 0.851 | 0.324 | 0.214 | 0.667 | 0.700 | 2.000 |
| Saarland University 2 | 0.000 | 3.000 | 4.000 | 0.200 | 0.000 | 0.000 | 0.400 | 0.674 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.150 | 0.700 | 4.000 | 1.200 | 3.600 | 6.400 | 4.000 | 0.825 | 0.528 | 0.437 | 0.700 | 0.700 | 2.800 |
| Saarland University 3 | 0.000 | 3.000 | 7.000 | 0.000 | 0.000 | 0.000 | 0.067 | 0.504 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.600 | 4.000 | 2.000 | 6.200 | 8.200 | 4.000 | 0.896 | 0.333 | 0.252 | 0.500 | 0.700 | 2.000 |
| Saarland University 4 | 0.000 | 3.000 | 6.800 | 0.200 | 0.000 | 0.000 | 0.467 | 0.543 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.200 | 0.500 | 4.000 | 2.200 | 6.600 | 8.400 | 4.000 | 0.598 | 0.263 | 0.188 | 0.450 | 0.700 | 1.800 |
| Saarland University 5 | 0.033 | 3.800 | 8.000 | 0.025 | 0.050 | 0.200 | 0.080 | 0.567 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.040 | 0.880 | 5.000 | 0.600 | 4.800 | 9.200 | 5.000 | 0.964 | 0.633 | 0.501 | 0.880 | 0.700 | 4.400 |
| Saarland University 6 | 0.000 | 3.000 | 4.000 | 0.200 | 0.000 | 0.000 | 0.450 | 0.733 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.200 | 0.650 | 4.000 | 1.400 | 2.400 | 5.000 | 4.000 | 0.761 | 0.520 | 0.433 | 0.650 | 0.700 | 2.600 |
| Saarland University 7 | 0.000 | 3.000 | 7.200 | 0.000 | 0.000 | 0.000 | 0.000 | 0.506 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.500 | 4.000 | 2.000 | 6.000 | 8.000 | 4.000 | 0.990 | 0.335 | 0.253 | 0.500 | 0.700 | 2.000 |
| Saarland University 8 | 0.044 | 3.800 | 4.600 | 0.040 | 0.050 | 0.200 | 0.000 | 0.892 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.100 | 0.360 | 5.000 | 3.200 | 4.000 | 5.800 | 5.000 | 0.906 | 0.325 | 0.302 | 0.360 | 0.700 | 1.800 |
| Saarland University 9 | 0.000 | 6.000 | 7.400 | 0.000 | 0.000 | 0.000 | 0.000 | 0.857 | 0.000 | 1.000 | 0.000 | 0.000 | 7.000 | 0.000 | 0.343 | 7.000 | 4.600 | 6.200 | 8.600 | 7.000 | 0.978 | 0.305 | 0.281 | 0.343 | 0.700 | 2.400 |

---
## Summary Statistics / 汇总统计

| Metric / 指标 | Mean / 均值 | Std / 标准差 | Min / 最小 | Max / 最大 |
|---|---|---|---|---|
| hierarchy.edge_f1 | 0.0086 | 0.0174 | 0.0000 | 0.0444 |
| hierarchy.edge_fn | 3.4000 | 1.1091 | 2.0000 | 6.0000 |
| hierarchy.edge_fp | 6.3556 | 1.6846 | 4.0000 | 8.2000 |
| hierarchy.edge_precision | 0.0739 | 0.0956 | 0.0000 | 0.2000 |
| hierarchy.edge_recall | 0.0111 | 0.0220 | 0.0000 | 0.0500 |
| hierarchy.edge_tp | 0.0444 | 0.0882 | 0.0000 | 0.2000 |
| hierarchy.lar | 0.2181 | 0.2272 | 0.0000 | 0.5000 |
| hierarchy.nted | 0.6219 | 0.1837 | 0.3212 | 0.8917 |
| hierarchy.pc_f1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_precision | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| hierarchy.pc_recall | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_tp | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.raw_ted | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| hierarchy.uas | 0.0767 | 0.0875 | 0.0000 | 0.2000 |
| label.entity_recall | 0.5851 | 0.1769 | 0.3429 | 0.8800 |
| label.entity_total | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.fn | 2.0222 | 1.2347 | 0.6000 | 4.6000 |
| label.fp | 5.2444 | 1.6364 | 2.4000 | 7.4000 |
| label.gen_count | 7.6667 | 1.5556 | 5.0000 | 9.4000 |
| label.gold_count | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.label_sim | 0.8633 | 0.1248 | 0.5982 | 0.9900 |
| label.node_f1 | 0.3963 | 0.1290 | 0.2626 | 0.6332 |
| label.node_precision | 0.3180 | 0.1111 | 0.1879 | 0.5008 |
| label.node_recall | 0.5611 | 0.1760 | 0.3429 | 0.8800 |
| label.threshold | 0.7000 | 0.0000 | 0.7000 | 0.7000 |
| label.tp | 2.4222 | 0.8212 | 1.8000 | 4.4000 |

---
## Best / Worst Cases / 最优与最差案例

- **hierarchy.edge_f1**
  - Best / 最优: Saarland University 8 (0.0444)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_fn**
  - Best / 最优: Saarland University 9 (6.0000)
  - Worst / 最差: Saarland University 1 (2.0000)
- **hierarchy.edge_fp**
  - Best / 最优: Saarland University 1 (8.2000)
  - Worst / 最差: Saarland University 6 (4.0000)
- **hierarchy.edge_precision**
  - Best / 最优: Saarland University 2 (0.2000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_recall**
  - Best / 最优: Saarland University 5 (0.0500)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_tp**
  - Best / 最优: Saarland University 5 (0.2000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.lar**
  - Best / 最优: Saarland University 1 (0.5000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.nted**
  - Best / 最优: Saarland University 8 (0.8917)
  - Worst / 最差: Saarland University 1 (0.3212)
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
  - Worst / 最差: Saarland University 1 (3.0000)
- **hierarchy.uas**
  - Best / 最优: Saarland University 4 (0.2000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **label.entity_recall**
  - Best / 最优: Saarland University 5 (0.8800)
  - Worst / 最差: Saarland University 9 (0.3429)
- **label.entity_total**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.fn**
  - Best / 最优: Saarland University 9 (4.6000)
  - Worst / 最差: Saarland University 5 (0.6000)
- **label.fp**
  - Best / 最优: Saarland University 1 (7.4000)
  - Worst / 最差: Saarland University 6 (2.4000)
- **label.gen_count**
  - Best / 最优: Saarland University 1 (9.4000)
  - Worst / 最差: Saarland University 6 (5.0000)
- **label.gold_count**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.label_sim**
  - Best / 最优: Saarland University 7 (0.9900)
  - Worst / 最差: Saarland University 4 (0.5982)
- **label.node_f1**
  - Best / 最优: Saarland University 5 (0.6332)
  - Worst / 最差: Saarland University 4 (0.2626)
- **label.node_precision**
  - Best / 最优: Saarland University 5 (0.5008)
  - Worst / 最差: Saarland University 4 (0.1879)
- **label.node_recall**
  - Best / 最优: Saarland University 5 (0.8800)
  - Worst / 最差: Saarland University 9 (0.3429)
- **label.threshold**
  - Best / 最优: Saarland University 1 (0.7000)
  - Worst / 最差: Saarland University 9 (0.7000)
- **label.tp**
  - Best / 最优: Saarland University 5 (4.4000)
  - Worst / 最差: Saarland University 8 (1.8000)

---
*Report Generated / 报告生成时间: 2026-07-30 12:52:23*