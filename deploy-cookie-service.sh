#!/bin/bash

# reinvent-insight Cookie Manager 服务部署脚本
# 使用方法: ./deploy-cookie-service.sh [选项]
# 选项:
#   --skip-cookie-import  跳过初始cookie导入
#   --cookie-file PATH    从指定文件导入cookies
#   --dry-run            显示将要执行的操作但不实际执行

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
COOKIE_SERVICE_NAME="reinvent-insight-cookies"
COOKIE_STORE_PATH="$HOME/.cookies.json"
NETSCAPE_COOKIE_PATH="$HOME/.cookies"
VENV_NAME=".venv-cookie-service"
DEPLOY_DIR="$HOME/cookie-service"
SKIP_COOKIE_IMPORT=false
COOKIE_FILE=""
DRY_RUN=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-cookie-import)
      SKIP_COOKIE_IMPORT=true
      shift
      ;;
    --cookie-file)
      COOKIE_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo -e "${RED}未知参数: $1${NC}"
      echo "使用方法: $0 [--skip-cookie-import] [--cookie-file PATH] [--dry-run]"
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

# 检查依赖
check_dependencies() {
    print_info "检查系统依赖..."
    
    local deps_ok=true
    
    # 检查 Python 3.8+
    if ! command -v python3 &> /dev/null; then
        print_error "未找到 Python 3"
        deps_ok=false
    else
        local python_version=$(python3 --version | awk '{print $2}')
        print_info "✓ Python 版本: $python_version"
    fi
    
    # 检查 pip
    if ! python3 -m pip --version &> /dev/null; then
        print_error "未找到 pip"
        deps_ok=false
    else
        print_info "✓ pip 已安装"
    fi
    
    if [ "$deps_ok" = false ]; then
        print_error "缺少必要的依赖，请先安装 Python 3.8+ 和 pip"
        return 1
    fi
    
    return 0
}

# 检查并安装 Python 依赖
check_and_install_dependencies() {
    print_info "检查 Python 依赖..."
    
    # 检查 reinvent-insight 包是否已安装
    if ! python3 -c "import reinvent_insight" 2>/dev/null; then
        print_warning "reinvent-insight 包未安装"
        
        if [ "$DRY_RUN" = true ]; then
            print_info "演练模式：将安装 reinvent-insight 包"
            return 0
        fi
        
        echo -n -e "${YELLOW}是否现在安装？(y/N): ${NC}"
        read -r confirm
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            print_info "安装 reinvent-insight..."
            pip install -e .
        else
            print_error "reinvent-insight 是必需的依赖"
            return 1
        fi
    else
        print_info "✓ reinvent-insight 已安装"
    fi
    
    # 检查 Playwright
    if ! python3 -c "import playwright" 2>/dev/null; then
        print_warning "Playwright 未安装"
        
        if [ "$DRY_RUN" = true ]; then
            print_info "演练模式：将安装 Playwright"
            return 0
        fi
        
        echo -n -e "${YELLOW}是否现在安装？(y/N): ${NC}"
        read -r confirm
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            print_info "安装 Playwright..."
            pip install playwright
            python3 -m playwright install chromium
            print_success "Playwright 安装完成"
        else
            print_error "Playwright 是必需的依赖"
            return 1
        fi
    else
        print_info "✓ Playwright 已安装"
        
        # 检查浏览器是否已安装
        if ! python3 -m playwright install --dry-run chromium 2>&1 | grep -q "is already installed"; then
            print_info "安装 Playwright Chromium 浏览器..."
            if [ "$DRY_RUN" = false ]; then
                python3 -m playwright install chromium
            fi
        else
            print_info "✓ Playwright Chromium 浏览器已安装"
        fi
    fi
    
    return 0
}

# 验证 cookie 格式
validate_cookie_format() {
    local cookie_file=$1
    
    # 检查文件是否为空
    if [ ! -s "$cookie_file" ]; then
        print_error "Cookie 文件为空"
        return 1
    fi
    
    # 检查是否包含 YouTube 域名
    if ! grep -q "youtube.com" "$cookie_file"; then
        print_warning "未找到 YouTube 域名的 cookies"
        echo -n -e "${YELLOW}是否继续？(y/N): ${NC}"
        read -r confirm
        [[ "$confirm" =~ ^[Yy]$ ]] || return 1
    fi
    
    print_success "Cookie 格式验证通过"
    return 0
}

