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
                                    "details": {"type": "array", "items": {"type": "string"}, "description": "层次化详细条目。每条以简洁前缀标识来源和类型（如 '定义:'、'关键点:'、'用户原文:'、'上下文:'），前缀语言与用户输入语言一致。融合用户输入、AI解释、转录上下文等多元信息。所有非标签的描述性、解释性内容必须存入此数组"}
                                },
                                "required": ["id", "label", "color"]
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
                                    "type": {"type": "string", "enum": ["solid", "dashed", "dotted", "reference", "contrast"], "description": "solid=父子实线, dashed=间接虚线, dotted=弱关联点线, reference=引用/依赖, contrast=对比/对立"}
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
                                    "details": {"type": "array", "items": {"type": "string"}, "description": "层次化详细条目。可从AI回复中提炼定义、解释、关键点作为补充。每条以简洁前缀标识来源（如 '定义:'、'关键点:'、'用户原文:'），前缀语言与用户输入语言一致"},
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
    # C: 阶段2 概念分组工具 — 将语义相关的概念划分为一组（不指定具体的父子从属关系）
    # E: Stage 2 Concept grouping tool — group semantically related concepts (no specific parent-child relations)
    return [
        {
            "type": "function",
            "function": {
                "name": "plan_hierarchy",
                "description": "C: 为提取的概念规划概念分组。将语义相关的概念划分为同一组，不指定具体的父子从属关系。每组包含一个或多个概念ID。\nE: Plan concept groupings for extracted concepts. Group semantically related concepts together, without specifying specific parent-child relationships. Each group contains one or more concept IDs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "description": "C: 概念分组列表。每个分组包含一个分组标识、包含的概念ID列表以及语义描述。\nE: List of concept groups. Each group has an ID, concept IDs, and a semantic label.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "group_id": {"type": "string", "description": "分组标识，如 'group_phonetics'"},
                                    "concept_ids": {"type": "array", "items": {"type": "string"}, "description": "C: 该分组包含的概念ID列表（必须来自新概念或已有节点）\nE: List of concept IDs in this group (must come from new concepts or existing nodes)"},
                                    "semantic_label": {"type": "string", "description": "C: 该分组的语义描述（如 '音位变化类型'）\nE: Semantic label for this group (e.g., 'Types of sound change')"}
                                },
                                "required": ["group_id", "concept_ids", "semantic_label"]
                            }
                        }
                    },
                    "required": ["groups"]
                }
            }
        }
    ]
