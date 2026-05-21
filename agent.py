import json
from openai import OpenAI
from config import DEEPSEEK_CONFIG
from tools import get_mindmap_tools

class MindMapAgent:
    def __init__(self):
        # C: 初始化 OpenAI 客户端与模型配置
        # E: Initialize OpenAI client and model configuration
        self.client = OpenAI(
            api_key=DEEPSEEK_CONFIG["api_key"],
            base_url=DEEPSEEK_CONFIG["base_url"]
        )
        self.model = DEEPSEEK_CONFIG["model"]
        self.tools = get_mindmap_tools()

    def chat_and_map(self, user_text: str, current_map: dict):
        # C: 定义系统提示词
        # E: Define system prompt
        messages = [
            {
                "role": "system", 
                "content": (
                    "C: 你是一个集成了思维导图工具的 Agent。每一轮对话，你都必须评估是否需要更新导图。如果是，请调用 update_mind_map 工具。\n"
                    "E: You are an Agent integrated with mind map tools. In every conversation round, you must evaluate whether the mind map needs to be updated. If so, please call the update_mind_map tool."
                )
            },
            {
                "role": "user", 
                "content": f"C: 当前导图状态: {json.dumps(current_map)}\n用户消息: {user_text}\nE: Current map state: {json.dumps(current_map)}\nUser message: {user_text}"
            }
        ]

        # C: 第一阶段：获取意图
        # E: Phase 1: Determine intent
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto" # C: 自动决定是否画图 / E: Automatically decide whether to draw
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # C: 如果 DeepSeek 决定画图
        # E: If DeepSeek decides to draw
        final_map = current_map
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name == "update_mind_map":
                    # C: 真实解析 Agent 想要生成的地图
                    # E: Actually parse the map the Agent intends to generate
                    final_map = json.loads(tool_call.function.arguments)
        
        # C: 即使画了图，AI 也要正常说话
        # C: 第二阶段：生成对话文本
        # C: 注意：这里我们简化逻辑，如果 AI 没说话，我们给它一个默认回复
        # E: Even if a map is drawn, the AI should still speak normally
        # E: Phase 2: Generate conversational text
        # E: Note: We simplify the logic here; if the AI doesn't speak, we provide a default reply
        ai_answer = response_message.content or "C: 我已经为您同步更新了思维导图。\nE: I have synchronized and updated the mind map for you."
        
        return {
            "answer": ai_answer,
            "map": final_map
        }