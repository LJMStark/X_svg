# 配置文件说明文档

本文档详细说明了项目中各种配置文件的格式、参数和用法。

## 配置文件概览

项目使用以下配置文件进行系统配置：

- `config.json` - 主配置文件
- `.env` - 环境变量文件
- `requirements.txt` - Python依赖包
- `processing_progress.json` - 处理进度记录

## 主配置文件 (config.json)

### 完整配置示例
```json
{
  "api_providers": {
    "openrouter": {
      "enabled": true,
      "key": "",
      "base_url": "https://openrouter.ai/api/v1",
      "timeout": 180
    },
    "gemini": {
      "enabled": false,
      "key": "",
      "base_url": "http://xai-studio.top:8000/openai/v1",
      "timeout": 180
    },
    "siliconflow": {
      "enabled": true,
      "key": "",
      "base_url": "https://api.siliconflow.cn/v1",
      "timeout": 180
    },
    "moonshot": {
      "enabled": true,
      "key": "",
      "base_url": "https://api.moonshot.cn/v1",
      "timeout": 180
    },
    "novita": {
      "enabled": true,
      "key": "",
      "base_url": "https://api.novita.ai/openai",
      "timeout": 180
    }
  },
  "tasks": {
    "title": {
      "primary": {
        "provider": "siliconflow",
        "model": "deepseek-ai/DeepSeek-V3.1"
      },
      "fallback": {
        "provider": "moonshot",
        "model": "kimi-k2-0711-preview"
      }
    },
    "body": {
      "primary": {
        "provider": "novita",
        "model": "deepseek/deepseek-v3.1"
      },
      "fallback": {
        "provider": "moonshot",
        "model": "kimi-k2-0711-preview"
      }
    },
    "svg": {
      "primary": {
        "provider": "openrouter",
        "model": "deepseek/deepseek-chat"
      },
      "fallback": {
        "provider": "novita",
        "model": "deepseek/deepseek-v3.1"
      },
      "fallback2": {
        "provider": "siliconflow",
        "model": "deepseek-ai/DeepSeek-V3.1"
      },
      "fallback3": {
        "provider": "moonshot",
        "model": "kimi-k2-0711-preview"
      }
    }
  },
  "rate_limit": {
    "openrouter_interval": 4.0,
    "gemini_interval": 2.0,
    "retry_attempts": 3,
    "retry_delay_seconds": 5
  },
  "files": {
    "input_json": "twillot-public-post-sorted.json",
    "svg_prompt": "svg提示词.txt",
    "title_prompt": "小红书标题提示词.txt",
    "xiaohongshu_prompt": "小红书文案提示词.txt",
    "output_dir": "output"
  },
  "logging": {
    "level": "INFO",
    "file": "batch_process.log",
    "console": true
  }
}
```

### 配置项说明

#### API提供商配置 (api_providers)
```json
{
  "provider_name": {
    "enabled": true,           // 是否启用该提供商
    "key": "",                 // API密钥（通常通过环境变量设置）
    "base_url": "https://...", // API端点URL
    "timeout": 180             // 请求超时时间（秒）
  }
}
```

**支持的提供商**:
- `openrouter` - OpenRouter API
- `gemini` - Gemini API（通过代理）
- `siliconflow` - SiliconFlow API
- `moonshot` - Moonshot API
- `novita` - Novita.ai API

#### 任务配置 (tasks)
```json
{
  "task_name": {
    "primary": {
      "provider": "provider_name",  // 主API提供商
      "model": "model_name"         // 使用的模型
    },
    "fallback": {                   // 备用API（可选）
      "provider": "provider_name",
      "model": "model_name"
    },
    "fallback2": {                  // 第二备用API（可选）
      "provider": "provider_name",
      "model": "model_name"
    },
    "fallback3": {                  // 第三备用API（可选）
      "provider": "provider_name",
      "model": "model_name"
    }
  }
}
```

**支持的任务**:
- `title` - 标题生成
- `body` - 正文生成
- `svg` - SVG图像生成

#### 速率限制配置 (rate_limit)
```json
{
  "openrouter_interval": 4.0,      // OpenRouter请求间隔（秒）
  "gemini_interval": 2.0,          // Gemini请求间隔（秒）
  "retry_attempts": 3,             // 重试次数
  "retry_delay_seconds": 5         // 重试延迟（秒）
}
```

