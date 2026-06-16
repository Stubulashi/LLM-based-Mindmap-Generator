# C: /home/akku/ai-mindmap-agent/tools.py
# E: /home/akku/ai-mindmap-agent/tools.py
# C: MindMap 工具定义 — 为 LLM function calling 提供 modify_mind_map 的 JSON Schema
# E: MindMap tool definitions — provides modify_mind_map JSON Schema for LLM function calling
def get_mindmap_tools():
    # C: 返回完整的工具列表，包含 add_nodes / update_nodes / add_links / delete_nodes 四个能力
    # E: Return the complete tool list, containing all four capabilities: add_nodes, update_nodes, add_links, delete_nodes
    return [
        {
            "type": "function",
            "function": {
                "name": "modify_mind_map",
                "description": "C: 增量更新思维导图。根据对话，提取需要【新增】的节点、需要【更新细节】的已有节点、建立层级关系的【连线】，以及需要【删除】的节点。\nE: Incrementally update the mind map. Based on the conversation, extract nodes to [add], existing nodes to [update details], [links] to establish hierarchical relationships, and nodes to [delete].",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "add_nodes": {
                            "type": "array",
                            "description": "C: 需要全新添加的节点——label 必须精简为核心名词（≤2词），严禁完整句子\nE: Nodes to be newly added - labels must be concise core nouns (≤2 words), full sentences are strictly prohibited",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "唯一英文标识，如 'node_cat'"},
                                    "label": {"type": "string", "description": "核心名词/短语，最多2词。反例：'chicken has rabbies'；正例：'Rabies'"},
                                    "color": {"type": "string", "description": "背景色变量，如 var(--node-blue), var(--node-green), var(--node-red)"},
                                    "details": {"type": "array", "items": {"type": "string"}, "description": "层次化详细条目。每条以简洁前缀标识来源和类型（如 '💡 定义:'、'🔑 关键点:'、'📝 用户原文:'、'📋 上下文:'）。融合用户输入、AI解释、转录上下文等多元信息。所有非标签的描述性、解释性内容必须存入此数组"},
                                    "x": {"type": "integer", "description": "横坐标 200-1200"},
                                    "y": {"type": "integer", "description": "纵坐标 50-800"}
                                },
                                "required": ["id", "label", "color", "x", "y"]
                            }
                        },
                        "update_nodes": {
                            "type": "array",
                            "description": "C: 需要追加 detail 内容的已有节点\nE: Existing nodes that need additional detail content appended",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "append_details": {"type": "array", "items": {"type": "string"}}
                                },
                                "required": ["id", "append_details"]
                            }
                        },
                        "add_links": {
                            "type": "array",
                            "description": "C: 表示节点之间层级和从属关系的连线\nE: Links representing hierarchical and affiliation relationships between nodes",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source": {"type": "string", "description": "父节点ID"},
                                    "target": {"type": "string", "description": "子节点ID"},
                                    "type": {"type": "string", "enum": ["solid", "dashed"], "description": "实线表示直接从属，虚线表示相关或参考"}
                                },
                                "required": ["source", "target", "type"]
                            }
                        },
                        "delete_nodes": {
                            "type": "array",
                            "description": "C: 需要删除的节点ID列表。如果用户要求移除某个概念，将其ID放入此列表。\nE: List of node IDs to be deleted. If the user requests removal of a concept, place its ID in this list.",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
    ]


def get_concept_extraction_tools():
    # C: 阶段1 概念提取工具 — 从对话中提取原子化概念
    # E: Stage 1 Concept extraction tool — extract atomic concepts from conversation
    return [
        {
            "type": "function",
            "function": {
                "name": "extract_concepts",
                "description": "C: 从对话中提取需要添加到导图的核心概念。仅提取用户提及的客观概念，严禁提取AI的分析或说教。\nE: Extract core concepts from the conversation to add to the mind map. Only extract objective concepts mentioned by the user, strictly prohibit extracting AI analysis or preaching.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "concepts": {
                            "type": "array",
                            "description": "C: 从对话中提取的核心概念列表\nE: List of core concepts extracted from the conversation",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "唯一英文标识，如 'node_deep_learning'"},
                                    "label": {"type": "string", "description": "核心名词/短语，最多2词。严禁完整句子"},
                                    "details": {"type": "array", "items": {"type": "string"}, "description": "层次化详细条目。可从AI回复中提炼定义、解释、关键点作为补充。每条以简洁前缀标识来源（如 '💡 定义:'、'🔑 关键点:'、'📝 用户原文:'）"},
                                    "color": {"type": "string", "description": "背景色变量，如 var(--node-blue), var(--node-green), var(--node-red)"}
                                },
                                "required": ["id", "label", "color"]
                            }
                        }
                    },
                    "required": ["concepts"]
                }
            }
        }
    ]


def get_hierarchy_planning_tools():
    # C: 阶段2 层级规划工具 — 为概念构建父子层级关系
    # E: Stage 2 Hierarchy planning tool — build parent-child hierarchy for concepts
    return [
        {
            "type": "function",
            "function": {
                "name": "plan_hierarchy",
                "description": "C: 为提取的概念规划父子层级关系。建立纵深结构，避免所有节点平铺在同一层。优先将新概念挂载到语义最相关的已有节点下。\nE: Plan parent-child hierarchy for extracted concepts. Establish depth structure, avoid flattening all nodes at the same level. Prioritize attaching new concepts under the most semantically relevant existing nodes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relations": {
                            "type": "array",
                            "description": "C: 层级关系列表。每个关系表示一对父子连线。\nE: List of hierarchy relations. Each relation represents a parent-child link.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "parent_id": {"type": "string", "description": "父节点ID（可以是已有节点或新概念）"},
                                    "child_id": {"type": "string", "description": "子节点ID（必须是新概念或已有节点）"},
                                    "type": {"type": "string", "enum": ["solid", "dashed"], "description": "实线表示直接从属，虚线表示相关或参考"}
                                },
                                "required": ["parent_id", "child_id", "type"]
                            }
                        }
                    },
                    "required": ["relations"]
                }
            }
        }
    ]