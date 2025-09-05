#!/usr/bin/env python3
"""
批量SVG生成脚本 - 使用OpenRouter API分批生成以避免超时
"""

import os
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from api_client import create_client
from config_manager import get_config_manager

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_styles():
    """加载所有风格"""
    try:
        with open("svg测试提示词.txt", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取基础提示词
        base_prompt = content.split("## 待处理内容：")[0]
        
        # 解析29种风格
        styles = []
        import re
        pattern = r'(\d+)\.\s*(.+?)\s*\(([^)]+)\)\s*\n\s*(.+?)(?=\n\n\d+\.|\n\n\*\*|$)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        # 只取前29个风格，避免解析到CSS链接等错误内容
        for match in matches[:29]:
            number, name_cn, name_en, description = match
            # 验证这是否是有效的风格（数字应该在1-29范围内）
            if 1 <= int(number) <= 29:
                styles.append({
                    'number': int(number),
                    'name_cn': name_cn.strip(),
                    'name_en': name_en.strip(),
                    'description': description.strip(),
                    'filename': f"{number.zfill(2)}-{name_cn.strip()} ({name_en.strip()}).svg"
                })
        
        return styles, base_prompt
        
    except Exception as e:
        logger.error(f"加载风格失败: {e}")
        return [], ""

def generate_svg_for_style(client, style_info, base_prompt, test_content):
    """为指定风格生成SVG"""
    try:
        # 构建提示词
        modified_prompt = base_prompt.replace(
            "请从以下29种设计风格中根据内容随机选择1种",
            f"请使用第{style_info['number']}种设计风格：{style_info['name_cn']} ({style_info['name_en']})"
        )
        
        if "## 待处理内容：" not in modified_prompt:
            modified_prompt += f"\n\n## 待处理内容：\n{test_content}"
        
        # 调用API
        logger.info(f"生成: {style_info['filename']}")
        response = client.call_api(
            system_prompt="你是一位专业的SVG设计师，擅长创建高质量的SVG图像。",
            user_content=modified_prompt
        )
        
        if not response:
            return None
        
        # 清理SVG内容
        import re
        svg_content = re.sub(r'```svg\n?', '', response)
        svg_content = re.sub(r'\n?```$', '', svg_content)
        svg_content = re.sub(r'@import url\([^)]+\);', '', svg_content)
        svg_content = svg_content.strip()
        
        if not svg_content.startswith('<svg'):
            svg_match = re.search(r'<svg[^>]*>', svg_content)
            if svg_match:
                svg_content = svg_content[svg_match.start():]
        
        return svg_content
        
    except Exception as e:
        logger.error(f"生成失败: {style_info['filename']} - {e}")
        return None

def main():
    """主函数"""
    print("批量SVG生成工具")
    print("=" * 50)
    
    # 使用配置管理器加载配置
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        print("配置管理器初始化成功")
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return
    
    styles, base_prompt = load_styles()
    if not styles:
        logger.error("未加载到风格")
        return
    
    # 获取测试内容
    try:
        with open("svg测试提示词.txt", 'r', encoding='utf-8') as f:
            content = f.read()
            test_content = content.split("## 待处理内容：")[-1].strip()
    except Exception as e:
        logger.error(f"加载测试内容失败: {e}")
        return
    
    # 创建API客户端
    try:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY 环境变量未设置")
        
        client = create_client(
            provider='openrouter',
            api_key=api_key,
            model='deepseek/deepseek-r1-0528:free',
            timeout=180
        )
        logger.info("OpenRouter API客户端创建成功")
    except Exception as e:
        logger.error(f"创建API客户端失败: {e}")
        return
    
    # 创建输出目录
    output_dir = Path("测试")
    output_dir.mkdir(exist_ok=True)
    
    # 检查已存在的文件
    existing_files = set(f.name for f in output_dir.glob("*.svg"))
    print(f"已存在 {len(existing_files)} 个SVG文件")
    
    # 找出需要生成的风格
    remaining_styles = [s for s in styles if s['filename'] not in existing_files]
    print(f"还需要生成 {len(remaining_styles)} 个风格")
    
    if not remaining_styles:
        print("所有风格已生成完成！")
        return
    
    # 询问要生成多少个
    try:
        batch_size = input(f"请输入要生成的数量 (1-{len(remaining_styles)}, 默认5): ").strip()
        if not batch_size:
            batch_size = 5
        else:
            batch_size = int(batch_size)
            batch_size = min(batch_size, len(remaining_styles))
    except ValueError:
        batch_size = 5
    
    print(f"将生成 {batch_size} 个风格...")
    
    # 生成SVG
    success_count = 0
    for i, style in enumerate(remaining_styles[:batch_size]):
        print(f"\n[{i+1}/{batch_size}] 生成: {style['filename']}")
        
        # 检查文件是否已存在
        filepath = output_dir / style['filename']
        if filepath.exists():
            print(f"文件已存在，跳过: {style['filename']}")
            continue
        
        # 生成SVG
        svg_content = generate_svg_for_style(client, style, base_prompt, test_content)
        
        if svg_content and svg_content.startswith('<svg'):
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print(f"✓ 生成成功: {style['filename']}")
            success_count += 1
        else:
            print(f"✗ 生成失败: {style['filename']}")
        
        # 遵守API速率限制
        if i < batch_size - 1:  # 最后一个不需要等待
            print("等待4秒...")
            time.sleep(4)
    
    print("\n" + "=" * 50)
    print(f"批量生成完成！成功生成 {success_count} 个SVG文件")
    print(f"当前总共有 {len(list(output_dir.glob('*.svg')))} 个SVG文件")

if __name__ == "__main__":
    main()