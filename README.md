# Product Name Normalizer (大批量品名标准化工具)

本项目是一个基于大语言模型（LLM）的自动化品名解析与分类工具，专门针对数万级规模的商品品名进行标准化处理。它能够自动识别品名中的关键信息，并将其归类到指定的品类和功能类别中。

## 核心功能

- **🚀 工业级异步并发**：采用 `asyncio` 异步框架与信号量（Semaphore）控制，支持高并发调用 LLM API，极速处理 5 万+ 规模的品名。
- **💾 断点续传 (Checkpointing)**：自动记录处理进度。若任务中途因网络、服务器等原因中断，重启后会自动跳过已处理的品名，从断点处继续执行，节省 API 消耗。
- **🔒 即时存盘 (Real-time Saving)**：**最高安全等级**。每成功解析一个品名，结果会立即以增量方式（JSON Lines）写入磁盘，并自动附带 `保存时间` 戳，确保即使程序意外崩溃，已调用的结果也绝不丢失，且方便进度追踪。
- **🧠 智能 JSON 提取**：内置鲁棒的正则提取逻辑，能够从模型回复中精准剥离出 JSON 结构，有效应对模型输出中夹杂的 Markdown 标签或解释性文字。
- **🔄 自动轮询重试**：针对处理失败（网络超时或逻辑错误）的品名，会自动进入下一轮重试队列，直至所有品名全部成功解析。
- **📊 结果自动导出**：任务完成后，自动去重并汇总所有中间进度，一键生成标准化的 Excel 结果报表。
- **📝 双重日志分流**：
  - `process.log`: 记录程序运行状态、进度及错误信息。
  - `model_request.log`: 完整记录每一次 API 的请求报文与原始响应，方便后期审计与质量分析。

## 环境配置

1.  **安装依赖**：
    ```bash
    pip install pandas loguru openai python-dotenv tqdm openpyxl
    ```
2.  **配置环境变量**：
    在根目录下创建 `.env` 文件，并填写您的 API 配置：
    ```env
    SPARK_API_KEY=您的APIKey:您的APISecret
    SPARK_BASE_URL=https://spark-api-open.xf-yun.com/v1
    SPARK_MODEL_DOMAIN=4.0Ultra
    ```

## 使用说明

1.  **准备输入文件**：
    将待处理的 Excel 文件命名为 `product.xlsx` 放置在根目录下，程序默认读取**第一列**作为品名。
2.  **配置 Prompt**：
    在 `prompt.txt` 中编写您的分类逻辑与规则。
3.  **运行任务**：
    ```bash
    # 直接运行
    python main.py
    
    # 云服务器后台运行（推荐）
    nohup python main.py > nohup.out 2>&1 &
    ```
4.  **查看进度**：
    ```bash
    # 查看进度条
    tail -f nohup.out
    
    # 查看运行日志
    tail -f process.log
    ```

## 产出文件

- `result_checkpoint.jsonl`: 运行过程中的即时增量备份文件（最重要）。
- `result.xlsx`: 最终生成的完整分类结果。
- `failed_products.txt`: 记录当前仍处于失败状态、待重试的品名。

## 注意事项

- **并发控制**：默认 `CONCURRENCY_LIMIT = 10`。如需提速且 API 余额充足，可调大此参数。
- **安全保障**：由于具备即时存盘功能，您可以随时通过杀掉进程的方式暂停任务，下次运行 `python main.py` 即可无缝接续。
