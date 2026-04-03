import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取配置
api_key = os.getenv("SPARK_API_KEY")
base_url = os.getenv("SPARK_BASE_URL")
model = os.getenv("SPARK_MODEL_DOMAIN")

print(f"正在测试 response_format 兼容性...")
print(f"Model: {model}")

# 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

try:
    # 测试 JSON Mode
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "请以 JSON 格式回复一个包含 'status' 字段的对象，值为 'ok'"}
        ],
        response_format={"type": "json_object"}
    )

    # 打印结果
    print("-" * 20)
    print("模型回复内容：")
    print(response.choices[0].message.content)
    print("-" * 20)
    print("测试结论：该模型支持 response_format='json_object'")

except Exception as e:
    print("-" * 20)
    print(f"测试失败！错误信息：\n{e}")
    print("-" * 20)
    if "400" in str(e):
        print("测试结论：该模型可能不支持 response_format 参数。")
    elif "401" in str(e):
        print("测试结论：鉴权依然失败，请检查 API Key 格式是否为 'APIKey:APISecret'。")
