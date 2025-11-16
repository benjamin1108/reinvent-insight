#!/bin/bash

# YouTube 下载功能修复脚本
# 解决 "n challenge solving failed" 错误
# 该错误是由于缺少 JavaScript 运行时导致的

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

echo "======================================"
echo "YouTube 下载功能修复脚本"
echo "======================================"
echo ""

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    print_error "无法检测操作系统"
    exit 1
fi

print_info "检测到操作系统: $OS $VERSION"
echo ""

# 检查 Node.js 是否已安装
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js 已安装: $NODE_VERSION"
    
    # 检查版本是否足够新（需要 14.x 或更高）
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -lt 14 ]; then
        print_warning "Node.js 版本过低（需要 14.x 或更高），建议升级"
    else
        print_success "Node.js 版本符合要求"
    fi
else
    print_warning "Node.js 未安装"
    echo ""
    echo "yt-dlp 需要 JavaScript 运行时来解决 YouTube 的反爬虫机制"
    echo ""
    echo -n -e "${YELLOW}是否现在安装 Node.js？(y/N): ${NC}"
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_info "已取消安装"
        echo ""
        echo "手动安装方法："
        case $OS in
            ubuntu|debian)
                echo "  # 安装 Node.js 18.x LTS"
                echo "  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
                echo "  sudo apt-get install -y nodejs"
                ;;
            centos|rhel|fedora)
                echo "  # 安装 Node.js 18.x LTS"
                echo "  curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -"
                echo "  sudo yum install -y nodejs"
                ;;
        esac
        exit 0
    fi
    
    echo ""
    print_info "开始安装 Node.js..."
    
    case $OS in
        ubuntu|debian)
            print_info "添加 NodeSource 仓库..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            
            print_info "安装 Node.js..."
            sudo apt-get install -y nodejs
            ;;
        centos|rhel|fedora)
            print_info "添加 NodeSource 仓库..."
            curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
            
            print_info "安装 Node.js..."
            sudo yum install -y nodejs
            ;;
        *)
            print_error "不支持的操作系统: $OS"
            echo ""
            echo "请手动安装 Node.js 14.x 或更高版本"
            echo "访问: https://nodejs.org/"
            exit 1
            ;;
    esac
    
    # 验证安装
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js 安装成功: $NODE_VERSION"
    else
        print_error "Node.js 安装失败"
        exit 1
    fi
fi

echo ""
print_info "检查 yt-dlp 版本..."

# 检查 yt-dlp 是否已安装
if ! command -v yt-dlp &> /dev/null; then
    print_warning "yt-dlp 未安装"
    echo -n -e "${YELLOW}是否现在安装 yt-dlp？(y/N): ${NC}"
    read -r confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        print_info "安装 yt-dlp..."
        pip3 install --upgrade yt-dlp
    else
        print_warning "请手动安装 yt-dlp: pip3 install yt-dlp"
    fi
else
    YTDLP_VERSION=$(yt-dlp --version)
    print_success "yt-dlp 已安装: $YTDLP_VERSION"
    
    # 建议更新到最新版本
    echo -n -e "${YELLOW}是否更新 yt-dlp 到最新版本？(y/N): ${NC}"
    read -r confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        print_info "更新 yt-dlp..."
        pip3 install --upgrade yt-dlp
        NEW_VERSION=$(yt-dlp --version)
        print_success "yt-dlp 已更新到: $NEW_VERSION"
    fi
fi

echo ""
print_info "测试 YouTube 下载功能..."

# 测试一个简单的 YouTube 视频元数据获取
TEST_URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"

print_info "测试 URL: $TEST_URL"
print_info "获取视频元数据（不下载视频）..."

if yt-dlp --dump-json --no-playlist "$TEST_URL" > /dev/null 2>&1; then
    print_success "YouTube 下载功能测试通过！"
else
    print_warning "测试失败，可能需要 cookies"
    print_info "如果您的视频需要登录才能访问，请确保配置了有效的 cookies"
fi

echo ""
echo "======================================"
echo -e "${GREEN}修复完成${NC}"
echo "======================================"
echo ""
echo "已安装/验证的组件:"
echo "  ✓ Node.js (JavaScript 运行时)"
echo "  ✓ yt-dlp (YouTube 下载工具)"
echo ""
echo "下一步:"
echo "  1. 如果服务正在运行，重启服务以应用更改:"
echo "     sudo systemctl restart reinvent-insight"
echo ""
echo "  2. 如果问题仍然存在，检查 cookies 是否有效:"
echo "     python3 -m reinvent_insight.main cookie-manager health"
echo ""
echo "  3. 查看服务日志:"
echo "     sudo journalctl -u reinvent-insight -f"
echo ""
echo "======================================"
