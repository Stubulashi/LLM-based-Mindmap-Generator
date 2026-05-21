from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
from openai import OpenAI

from config import Config
from mindmap_agent import MindMapSpecialistAgent # C: 引入我们的专业绘图 Agent / E: Import our professional drawing Agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# C: 初始化两个不同职能的实体
# E: Initialize two entities with different functions
chat_client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
map_specialist = MindMapSpecialistAgent()

# C: 在内存中维护一下近期的对话上下文（简单版 Memory）
# E: Maintain recent conversation context in memory (simple version of Memory)
session_memory = []

@app.get("/")
async def read_index():
    return FileResponse('index.html')

class ChatRequest(BaseModel):
    message: str
    current_map: Optional[Dict[str, Any]] = None

@app.post("/chat")
async def handle_multimodal_chat(request: ChatRequest):
    global session_memory
    try:
        user_msg = request.message
        current_map = request.current_map or {"nodes": [], "links": []}
        
        # C: 将用户的话加入记忆
        # E: Add user message to memory
        session_memory.append({"role": "user", "content": user_msg})
        
        # ---------------------------------------------------------
        # C: 阶段一：Chat Agent (DeepSeek) 负责聊天
        # E: Phase 1: Chat Agent (DeepSeek) responsible for chatting
        # ---------------------------------------------------------
        chat_sys_prompt = "你是一个亲切的 AI 助手。我们正在一起构建一个思维导图。请回答用户的问题。注意：你只负责聊天，另一个专业的 Agent 会负责画图，所以你不需要在对话中输出 JSON 代码。"
        
        # C: 截取最近 5 轮对话，防止上下文过长
        # E: Truncate to the last 5 rounds of conversation to prevent context overflow
        recent_context = [{"role": "system", "content": chat_sys_prompt}] + session_memory[-5:]
        
        chat_response = chat_client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=recent_context
        )
        ai_reply = chat_response.choices[0].message.content
        
        # C: 将 AI 的回复也加入记忆
        # E: Add AI reply to memory
        session_memory.append({"role": "assistant", "content": ai_reply})

        # ---------------------------------------------------------
        # C: 阶段二：MCP 协议模拟 (将上下文发给 MindMap Agent)
        # E: Phase 2: MCP protocol simulation (send context to MindMap Agent)
        # ---------------------------------------------------------
        # C: 规整化上下文：提取最近的一组对话发给绘图专家
        # E: Normalize context: extract the latest conversation to send to the drawing expert
        formatted_history = (
            f"【最高优先级指令】用户说：{user_msg}\n"
            f"【仅供参考的聊天记录，禁止将其中的逻辑分析画入导图】AI回复说：{ai_reply}"
        )
        
        print("C: [Orchestrator] 正在唤醒 MindMap Agent 绘制导图...")
        print("E: [Orchestrator] Waking up MindMap Agent to generate map...")
        
        # C: 调用绘图 Agent，这在真实的 MCP 中等同于发起一次 client.call_tool("update_mindmap", ...)
        # E: Call the drawing agent, which is equivalent to initiating client.call_tool("update_mindmap", ...) in real MCP
        updated_map = map_specialist.generate_map_from_context(
            chat_history=formatted_history,
            current_map=current_map
        )
        print("C: [Orchestrator] MindMap Agent 绘制完成！")
        print("E: [Orchestrator] MindMap Agent generation complete!")

        # ---------------------------------------------------------
        # C: 阶段三：合并结果返回给前端
        # E: Phase 3: Combine results and return to frontend
        # ---------------------------------------------------------
        return {
            "answer": ai_reply,
            "map": updated_map
        }

    except Exception as e:
        print(f"C: 系统运行错误: {e}")
        print(f"E: System runtime error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)