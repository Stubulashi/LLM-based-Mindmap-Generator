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
                                    "details": {"type": "array", "items": {"type": "string"}, "description": "详细解释和说明。所有非标签的描述性、解释性内容必须存入此数组"},
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