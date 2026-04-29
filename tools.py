# /home/akku/ai-mindmap-agent/tools.py
def get_mindmap_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "modify_mind_map",
                "description": "增量更新思维导图。根据对话，提取需要【新增】的节点、需要【更新细节】的已有节点，以及建立层级关系的【连线】。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "add_nodes": {
                            "type": "array",
                            "description": "需要全新添加的节点",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "唯一英文标识，如 'node_tech'"},
                                    "label": {"type": "string", "description": "简短标题"},
                                    "color": {"type": "string", "description": "背景色变量，如 var(--node-blue), var(--node-green), var(--node-red)"},
                                    "details": {"type": "array", "items": {"type": "string"}},
                                    "x": {"type": "integer", "description": "横坐标 200-1000"},
                                    "y": {"type": "integer", "description": "纵坐标 100-800"}
                                },
                                "required": ["id", "label", "color", "x", "y"]
                            }
                        },
                        "update_nodes": {
                            "type": "array",
                            "description": "需要追加 detail 内容的已有节点",
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
                            "description": "表示节点之间层级和从属关系的连线",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source": {"type": "string", "description": "父节点ID"},
                                    "target": {"type": "string", "description": "子节点ID"},
                                    "type": {"type": "string", "enum": ["solid", "dashed"], "description": "实线表示直接从属，虚线表示相关或参考"}
                                },
                                "required": ["source", "target", "type"]
                            }
                        }
                    }
                }
            }
        }
    ]

def get_mindmap_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "modify_mind_map",
                "description": "增量更新思维导图。可以新增、更新细节、连线，以及【删除】节点。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        # ... 保留之前的 add_nodes, update_nodes, add_links ...
                        "delete_nodes": {
                            "type": "array",
                            "description": "需要删除的节点ID列表。如果用户要求移除某个概念，将其ID放入此列表。",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
    ]