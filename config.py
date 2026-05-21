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
    E: Configuration management class
    """
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))

# C: 为了兼容 agent.py，我们在类外部定义这个变量
# E: For compatibility with agent.py, we define this variable outside the class
DEEPSEEK_CONFIG = {
    "api_key": Config.DEEPSEEK_API_KEY,
    "base_url": Config.DEEPSEEK_BASE_URL,
    "model": Config.DEEPSEEK_MODEL
}

if __name__ == "__main__":
    if Config.DEEPSEEK_API_KEY:
        print(f"C: Base URL: {Config.DEEPSEEK_BASE_URL}")
        print(f"E: Base URL: {Config.DEEPSEEK_BASE_URL}")
        print("C: 配置加载成功！")
        print("E: Configuration loaded successfully!")