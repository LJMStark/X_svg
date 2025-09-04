#!/usr/bin/env python3
"""
批量处理推文数据集，为每条记录生成SVG图像和小红书文案
"""

import os
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging
from tqdm import tqdm
from dotenv import load_dotenv
from api_client import create_client, BaseAPIClient

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_process.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TweetProcessor:
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化推文处理器
        
        Args:
            config: 配置字典，如果为None则从文件加载
        """
        if config is None:
            config = self._load_config()
        self.config = config
        
        # 读取提示词文件
        self.svg_prompt = self._read_prompt_file(config["files"]["svg_prompt"])
        self.title_prompt = self._read_prompt_file(config["files"]["title_prompt"])
        self.xiaohongshu_prompt = self._read_prompt_file(config["files"]["xiaohongshu_prompt"])
        
        self.output_dir = Path(config["files"]["output_dir"])
        self.output_dir.mkdir(exist_ok=True)
        
        self.clients: Dict[str, BaseAPIClient] = {} # API客户端缓存
        self.task_config = self.config.get("tasks", {})
        self.api_stats = {} # API使用统计

    def _read_prompt_file(self, file_path: str) -> str:
        """读取提示词文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"提示词文件未找到: {file_path}")
            raise
        except Exception as e:
            logger.error(f"读取提示词文件失败 {file_path}: {e}")
            raise

    def _sanitize_filename(self, filename: str, max_length: int = 100) -> str:
        """
        清理文件名，移除不合法字符
        
        Args:
            filename: 原始文件名
            max_length: 最大长度
            
        Returns:
            清理后的文件名
        """
        # 移除或替换不合法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # 限制长度
        if len(filename) > max_length:
            filename = filename[:max_length].rstrip()
        
        # 确保不为空
        if not filename:
            filename = "untitled"
            
        return filename

    def _get_client(self, provider: str, model: str) -> Optional[BaseAPIClient]:
        """获取或创建并缓存API客户端"""
        client_key = f"{provider}_{model}"
        if client_key in self.clients:
            return self.clients[client_key]

        provider_config = self.config.get("api_providers", {}).get(provider, {})
        api_key = provider_config.get("key")
        timeout = provider_config.get("timeout", 30)

        if not api_key:
            logger.error(f"未找到提供商 {provider} 的API密钥")
            return None
        
        client = create_client(provider, api_key, model, timeout=timeout)
        if client:
            self.clients[client_key] = client
        return client

    def _call_api_for_task(self, task_name: str, system_prompt: str, user_content: str, max_retries: int = 3) -> Optional[str]:
        """为特定任务调用API，带重试和故障转移"""
        task_info = self.task_config.get(task_name)
        if not task_info:
            logger.error(f"任务 '{task_name}' 未在配置中定义")
            return None

        for attempt in range(max_retries):
            # 尝试主API
            primary_info = task_info.get("primary")
            client = self._get_client(primary_info["provider"], primary_info["model"])
            if client:
                response = client.call_api(system_prompt, user_content)
                if response:
                    logger.info(f"主API {primary_info['provider']} 为任务 {task_name} 调用成功")
                    self.api_stats[primary_info['provider']] = self.api_stats.get(primary_info['provider'], 0) + 1
                    return response
            
            logger.warning(f"主API为任务 {task_name} 调用失败 (尝试 {attempt + 1}/{max_retries})")

            # 尝试备用API
            fallback_info = task_info.get("fallback")
            if fallback_info:
                client = self._get_client(fallback_info["provider"], fallback_info["model"])
                if client:
                    response = client.call_api(system_prompt, user_content)
                    if response:
                        logger.info(f"备用API {fallback_info['provider']} 为任务 {task_name} 调用成功")
                        self.api_stats[fallback_info['provider']] = self.api_stats.get(fallback_info['provider'], 0) + 1
                        return response
                logger.warning(f"备用API为任务 {task_name} 调用失败 (尝试 {attempt + 1}/{max_retries})")

            wait_time = 5 * (attempt + 1)
            logger.info(f"等待 {wait_time} 秒后重试")
            time.sleep(wait_time)
        
        logger.error(f"任务 {task_name} 的所有API均调用失败")
        self.api_stats["failed"] = self.api_stats.get("failed", 0) + 1
        return None
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件并使用环境变量覆盖"""
        config_file = os.getenv("CONFIG_FILE", "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"加载或解析配置文件 {config_file} 失败: {e}")
            raise

        # 从环境变量覆盖API密钥
        providers = config.get("api_providers", {})
        key_mapping = {
            "OPENROUTER_API_KEY": "openrouter",
            "GEMINI_API_KEY": "gemini",
            "SILICONFLOW_API_KEY": "siliconflow",
            "MOONSHOT_API_KEY": "moonshot",
            "NOVITA_API_KEY": "novita"
        }
        for env_var, provider_name in key_mapping.items():
            if env_var in os.environ and provider_name in providers:
                providers[provider_name]["key"] = os.environ[env_var]
        
        return config
    
    def get_api_stats(self) -> Dict[str, int]:
        """
        获取API使用统计
        
        Returns:
            API使用统计字典
        """
        return self.api_stats.copy()

    def _generate_svg(self, full_text: str) -> Optional[str]:
        """
        生成SVG图像
        
        Args:
            full_text: 推文内容
            
        Returns:
            SVG代码，失败时返回None
        """
        logger.info("生成SVG图像...")
        svg_raw = self._call_api_for_task(
            task_name="svg",
            system_prompt=self.svg_prompt,
            user_content=full_text
        )
        if not svg_raw:
            return None
        return self._clean_svg_text(svg_raw)

    def _generate_title(self, full_text: str) -> Optional[str]:
        """生成小红书标题"""
        logger.info("生成小红书标题...")
        title = self._call_api_for_task(
            task_name="title",
            system_prompt=self.title_prompt,
            user_content=full_text
        )
        return title.strip() if title else None

    def _generate_body(self, full_text: str, title: str) -> Optional[str]:
        """生成小红书正文"""
        logger.info("生成小红书正文...")
        user_content_for_body = f"标题：{title}\n\n根据这个标题和以下推文内容生成一篇小红书风格的正文和标签。\n\n推文内容：\n{full_text}"
        body = self._call_api_for_task(
            task_name="body",
            system_prompt=self.xiaohongshu_prompt,
            user_content=user_content_for_body
        )
        return body.strip() if body else None

    def _clean_svg_text(self, svg_content: str) -> str:
        """清理SVG文本：去除markdown围栏、移除@import、替换为系统字体、修复XML实体引用。"""
        text = (svg_content or "").strip()
        if text.startswith("```svg"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # 移除可能的 @import 行（通配任意URL）
        try:
            text = re.sub(r"@import\s+url\([^)]*\);", "", text)
        except Exception:
            pass

        # 修复无效的XML实体引用
        try:
            # 修复 &; 这种无效的实体引用
            text = re.sub(r'&;(?![a-zA-Z#])', '•', text)
            # 修复其他可能的无效实体引用
            text = re.sub(r'&(?![a-zA-Z#][a-zA-Z0-9]*;)', '&amp;', text)
        except Exception:
            pass

        # 字体替换为系统可用字体
        replacements = {
            "'Noto Serif SC'": "'Arial', 'Helvetica', sans-serif",
            "'Noto Sans SC'": "'Arial', 'Helvetica', sans-serif",
            "'Space Mono'": "'Courier New', monospace",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def _is_svg_mostly_chinese(self, svg_text: str) -> bool:
        """严格中文检测：必须包含中文，且不包含任何英文字母。"""
        if not svg_text:
            return False
        # 提取所有可见文本（粗略）：删除标签
        try:
            visible = re.sub(r"<[^>]+>", " ", svg_text)
        except Exception:
            visible = svg_text

        chinese_chars = re.findall(r"[\u4e00-\u9fff]", visible)
        latin_letters = re.findall(r"[A-Za-z]", visible)

        # 至少包含一定数量中文，且不允许出现任何英文字母
        return len(chinese_chars) >= 5 and len(latin_letters) == 0

    def _strip_latin_in_text_nodes(self, svg_text: str) -> str:
        """在 <text> 节点中移除英文字母及下划线/点号，保留中文与标点。"""
        if not svg_text:
            return svg_text
        try:
            def repl(m):
                inner = m.group(1)
                # 移除拉丁字母与常见代码样式字符
                inner = re.sub(r"[A-Za-z_.]+", "", inner)
                return f">{inner}<"

            return re.sub(r">([^<]*)<", repl, svg_text)
        except Exception:
            return svg_text
    
    def _save_files(self, folder_path: Path, svg_content: str, title: str, body: str) -> bool:
        """保存所有生成的文件"""
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            
            (folder_path / "generated.svg").write_text(self._clean_svg_text(svg_content), encoding='utf-8')
            (folder_path / "title.txt").write_text(title, encoding='utf-8')
            (folder_path / "body.txt").write_text(body, encoding='utf-8')

            logger.info(f"文件保存成功: {folder_path}")
            return True
        except Exception as e:
            logger.error(f"保存文件失败 {folder_path}: {e}")
            return False

    def _is_already_processed(self, folder_path: Path) -> bool:
        """
        检查记录是否已经处理过

        Args:
            folder_path: 文件夹路径

        Returns:
            是否已处理
        """
        required_files = ["generated.svg", "body.txt", "title.txt"]
        return all((folder_path / file).exists() for file in required_files)

    def _get_unique_folder_name(self, base_name: str) -> str:
        """
        获取唯一的文件夹名称（处理重复）

        Args:
            base_name: 基础名称

        Returns:
            唯一的文件夹名称
        """
        folder_name = self._sanitize_filename(base_name)
        folder_path = self.output_dir / folder_name
        counter = 1
        while folder_path.exists():
            folder_path = self.output_dir / f"{folder_name}_{counter}"
            counter += 1
        return folder_path.name

    def process_single_tweet(self, tweet_data: Dict, index: int) -> bool:
        """
        处理单条推文

        Args:
            tweet_data: 推文数据
            index: 索引号

        Returns:
            处理是否成功
        """
        full_text = tweet_data.get('full_text', '')
        if not full_text:
            logger.warning(f"推文 {index} 没有full_text内容，跳过")
            return False

        logger.info(f"处理推文 {index}: {full_text[:50]}...")

        # 检查是否已处理 (基于推文内容可能生成不确定标题，所以先生成标题再检查)
        title = self._generate_title(full_text)
        if not title:
            logger.error(f"推文 {index} 标题生成失败")
            return False

        folder_name = self._sanitize_filename(title)
        folder_path = self.output_dir / folder_name
        if self._is_already_processed(folder_path):
            logger.info(f"推文 {index} (标题: {title}) 已处理，跳过")
            return True

        body = self._generate_body(full_text, title)
        if not body:
            logger.error(f"推文 {index} 正文生成失败")
            return False

        svg_content = self._generate_svg(full_text)
        if not svg_content:
            logger.error(f"推文 {index} SVG生成失败")
            return False

        # 获取唯一的文件夹名称
        unique_folder_name = self._get_unique_folder_name(title)
        final_folder_path = self.output_dir / unique_folder_name

        success = self._save_files(final_folder_path, svg_content, title, body)
        if success:
            logger.info(f"推文 {index} 处理完成")
        return success

    def process_dataset(self, json_file: str, start_index: int = 0, max_count: Optional[int] = None):
        """
        批量处理数据集

        Args:
            json_file: JSON数据文件路径
            start_index: 开始索引
            max_count: 最大处理数量
        """
        try:
            # 读取数据
            logger.info(f"读取数据文件: {json_file}")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError("数据文件应包含推文数组")

            total_count = len(data)
            logger.info(f"数据集包含 {total_count} 条记录")

            # 确定处理范围
            end_index = min(start_index + max_count, total_count) if max_count else total_count
            process_data = data[start_index:end_index]

            logger.info(f"开始处理记录 {start_index} 到 {end_index-1} (共 {len(process_data)} 条)")

            # 统计
            success_count = 0
            failed_count = 0

            # 处理每条记录
            for i, tweet_data in enumerate(tqdm(process_data, desc="处理推文")):
                actual_index = start_index + i

                try:
                    if self.process_single_tweet(tweet_data, actual_index):
                        success_count += 1
                    else:
                        failed_count += 1

                except KeyboardInterrupt:
                    logger.info("用户中断处理")
                    break
                except Exception as e:
                    logger.error(f"处理推文 {actual_index} 时发生致命错误: {e}", exc_info=True)
                    failed_count += 1

            # 输出统计结果
            logger.info(f"处理完成 - 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            logger.error(f"批量处理失败: {e}", exc_info=True)
            raise

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量处理推文数据集')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--input', help='输入JSON文件（覆盖配置文件）')
    parser.add_argument('--svg-prompt', help='SVG提示词文件（覆盖配置文件）')
    parser.add_argument('--xiaohongshu-prompt', help='小红书提示词文件（覆盖配置文件）')
    parser.add_argument('--start', type=int, default=0, help='开始索引')
    parser.add_argument('--count', type=int, help='处理数量限制')
    parser.add_argument('--stats', action='store_true', help='显示API使用统计')

    args = parser.parse_args()

    try:
        # 加载配置
        config = TweetProcessor._load_config(None)
        
        # 命令行参数覆盖配置
        if args.input:
            config["files"]["input_json"] = args.input
        if args.svg_prompt:
            config["files"]["svg_prompt"] = args.svg_prompt
        if args.xiaohongshu_prompt:
            config["files"]["xiaohongshu_prompt"] = args.xiaohongshu_prompt
        
        processor = TweetProcessor(config)

        processor.process_dataset(
            json_file=config["files"]["input_json"],
            start_index=args.start,
            max_count=args.count
        )
        
        # 显示统计信息
        if args.stats:
            stats = processor.get_api_stats()
            logger.info("API使用统计:")
            for api, count in stats.items():
                logger.info(f"  {api}: {count} 次")

    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return 1

    return 0

if __name__ == "__main__":
    # Ensure logging is configured before anything runs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('batch_process.log', mode='w'),
            logging.StreamHandler()
        ]
    )
    exit(main())
