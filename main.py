from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
from openai import OpenAI

from config import Config
from mindmap_agent import MindMapSpecialistAgent # 引入我们的专业绘图 Agent

def parse_args():
    """
    Parse cli arguments.
    """
    default_config = {
        "api_key": Config.DEEPSEEK_API_KEY,
        "base_url": Config.DEEPSEEK_BASE_URL,
        "model": Config.DEEPSEEK_MODEL,
        "timeout": Config.API_TIMEOUT
    }

    import sys
    args = sys.argv
    status = None
    for arg in args:
        if arg == "-api":
            status = arg
        elif arg == "-url":
            status = arg
        elif arg == "-model":
            status = arg
        elif arg == "-timeout":
            status = arg
        elif status == "-api":
            default_config.api_key = arg
            status = None
        elif status == "-url":
            default_config.base_url = arg
            status = None
        elif status == "-model":
            default_config.model = arg
            status = None
        elif status == "-timeout":
            default_config.timeout = int(arg)
            status = None
        else:
            quit("Error during argument parsing.")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化两个不同职能的实体
chat_client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
map_specialist = MindMapSpecialistAgent()

# 在内存中维护一下近期的对话上下文（简单版 Memory）
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
        
        # 将用户的话加入记忆
        session_memory.append({"role": "user", "content": user_msg})
        
        # ---------------------------------------------------------
        # 阶段一：Chat Agent (DeepSeek) 负责聊天
        # ---------------------------------------------------------
        chat_sys_prompt = "你是一个亲切的 AI 助手。我们正在一起构建一个思维导图。请回答用户的问题。注意：你只负责聊天，另一个专业的 Agent 会负责画图，所以你不需要在对话中输出 JSON 代码。"
        
        # 截取最近 5 轮对话，防止上下文过长
        recent_context = [{"role": "system", "content": chat_sys_prompt}] + session_memory[-5:]
        
        chat_response = chat_client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=recent_context
        )
        ai_reply = chat_response.choices[0].message.content
        
        # 将 AI 的回复也加入记忆
        session_memory.append({"role": "assistant", "content": ai_reply})

        # ---------------------------------------------------------
        # 阶段二：MCP 协议模拟 (将上下文发给 MindMap Agent)
        # ---------------------------------------------------------
        # 规整化上下文：提取最近的一组对话发给绘图专家
        formatted_history = f"用户说：{user_msg}\nAI回复说：{ai_reply}"
        
        print(f"[Orchestrator] 正在唤醒 MindMap Agent 绘制导图...")
        # 调用绘图 Agent，这在真实的 MCP 中等同于发起一次 client.call_tool("update_mindmap", ...)
        updated_map = map_specialist.generate_map_from_context(
            chat_history=formatted_history,
            current_map=current_map
        )
        print(f"[Orchestrator] MindMap Agent 绘制完成！")

        # ---------------------------------------------------------
        # 阶段三：合并结果返回给前端
        # ---------------------------------------------------------
        return {
            "answer": ai_reply,
            "map": updated_map
        }

    except Exception as e:
        print(f"系统运行错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)