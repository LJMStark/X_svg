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
from config_manager import get_config_manager, get_file_config, get_task_config, get_batch_config

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
    def __init__(self, config_file: str = None):
        """
        初始化推文处理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认配置
        """
        # 使用新的配置管理器
        self.config_manager = get_config_manager(config_file)
        self.config = self.config_manager.get_config()
        
        # 获取文件配置
        file_config = get_file_config()
        
        # 读取提示词文件
        self.svg_prompt = self._read_prompt_file(file_config.svg_prompt)
        self.title_prompt = self._read_prompt_file(file_config.title_prompt)
        self.xiaohongshu_prompt = self._read_prompt_file(file_config.xiaohongshu_prompt)
        
        self.output_dir = Path(file_config.output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 进度记录文件
        self.progress_file = Path("processing_progress.json")
        
        self.clients: Dict[str, BaseAPIClient] = {} # API客户端缓存
        self.task_config = self.config.get("tasks", {})
        self.api_stats = {} # API使用统计
        
        # 获取批处理配置
        self.batch_config = get_batch_config()
        logger.info(f"批处理配置: 批量大小={self.batch_config.batch_size}, 保存间隔={self.batch_config.progress_save_interval}")

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

        # 使用配置管理器获取API配置
        provider_config = self.config_manager.get_api_provider_config(provider)
        if not provider_config.enabled:
            logger.error(f"API提供商 {provider} 未启用")
            return None

        if not provider_config.key:
            logger.error(f"未找到提供商 {provider} 的API密钥")
            return None
        
        client = create_client(provider, provider_config.key, model, timeout=provider_config.timeout)
        if client:
            self.clients[client_key] = client
        return client

    def _call_api_for_task(self, task_name: str, system_prompt: str, user_content: str, max_retries: int = 3) -> Optional[str]:
        """为特定任务调用API，带重试和多级故障转移"""
        # 使用配置管理器获取任务配置
        task_config = get_task_config(task_name)
        if not task_config:
            logger.error(f"任务 '{task_name}' 未在配置中定义")
            return None

        # 获取所有可用的API配置（按优先级排序）
        api_configs = []
        if task_config.primary:
            api_configs.append(("主API", task_config.primary))
        if task_config.fallback:
            api_configs.append(("备用API", task_config.fallback))
        if task_config.fallback2:
            api_configs.append(("备用API2", task_config.fallback2))
        if task_config.fallback3:
            api_configs.append(("备用API3", task_config.fallback3))

        for attempt in range(max_retries):
            # 依次尝试所有配置的API
            for api_label, api_info in api_configs:
                client = self._get_client(api_info["provider"], api_info["model"])
                if client:
                    response = client.call_api(system_prompt, user_content)
                    if response:
                        logger.info(f"{api_label} {api_info['provider']} 为任务 {task_name} 调用成功")
                        self.api_stats[api_info['provider']] = self.api_stats.get(api_info['provider'], 0) + 1
                        return response
                
                logger.warning(f"{api_label} {api_info['provider']} 为任务 {task_name} 调用失败 (尝试 {attempt + 1}/{max_retries})")

            # 所有API都失败后，等待重试
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                logger.info(f"等待 {wait_time} 秒后重试")
                time.sleep(wait_time)
        
        logger.error(f"任务 {task_name} 的所有API均调用失败")
        self.api_stats["failed"] = self.api_stats.get("failed", 0) + 1
        return None
    
    def get_api_stats(self) -> Dict[str, int]:
        """
        获取API使用统计
        
        Returns:
            API使用统计字典
        """
        return self.api_stats.copy()

    def _load_progress(self) -> Dict[str, Any]:
        """
        加载处理进度
        
        Returns:
            进度信息字典
        """
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                logger.info(f"加载进度记录: 已处理 {progress.get('last_processed_index', -1) + 1} 条记录")
                return progress
            else:
                logger.info("未找到进度记录文件，从头开始处理")
                return {"last_processed_index": -1, "total_processed": 0, "total_success": 0, "total_failed": 0}
        except Exception as e:
            logger.warning(f"加载进度记录失败: {e}，从头开始处理")
            return {"last_processed_index": -1, "total_processed": 0, "total_success": 0, "total_failed": 0}

    def _save_progress(self, last_index: int, success_count: int, failed_count: int):
        """
        保存处理进度
        
        Args:
            last_index: 最后处理的索引
            success_count: 成功数量
            failed_count: 失败数量
        """
        try:
            progress = {
                "last_processed_index": last_index,
                "total_processed": last_index + 1,
                "total_success": success_count,
                "total_failed": failed_count,
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            logger.debug(f"进度已保存: 索引 {last_index}")
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
    
    def _process_batch(self, batch_data: List[Dict], start_index: int) -> Tuple[int, int]:
        """
        处理一批推文数据
        
        Args:
            batch_data: 批量推文数据
            start_index: 开始索引
            
        Returns:
            (成功数量, 失败数量)
        """
        batch_success = 0
        batch_failed = 0
        
        # 批处理开始时重置所有API客户端的速率限制计时器
        for client in self.clients.values():
            if hasattr(client, 'reset_rate_limit'):
                client.reset_rate_limit()
        
        for i, tweet_data in enumerate(batch_data):
            actual_index = start_index + i
            
            try:
                if self.process_single_tweet(tweet_data, actual_index):
                    batch_success += 1
                else:
                    batch_failed += 1
                    
                # 仅在批处理模式下使用短缓冲时间
                if (i < len(batch_data) - 1 and 
                    self.batch_config.enable_batching and 
                    self.batch_config.api_call_buffer_time > 0):
                    time.sleep(self.batch_config.api_call_buffer_time)
                    
            except KeyboardInterrupt:
                logger.info("用户中断处理")
                break
            except Exception as e:
                logger.error(f"处理推文 {actual_index} 时发生错误: {e}")
                batch_failed += 1
        
        return batch_success, batch_failed

    def get_auto_start_index(self, json_file: str) -> int:
        """
        获取自动开始索引（从上次停止的地方继续）
        
        Args:
            json_file: JSON数据文件路径
            
        Returns:
            建议的开始索引
        """
        progress = self._load_progress()
        last_index = progress.get("last_processed_index", -1)
        
        # 验证数据文件是否存在且有效
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            total_count = len(data)
            
            if last_index >= total_count - 1:
                logger.info("所有记录已处理完成")
                return total_count
            else:
                next_index = last_index + 1
                logger.info(f"从索引 {next_index} 开始继续处理 (剩余 {total_count - next_index} 条)")
                return next_index
                
        except Exception as e:
            logger.error(f"验证数据文件失败: {e}")
            return 0

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
        
        if not title:
            return None
            
        # 处理API返回的多个标题，提取第一个有效标题
        title = title.strip()
        
        # 如果返回的内容包含多个标题（以"标题："开头），则提取第一个
        if "标题：" in title:
            # 分割内容并找到所有有效的标题行
            lines = title.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("标题："):
                    # 提取标题内容（去掉"标题："前缀）
                    extracted_title = line[3:].strip()
                    if extracted_title:
                        logger.info(f"提取标题: {extracted_title}")
                        return extracted_title
        
        # 如果没有找到"标题："格式，但内容很长，尝试按行分割并返回第一行
        if len(title) > 50:
            lines = title.split('\n')
            first_line = lines[0].strip()
            if first_line:
                logger.info(f"使用第一行作为标题: {first_line}")
                return first_line
        
        # 如果都不符合，直接返回原始内容
        return title

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

    def process_dataset(self, json_file: str, start_index: int = None, max_count: Optional[int] = None, auto_continue: bool = True):
        """
        批量处理数据集

        Args:
            json_file: JSON数据文件路径
            start_index: 开始索引，如果为None且auto_continue=True，则自动从上次停止处继续
            max_count: 最大处理数量
            auto_continue: 是否自动从上次停止的地方继续
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

            # 确定开始索引
            if start_index is None and auto_continue:
                start_index = self.get_auto_start_index(json_file)
            elif start_index is None:
                start_index = 0

            # 如果已经处理完所有记录
            if start_index >= total_count:
                logger.info("所有记录已处理完成，无需继续处理")
                return

            # 确定处理范围
            end_index = min(start_index + max_count, total_count) if max_count else total_count
            process_data = data[start_index:end_index]

            logger.info(f"开始处理记录 {start_index} 到 {end_index-1} (共 {len(process_data)} 条)")

            # 统计
            success_count = 0
            failed_count = 0

            # 批量处理逻辑
            if self.batch_config.enable_batching:
                logger.info(f"启用批处理模式: 批量大小={self.batch_config.batch_size}")
                
                # 分批处理
                total_batches = (len(process_data) + self.batch_config.batch_size - 1) // self.batch_config.batch_size
                batch_count = 0
                
                for batch_start in range(0, len(process_data), self.batch_config.batch_size):
                    batch_end = min(batch_start + self.batch_config.batch_size, len(process_data))
                    batch_data = process_data[batch_start:batch_end]
                    batch_actual_start = start_index + batch_start
                    
                    batch_count += 1
                    logger.info(f"处理第 {batch_count}/{total_batches} 批 (索引 {batch_actual_start}-{batch_actual_start + len(batch_data) - 1})")
                    
                    # 处理当前批次
                    batch_success, batch_failed = self._process_batch(batch_data, batch_actual_start)
                    success_count += batch_success
                    failed_count += batch_failed
                    
                    # 定期保存进度（减少I/O操作）
                    if batch_count % self.batch_config.progress_save_interval == 0 or batch_count == total_batches:
                        last_index = batch_actual_start + len(batch_data) - 1
                        self._save_progress(last_index, success_count, failed_count)
                        logger.info(f"批次 {batch_count} 完成，进度已保存")
                    
                    # 批次间休息（避免API速率限制）
                    if batch_count < total_batches and self.batch_config.batch_rest_time > 0:
                        logger.info(f"批次间休息 {self.batch_config.batch_rest_time} 秒...")
                        time.sleep(self.batch_config.batch_rest_time)
            else:
                # 原有的逐条处理模式
                logger.info("使用逐条处理模式")
                for i, tweet_data in enumerate(tqdm(process_data, desc="处理推文")):
                    actual_index = start_index + i

                    try:
                        if self.process_single_tweet(tweet_data, actual_index):
                            success_count += 1
                        else:
                            failed_count += 1

                        # 每处理一条记录就保存进度
                        self._save_progress(actual_index, success_count, failed_count)

                    except KeyboardInterrupt:
                        logger.info("用户中断处理")
                        # 保存当前进度
                        self._save_progress(actual_index, success_count, failed_count)
                        break
                    except Exception as e:
                        logger.error(f"处理推文 {actual_index} 时发生致命错误: {e}", exc_info=True)
                        failed_count += 1
                        # 即使失败也保存进度
                        self._save_progress(actual_index, success_count, failed_count)

            # 输出统计结果
            logger.info(f"处理完成 - 成功: {success_count}, 失败: {failed_count}")
            logger.info(f"进度已保存到: {self.progress_file}")

        except Exception as e:
            logger.error(f"批量处理失败: {e}", exc_info=True)
            raise

def main():
    """主函数"""
    import argparse
    from config_manager import get_config_manager

    parser = argparse.ArgumentParser(description='批量处理推文数据集')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--input', help='输入JSON文件（覆盖配置文件）')
    parser.add_argument('--svg-prompt', help='SVG提示词文件（覆盖配置文件）')
    parser.add_argument('--xiaohongshu-prompt', help='小红书提示词文件（覆盖配置文件）')
    parser.add_argument('--start', type=int, help='开始索引（不指定则自动从上次停止处继续）')
    parser.add_argument('--count', type=int, help='处理数量限制')
    parser.add_argument('--stats', action='store_true', help='显示API使用统计')
    parser.add_argument('--no-auto-continue', action='store_true', help='禁用自动继续功能，从头开始处理')
    parser.add_argument('--reset-progress', action='store_true', help='重置进度记录，从头开始处理')
    parser.add_argument('--batch-size', type=int, help='批处理大小（覆盖配置文件）')
    parser.add_argument('--no-batching', action='store_true', help='禁用批处理模式，使用逐条处理')
    parser.add_argument('--progress-interval', type=int, help='进度保存间隔（批次数）')
    parser.add_argument('--slow-mode', action='store_true', help='启用慢速模式，增加API调用间隔')

    args = parser.parse_args()

    try:
        # 使用配置管理器
        config_manager = get_config_manager(args.config)
        
        # 命令行参数覆盖配置
        if args.input:
            config_manager.config["files"]["input_json"] = args.input
        if args.svg_prompt:
            config_manager.config["files"]["svg_prompt"] = args.svg_prompt
        if args.xiaohongshu_prompt:
            config_manager.config["files"]["xiaohongshu_prompt"] = args.xiaohongshu_prompt
        
        # 批处理参数覆盖
        if args.batch_size:
            if "batch" not in config_manager.config:
                config_manager.config["batch"] = {}
            config_manager.config["batch"]["batch_size"] = args.batch_size
        
        if args.no_batching:
            if "batch" not in config_manager.config:
                config_manager.config["batch"] = {}
            config_manager.config["batch"]["enable_batching"] = False
        
        if args.progress_interval:
            if "batch" not in config_manager.config:
                config_manager.config["batch"] = {}
            config_manager.config["batch"]["progress_save_interval"] = args.progress_interval
        
        # 慢速模式配置
        if args.slow_mode:
            if "batch" not in config_manager.config:
                config_manager.config["batch"] = {}
            config_manager.config["batch"]["fast_mode"] = False
            config_manager.config["batch"]["api_call_buffer_time"] = 0.2
            config_manager.config["batch"]["batch_rest_time"] = 1.0
            logger.info("已启用慢速模式，增加API调用间隔")
        
        processor = TweetProcessor(args.config)

        # 处理重置进度选项
        if args.reset_progress:
            if processor.progress_file.exists():
                processor.progress_file.unlink()
                logger.info("进度记录已重置")

        # 确定开始索引
        start_index = args.start
        auto_continue = not args.no_auto_continue

        # 获取文件配置
        file_config = get_file_config()
        
        processor.process_dataset(
            json_file=file_config.input_json,
            start_index=start_index,
            max_count=args.count,
            auto_continue=auto_continue
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
