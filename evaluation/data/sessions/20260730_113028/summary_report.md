# Batch Evaluation Summary Report

**Batch Timestamp / 批次时间**: 20260730_113028
**Total Pairs / 总配对数**: 9
**Embedding Model**: paraphrase-multilingual-MiniLM-L12-v2
**Threshold τ**: 0.7
**Methods / 评估方法**: label, hierarchy

---
## Per-Pair Results / 每对结果

| Pair / 配对 | edge_f1 | edge_fn | edge_fp | edge_precision | edge_recall | edge_tp | lar | nted | pc_f1 | pc_precision | pc_recall | pc_tp | raw_ted | uas | entity_recall | entity_total | fn | fp | gen_count | gold_count | label_sim | node_f1 | node_precision | node_recall | threshold | tp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Saarland University 1 | 0.222 | 1.333 | 3.667 | 0.167 | 0.333 | 0.667 | 0.500 | 0.492 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 0.667 | 0.889 | 3.000 | 1.000 | 4.333 | 6.333 | 3.000 | 0.851 | 0.436 | 0.328 | 0.667 | 0.700 | 2.000 |
| Saarland University 2 | 0.148 | 2.333 | 3.333 | 0.111 | 0.222 | 0.667 | 0.389 | 0.857 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.611 | 0.833 | 4.000 | 1.333 | 2.333 | 5.000 | 4.000 | 0.793 | 0.599 | 0.560 | 0.667 | 0.700 | 2.667 |
| Saarland University 3 | 0.095 | 2.667 | 2.667 | 0.083 | 0.111 | 0.333 | 0.111 | 0.933 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.222 | 0.667 | 4.000 | 1.667 | 1.667 | 4.000 | 4.000 | 0.910 | 0.579 | 0.589 | 0.583 | 0.700 | 2.333 |
| Saarland University 4 | 0.167 | 2.333 | 2.333 | 0.133 | 0.222 | 0.667 | 0.333 | 0.756 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.556 | 0.750 | 4.000 | 1.000 | 2.333 | 5.333 | 4.000 | 0.733 | 0.644 | 0.567 | 0.750 | 0.700 | 3.000 |
| Saarland University 5 | 0.000 | 4.000 | 5.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.750 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.000 | 0.800 | 5.000 | 1.000 | 3.000 | 7.000 | 5.000 | 0.983 | 0.677 | 0.600 | 0.800 | 0.700 | 4.000 |
| Saarland University 6 | 0.333 | 2.000 | 2.000 | 0.467 | 0.333 | 1.000 | 0.222 | 0.750 | 0.000 | 1.000 | 0.000 | 0.000 | 3.333 | 0.556 | 0.667 | 4.000 | 1.333 | 1.667 | 4.333 | 4.000 | 0.894 | 0.652 | 0.667 | 0.667 | 0.700 | 2.667 |
| Saarland University 7 | 0.340 | 2.000 | 2.000 | 0.361 | 0.333 | 1.000 | 0.000 | 0.933 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.500 | 0.500 | 4.000 | 2.000 | 2.000 | 4.000 | 4.000 | 0.990 | 0.505 | 0.522 | 0.500 | 0.700 | 2.000 |
| Saarland University 8 | 0.306 | 3.000 | 1.667 | 0.417 | 0.250 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.500 | 0.400 | 5.000 | 3.000 | 2.000 | 4.000 | 5.000 | 0.908 | 0.448 | 0.522 | 0.400 | 0.700 | 2.000 |
| Saarland University 9 | 0.252 | 4.667 | 3.000 | 0.306 | 0.222 | 1.333 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 7.000 | 0.389 | 0.476 | 7.000 | 3.667 | 3.000 | 6.333 | 7.000 | 0.991 | 0.498 | 0.524 | 0.476 | 0.700 | 3.333 |

---
## Summary Statistics / 汇总统计

