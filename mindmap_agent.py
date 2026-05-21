# /home/akku/ai-mindmap-agent/mindmap_agent.py
import json
from openai import OpenAI
from config import Config
from tools import get_mindmap_tools

class MindMapSpecialistAgent:
    def __init__(self):
        # C: 初始化 OpenAI 客户端与工具
        # E: Initialize OpenAI client and tools
        self.client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
        self.model = Config.DEEPSEEK_MODEL
        self.tools = get_mindmap_tools()

    def _get_system_prompt(self):
        # C: 返回系统提示词
        # E: Return system prompt
        return """你是一个专业的 MCP 思维导图绘图引擎。
你的任务是：根据对话历史，决定如何【增量修改】当前的思维导图。
规则：
1. 建立纵深与层级：当提到一个大概念下的子概念时，请使用 add_links 连接它们（父节点为 source，子节点为 target）。
2. 不要重复创建：如果节点已存在，只需使用 update_nodes 追加详情。
3. 坐标分布：父节点通常在上方或左侧，子节点在下方或右侧。

E: You are a professional MCP mind map drawing engine.
Your task is: Based on the conversation history, decide how to [incrementally modify] the current mind map.
Rules:
1. Establish depth and hierarchy: When a sub-concept under a major concept is mentioned, use add_links to connect them (parent node as source, child node as target).
2. Do not create duplicates: If a node already exists, simply use update_nodes to append details.
3. Coordinate distribution: Parent nodes are usually at the top or left, while child nodes are at the bottom or right."""

    def generate_map_from_context(self, chat_history: str, current_map: dict) -> dict:
        # C: 构建输入提示词
        # E: Construct input prompt
        prompt = f"C: 【当前导图状态】:\n{json.dumps(current_map, ensure_ascii=False)}\n\n【近期对话历史】:\n{chat_history}\nE: [Current Map State]:\n{json.dumps(current_map, ensure_ascii=False)}\n\n[Recent Conversation History]:\n{chat_history}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                tools=self.tools,
                tool_choice={"type": "function", "function": {"name": "modify_mind_map"}}
            )
            
            tool_call = response.choices[0].message.tool_calls[0]
            delta = json.loads(tool_call.function.arguments)
            
            # ---------------------------------------------------------
            # C: 核心：在后端进行状态合并 (State Merge)
            # E: Core: Perform state merge on the backend
            # ---------------------------------------------------------
            nodes_dict = {str(n['id']): n for n in current_map.get('nodes', [])}
            links_list = current_map.get('links', [])

            # C: 添加新节点 / E: Add new nodes
            for n in delta.get('add_nodes', []):
                nodes_dict[str(n['id'])] = n
            
            # C: 更新旧节点 / E: Update existing nodes
            for u in delta.get('update_nodes', []):
                nid = str(u['id'])
                if nid in nodes_dict:
                    nodes_dict[nid]['details'].extend(u.get('append_details', []))
            
            # C: 建立新连线 / E: Create new links
            for l in delta.get('add_links', []):
                if not any(el['source'] == l['source'] and el['target'] == l['target'] for el in links_list):
                    links_list.append(l)

            # ---------------------------------------------------------
            # C: 新增：处理删除节点逻辑
            # E: New: Handle node deletion logic
            # ---------------------------------------------------------
            for del_id in delta.get('delete_nodes', []):
                del_id_str = str(del_id)
                # C: 1. 删除节点 / E: 1. Delete node
                if del_id_str in nodes_dict:
                    del nodes_dict[del_id_str]
                # C: 2. 删除孤儿连线（只要 source 或 target 包含这个ID，统统干掉）
                # E: 2. Delete orphaned links (if source or target contains this ID, remove it)
                links_list = [
                    l for l in links_list 
                    if str(l['source']) != del_id_str and str(l['target']) != del_id_str
                ]

            return {
                "nodes": list(nodes_dict.values()),
                "links": links_list
            }
        except Exception as e:
            print(f"C: [MindMap Agent] 增量绘图失败: {e}")
            print(f"E: [MindMap Agent] Incremental drawing failed: {e}")
            return current_map