# 使用编辑器导入 cookies
import_with_editor() {
    local editor=$1
    
    # 创建临时文件
    local temp_file=$(mktemp /tmp/cookie_import_XXXXXX.txt)
    
    print_info "打开 $editor 编辑器..."
    print_info "请粘贴您的 cookies 内容，保存并退出"
    echo ""
    echo "提示："
    echo "  1. 从浏览器扩展（如 'Get cookies.txt LOCALLY'）导出 cookies"
    echo "  2. 复制所有内容"
    echo "  3. 粘贴到编辑器中"
    echo "  4. 保存并退出"
    echo ""
    echo -n "按 Enter 继续..."
    read
    
    # 打开编辑器
    $editor "$temp_file"
    
    # 验证格式
    if validate_cookie_format "$temp_file"; then
        # 使用 reinvent-insight CLI 导入
        print_info "导入 cookies..."
        if python3 -m reinvent_insight.main cookie-manager import-cookies "$temp_file"; then
            print_success "Cookies 导入成功"
            rm -f "$temp_file"
            return 0
        else
            print_error "Cookies 导入失败"
            rm -f "$temp_file"
            return 1
        fi
    else
        print_error "Cookie 格式验证失败"
        rm -f "$temp_file"
        return 1
    fi
}

# 从文件导入 cookies
import_from_file() {
    local cookie_file=$1
    
    # 验证文件存在
    if [ ! -f "$cookie_file" ]; then
        print_error "文件不存在: $cookie_file"
        return 1
    fi
    
    # 验证格式
    if ! validate_cookie_format "$cookie_file"; then
        return 1
    fi
    
    # 使用 reinvent-insight CLI 导入
    print_info "导入 cookies..."
    if python3 -m reinvent_insight.main cookie-manager import-cookies "$cookie_file"; then
        print_success "Cookies 导入成功"
        return 0
    else
        print_error "Cookies 导入失败"
        return 1
    fi
}

# 交互式导入 cookies
interactive_cookie_import() {
    print_info "Cookie 导入向导"
    echo ""
    echo "请选择导入方式："
    echo "  1) 使用 nano 编辑器输入"
    echo "  2) 使用 vim 编辑器输入"
    echo "  3) 从文件导入"
    echo "  4) 跳过（稍后手动导入）"
    echo ""
    echo -n "请选择 (1-4): "
    read -r choice
    
    case $choice in
        1)
            if command -v nano &> /dev/null; then
                import_with_editor "nano"
                return $?
            else
                print_error "nano 编辑器未安装"
                return 1
            fi
            ;;
        2)
            if command -v vim &> /dev/null; then
                import_with_editor "vim"
                return $?
            else
                print_error "vim 编辑器未安装"
                return 1
            fi
            ;;
        3)
            echo -n "请输入 cookie 文件路径: "
            read -r file_path
            import_from_file "$file_path"
            return $?
            ;;
        4)
            print_info "跳过 cookie 导入"
            print_warning "请稍后使用以下命令手动导入："
            print_warning "  python3 -m reinvent_insight.main cookie-manager import-cookies <cookies.txt>"
            return 0
            ;;
        *)
            print_error "无效选择"
            return 1
            ;;
    esac
}

# 部署 Cookie 服务
deploy_cookie_service() {
    print_info "开始部署 Cookie Manager 服务..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "演练模式：将创建 systemd 服务"
        return 0
    fi
    
    # 创建 systemd 服务文件
    local service_file="/tmp/${COOKIE_SERVICE_NAME}.service"
    
    print_info "创建 systemd 服务配置..."
    cat > "$service_file" << EOF
[Unit]
Description=reinvent-insight Cookie Manager Service
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$HOME
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="ENVIRONMENT=production"
ExecStart=$(which python3) -m reinvent_insight.main cookie-manager start --daemon
Restart=always
RestartSec=10
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 复制到 systemd 目录
    print_info "安装 systemd 服务..."
    sudo cp "$service_file" "/etc/systemd/system/${COOKIE_SERVICE_NAME}.service"
    
    # 重新加载 systemd
    sudo systemctl daemon-reload
    
    # 启用服务
    sudo systemctl enable "$COOKIE_SERVICE_NAME"
    
    print_success "Cookie Manager 服务部署完成"
    return 0
}

# 停止现有服务
stop_cookie_service() {
    print_info "检查现有服务..."
    
    if systemctl is-active --quiet "$COOKIE_SERVICE_NAME" 2>/dev/null; then
        print_info "停止现有服务..."
        
        if [ "$DRY_RUN" = false ]; then
            sudo systemctl stop "$COOKIE_SERVICE_NAME"
            sleep 2
        fi
        
        print_success "服务已停止"
    else
        print_info "服务未运行"
    fi
    
    return 0
}