| Metric / 指标 | Mean / 均值 | Std / 标准差 | Min / 最小 | Max / 最大 |
|---|---|---|---|---|
| hierarchy.edge_f1 | 0.2070 | 0.1151 | 0.0000 | 0.3397 |
| hierarchy.edge_fn | 2.7037 | 1.0467 | 1.3333 | 4.6667 |
| hierarchy.edge_fp | 2.8519 | 1.0423 | 1.6667 | 5.0000 |
| hierarchy.edge_precision | 0.2272 | 0.1642 | 0.0000 | 0.4667 |
| hierarchy.edge_recall | 0.2253 | 0.1115 | 0.0000 | 0.3333 |
| hierarchy.edge_tp | 0.7407 | 0.4006 | 0.0000 | 1.3333 |
| hierarchy.lar | 0.1728 | 0.1953 | 0.0000 | 0.5000 |
| hierarchy.nted | 0.8301 | 0.1631 | 0.4917 | 1.0000 |
| hierarchy.pc_f1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_precision | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| hierarchy.pc_recall | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_tp | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.raw_ted | 4.3704 | 1.1837 | 3.0000 | 7.0000 |
| hierarchy.uas | 0.4444 | 0.2115 | 0.0000 | 0.6667 |
| label.entity_recall | 0.6646 | 0.1721 | 0.4000 | 0.8889 |
| label.entity_total | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.fn | 1.7778 | 0.9574 | 1.0000 | 3.6667 |
| label.fp | 2.4815 | 0.8517 | 1.6667 | 4.3333 |
| label.gen_count | 5.1481 | 1.1680 | 4.0000 | 7.0000 |
| label.gold_count | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.label_sim | 0.8948 | 0.0899 | 0.7332 | 0.9906 |
| label.node_f1 | 0.5599 | 0.0908 | 0.4360 | 0.6769 |
| label.node_precision | 0.5420 | 0.0929 | 0.3278 | 0.6667 |
| label.node_recall | 0.6122 | 0.1323 | 0.4000 | 0.8000 |
| label.threshold | 0.7000 | 0.0000 | 0.7000 | 0.7000 |
| label.tp | 2.6667 | 0.6872 | 2.0000 | 4.0000 |

---
## Best / Worst Cases / 最优与最差案例

- **hierarchy.edge_f1**
  - Best / 最优: Saarland University 7 (0.3397)
  - Worst / 最差: Saarland University 5 (0.0000)
- **hierarchy.edge_fn**
  - Best / 最优: Saarland University 9 (4.6667)
  - Worst / 最差: Saarland University 1 (1.3333)
- **hierarchy.edge_fp**
  - Best / 最优: Saarland University 5 (5.0000)
  - Worst / 最差: Saarland University 8 (1.6667)
- **hierarchy.edge_precision**
  - Best / 最优: Saarland University 6 (0.4667)
  - Worst / 最差: Saarland University 5 (0.0000)
- **hierarchy.edge_recall**
  - Best / 最优: Saarland University 1 (0.3333)
  - Worst / 最差: Saarland University 5 (0.0000)
- **hierarchy.edge_tp**
  - Best / 最优: Saarland University 9 (1.3333)
  - Worst / 最差: Saarland University 5 (0.0000)
- **hierarchy.lar**
  - Best / 最优: Saarland University 1 (0.5000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.nted**
  - Best / 最优: Saarland University 8 (1.0000)
  - Worst / 最差: Saarland University 1 (0.4917)
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
  - Best / 最优: Saarland University 1 (0.6667)
  - Worst / 最差: Saarland University 5 (0.0000)
- **label.entity_recall**
  - Best / 最优: Saarland University 1 (0.8889)
  - Worst / 最差: Saarland University 8 (0.4000)
- **label.entity_total**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.fn**
  - Best / 最优: Saarland University 9 (3.6667)
  - Worst / 最差: Saarland University 5 (1.0000)
- **label.fp**
  - Best / 最优: Saarland University 1 (4.3333)
  - Worst / 最差: Saarland University 6 (1.6667)
- **label.gen_count**
  - Best / 最优: Saarland University 5 (7.0000)
  - Worst / 最差: Saarland University 8 (4.0000)
- **label.gold_count**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.label_sim**
  - Best / 最优: Saarland University 9 (0.9906)
  - Worst / 最差: Saarland University 4 (0.7332)
- **label.node_f1**
  - Best / 最优: Saarland University 5 (0.6769)
  - Worst / 最差: Saarland University 1 (0.4360)
- **label.node_precision**
  - Best / 最优: Saarland University 6 (0.6667)
  - Worst / 最差: Saarland University 1 (0.3278)
- **label.node_recall**
  - Best / 最优: Saarland University 5 (0.8000)
  - Worst / 最差: Saarland University 8 (0.4000)
- **label.threshold**
  - Best / 最优: Saarland University 1 (0.7000)
  - Worst / 最差: Saarland University 9 (0.7000)
- **label.tp**
  - Best / 最优: Saarland University 5 (4.0000)
  - Worst / 最差: Saarland University 8 (2.0000)

---
*Report Generated / 报告生成时间: 2026-07-30 11:37:12*