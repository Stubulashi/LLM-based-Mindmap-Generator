# /home/akku/ai-mindmap-agent/mindmap_agent.py
import json
from openai import OpenAI
from config import Config
from tools import get_mindmap_tools

class MindMapSpecialistAgent:
    def __init__(self):
        self.client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
        self.model = Config.DEEPSEEK_MODEL
        self.tools = get_mindmap_tools()

    def _get_system_prompt(self):
        return """你是一个专业的 MCP 思维导图绘图引擎，遵循 ReAct（Reasoning + Acting）模式工作。
你的任务是：根据对话历史，对当前导图进行【增量修改】，而非从头重建。

【ReAct 工作流程 - 每轮调用前必须在心中完成】
步骤一（READ）：阅读当前导图全量结构。识别已有节点、它们的父子关系、以及各节点的 details 内容。
步骤二（REASON）：对照近期对话，推理需要做什么：
  - 对话中出现了哪些新概念？→ 用 add_nodes 创建，精简为原子化标签
  - 哪些概念是对已有节点的补充？→ 用 update_nodes 追加 details
  - 哪些新关系需要建立？→ 用 add_links 连接
  - 哪些内容已被推翻或冗余？→ 用 delete_nodes 移除
步骤三（ACT）：调用 modify_mind_map 工具，只传递增量差异（delta），不要重建整个 map。

【原子化标签规则 - 必须严格遵守】
1. 节点 label 必须是精简的核心名词或短语，最多 2 个词。
2. 严禁使用完整句子作为 label！例如：
   - ❌ 错误：'chicken has rabbies'
   - ✅ 正确：label='Rabies', details=['Discussed that chickens can have rabbies']
   - ❌ 错误：'I am a cat that likes fish'
   - ✅ 正确：label='Cat', details=['Likes fish', 'Self-identifies as a cat']
3. 所有解释性、描述性、逻辑性内容必须放入 details 数组。

【常规绘图规则】
4. 建立纵深与层级，使用 add_links 连接父子节点（source=父, target=子）。
5. 不要重复创建：如果节点已存在，使用 update_nodes 追加详情到其 details。
6. 坐标分布：父节点在上方/左侧，子节点在下方/右侧。避免与已有节点坐标重叠。

【语言规则 - 必须严格遵守】
7. 检测用户使用的语言（English, 中文, Deutsch, Français, Español, 日本語 等）。
8. 所有 label 和 details 必须与用户输入语言完全一致。
9. 绝对不要将节点内容切换为其他语言，包括中文。"""

    def generate_map_from_context(self, chat_history: str, current_map: dict) -> dict:
        prompt = f"""【当前导图全量状态 - 请仔细阅读】
节点列表: {json.dumps(current_map.get('nodes', []), ensure_ascii=False)}
连线列表: {json.dumps(current_map.get('links', []), ensure_ascii=False)}

【最新对话上下文】
{chat_history}

---
请按照 ReAct 模式处理：
1. 先阅读上方导图结构，理解现有节点和层级关系
2. 再根据对话内容推理需要的增量修改
3. 最后调用 modify_mind_map 工具提交增量 delta"""
        
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
            
            # --- 核心：在后端进行状态合并 (State Merge) ---
            nodes_dict = {str(n['id']): n for n in current_map.get('nodes', [])}
            links_list = current_map.get('links', [])

            # 添加新节点
            for n in delta.get('add_nodes', []):
                nodes_dict[str(n['id'])] = n
            
            # 更新旧节点
            for u in delta.get('update_nodes', []):
                nid = str(u['id'])
                if nid in nodes_dict:
                    nodes_dict[nid]['details'].extend(u.get('append_details', []))
            
            # 建立新连线
            for l in delta.get('add_links', []):
                if not any(el['source'] == l['source'] and el['target'] == l['target'] for el in links_list):
                    links_list.append(l)

            # --- 新增：处理删除节点逻辑 ---
            for del_id in delta.get('delete_nodes', []):
                del_id_str = str(del_id)
                # 1. 删节点
                if del_id_str in nodes_dict:
                    del nodes_dict[del_id_str]
                # 2. 删孤儿连线（只要 source 或 target 包含这个ID，统统干掉）
                links_list = [
                    l for l in links_list 
                    if str(l['source']) != del_id_str and str(l['target']) != del_id_str
                ]

            return {
                "nodes": list(nodes_dict.values()),
                "links": links_list
            }
        except Exception as e:
            print(f"[MindMap Agent] 增量绘图失败: {e}")
            return current_map