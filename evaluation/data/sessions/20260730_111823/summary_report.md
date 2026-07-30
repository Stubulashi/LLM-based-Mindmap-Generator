# Batch Evaluation Summary Report

**Batch Timestamp / 批次时间**: 20260730_111823
**Total Pairs / 总配对数**: 9
**Embedding Model**: paraphrase-multilingual-MiniLM-L12-v2
**Threshold τ**: 0.7
**Methods / 评估方法**: label, hierarchy

---
## Per-Pair Results / 每对结果

| Pair / 配对 | edge_f1 | edge_fn | edge_fp | edge_precision | edge_recall | edge_tp | lar | nted | pc_f1 | pc_precision | pc_recall | pc_tp | raw_ted | uas | entity_recall | entity_total | fn | fp | gen_count | gold_count | label_sim | node_f1 | node_precision | node_recall | threshold | tp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Saarland University 1 | 0.000 | 2.000 | 4.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.600 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 0.000 | 0.667 | 3.000 | 1.000 | 3.000 | 5.000 | 3.000 | 0.851 | 0.500 | 0.400 | 0.667 | 0.700 | 2.000 |
| Saarland University 2 | 0.000 | 3.000 | 3.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.250 | 4.000 | 3.000 | 3.000 | 4.000 | 4.000 | 0.771 | 0.250 | 0.250 | 0.250 | 0.700 | 1.000 |
| Saarland University 3 | 0.000 | 3.000 | 2.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.000 | 0.500 | 4.000 | 2.000 | 1.000 | 3.000 | 4.000 | 0.864 | 0.571 | 0.667 | 0.500 | 0.700 | 2.000 |
| Saarland University 4 | 0.286 | 2.000 | 3.000 | 0.250 | 0.333 | 1.000 | 0.333 | 0.667 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.667 | 0.750 | 4.000 | 1.000 | 3.000 | 6.000 | 4.000 | 0.752 | 0.600 | 0.500 | 0.750 | 0.700 | 3.000 |
| Saarland University 5 | 0.000 | 4.000 | 4.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.000 | 0.800 | 5.000 | 1.000 | 1.000 | 5.000 | 5.000 | 0.983 | 0.800 | 0.800 | 0.800 | 0.700 | 4.000 |
| Saarland University 6 | 0.800 | 1.000 | 0.000 | 1.000 | 0.667 | 2.000 | 0.333 | 0.750 | 0.000 | 1.000 | 0.000 | 0.000 | 3.000 | 1.000 | 0.750 | 4.000 | 1.000 | 0.000 | 3.000 | 4.000 | 1.000 | 0.857 | 1.000 | 0.750 | 0.700 | 3.000 |
| Saarland University 7 | 0.286 | 2.000 | 3.000 | 0.250 | 0.333 | 1.000 | 0.000 | 0.800 | 0.000 | 1.000 | 0.000 | 0.000 | 4.000 | 0.500 | 0.500 | 4.000 | 2.000 | 3.000 | 5.000 | 4.000 | 0.990 | 0.444 | 0.400 | 0.500 | 0.700 | 2.000 |
| Saarland University 8 | 0.000 | 4.000 | 2.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 5.000 | 0.000 | 0.200 | 5.000 | 4.000 | 2.000 | 3.000 | 5.000 | 0.996 | 0.250 | 0.333 | 0.200 | 0.700 | 1.000 |
| Saarland University 9 | 0.000 | 6.000 | 2.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 7.000 | 0.000 | 0.429 | 7.000 | 5.000 | 2.000 | 4.000 | 7.000 | 0.966 | 0.364 | 0.500 | 0.286 | 0.700 | 2.000 |

---
## Summary Statistics / 汇总统计

