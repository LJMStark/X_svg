#!/usr/bin/env python3
"""
使用示例脚本 - 批量处理推文数据集
"""

import os
from dotenv import load_dotenv
from batch_process_tweets import TweetProcessor

# 加载环境变量
load_dotenv()

def main():
    # 检查API密钥配置
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not openrouter_key and not gemini_key:
        print("错误：请至少设置一个API密钥")
        print("选项1: export OPENROUTER_API_KEY='your_openrouter_key'")
        print("选项2: export GEMINI_API_KEY='your_gemini_key'")
        return
    
    print("API配置:")
    if openrouter_key:
        print("✅ OpenRouter API已配置")
    if gemini_key:
        print("✅ Gemini API已配置")
    
    try:
        # 创建处理器（自动从配置文件加载）
        processor = TweetProcessor()
        
        # 批量处理数据集
        # 参数说明：
        # - json_file: 输入的JSON文件路径
        # - start_index: 开始处理的索引（默认0）
        # - max_count: 最大处理数量（None表示处理所有）
        
        print("开始批量处理推文数据集...")
        print("支持多API故障转移:")
        print("- 主API: OpenRouter (moonshotai/kimi-k2:free)")
        print("- 备用API: Gemini (gemini-2.5-pro)")
        print("- 自动切换: 当主API失败时自动使用备用API")
        
        # 示例1: 处理前5条记录（用于测试）
        processor.process_dataset(
            json_file="twillot-public-post-sorted.json",
            start_index=0,
            max_count=1
        )
        
        # 示例2: 处理所有记录（取消注释以使用）
        # processor.process_dataset(
        #     json_file="twillot-public-post-sorted.json",
        #     start_index=0,
        #     max_count=None
        # )
        
        # 示例3: 从第10条开始处理20条记录
        # processor.process_dataset(
        #     json_file="twillot-public-post-sorted.json",
        #     start_index=10,
        #     max_count=20
        # )
        
        # 显示API使用统计
        stats = processor.get_api_stats()
        print("\nAPI使用统计:")
        for api, count in stats.items():
            print(f"  {api}: {count} 次")
        
        print("\n处理完成！请查看output文件夹中的结果。")
        
    except Exception as e:
        print(f"处理失败: {e}")

if __name__ == "__main__":
    main()
