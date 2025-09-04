#!/usr/bin/env python3
"""
Gemini API测试脚本
用于调试Gemini API调用问题
"""

import os
import json
import logging
from dotenv import load_dotenv
import openai

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gemini_api():
    """测试Gemini API调用"""
    
    # 获取API密钥
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("未找到GEMINI_API_KEY环境变量")
        return
    
    logger.info(f"使用API密钥: {api_key[:10]}...")
    
    # 创建OpenAI兼容的客户端
    base_url = "http://xai-studio.top:8000/openai/v1"
    model = "gemini-2.5-flash"
    
    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        logger.info("Gemini客户端创建成功")
        
        # 测试简单的聊天完成
        system_prompt = "你是一个有用的AI助手。"
        user_content = "请说'Hello World'。"  # 简化请求内容
        
        logger.info("开始API调用...")
        logger.info(f"系统提示词: {system_prompt}")
        logger.info(f"用户内容: {user_content}")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=500,  # 减少token数量
            temperature=0.7
        )
        
        logger.info("API调用成功！")
        logger.info(f"响应对象类型: {type(response)}")
        logger.info(f"响应对象属性: {dir(response)}")
        
        if hasattr(response, 'choices'):
            logger.info(f"choices数量: {len(response.choices)}")
            for i, choice in enumerate(response.choices):
                logger.info(f"choice {i}: {choice}")
                if hasattr(choice, 'message'):
                    logger.info(f"message: {choice.message}")
                    if hasattr(choice.message, 'content'):
                        content = choice.message.content
                        logger.info(f"content: {content}")
                        if content and content.strip():
                            logger.info("✅ 成功获取到内容！")
                            return True
                        else:
                            logger.warning("❌ 内容为空")
                    else:
                        logger.warning("❌ message对象没有content属性")
                else:
                    logger.warning("❌ choice对象没有message属性")
        else:
            logger.warning("❌ 响应对象没有choices属性")
        
        # 尝试其他可能的属性
        logger.info("检查其他可能的响应属性...")
        for attr in ['content', 'text', 'response', 'result', 'data']:
            if hasattr(response, attr):
                logger.info(f"找到属性 {attr}: {getattr(response, attr)}")
        
        return False
        
    except Exception as e:
        logger.error(f"API调用失败: {e}")
        logger.error(f"错误类型: {type(e)}")
        return False

def test_gemini_models():
    """测试获取可用模型列表"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("未找到GEMINI_API_KEY环境变量")
        return
    
    base_url = "http://xai-studio.top:8000/openai/v1"
    
    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        logger.info("获取可用模型列表...")
        models = client.models.list()
        
        logger.info(f"找到 {len(models.data)} 个模型:")
        for model in models.data:
            logger.info(f"  - {model.id}")
            
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")

def test_gemini_raw_request():
    """测试原始HTTP请求"""
    
    import requests
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("未找到GEMINI_API_KEY环境变量")
        return
    
    base_url = "http://xai-studio.top:8000/openai/v1"
    model = "gemini-2.5-flash"
    
    url = f"{base_url}/chat/completions"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个有用的AI助手。"},
            {"role": "user", "content": "请说'Hello World'"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        logger.info("发送原始HTTP请求...")
        logger.info(f"URL: {url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"响应状态码: {response.status_code}")
        logger.info(f"响应头: {dict(response.headers)}")
        logger.info(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"JSON响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
        
    except Exception as e:
        logger.error(f"原始HTTP请求失败: {e}")

if __name__ == "__main__":
    logger.info("=== Gemini API 测试开始 ===")
    
    print("\n1. 测试获取可用模型...")
    test_gemini_models()
    
    print("\n2. 测试原始HTTP请求...")
    test_gemini_raw_request()
    
    print("\n3. 测试OpenAI兼容客户端...")
    test_gemini_api()
    
    logger.info("=== Gemini API 测试完成 ===")
