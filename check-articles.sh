#!/bin/bash

# 检查开发环境和生产环境的文章数量

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== reinvent-insight 文章统计 ===${NC}"
echo

# 开发环境
DEV_DIR="$HOME/reinvent-insight/downloads/summaries"
if [ -d "$DEV_DIR" ]; then
    DEV_COUNT=$(find "$DEV_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
    echo -e "${YELLOW}开发环境:${NC}"
    echo "  目录: $DEV_DIR"
    echo -e "  文章数: ${GREEN}$DEV_COUNT${NC}"
    
    # 显示最新的3篇文章
    if [ "$DEV_COUNT" -gt 0 ]; then
        echo "  最新文章:"
        find "$DEV_DIR" -name "*.md" -type f -printf "%T@ %p\n" 2>/dev/null | \
            sort -rn | head -3 | while read -r timestamp file; do
            basename "$file" | sed 's/^/    - /'
        done
    fi
else
    echo -e "${YELLOW}开发环境:${NC} 目录不存在"
fi

echo

# 生产环境
PROD_DIR="$HOME/reinvent-insight-prod/reinvent_insight-0.1.0/downloads/summaries"
if [ -d "$PROD_DIR" ]; then
    PROD_COUNT=$(find "$PROD_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
    echo -e "${YELLOW}生产环境:${NC}"
    echo "  目录: $PROD_DIR"
    echo -e "  文章数: ${GREEN}$PROD_COUNT${NC}"
    
    # 显示最新的3篇文章
    if [ "$PROD_COUNT" -gt 0 ]; then
        echo "  最新文章:"
        find "$PROD_DIR" -name "*.md" -type f -printf "%T@ %p\n" 2>/dev/null | \
            sort -rn | head -3 | while read -r timestamp file; do
            basename "$file" | sed 's/^/    - /'
        done
    fi
else
    echo -e "${YELLOW}生产环境:${NC} 目录不存在（尚未部署）"
fi

echo
echo -e "${BLUE}=====================================${NC}"

# 如果两个环境都存在，显示差异和增量分析
if [ -d "$DEV_DIR" ] && [ -d "$PROD_DIR" ]; then
    DIFF=$((DEV_COUNT - PROD_COUNT))
    
    # 分析增量文章
    NEW_ARTICLES=0
    if [ "$DEV_COUNT" -gt 0 ] && [ "$PROD_COUNT" -gt 0 ]; then
        echo -e "${BLUE}增量分析:${NC}"
        
        # 检查开发环境有而生产环境没有的文章
        while IFS= read -r -d '' dev_file; do
            filename=$(basename "$dev_file")
            if [ ! -f "$PROD_DIR/$filename" ]; then
                if [ "$NEW_ARTICLES" -eq 0 ]; then
                    echo "  开发环境独有的文章:"
                fi
                echo "    + $filename"
                NEW_ARTICLES=$((NEW_ARTICLES + 1))
            fi
        done < <(find "$DEV_DIR" -name "*.md" -type f -print0 2>/dev/null)
        
        if [ "$NEW_ARTICLES" -eq 0 ]; then
            echo "  没有发现开发环境独有的文章"
        fi
        echo
    fi
    
    # 部署建议
    if [ "$DIFF" -gt 0 ]; then
        echo -e "${YELLOW}部署建议:${NC}"
                 if [ "$NEW_ARTICLES" -gt 0 ]; then
             echo -e "  开发环境有 ${GREEN}$NEW_ARTICLES${NC} 篇新文章可以增量复制"
             echo "  运行 ./redeploy.sh 将增量复制这些新文章"
        else
            echo "  开发环境文章更多，但可能是同名文件的不同版本"
            echo "  增量复制策略将跳过同名文件"
        fi
    elif [ "$DIFF" -eq 0 ]; then
        if [ "$NEW_ARTICLES" -eq 0 ]; then
            echo -e "${GREEN}✓ 两个环境的文章完全一致${NC}"
        else
            echo -e "${YELLOW}注意:${NC} 文章数量相同，但内容可能不同"
        fi
    else
        echo -e "${YELLOW}增量复制策略:${NC}"
        echo "  生产环境文章更多，将跳过从开发环境复制"
        echo "  当前不会进行任何文章复制"
    fi
fi 