"""上下文管理 - 使用 contextvars 实现线程安全的上下文传递"""

import contextvars
from typing import Optional, Dict, Any
from contextlib import contextmanager


# 业务上下文变量
_business_context: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    'business_context', 
    default=None
)

# 交互上下文变量（用于调用链追踪）
_interaction_context: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    'interaction_context',
    default=None
)


def get_business_context() -> Optional[Dict[str, Any]]:
    """
    获取当前的业务上下文
    
    Returns:
        业务上下文字典，如果未设置则返回 None
    """
    return _business_context.get()


def get_current_interaction_context() -> Optional[Dict[str, Any]]:
    """
    获取当前的交互上下文（用于调用链追踪）
    
    Returns:
        交互上下文字典，如果未设置则返回 None
    """
    return _interaction_context.get()


def set_interaction_context(interaction_id: str, root_interaction_id: str, call_depth: int) -> contextvars.Token:
    """
    设置交互上下文（内部使用）
    
    Args:
        interaction_id: 当前交互ID
        root_interaction_id: 根交互ID
        call_depth: 调用深度
        
    Returns:
        上下文令牌，用于后续重置
    """
    ctx = {
        "interaction_id": interaction_id,
        "root_interaction_id": root_interaction_id,
        "call_depth": call_depth
    }
    return _interaction_context.set(ctx)


def reset_interaction_context(token: contextvars.Token) -> None:
    """
    重置交互上下文（内部使用）
    
    Args:
        token: 之前设置时返回的令牌
    """
    _interaction_context.reset(token)


@contextmanager
def set_business_context(**kwargs):
    """
    设置业务上下文的上下文管理器
    
    用法:
        with set_business_context(task_id="abc", task_type="video_summary"):
            # 在这个作用域内的所有模型调用都会关联这个上下文
            result = await client.generate_content(prompt)
    
    Args:
        **kwargs: 业务上下文的键值对
    """
    token = _business_context.set(kwargs)
    try:
        yield
    finally:
        _business_context.reset(token)


def track_with_context(**context_defaults):
    """
    装饰器：自动设置业务上下文
    
    用法:
        @track_with_context(task_type="video_summary")
        async def process_video(task_id, video_url):
            # 自动设置 task_id 和 task_type
            ...
    
    Args:
        **context_defaults: 默认的上下文值
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 尝试从函数参数中提取 task_id
            context = context_defaults.copy()
            
            # 如果第一个参数名为 task_id，自动添加到上下文
            if args and hasattr(func, '__code__'):
                arg_names = func.__code__.co_varnames
                if len(arg_names) > 0 and arg_names[0] == 'task_id':
                    context['task_id'] = args[0]
            
            # 或者从 kwargs 中提取
            if 'task_id' in kwargs:
                context['task_id'] = kwargs['task_id']
            
            with set_business_context(**context):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator
