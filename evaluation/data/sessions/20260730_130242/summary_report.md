# Batch Evaluation Summary Report

**Batch Timestamp / 批次时间**: 20260730_130242
**Total Pairs / 总配对数**: 9
**Embedding Model**: paraphrase-multilingual-MiniLM-L12-v2
**Threshold τ**: 0.7
**Methods / 评估方法**: label, hierarchy

---
## Per-Pair Results / 每对结果

| Pair / 配对 | edge_f1 | edge_fn | edge_fp | edge_precision | edge_recall | edge_tp | lar | nted | pc_f1 | pc_precision | pc_recall | pc_tp | raw_ted | uas | entity_recall | entity_total | fn | fp | gen_count | gold_count | label_sim | node_f1 | node_precision | node_recall | threshold | tp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Saarland University 1 | 0.000 | 2.000 | 9.333 | 0.000 | 0.000 | 0.000 | 0.500 | 0.285 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 0.000 | 0.667 | 3.000 | 1.000 | 8.667 | 10.667 | 3.000 | 0.855 | 0.295 | 0.190 | 0.667 | 0.700 | 2.000 |
| Saarland University 2 | 0.000 | 3.000 | 5.667 | 0.000 | 0.000 | 0.000 | 0.250 | 0.579 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.750 | 4.000 | 1.333 | 4.333 | 7.000 | 4.000 | 0.800 | 0.477 | 0.373 | 0.667 | 0.700 | 2.667 |
| Saarland University 3 | 0.000 | 3.000 | 6.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.579 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.500 | 4.000 | 2.000 | 5.000 | 7.000 | 4.000 | 0.916 | 0.366 | 0.290 | 0.500 | 0.700 | 2.000 |
| Saarland University 4 | 0.000 | 3.000 | 9.333 | 0.000 | 0.000 | 0.000 | 0.333 | 0.384 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.750 | 4.000 | 1.000 | 7.667 | 10.667 | 4.000 | 0.757 | 0.414 | 0.288 | 0.750 | 0.700 | 3.000 |
| Saarland University 5 | 0.000 | 4.000 | 4.667 | 0.333 | 0.000 | 0.000 | 0.133 | 0.568 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.133 | 0.933 | 5.000 | 0.333 | 4.333 | 9.000 | 5.000 | 0.951 | 0.670 | 0.526 | 0.933 | 0.700 | 4.667 |
| Saarland University 6 | 0.148 | 2.333 | 5.000 | 0.111 | 0.222 | 0.667 | 0.361 | 0.579 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.389 | 0.750 | 4.000 | 1.000 | 4.000 | 7.000 | 4.000 | 0.810 | 0.560 | 0.448 | 0.750 | 0.700 | 3.000 |
| Saarland University 7 | 0.000 | 3.000 | 8.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.448 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.500 | 4.000 | 2.000 | 7.000 | 9.000 | 4.000 | 0.990 | 0.309 | 0.224 | 0.500 | 0.700 | 2.000 |
| Saarland University 8 | 0.000 | 4.000 | 3.667 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.000 | 0.200 | 5.000 | 4.000 | 3.667 | 4.667 | 5.000 | 0.867 | 0.207 | 0.217 | 0.200 | 0.700 | 1.000 |
| Saarland University 9 | 0.000 | 6.000 | 7.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.879 | 0.000 | 1.000 | 0.000 | 0.000 | 7.000 | 0.000 | 0.333 | 7.000 | 4.667 | 5.667 | 8.000 | 7.000 | 0.991 | 0.309 | 0.297 | 0.333 | 0.700 | 2.333 |

---
## Summary Statistics / 汇总统计