| Metric / 指标 | Mean / 均值 | Std / 标准差 | Min / 最小 | Max / 最大 |
|---|---|---|---|---|
| hierarchy.edge_f1 | 0.1524 | 0.2726 | 0.0000 | 0.8000 |
| hierarchy.edge_fn | 3.0000 | 1.5000 | 1.0000 | 6.0000 |
| hierarchy.edge_fp | 2.5556 | 1.2360 | 0.0000 | 4.0000 |
| hierarchy.edge_precision | 0.1667 | 0.3307 | 0.0000 | 1.0000 |
| hierarchy.edge_recall | 0.1481 | 0.2422 | 0.0000 | 0.6667 |
| hierarchy.edge_tp | 0.4444 | 0.7265 | 0.0000 | 2.0000 |
| hierarchy.lar | 0.1296 | 0.2003 | 0.0000 | 0.5000 |
| hierarchy.nted | 0.8685 | 0.1651 | 0.6000 | 1.0000 |
| hierarchy.pc_f1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_precision | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| hierarchy.pc_recall | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.pc_tp | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hierarchy.raw_ted | 4.3333 | 1.2247 | 3.0000 | 7.0000 |
| hierarchy.uas | 0.2407 | 0.3829 | 0.0000 | 1.0000 |
| label.entity_recall | 0.5384 | 0.2200 | 0.2000 | 0.8000 |
| label.entity_total | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.fn | 2.2222 | 1.4814 | 1.0000 | 5.0000 |
| label.fp | 2.0000 | 1.1180 | 0.0000 | 3.0000 |
| label.gen_count | 4.2222 | 1.0929 | 3.0000 | 6.0000 |
| label.gold_count | 4.4444 | 1.1304 | 3.0000 | 7.0000 |
| label.label_sim | 0.9080 | 0.1001 | 0.7517 | 1.0000 |
| label.node_f1 | 0.5152 | 0.2172 | 0.2500 | 0.8571 |
| label.node_precision | 0.5389 | 0.2410 | 0.2500 | 1.0000 |
| label.node_recall | 0.5225 | 0.2336 | 0.2000 | 0.8000 |
| label.threshold | 0.7000 | 0.0000 | 0.7000 | 0.7000 |
| label.tp | 2.2222 | 0.9718 | 1.0000 | 4.0000 |

---
## Best / Worst Cases / 最优与最差案例

- **hierarchy.edge_f1**
  - Best / 最优: Saarland University 6 (0.8000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_fn**
  - Best / 最优: Saarland University 9 (6.0000)
  - Worst / 最差: Saarland University 6 (1.0000)
- **hierarchy.edge_fp**
  - Best / 最优: Saarland University 1 (4.0000)
  - Worst / 最差: Saarland University 6 (0.0000)
- **hierarchy.edge_precision**
  - Best / 最优: Saarland University 6 (1.0000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_recall**
  - Best / 最优: Saarland University 6 (0.6667)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.edge_tp**
  - Best / 最优: Saarland University 6 (2.0000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.lar**
  - Best / 最优: Saarland University 1 (0.5000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **hierarchy.nted**
  - Best / 最优: Saarland University 2 (1.0000)
  - Worst / 最差: Saarland University 1 (0.6000)
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
  - Worst / 最差: Saarland University 6 (3.0000)
- **hierarchy.uas**
  - Best / 最优: Saarland University 6 (1.0000)
  - Worst / 最差: Saarland University 9 (0.0000)
- **label.entity_recall**
  - Best / 最优: Saarland University 5 (0.8000)
  - Worst / 最差: Saarland University 8 (0.2000)
- **label.entity_total**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.fn**
  - Best / 最优: Saarland University 9 (5.0000)
  - Worst / 最差: Saarland University 6 (1.0000)
- **label.fp**
  - Best / 最优: Saarland University 1 (3.0000)
  - Worst / 最差: Saarland University 6 (0.0000)
- **label.gen_count**
  - Best / 最优: Saarland University 4 (6.0000)
  - Worst / 最差: Saarland University 8 (3.0000)
- **label.gold_count**
  - Best / 最优: Saarland University 9 (7.0000)
  - Worst / 最差: Saarland University 1 (3.0000)
- **label.label_sim**
  - Best / 最优: Saarland University 6 (1.0000)
  - Worst / 最差: Saarland University 4 (0.7517)
- **label.node_f1**
  - Best / 最优: Saarland University 6 (0.8571)
  - Worst / 最差: Saarland University 8 (0.2500)
- **label.node_precision**
  - Best / 最优: Saarland University 6 (1.0000)
  - Worst / 最差: Saarland University 2 (0.2500)
- **label.node_recall**
  - Best / 最优: Saarland University 5 (0.8000)
  - Worst / 最差: Saarland University 8 (0.2000)
- **label.threshold**
  - Best / 最优: Saarland University 1 (0.7000)
  - Worst / 最差: Saarland University 9 (0.7000)
- **label.tp**
  - Best / 最优: Saarland University 5 (4.0000)
  - Worst / 最差: Saarland University 8 (1.0000)

---
*Report Generated / 报告生成时间: 2026-07-30 11:21:13*