#!/usr/bin/env python3
"""模型交互日志分析工具

提供命令行工具分析可观测层生成的日志文件，包括：
- 调用链树形可视化
- 错误追踪
- 性能分析
- 统计报告
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional


class InteractionAnalyzer:
    """交互日志分析器"""
    
    def __init__(self, log_dir: Path):
        """
        初始化分析器
        
        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = log_dir
        self.interactions = []
        self._load_interactions()
    
    def _load_interactions(self):
        """加载所有交互记录"""
        if not self.log_dir.exists():
            print(f"❌ 日志目录不存在: {self.log_dir}")
            return
        
        # 查找所有 JSONL 文件
        jsonl_files = list(self.log_dir.glob("*.jsonl"))
        
        if not jsonl_files:
            print(f"⚠️  未找到日志文件: {self.log_dir}")
            return
        
        for jsonl_file in jsonl_files:
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            record = json.loads(line)
                            self.interactions.append(record)
            except Exception as e:
                print(f"⚠️  读取文件失败 {jsonl_file}: {e}")
        
        print(f"✓ 已加载 {len(self.interactions)} 条交互记录")
    
    def show_tree(self, task_id: Optional[str] = None, root_id: Optional[str] = None):
        """
        显示调用链树形结构
        
        Args:
            task_id: 任务ID（优先使用）
            root_id: 根交互ID
        """
        if not self.interactions:
            print("❌ 没有可用的交互记录")
            return
        
        # 筛选相关记录
        if task_id:
            records = [
                r for r in self.interactions 
                if r.get('business_context', {}).get('task_id') == task_id
            ]
            if not records:
                print(f"❌ 未找到任务ID为 {task_id} 的记录")
                return
            print(f"\n📋 任务: {task_id}")
        elif root_id:
            records = [
                r for r in self.interactions 
                if r.get('root_interaction_id') == root_id
            ]
            if not records:
                print(f"❌ 未找到根交互ID为 {root_id} 的记录")
                return
            print(f"\n🔗 调用链: {root_id[:8]}")
        else:
            # 显示所有根调用
            records = [r for r in self.interactions if r.get('call_depth', 0) == 0]
            print(f"\n📊 所有根调用 (共 {len(records)} 个)")
        
        # 按调用深度和时间排序
        records.sort(key=lambda x: (x.get('call_depth', 0), x.get('timestamp', '')))
        
        # 构建树形结构
        self._print_tree(records)
    
    def _print_tree(self, records: List[Dict]):
        """打印树形结构"""
        if not records:
            return
        
        # 按 parent_id 分组
        children_map = defaultdict(list)
        root_records = []
        
        for record in records:
            parent_id = record.get('parent_interaction_id')
            if parent_id:
                children_map[parent_id].append(record)
            else:
                root_records.append(record)
        
        # 打印树
        for root in root_records:
            self._print_node(root, children_map, prefix="", is_last=True)
    
    def _print_node(
        self, 
        record: Dict, 
        children_map: Dict, 
        prefix: str = "", 
        is_last: bool = True
    ):
        """递归打印节点"""
        # 状态图标
        status = record.get('response', {}).get('status', 'unknown')
        status_icon = {
            'success': '✅',
            'error': '❌',
            'timeout': '⏱️',
        }.get(status, '❓')
        
        # 延迟
        latency = record['performance']['latency_ms']
        latency_str = f"{latency:,}ms" if latency < 10000 else f"{latency/1000:.1f}s"
        
        # 方法名
        method = record.get('method_name', 'unknown')
        
        # 业务上下文
        ctx = record.get('business_context', {})
        phase = ctx.get('phase', '')
        phase_str = f" [{phase}]" if phase else ""
        
        # 打印当前节点
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{status_icon} {method}{phase_str} ({latency_str})")
        
        # 打印子节点
        interaction_id = record['interaction_id']
        children = children_map.get(interaction_id, [])
        
        if children:
            extension = "    " if is_last else "│   "
            for i, child in enumerate(children):
                is_child_last = (i == len(children) - 1)
                self._print_node(child, children_map, prefix + extension, is_child_last)
    
    def find_errors(self, task_id: Optional[str] = None):
        """
        查找所有错误
        
        Args:
            task_id: 可选的任务ID过滤
        """
        records = self.interactions
        
        if task_id:
            records = [
                r for r in records 
                if r.get('business_context', {}).get('task_id') == task_id
            ]
        
        errors = [
            r for r in records 
            if r.get('response', {}).get('status') in ['error', 'timeout']
        ]
        
        if not errors:
            print("✅ 未发现错误")
            return
        
        print(f"\n❌ 发现 {len(errors)} 个错误:\n")
        
        for i, error in enumerate(errors, 1):
            print(f"{i}. [{error['timestamp']}]")
            print(f"   模型: {error['provider']}/{error['model_name']}")
            print(f"   方法: {error['method_name']}")
            print(f"   状态: {error['response']['status']}")
            
            if 'error' in error:
                print(f"   类型: {error['error']['type']}")
                print(f"   消息: {error['error']['message']}")
            
            ctx = error.get('business_context', {})
            if ctx:
                print(f"   任务: {ctx.get('task_id', 'N/A')}")
            
            print()
    
    def show_stats(self, provider: Optional[str] = None):
        """
        显示统计信息
        
        Args:
            provider: 可选的提供商过滤
        """
        records = self.interactions
        
        if provider:
            records = [r for r in records if r.get('provider') == provider]
            print(f"\n📊 统计信息 (提供商: {provider})")
        else:
            print("\n📊 统计信息 (全部)")
        
        if not records:
            print("❌ 没有匹配的记录")
            return
        
        # 基础统计
        total = len(records)
        success = len([r for r in records if r.get('response', {}).get('status') == 'success'])
        error = len([r for r in records if r.get('response', {}).get('status') == 'error'])
        timeout = len([r for r in records if r.get('response', {}).get('status') == 'timeout'])
        
        print(f"\n总调用次数: {total}")
        print(f"  ✅ 成功: {success} ({success/total*100:.1f}%)")
        print(f"  ❌ 错误: {error} ({error/total*100:.1f}%)")
        print(f"  ⏱️  超时: {timeout} ({timeout/total*100:.1f}%)")
        
        # 延迟统计
        latencies = [r['performance']['latency_ms'] for r in records]
        if latencies:
            latencies.sort()
            avg = sum(latencies) / len(latencies)
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[int(len(latencies) * 0.95)]
            p99 = latencies[int(len(latencies) * 0.99)]
            
            print(f"\n延迟统计 (毫秒):")
            print(f"  平均: {avg:,.0f}")
            print(f"  P50: {p50:,}")
            print(f"  P95: {p95:,}")
            print(f"  P99: {p99:,}")
            print(f"  最大: {max(latencies):,}")
        
        # 按模型统计
        model_counts = defaultdict(int)
        for r in records:
            model = r.get('model_name', 'unknown')
            model_counts[model] += 1
        
        print(f"\n按模型统计:")
        for model, count in sorted(model_counts.items(), key=lambda x: -x[1]):
            print(f"  {model}: {count}")
        
        # 按任务类型统计
        task_type_counts = defaultdict(int)
        for r in records:
            task_type = r.get('business_context', {}).get('task_type', 'unknown')
            task_type_counts[task_type] += 1
        
        if any(t != 'unknown' for t in task_type_counts.keys()):
            print(f"\n按任务类型统计:")
            for task_type, count in sorted(task_type_counts.items(), key=lambda x: -x[1]):
                if task_type != 'unknown':
                    print(f"  {task_type}: {count}")
    
    def show_detail(self, interaction_id: str):
        """
        显示单个交互的详细信息
        
        Args:
            interaction_id: 交互ID（支持短ID）
        """
        # 查找匹配的记录（支持短ID）
        matches = [
            r for r in self.interactions 
            if r['interaction_id'].startswith(interaction_id)
        ]
        
        if not matches:
            print(f"❌ 未找到ID为 {interaction_id} 的记录")
            return
        
        if len(matches) > 1:
            print(f"⚠️  找到 {len(matches)} 个匹配的记录，显示第一个")
        
        record = matches[0]
        
        # 打印详细信息
        print("\n" + "━" * 80)
        print(f"🤖 交互详情: {record['interaction_id']}")
        print("━" * 80)
        
        print(f"\n📅 时间: {record['timestamp']}")
        print(f"🏢 提供商: {record['provider']}")
        print(f"🎯 模型: {record['model_name']}")
        print(f"⚙️  方法: {record['method_name']}")
        
        # 调用链信息
        if record.get('parent_interaction_id'):
            print(f"\n🔗 调用链:")
            print(f"  深度: {record['call_depth']}")
            print(f"  父节点: {record['parent_interaction_id'][:8]}")
            print(f"  根节点: {record['root_interaction_id'][:8]}")
        
        # 请求信息
        req = record['request']
        print(f"\n📤 请求:")
        print(f"  提示词长度: {req['prompt_length']:,} 字符")
        if req['params']:
            print(f"  参数:")
            for key, value in req['params'].items():
                print(f"    {key}: {value}")
        
        # 响应信息
        resp = record['response']
        print(f"\n📥 响应:")
        print(f"  内容长度: {resp['content_length']:,} 字符")
        print(f"  状态: {resp['status']}")
        
        # 性能指标
        perf = record['performance']
        print(f"\n📊 性能:")
        print(f"  延迟: {perf['latency_ms']:,} ms")
        if perf.get('retry_count', 0) > 0:
            print(f"  重试次数: {perf['retry_count']}")
        if perf.get('rate_limit_wait_ms', 0) > 0:
            print(f"  速率限制等待: {perf['rate_limit_wait_ms']:,} ms")
        
        # 错误信息
        if 'error' in record:
            print(f"\n❌ 错误:")
            print(f"  类型: {record['error']['type']}")
            print(f"  消息: {record['error']['message']}")
        
        # 业务上下文
        if record.get('business_context'):
            print(f"\n📋 业务上下文:")
            for key, value in record['business_context'].items():
                print(f"  {key}: {value}")
        
        print("\n" + "━" * 80 + "\n")
    
    def export_mermaid(self, task_id: Optional[str] = None, output_file: Optional[str] = None):
        """
        导出 Mermaid 图表
        
        Args:
            task_id: 任务ID
            output_file: 输出文件路径
        """
        if not task_id:
            print("❌ 导出 Mermaid 图表需要指定 task_id")
            return
        
        records = [
            r for r in self.interactions 
            if r.get('business_context', {}).get('task_id') == task_id
        ]
        
        if not records:
            print(f"❌ 未找到任务ID为 {task_id} 的记录")
            return
        
        # 生成 Mermaid 代码
        lines = ["graph TD"]
        
        # 按调用链组织
        for record in records:
            node_id = record['interaction_id'][:8]
            method = record['method_name']
            latency = record['performance']['latency_ms']
            status = record['response']['status']
            
            # 节点样式
            status_class = {
                'success': ':::success',
                'error': ':::error',
                'timeout': ':::timeout'
            }.get(status, '')
            
            label = f"{method}\\n{latency}ms"
            lines.append(f"    {node_id}[\"{label}\"]{status_class}")
            
            # 连接父节点
            parent_id = record.get('parent_interaction_id')
            if parent_id:
                parent_short = parent_id[:8]
                lines.append(f"    {parent_short} --> {node_id}")
        
        # 样式定义
        lines.extend([
            "",
            "    classDef success fill:#d4edda,stroke:#28a745",
            "    classDef error fill:#f8d7da,stroke:#dc3545",
            "    classDef timeout fill:#fff3cd,stroke:#ffc107"
        ])
        
        mermaid_code = "\n".join(lines)
        
        # 输出
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(mermaid_code)
            print(f"✓ Mermaid 图表已保存到: {output_file}")
        else:
            print("\n" + mermaid_code + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='模型交互日志分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 显示调用树
  python -m reinvent_insight.tools.analyze_model_interactions show-tree --task-id task_abc123
  
  # 查找错误
  python -m reinvent_insight.tools.analyze_model_interactions find-errors
  
  # 统计信息
  python -m reinvent_insight.tools.analyze_model_interactions stats --provider gemini
  
  # 查看详情
  python -m reinvent_insight.tools.analyze_model_interactions show-detail abc123
  
  # 导出图表
  python -m reinvent_insight.tools.analyze_model_interactions export --task-id task_abc123 --output diagram.mmd
        """
    )
    
    parser.add_argument(
        'command',
        choices=['show-tree', 'find-errors', 'stats', 'show-detail', 'export'],
        help='要执行的命令'
    )
    
    parser.add_argument(
        '--date',
        default=datetime.now().strftime('%Y-%m-%d'),
        help='日志日期 (默认: 今天)'
    )
    
    parser.add_argument(
        '--task-id',
        help='任务ID'
    )
    
    parser.add_argument(
        '--root-id',
        help='根交互ID'
    )
    
    parser.add_argument(
        '--interaction-id',
        help='交互ID（用于 show-detail）'
    )
    
    parser.add_argument(
        '--provider',
        choices=['gemini', 'dashscope'],
        help='模型提供商'
    )
    
    parser.add_argument(
        '--output',
        help='输出文件路径'
    )
    
    args = parser.parse_args()
    
    # 确定日志目录
    log_dir = Path(f"downloads/model_logs/{args.date}")
    
    # 创建分析器
    analyzer = InteractionAnalyzer(log_dir)
    
    # 执行命令
    if args.command == 'show-tree':
        analyzer.show_tree(task_id=args.task_id, root_id=args.root_id)
    
    elif args.command == 'find-errors':
        analyzer.find_errors(task_id=args.task_id)
    
    elif args.command == 'stats':
        analyzer.show_stats(provider=args.provider)
    
    elif args.command == 'show-detail':
        if not args.interaction_id:
            print("❌ show-detail 命令需要 --interaction-id 参数")
            sys.exit(1)
        analyzer.show_detail(args.interaction_id)
    
    elif args.command == 'export':
        analyzer.export_mermaid(task_id=args.task_id, output_file=args.output)


if __name__ == '__main__':
    main()
