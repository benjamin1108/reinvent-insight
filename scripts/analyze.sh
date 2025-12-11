#!/bin/bash
# 模型交互分析工具快速启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 默认使用今天的日志
DATE=${DATE:-$(date +%Y-%m-%d)}

# 显示帮助
if [ "$1" == "-h" ] || [ "$1" == "--help" ] || [ -z "$1" ]; then
    echo "模型交互分析工具"
    echo ""
    echo "用法: ./scripts/analyze.sh <命令> [选项]"
    echo ""
    echo "命令:"
    echo "  tree      显示调用链树形结构"
    echo "  errors    查找错误"
    echo "  stats     统计信息"
    echo "  detail    查看详细信息"
    echo "  export    导出 Mermaid 图表"
    echo ""
    echo "示例:"
    echo "  ./scripts/analyze.sh tree --task-id task_abc123"
    echo "  ./scripts/analyze.sh errors"
    echo "  ./scripts/analyze.sh stats --provider gemini"
    echo "  ./scripts/analyze.sh detail --interaction-id abc123"
    echo "  ./scripts/analyze.sh export --task-id task_abc123 --output diagram.mmd"
    echo ""
    echo "环境变量:"
    echo "  DATE=2025-12-10  指定日志日期（默认今天）"
    exit 0
fi

# 转换命令别名
case "$1" in
    tree)
        CMD="show-tree"
        ;;
    errors)
        CMD="find-errors"
        ;;
    stats)
        CMD="stats"
        ;;
    detail)
        CMD="show-detail"
        ;;
    export)
        CMD="export"
        ;;
    *)
        CMD="$1"
        ;;
esac

shift

# 执行
python -m reinvent_insight.tools.analyze_model_interactions "$CMD" --date "$DATE" "$@"
