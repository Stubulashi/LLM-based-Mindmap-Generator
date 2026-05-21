from openai import OpenAI
from config import Config

# C: 验证配置
# E: Validate configuration
Config.validate()

# C: 初始化 DeepSeek 客户端
# E: Initialize DeepSeek client
client = OpenAI(
    api_key=Config.DEEPSEEK_API_KEY,
    base_url=Config.DEEPSEEK_BASE_URL
)

def test_connection():
    """
    C: 测试 API 连接
    E: Test API connection
    """
    try:
        response = client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "C: 你是一个助手 / E: You are an assistant"},
                {"role": "user", "content": "C: 请用一句话介绍自己 / E: Please introduce yourself in one sentence"}
            ],
            max_tokens=50,
            temperature=Config.TEMPERATURE
        )
        
        print("C: ✅ API 连接成功！")
        print("E: ✅ API connection successful!")
        print(f"C: 回复: {response.choices[0].message.content}")
        print(f"E: Reply: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"C: ❌ API 连接失败: {e}")
        print(f"E: ❌ API connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()