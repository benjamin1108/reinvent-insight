#!/bin/bash

# 系统依赖安装脚本
# 用于安装 PDF 处理库、中文字体和 Playwright 浏览器依赖

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        print_error "无法检测操作系统"
        exit 1
    fi
    
    print_info "检测到操作系统: $OS $VERSION"
}

# Ubuntu/Debian 系统依赖安装
install_ubuntu_deps() {
    print_info "开始安装 Ubuntu/Debian 系统依赖..."
    
    # 更新包列表
    print_info "更新包列表..."
    sudo apt-get update -qq
    
    # Node.js (yt-dlp 需要 JavaScript 运行时)
    print_info "检查 Node.js..."
    if ! command -v node &> /dev/null; then
        print_info "安装 Node.js 18.x LTS..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
        print_success "Node.js 安装完成"
    else
        NODE_VERSION=$(node --version)
        print_info "Node.js 已安装: $NODE_VERSION"
    fi
    
    # PDF 处理相关依赖
    print_info "安装 PDF 处理库..."
    sudo apt-get install -y -qq \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        python3-cffi \
        python3-brotli \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libfribidi0
    
    print_success "PDF 处理库安装完成"
    
    # 中文字体支持
    print_info "安装中文字体..."
    sudo apt-get install -y -qq \
        fonts-noto-cjk \
        fonts-noto-cjk-extra \
        fonts-wqy-microhei \
        fonts-wqy-zenhei \
        fontconfig
    
    print_success "中文字体安装完成"
    
    # Playwright 浏览器依赖
    print_info "安装 Playwright 浏览器依赖..."
    sudo apt-get install -y -qq \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libatspi2.0-0 \
        libxshmfence1 \
        libx11-xcb1 \
        libxcb1
    
    print_success "Playwright 浏览器依赖安装完成"
}

# CentOS/RHEL/Fedora 系统依赖安装
install_centos_deps() {
    print_info "开始安装 CentOS/RHEL/Fedora 系统依赖..."
    
    # Node.js (yt-dlp 需要 JavaScript 运行时)
    print_info "检查 Node.js..."
    if ! command -v node &> /dev/null; then
        print_info "安装 Node.js 18.x LTS..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo yum install -y nodejs
        print_success "Node.js 安装完成"
    else
        NODE_VERSION=$(node --version)
        print_info "Node.js 已安装: $NODE_VERSION"
    fi
    
    # PDF 处理相关依赖
    print_info "安装 PDF 处理库..."
    sudo yum install -y -q \
        cairo \
        pango \
        gdk-pixbuf2 \
        libffi-devel \
        python3-cffi \
        harfbuzz \
        fribidi
    
    print_success "PDF 处理库安装完成"
    
    # 中文字体支持
    print_info "安装中文字体..."
    sudo yum install -y -q \
        google-noto-cjk-fonts \
        wqy-microhei-fonts \
        wqy-zenhei-fonts \
        fontconfig
    
    print_success "中文字体安装完成"
    
    # Playwright 浏览器依赖
    print_info "安装 Playwright 浏览器依赖..."
    sudo yum install -y -q \
        nss \
        nspr \
        atk \
        at-spi2-atk \
        cups-libs \
        libdrm \
        libxkbcommon \
        libXcomposite \
        libXdamage \
        libXfixes \
        libXrandr \
        mesa-libgbm \
        alsa-lib \
        libX11-xcb \
        libxcb
    
    print_success "Playwright 浏览器依赖安装完成"
}

