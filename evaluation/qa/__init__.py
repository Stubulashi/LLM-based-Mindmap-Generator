"""
C: §3 下游 QA 评估模块
E: §3 Downstream QA Evaluation Module

Evaluation_Schema.md §3
包含 / Includes:
  - 3.1 实验设计 (对照组/实验组对比)
  - 3.2 题型设计原则 (40%事实检索 + 40%关系推理 + 20%综合应用)
  - 3.3 评分标准 (BLEU-4 + ROUGE-L + BERTScore)
  - 3.4 Prompt 设计要求

需要 / Requires:
  - 预置问答问题集 / Preset question set
  - LLM API 访问 (复用 Config.LLM_*)
"""