#### 文件配置 (files)
```json
{
  "input_json": "twillot-public-post-sorted.json",     // 输入数据文件
  "svg_prompt": "svg提示词.txt",                       // SVG生成提示词
  "title_prompt": "小红书标题提示词.txt",               // 标题生成提示词
  "xiaohongshu_prompt": "小红书文案提示词.txt",         // 正文生成提示词
  "output_dir": "output"                               // 输出目录
}
```

#### 日志配置 (logging)
```json
{
  "level": "INFO",        // 日志级别 (DEBUG, INFO, WARNING, ERROR)
  "file": "batch_process.log",  // 日志文件名
  "console": true         // 是否输出到控制台
}
```

## 环境变量文件 (.env)

### 环境变量配置
```bash
# OpenRouter API密钥
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Novita API密钥
NOVITA_API_KEY=your_novita_api_key_here

# SiliconFlow API密钥
SILICONFLOW_API_KEY=your_siliconflow_api_key_here

# Moonshot API密钥
MOONSHOT_API_KEY=your_moonshot_api_key_here

# Gemini API密钥
GEMINI_API_KEY=your_gemini_api_key_here

# 可选配置
CONFIG_FILE=config.json
LOG_LEVEL=INFO
```

### 环境变量说明
- **API密钥**: 各API提供商的认证密钥
- **CONFIG_FILE**: 自定义配置文件路径（可选）
- **LOG_LEVEL**: 日志级别（可选）

## 依赖包配置 (requirements.txt)

```txt
openai>=1.0.0
tqdm>=4.65.0
python-dotenv>=1.0.0
```

### 依赖包说明
- `openai` - OpenAI兼容的API客户端
- `tqdm` - 进度条显示
- `python-dotenv` - 环境变量加载

## 进度记录文件 (processing_progress.json)

### 进度文件格式
```json
{
  "last_processed_index": 0,
  "total_processed": 1,
  "total_success": 1,
  "total_failed": 0,
  "last_update": "2025-09-05 10:38:20"
}
```

### 进度字段说明
- `last_processed_index` - 最后处理的记录索引
- `total_processed` - 总处理数量
- `total_success` - 成功处理数量
- `total_failed` - 失败处理数量
- `last_update` - 最后更新时间

## 配置优先级

系统按以下优先级加载配置：

1. **环境变量** - 最高优先级
2. **config.json** - 中等优先级
3. **默认值** - 最低优先级

### 环境变量覆盖示例
```bash
# 环境变量会覆盖config.json中的设置
export OPENROUTER_API_KEY="new_key"
export CONFIG_FILE="custom_config.json"
```

## 配置验证

### 自动验证
系统启动时会自动验证配置：

1. **文件存在性检查** - 验证所有必需文件是否存在
2. **API密钥验证** - 检查API密钥是否设置
3. **配置格式验证** - 验证JSON格式是否正确
4. **依赖检查** - 检查Python依赖包是否安装

### 手动验证
```bash
# 验证配置文件格式
python -c "import json; json.load(open('config.json'))"

# 验证环境变量
python -c "import os; print('OPENROUTER_API_KEY:', bool(os.getenv('OPENROUTER_API_KEY')))"

# 测试API连接
python -c "from api_client import create_client; print('API客户端测试成功')"
```

## 配置最佳实践

### 1. 安全性
- 不要在配置文件中硬编码API密钥
- 使用环境变量存储敏感信息
- 将`.env`文件添加到`.gitignore`

### 2. 灵活性
- 为不同环境创建不同的配置文件
- 使用环境变量进行配置覆盖
- 保持配置文件的向后兼容性

### 3. 维护性
- 定期备份配置文件
- 记录配置变更历史
- 使用版本控制管理配置文件

### 4. 性能优化
- 根据API限制调整速率限制配置
- 优化超时设置
- 合理配置重试策略

## 故障排除

### 常见配置问题

1. **配置文件格式错误**
   ```bash
   # 检查JSON格式
   python -m json.tool config.json
   ```

2. **API密钥未设置**
   ```bash
   # 检查环境变量
   echo $OPENROUTER_API_KEY
   ```

3. **文件路径错误**
   ```bash
   # 检查文件是否存在
   ls -la svg提示词.txt
   ```

4. **依赖包缺失**
   ```bash
   # 安装依赖包
   pip install -r requirements.txt
   ```

### 调试配置
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 使用自定义配置
export CONFIG_FILE=debug_config.json

# 运行配置测试
python -c "from batch_process_tweets import TweetProcessor; processor = TweetProcessor(); print('配置加载成功')"
```

## 配置更新日志

### 2025-09-05
- 更新SVG生成API优先级（OpenRouter为主API）
- 优化速率限制配置
- 增强配置验证机制
- 添加进度记录功能
