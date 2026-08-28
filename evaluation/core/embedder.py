"""
E: Embedding model wrapper — lazy loading, process-level caching, batch encoding
C: Embedding 模型封装 — 懒加载、进程内缓存、批量编码
"""
from typing import Optional
import numpy as np

_model_cache: dict[str, 'SentenceTransformer'] = {}


def get_embedding_model(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
    """E: Get/cache embedding model (in-process singleton) / C: 获取/缓存 embedding 模型（进程内单例）"""
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def compute_similarity_matrix(
    gold_labels: list[str],
    gen_labels: list[str],
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    normalize: bool = True,
) -> np.ndarray:
    """
    E: Compute cosine similarity matrix between gold and generated labels
    C: 计算金标准与生成标签之间的余弦相似度矩阵

    Returns: similarity matrix of shape (len(gold_labels), len(gen_labels))
    C: 返回: (len(gold_labels), len(gen_labels)) 的相似度矩阵
    """
    # C: 空列表保护 — 空标签集时返回空矩阵（避免 encode([]) 崩溃）
    # E: Empty-list guard — return empty matrix for empty label sets (avoid encode([]) crash)
    if not gold_labels or not gen_labels:
        return np.zeros((len(gold_labels), len(gen_labels)))

    model = get_embedding_model(model_name)
    gold_embs = model.encode(gold_labels, normalize_embeddings=normalize)
    gen_embs = model.encode(gen_labels, normalize_embeddings=normalize)
    return gold_embs @ gen_embs.T


def batch_similarity(
    queries: list[str],
    targets: list[str],
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> np.ndarray:
    """
    E: Batch query-target similarity computation (for Entity Recall)
    C: 批量查询-目标相似度计算（用于 Entity Recall）
    """
    return compute_similarity_matrix(queries, targets, model_name)
