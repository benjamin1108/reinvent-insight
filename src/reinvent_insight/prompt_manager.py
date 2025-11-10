# -*- coding: utf-8 -*-
"""
Prompt 管理器模块

提供统一的 prompt 加载、缓存和格式化功能，实现单一数据源原则。
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger

logger = logger.bind(name=__name__)


# ============================================
# 异常类定义
# ============================================

class PromptError(Exception):
    """Prompt 相关错误的基类"""
    pass


class PromptNotFoundError(PromptError):
    """Prompt 不存在"""
    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Prompt '{key}' not found in configuration")


class PromptLoadError(PromptError):
    """Prompt 加载失败"""
    def __init__(self, key: str, file_path: str, reason: str):
        self.key = key
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Failed to load prompt '{key}' from '{file_path}': {reason}")


class MissingParameterError(PromptError):
    """缺少必需参数"""
    def __init__(self, key: str, missing_params: List[str]):
        self.key = key
        self.missing_params = missing_params
        params_str = ", ".join(missing_params)
        super().__init__(f"Missing required parameters for prompt '{key}': {params_str}")


class PromptValidationError(PromptError):
    """Prompt 验证失败"""
    pass


class CircularIncludeError(PromptError):
    """循环包含错误"""
    def __init__(self, chain: List[str]):
        self.chain = chain
        chain_str = " -> ".join(chain)
        super().__init__(f"Circular include detected: {chain_str}")


# ============================================
# 数据类定义
# ============================================

@dataclass
class PromptConfig:
    """Prompt 配置数据类"""
    key: str                                    # prompt 唯一标识符
    type: str                                   # prompt 类型: base, template, fragment
    file: str                                   # 文件路径（相对于 base_dir）
    description: str = ""                       # 描述信息
    version: str = "1.0"                        # 版本号
    required_params: List[str] = field(default_factory=list)  # 必需参数列表
    optional_params: Dict[str, str] = field(default_factory=dict)  # 可选参数及默认值
    includes: List[str] = field(default_factory=list)  # 包含的其他 prompt 片段
    
    def validate(self) -> List[str]:
        """
        验证配置的完整性
        
        Returns:
            错误信息列表，如果为空则表示验证通过
        """
        errors = []
        
        if not self.key:
            errors.append("Prompt key cannot be empty")
        
        if self.type not in ['base', 'template', 'fragment']:
            errors.append(f"Invalid prompt type '{self.type}', must be one of: base, template, fragment")
        
        if not self.file:
            errors.append(f"Prompt '{self.key}' missing file path")
        
        return errors


# ============================================
# PromptManager 核心类
# ============================================

class PromptManager:
    """
    Prompt 管理器，负责加载、缓存和提供 prompt
    
    Features:
    - 从 YAML 配置文件加载 prompt 定义
    - 缓存 prompt 内容以提高性能
    - 支持 prompt 片段组合
    - 支持模板参数替换
    - 支持热重载（开发模式）
    """
    
    def __init__(self, config_path: str = "./prompt/config.yaml", enable_hot_reload: bool = False):
        """
        初始化 Prompt Manager
        
        Args:
            config_path: 配置文件路径
            enable_hot_reload: 是否启用热重载（开发模式）
        """
        self.config_path = Path(config_path)
        self.enable_hot_reload = enable_hot_reload
        self.base_dir: Optional[Path] = None
        self.config_version: str = "unknown"
        
        # 缓存
        self._configs: Dict[str, PromptConfig] = {}  # key -> PromptConfig
        self._content_cache: Dict[str, str] = {}     # key -> prompt content
        self._file_mtimes: Dict[str, float] = {}     # file_path -> modification time
        
        # 加载配置
        self.load_prompts()
        
        logger.info(f"PromptManager initialized with config: {self.config_path}")
        logger.info(f"Hot reload: {'enabled' if enable_hot_reload else 'disabled'}")
        logger.info(f"Loaded {len(self._configs)} prompt configurations")
    
    def load_prompts(self) -> None:
        """加载所有 prompt 配置和内容"""
        try:
            # 读取配置文件
            if not self.config_path.exists():
                raise PromptLoadError("config", str(self.config_path), "Config file not found")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 提取基础配置
            self.config_version = config_data.get('version', 'unknown')
            base_dir_str = config_data.get('base_dir', './prompt')
            self.base_dir = Path(base_dir_str)
            
            # 如果 base_dir 是相对路径，相对于配置文件所在目录
            if not self.base_dir.is_absolute():
                # 配置文件在 prompt/ 目录下，base_dir 也指向 prompt/，所以直接使用配置文件所在目录
                self.base_dir = self.config_path.parent
            
            # 解析 prompt 配置
            prompts_data = config_data.get('prompts', {})
            self._configs.clear()
            
            for key, prompt_data in prompts_data.items():
                config = PromptConfig(
                    key=key,
                    type=prompt_data.get('type', 'base'),
                    file=prompt_data.get('file', ''),
                    description=prompt_data.get('description', ''),
                    version=prompt_data.get('version', '1.0'),
                    required_params=prompt_data.get('required_params', []),
                    optional_params=prompt_data.get('optional_params', {}),
                    includes=prompt_data.get('includes', [])
                )
                
                # 验证配置
                errors = config.validate()
                if errors:
                    logger.error(f"Invalid configuration for prompt '{key}': {', '.join(errors)}")
                    continue
                
                self._configs[key] = config
            
            # 清空内容缓存，强制重新加载
            self._content_cache.clear()
            self._file_mtimes.clear()
            
            logger.info(f"Loaded {len(self._configs)} prompt configurations (version: {self.config_version})")
            
        except yaml.YAMLError as e:
            raise PromptLoadError("config", str(self.config_path), f"YAML parse error: {e}")
        except Exception as e:
            raise PromptLoadError("config", str(self.config_path), str(e))
    
    def _read_file(self, file_path: Path) -> str:
        """
        读取文件内容，支持缓存和热重载
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容
        """
        file_path_str = str(file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        # 如果启用热重载，检查文件是否被修改
        if self.enable_hot_reload:
            current_mtime = file_path.stat().st_mtime
            cached_mtime = self._file_mtimes.get(file_path_str)
            
            if cached_mtime is None or current_mtime > cached_mtime:
                # 文件被修改或首次读取，重新加载
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._file_mtimes[file_path_str] = current_mtime
                return content
        
        # 使用缓存（生产模式或文件未修改）
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self._file_mtimes[file_path_str] = file_path.stat().st_mtime
        return content
    
    def get_prompt(self, key: str, raw: bool = False) -> str:
        """
        获取 prompt 内容
        
        Args:
            key: prompt 标识符
            raw: 是否返回原始内容（不进行片段组合）
            
        Returns:
            prompt 内容字符串
            
        Raises:
            PromptNotFoundError: prompt 不存在
            PromptLoadError: prompt 加载失败
        """
        # 检查 prompt 是否存在
        if key not in self._configs:
            raise PromptNotFoundError(key)
        
        # 如果已缓存且不需要热重载，直接返回
        if not self.enable_hot_reload and key in self._content_cache:
            return self._content_cache[key]
        
        config = self._configs[key]
        
        try:
            # 构建完整文件路径
            file_path = self.base_dir / config.file
            
            # 读取文件内容
            content = self._read_file(file_path)
            
            # 如果不是 raw 模式，解析 {{include:key}} 语法
            if not raw:
                content = self._resolve_includes(content, visited=[key])
            
            # 缓存内容
            self._content_cache[key] = content
            
            return content
            
        except FileNotFoundError as e:
            raise PromptLoadError(key, config.file, str(e))
        except Exception as e:
            raise PromptLoadError(key, config.file, str(e))
    
    def _process_includes(self, content: str, includes: List[str], visited: List[str]) -> str:
        """
        处理 prompt 中的 includes（预处理阶段）
        
        这个方法处理配置文件中定义的 includes，而不是内容中的 {{include:key}} 语法
        
        Args:
            content: prompt 内容
            includes: 要包含的 prompt keys
            visited: 已访问的 prompt keys（用于检测循环）
            
        Returns:
            处理后的内容
        """
        # 这里暂时不做处理，includes 的处理将在 _resolve_includes 中统一完成
        # 这个方法保留用于未来可能的预处理需求
        return content
    
    def _resolve_includes(self, content: str, visited: Optional[List[str]] = None) -> str:
        """
        解析并替换内容中的 {{include:key}} 语法
        
        Args:
            content: 包含 {{include:key}} 语法的内容
            visited: 已访问的 prompt keys（用于检测循环）
            
        Returns:
            解析后的内容
            
        Raises:
            CircularIncludeError: 检测到循环引用
            PromptNotFoundError: 引用的 prompt 不存在
        """
        if visited is None:
            visited = []
        
        # 匹配 {{include:key}} 模式
        include_pattern = r'\{\{include:(\w+)\}\}'
        
        def replace_include(match):
            include_key = match.group(1)
            
            # 检测循环引用
            if include_key in visited:
                raise CircularIncludeError(visited + [include_key])
            
            # 获取被包含的 prompt 内容
            included_content = self.get_prompt(include_key, raw=True)
            
            # 递归解析被包含内容中的 includes
            return self._resolve_includes(included_content, visited + [include_key])
        
        # 替换所有 {{include:key}}
        resolved_content = re.sub(include_pattern, replace_include, content)
        
        return resolved_content
    
    def format_prompt(self, key: str, **params) -> str:
        """
        格式化 prompt 模板，替换占位符
        
        Args:
            key: prompt 标识符
            **params: 模板参数
            
        Returns:
            格式化后的 prompt 字符串
            
        Raises:
            PromptNotFoundError: prompt 不存在
            MissingParameterError: 缺少必需参数
        """
        # 获取配置
        if key not in self._configs:
            raise PromptNotFoundError(key)
        
        config = self._configs[key]
        
        # 检查必需参数
        missing_params = []
        for required_param in config.required_params:
            if required_param not in params:
                missing_params.append(required_param)
        
        if missing_params:
            raise MissingParameterError(key, missing_params)
        
        # 合并可选参数的默认值
        all_params = dict(config.optional_params)
        all_params.update(params)
        
        # 获取 prompt 内容
        content = self.get_prompt(key)
        
        # 处理条件包含 {{if:param}}...{{endif}}
        content = self._process_conditional_includes(content, all_params)
        
        # 替换参数占位符 {param}
        try:
            formatted_content = content.format(**all_params)
        except KeyError as e:
            # 如果有未提供的参数，给出更友好的错误信息
            missing_param = str(e).strip("'")
            raise MissingParameterError(key, [missing_param])
        
        return formatted_content
    
    def _process_conditional_includes(self, content: str, params: Dict[str, Any]) -> str:
        """
        处理条件包含 {{if:param}}...{{endif}} 语法
        
        Args:
            content: 包含条件语法的内容
            params: 参数字典
            
        Returns:
            处理后的内容
        """
        # 匹配 {{if:param}}...{{endif}} 模式
        conditional_pattern = r'\{\{if:(\w+)\}\}(.*?)\{\{endif\}\}'
        
        def replace_conditional(match):
            param_name = match.group(1)
            conditional_content = match.group(2)
            
            # 检查参数是否存在且为真值
            param_value = params.get(param_name)
            if param_value:
                return conditional_content
            else:
                return ""
        
        # 替换所有条件包含
        processed_content = re.sub(conditional_pattern, replace_conditional, content, flags=re.DOTALL)
        
        return processed_content
    
    def reload_prompts(self) -> None:
        """
        重新加载所有 prompt（用于热重载）
        
        此方法会：
        1. 重新读取配置文件
        2. 清空所有缓存
        3. 如果重载失败，保留旧的缓存内容（降级策略）
        
        Note:
            - 在开发模式下，文件修改会自动检测（通过 _read_file 中的 mtime 检查）
            - 此方法用于手动触发完整重载，包括配置文件本身
        """
        try:
            logger.info("Reloading prompts...")
            old_configs = self._configs.copy()
            old_cache = self._content_cache.copy()
            
            self.load_prompts()
            logger.info("Prompts reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload prompts: {e}")
            logger.warning("Continuing with cached prompts (degraded mode)")
            # 恢复旧的配置和缓存（降级策略）
            self._configs = old_configs
            self._content_cache = old_cache
    
    def list_prompts(self) -> List[PromptConfig]:
        """列出所有可用的 prompt 配置"""
        return list(self._configs.values())
    
    def validate_prompts(self) -> Dict[str, List[str]]:
        """
        验证所有 prompt 的完整性
        
        Returns:
            验证结果字典，包含错误和警告信息
            {
                'errors': ['error1', 'error2', ...],
                'warnings': ['warning1', 'warning2', ...]
            }
        """
        result = {
            'errors': [],
            'warnings': []
        }
        
        # 验证每个 prompt 配置
        for key, config in self._configs.items():
            # 验证配置本身
            config_errors = config.validate()
            if config_errors:
                result['errors'].extend([f"[{key}] {err}" for err in config_errors])
            
            # 验证文件是否存在
            file_path = self.base_dir / config.file
            if not file_path.exists():
                result['errors'].append(f"[{key}] File not found: {config.file}")
            
            # 验证 includes 引用
            for include_key in config.includes:
                if include_key not in self._configs:
                    result['errors'].append(f"[{key}] Invalid include reference: {include_key}")
        
        # 检查循环引用
        for key in self._configs.keys():
            try:
                self._check_circular_includes(key, [])
            except CircularIncludeError as e:
                result['errors'].append(str(e))
        
        return result
    
    def _check_circular_includes(self, key: str, visited: List[str]) -> None:
        """
        检查循环引用
        
        Args:
            key: 当前检查的 prompt key
            visited: 已访问的 prompt keys
            
        Raises:
            CircularIncludeError: 检测到循环引用
        """
        if key in visited:
            visited.append(key)
            raise CircularIncludeError(visited)
        
        if key not in self._configs:
            return
        
        config = self._configs[key]
        new_visited = visited + [key]
        
        for include_key in config.includes:
            self._check_circular_includes(include_key, new_visited)


# ============================================
# 全局实例
# ============================================

_global_manager: Optional[PromptManager] = None


def get_prompt_manager(config_path: str = "./prompt/config.yaml", 
                       enable_hot_reload: bool = False) -> PromptManager:
    """
    获取全局 PromptManager 实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        enable_hot_reload: 是否启用热重载
        
    Returns:
        PromptManager 实例
    """
    global _global_manager
    
    if _global_manager is None:
        _global_manager = PromptManager(config_path, enable_hot_reload)
    
    return _global_manager
