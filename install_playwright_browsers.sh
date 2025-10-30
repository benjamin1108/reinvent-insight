#!/bin/bash

# Playwright 浏览器安装脚本
# 用于快速安装 Playwright Chromium 浏览器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查虚拟环境
if [ -d ".venv" ]; then
    PYTHON_BIN=".venv/bin/python"
    print_info "使用虚拟环境: .venv"
elif [ -d "venv" ]; then
    PYTHON_BIN="venv/bin/python"
    print_info "使用虚拟环境: venv"
else
    PYTHON_BIN="python3"
    print_warning "未找到虚拟环境，使用系统 Python"
fi

# 检查 Playwright 是否已安装
print_info "检查 Playwright 安装状态..."
if ! $PYTHON_BIN -c "import playwright" 2>/dev/null; then
    print_error "Playwright 未安装"
    print_info "请先安装 Playwright: pip install playwright"
    exit 1
fi

print_success "Playwright Python 包已安装"

# 检查磁盘空间
print_info "检查磁盘空间..."
AVAILABLE_SPACE=$(df -BM ~/.cache | tail -1 | awk '{print $4}' | sed 's/M//')
if [ "$AVAILABLE_SPACE" -lt 500 ]; then
    print_warning "可用磁盘空间不足 500MB，可能导致安装失败"
    echo -n "是否继续？(y/N): "
    read -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_info "安装已取消"
        exit 0
    fi
fi

# 安装浏览器
print_info "开始安装 Playwright Chromium 浏览器..."
print_info "这可能需要几分钟时间，请耐心等待..."

if $PYTHON_BIN -m playwright install chromium; then
    print_success "Playwright Chromium 浏览器安装成功"
else
    print_error "浏览器安装失败"
    exit 1
fi

# 验证安装
print_info "验证浏览器安装..."
if [ -d "$HOME/.cache/ms-playwright" ]; then
    BROWSER_COUNT=$(find "$HOME/.cache/ms-playwright" -name "chrome-linux" -o -name "headless_shell" 2>/dev/null | wc -l)
    if [ "$BROWSER_COUNT" -gt 0 ]; then
        print_success "浏览器文件已正确安装"
        print_info "浏览器位置: $HOME/.cache/ms-playwright"
        
        # 显示安装的浏览器
        echo ""
        echo "已安装的浏览器："
        ls -lh "$HOME/.cache/ms-playwright" | grep "^d"
    else
        print_warning "浏览器文件未找到，但安装命令成功"
    fi
else
    print_warning "Playwright 缓存目录不存在"
fi

# 测试浏览器启动
print_info "测试浏览器启动..."
if $PYTHON_BIN -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); browser = p.chromium.launch(headless=True); print('浏览器启动成功'); browser.close(); p.stop()" 2>/dev/null; then
    print_success "浏览器启动测试通过"
else
    print_warning "浏览器启动测试失败，但这可能是正常的"
    print_info "请尝试运行 Cookie Manager 服务进行实际测试"
fi

echo ""
print_success "安装完成！"
echo ""
echo "下一步："
echo "1. 测试 Cookie Manager: reinvent-insight cookie-manager health"
echo "2. 启动服务: reinvent-insight cookie-manager start"
echo "3. 查看状态: reinvent-insight cookie-manager status"
