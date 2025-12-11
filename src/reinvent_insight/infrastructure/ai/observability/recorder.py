"""交互记录器"""

import time
from datetime import datetime
from typing import Optional, Dict, Any

from .models import InteractionRecord
from .context import get_current_interaction_context, get_business_context


class InteractionRecorder:
    """捕获单次交互的完整生命周期"""
    
    def __init__(self):
        self.record: Optional[InteractionRecord] = None
        self._start_time: Optional[float] = None
        self._rate_limit_start: Optional[float] = None
    
    def start_recording(
        self,
        provider: str,
        model_name: str,
        method_name: str
    ) -> None:
        """
        开始记录交互
        
        Args:
            provider: 模型提供商（gemini / dashscope）
            model_name: 模型名称
            method_name: 调用的方法名
        """
        self._start_time = time.time()
        
        # 从上下文中获取父调用信息
        parent_ctx = get_current_interaction_context()
        
        # 创建记录
        self.record = InteractionRecord(
            provider=provider,
            model_name=model_name,
            method_name=method_name,
            timestamp=datetime.now().isoformat()
        )
        
        # 设置调用链信息
        if parent_ctx:
            self.record.parent_interaction_id = parent_ctx.get("interaction_id")
            self.record.root_interaction_id = parent_ctx.get("root_interaction_id")
            self.record.call_depth = parent_ctx.get("call_depth", 0) + 1
        else:
            # 根调用
            self.record.parent_interaction_id = None
            self.record.root_interaction_id = self.record.interaction_id
            self.record.call_depth = 0
        
        # 尝试获取业务上下文
        business_ctx = get_business_context()
        if business_ctx:
            self.record.business_context = business_ctx.copy()
    
    def record_request(
        self,
        prompt: str,
        params: Dict[str, Any]
    ) -> None:
        """
        记录请求信息
        
        Args:
            prompt: 提示词
            params: 请求参数
        """
        if self.record is None:
            return
        
        # 记录提示词
        self.record.prompt_length = len(prompt)
        self.record.prompt_preview = prompt
        
        # 记录请求参数（去除API Key等敏感信息）
        self.record.request_params = params.copy()
    
    def record_response(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录响应信息
        
        Args:
            content: 响应内容
            metadata: 额外的元数据
        """
        if self.record is None:
            return
        
        # 记录响应内容
        self.record.response_length = len(content)
        self.record.response_preview = content
        
        # 记录性能指标
        if self._start_time:
            self.record.latency_ms = int((time.time() - self._start_time) * 1000)
        
        # 设置状态为成功
        self.record.status = "success"
        
        # 记录元数据
        if metadata:
            self.record.metadata.update(metadata)
    
    def record_error(
        self,
        exception: Exception
    ) -> None:
        """
        记录错误信息
        
        Args:
            exception: 异常对象
        """
        if self.record is None:
            return
        
        # 记录错误信息
        self.record.error_type = type(exception).__name__
        self.record.error_message = str(exception)
        
        # 设置状态
        if "timeout" in str(exception).lower():
            self.record.status = "timeout"
        else:
            self.record.status = "error"
        
        # 记录延迟
        if self._start_time:
            self.record.latency_ms = int((time.time() - self._start_time) * 1000)
    
    def record_retry(self) -> None:
        """记录重试"""
        if self.record is None:
            return
        
        self.record.retry_count += 1
    
    def record_rate_limit_start(self) -> None:
        """记录速率限制等待开始"""
        self._rate_limit_start = time.time()
    
    def record_rate_limit_end(self) -> None:
        """记录速率限制等待结束"""
        if self._rate_limit_start and self.record:
            wait_time = int((time.time() - self._rate_limit_start) * 1000)
            self.record.rate_limit_wait_ms += wait_time
            self._rate_limit_start = None
    
    def finalize(
        self,
        max_prompt_length: int = 2000,
        max_response_length: int = 5000,
        mask_sensitive: bool = True
    ) -> Optional[InteractionRecord]:
        """
        完成记录并返回数据对象
        
        Args:
            max_prompt_length: 提示词最大预览长度
            max_response_length: 响应最大预览长度
            mask_sensitive: 是否脱敏敏感信息
            
        Returns:
            交互记录对象
        """
        if self.record is None:
            return None
        
        # 截断内容
        self.record.truncate_content(max_prompt_length, max_response_length)
        
        # 脱敏敏感信息
        if mask_sensitive:
            self.record.mask_sensitive_data()
        
        return self.record
