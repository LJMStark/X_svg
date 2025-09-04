# 推文数据集批量处理工具

这个工具用于批量处理已排序的推文数据集，为每条记录生成SVG图像和小红书文案。

## 功能特性

- 🎨 **SVG图像生成**: 使用DeepSeek模型根据推文内容生成高级杂志风格SVG图像
- 📝 **小红书文案生成**: 使用DeepSeek模型生成小红书风格的标题和正文
- 📁 **自动文件组织**: 为每条记录创建独立文件夹，包含所有生成的内容
- 🔄 **断点续传**: 支持跳过已处理的记录，可随时中断和恢复
- 🛡️ **错误处理**: 完善的重试机制和错误日志
- 📊 **进度显示**: 实时显示处理进度和统计信息
- ⚡ **智能速度限制**: 自动处理OpenRouter API的速度限制，避免429错误

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

### 1. 获取OpenRouter API密钥

1. 访问 [OpenRouter.ai](https://openrouter.ai/keys) 注册账号
2. 获取API密钥
3. 设置环境变量（推荐）：

```bash
export OPENROUTER_API_KEY="your_api_key_here"
```

或者使用配置文件：

1. 复制 `config.example.json` 为 `config.json`
2. 在 `config.json` 中填入您的API密钥

### 2. 环境变量配置（可选）

```bash
# 复制环境变量示例文件
cp .env.example .env
# 编辑 .env 文件，填入您的API密钥
```

## 文件准备

确保以下文件存在于工作目录中：

1. `twillot-public-post-sorted.json` - 已排序的推文数据集
2. `svg提示词.txt` - SVG生成的系统提示词
3. `小红书文案提示词.txt` - 小红书文案生成的系统提示词

## 使用方法

### 方法1: 命令行使用

```bash
# 基本使用（处理前5条记录）
python batch_process_tweets.py --api-key "your_openrouter_api_key_here" --count 5

# 处理所有记录
python batch_process_tweets.py --api-key "your_openrouter_api_key_here"

# 从第10条开始处理20条记录
python batch_process_tweets.py --api-key "your_openrouter_api_key_here" --start 10 --count 20

# 指定自定义文件路径
python batch_process_tweets.py \
    --api-key "your_openrouter_api_key_here" \
    --input "custom_data.json" \
    --svg-prompt "custom_svg_prompt.txt" \
    --xiaohongshu-prompt "custom_xhs_prompt.txt"
```

### 方法2: 使用环境变量

```bash
# 设置环境变量
export OPENROUTER_API_KEY="your_api_key_here"

# 运行程序（会自动读取环境变量）
python batch_process_tweets.py --count 5
```

### 方法3: 使用示例脚本

1. 设置环境变量：

```bash
export OPENROUTER_API_KEY="your_api_key_here"
```

2. 运行脚本：

```bash
python run_example.py
```

### 命令行参数说明

- `--api-key`: OpenRouter API密钥（必需，或者设置环境变量）
- `--input`: 输入JSON文件路径（默认: twillot-public-post-sorted.json）
- `--svg-prompt`: SVG提示词文件路径（默认: svg提示词.txt）
- `--xiaohongshu-prompt`: 小红书提示词文件路径（默认: 小红书文案提示词.txt）
- `--start`: 开始处理的索引（默认: 0）
- `--count`: 处理数量限制（默认: 处理所有）

## 输出结构

处理完成后，会在 `output/` 目录下生成以下结构：

```
output/
├── 标题1/
│   ├── generated.svg    # 生成的SVG图像
│   ├── title.txt       # 标题内容
│   └── body.txt        # 正文和标签内容
├── 标题2/
│   ├── generated.svg
│   ├── title.txt
│   └── body.txt
└── ...
```

## API配置

脚本使用OpenRouter API，配置如下：

```python
client = openai.OpenAI(
    api_key="your_api_key_here",  # 从 https://openrouter.ai/keys 获取
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://github.com",
        "X-Title": "TweetProcessor"
    }
)
```

### 使用的模型

- **SVG生成**: deepseek/deepseek-chat-v3-1:free
- **小红书文案生成**: deepseek/deepseek-chat-v3-1:free

### API限制

- **免费模型限制**: 每分钟16次请求
- **自动处理**: 程序会自动处理速度限制，避免429错误
- **建议间隔**: 4秒每次请求（程序自动控制）

## 性能优化

- **智能速度限制**: 默认4秒间隔，自动处理OpenRouter API限制
- **重试机制**: 失败时自动重试3次，429错误会延长等待时间
- **断点续传**: 自动跳过已处理的记录
- **内存优化**: 逐条处理，不会占用大量内存
- **错误恢复**: 网络错误自动重试，保证处理稳定性

## 错误处理

- 所有操作都有完善的异常处理
- 详细的日志记录（同时输出到控制台和 `batch_process.log` 文件）
- API调用失败时自动重试
- 文件名冲突自动处理（添加数字后缀）

## 注意事项

1. **API费用**: DeepSeek模型目前免费，但请注意OpenRouter的价格政策变化
2. **处理时间**: 大量数据处理需要较长时间（每条约4秒），建议分批处理
3. **网络稳定**: 确保网络连接稳定，避免API调用中断
4. **磁盘空间**: 确保有足够磁盘空间存储生成的文件
5. **速度限制**: 程序会自动处理API速度限制，请耐心等待

## 故障排除

### 常见问题

1. **API密钥错误**: 检查OpenRouter密钥是否正确
2. **文件不存在**: 确保所有必需文件都在正确位置
3. **速度限制429错误**: 程序会自动处理，如果频繁出现请检查网络连接
4. **网络超时**: 检查网络连接，可能需要重试
5. **磁盘空间不足**: 清理磁盘空间或更改输出目录

### 日志查看

查看 `batch_process.log` 文件获取详细的错误信息和处理日志。

## 示例输出

处理成功后，您会看到类似以下的输出：

```
2024-01-01 12:00:00 - INFO - 读取数据文件: twillot-public-post-sorted.json
2024-01-01 12:00:01 - INFO - 数据集包含 1667 条记录
2024-01-01 12:00:01 - INFO - 开始处理记录 0 到 4 (共 5 条)
处理推文: 100%|██████████| 5/5 [00:20<00:00,  4.12s/it]
2024-01-01 12:00:21 - INFO - 处理完成 - 成功: 5, 失败: 0
```