# 启动服务
start_cookie_service() {
    print_info "启动 Cookie Manager 服务..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "演练模式：将启动服务"
        return 0
    fi
    
    # 启动服务
    sudo systemctl start "$COOKIE_SERVICE_NAME"
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    if systemctl is-active --quiet "$COOKIE_SERVICE_NAME"; then
        print_success "Cookie Manager 服务已成功启动"
        
        # 检查 cookies 是否存在
        if [ -f "$NETSCAPE_COOKIE_PATH" ] || [ -f "$COOKIE_STORE_PATH" ]; then
            print_info "✓ Cookies 已配置"
        else
            print_warning "⚠ 未检测到 cookies，请导入 cookies"
        fi
        
        return 0
    else
        print_error "Cookie Manager 服务启动失败"
        print_info "查看日志: sudo journalctl -u $COOKIE_SERVICE_NAME -n 20"
        
        # 显示最近的错误
        echo ""
        echo "最近的错误日志："
        sudo journalctl -u "$COOKIE_SERVICE_NAME" -n 10 --no-pager | grep -E "(ERROR|CRITICAL|Failed)" || echo "没有发现明显错误"
        
        return 1
    fi
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "======================================"
    echo -e "${GREEN}Cookie Manager 服务部署完成${NC}"
    echo "======================================"
    echo ""
    echo "服务信息:"
    echo "  • 服务名称: $COOKIE_SERVICE_NAME"
    
    if systemctl is-active --quiet "$COOKIE_SERVICE_NAME" 2>/dev/null; then
        echo "  • 服务状态: ✓ 运行中"
    else
        echo "  • 服务状态: ✗ 未运行"
    fi
    
    echo ""
    echo "Cookie 存储位置:"
    echo "  • JSON 格式: $COOKIE_STORE_PATH"
    echo "  • Netscape 格式: $NETSCAPE_COOKIE_PATH"
    
    # 检查 cookies 是否存在
    if [ -f "$NETSCAPE_COOKIE_PATH" ] || [ -f "$COOKIE_STORE_PATH" ]; then
        echo "  • 状态: ✓ 已配置"
    else
        echo "  • 状态: ⚠ 需要导入"
    fi
    
    echo ""
    echo "常用命令:"
    echo "  查看状态:"
    echo "    sudo systemctl status $COOKIE_SERVICE_NAME"
    echo "    python3 -m reinvent_insight.main cookie-manager status"
    echo ""
    echo "  查看日志:"
    echo "    sudo journalctl -u $COOKIE_SERVICE_NAME -f"
    echo ""
    echo "  服务管理:"
    echo "    sudo systemctl start $COOKIE_SERVICE_NAME"
    echo "    sudo systemctl stop $COOKIE_SERVICE_NAME"
    echo "    sudo systemctl restart $COOKIE_SERVICE_NAME"
    echo ""
    echo "  Cookie 管理:"
    echo "    python3 -m reinvent_insight.main cookie-manager import-cookies <file>"
    echo "    python3 -m reinvent_insight.main cookie-manager refresh"
    echo "    python3 -m reinvent_insight.main cookie-manager health"
    echo ""
    echo "======================================"
}

# 主流程
main() {
    if [ "$DRY_RUN" = true ]; then
        print_warning "演练模式：只显示将要执行的操作，不会实际执行"
        echo ""
    fi
    
    print_info "Cookie Manager 服务部署脚本"
    print_info "Cookie 存储位置: $COOKIE_STORE_PATH"
    print_info "Netscape 格式: $NETSCAPE_COOKIE_PATH"
    echo ""
    
    # 检查依赖
    check_dependencies || exit 1
    check_and_install_dependencies || exit 1
    
    echo ""
    print_success "环境检查完成"
    echo ""
    
    # 处理 Cookie 导入
    if [ "$SKIP_COOKIE_IMPORT" = false ]; then
        # 检查是否已有 cookies
        if [ -f "$NETSCAPE_COOKIE_PATH" ] || [ -f "$COOKIE_STORE_PATH" ]; then
            print_info "检测到现有 cookies"
            echo -n -e "${YELLOW}是否重新导入？(y/N): ${NC}"
            read -r confirm
            
            if [[ "$confirm" =~ ^[Yy]$ ]]; then
                if [ -n "$COOKIE_FILE" ]; then
                    import_from_file "$COOKIE_FILE" || exit 1
                else
                    interactive_cookie_import || exit 1
                fi
            fi
        else
            # 没有 cookies，需要导入
            if [ -n "$COOKIE_FILE" ]; then
                import_from_file "$COOKIE_FILE" || exit 1
            else
                interactive_cookie_import || exit 1
            fi
        fi
    else
        print_info "跳过 cookie 导入（--skip-cookie-import）"
    fi
    
    echo ""
    
    # 停止现有服务
    stop_cookie_service
    
    # 部署服务
    deploy_cookie_service || exit 1
    
    # 启动服务
    start_cookie_service || exit 1
    
    # 显示部署信息
    show_deployment_info
    
    echo ""
    print_success "部署完成！"
}

# 运行主流程
main
