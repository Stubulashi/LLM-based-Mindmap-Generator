import os  
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """配置管理类"""
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))

# --- 为了兼容 agent.py，我们在类外部定义这个变量 ---
DEEPSEEK_CONFIG = {
    "api_key": Config.DEEPSEEK_API_KEY,
    "base_url": Config.DEEPSEEK_BASE_URL,
    "model": Config.DEEPSEEK_MODEL
}

if __name__ == "__main__":
    if Config.DEEPSEEK_API_KEY:
        print(f"Base URL: {Config.DEEPSEEK_BASE_URL}")
        print("配置加载成功！")
