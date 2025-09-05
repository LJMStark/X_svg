# 推文数据集批量处理工具

这个工具用于批量处理已排序的推文数据集，为每条记录生成SVG图像和小红书文案。

## 功能特性

- 🎨 **SVG图像生成**: 使用多AI模型根据推文内容生成高级杂志风格SVG图像
- 📝 **小红书文案生成**: 分离式标题和正文生成，使用专门的小红书风格提示词
- 📁 **自动文件组织**: 为每条记录创建独立文件夹，包含所有生成的内容
- 🔄 **断点续传**: 支持跳过已处理的记录，可随时中断和恢复
- 🛡️ **多API故障转移**: 支持5个API提供商，4级故障转移机制
- 📊 **进度显示**: 实时显示处理进度和统计信息
- ⚡ **智能速度限制**: 自动处理各API的速度限制，避免429错误
- 🎯 **质量控制**: SVG内容验证、XML修复、字体替换等

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

### 1. 多API提供商支持

系统支持5个API提供商，每个任务可配置独立的API调用顺序：

- **OpenRouter**: 主API，支持多种模型
- **Novita**: 备用API，DeepSeek模型
- **SiliconFlow**: 备用API，DeepSeek模型
- **Moonshot**: 备用API，Kimi模型
- **Gemini**: 备用API，通过代理服务

### 2. 环境变量配置

```bash
# 设置API密钥（推荐）
export OPENROUTER_API_KEY="your_openrouter_key"
export NOVITA_API_KEY="your_novita_key"
export SILICONFLOW_API_KEY="your_siliconflow_key"
export MOONSHOT_API_KEY="your_moonshot_key"
export GEMINI_API_KEY="your_gemini_key"
```

### 3. 配置文件

系统使用 `config.json` 进行配置管理，支持完整的配置验证和管理：

```json
{
  "api_providers": {
    "openrouter": {
      "enabled": true,
      "key": "sk-or-v1-xxxxx",
      "base_url": "https://openrouter.ai/api/v1",
      "timeout": 180
    },
    "siliconflow": {
      "enabled": true,
      "key": "sk-xxxxx",
      "base_url": "https://api.siliconflow.cn/v1",
      "timeout": 180
    }
  },
  "tasks": {
    "title": {
      "primary": {"provider": "siliconflow", "model": "deepseek-ai/DeepSeek-V3.1"},
      "fallback": {"provider": "moonshot", "model": "kimi-k2-0711-preview"}
    },
    "body": {
      "primary": {"provider": "openrouter", "model": "deepseek/deepseek-r1-0528:free"},
      "fallback": {"provider": "novita", "model": "deepseek/deepseek-v3.1"},
      "fallback2": {"provider": "moonshot", "model": "kimi-k2-0711-preview"}
    },
    "svg": {
      "primary": {"provider": "openrouter", "model": "deepseek/deepseek-r1-0528:free"},
      "fallback": {"provider": "novita", "model": "deepseek/deepseek-v3.1"},
      "fallback2": {"provider": "siliconflow", "model": "deepseek-ai/DeepSeek-V3.1"},
      "fallback3": {"provider": "moonshot", "model": "kimi-k2-0711-preview"}
    }
  },
  "batch": {
    "batch_size": 5,
    "progress_save_interval": 5,
    "api_call_buffer_time": 0.05,
    "batch_rest_time": 0.2,
    "enable_batching": true,
    "fast_mode": true
  }
}
```

### 4. 配置管理器 (新增)

系统包含完整的配置管理器 (`config_manager.py`)，提供以下功能：

- **配置验证**: JSON Schema验证配置文件格式
- **环境变量覆盖**: 支持环境变量覆盖配置文件设置
- **API密钥验证**: 验证API密钥格式和存在性
- **文件存在性检查**: 验证必需文件是否存在
- **便捷函数**: 提供各类配置的便捷获取函数

## 文件准备

确保以下文件存在于工作目录中：

