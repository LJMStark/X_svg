#!/usr/bin/env python3
"""
提示词过滤测试脚本
用于测试哪些关键词会触发代理服务的过滤
"""

import os
import logging
from dotenv import load_dotenv
import openai

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_prompt_variations():
    """测试不同的提示词变体"""
    
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
        
        # 测试不同的提示词变体
        test_cases = [
            {
                "name": "基础文本生成",
                "system": "你是一个有用的助手。",
                "user": "请说'Hello World'。"
            },
            {
                "name": "代码生成（避免SVG关键词）",
                "system": "你是一个代码生成专家。",
                "user": "请生成一个简单的HTML页面，内容是'Hello World'。"
            },
            {
                "name": "设计描述（避免图像关键词）",
                "system": "你是一个设计专家。",
                "user": "请描述一个现代风格的Hello World设计。"
            },
            {
                "name": "XML格式（避免SVG关键词）",
                "system": "你是一个XML专家。",
                "user": "请生成一个XML文档，内容是'Hello World'。"
            },
            {
                "name": "标记语言（避免SVG关键词）",
                "system": "你是一个标记语言专家。",
                "user": "请生成一个简单的标记代码，内容是'Hello World'。"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n--- 测试 {i}: {test_case['name']} ---")
            
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": test_case["system"]},
                        {"role": "user", "content": test_case["user"]}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                
                if response.choices and len(response.choices) > 0:
                    choice = response.choices[0]
                    content = choice.message.content
                    finish_reason = choice.finish_reason
                    
                    logger.info(f"finish_reason: {finish_reason}")
                    logger.info(f"content: {content}")
                    
                    if content and content.strip():
                        logger.info("✅ 成功获取到内容！")
                    else:
                        logger.warning("❌ 内容为空")
                else:
                    logger.warning("❌ 响应对象没有choices")
                    
            except Exception as e:
                logger.error(f"测试失败: {e}")
                
    except Exception as e:
        logger.error(f"客户端创建失败: {e}")

if __name__ == "__main__":
    logger.info("=== 提示词过滤测试开始 ===")
    test_prompt_variations()
    logger.info("=== 提示词过滤测试完成 ===")
