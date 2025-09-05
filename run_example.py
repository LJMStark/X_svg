#!/usr/bin/env python3
"""
使用示例脚本 - 批量处理推文数据集
"""

import os
from dotenv import load_dotenv
from batch_process_tweets import TweetProcessor
from config_manager import get_config_manager

# 加载环境变量
load_dotenv()

def main():
    # 使用配置管理器检查配置
    try:
        config_manager = get_config_manager()
        print("配置管理器初始化成功")
        
        # 显示已启用的API提供商
        enabled_providers = config_manager.get_enabled_providers()
        print("已启用的API提供商:")
        for provider in enabled_providers:
            key_display = config_manager.get_provider_key(provider)
            print(f"✅ {provider}: {key_display}")
        
        if not enabled_providers:
            print("错误：未启用任何API提供商")
            print("请在配置文件中启用至少一个API提供商")
            return
    
    except Exception as e:
        print(f"配置管理器初始化失败: {e}")
        return
    
    try:
        # 创建处理器（使用新的配置管理）
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
