#!/bin/bash
#
# TTS 音频重新生成脚本（方法 3）
# 
# 使用方法：
#   ./regenerate_tts.sh "文件名.md"
#
# 功能：
#   1. 删除指定文件的音频缓存元数据
#   2. 手动触发 TTS 预生成任务
#   3. 实时显示生成进度
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
API_BASE="http://localhost:8002"
CACHE_DIR="downloads/tts_cache"
METADATA_FILE="${CACHE_DIR}/metadata.json"

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${RED}错误：请提供文件名${NC}"
    echo ""
    echo "使用方法："
    echo "  $0 \"文件名.md\""
    echo ""
    echo "示例："
    echo "  $0 \"AWS reInvent 2024 - Use generative AI to optimize cloud operations for Microsoft workloads (XNT312).md\""
    exit 1
fi

FILENAME="$1"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          TTS 音频重新生成工具（方法 3）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 步骤 1: 计算文章哈希
echo -e "${YELLOW}[步骤 1/4]${NC} 计算文章哈希..."
FILE_PATH="downloads/summaries/${FILENAME}"

if [ ! -f "${FILE_PATH}" ]; then
    echo -e "${RED}错误：文件不存在: ${FILE_PATH}${NC}"
    exit 1
fi

# 从文件中提取 video_url 和 title
VIDEO_URL=$(grep -oP '(?<=video_url: )[^\r\n]+' "${FILE_PATH}" | head -1 || echo "")
TITLE=$(grep -oP '(?<=title: )[^\r\n]+' "${FILE_PATH}" | head -1 || echo "")
UPLOAD_DATE=$(grep -oP '(?<=upload_date: )[^\r\n]+' "${FILE_PATH}" | head -1 || echo "")

if [ -z "${VIDEO_URL}" ] && [ -z "${TITLE}" ]; then
    echo -e "${RED}错误：无法从文件中提取元数据${NC}"
    exit 1
fi

# 计算哈希（与 Python 代码保持一致）
HASH_CONTENT="${VIDEO_URL}|${TITLE}|${UPLOAD_DATE}"
ARTICLE_HASH=$(echo -n "${HASH_CONTENT}" | sha256sum | cut -c1-16)

echo -e "${GREEN}✓${NC} 文章哈希: ${ARTICLE_HASH}"
echo ""

# 步骤 2: 查找并删除音频缓存元数据
echo -e "${YELLOW}[步骤 2/4]${NC} 删除音频缓存元数据..."

if [ ! -f "${METADATA_FILE}" ]; then
    echo -e "${YELLOW}⚠${NC}  元数据文件不存在，跳过删除"
else
    # 使用 jq 删除匹配的音频记录
    if command -v jq &> /dev/null; then
        # 备份元数据
        cp "${METADATA_FILE}" "${METADATA_FILE}.bak"
        
        # 删除匹配 article_hash 的记录
        jq "with_entries(select(.value.article_hash != \"${ARTICLE_HASH}\"))" "${METADATA_FILE}" > "${METADATA_FILE}.tmp"
        mv "${METADATA_FILE}.tmp" "${METADATA_FILE}"
        
        echo -e "${GREEN}✓${NC} 已删除音频缓存元数据（备份: ${METADATA_FILE}.bak）"
    else
        echo -e "${YELLOW}⚠${NC}  未安装 jq，请手动编辑 ${METADATA_FILE}"
        echo -e "    删除 article_hash 为 ${ARTICLE_HASH} 的记录"
    fi
fi
echo ""

# 步骤 3: 触发 TTS 预生成
echo -e "${YELLOW}[步骤 3/4]${NC} 触发 TTS 预生成任务..."

RESPONSE=$(curl -s -X POST "${API_BASE}/api/tts/pregenerate" \
    -H "Content-Type: application/json" \
    -d "{\"filename\": \"${FILENAME}\"}")

TASK_ID=$(echo "${RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_id', ''))" 2>/dev/null || echo "")
STATUS=$(echo "${RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")

if [ -z "${TASK_ID}" ]; then
    echo -e "${RED}✗${NC} 触发失败"
    echo "${RESPONSE}"
    exit 1
fi

echo -e "${GREEN}✓${NC} 任务已创建"
echo -e "    任务 ID: ${TASK_ID}"
echo -e "    状态: ${STATUS}"
echo ""

# 步骤 4: 监控任务进度
echo -e "${YELLOW}[步骤 4/4]${NC} 监控任务进度..."
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 循环检查任务状态
MAX_WAIT=1800  # 最多等待 30 分钟
WAIT_TIME=0
INTERVAL=5

while [ ${WAIT_TIME} -lt ${MAX_WAIT} ]; do
    # 获取任务详情
    TASK_INFO=$(curl -s "${API_BASE}/api/tts/queue/tasks?limit=1" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data['tasks']:
    task = data['tasks'][0]
    print(f\"{task['status']}|{task.get('error_message', '')}|{task.get('audio_hash', '')}\")
else:
    print('||')
" 2>/dev/null || echo "||")

    IFS='|' read -r TASK_STATUS ERROR_MSG AUDIO_HASH <<< "${TASK_INFO}"
    
    # 显示进度
    printf "\r${BLUE}⏱${NC}  等待时间: %3ds | 状态: %-12s" ${WAIT_TIME} "${TASK_STATUS}"
    
    # 检查是否完成
    if [ "${TASK_STATUS}" = "completed" ]; then
        echo ""
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}          ✓ TTS 音频生成成功！${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "音频哈希: ${AUDIO_HASH}"
        echo -e "音频 URL: ${API_BASE}/api/tts/cache/${AUDIO_HASH}"
        echo ""
        
        # 显示队列统计
        echo -e "${BLUE}队列统计：${NC}"
        curl -s "${API_BASE}/api/tts/queue/stats" | python3 -m json.tool
        
        exit 0
    elif [ "${TASK_STATUS}" = "failed" ]; then
        echo ""
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}          ✗ TTS 音频生成失败${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "错误信息: ${ERROR_MSG}"
        echo ""
        exit 1
    fi
    
    # 等待
    sleep ${INTERVAL}
    WAIT_TIME=$((WAIT_TIME + INTERVAL))
done

# 超时
echo ""
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}          ⚠ 等待超时${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "任务仍在进行中，请稍后手动检查"
echo "检查命令: curl ${API_BASE}/api/tts/queue/stats"
echo ""
