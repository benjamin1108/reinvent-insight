#!/bin/bash

# reinvent-insight 部署清理脚本
# 使用方法: ./clean-deploy.sh [--all]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== reinvent-insight 部署清理脚本 ===${NC}"

# 检查参数
CLEAN_ALL=false
if [ "$1" = "--all" ]; then
    CLEAN_ALL=true
fi

# 停止服务
echo -e "${YELLOW}停止运行中的服务...${NC}"
if systemctl is-active --quiet reinvent-insight 2>/dev/null; then
    sudo systemctl stop reinvent-insight
    echo "已停止 systemd 服务"
fi

if pgrep -f "reinvent-insight web" > /dev/null; then
    pkill -f "reinvent-insight web"
    echo "已停止运行中的进程"
fi

# 清理构建文件
echo -e "${YELLOW}清理构建文件...${NC}"
rm -rf build/ dist/ *.egg-info src/*.egg-info
echo "已清理构建文件"

# 清理测试部署
if [ -d "dist/test-deploy" ]; then
    echo -e "${YELLOW}清理测试部署目录...${NC}"
    rm -rf dist/test-deploy
    echo "已清理测试部署"
fi

# 如果指定了 --all，还要清理生产部署
if [ "$CLEAN_ALL" = true ]; then
    PROD_DIR="$HOME/reinvent-insight-prod"
    if [ -d "$PROD_DIR" ]; then
        echo -e "${RED}警告：即将删除生产部署目录: $PROD_DIR${NC}"
        echo -n "确定要继续吗？(y/N): "
        read -r response
        if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
            # 先备份重要数据
            if [ -d "$PROD_DIR/reinvent_insight-0.1.0/downloads" ] || [ -f "$PROD_DIR/reinvent_insight-0.1.0/.env" ]; then
                BACKUP_DIR="${PROD_DIR}_final_backup_$(date +%Y%m%d_%H%M%S)"
                mkdir -p "$BACKUP_DIR"
                
                if [ -d "$PROD_DIR/reinvent_insight-0.1.0/downloads" ]; then
                    cp -r "$PROD_DIR/reinvent_insight-0.1.0/downloads" "$BACKUP_DIR/"
                fi
                
                if [ -f "$PROD_DIR/reinvent_insight-0.1.0/.env" ]; then
                    cp "$PROD_DIR/reinvent_insight-0.1.0/.env" "$BACKUP_DIR/"
                fi
                
                echo -e "${GREEN}已备份重要数据到: $BACKUP_DIR${NC}"
            fi
            
            rm -rf "$PROD_DIR"
            echo "已清理生产部署目录"
        else
            echo "已取消清理生产部署"
        fi
    fi
fi

echo -e "${GREEN}清理完成！${NC}" 