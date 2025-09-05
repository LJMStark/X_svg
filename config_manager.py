#!/usr/bin/env python3
"""
配置管理模块 - 统一管理应用配置
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class APIProviderConfig:
    """API提供商配置"""
    enabled: bool = True
    key: str = ""
    base_url: str = ""
    timeout: int = 180
    model: str = ""

@dataclass
class TaskConfig:
    """任务配置"""
    primary: Dict[str, str] = field(default_factory=dict)
    fallback: Dict[str, str] = field(default_factory=dict)
    fallback2: Dict[str, str] = field(default_factory=dict)
    fallback3: Dict[str, str] = field(default_factory=dict)

@dataclass
class RateLimitConfig:
    """速率限制配置"""
    openrouter_interval: float = 4.0
    gemini_interval: float = 2.0
    retry_attempts: int = 3
    retry_delay_seconds: int = 5

@dataclass
class FileConfig:
    """文件配置"""
    input_json: str = "twillot-public-post-sorted.json"
    svg_prompt: str = "svg提示词.txt"
    title_prompt: str = "小红书标题提示词.txt"
    xiaohongshu_prompt: str = "小红书文案提示词.txt"
    output_dir: str = "output"

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "batch_process.log"
    console: bool = True

@dataclass
class BatchConfig:
    """批处理配置"""
    batch_size: int = 5  # 小批量大小
    progress_save_interval: int = 5  # 每处理N个批次保存一次进度
    api_call_buffer_time: float = 0.1  # API调用缓冲时间（秒）
    batch_rest_time: float = 0.5  # 批次间休息时间（秒）
    enable_batching: bool = True  # 启用批处理模式
    fast_mode: bool = False  # 快速模式（更少等待）

class ConfigValidator:
    """配置验证器"""
    
    # 配置架构定义
    CONFIG_SCHEMA = {
        "api_providers": {
            "type": "dict",
            "required": True,
            "fields": {
                "openrouter": {"type": "dict", "required": True},
                "gemini": {"type": "dict", "required": True},
                "siliconflow": {"type": "dict", "required": True},
                "moonshot": {"type": "dict", "required": True},
                "novita": {"type": "dict", "required": True}
            }
        },
        "tasks": {
            "type": "dict",
            "required": True,
            "fields": {
                "title": {"type": "dict", "required": True},
                "body": {"type": "dict", "required": True},
                "svg": {"type": "dict", "required": True}
            }
        },
        "rate_limit": {
            "type": "dict",
            "required": True,
            "fields": {
                "openrouter_interval": {"type": "float", "required": True},
                "gemini_interval": {"type": "float", "required": True},
                "retry_attempts": {"type": "int", "required": True},
                "retry_delay_seconds": {"type": "int", "required": True}
            }
        },
        "files": {
            "type": "dict",
            "required": True,
            "fields": {
                "input_json": {"type": "str", "required": True},
                "svg_prompt": {"type": "str", "required": True},
                "title_prompt": {"type": "str", "required": True},
                "xiaohongshu_prompt": {"type": "str", "required": True},
                "output_dir": {"type": "str", "required": True}
            }
        },
        "logging": {
            "type": "dict",
            "required": True,
            "fields": {
                "level": {"type": "str", "required": True},
                "file": {"type": "str", "required": True},
                "console": {"type": "bool", "required": True}
            }
        },
        "batch": {
            "type": "dict",
            "required": False,
            "fields": {
                "batch_size": {"type": "int", "required": False},
                "progress_save_interval": {"type": "int", "required": False},
                "api_call_buffer_time": {"type": "float", "required": False},
                "batch_rest_time": {"type": "float", "required": False},
                "enable_batching": {"type": "bool", "required": False}
            }
        }
    }
    
    # API密钥格式验证
    API_KEY_PATTERNS = {
        "openrouter": r"^sk-or-v1-[a-zA-Z0-9]+$",
        "gemini": r"^sk-[a-zA-Z0-9]+$",
        "siliconflow": r"^sk-[a-zA-Z0-9]+$",
        "moonshot": r"^sk-[a-zA-Z0-9]+$",
        "novita": r"^sk_[a-zA-Z0-9]+$"
    }
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> List[str]:
        """验证配置文件格式"""
        errors = []
        
        def validate_section(section_name: str, section_schema: Dict, section_data: Dict):
            if section_schema.get("required", False) and section_name not in config:
                errors.append(f"缺少必需的配置节: {section_name}")
                return
            
            if section_name not in config:
                return
                
            section_value = config[section_name]
            
            # 验证类型
            expected_type = section_schema.get("type")
            if expected_type and not isinstance(section_value, eval(expected_type)):
                errors.append(f"配置节 {section_name} 类型错误，期望 {expected_type}")
                return
            
            # 验证字段
            fields = section_schema.get("fields", {})
            for field_name, field_schema in fields.items():
                if field_schema.get("required", False) and field_name not in section_value:
                    errors.append(f"缺少必需的配置字段: {section_name}.{field_name}")
                
                if field_name in section_value:
                    field_value = section_value[field_name]
                    expected_field_type = field_schema.get("type")
                    if expected_field_type and not isinstance(field_value, eval(expected_field_type)):
                        errors.append(f"配置字段 {section_name}.{field_name} 类型错误，期望 {expected_field_type}")
        
        # 验证所有配置节
        for section_name, section_schema in cls.CONFIG_SCHEMA.items():
            validate_section(section_name, section_schema, config.get(section_name, {}))
        
        return errors
    
    @classmethod
    def validate_api_keys(cls, config: Dict[str, Any]) -> List[str]:
        """验证API密钥格式"""
        errors = []
        api_providers = config.get("api_providers", {})
        
        for provider_name, pattern in cls.API_KEY_PATTERNS.items():
            if provider_name in api_providers:
                provider_config = api_providers[provider_name]
                if provider_config.get("enabled", True):
                    api_key = provider_config.get("key", "")
                    if not api_key:
                        errors.append(f"API提供商 {provider_name} 已启用但未设置密钥")
                    else:
                        import re
                        if not re.match(pattern, api_key):
                            errors.append(f"API提供商 {provider_name} 密钥格式不正确")
        
        return errors
    
    @classmethod
    def validate_files_exist(cls, config: Dict[str, Any]) -> List[str]:
        """验证必要文件是否存在"""
        errors = []
        files_config = config.get("files", {})
        
        required_files = [
            ("input_json", "输入JSON文件"),
            ("svg_prompt", "SVG提示词文件"),
            ("title_prompt", "标题提示词文件"),
            ("xiaohongshu_prompt", "小红书提示词文件")
        ]
        
        for file_key, file_desc in required_files:
            file_path = files_config.get(file_key, "")
            if not file_path:
                errors.append(f"未设置{file_desc}路径")
            elif not Path(file_path).exists():
                errors.append(f"{file_desc}不存在: {file_path}")
        
        return errors

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        try:
            # 加载配置文件
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"配置文件加载成功: {self.config_file}")
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {self.config_file}")
                self.config = self._get_default_config()
            
            # 应用环境变量覆盖
            self._apply_env_overrides()
            
            # 验证配置
            self._validate_config()
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api_providers": {
                "openrouter": {
                    "enabled": True,
                    "key": "",
                    "base_url": "https://openrouter.ai/api/v1",
                    "timeout": 180
                },
                "gemini": {
                    "enabled": False,
                    "key": "",
                    "base_url": "http://xai-studio.top:8000/openai/v1",
                    "timeout": 180
                },
                "siliconflow": {
                    "enabled": True,
                    "key": "",
                    "base_url": "https://api.siliconflow.cn/v1",
                    "timeout": 180
                },
                "moonshot": {
                    "enabled": True,
                    "key": "",
                    "base_url": "https://api.moonshot.cn/v1",
                    "timeout": 180
                },
                "novita": {
                    "enabled": True,
                    "key": "",
                    "base_url": "https://api.novita.ai/openai",
                    "timeout": 180
                }
            },
            "tasks": {
                "title": {
                    "primary": {
                        "provider": "siliconflow",
                        "model": "deepseek-ai/DeepSeek-V3.1"
                    },
                    "fallback": {
                        "provider": "moonshot",
                        "model": "kimi-k2-0711-preview"
                    }
                },
                "body": {
                    "primary": {
                        "provider": "novita",
                        "model": "deepseek/deepseek-v3.1"
                    },
                    "fallback": {
                        "provider": "moonshot",
                        "model": "kimi-k2-0711-preview"
                    }
                },
                "svg": {
                    "primary": {
                        "provider": "openrouter",
                        "model": "deepseek/deepseek-chat"
                    },
                    "fallback": {
                        "provider": "novita",
                        "model": "deepseek/deepseek-v3.1"
                    },
                    "fallback2": {
                        "provider": "siliconflow",
                        "model": "deepseek-ai/DeepSeek-V3.1"
                    },
                    "fallback3": {
                        "provider": "moonshot",
                        "model": "kimi-k2-0711-preview"
                    }
                }
            },
            "rate_limit": {
                "openrouter_interval": 4.0,
                "gemini_interval": 2.0,
                "retry_attempts": 3,
                "retry_delay_seconds": 5
            },
            "files": {
                "input_json": "twillot-public-post-sorted.json",
                "svg_prompt": "svg提示词.txt",
                "title_prompt": "小红书标题提示词.txt",
                "xiaohongshu_prompt": "小红书文案提示词.txt",
                "output_dir": "output"
            },
            "logging": {
                "level": "INFO",
                "file": "batch_process.log",
                "console": True
            },
            "batch": {
                "batch_size": 5,
                "progress_save_interval": 5,
                "api_call_buffer_time": 0.2,
                "batch_rest_time": 1.0,
                "enable_batching": True
            }
        }
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        env_mappings = {
            "OPENROUTER_API_KEY": ("api_providers", "openrouter", "key"),
            "GEMINI_API_KEY": ("api_providers", "gemini", "key"),
            "SILICONFLOW_API_KEY": ("api_providers", "siliconflow", "key"),
            "MOONSHOT_API_KEY": ("api_providers", "moonshot", "key"),
            "NOVITA_API_KEY": ("api_providers", "novita", "key"),
            "LOG_LEVEL": ("logging", "level"),
            "INPUT_JSON": ("files", "input_json"),
            "OUTPUT_DIR": ("files", "output_dir")
        }
        
        for env_var, (section, key, *_) in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                if section and key:
                    if section not in self.config:
                        self.config[section] = {}
                    # 确保目标位置是字典
                    if section == "api_providers" and key in ["openrouter", "gemini", "siliconflow", "moonshot", "novita"]:
                        if key not in self.config[section] or not isinstance(self.config[section][key], dict):
                            self.config[section][key] = {}
                        self.config[section][key]["key"] = value
                    else:
                        self.config[section][key] = value
                    logger.debug(f"环境变量覆盖: {section}.{key} = {value[:20]}...")
                elif not section and not key and len(_) > 0:
                    setattr(self, _[0], value)
                    logger.debug(f"环境变量覆盖: {_[0]} = {value}")
    
    def _validate_config(self):
        """验证配置"""
        errors = []
        
        # 验证配置结构
        errors.extend(ConfigValidator.validate_config(self.config))
        
        # 验证API密钥
        errors.extend(ConfigValidator.validate_api_keys(self.config))
        
        # 验证文件存在性
        errors.extend(ConfigValidator.validate_files_exist(self.config))
        
        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("配置验证通过")
    
    def get_api_provider_config(self, provider: str) -> APIProviderConfig:
        """获取API提供商配置"""
        provider_data = self.config.get("api_providers", {}).get(provider, {})
        return APIProviderConfig(**provider_data)
    
    def get_task_config(self, task: str) -> TaskConfig:
        """获取任务配置"""
        task_data = self.config.get("tasks", {}).get(task, {})
        return TaskConfig(**task_data)
    
    def get_rate_limit_config(self) -> RateLimitConfig:
        """获取速率限制配置"""
        rate_limit_data = self.config.get("rate_limit", {})
        return RateLimitConfig(**rate_limit_data)
    
    def get_file_config(self) -> FileConfig:
        """获取文件配置"""
        files_data = self.config.get("files", {})
        return FileConfig(**files_data)
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        logging_data = self.config.get("logging", {})
        return LoggingConfig(**logging_data)
    
    def get_batch_config(self) -> BatchConfig:
        """获取批处理配置"""
        batch_data = self.config.get("batch", {})
        return BatchConfig(**batch_data)
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config.copy()
    
    def reload(self):
        """重新加载配置"""
        logger.info("重新加载配置")
        self._load_config()
    
    def save_config(self, file_path: Optional[str] = None):
        """保存配置到文件"""
        if file_path is None:
            file_path = self.config_file
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置保存成功: {file_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
    
    def get_enabled_providers(self) -> List[str]:
        """获取已启用的API提供商列表"""
        providers = []
        api_providers = self.config.get("api_providers", {})
        
        for provider_name, provider_config in api_providers.items():
            if provider_config.get("enabled", True):
                providers.append(provider_name)
        
        return providers
    
    def get_provider_key(self, provider: str) -> Optional[str]:
        """获取API密钥（脱敏）"""
        provider_config = self.config.get("api_providers", {}).get(provider, {})
        if isinstance(provider_config, dict):
            key = provider_config.get("key", "")
        else:
            key = ""
        
        if key:
            # 脱敏显示
            return key[:8] + "*" * (len(key) - 12) + key[-4:] if len(key) > 12 else "*" * len(key)
        
        return None
    
    def __str__(self) -> str:
        """字符串表示"""
        enabled_providers = self.get_enabled_providers()
        return f"ConfigManager(file={self.config_file}, providers={enabled_providers})"

# 全局配置管理器实例
_config_manager = None

def get_config_manager(config_file: str = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    
    if _config_manager is None or (config_file and config_file != _config_manager.config_file):
        _config_manager = ConfigManager(config_file or "config.json")
    
    return _config_manager

def reload_config():
    """重新加载全局配置"""
    global _config_manager
    if _config_manager:
        _config_manager.reload()

# 便捷函数
def get_config() -> Dict[str, Any]:
    """获取完整配置"""
    return get_config_manager().get_config()

def get_api_provider_config(provider: str) -> APIProviderConfig:
    """获取API提供商配置"""
    return get_config_manager().get_api_provider_config(provider)

def get_task_config(task: str) -> TaskConfig:
    """获取任务配置"""
    return get_config_manager().get_task_config(task)

def get_rate_limit_config() -> RateLimitConfig:
    """获取速率限制配置"""
    return get_config_manager().get_rate_limit_config()

def get_file_config() -> FileConfig:
    """获取文件配置"""
    return get_config_manager().get_file_config()

def get_logging_config() -> LoggingConfig:
    """获取日志配置"""
    return get_config_manager().get_logging_config()

def get_batch_config() -> BatchConfig:
    """获取批处理配置"""
    return get_config_manager().get_batch_config()

if __name__ == "__main__":
    # 测试配置管理器
    try:
        config_manager = get_config_manager()
        print(f"配置管理器: {config_manager}")
        print(f"已启用的API提供商: {config_manager.get_enabled_providers()}")
        
        # 显示脱敏的API密钥
        for provider in config_manager.get_enabled_providers():
            key = config_manager.get_provider_key(provider)
            print(f"  {provider}: {key}")
        
    except Exception as e:
        print(f"配置管理器测试失败: {e}")