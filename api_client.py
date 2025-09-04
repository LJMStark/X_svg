#!/usr/bin/env python3
"""
通用API客户端模块 - 支持多个API提供商
"""

import openai
import time
import logging
import requests
import os
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class BaseAPIClient(ABC):
    """API客户端基类"""
    
    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.kwargs = kwargs
        self._last_call_time = 0
        
    @abstractmethod
    def call_api(self, system_prompt: str, user_content: str, **kwargs) -> Optional[str]:
        """调用API"""
        pass
    
    def _enforce_rate_limit(self, min_interval: float = 1.0):
        """强制执行速度限制"""
        current_time = time.time()
        time_since_last = current_time - self._last_call_time
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            logger.info(f"等待速度限制: {wait_time:.1f}秒")
            time.sleep(wait_time)
        self._last_call_time = time.time()

class OpenAICompatibleClient(BaseAPIClient):
    """通用OpenAI兼容API客户端"""
    def __init__(self, api_key: str, base_url: str, model: str, default_headers: Optional[Dict] = None, timeout: int = 30):
        super().__init__(api_key, base_url, model)
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=default_headers or {},
            timeout=timeout
        )
    
    def call_api(self, system_prompt: str, user_content: str, **kwargs) -> Optional[str]:
        try:
            self._enforce_rate_limit(kwargs.get("min_interval", 1.0))
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs.get("extra_params", {})
            )
            
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.warning(f"{self.base_url} 速度限制: {e}")
            else:
                logger.error(f"API call to {self.base_url} failed: {e}")
            return None

class OpenRouterClient(OpenAICompatibleClient):
    """OpenRouter API客户端"""
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model=model,
            default_headers={
                "HTTP-Referer": "https://github.com",
                "X-Title": "TweetProcessor"
            },
            **kwargs
        )

class GeminiClient(OpenAICompatibleClient):
    """Gemini API客户端 - 使用代理端点"""
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="http://xai-studio.top:8000/openai/v1",
            model=model,
            **kwargs
        )

class MoonshotClient(OpenAICompatibleClient):
    """Moonshot (月之暗面) API客户端"""
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
            model=model,
            **kwargs
        )

class NovitaAIClient(OpenAICompatibleClient):
    """Novita.ai API客户端"""
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://api.novita.ai/openai",
            model=model,
            **kwargs
        )

class SiliconFlowClient(BaseAPIClient):
    """SiliconFlow API客户端 - 使用requests"""
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1",
            model=model,
            **kwargs
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.endpoint = f"{self.base_url}/chat/completions"
        self.timeout = kwargs.get("timeout", 30)

    def call_api(self, system_prompt: str, user_content: str, **kwargs) -> Optional[str]:
        """调用SiliconFlow API"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            **kwargs.get("extra_params", {})
        }
        
        try:
            self._enforce_rate_limit(kwargs.get("min_interval", 1.0))
            
            response = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if data.get("choices") and data["choices"][0].get("message"):
                return data["choices"][0]["message"].get("content")
            else:
                logger.warning(f"SiliconFlow API响应格式异常: {data}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SiliconFlow API调用失败: {e}")
            return None

# --- Client Factory ---

CLIENT_CLASSES = {
    "openrouter": OpenRouterClient,
    "gemini": GeminiClient,
    "siliconflow": SiliconFlowClient,
    "moonshot": MoonshotClient,
    "novita": NovitaAIClient
}

def create_client(provider: str, api_key: str, model: str, **kwargs) -> Optional[BaseAPIClient]:
    """
    根据提供商名称创建API客户端实例
    
    Args:
        provider: API提供商名称 (e.g., "openrouter")
        api_key: API密钥
        model: 模型名称
        **kwargs: 传递给客户端构造函数的其他参数
        
    Returns:
        API客户端实例或None
    """
    if provider not in CLIENT_CLASSES:
        logger.error(f"未知的API提供商: {provider}")
        return None
    
    try:
        client_class = CLIENT_CLASSES[provider]
        client = client_class(api_key=api_key, model=model, **kwargs)
        logger.info(f"{provider} 客户端创建成功 (模型: {model})")
        return client
    except Exception as e:
        logger.error(f"创建 {provider} 客户端失败: {e}")
        return None