# 验证字体安装
verify_fonts() {
    print_info "验证字体安装..."
    
    if ! command -v fc-list &> /dev/null; then
        print_warning "fc-list 命令不可用，无法验证字体"
        return
    fi
    
    # 刷新字体缓存
    print_info "刷新字体缓存..."
    sudo fc-cache -f -v > /dev/null 2>&1
    
    # 检查中文字体
    local noto_fonts=$(fc-list | grep -i "noto.*cjk" | wc -l)
    local wqy_fonts=$(fc-list | grep -i "wqy" | wc -l)
    
    # 验证 Node.js
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        print_success "Node.js: $node_version"
    else
        print_warning "Node.js: 未安装"
    fi
    
    echo ""
    echo "======================================"
    echo "字体安装验证"
    echo "======================================"
    
    if [ "$noto_fonts" -gt 0 ]; then
        print_success "Noto CJK 字体: $noto_fonts 个"
    else
        print_warning "Noto CJK 字体: 未找到"
    fi
    
    if [ "$wqy_fonts" -gt 0 ]; then
        print_success "WQY 字体: $wqy_fonts 个"
    else
        print_warning "WQY 字体: 未找到"
    fi
    
    # 显示一些可用的中文字体
    echo ""
    echo "可用的中文字体示例:"
    fc-list :lang=zh | head -5 | while read line; do
        echo "  - $(echo $line | cut -d: -f2 | cut -d, -f1)"
    done
    
    echo "======================================"
}

# 测试 PDF 生成
test_pdf_generation() {
    print_info "测试 PDF 生成功能..."
    
    # 创建测试 HTML
    cat > /tmp/test_pdf.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: "Noto Sans CJK SC", "WenQuanYi Micro Hei", sans-serif; }
    </style>
</head>
<body>
    <h1>PDF 生成测试</h1>
    <p>这是一个中文测试文档。</p>
    <p>This is an English test document.</p>
</body>
</html>
EOF

    # 尝试使用 weasyprint 生成 PDF
    if command -v weasyprint &> /dev/null; then
        if weasyprint /tmp/test_pdf.html /tmp/test_output.pdf 2>/dev/null; then
            print_success "PDF 生成测试成功"
            print_info "测试文件: /tmp/test_output.pdf"
        else
            print_warning "PDF 生成测试失败（可能需要安装 Python 依赖）"
        fi
    else
        print_info "weasyprint 未安装，跳过 PDF 生成测试"
        print_info "安装方法: pip install weasyprint"
    fi
    
    # 清理测试文件
    rm -f /tmp/test_pdf.html
}

# 显示安装总结
show_summary() {
    echo ""
    echo "======================================"
    echo -e "${GREEN}安装总结${NC}"
    echo "======================================"
    echo "已安装的组件:"
    echo "  ✓ Node.js (JavaScript 运行时，yt-dlp 需要)"
    echo "  ✓ PDF 处理库 (Cairo, Pango, etc.)"
    echo "  ✓ 中文字体 (Noto CJK, WQY)"
    echo "  ✓ Playwright 浏览器依赖"
    echo ""
    echo "下一步:"
    echo "  1. 安装 Python 依赖:"
    echo "     pip install weasyprint reportlab playwright yt-dlp"
    echo ""
    echo "  2. 安装 Playwright 浏览器:"
    echo "     playwright install chromium"
    echo ""
    echo "  3. 测试 YouTube 下载:"
    echo "     yt-dlp --dump-json --no-playlist 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"
    echo ""
    echo "  4. 测试 PDF 生成:"
    echo "     python -c 'from weasyprint import HTML; HTML(string=\"<h1>测试</h1>\").write_pdf(\"/tmp/test.pdf\")'"
    echo ""
    echo "======================================"
}

# 主流程
main() {
    echo "======================================"
    echo "系统依赖安装脚本"
    echo "======================================"
    echo ""
    
    # 检测操作系统
    detect_os
    
    echo ""
    echo "将要安装以下组件:"
    echo "  • PDF 处理库 (Cairo, Pango, GdkPixbuf)"
    echo "  • 中文字体 (Noto CJK, WQY)"
    echo "  • Playwright 浏览器依赖"
    echo ""
    echo -n -e "${YELLOW}是否继续？(y/N): ${NC}"
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_info "安装已取消"
        exit 0
    fi
    
    echo ""
    
    # 根据操作系统安装依赖
    case $OS in
        ubuntu|debian)
            install_ubuntu_deps
            ;;
        centos|rhel|fedora)
            install_centos_deps
            ;;
        *)
            print_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
    
    # 验证字体安装
    verify_fonts
    
    # 测试 PDF 生成
    test_pdf_generation
    
    # 显示安装总结
    show_summary
    
    print_success "系统依赖安装完成！"
}

# 运行主流程
main