1. `twillot-public-post-sorted.json` - 已排序的推文数据集
2. `svg提示词.txt` - SVG生成的系统提示词
3. `小红书标题提示词.txt` - 小红书标题生成的系统提示词
4. `小红书文案提示词.txt` - 小红书正文生成的系统提示词
5. `config.json` - 系统配置文件
6. `.env` - 环境变量文件（可选）

## 使用方法

### 方法1: 使用示例脚本（推荐）

```bash
# 设置环境变量
export OPENROUTER_API_KEY="your_api_key_here"

# 运行示例脚本（自动从上次停止处继续）
python run_example.py
```

### 方法2: 命令行使用

```bash
# 基本使用（处理前5条记录）
python batch_process_tweets.py --count 5

# 处理所有记录
python batch_process_tweets.py

# 从第10条开始处理20条记录
python batch_process_tweets.py --start 10 --count 20

# 重置进度，从头开始
python batch_process_tweets.py --reset-progress

# 显示API使用统计
python batch_process_tweets.py --stats

# 指定自定义文件路径
python batch_process_tweets.py \
    --input "custom_data.json" \
    --svg-prompt "custom_svg_prompt.txt" \
    --xiaohongshu-prompt "custom_xhs_prompt.txt"
```

### 方法3: 批量SVG生成

```bash
# 使用专门的SVG生成脚本
python batch_generate_svg.py
```

### 命令行参数说明

- `--config`: 配置文件路径（默认: config.json）
- `--input`: 输入JSON文件路径（默认: twillot-public-post-sorted.json）
- `--svg-prompt`: SVG提示词文件路径（默认: svg提示词.txt）
- `--xiaohongshu-prompt`: 小红书提示词文件路径（默认: 小红书文案提示词.txt）
- `--start`: 开始处理的索引（默认: 自动从上次停止处继续）
- `--count`: 处理数量限制（默认: 处理所有）
- `--stats`: 显示API使用统计
- `--reset-progress`: 重置进度记录，从头开始处理
- `--no-auto-continue`: 禁用自动继续功能
- `--batch-size`: 批处理大小（覆盖配置文件设置）
- `--no-batching`: 禁用批处理模式，使用逐条处理
- `--progress-interval`: 进度保存间隔（批次数）
- `--slow-mode`: 启用慢速模式，增加API调用间隔（默认为快速模式）

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

### 多API故障转移机制

系统支持5个API提供商，每个任务都有独立的故障转移配置：

#### 标题生成 (title)
1. **主API**: SiliconFlow + DeepSeek-V3.1
2. **备用API**: Moonshot + Kimi-K2

#### 正文生成 (body)
1. **主API**: OpenRouter + deepseek-r1-0528:free
2. **备用API**: Novita + DeepSeek-V3.1
3. **备用API2**: Moonshot + Kimi-K2

#### SVG生成 (svg)
1. **主API**: OpenRouter + deepseek-r1-0528:free
2. **备用API**: Novita + DeepSeek-V3.1
3. **备用API2**: SiliconFlow + DeepSeek-V3.1
4. **备用API3**: Moonshot + Kimi-K2

### API限制和速度控制

- **OpenRouter**: 4秒间隔限制
- **Gemini**: 2秒间隔限制
- **其他API**: 根据提供商限制自动调整
- **重试机制**: 最多3次重试，429错误递增延迟
- **自动处理**: 程序会自动处理速度限制，避免429错误

## 性能优化

- **多API故障转移**: 5个API提供商，4级故障转移机制
- **智能速度限制**: 根据API提供商自动调整间隔时间
- **重试机制**: 失败时自动重试3次，429错误递增延迟
- **断点续传**: 自动跳过已处理的记录，支持中断恢复
- **内存优化**: 逐条处理，不会占用大量内存
- **错误恢复**: 网络错误自动重试，保证处理稳定性
- **进度跟踪**: 实时保存处理进度，支持统计信息

### 批处理优化 (新增)

