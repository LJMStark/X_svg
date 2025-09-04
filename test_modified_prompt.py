#!/usr/bin/env python3
"""
修改版提示词测试脚本
测试避免过滤关键词的提示词
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

def test_modified_prompt():
    """测试修改版的提示词"""
    
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
        
        # 读取修改版的提示词
        with open("svg提示词_修改版.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
        
        user_content = "请为以下内容创建一个知识卡片：Go on more walks. Walk for no reason. Walk to solve problems. Walk to think. Walk to breathe. Walk to be alone. Walk to be with others. Walk to explore. Walk to discover. Walk to heal. Walk to grow. Walk to live."
        
        logger.info("开始测试修改版提示词...")
        logger.info(f"系统提示词长度: {len(system_prompt)} 字符")
        logger.info(f"用户内容长度: {len(user_content)} 字符")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=500,
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
                return True
            else:
                logger.warning("❌ 内容为空")
                return False
        else:
            logger.warning("❌ 响应对象没有choices")
            return False
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== 修改版提示词测试开始 ===")
    result = test_modified_prompt()
    logger.info(f"测试结果: {'✅ 成功' if result else '❌ 失败'}")
    logger.info("=== 修改版提示词测试完成 ===")
