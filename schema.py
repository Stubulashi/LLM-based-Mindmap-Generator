from pydantic import BaseModel, Field
from typing import List, Optional

class Node(BaseModel):
    # C: 节点的唯一ID / E: Unique ID of the node
    id: int = Field(..., description="C: 节点的唯一ID / E: Unique ID of the node")
    # C: 节点显示的简短标题 / E: Short title displayed on the node
    label: str = Field(..., description="C: 节点显示的简短标题 / E: Short title displayed on the node")
    # C: 节点的背景颜色，使用莫兰迪色系变量，如 var(--node-blue)
    # E: Background color of the node, using Morandi color variables, e.g., var(--node-blue)
    color: str = Field(..., description="C: 节点的背景颜色 / E: Background color of the node")
    # C: 节点的详细条目列表 / E: List of detailed items for the node
    details: List[str] = Field(default_factory=list, description="C: 节点的详细条目列表 / E: List of detailed items for the node")
    # C: 横坐标 (200-800) / E: X-coordinate (200-800)
    x: int = Field(..., description="C: 横坐标 (200-800) / E: X-coordinate (200-800)")
    # C: 纵坐标 (100-600) / E: Y-coordinate (100-600)
    y: int = Field(..., description="C: 纵坐标 (100-600) / E: Y-coordinate (100-600)")

class Link(BaseModel):
    # C: 起始节点的ID / E: ID of the starting node
    source: int = Field(..., description="C: 起始节点的ID / E: ID of the starting node")
    # C: 目标节点的ID / E: ID of the target node
    target: int = Field(..., description="C: 目标节点的ID / E: ID of the target node")
    
    # C: 注意：前端之前使用的是 SVG path，但 LLM 很难直接计算曲线路径
    # C: 更好的做法是后端返回关系，由前端根据 source 和 target 坐标动态计算 path
    # E: Note: The frontend previously used SVG paths, but LLMs struggle to calculate curved paths directly.
    # E: A better approach is for the backend to return relationships, and let the frontend dynamically calculate the path based on source and target coordinates.

class MindMapData(BaseModel):
    nodes: List[Node]
    links: List[Link]