import os
import asyncio
import json
import re
import pandas as pd
from datetime import datetime
from loguru import logger
from openai import AsyncOpenAI
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

# 加载环境变量
load_dotenv()


# 日志分流逻辑
def filter_process(record):
    """常规日志不记录带有 request 标记的内容"""
    return "request" not in record["extra"]


def filter_request(record):
    """请求日志仅记录带有 request 标记的内容"""
    return "request" in record["extra"]


logger.remove()
logger.add(
    "process.log",
    rotation="10 MB",
    level="INFO",
    encoding="utf-8",
    filter=filter_process,
)
logger.add(
    "model_request.log",
    rotation="10 MB",
    level="INFO",
    encoding="utf-8",
    filter=filter_request,
    format="{message}",
)

# 配置
SPARK_API_KEY = os.getenv("SPARK_API_KEY")
SPARK_BASE_URL = os.getenv("SPARK_BASE_URL")
SPARK_MODEL_DOMAIN = os.getenv("SPARK_MODEL_DOMAIN")

CONCURRENCY_LIMIT = 10
RETRY_COUNT = 3

# 初始化客户端
client = AsyncOpenAI(api_key=SPARK_API_KEY, base_url=SPARK_BASE_URL)


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
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                        + "\n请务必只以纯 JSON 格式回复，不要包含任何 markdown 块标记或解释文字。",
                    },
                    {"role": "user", "content": f'输入品名 = "{product_name}"'},
                ]

                # 记录请求内容到独立日志
                logger.bind(request=True).info(json.dumps(messages, ensure_ascii=False))

                response = await client.chat.completions.create(
                    model=SPARK_MODEL_DOMAIN,
                    messages=messages,
                    temperature=0.7,
                    # 推理模型使用此参数将导致推理失效
                    # response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content.strip()
                full_content = response  # 用于日志记录完整响应内容
                logger.bind(request=True).info(json.dumps(content, ensure_ascii=False))
                logger.bind(request=True).info(full_content)

                # 智能提取 JSON
                json_text = ""
                code_block_match = re.search(
                    r"```json\s*(\{.*?\})\s*```", content, re.DOTALL
                )
                if code_block_match:
                    json_text = code_block_match.group(1)
                else:
                    json_match = re.search(r"(\{.*\})", content, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(1)

                if json_text:
                    data = json.loads(json_text)
                    return {
                        "被解析品名": product_name,
                        "品类": data.get("品类", "未知"),
                        "功能类别": data.get("功能类别", "未知"),
                        "置信度": data.get("置信度", "0%"),
                    }
                else:
                    logger.warning(
                        f"品名 '{product_name}' 返回内容未发现 JSON 结构: {content}"
                    )
                    raise ValueError("No JSON found in response")

            except Exception as e:
                logger.error(
                    f"处理品名 '{product_name}' 失败 (尝试 {attempt+1}/{RETRY_COUNT}): {e}"
                )
                if attempt == RETRY_COUNT - 1:
                    return {
                        "被解析品名": product_name,
                        "品类": "处理失败",
                        "功能类别": "处理失败",
                        "置信度": "N/A",
                        "error": str(e),
                    }
                await asyncio.sleep(1)


async def main():
    if not SPARK_API_KEY:
        logger.error("请在 .env 文件中配置 SPARK_API_KEY (格式为 APIKey:APISecret)")
        return

    input_file = "product.xlsx"
    output_file = "result.xlsx"
    failed_file = "failed_products.txt"
    checkpoint_file = "result_checkpoint.jsonl"

    # 1. 初始读取数据
    if not os.path.exists(input_file):
        logger.error(f"找不到输入文件 {input_file}")
        return
    try:
        df = pd.read_excel(input_file)
        original_col_name = df.columns[0]
        all_products = (
            df[original_col_name].dropna().astype(str).str.strip().unique().tolist()
        )
        logger.info(f"从 {input_file} 原始读取到 {len(all_products)} 个唯一品名。")
    except Exception as e:
        logger.error(f"读取 Excel 失败: {e}")
        return

    # 2. 读取断点续传记录（已经成功的品名）
    processed_products = set()
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        processed_products.add(data.get("被解析品名"))
            logger.info(f"检测到断点记录，已成功处理过 {len(processed_products)} 个品名。")
        except Exception as e:
            logger.error(f"读取断点记录失败: {e}")

    # 3. 筛选出还未处理的品名
    if os.path.exists(failed_file):
        try:
            with open(failed_file, "r", encoding="utf-8") as f:
                failed_products = [line.strip() for line in f if line.strip()]
            products_to_process = [
                p for p in failed_products if p not in processed_products
            ]
            logger.info(
                f"从 {failed_file} 恢复，剔除已成功项后，剩余 {len(products_to_process)} 个待处理品名。"
            )
        except Exception as e:
            logger.error(f"读取 {failed_file} 失败: {e}")
            return
    else:
        products_to_process = [p for p in all_products if p not in processed_products]
        logger.info(f"去重后，本次实际待处理品名数量: {len(products_to_process)}")

    iteration = 1
    while products_to_process:
        logger.info(f"第 {iteration} 轮处理，待处理品名数量: {len(products_to_process)}")

        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        tasks = [get_classification(name, semaphore) for name in products_to_process]

        failed_results = []
        # ★★★ 关键修改：在循环内部即时保存 ★★★
        for coro in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc=f"第 {iteration} 轮分类进度",
        ):
            result = await coro
            
            if result.get("品类") != "处理失败":
                # 添加保存时间
                result["保存时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # 只要成功一个，立刻追加保存一行
                try:
                    with open(checkpoint_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(result, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.error(f"即时保存结果失败: {e}")
            else:
                # 失败的存入临时列表用于下一轮重试
                failed_results.append(result)

        if failed_results:
            products_to_process = [r["被解析品名"] for r in failed_results]
            # 记录失败品名到文件
            try:
                with open(failed_file, "w", encoding="utf-8") as f:
                    for name in products_to_process:
                        f.write(f"{name}\n")
                logger.warning(
                    f"第 {iteration} 轮有 {len(failed_results)} 个品名解析失败，已保存至 {failed_file}。"
                )
            except Exception as e:
                logger.error(f"保存失败品名到文件失败: {e}")

            # 轮次间稍微等待，避免立即触发限速
            await asyncio.sleep(1)
        else:
            products_to_process = []
            if os.path.exists(failed_file):
                os.remove(failed_file)
            logger.info("本轮所有品名均已成功解析。")

        iteration += 1

    # 4. 保存结果 (从 checkpoint 文件读取全部结果)
    final_results = []
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        final_results.append(json.loads(line))
        except Exception as e:
            logger.error(f"读取最终断点文件失败: {e}")

    if final_results:
        try:
            res_df = pd.DataFrame(final_results)
            # 即使有重复写入也进行去重
            res_df = res_df.drop_duplicates(subset=["被解析品名"], keep="last")
            cols = ["被解析品名", "品类", "功能类别", "置信度"]
            res_df[cols].to_excel(output_file, index=False)
            logger.info(
                f"全部处理完成，共 {len(res_df)} 条结果，已保存至 {output_file}"
            )
        except Exception as e:
            logger.error(f"保存最终结果失败: {e}")
    else:
        logger.warning("没有成功的结果可以保存。")


if __name__ == "__main__":
    asyncio.run(main())
