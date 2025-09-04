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

class OpenRouterClient(BaseAPIClient):
    """OpenRouter API客户端"""
    
    def __init__(self, api_key: str, model: str = "moonshotai/kimi-k2:free"):
        super().__init__(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model=model
        )
        
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": "https://github.com",
                "X-Title": "TweetProcessor"
            }
        )
    
    def call_api(self, system_prompt: str, user_content: str, **kwargs) -> Optional[str]:
        """调用OpenRouter API"""
        try:
            self._enforce_rate_limit(4.0)  # OpenRouter限制: 4秒间隔
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.warning(f"OpenRouter速度限制: {e}")
            else:
                logger.error(f"OpenRouter API调用失败: {e}")
            return None

class GeminiClient(BaseAPIClient):
    """Gemini API客户端 - 使用代理端点"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        super().__init__(
            api_key=api_key,
            base_url="http://xai-studio.top:8000/openai/v1",  # 使用OpenAI兼容端点
            model=model
        )
        
        # 使用OpenAI兼容的客户端连接代理
        try:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=self.base_url
            )
            logger.info("Gemini客户端初始化成功")
        except Exception as e:
            logger.error(f"Gemini客户端初始化失败: {e}")
            raise
    
    def call_api(self, system_prompt: str, user_content: str, **kwargs) -> Optional[str]:
        """调用Gemini API通过代理"""
        try:
            self._enforce_rate_limit(2.0)  # Gemini限制: 2秒间隔
            
            # 使用OpenAI兼容的格式
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', 500),  # 限制token数量避免length问题
                temperature=kwargs.get('temperature', 0.7),
                **kwargs
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.debug(f"Gemini API响应内容: {content}")
                if content and content.strip():
                    return content.strip()
                else:
                    logger.warning("Gemini API返回空文本")
                    return None
            else:
                logger.warning(f"Gemini API响应格式异常: 缺少choices，响应: {response}")
                return None
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.warning(f"Gemini速度限制: {e}")
            elif "403" in error_msg or "unauthorized" in error_msg.lower():
                logger.warning(f"Gemini API密钥无效: {e}")
            else:
                logger.error(f"Gemini API调用失败: {e}")
            return None

class APIClientManager:
    """API客户端管理器 - 支持故障转移"""
    
    def __init__(self, clients: Dict[str, BaseAPIClient], primary: str = "openrouter"):
        self.clients = clients
        self.primary = primary
        self.fallback_order = [c for c in clients.keys() if c != primary] + [primary]
        
    def call_with_fallback(self, system_prompt: str, user_content: str, **kwargs) -> tuple[str, Optional[str]]:
        """
        带故障转移的API调用
        
        Returns:
            (api_provider, response_content)
        """
        # 首先尝试主API
        if self.primary in self.clients:
            response = self.clients[self.primary].call_api(system_prompt, user_content, **kwargs)
            if response:
                return self.primary, response
            logger.warning(f"主API {self.primary} 调用失败，尝试备用API")
        
        # 按顺序尝试备用API
        for provider in self.fallback_order:
            if provider in self.clients:
                logger.info(f"尝试备用API: {provider}")
                response = self.clients[provider].call_api(system_prompt, user_content, **kwargs)
                if response:
                    return provider, response
                logger.warning(f"备用API {provider} 调用失败")
        
        logger.error("所有API提供商都调用失败")
        return "none", None

def create_api_clients(config: Dict[str, Any]) -> APIClientManager:
    """
    根据配置创建API客户端管理器
    
    Args:
        config: 配置字典，包含API设置
        
    Returns:
        APIClientManager实例
    """
    clients = {}
    
    # OpenRouter客户端
    if config.get("openrouter", {}).get("enabled", True):
        openrouter_config = config["openrouter"]
        if openrouter_config.get("key"):
            clients["openrouter"] = OpenRouterClient(
                api_key=openrouter_config["key"],
                model=openrouter_config.get("model", "moonshotai/kimi-k2:free")
            )
            logger.info("OpenRouter客户端已启用")
    
    # Gemini客户端
    if config.get("gemini", {}).get("enabled", False):
        gemini_config = config["gemini"]
        if gemini_config.get("key"):
            clients["gemini"] = GeminiClient(
                api_key=gemini_config["key"],
                model=gemini_config.get("model", "gemini-2.5-pro")
            )
            logger.info("Gemini客户端已启用")
    
    if not clients:
        raise ValueError("没有配置任何可用的API客户端")
    
    # 确定主API
    primary = config.get("primary_api", "openrouter")
    if primary not in clients:
        primary = list(clients.keys())[0]
        logger.warning(f"主API {primary} 不可用，使用 {primary} 作为主API")
    
    return APIClientManager(clients, primary)