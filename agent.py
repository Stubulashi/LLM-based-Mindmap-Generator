# /home/akku/ai-mindmap-agent/agent.py
import json
from openai import OpenAI
from config import DEEPSEEK_CONFIG
from tools import get_mindmap_tools

class MindMapAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_CONFIG["api_key"],
            base_url=DEEPSEEK_CONFIG["base_url"]
        )
        self.model = DEEPSEEK_CONFIG["model"]
        self.tools = get_mindmap_tools()

    def chat_and_map(self, user_text: str, current_map: dict):
        messages = [
            {"role": "system", "content": "你是一个集成了思维导图工具的 Agent。每一轮对话，你都必须评估是否需要更新导图。如果是，请调用 update_mind_map 工具。"},
            {"role": "user", "content": f"当前导图状态: {json.dumps(current_map)}\n\n用户消息: {user_text}"}
        ]

        # 第一阶段：获取意图
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto" # 自动决定是否画图
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # 如果 DeepSeek 决定画图
        final_map = current_map
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name == "update_mind_map":
                    # 真实解析 Agent 想要生成的地图
                    final_map = json.loads(tool_call.function.arguments)
        
        # 即使画了图，AI 也要正常说话
        # 第二阶段：生成对话文本
        # 注意：这里我们简化逻辑，如果 AI 没说话，我们给它一个默认回复
        ai_answer = response_message.content or "我已经为您同步更新了思维导图。"
        
        return {
            "answer": ai_answer,
            "map": final_map
        }