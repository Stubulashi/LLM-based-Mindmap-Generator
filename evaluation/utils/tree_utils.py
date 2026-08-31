"""
E: Tree utility functions — depth computation, parent-child extraction, edge conversion
C: 树结构工具 — 深度计算、父子关系提取、边集转换
"""
from typing import Optional


# E: Link types considered hierarchical edges (tree semantics)
# C: 视为层级边的连线类型（保持树语义）
# E: Derived from schema.LINK_TYPE_SCHEMA (hierarchical=True); fallback keeps solid/dashed/containment
# C: 从 schema.LINK_TYPE_SCHEMA 派生（hierarchical=True）；回退保持 solid/dashed/containment
try:
    from schema import LINK_TYPE_SCHEMA
    HIERARCHY_LINK_TYPES = tuple(
        t for t, meta in LINK_TYPE_SCHEMA.items() if meta['hierarchical']
    )
except ImportError:
    HIERARCHY_LINK_TYPES = ('solid', 'dashed', 'containment')


def _build_parent_map_from_links(nodes: list[dict], links: list[dict]) -> dict[str, str]:
    """E: Derive child→parent map from links (solid/dashed only).
    C: 从 links（仅 solid/dashed）推导 child→parent 映射。"""
    node_ids = {str(n.get('id', '')) for n in nodes}
    parent_map: dict[str, str] = {}
    for link in links:
        src = str(link.get('source'))
        tgt = str(link.get('target'))
        if src not in node_ids or tgt not in node_ids:
            continue
        lt = link.get('link_type') or link.get('type', 'solid')
        if lt not in HIERARCHY_LINK_TYPES:
            continue
        # C: 多入边时保留第一条（与 flatten_to_tree 的 visited 语义一致）
        # E: Keep first incoming edge (consistent with flatten_to_tree visited semantics)
        if tgt not in parent_map:
            parent_map[tgt] = src
    return parent_map


def _build_parent_map_from_nested_tree(tree_nodes: list[dict], parent_map: dict[str, str], parent_id: Optional[str] = None) -> None:
    """
    E: Recursively derive child->parent map from nested tree (mirrors _extract_edges_from_tree).
    C: 递归从嵌套树推导 child->parent 映射（与 _extract_edges_from_tree 一致）。
    """
    for tn in tree_nodes:
        nid = str(tn.get('id', ''))
        if parent_id is not None and nid and nid not in parent_map:
            parent_map[nid] = parent_id
        children = _as_tree_list(tn.get('children'))
        if children:
            _build_parent_map_from_nested_tree(children, parent_map, nid)


def compute_depth_map(nodes: list[dict], links: Optional[list[dict]] = None,
                      tree: Optional[list[dict]] = None) -> dict[str, int]:
    """
    E: Compute depth for each node (root depth=0)
        Falls back to links when parent_id is missing (flat maps without parent_id).
    C: 计算每个节点的深度（根 depth=0）
        parent_id 缺失时从 links 推导（无 parent_id 的扁平导图）；
        新增 tree 递归兜底，覆盖 flatten 后丢失 parent_id 的节点。
    """
    parent_map = {}
    for n in nodes:
        pid = n.get('parent_id')
        if pid:
            parent_map[str(n.get('id', ''))] = str(pid)

    if tree:
        _build_parent_map_from_nested_tree(_as_tree_list(tree), parent_map)

    if links:
        link_parents = _build_parent_map_from_links(nodes, links)
        for child, parent in link_parents.items():
            if child not in parent_map:
                parent_map[child] = parent

    depth_cache = {}

    def _depth(start_nid: str) -> int:
        # E: Iterative with in-path guard against cycles (parent_id loops)
        # C: 迭代计算 + 路径内防环（防止 parent_id 成环时无限递归）
        if start_nid in depth_cache:
            return depth_cache[start_nid]
        stack = []
        cur = start_nid
        on_path: set[str] = set()
        while parent_map.get(cur) is not None:
            if cur in on_path:  # E: loop detected / C: 检测到环
                break
            on_path.add(cur)
            stack.append(cur)
            cur = parent_map[cur]
        # E: base depth at deepest reachable anchor / C: 到最深可达锚点的基准深度
        depth = 0 if cur not in depth_cache else depth_cache[cur]
        # E: walk back assigning depths / C: 回溯赋值深度
        for node in reversed(stack):
            depth += 1
            depth_cache[node] = depth
        depth_cache[start_nid] = depth_cache.get(start_nid, depth)
        return depth_cache[start_nid]

    for n in nodes:
        _depth(n.get('id', ''))
    return depth_cache


def _as_tree_list(tree) -> list[dict]:
    """E: Normalize nested `tree` into a list of nodes (accept single-dict root too).
    C: 将嵌套 `tree` 统一为节点列表（兼容单个 dict 根的形式）。"""
    if tree is None:
        return []
    if isinstance(tree, dict):
        return [tree]
    return tree or []


