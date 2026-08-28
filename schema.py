from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Node(BaseModel):
    # C: 节点的唯一ID（统一为字符串） / E: Unique ID of the node (unified as string)
    id: str = Field(..., description="C: 节点的唯一ID / E: Unique ID of the node")
    # C: 节点显示的简短标题 / E: Short title displayed on the node
    label: str = Field(..., description="C: 节点显示的简短标题 / E: Short title displayed on the node")
    # C: 节点的背景颜色，使用莫兰迪色系变量，如 var(--node-blue)
    # E: Background color of the node, using Morandi color variables, e.g., var(--node-blue)
    color: str = Field(..., description="C: 节点的背景颜色 / E: Background color of the node")
    # C: 节点的详细条目列表 / E: List of detailed items for the node
    details: List[str] = Field(default_factory=list, description="C: 节点的详细条目列表 / E: List of detailed items for the node")
    # C: 父节点ID（根节点为None） / E: Parent node ID (None for root nodes)
    parent_id: Optional[str] = Field(default=None, description="C: 父节点ID / E: Parent node ID")
    # C: 子节点列表（G6嵌套树格式，后端填充） / E: Children list (G6 nested tree format, filled by backend)
    children: Optional[List['Node']] = Field(default=None, description="C: 子节点列表 / E: Children list")
    # C: 折叠状态 / E: Collapse state
    collapsed: bool = Field(default=False, description="C: 折叠状态 / E: Collapse state")
    # C: 节点坐标X（可选，拖拽后由前端设置） / E: Node X coordinate (optional, set by frontend after drag)
    x: Optional[float] = Field(default=None, description="C: 节点坐标X / E: Node X coordinate")
    # C: 节点坐标Y（可选，拖拽后由前端设置） / E: Node Y coordinate (optional, set by frontend after drag)
    y: Optional[float] = Field(default=None, description="C: 节点坐标Y / E: Node Y coordinate")
    # C: 用户手动定位标记（true=跳过自动布局） / E: User positioned flag (true=skip auto-layout)
    userPositioned: bool = Field(default=False, description="C: 用户手动定位标记 / E: User positioned flag")
    # C: G6内部元数据标记（序列化为 _isVirtual, _isRoot, _depth, _hasChildren）
    # E: G6 internal metadata flags (serialized as _isVirtual, _isRoot, _depth, _hasChildren)
    isVirtual: bool = Field(default=False, serialization_alias='_isVirtual', description="C: 虚拟根节点标记 / E: Virtual root flag")
    isRoot: bool = Field(default=False, serialization_alias='_isRoot', description="C: 根节点标记 / E: Root node flag")
    depth: int = Field(default=0, serialization_alias='_depth', description="C: 节点深度 / E: Node depth")
    hasChildren: bool = Field(default=False, serialization_alias='_hasChildren', description="C: 是否有子节点 / E: Whether has children")

class Link(BaseModel):
    # C: 连线唯一ID（可选） / E: Unique link ID (optional)
    id: Optional[str] = Field(default=None, description="C: 连线唯一ID / E: Unique link ID")
    # C: 起始节点的ID / E: ID of the starting node
    source: str = Field(..., description="C: 起始节点的ID / E: ID of the starting node")
    # C: 目标节点的ID / E: ID of the target node
    target: str = Field(..., description="C: 目标节点的ID / E: ID of the target node")
    # C: 连线类型（见 LINK_TYPE_SCHEMA，合法值由 VALID_LINK_TYPES 约束）
    # E: Link type (see LINK_TYPE_SCHEMA; valid values constrained by VALID_LINK_TYPES)
    link_type: str = Field(default="solid", description="C: 连线类型 / E: Link type")
    # C: 连线上的说明文字（可选） / E: Optional label on the link
    label: Optional[str] = Field(default=None, description="C: 连线标签 / E: Link label")

