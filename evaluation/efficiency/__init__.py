"""
C: §4 生成效率与 STT 保真度评估模块
E: §4 Generation Efficiency & STT Fidelity Evaluation Module

Evaluation_Schema.md §4.1~4.2
包含 / Includes:
  - 4.1 端到端延迟测量 (P50/P95)
  - 4.2.1 词错率 WER (Word Error Rate)
  - 4.2.2 关键术语保留率 KTRR (Key Term Retention Rate)
  - 4.2.3 STT-导图关联分析

需要 / Requires:
  - 计时日志 / Timing logs
  - 参考文本 / Reference transcript
  - 关键术语列表 / Key terms list
"""
