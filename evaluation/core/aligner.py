"""
E: Hungarian aligner — shared infrastructure for all node-level and edge-level metrics
C: 匈牙利匹配共享基类 — 所有节点级/边级指标的基础

参考 Evaluation_Schema.md §1.1 / §8.2
Refer to Evaluation_Schema.md §1.1 / §8.2
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from evaluation.core.embedder import get_embedding_model


@dataclass
class AlignmentResult:
    """
    E: Hungarian matching result — shared foundation for all downstream metrics
    C: 匈牙利匹配结果 — 所有下游指标的共享基础
    """
    similarity_matrix: np.ndarray
    raw_matches: list[tuple[int, int, float]]          # M*: [(gen_idx, gold_idx, sim)]
    filtered_matches: list[tuple[int, int, float]]     # M_tau: filtered by threshold
    threshold: float
    model_name: str
    gen_labels: list[str] = field(default_factory=list)
    gold_labels: list[str] = field(default_factory=list)
    gen_ids: list[str] = field(default_factory=list)
    gold_ids: list[str] = field(default_factory=list)

    @property
    def tp(self) -> int:
        """E: True positives / C: 真阳性数"""
        return len(self.filtered_matches)

    @property
    def fp(self) -> int:
        """E: False positives / C: 假阳性数（生成节点中未匹配的）"""
        return len(self.gen_labels) - self.tp

    @property
    def fn(self) -> int:
        """E: False negatives / C: 假阴性数（金标准节点中未匹配的）"""
        return len(self.gold_labels) - self.tp

    @property
    def mu(self) -> dict[str, str]:
        """
        E: Node mapping gold_id → gen_id (only τ-filtered results)
        C: 节点映射 gold_id → gen_id（仅 τ 过滤后的结果）
        """
        result = {}
        for gen_idx, gold_idx, _ in self.filtered_matches:
            if gen_idx < len(self.gen_ids) and gold_idx < len(self.gold_ids):
                result[self.gold_ids[gold_idx]] = self.gen_ids[gen_idx]
        return result

    @property
    def inv_mu(self) -> dict[str, str]:
        """E: Inverse mapping gen_id → gold_id / C: 逆映射 gen_id → gold_id"""
        return {v: k for k, v in self.mu.items()}

    def node_matches_table(self) -> list[dict]:
        """E: Return readable match table / C: 返回可读的匹配表格"""
        rows = []
        for gen_idx, gold_idx, sim in self.filtered_matches:
            rows.append({
                'gold_label': self.gold_labels[gold_idx] if gold_idx < len(self.gold_labels) else '?',
                'gen_label': self.gen_labels[gen_idx] if gen_idx < len(self.gen_labels) else '?',
                'similarity': round(float(sim), 4),
            })
        return rows


class HungarianAligner:
    """
    E: Hungarian aligner — shared infrastructure
        All node-level and edge-level metrics share the same AlignmentResult.
    C: 匈牙利匹配器 — 共享基础设施
        所有节点级和边级指标共享同一个 AlignmentResult。

    用法 / Usage:
        aligner = HungarianAligner(model_name=..., threshold=0.70)
        result = aligner.align(gold_nodes, gen_nodes)
        # result.tp, result.fp, result.fn, result.mu 等
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 threshold: float = 0.70):
        self.model_name = model_name
        self.threshold = threshold
        self._embedder = None

    def _get_model(self):
        """E: Lazy-load embedding model / C: 懒加载 embedding 模型"""
        if self._embedder is None:
            self._embedder = get_embedding_model(self.model_name)
        return self._embedder

    def align(self, gold_nodes: list[dict], gen_nodes: list[dict]) -> AlignmentResult:
        """
        E: Execute one complete Hungarian matching
        C: 执行一次完整的匈牙利匹配

        步骤 / Steps:
        1. Extract labels / 提取标签
        2. Embedding + cosine similarity matrix / Embedding + 余弦相似度矩阵
        3. Hungarian optimal assignment (scipy.optimize.linear_sum_assignment) / 匈牙利最优指派
        4. Threshold filtering / 阈值过滤
        """
        from scipy.optimize import linear_sum_assignment

        gold_labels = [n.get('label', '') for n in gold_nodes]
        gen_labels = [n.get('label', '') for n in gen_nodes]
        # E: Normalize ids to str — matches tree_utils edge/depth extraction, so
        #    int ids (e.g. from JSON) never cause silent Edge-TP=0 / UAS/LAR inflation.
        # C: id 统一 str 化 — 与 tree_utils 的边/深度提取口径一致，避免整数 id 导致
        #    Edge-TP 恒 0、UAS/LAR 虚高（None==None 误判）的静默失真。
        gold_ids = [str(n.get('id', '')) for n in gold_nodes]
        gen_ids = [str(n.get('id', '')) for n in gen_nodes]

        if not gold_labels or not gen_labels:
            # E: Empty set handling / C: 空集处理
            return AlignmentResult(
                similarity_matrix=np.zeros((len(gold_labels), len(gen_labels))),
                raw_matches=[],
                filtered_matches=[],
                threshold=self.threshold,
                model_name=self.model_name,
                gen_labels=gen_labels,
                gold_labels=gold_labels,
                gen_ids=gen_ids,
                gold_ids=gold_ids,
            )

        # Step 2: Cosine similarity matrix / 余弦相似度矩阵
        model = self._get_model()
        gold_embs = model.encode(gold_labels, normalize_embeddings=True)
        gen_embs = model.encode(gen_labels, normalize_embeddings=True)
        S = gold_embs @ gen_embs.T  # (gold_n, gen_n)

        # Step 3: Hungarian optimal assignment / 匈牙利最优指派
        cost = 1.0 - S
        gold_indices, gen_indices = linear_sum_assignment(cost)

        raw_matches = []
        for g_idx, p_idx in zip(gold_indices, gen_indices):
            raw_matches.append((int(p_idx), int(g_idx), float(S[g_idx, p_idx])))

        # Step 4: Threshold filtering / 阈值过滤
        filtered = [(g, s, sim) for g, s, sim in raw_matches if sim >= self.threshold]

        return AlignmentResult(
            similarity_matrix=S,
            raw_matches=raw_matches,
            filtered_matches=filtered,
            threshold=self.threshold,
            model_name=self.model_name,
            gen_labels=gen_labels,
            gold_labels=gold_labels,
            gen_ids=gen_ids,
            gold_ids=gold_ids,
        )
