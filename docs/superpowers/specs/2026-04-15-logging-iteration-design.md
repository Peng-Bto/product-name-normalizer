# 设计文档：日志记录逻辑迭代 - 发送内容专项记录

## 1. 目标
在现有的 `product-name-normalizer` 项目中，迭代日志记录逻辑。将发送给模型（Model）的完整 Prompt 内容（包括 System Prompt 和 User Input）记录到独立的日志文件中，以便与程序的流程日志和错误日志区分开。

## 2. 背景
目前项目使用 `loguru` 进行日志记录，所有日志均记录在 `process.log` 中。为了方便后续分析 Prompt 效果和调试模型响应，需要将“请求报文”提取到单独的文件中。

## 3. 技术方案：Loguru Filter 机制
我们将利用 `loguru` 的 `filter` 和 `bind` 功能实现日志流的分离。

### 3.1 日志配置更新
- **现有日志 (`process.log`)**: 修改配置，增加 `filter`。如果日志记录中包含 `request` 标识，则不记录到此文件。
- **新增日志 (`model_request.log`)**: 增加配置，通过 `filter` 只记录包含 `request` 标识的日志。

### 3.2 记录位置
在 `main.py` 的 `get_classification` 函数中，在调用 `client.chat.completions.create` 之前，构造好 `messages` 列表后，立即进行记录。

### 3.3 记录格式
建议将 `messages` 数组转为 JSON 字符串记录，每行一条记录（类似 JSONL 风格，但在 loguru 的日志行内），方便解析。

## 4. 详细设计

### 4.1 Loguru 配置修改建议
```python
# 过滤函数：常规日志不记录 request=True 的内容
def filter_process(record):
    return "request" not in record["extra"]

# 过滤函数：请求日志只记录 request=True 的内容
def filter_request(record):
    return record["extra"].get("request") is True

logger.remove() # 移除默认控制台输出（如果需要重新配置）
# 配置常规日志
logger.add("process.log", rotation="10 MB", level="INFO", encoding="utf-8", filter=filter_process)
# 配置请求日志
logger.add("model_request.log", rotation="10 MB", level="INFO", encoding="utf-8", filter=filter_request, format="{message}")
```

### 4.2 业务逻辑修改建议
在 `get_classification` 中：
```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT + "..."},
    {"role": "user", "content": f'输入品名 = "{product_name}"'},
]
# 关键记录步骤
logger.bind(request=True).info(json.dumps(messages, ensure_ascii=False))

response = await client.chat.completions.create(...)
```

## 5. 验收标准
1. 运行程序后，生成 `process.log` 和 `model_request.log` 两个文件。
2. `process.log` 中不应包含发送给模型的完整 `messages` 内容。
3. `model_request.log` 中应且仅包含发送给模型的 `messages` 内容。
4. 程序的并发处理和限速逻辑不受日志记录影响。