class TreeMapData(BaseModel):
    # C: G6嵌套树格式（前端graph.setData直接消费）
    # E: G6 nested tree format (directly consumed by frontend graph.setData)
    tree: List[dict] = Field(default_factory=list, description="C: G6嵌套树数据 / E: G6 nested tree data")
    # C: 扁平节点列表（用于增量更新回传） / E: Flat node list (for incremental update round-trip)
    nodes: List[Node] = Field(default_factory=list, description="C: 扁平节点列表 / E: Flat node list")
    # C: 扁平连线列表（用于增量更新回传） / E: Flat link list (for incremental update round-trip)
    links: List[Link] = Field(default_factory=list, description="C: 扁平连线列表 / E: Flat link list")

# C: 向后兼容 / E: Backward compatibility
MindMapData = TreeMapData

# =========================================================
# C: 节点颜色映射表 — 前后端共享的单一事实来源
#    前端 index.html 的 CSS_COLOR_MAP 必须与此表保持同步
#    后端 mindmap_agent.py 的 VALID_COLORS 必须与此表的 keys 保持同步
# E: Node color schema — single source of truth shared by frontend and backend
#    Frontend CSS_COLOR_MAP in index.html MUST stay in sync with this table
#    Backend VALID_COLORS in mindmap_agent.py MUST stay in sync with keys
# =========================================================
NODE_COLOR_SCHEMA: dict[str, str] = {
    'var(--node-blue)':   '#e8f0fe',
    'var(--node-green)':  '#e6f4ea',
    'var(--node-yellow)': '#fef7e0',
    'var(--node-red)':    '#fce8e6',
    'var(--node-purple)': '#f3e8fd',
    'var(--node-orange)': '#fef3e0',
    'var(--node-teal)':   '#e0f7f4',
    'var(--node-pink)':   '#fde8f0',
}

# =========================================================
# C: 连线类型映射表 — 前后端共享的单一事实来源
#    前端 index.html 的 LINK_TYPE_SCHEMA（JS 常量）必须与此表保持同步
#    hierarchical=True 表示该类型计入父子层级边（树语义，影响评估 Edge-F1/UAS）
#    dash/arrow 用于 G6 渲染（dash 为 SVG dasharray，[] 表示实线）
# E: Link type schema — single source of truth shared by frontend and backend
#    Frontend LINK_TYPE_SCHEMA (JS const) in index.html MUST stay in sync
#    hierarchical=True means the type counts as a tree edge (affects eval Edge-F1/UAS)
#    dash/arrow drive G6 rendering (dash is SVG dasharray, [] = solid line)
# =========================================================
LINK_TYPE_SCHEMA: dict[str, dict] = {
    'solid': {
        'name_zh': '父子关系', 'name_en': 'Parent-child',
        'color': '#3b82f6', 'dash': [], 'arrow': False, 'hierarchical': True,
    },
    'dashed': {
        'name_zh': '间接关联', 'name_en': 'Indirect',
        'color': '#94a3b8', 'dash': [6, 4], 'arrow': False, 'hierarchical': True,
    },
    'containment': {
        'name_zh': '包含', 'name_en': 'Containment',
        'color': '#06b6d4', 'dash': [], 'arrow': False, 'hierarchical': True,
    },
    'dotted': {
        'name_zh': '弱关联', 'name_en': 'Weak',
        'color': '#a78bfa', 'dash': [2, 4], 'arrow': False, 'hierarchical': False,
    },
    'reference': {
        'name_zh': '引用', 'name_en': 'Reference',
        'color': '#10b981', 'dash': [], 'arrow': True, 'hierarchical': False,
    },
    'contrast': {
        'name_zh': '对比', 'name_en': 'Contrast',
        'color': '#f59e0b', 'dash': [], 'arrow': True, 'hierarchical': False,
    },
    'causal': {
        'name_zh': '因果', 'name_en': 'Causal',
        'color': '#ef4444', 'dash': [6, 4], 'arrow': True, 'hierarchical': False,
    },
}

# C: 合法连线类型集合（由 LINK_TYPE_SCHEMA 派生，禁止各处硬编码）
# E: Valid link type set (derived from LINK_TYPE_SCHEMA; no hardcoding elsewhere)
VALID_LINK_TYPES: frozenset[str] = frozenset(LINK_TYPE_SCHEMA.keys())