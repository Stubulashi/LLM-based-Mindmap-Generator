from openai import OpenAI
from config import Config

# 验证配置
Config.validate()

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=Config.DEEPSEEK_API_KEY,
    base_url=Config.DEEPSEEK_BASE_URL
)

def test_connection():
    """测试 API 连接"""
    try:
        response = client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是一个助手"},
                {"role": "user", "content": "请用一句话介绍自己"}
            ],
            max_tokens=50,
            temperature=Config.TEMPERATURE
        )
        
        print("✅ API 连接成功！")
        print(f"回复: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ API 连接失败: {e}")
        return False

if __name__ == "__main__":
    test_connection()
