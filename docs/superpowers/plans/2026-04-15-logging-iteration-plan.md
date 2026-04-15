# 日志记录逻辑迭代实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将发送给模型的内容单独记录在 `model_request.log` 中，并与 `process.log` 分离。

**Architecture:** 利用 `loguru` 的 `filter` 和 `bind` 机制。通过 `logger.bind(request=True)` 标记请求日志，并在配置中使用自定义 filter 函数进行分流。

**Tech Stack:** Python, loguru

---

### Task 1: 配置 Loguru 分流逻辑

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 修改 `main.py` 中的日志配置部分**

```python
# 替换原有的 logger.add("process.log", ...)

def filter_process(record):
    """常规日志不记录带有 request 标记的内容"""
    return "request" not in record["extra"]

def filter_request(record):
    """请求日志仅记录带有 request 标记的内容"""
    return record["extra"].get("request") is True

logger.remove()  # 移除默认配置
# 配置常规流程日志
logger.add("process.log", rotation="10 MB", level="INFO", encoding="utf-8", filter=filter_process)
# 配置模型请求日志，仅记录消息内容本身
logger.add("model_request.log", rotation="10 MB", level="INFO", encoding="utf-8", filter=filter_request, format="{message}")
```

- [ ] **Step 2: 提交代码**

```bash
git add main.py
git commit -m "chore: configure loguru filters for log separation"
```

---

### Task 2: 在业务代码中记录模型请求

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 在 `get_classification` 函数中添加记录逻辑**

找到构造 `messages` 的位置，在调用 API 之前记录。

```python
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
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
```

- [ ] **Step 2: 提交代码**

```bash
git add main.py
git commit -m "feat: log model requests to dedicated log file"
```

---

### Task 3: 验证日志分离效果

**Files:**
- Create: `test_logging_logic.py`

- [ ] **Step 1: 编写验证脚本**

```python
import os
import json
from loguru import logger

# 复制 main.py 中的配置逻辑进行测试
def filter_process(record):
    return "request" not in record["extra"]

def filter_request(record):
    return record["extra"].get("request") is True

def setup_test_logging():
    logger.remove()
    if os.path.exists("test_process.log"): os.remove("test_process.log")
    if os.path.exists("test_model_request.log"): os.remove("test_model_request.log")
    
    logger.add("test_process.log", filter=filter_process)
    logger.add("test_model_request.log", filter=filter_request, format="{message}")

def test_logging():
    setup_test_logging()
    
    # 记录普通日志
    logger.info("This is a process log")
    
    # 记录请求日志
    messages = [{"role": "user", "content": "hello"}]
    logger.bind(request=True).info(json.dumps(messages))
    
    # 验证文件内容
    with open("test_process.log", "r") as f:
        process_content = f.read()
        assert "This is a process log" in process_content
        assert "hello" not in process_content
        
    with open("test_model_request.log", "r") as f:
        request_content = f.read()
        assert "This is a process log" not in request_content
        assert "hello" in request_content

    print("Logging separation test passed!")

if __name__ == "__main__":
    test_logging()
```

- [ ] **Step 2: 运行验证脚本**

Run: `python test_logging_logic.py`
Expected: 打印 "Logging separation test passed!"，且生成的两个测试日志文件内容符合预期。

- [ ] **Step 3: 清理并提交**

删除测试脚本和生成的测试日志文件。

```bash
rm test_logging_logic.py test_process.log test_model_request.log
```
