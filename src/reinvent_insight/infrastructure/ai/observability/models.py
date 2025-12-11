"""可观测层数据模型"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class InteractionRecord:
    """模型交互记录数据类"""
    
    # 调用链标识
    interaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_interaction_id: Optional[str] = None
    root_interaction_id: Optional[str] = None
    call_depth: int = 0
    
    # 基础信息
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    provider: str = ""
    model_name: str = ""
    method_name: str = ""
    
    # 请求信息
    request_params: Dict[str, Any] = field(default_factory=dict)
    prompt_preview: str = ""
    prompt_length: int = 0
    
    # 响应信息
    response_preview: str = ""
    response_length: int = 0
    status: str = "pending"  # success / error / timeout
    
    # 性能指标
    latency_ms: int = 0
    retry_count: int = 0
    rate_limit_wait_ms: int = 0
    
    # 错误信息（可选）
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    business_context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """初始化后验证"""
        # 验证 status
        valid_statuses = ["pending", "success", "error", "timeout"]
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
        
        # 如果是根调用，设置 root_interaction_id
        if self.parent_interaction_id is None and self.root_interaction_id is None:
            self.root_interaction_id = self.interaction_id
            self.call_depth = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractionRecord':
        """从字典创建实例"""
        return cls(**data)
    
    def truncate_content(self, max_prompt_length: int = 2000, max_response_length: int = 5000):
        """截断过长的内容"""
        if self.prompt_length > max_prompt_length:
            self.prompt_preview = self.prompt_preview[:max_prompt_length]
        
        if self.response_length > max_response_length:
            self.response_preview = self.response_preview[:max_response_length]
    
    def mask_sensitive_data(self):
        """脱敏敏感信息"""
        # 脱敏 API Key
        if "api_key" in self.request_params:
            api_key = self.request_params["api_key"]
            if isinstance(api_key, str) and len(api_key) > 8:
                self.request_params["api_key"] = f"{api_key[:4]}****{api_key[-4:]}"
        
        # 脱敏业务上下文中的用户信息
        if self.business_context:
            if "user_id" in self.business_context:
                user_id = self.business_context["user_id"]
                if isinstance(user_id, str) and len(user_id) > 4:
                    self.business_context["user_id"] = f"{user_id[:4]}****{user_id[-2:]}"


def validate_interaction_id(interaction_id: str) -> bool:
    """验证交互ID是否为有效的UUID格式"""
    try:
        uuid.UUID(interaction_id)
        return True
    except (ValueError, AttributeError):
        return False