- **智能批处理**: 可配置的批处理大小（默认5条），减少I/O操作
- **快速模式默认**: 系统默认启用快速模式，优化处理速度
- **速度优化**: 批处理模式下的API调用缓冲时间（默认0.05秒）
- **进度保存优化**: 批量完成后统一保存进度，减少文件I/O
- **速率限制重置**: 批处理开始时重置所有API客户端速率限制计时器
- **慢速模式选项**: 可通过--slow-mode参数启用保守模式，增加API调用间隔
- **批次间休息**: 可配置的批次间休息时间（默认0.2秒），避免API速率限制

## 错误处理

- **多级异常处理**: 所有操作都有完善的异常处理
- **详细日志记录**: 同时输出到控制台和 `batch_process.log` 文件
- **API故障转移**: 主API失败时自动切换到备用API
- **重试机制**: API调用失败时自动重试，429错误特殊处理
- **文件冲突处理**: 文件名冲突自动处理（添加数字后缀）
- **进度保护**: 即使出现错误也会保存处理进度

## 注意事项

1. **免费模型限制**: OpenRouter API 强制使用免费模型 `deepseek/deepseek-r1-0528:free`，禁止使用付费模型
2. **处理时间**: 大量数据处理需要较长时间，建议分批处理
3. **网络稳定**: 确保网络连接稳定，避免API调用中断
4. **磁盘空间**: 确保有足够磁盘空间存储生成的文件
5. **速度限制**: 程序会自动处理API速度限制，请耐心等待
6. **多API配置**: 建议配置多个API密钥以提高系统可用性

## 故障排除

### 常见问题

1. **API密钥错误**: 检查各API提供商的密钥是否正确配置
2. **文件不存在**: 确保所有必需文件都在正确位置
3. **速度限制429错误**: 程序会自动处理，如果频繁出现请检查网络连接
4. **网络超时**: 检查网络连接，系统会自动重试和故障转移
5. **磁盘空间不足**: 清理磁盘空间或更改输出目录
6. **API故障转移**: 如果主API失败，系统会自动切换到备用API

### 日志查看

查看 `batch_process.log` 文件获取详细的错误信息和处理日志。

## 示例输出

处理成功后，您会看到类似以下的输出：

```
API配置:
✅ OpenRouter API已配置
✅ Gemini API已配置
开始批量处理推文数据集...
支持多API故障转移:
- 主API: OpenRouter (moonshotai/kimi-k2:free)
- 备用API: Gemini (gemini-2.5-pro)
- 自动切换: 当主API失败时自动使用备用API
2025-09-05 10:37:58,660 - INFO - 读取数据文件: twillot-public-post-sorted.json
2025-09-05 10:37:58,677 - INFO - 数据集包含 1667 条记录
2025-09-05 10:37:58,677 - INFO - 开始处理记录 0 到 0 (共 1 条)
处理推文: 100%|█████████████████████████████████████████████████████████| 1/1 [00:22<00:00, 22.31s/it]
2025-09-05 10:38:20,998 - INFO - 处理完成 - 成功: 1, 失败: 0
2025-09-05 10:38:20,999 - INFO - 进度已保存到: processing_progress.json

API使用统计:
  siliconflow: 1 次
  novita: 1 次
  openrouter: 1 次

处理完成！请查看output文件夹中的结果。
```

## 项目结构

```
X_svg/
├── batch_process_tweets.py      # 主处理脚本
├── batch_generate_svg.py        # SVG批量生成脚本
├── run_example.py              # 示例运行脚本
├── config_manager.py           # 配置管理器 (新增)
├── api_client.py               # API客户端模块
├── config.json                 # 配置文件
├── processing_progress.json    # 进度跟踪文件
├── requirements.txt            # 依赖包
├── .env                        # 环境变量
├── svg提示词.txt               # SVG生成提示词
├── 小红书标题提示词.txt         # 标题生成提示词
├── 小红书文案提示词.txt         # 正文生成提示词
├── twillot-public-post-sorted.json  # 推文数据
├── output/                     # 输出目录
├── 测试/                       # 测试SVG文件
└── README.md                   # 项目文档
```
