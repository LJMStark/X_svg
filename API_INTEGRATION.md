# API集成文档

本文档详细说明了项目中多API提供商的集成架构、配置方法和故障转移机制。

## 概述

项目支持5个API提供商，每个任务都有独立的API配置和故障转移机制，确保高可用性和稳定性。

## 支持的API提供商

### 1. OpenRouter
- **端点**: `https://openrouter.ai/api/v1`
- **特点**: 支持多种模型，价格透明
- **速度限制**: 4秒间隔
- **主要用途**: SVG生成（主API）

### 2. Novita.ai
- **端点**: `https://api.novita.ai/openai`
- **特点**: DeepSeek模型，稳定可靠
- **速度限制**: 2秒间隔
- **主要用途**: 正文生成（主API），SVG生成（备用API）

### 3. SiliconFlow
- **端点**: `https://api.siliconflow.cn/v1`
- **特点**: 国内服务，访问速度快
- **速度限制**: 2秒间隔
- **主要用途**: 标题生成（主API），SVG生成（备用API2）

### 4. Moonshot
- **端点**: `https://api.moonshot.cn/v1`
- **特点**: Kimi模型，中文优化
- **速度限制**: 2秒间隔
- **主要用途**: 各任务的备用API

### 5. Gemini
- **端点**: `http://xai-studio.top:8000/openai/v1`
- **特点**: 通过代理服务访问
- **速度限制**: 2秒间隔
- **主要用途**: 备用API

## 任务配置

### 标题生成 (title)
```json
{
  "title": {
    "primary": {
      "provider": "siliconflow",
      "model": "deepseek-ai/DeepSeek-V3.1"
    },
    "fallback": {
      "provider": "moonshot",
      "model": "kimi-k2-0711-preview"
    }
  }
}
```

### 正文生成 (body)
```json
{
  "body": {
    "primary": {
      "provider": "novita",
      "model": "deepseek/deepseek-v3.1"
    },
    "fallback": {
      "provider": "moonshot",
      "model": "kimi-k2-0711-preview"
    }
  }
}
```

### SVG生成 (svg)
```json
{
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
}
```

## 环境变量配置

### 必需的环境变量
```bash
# OpenRouter API密钥
export OPENROUTER_API_KEY="your_openrouter_key"

# Novita API密钥
export NOVITA_API_KEY="your_novita_key"

# SiliconFlow API密钥
export SILICONFLOW_API_KEY="your_siliconflow_key"

# Moonshot API密钥
export MOONSHOT_API_KEY="your_moonshot_key"

# Gemini API密钥
export GEMINI_API_KEY="your_gemini_key"
```

### 可选的环境变量
```bash
# 自定义配置文件路径
export CONFIG_FILE="custom_config.json"

# 日志级别
export LOG_LEVEL="INFO"
```

## 故障转移机制

### 自动故障转移流程
1. **主API调用**: 首先尝试主API
2. **失败检测**: 检测API调用失败（网络错误、认证错误、速率限制等）
3. **备用API切换**: 自动切换到下一个备用API
4. **重试机制**: 每个API最多重试3次
5. **递增延迟**: 429错误时使用递增延迟策略

### 重试策略
```python
# 重试配置
max_retries = 3
base_delay = 5  # 基础延迟5秒

# 429错误特殊处理
if "429" in error_message:
    wait_time = 10 * (attempt + 1)  # 10, 20, 30秒
else:
    wait_time = base_delay * (attempt + 1)  # 5, 10, 15秒
```

## API客户端架构

### 基础客户端类
```python
class BaseAPIClient:
    """API客户端基类"""
    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
    
    def call_api(self, system_prompt: str, user_content: str) -> Optional[str]:
        """调用API生成内容"""
        pass
```

### 提供商特定客户端
```python
class OpenRouterClient(BaseAPIClient):
    """OpenRouter API客户端"""
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model=model,
            default_headers={
                "HTTP-Referer": "https://github.com",
                "X-Title": "TweetProcessor"
            }
        )
```

## 速率限制处理

### 提供商特定限制
- **OpenRouter**: 4秒间隔，每分钟16次请求
- **Novita**: 2秒间隔
- **SiliconFlow**: 2秒间隔
- **Moonshot**: 2秒间隔
- **Gemini**: 2秒间隔

### 智能等待机制
```python
def wait_for_rate_limit(self, provider: str):
    """根据提供商等待速率限制"""
    intervals = {
        "openrouter": 4.0,
        "gemini": 2.0,
        "novita": 2.0,
        "siliconflow": 2.0,
        "moonshot": 2.0
    }
    wait_time = intervals.get(provider, 2.0)
    time.sleep(wait_time)
```

## 错误处理

### 常见错误类型
1. **认证错误 (401)**: API密钥无效或过期
2. **速率限制 (429)**: 请求过于频繁
3. **网络错误**: 连接超时或网络中断
4. **服务器错误 (5xx)**: 服务端临时故障
5. **内容错误 (4xx)**: 请求参数错误

### 错误处理策略
```python
def handle_api_error(self, error: Exception, attempt: int) -> bool:
    """处理API错误"""
    error_msg = str(error)
    
    if "401" in error_msg:
        logger.error("API密钥无效")
        return False  # 不重试
    
    if "429" in error_msg:
        wait_time = 10 * (attempt + 1)
        logger.warning(f"速率限制，等待 {wait_time} 秒")
        time.sleep(wait_time)
        return True  # 重试
    
    if "5xx" in error_msg:
        logger.warning("服务器错误，重试中...")
        return True  # 重试
    
    return False  # 其他错误不重试
```

## 性能监控

### API使用统计
```python
# 统计信息收集
api_stats = {
    "openrouter": 0,
    "novita": 0,
    "siliconflow": 0,
    "moonshot": 0,
    "gemini": 0,
    "failed": 0
}

# 更新统计
def update_stats(self, provider: str, success: bool):
    if success:
        self.api_stats[provider] += 1
    else:
        self.api_stats["failed"] += 1
```

### 性能指标
- **成功率**: 各API的成功调用比例
- **响应时间**: 平均API响应时间
- **故障转移频率**: 备用API使用频率
- **错误分布**: 各类错误的分布情况

## 最佳实践

### 1. API密钥管理
- 使用环境变量存储API密钥
- 定期轮换API密钥
- 监控API使用量和费用

### 2. 故障转移配置
- 为每个任务配置多个备用API
- 根据API稳定性调整优先级
- 定期测试各API的可用性

### 3. 速率限制优化
- 根据API限制调整请求间隔
- 实现智能等待机制
- 监控速率限制使用情况

### 4. 错误处理
- 实现完善的错误分类和处理
- 记录详细的错误日志
- 设置合理的重试策略

## 故障排除

### 常见问题
1. **所有API都失败**: 检查网络连接和API密钥
2. **频繁的429错误**: 调整请求间隔或增加API配额
3. **认证错误**: 验证API密钥的有效性
4. **响应超时**: 检查网络连接和API服务状态

### 调试方法
```bash
# 测试API连接
python -c "from api_client import create_client; client = create_client('openrouter', 'your_key', 'model'); print('API连接成功')"

# 查看API统计
python batch_process_tweets.py --stats

# 检查配置文件
python -c "import json; print(json.load(open('config.json')))"
```

## 更新日志

### 2025-09-05
- 将OpenRouter设为主API用于SVG生成
- 优化故障转移机制
- 增强错误处理和重试逻辑
- 添加性能监控和统计功能
