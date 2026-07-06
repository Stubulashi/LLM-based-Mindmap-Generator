"""
C: 核心基础设施模块 — Embedding、匈牙利对齐、数据加载、阈值定义
E: Core infrastructure — Embedding, Hungarian alignment, data loading, thresholds

Evaluation_Schema.md 相关章节 / Relevant sections: §1.1, §8.1~8.2, §7.1

模块 / Modules:
    - embedder: 多语言 Sentence-Transformer 封装 / Multilingual embedding wrapper
    - aligner: 匈牙利匹配器（共享基础设施）/ Hungarian aligner (shared infrastructure)
    - data_loader: 导图数据加载 / Mind map data loading
    - thresholds: 全指标阈值定义 / All-metric threshold definitions
"""