def _extract_edges_from_tree(tree_nodes: list[dict], edges: set[tuple[str, str]], parent_id: Optional[str] = None,
                             flat_ids: Optional[set[str]] = None) -> None:
    """
    E: Recursively extract edges from nested G6 tree structure,
        covering nodes whose parent_id is dropped during flattening.
        When flat_ids is given, only edges whose endpoints exist in the flat
        node list are kept (filters G6 virtual roots / dangling ids that would
        otherwise count as permanent FN/FP and distort Edge metrics).
    C: 递归从 G6 嵌套树结构中提取边，
        覆盖扁平化（flatten）后丢失 parent_id 的节点。
        给定 flat_ids 时，仅保留两端都存在于扁平节点列表的边
        （过滤 G6 虚拟根/悬空 id，避免其恒计入 FN/FP 扭曲 Edge 指标）。
    """
    for tn in tree_nodes:
        nid = str(tn.get('id', ''))
        if parent_id is not None and nid:
            if flat_ids is None or (parent_id in flat_ids and nid in flat_ids):
                edges.add((parent_id, nid))
        children = _as_tree_list(tn.get('children'))
        if children:
            _extract_edges_from_tree(children, edges, nid, flat_ids)


def extract_edges(nodes: list[dict], links: Optional[list[dict]] = None,
                  tree: Optional[list[dict]] = None) -> list[tuple[str, str]]:
    """
    E: Extract parent-child edges [(parent_id, child_id), ...]
        Priority: tree (nested) > nodes parent_id > links
    C: 提取父子边列表 [(parent_id, child_id), ...]
        优先级：tree（嵌套）> nodes 的 parent_id > links。
        新增 tree 递归解析，兜底 flatten 后丢失 parent_id 的节点，
        避免其成为「视觉上存在、边集合缺失」的孤儿。
    """
    edges = set()

    # Method 0: From nested tree (covers flatten-dropped parent_id) / 方法0: 从嵌套树提取（兜底扁平化丢掉的 parent_id）
    if tree:
        # E: Filter dangling ids unless the flat node list is empty (empty list
        #    keeps legacy behaviour where the tree alone defines the edges).
        # C: 过滤悬空 id；若扁平节点列表为空则保持旧行为（仅由 tree 定义边）
        flat_ids = {str(n.get('id', '')) for n in nodes} or None
        _extract_edges_from_tree(_as_tree_list(tree), edges, flat_ids=flat_ids)

    # Method 1: Extract from nodes' parent_id / 方法1: 从 nodes 的 parent_id 提取
    for n in nodes:
        pid = n.get('parent_id')
        if pid:
            edges.add((str(pid), str(n.get('id', ''))))

    # Method 2: Extract from links (supplement) / 方法2: 从 links 提取（补充）
    if links:
        node_children = {c for _, c in edges}
        for link in links:
            src = link.get('source')
            tgt = link.get('target')
            if src is None or tgt is None:
                continue
            lt = link.get('link_type') or link.get('type', 'solid')
            if lt in HIERARCHY_LINK_TYPES:
                edges.add((str(src), str(tgt)))
            elif str(tgt) not in node_children:
                # E: Non-hierarchical link (e.g. reference) — only promote to an edge
                #    when the target has no parent yet, keeping visual tree consistent.
                # C: 非层级边（如 reference）— 仅当 target 尚无父节点时才提升为边，
                #    与 tree 视图的父子关系保持一致。
                node_children.add(str(tgt))
                edges.add((str(src), str(tgt)))

    return list(edges)


def extract_parent_child_pairs(nodes: list[dict], links: Optional[list[dict]] = None) -> list[tuple[str, str, str, str]]:
    """
    E: Extract parent-child label pairs [(parent_label, child_label, parent_id, child_id), ...]
        Falls back to links (solid/dashed) when nodes lack parent_id.
    C: 提取父子标签对 [(parent_label, child_label, parent_id, child_id), ...]
        节点无 parent_id 时从 links（solid/dashed）推导。
    """
    node_labels = {str(n.get('id', '')): n.get('label', '') for n in nodes}
    pairs = []
    seen: set[tuple[str, str]] = set()
    for n in nodes:
        pid = n.get('parent_id')
        if pid and str(pid) in node_labels:
            key = (str(pid), str(n.get('id', '')))
            if key not in seen:
                seen.add(key)
                pairs.append((node_labels[str(pid)], n.get('label', ''), str(pid), str(n.get('id', ''))))

    if links:
        link_parents = _build_parent_map_from_links(nodes, links)
        for child, parent in link_parents.items():
            key = (parent, child)
            if key not in seen and parent in node_labels:
                seen.add(key)
                pairs.append((node_labels[parent], node_labels.get(child, ''), parent, child))
    return pairs


def build_node_id_map(nodes: list[dict]) -> dict[str, dict]:
    """E: Build id-to-node mapping / C: 构建 id→node 的映射"""
    return {str(n.get('id', '')): n for n in nodes if n.get('id') is not None}


def build_parent_map(nodes: list[dict]) -> dict[str, Optional[str]]:
    """E: Build child-to-parent mapping / C: 构建 child_id → parent_id 映射"""
    return {str(n.get('id', '')): n.get('parent_id') for n in nodes if n.get('id') is not None}


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
