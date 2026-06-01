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
        # C: 返回系统提示词（中英双语）
        # E: Return system prompt (bilingual CN/EN)
        return """你是一个专业的 MCP 思维导图绘图引擎，遵循 ReAct（Reasoning + Acting）模式工作。
你的任务是：根据对话历史，对当前导图进行【增量修改】，而非从头重建。

【核心铁律 - 必须严格遵守】
1. 绝对服从用户：【用户说】的内容具有绝对的权威。即使用户的逻辑是荒诞的、无厘头的或违反常理的，你也必须严格按照用户的概念拓扑直接建图。
2. 严禁生成"元节点（Meta-nodes）"：绝对不要将 AI 的逻辑分析、说教或总结画进导图。画布只用来呈现用户指定的客观概念。
3. 屏蔽 AI 发散：【AI回复说】的内容仅作为语境参考。你的图谱实体提取必须 100% 以用户提供的词汇为准。

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
7. 关联更新机制与层级隔离（重点）：当用户为现有的某个概念（如节点A）添加特征、附属物或下级概念（如节点B）时，你必须同时进行两步操作：
   - 第一步：使用 add_nodes 创建新节点 B，并使用 add_links 将其与 A 连接。
   - 第二步：必须使用 update_nodes，将这个新特征的描述语句追加到直接相关节点（A）的 details 属性中。
   - 【禁止追溯原则】：绝对禁止向上追溯！只能更新直接父节点 A，绝对不允许将该细节跨层级更新到 A 的父节点、祖父节点等更上层级中。

【语言规则 - 必须严格遵守】
8. 检测用户使用的语言（English, 中文, Deutsch, Français, Español, 日本語 等）。
9. 所有 label 和 details 必须与用户输入语言完全一致。
10. 绝对不要将节点内容切换为其他语言，包括中文。

E: You are a professional MCP mind map drawing engine following ReAct (Reasoning + Acting) mode.
Core Iron Laws: 1) Obey user's concepts absolutely - user's words have ultimate authority. 2) No meta-nodes - canvas only presents user-specified objective concepts. 3) Block AI divergence - extract entities 100% from user vocabulary, AI replies are context only.
Atomic Label Rules: labels must be ≤2 words, core nouns only, never full sentences. Push all explanatory content to details array.
Drawing Rules: Use add_links for hierarchy (source=parent, target=child). Don't duplicate nodes - use update_nodes. Parent top/left, children bottom/right. When adding child concepts, also update direct parent's details (NO upward propagation to grandparents).
Language Rules: Detect user language. All labels and details must match user's input language exactly. Never switch languages."""

    def generate_map_from_context(self, chat_history: str, current_map: dict) -> dict:
        # C: 构建 ReAct 式输入提示词
        # E: Construct ReAct-style input prompt
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