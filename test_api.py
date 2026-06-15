from openai import OpenAI
from config import Config

# C: 初始化 LLM 客户端（兼容任意 OpenAI API 提供商）
# E: Initialize LLM client (compatible with any OpenAI API provider)
client = OpenAI(
    api_key=Config.LLM_API_KEY,
    base_url=Config.LLM_BASE_URL
)

def test_connection():
    """
    C: 测试 API 连接（使用 Config.LLM_* 配置的模型）
    E: Test API connection (using model configured via Config.LLM_*)
    """
    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {"role": "system", "content": "C: 你是一个助手 / E: You are an assistant"},
                {"role": "user", "content": "C: 请用一句话介绍自己 / E: Please introduce yourself in one sentence"}
            ],
            max_tokens=50,
        )
        
        print("C: ✅ API 连接成功！")
        print("E: ✅ API connection successful!")
        print(f"  Model:  {Config.LLM_MODEL}")
        print(f"  URL:    {Config.LLM_BASE_URL}")
        print(f"C: 回复: {response.choices[0].message.content}")
        print(f"E: Reply: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"C: ❌ API 连接失败: {e}")
        print(f"E: ❌ API connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()