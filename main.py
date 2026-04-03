import os
import asyncio
import json
import re
import pandas as pd
from loguru import logger
from openai import AsyncOpenAI
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

# 加载环境变量
load_dotenv()

# 日志配置
logger.add("process.log", rotation="10 MB", level="INFO", encoding="utf-8")

# 配置
SPARK_API_KEY = os.getenv("SPARK_API_KEY")
SPARK_BASE_URL = os.getenv("SPARK_BASE_URL", "https://maas-api.cn-huabei-1.xf-yun.com/v2")
SPARK_MODEL_DOMAIN = os.getenv("SPARK_MODEL_DOMAIN", "generalv3.5") 

CONCURRENCY_LIMIT = 10
RETRY_COUNT = 3

# 初始化客户端
client = AsyncOpenAI(
    api_key=SPARK_API_KEY,
    base_url=SPARK_BASE_URL
)

# 读取 Prompt
def load_prompt():
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"无法读取 prompt.txt: {e}")
        return ""

SYSTEM_PROMPT = load_prompt()

async def get_classification(product_name, semaphore):
    async with semaphore:
        for attempt in range(RETRY_COUNT):
            try:
                # 构造对话
                response = await client.chat.completions.create(
                    model=SPARK_MODEL_DOMAIN,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT + "\n请务必只以纯 JSON 格式回复，不要包含任何 markdown 块标记或解释文字。"},
                        {"role": "user", "content": f"输入品名 = \"{product_name}\""}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content.strip()
                
                # 智能提取 JSON
                json_text = ""
                code_block_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                if code_block_match:
                    json_text = code_block_match.group(1)
                else:
                    json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(1)
                
                if json_text:
                    data = json.loads(json_text)
                    return {
                        "被解析品名": product_name,
                        "品类": data.get("品类", "未知"),
                        "功能类别": data.get("功能类别", "未知"),
                        "置信度": data.get("置信度", "0%")
                    }
                else:
                    logger.warning(f"品名 '{product_name}' 返回内容未发现 JSON 结构: {content}")
                    raise ValueError("No JSON found in response")
                
            except Exception as e:
                logger.error(f"处理品名 '{product_name}' 失败 (尝试 {attempt+1}/{RETRY_COUNT}): {e}")
                if attempt == RETRY_COUNT - 1:
                    return {
                        "被解析品名": product_name,
                        "品类": "处理失败",
                        "功能类别": "处理失败",
                        "置信度": "N/A",
                        "error": str(e)
                    }
                await asyncio.sleep(1)

async def main():
    if not SPARK_API_KEY:
        logger.error("请在 .env 文件中配置 SPARK_API_KEY (格式为 APIKey:APISecret)")
        return

    # 1. 读取数据
    input_file = "product.xlsx"
    output_file = "result.xlsx"
    
    if not os.path.exists(input_file):
        logger.error(f"找不到输入文件 {input_file}")
        return

    try:
        df = pd.read_excel(input_file)
        # 假设第一列是品名
        original_col_name = df.columns[0]
        # 去重、去空格
        products = df[original_col_name].dropna().astype(str).str.strip().unique().tolist()
        logger.info(f"读取到 {len(products)} 个唯一品名。")
    except Exception as e:
        logger.error(f"读取 Excel 失败: {e}")
        return

    # 2. 并发处理
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [get_classification(name, semaphore) for name in products]
    
    results = []
    # 使用 tqdm 显示进度
    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="正在分类品名"):
        result = await coro
        results.append(result)

    # 3. 保存结果
    try:
        res_df = pd.DataFrame(results)
        cols = ["被解析品名", "品类", "功能类别", "置信度"]
        if "error" in res_df.columns:
            cols.append("error")
            
        res_df[cols].to_excel(output_file, index=False)
        logger.info(f"处理完成，结果已保存至 {output_file}")
    except Exception as e:
        logger.error(f"保存结果失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
