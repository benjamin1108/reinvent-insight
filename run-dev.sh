#!/bin/bash

# reinvent-insight 开发环境启动脚本
# 使用方法: ./run-dev.sh [选项]
# 选项:
#   --port PORT  指定端口号（默认：8001）
#   --host HOST  指定主机地址（默认：127.0.0.1）
#   --reload     启用热重载（默认启用）
#   --no-reload  禁用热重载

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
PORT=8002
HOST="0.0.0.0"
RELOAD=true
PROJECT_NAME="reinvent-insight"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --reload)
      RELOAD=true
      shift
      ;;
    --no-reload)
      RELOAD=false
      shift
      ;;
    *)
      echo -e "${RED}未知参数: $1${NC}"
      echo "使用方法: $0 [--port PORT] [--host HOST] [--reload|--no-reload]"
      exit 1
      ;;
  esac
done

# 打印带颜色的信息
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

# 检查是否在项目根目录
check_project_root() {
    if [ ! -f "pyproject.toml" ] || [ ! -d "src/reinvent_insight" ]; then
        print_error "请在项目根目录下运行此脚本"
        exit 1
    fi
}

# 检查并创建虚拟环境
setup_venv() {
    if [ ! -d ".venv" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv .venv
        print_success "虚拟环境创建完成"
    fi
    
    print_info "激活虚拟环境..."
    source .venv/bin/activate
}

# 安装依赖
install_dependencies() {
    print_info "检查并安装依赖..."
    
    # 确保 pip 是最新版本
    python -m pip install --upgrade pip -q
    
    # 安装项目依赖（开发模式）
    if pip install -e . -q; then
        print_success "依赖安装完成"
    else
        print_error "依赖安装失败"
        exit 1
    fi
}

# 检查环境配置
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在"
        
        # 如果存在 .env.example，提示复制
        if [ -f ".env.example" ]; then
            print_info "发现 .env.example 文件"
            echo -n -e "${YELLOW}是否从 .env.example 创建 .env 文件？(y/N): ${NC}"
            read -r create_env
            
            if [[ "$create_env" =~ ^[Yy]$ ]]; then
                cp .env.example .env
                print_success "已创建 .env 文件，请编辑配置"
                echo -e "${YELLOW}提示：使用 nano .env 或 vim .env 编辑配置文件${NC}"
            fi
        else
            print_info "创建示例 .env 文件..."
            cat > .env << EOF
GEMINI_API_KEY=your-gemini-api-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
EOF
            print_success "已创建示例 .env 文件"
            print_warning "请编辑 .env 文件，填入正确的 API 密钥和密码"
        fi
    else
        # 检查是否是示例配置
        if grep -q "your-gemini-api-key-here" .env 2>/dev/null; then
            print_warning ".env 文件包含示例配置，请确保已填入真实的 API 密钥"
        else
            print_success ".env 文件已配置"
        fi
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    mkdir -p downloads/subtitles downloads/summaries downloads/pdfs logs
    print_success "目录创建完成"
}

# 启动开发服务器
start_dev_server() {
    echo ""
    echo "======================================"
    echo -e "${BLUE}开发服务器配置${NC}"
    echo "======================================"
    echo "• 项目名称: $PROJECT_NAME"
    echo "• 服务地址: http://$HOST:$PORT"
    echo "• 热重载: $([ "$RELOAD" = true ] && echo "启用" || echo "禁用")"
    echo "• 工作目录: $(pwd)"
    echo "======================================"
    echo ""
    
    print_info "启动开发服务器..."
    
    # 构建启动命令
    if [ "$RELOAD" = true ]; then
        print_info "热重载已启用，代码修改将自动重启服务器"
        # 使用 uvicorn 的 reload 功能
        ENVIRONMENT=development ENV=dev exec python -m uvicorn reinvent_insight.api.app:app \
            --host "$HOST" \
            --port "$PORT" \
            --reload \
            --reload-dir src \
            --reload-dir web
    else
        # 不使用 reload
        ENVIRONMENT=development ENV=dev exec python -m uvicorn reinvent_insight.api.app:app \
            --host "$HOST" \
            --port "$PORT"
    fi
}

# 主函数
main() {
    print_info "启动 $PROJECT_NAME 开发环境..."
    
    # 检查项目根目录
    check_project_root
    
    # 设置虚拟环境
    setup_venv
    
    # 安装依赖
    install_dependencies
    
    # 检查环境配置
    check_env
    
    # 创建必要的目录
    create_directories
    
    # 启动开发服务器
    start_dev_server
}

# 运行主函数
main 