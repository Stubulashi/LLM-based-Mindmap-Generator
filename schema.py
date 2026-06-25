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
    # C: 连线类型：solid=父子实线, dashed=间接虚线, dotted=弱关联点线, reference=引用, contrast=对比
    # E: Link type: solid=parent-child, dashed=indirect, dotted=weak, reference=citation, contrast=opposition
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