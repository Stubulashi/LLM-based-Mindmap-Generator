"""
E: Tree utility functions — depth computation, parent-child extraction, edge conversion
C: 树结构工具 — 深度计算、父子关系提取、边集转换
"""
from typing import Optional


def compute_depth_map(nodes: list[dict]) -> dict[str, int]:
    """
    E: Compute depth for each node (root depth=0)
    C: 计算每个节点的深度（根 depth=0）
    """
    parent_map = {}
    for n in nodes:
        pid = n.get('parent_id')
        if pid:
            parent_map[n['id']] = pid

    depth_cache = {}

    def _depth(nid: str) -> int:
        if nid in depth_cache:
            return depth_cache[nid]
        p = parent_map.get(nid)
        if p is None:
            depth_cache[nid] = 0
        else:
            depth_cache[nid] = _depth(p) + 1
        return depth_cache[nid]

    for n in nodes:
        _depth(n['id'])
    return depth_cache


def extract_edges(nodes: list[dict], links: Optional[list[dict]] = None) -> list[tuple[str, str]]:
    """
    E: Extract parent-child edges [(parent_id, child_id), ...]
        Priority: nodes parent_id > links
    C: 提取父子边列表 [(parent_id, child_id), ...]
        优先从 nodes 的 parent_id 提取，其次从 links 提取
    """
    edges = set()

    # Method 1: Extract from nodes' parent_id / 方法1: 从 nodes 的 parent_id 提取
    for n in nodes:
        pid = n.get('parent_id')
        if pid:
            edges.add((pid, n['id']))

    # Method 2: Extract from links (supplement) / 方法2: 从 links 提取（补充）
    if links:
        for link in links:
            lt = link.get('link_type') or link.get('type', 'solid')
            if lt in ('solid',):
                edges.add((link['source'], link['target']))

    return list(edges)


def extract_parent_child_pairs(nodes: list[dict]) -> list[tuple[str, str, str, str]]:
    """
    E: Extract parent-child label pairs [(parent_label, child_label, parent_id, child_id), ...]
    C: 提取父子标签对 [(parent_label, child_label, parent_id, child_id), ...]
    """
    node_labels = {n['id']: n['label'] for n in nodes}
    pairs = []
    for n in nodes:
        pid = n.get('parent_id')
        if pid and pid in node_labels:
            pairs.append((node_labels[pid], n['label'], pid, n['id']))
    return pairs


def build_node_id_map(nodes: list[dict]) -> dict[str, dict]:
    """E: Build id-to-node mapping / C: 构建 id→node 的映射"""
    return {n['id']: n for n in nodes}


def build_parent_map(nodes: list[dict]) -> dict[str, Optional[str]]:
    """E: Build child-to-parent mapping / C: 构建 child_id → parent_id 映射"""
    return {n['id']: n.get('parent_id') for n in nodes}


def nested_to_flat(tree_nodes: list[dict], parent_id: Optional[str] = None) -> tuple[list[dict], list[dict]]:
    """
    E: Convert G6 nested tree format to flat nodes/links
    C: 将 G6 嵌套树格式转换为扁平 nodes/links
    """
    flat_nodes = []
    flat_links = []
    for tn in tree_nodes:
        nid = tn.get('id', '')
        label = tn.get('label', '')
        children = tn.get('children', [])
        flat_nodes.append({
            'id': nid,
            'label': label,
            'children': children,
            'details': tn.get('details', []),
        })
        if parent_id:
            flat_links.append({'source': parent_id, 'target': nid, 'type': 'solid'})
        child_nodes, child_links = nested_to_flat(children, nid)
        flat_nodes.extend(child_nodes)
        flat_links.extend(child_links)
    return flat_nodes, flat_links