| Metric / 指标 | Mean / 均值 | Std / 标准差 | Min / 最小 | Max / 最大 |
|---|---|---|---|---|
| hierarchy.edge_f1 | 0.0165 | 0.0494 | 0.0000 | 0.1481 |
| hierarchy.edge_fn | 3.3704 | 1.1837 | 2.0000 | 6.0000 |
| hierarchy.edge_fp | 6.5185 | 2.0352 | 3.6667 | 9.3333 |
| hierarchy.edge_precision | 0.0494 | 0.1126 | 0.0000 | 0.3333 |
| hierarchy.edge_recall | 0.0247 | 0.0741 | 0.0000 | 0.2222 |
| hierarchy.edge_tp | 0.0741 | 0.2222 | 0.0000 | 0.6667 |
| hierarchy.lar | 0.1753 | 0.1921 | 0.0000 | 0.5000 |
| hierarchy.nted | 0.5892 | 0.2257 | 0.2853 | 1.0000 |
| hierarchy.pc_f1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_precision | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| hierarchy.pc_recall | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_tp | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.raw_ted | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| hierarchy.uas | 0.0580 | 0.1317 | 0.0000 | 0.3889 |
| label.entity_recall | 0.5982 | 0.2330 | 0.2000 | 0.9333 |
| label.entity_total | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.fn | 1.9259 | 1.4699 | 0.3333 | 4.6667 |
| label.fp | 5.5926 | 1.7856 | 3.6667 | 8.6667 |
| label.gen_count | 8.1111 | 1.9437 | 4.6667 | 10.6667 |
| label.gold_count | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.label_sim | 0.8818 | 0.0851 | 0.7575 | 0.9908 |
| label.node_f1 | 0.4007 | 0.1459 | 0.2074 | 0.6699 |
| label.node_precision | 0.3171 | 0.1124 | 0.1902 | 0.5265 |
| label.node_recall | 0.5889 | 0.2278 | 0.2000 | 0.9333 |
| label.threshold | 0.7000 | 0.0000 | 0.7000 | 0.7000 |
| label.tp | 2.5185 | 1.0153 | 1.0000 | 4.6667 |

---
## Best / Worst Cases / 最优与最差案例

- **hierarchy.edge_f1**
  - Best / 最优: Saarland University 6 (0.1481)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_fn**
  - Best / 最优: Saarland University 9 (6.0000)
  - Worst / 最差: Saarland University 1 (2.0000)
- **hierarchy.edge_fp**
  - Best / 最优: Saarland University 1 (9.3333)
  - Worst / 最差: Saarland University 8 (3.6667)
- **hierarchy.edge_precision**
  - Best / 最优: Saarland University 5 (0.3333)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_recall**
  - Best / 最优: Saarland University 6 (0.2222)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_tp**
  - Best / 最优: Saarland University 6 (0.6667)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.lar**
  - Best / 最优: Saarland University 1 (0.5000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.nted**
  - Best / 最优: Saarland University 8 (1.0000)
  - Worst / 最差: Saarland University 1 (0.2853)
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
  - Best / 最优: Saarland University 6 (0.3889)
  - Worst / 最差: Saarland University 9 (0.0000)
- **label.entity_recall**
  - Best / 最优: Saarland University 5 (0.9333)
  - Worst / 最差: Saarland University 8 (0.2000)
- **label.entity_total**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.fn**
  - Best / 最优: Saarland University 9 (4.6667)
  - Worst / 最差: Saarland University 5 (0.3333)
- **label.fp**
  - Best / 最优: Saarland University 1 (8.6667)
  - Worst / 最差: Saarland University 8 (3.6667)
- **label.gen_count**
  - Best / 最优: Saarland University 1 (10.6667)
  - Worst / 最差: Saarland University 8 (4.6667)
- **label.gold_count**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.label_sim**
  - Best / 最优: Saarland University 9 (0.9908)
  - Worst / 最差: Saarland University 4 (0.7575)
- **label.node_f1**
  - Best / 最优: Saarland University 5 (0.6699)
  - Worst / 最差: Saarland University 8 (0.2074)
- **label.node_precision**
  - Best / 最优: Saarland University 5 (0.5265)
  - Worst / 最差: Saarland University 1 (0.1902)
- **label.node_recall**
  - Best / 最优: Saarland University 5 (0.9333)
  - Worst / 最差: Saarland University 8 (0.2000)
- **label.threshold**
  - Best / 最优: Saarland University 1 (0.7000)
  - Worst / 最差: Saarland University 9 (0.7000)
- **label.tp**
  - Best / 最优: Saarland University 5 (4.6667)
  - Worst / 最差: Saarland University 8 (1.0000)

---
*Report Generated / 报告生成时间: 2026-07-30 13:10:49*