import os  
from dotenv import load_dotenv
from pathlib import Path

# C: 加载 .env 文件
# E: Load the .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """
    C: 配置管理类
       LLM_* 变量支持任意 OpenAI 兼容的模型提供商（DeepSeek / OpenAI / 本地模型等）。
       优先级: LLM_* 环境变量 > DEEPSEEK_* 环境变量 > 默认值(DeepSeek)。
       用户只需修改 .env 中的 LLM_* 变量即可切换提供商，无需改动任何代码。
    E: Configuration management class
       LLM_* variables support any OpenAI-compatible model provider (DeepSeek / OpenAI / local models etc.).
       Priority: LLM_* env vars > DEEPSEEK_* env vars > defaults (DeepSeek).
       Users only need to modify LLM_* in .env to switch providers, no code changes needed.
    """
    
    # ---------------------------------------------------------
    # C: 通用 LLM 配置（主要使用这些变量）
    #    设置方法：在 .env 中定义 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
    #    如果不设置，自动回退到 DEEPSEEK_* 变量（向后兼容）
    # E: Generic LLM config (use these primarily)
    #    Set in .env: LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
    #    If not set, auto-fallback to DEEPSEEK_* vars (backward compatible)
    # ---------------------------------------------------------
    LLM_API_KEY = (
        os.getenv('LLM_API_KEY')
        or os.getenv('DEEPSEEK_API_KEY')
    )
    LLM_BASE_URL = (
        os.getenv('LLM_BASE_URL')
        or os.getenv('DEEPSEEK_BASE_URL')
        or 'https://api.deepseek.com'
    )
    LLM_MODEL = (
        os.getenv('LLM_MODEL')
        or os.getenv('DEEPSEEK_MODEL')
        or 'deepseek-chat'
    )
    
    # ---------------------------------------------------------
    # C: DeepSeek 专用变量（向后兼容，指向 LLM_* 同名值）
    #    已废弃：新代码请使用 Config.LLM_API_KEY 等
    #    保留原因：agent.py / test_api.py 仍在使用
    # E: DeepSeek-specific vars (backward compatible, alias to LLM_*)
    #    Deprecated: new code should use Config.LLM_API_KEY etc.
    #    Kept for: agent.py / test_api.py compatibility
    # ---------------------------------------------------------
    DEEPSEEK_API_KEY = LLM_API_KEY
    DEEPSEEK_BASE_URL = LLM_BASE_URL
    DEEPSEEK_MODEL = LLM_MODEL
    
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))
    
    # ---------------------------------------------------------
    # C: 润色专用轻量模型配置（混合审查模式）
    #    设置 POLISH_MODEL 可启用「小模型迭代 + 主模型终审」混合润色。
    #    未配置时自动回退为 LLM_MODEL 直接润色（零额外开销）。
    #    推荐轻量模型: deepseek-lite（云端）, llama3.2 / qwen2.5:0.5b（本地 Ollama）
    # E: Polish-specific lightweight model config (hybrid review mode)
    #    Set POLISH_MODEL to enable "lightweight iteration + main model review".
    #    Falls back to LLM_MODEL direct polish when not configured (zero overhead).
    #    Recommended: deepseek-lite (cloud), llama3.2 / qwen2.5:0.5b (local Ollama)
    # ---------------------------------------------------------
    POLISH_MODEL = (
        os.getenv('POLISH_MODEL')
        or None  # None = 未配置，使用主力模型直润
    )
    POLISH_BASE_URL = (
        os.getenv('POLISH_BASE_URL')
        or LLM_BASE_URL  # 默认与主力模型共用端点
    )
    POLISH_API_KEY = (
        os.getenv('POLISH_API_KEY')
        or LLM_API_KEY  # 默认与主力模型共用 Key
    )
    # C: 轻量模型自迭代最大次数（1~5，默认3）
    # E: Max lightweight self-iteration count (1~5, default 3)
    POLISH_ITERATIONS = int(os.getenv('POLISH_ITERATIONS', '3'))
    
    # C: MCP Server 脚本绝对路径（供 Client spawn 子进程使用）
    # E: MCP Server script absolute path (for Client to spawn subprocess)
    MCP_SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

# C: 为了兼容 agent.py，我们在类外部定义这个变量
# E: For compatibility with agent.py, we define this variable outside the class
DEEPSEEK_CONFIG = {
    "api_key": Config.LLM_API_KEY,
    "base_url": Config.LLM_BASE_URL,
    "model": Config.LLM_MODEL
}

if __name__ == "__main__":
    if Config.LLM_API_KEY:
        print(f"C: LLM_CONFIG:")
        print(f"E: LLM_CONFIG:")
        print(f"  Model:     {Config.LLM_MODEL}")
        print(f"  Base URL:  {Config.LLM_BASE_URL}")
        print(f"  API Key:   {'***' + Config.LLM_API_KEY[-4:]}")
        print("C: 配置加载成功！")
        print("E: Configuration loaded successfully!")
    else:
        print("C: 警告: 未设置 LLM_API_KEY 或 DEEPSEEK_API_KEY")
        print("E: Warning: LLM_API_KEY or DEEPSEEK_API_KEY not set")