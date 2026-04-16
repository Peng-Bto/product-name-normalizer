# 品名自动分类工具 (Product Name Normalizer)

基于科大讯飞星火大模型（OpenAI 兼容接口）实现的自动化海关品名分类工具。支持高并发处理、自动去重、断点续传及完善的日志记录。

## 🚀 功能特性

- **高并发处理**：默认开启 7 路异步并发，显著提升大批量品名的解析效率。
- **断点续传**：解析失败的品名会自动保存到 `failed_products.txt`，重启程序将优先处理上次未成功的任务。
- **自动重试机制**：程序会自动循环重试失败品名，并在轮次间加入 1 秒延迟，直至所有品名解析成功。
- **数据预处理**：自动读取 Excel 第一列品名，剔除重复项及首尾空格，节省 Token。
- **智能解析**：强制启用 `json_object` 模式，确保模型返回稳定的 JSON 结构。
- **全流程日志**：集成 `loguru`，实时记录处理进度、错误详情及 API 交互。
- **环境管理**：使用 `uv` 进行现代化的 Python 依赖和环境管理。

## 🛠️ 环境准备

1. **安装 uv** (如果尚未安装):
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **获取 API 凭证**:
   前往 [讯飞开放平台-星火大模型](https://console.xfyun.cn/services/bm2) 获取您的 `APIKey` 和 `APISecret`。

## 📦 安装与配置

1. **克隆项目**:
   ```bash
   git clone https://github.com/Peng-Bto/product-name-normalizer.git
   cd product-name-normalizer
   ```

2. **配置环境变量**:
   将 `.env.example` 重命名为 `.env`，并填入您的配置：
   ```bash
   # 注意：API_KEY 格式为 APIKey:APISecret
   SPARK_API_KEY=您的APIKey:您的APISecret
   SPARK_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
   SPARK_MODEL_DOMAIN=generalv3.5
   ```

3. **准备数据**:
   在项目根目录下放置 `product.xlsx`，确保第一列为您需要分类的原始品名。

## 💻 运行使用

使用 `uv` 一键安装依赖并启动程序：

```powershell
uv run main.py
```

### ☁️ 云服务器后台运行

如果你在云服务器上运行，建议使用 `nohup` 后台执行：

```bash
nohup python main.py > output.log 2>&1 &
```

实时查看日志：

```bash
tail -f output.log
```

项目还会生成以下日志文件：

- `process.log`
- `model_request.log`

可以同时查看：

```bash
tail -f process.log model_request.log
```

> 退出实时查看：按 `Ctrl+C`。

## 📂 项目结构

- `main.py`: 核心异步并发处理逻辑。
- `prompt.txt`: 包含海关品名分类标准的系统提示词。
- `failed_products.txt`: 自动生成的失败/待处理品名清单（支持断点续传）。
- `product.xlsx`: 输入数据文件（需自备）。
- `result.xlsx`: 自动生成的分类结果文件。
- `process.log`: 运行过程中的详细日志。
- `test_connection.py`: 简易连通性与兼容性测试工具。

## 📝 注意事项

- **分类标准**：如需调整分类类别，请直接修改 `prompt.txt`。
- **并发限制**：如需调整并发数，请修改 `main.py` 中的 `CONCURRENCY_LIMIT` 常量。
- **安全提醒**：请勿将包含真实 API Key 的 `.env` 文件提交到代码仓库（已默认配置 `.gitignore`）。
