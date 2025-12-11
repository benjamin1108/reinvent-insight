"""日志格式化器 - 生成人类可读和JSONL格式"""

import json
from typing import Dict, Any
from datetime import datetime

from .models import InteractionRecord


class LogFormatter:
    """日志格式化器"""
    
    @staticmethod
    def format_human_readable(record: InteractionRecord) -> str:
        """
        生成人类可读的格式
        
        Args:
            record: 交互记录
            
        Returns:
            格式化的字符串
        """
        lines = []
        
        # 分隔线
        lines.append("━" * 80)
        lines.append(f"🤖 模型交互记录 #{record.interaction_id[:8]}")
        lines.append("━" * 80)
        lines.append("")
        
        # 基础信息
        timestamp = record.timestamp
        lines.append(f"📅 时间: {timestamp}")
        
        # 调用链信息
        if record.parent_interaction_id:
            lines.append(f"🔗 调用链: 根节点 {record.root_interaction_id[:8]} (深度: {record.call_depth})")
        
        lines.append(f"🏢 提供商: {record.provider}")
        lines.append(f"🎯 模型: {record.model_name}")
        lines.append(f"⚙️  方法: {record.method_name}")
        lines.append("")
        
        # 请求参数
        if record.request_params:
            lines.append("┌─ 请求参数 " + "─" * 62)
            for key, value in record.request_params.items():
                lines.append(f"│ {key}: {value}")
            lines.append("└" + "─" * 79)
            lines.append("")
        
        # 提示词
        lines.append(f"┌─ 提示词 (长度: {record.prompt_length:,} 字符，预览前 {len(record.prompt_preview)}) " + "─" * 30)
        lines.append(f"│ {record.prompt_preview[:200]}...")
        if record.prompt_length > len(record.prompt_preview):
            lines.append("│ [内容已截断]")
        lines.append("└" + "─" * 79)
        lines.append("")
        
        # 响应内容
        if record.response_preview:
            lines.append(f"┌─ 响应内容 (长度: {record.response_length:,} 字符，预览前 {len(record.response_preview)}) " + "─" * 25)
            # 只显示前几行
            preview_lines = record.response_preview[:300].split('\n')[:5]
            for line in preview_lines:
                lines.append(f"│ {line}")
            if record.response_length > len(record.response_preview):
                lines.append("│ [内容已截断]")
            lines.append("└" + "─" * 79)
            lines.append("")
        
        # 业务上下文
        if record.business_context:
            lines.append("┌─ 业务上下文 " + "─" * 64)
            for key, value in record.business_context.items():
                emoji = "📋" if "task" in key else "👤" if "user" in key else "🏷️"
                lines.append(f"│ {emoji} {key}: {value}")
            lines.append("└" + "─" * 79)
            lines.append("")
        
        # 性能指标
        lines.append("📊 性能指标:")
        lines.append(f"  • 响应延迟: {record.latency_ms:,} ms")
        if record.retry_count > 0:
            lines.append(f"  • 重试次数: {record.retry_count}")
        if record.rate_limit_wait_ms > 0:
            lines.append(f"  • 速率限制等待: {record.rate_limit_wait_ms:,} ms")
        
        # 状态
        status_emoji = "✅" if record.status == "success" else "❌" if record.status == "error" else "⏱️"
        lines.append(f"  • 状态: {status_emoji} {record.status.upper()}")
        
        # 错误信息
        if record.error_message:
            lines.append("")
            lines.append("❌ 错误信息:")
            lines.append(f"  • 类型: {record.error_type}")
            lines.append(f"  • 消息: {record.error_message}")
        
        lines.append("")
        lines.append("━" * 80)
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_jsonl(record: InteractionRecord) -> str:
        """
        生成JSONL格式（单行JSON）
        
        Args:
            record: 交互记录
            
        Returns:
            JSON字符串
        """
        data = {
            "interaction_id": record.interaction_id,
            "parent_interaction_id": record.parent_interaction_id,
            "root_interaction_id": record.root_interaction_id,
            "call_depth": record.call_depth,
            "timestamp": record.timestamp,
            "provider": record.provider,
            "model_name": record.model_name,
            "method_name": record.method_name,
            "request": {
                "prompt_length": record.prompt_length,
                "prompt_preview": record.prompt_preview,
                "params": record.request_params
            },
            "response": {
                "content_length": record.response_length,
                "content_preview": record.response_preview,
                "status": record.status
            },
            "performance": {
                "latency_ms": record.latency_ms,
                "retry_count": record.retry_count,
                "rate_limit_wait_ms": record.rate_limit_wait_ms
            }
        }
        
        # 添加错误信息
        if record.error_message:
            data["error"] = {
                "type": record.error_type,
                "message": record.error_message
            }
        
        # 添加元数据
        if record.metadata:
            data["metadata"] = record.metadata
        
        # 添加业务上下文
        if record.business_context:
            data["business_context"] = record.business_context
        
        return json.dumps(data, ensure_ascii=False)
    
    @staticmethod
    def format_simple(record: InteractionRecord) -> str:
        """
        生成简化格式（单行摘要）
        
        Args:
            record: 交互记录
            
        Returns:
            简化字符串
        """
        status_emoji = "✅" if record.status == "success" else "❌"
        return (
            f"{status_emoji} [{record.timestamp}] "
            f"{record.provider}/{record.model_name} "
            f"{record.method_name} - "
            f"{record.latency_ms}ms - "
            f"prompt:{record.prompt_length} response:{record.response_length}"
        )
