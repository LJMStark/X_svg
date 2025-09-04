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
from api_client import create_api_clients

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
        # 加载配置
        if config is None:
            config = self._load_config()
        
        self.config = config
        
        # 读取提示词文件
        svg_prompt_file = config["files"]["svg_prompt"]
        xiaohongshu_prompt_file = config["files"]["xiaohongshu_prompt"]
        self.svg_prompt = self._read_prompt_file(svg_prompt_file)
        self.xiaohongshu_prompt = self._read_prompt_file(xiaohongshu_prompt_file)
        
        # 创建输出目录
        self.output_dir = Path(config["files"]["output_dir"])
        self.output_dir.mkdir(exist_ok=True)
        
        # 初始化API客户端管理器
        self.api_manager = create_api_clients(config)
        
        # 统计信息
        self.api_stats = {"openrouter": 0, "gemini": 0, "failed": 0}
        
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
    
    def _call_api_with_fallback(self, system_prompt: str, user_content: str, 
                              max_retries: int = 3) -> Tuple[str, Optional[str]]:
        """
        带故障转移的API调用
        
        Args:
            system_prompt: 系统提示词
            user_content: 用户输入内容
            max_retries: 最大重试次数
            
        Returns:
            (api_provider, response_content) 元组
        """
        for attempt in range(max_retries):
            api_provider, response = self.api_manager.call_with_fallback(
                system_prompt, user_content
            )
            
            if response:
                # 更新统计信息
                if api_provider in self.api_stats:
                    self.api_stats[api_provider] += 1
                logger.info(f"API调用成功 - 提供商: {api_provider}")
                return api_provider, response
            else:
                self.api_stats["failed"] += 1
                logger.warning(f"API调用失败 (尝试 {attempt + 1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)  # 递增延迟：5, 10, 15秒
                    logger.info(f"等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
        
        logger.error(f"API调用最终失败，重试次数已达上限")
        return "none", None
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        # 优先从环境变量读取
        config_file = os.getenv("CONFIG_FILE", "config.json")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            logger.error(f"配置文件未找到: {config_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise
        
        # 从环境变量覆盖API密钥
        if "OPENROUTER_API_KEY" in os.environ:
            if "openrouter" not in config:
                config["openrouter"] = {}
            config["openrouter"]["key"] = os.environ["OPENROUTER_API_KEY"]
            config["openrouter"]["enabled"] = True
        
        if "GEMINI_API_KEY" in os.environ:
            if "gemini" not in config:
                config["gemini"] = {}
            config["gemini"]["key"] = os.environ["GEMINI_API_KEY"]
            config["gemini"]["enabled"] = True
        
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
        api_provider, svg_raw = self._call_api_with_fallback(
            system_prompt=self.svg_prompt,
            user_content=full_text
        )
        if not svg_raw:
            return None

        cleaned = self._clean_svg_text(svg_raw)

        # 若中文检测未通过，则追加强制中文约束重试一次
        if not self._is_svg_mostly_chinese(cleaned):
            strengthened_user = (
                f"{full_text}\n\n"
                "约束（必须严格遵守）：\n"
                "1) 所有文本内容必须为中文；\n"
                "2) 不得出现任何英文字母或英文单词；\n"
                "3) 仅输出纯 SVG 源码，不要包含代码块围栏。"
            )
            retry_api_provider, retry_svg = self._call_api_with_fallback(
                system_prompt=self.svg_prompt,
                user_content=strengthened_user
            )
            if retry_svg:
                cleaned_retry = self._clean_svg_text(retry_svg)
                if self._is_svg_mostly_chinese(cleaned_retry):
                    return cleaned_retry
                # 若仍未通过，最后进行一次文本节点英文字母剔除
                cleaned_retry = self._strip_latin_in_text_nodes(cleaned_retry)
                return cleaned_retry

        logger.info(f"SVG生成完成 - 使用API: {api_provider}")
        return cleaned

    def _clean_svg_text(self, svg_content: str) -> str:
        """清理SVG文本：去除markdown围栏、移除@import、替换为系统字体。"""
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
    
    def _generate_xiaohongshu_content(self, full_text: str) -> Optional[Tuple[str, str]]:
        """
        生成小红书文案
        
        Args:
            full_text: 推文内容
            
        Returns:
            (标题, 正文和标签) 元组，失败时返回None
        """
        logger.info("生成小红书文案...")
        api_provider, response = self._call_api_with_fallback(
            system_prompt=self.xiaohongshu_prompt,
            user_content=full_text
        )
        
        if not response:
            return None
        
        logger.info(f"小红书文案生成完成 - 使用API: {api_provider}")
            
        # 解析响应，提取标题和正文
        try:
            lines = response.strip().split('\n')
            title = ""
            body_lines = []
            
            # 处理API实际返回的格式：第一行是标题，可能有"2. 正文"标记
            if lines:
                # 第一行作为标题
                title = lines[0].strip()
                
                # 从第二行开始处理正文
                for i, line in enumerate(lines[1:], 1):
                    line = line.strip()
                    # 跳过"2. 正文"、"正文:"等标记行
                    if line in ["2. 正文", "正文:", "Body:", "1. 标题", "标题:"]:
                        continue
                    # 跳过空行
                    if not line:
                        continue
                    body_lines.append(line)
            
            body = '\n'.join(body_lines)
            return title, body
            
        except Exception as e:
            logger.error(f"解析小红书文案失败: {e}")
            # 如果解析失败，将整个响应作为正文，生成简单标题
            return "Generated Content", response

    def _save_files(self, folder_path: Path, svg_content: str, title: str, body: str) -> bool:
        """
        保存生成的文件

        Args:
            folder_path: 文件夹路径
            svg_content: SVG内容
            title: 标题内容
            body: 正文内容

        Returns:
            保存是否成功
        """
        try:
            folder_path.mkdir(parents=True, exist_ok=True)

            # 保存SVG文件（使用统一清理逻辑）
            svg_file = folder_path / "generated.svg"
            cleaned_svg = self._clean_svg_text(svg_content)
            
            with open(svg_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_svg)

            # 保存正文文件（第一行作为标题）
            body_file = folder_path / "body.txt"
            with open(body_file, 'w', encoding='utf-8') as f:
                f.write(body)

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
        required_files = ["generated.svg", "body.txt"]
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
        while folder_path.exists() and not self._is_already_processed(folder_path):
            folder_name = f"{self._sanitize_filename(base_name)}_{counter}"
            folder_path = self.output_dir / folder_name
            counter += 1

        return folder_name

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

        # 生成SVG
        svg_content = self._generate_svg(full_text)
        if not svg_content:
            logger.error(f"推文 {index} SVG生成失败")
            return False

        # 生成小红书文案
        xiaohongshu_result = self._generate_xiaohongshu_content(full_text)
        if not xiaohongshu_result:
            logger.error(f"推文 {index} 小红书文案生成失败")
            return False

        title, body = xiaohongshu_result

        # 从body的第一行提取文件夹名称
        body_lines = body.strip().split('\n')
        folder_title = body_lines[0].strip() if body_lines else f"tweet_{index}"
        
        # 创建文件夹
        folder_name = self._get_unique_folder_name(folder_title)
        folder_path = self.output_dir / folder_name

        # 检查是否已处理
        if self._is_already_processed(folder_path):
            logger.info(f"推文 {index} 已处理，跳过")
            return True

        # 保存文件
        success = self._save_files(folder_path, svg_content, title, body)

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
                    logger.error(f"处理推文 {actual_index} 时发生错误: {e}")
                    failed_count += 1

            # 输出统计结果
            logger.info(f"处理完成 - 成功: {success_count}, 失败: {failed_count}")

        except Exception as e:
            logger.error(f"批量处理失败: {e}")
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
    exit(main())
