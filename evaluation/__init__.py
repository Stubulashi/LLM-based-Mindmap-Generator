"""
C: 思维导图生成质量评估框架
E: Mind Map Generation Quality Assessment Framework

Evaluation_Schema.md v1.5 — 全维度评估体系 / Full-dimension evaluation system
包含 7 大维度 / Includes 7 dimensions:
  §1: 节点标签质量 / Node Label Quality
  §2: 层级结构正确率 / Hierarchy Structure Accuracy
  §3: 下游 QA 测试 / Downstream QA Utility
  §4: 生成效率与 STT 保真度 / Generation Efficiency & STT Fidelity
  §5: 多语言适应性与鲁棒性 / Multilingual Adaptability & Robustness
  §6: 人工评估与自动化对齐 / Human Evaluation & Automated Alignment
  §7: 综合评估汇总 / Summary & Aggregation

核心入口 / Core Entry:
    from evaluation.run_evaluation import main
    main()
"""
