from pydantic import BaseModel, Field
from typing import List, Optional

class Node(BaseModel):
    id: int = Field(..., description="节点的唯一ID")
    label: str = Field(..., description="节点显示的简短标题")
    color: str = Field(..., description="节点的背景颜色，使用莫兰迪色系变量，如 var(--node-blue)")
    details: List[str] = Field(default_factory=list, description="节点的详细条目列表")
    x: int = Field(..., description="横坐标 (200-800)")
    y: int = Field(..., description="纵坐标 (100-600)")

class Link(BaseModel):
    source: int = Field(..., description="起始节点的ID")
    target: int = Field(..., description="目标节点的ID")
    # 注意：前端之前使用的是 SVG path，但 LLM 很难直接计算曲线路径
    # 更好的做法是后端返回关系，由前端根据 source 和 target 坐标动态计算 path

class MindMapData(BaseModel):
    nodes: List[Node]
    links: List[Link]
