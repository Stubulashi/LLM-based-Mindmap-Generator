"""
E: Data loader — load gold/generated mind map data
C: 数据加载器 — 加载 gold/generated 导图数据
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional

from evaluation.utils.tree_utils import extract_edges, compute_depth_map


@dataclass
class MindMapData:
    """E: Unified mind map data structure / C: 统一定义的导图数据结构"""
    nodes: list[dict] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    tree: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def link_count(self) -> int:
        return len(self.links)

    def get_labels(self) -> list[str]:
        """E: Extract all node labels / C: 提取所有节点的 label"""
        return [n.get('label', '') for n in self.nodes]

    def get_node_ids(self) -> list[str]:
        """E: Extract all node IDs / C: 提取所有节点的 ID"""
        return [n.get('id', '') for n in self.nodes]

    def get_edges(self) -> list[tuple[str, str]]:
        """E: Extract parent-child edges / C: 提取父子边"""
        return extract_edges(self.nodes, self.links)

    def get_depths(self) -> dict[str, int]:
        """E: Compute depth map / C: 计算深度映射"""
        return compute_depth_map(self.nodes)

    def get_all_texts(self) -> list[str]:
        """
        E: Collect all text content (label + details) for Entity Recall
        C: 收集所有文本内容（label + details）用于 Entity Recall
        """
        texts = []
        for n in self.nodes:
            texts.append(n.get('label', ''))
            texts.extend(n.get('details', []))
        return texts


class DataLoader:
    """E: Data Loader / C: 数据加载器"""

    @staticmethod
    def from_map_file(filepath: str) -> Optional[MindMapData]:
        """
        E: Load from maps/*.json format
        C: 从 maps/*.json 格式加载
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                payload = json.load(f)

            data = payload.get('data', payload)  # support both wrapped and flat
            if isinstance(data, dict):
                nodes = data.get('nodes', [])
                links = data.get('links', [])
                tree = data.get('tree', [])
            elif isinstance(payload, dict):
                nodes = payload.get('nodes', [])
                links = payload.get('links', [])
                tree = payload.get('tree', [])
            else:
                return None

            metadata = {}
            if 'map_id' in payload:
                metadata = {k: v for k, v in payload.items() if k != 'data'}

            return MindMapData(nodes=nodes, links=links, tree=tree, metadata=metadata)
        except Exception as e:
            print(f"[DataLoader] Load failed / 加载失败 '{filepath}': {e}")
            return None

    @staticmethod
    def from_flat_dict(data: dict) -> MindMapData:
        """E: Load from {nodes, links, tree} dict / C: 从 {nodes, links, tree} dict 加载"""
        return MindMapData(
            nodes=data.get('nodes', []),
            links=data.get('links', []),
            tree=data.get('tree', []),
        )

    @staticmethod
    def from_debug_output(session_ts: str) -> Optional[MindMapData]:
        """
        E: Load latest map from debug_output/<session_ts>/
        C: 从 debug_output/<session_ts>/ 加载最新导图
        """
        import glob
        debug_dir = os.path.join("debug_output", session_ts)
        if not os.path.isdir(debug_dir):
            return None
        # Load map_final.json or most recently modified JSON
        # C: 加载 map_final.json 或最新修改的 JSON
        candidates = sorted(glob.glob(os.path.join(debug_dir, "*.json")))
        if not candidates:
            return None
        return DataLoader.from_map_file(candidates[-1])
