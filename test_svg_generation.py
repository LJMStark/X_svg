#!/usr/bin/env python3
"""
SVG生成测试脚本
用于调试复杂请求（SVG生成）的问题
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

def test_svg_generation():
    """测试SVG生成请求"""
    
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
        
        # 测试SVG生成请求（这是实际使用中的复杂请求）
        system_prompt = """你是一个专业的SVG图像生成专家。请根据用户的要求生成高质量的SVG图像代码。

要求：
1. 只返回SVG代码，不要包含任何解释文字
2. SVG代码必须是完整的、可用的
3. 图像要美观、现代、有设计感
4. 使用合适的颜色搭配和布局"""
        
        user_content = "请生成一个简单的SVG图像，内容是'Hello World'，使用现代设计风格。"
        
        logger.info("开始SVG生成API调用...")
        logger.info(f"系统提示词长度: {len(system_prompt)} 字符")
        logger.info(f"用户内容长度: {len(user_content)} 字符")
        
        # 尝试不同的max_tokens设置
        for max_tokens in [100, 200, 500, 1000]:
            logger.info(f"\n--- 测试 max_tokens={max_tokens} ---")
            
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                
                logger.info(f"API调用成功！max_tokens={max_tokens}")
                logger.info(f"finish_reason: {response.choices[0].finish_reason}")
                
                if response.choices and len(response.choices) > 0:
                    choice = response.choices[0]
                    content = choice.message.content
                    logger.info(f"content: {content}")
                    
                    if content and content.strip():
                        logger.info("✅ 成功获取到SVG内容！")
                        return True
                    else:
                        logger.warning("❌ 内容为空")
                else:
                    logger.warning("❌ 响应对象没有choices")
                    
            except Exception as e:
                logger.error(f"max_tokens={max_tokens} 时API调用失败: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"客户端创建失败: {e}")
        return False

def test_simple_svg():
    """测试简单的SVG请求"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("未找到GEMINI_API_KEY环境变量")
        return
    
    base_url = "http://xai-studio.top:8000/openai/v1"
    model = "gemini-2.5-flash"
    
    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 使用更简单的提示词
        system_prompt = "生成SVG图像。"
        user_content = "创建一个简单的Hello World SVG。"
        
        logger.info("测试简单SVG请求...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            logger.info(f"简单请求结果: {content}")
            return content and content.strip()
        
        return False
        
    except Exception as e:
        logger.error(f"简单SVG测试失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== SVG生成测试开始 ===")
    
    print("\n1. 测试简单SVG请求...")
    simple_result = test_simple_svg()
    
    print("\n2. 测试完整SVG生成...")
    svg_result = test_svg_generation()
    
    logger.info("=== SVG生成测试完成 ===")
    logger.info(f"简单请求: {'✅ 成功' if simple_result else '❌ 失败'}")
    logger.info(f"完整SVG: {'✅ 成功' if svg_result else '❌ 失败'}")
