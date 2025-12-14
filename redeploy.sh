#!/bin/bash

# reinvent-insight 自动化重新打包和部署脚本
# 采用软链接切换架构 (Symlink Switching)
# 使用方法: ./redeploy.sh [选项]
# 选项:
#   --no-backup  不备份现有数据
#   --copy-dev-articles  自动复制开发环境文章到生产环境（默认不复制）
#   --port PORT  指定端口号（默认：8001）
#   --host HOST  指定主机地址（默认：127.0.0.1）
#   --fresh      完全重新部署（不复用旧 venv）
#   --dry-run    显示将要执行的操作但不实际执行
#   --fix-permissions 只修复现有部署的文件权限
#   --rollback   回滚到上一个版本

set -e  # 遇到错误立即退出

# 禁止 root 用户直接运行
if [ "$EUID" -eq 0 ]; then
    echo -e "\033[0;31m❌ 请不要使用 sudo 直接运行此脚本！脚本内部会自动处理权限。\033[0m"
    exit 1
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
PORT=8001
HOST="127.0.0.1"
BACKUP=true
COPY_DEV_ARTICLES=false
PROJECT_NAME="reinvent-insight"
SERVICE_NAME="${PROJECT_NAME}"
VENV_NAME=".venv"
FIX_PERMISSIONS=false
FRESH_DEPLOY=false
ROLLBACK=false

# === 软链接架构目录结构 ===
BASE_DIR="$HOME/${PROJECT_NAME}-deploy"     # 部署根目录
RELEASES_DIR="$BASE_DIR/releases"           # 历史版本目录
SHARED_DIR="$BASE_DIR/shared"               # 共享数据目录
CURRENT_LINK="$BASE_DIR/current"            # 当前版本软链接（systemd 指向此）
BACKUP_ROOT="$HOME/${PROJECT_NAME}-backups" # 备份目录

# 新版本目录（运行时生成）
NEW_RELEASE_DIR=""

# 状态变量
LATEST_BACKUP=""
FRESH_INSTALL=false
DRY_RUN=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-backup)
      BACKUP=false
      shift
      ;;
    --copy-dev-articles)
      COPY_DEV_ARTICLES=true
      shift
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --fix-permissions)
      FIX_PERMISSIONS=true
      shift
      ;;
    --fresh)
      FRESH_DEPLOY=true
      shift
      ;;
    --rollback)
      ROLLBACK=true
      shift
      ;;
    *)
      echo -e "${RED}未知参数: $1${NC}"
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

# 带倒计时的确认函数
# 参数: $1 提示文字, $2 默认值(y/n), $3 倒计时秒数
confirm_with_countdown() {
    local prompt="$1"
    local default="$2"
    local timeout="${3:-5}"
    local response
    
    if [ "$default" = "y" ]; then
        echo -n -e "${YELLOW}${prompt} (Y/n) [${timeout}s 后默认 Y]: ${NC}"
    else
        echo -n -e "${YELLOW}${prompt} (y/N) [${timeout}s 后默认 N]: ${NC}"
    fi
    
    # 读取用户输入，带超时
    if read -t "$timeout" -r response; then
        # 用户有输入
        if [ -z "$response" ]; then
            response="$default"
        fi
    else
        # 超时，使用默认值
        echo ""  # 换行
        response="$default"
        print_info "超时，使用默认值: $default"
    fi
    
    # 返回结果
    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0  # true
    else
        return 1  # false
    fi
}

# 预先获取 sudo 权限
acquire_sudo() {
    print_info "需要 sudo 权限执行部署操作..."
    if sudo -v; then
        print_success "已获取 sudo 权限"
        # 保持 sudo 会话活跃（在后台每 60 秒刷新一次）
        ( while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null ) &
        SUDO_KEEPER_PID=$!
    else
        print_error "无法获取 sudo 权限"
        exit 1
    fi
}

# 清理 sudo keeper 进程
cleanup_sudo_keeper() {
    if [ -n "$SUDO_KEEPER_PID" ]; then
        kill "$SUDO_KEEPER_PID" 2>/dev/null || true
    fi
}

# 注册退出时清理
trap cleanup_sudo_keeper EXIT

# 检查是否在项目根目录
check_project_root() {
    if [ ! -f "pyproject.toml" ] || [ ! -d "src/reinvent_insight" ]; then
        print_error "请在项目根目录下运行此脚本"
        exit 1
    fi
}

# 初始化软链接架构目录结构
init_structure() {
    print_info "初始化部署目录结构..."
    
    # 创建核心目录
    mkdir -p "$RELEASES_DIR"
    # 只创建用户数据目录，不创建临时文件和日志目录
    # 临时文件（tasks、chunks）在 cache/ 目录，每个 release 独立
    # 日志使用 journalctl，不需要文件日志
    mkdir -p "$SHARED_DIR/downloads/subtitles"
    mkdir -p "$SHARED_DIR/downloads/summaries"
    mkdir -p "$SHARED_DIR/downloads/pdfs"
    mkdir -p "$SHARED_DIR/downloads/keyframes"
    mkdir -p "$SHARED_DIR/downloads/trash"
    mkdir -p "$SHARED_DIR/downloads/tts_cache"
    mkdir -p "$SHARED_DIR/downloads/tts_texts"
    mkdir -p "$SHARED_DIR/config"
    mkdir -p "$BACKUP_ROOT"
    
    print_success "目录结构初始化完成"
    print_info "  releases: $RELEASES_DIR"
    print_info "  shared:   $SHARED_DIR"
    print_info "  current:  $CURRENT_LINK"
}

# 迁移旧版部署数据到新架构
migrate_old_deployment() {
    local OLD_DEPLOY="$HOME/${PROJECT_NAME}-prod/reinvent_insight-0.1.0"
    local MIGRATED=false
    
    # 1. 检查 shared/downloads 是否为空，如果有内容则无需迁移
    local shared_file_count=$(find "$SHARED_DIR/downloads" -type f 2>/dev/null | wc -l)
    if [ "$shared_file_count" -gt 0 ]; then
        print_info "shared/downloads 已有 $shared_file_count 个文件，跳过数据迁移"
        return
    fi
    
    # 2. 尝试从旧版 reinvent-insight-prod 目录迁移
    if [ -d "$OLD_DEPLOY" ]; then
        print_info "检测到旧版部署，迁移数据到新架构..."
        
        # 迁移配置文件
        if [ -f "$OLD_DEPLOY/.env" ]; then
            if ! grep -q "your-gemini-api-key-here" "$OLD_DEPLOY/.env" 2>/dev/null; then
                cp "$OLD_DEPLOY/.env" "$SHARED_DIR/config/.env"
                print_info "已迁移 .env 配置文件"
            fi
        fi
        
        # 迁移 .cookies
        if [ -f "$OLD_DEPLOY/.cookies" ]; then
            cp "$OLD_DEPLOY/.cookies" "$SHARED_DIR/config/.cookies"
            print_info "已迁移 .cookies 文件"
        fi
        
        # 迁移 downloads 目录
        if [ -d "$OLD_DEPLOY/downloads" ] && [ "$(ls -A "$OLD_DEPLOY/downloads" 2>/dev/null)" ]; then
            cp -r "$OLD_DEPLOY/downloads"/* "$SHARED_DIR/downloads/" 2>/dev/null || true
            MIGRATED=true
        fi
    fi
    
    # 3. 尝试从现有 releases 版本中迁移（处理非软链接的 downloads 目录）
    if [ "$MIGRATED" = false ] && [ -d "$RELEASES_DIR" ]; then
        for release in $(ls -t "$RELEASES_DIR" 2>/dev/null | head -5); do
            local release_downloads="$RELEASES_DIR/$release/downloads"
            # 检查是否为真实目录（非软链接）且有内容
            if [ -d "$release_downloads" ] && [ ! -L "$release_downloads" ]; then
                local release_file_count=$(find "$release_downloads" -type f 2>/dev/null | wc -l)
                if [ "$release_file_count" -gt 0 ]; then
                    print_info "从 releases/$release 迁移 $release_file_count 个文件到 shared/downloads..."
                    cp -r "$release_downloads"/* "$SHARED_DIR/downloads/" 2>/dev/null || true
                    MIGRATED=true
                    break
                fi
            fi
        done
    fi
    
    # 4. 尝试从备份目录恢复（如果之前有备份）
    if [ "$MIGRATED" = false ] && [ -d "$BACKUP_ROOT" ]; then
        local latest_backup=$(ls -t "$BACKUP_ROOT" 2>/dev/null | head -1)
        if [ -n "$latest_backup" ] && [ -d "$BACKUP_ROOT/$latest_backup/downloads" ]; then
            local backup_file_count=$(find "$BACKUP_ROOT/$latest_backup/downloads" -type f 2>/dev/null | wc -l)
            if [ "$backup_file_count" -gt 0 ]; then
                print_info "从备份 $latest_backup 恢复 $backup_file_count 个文件到 shared/downloads..."
                cp -r "$BACKUP_ROOT/$latest_backup/downloads"/* "$SHARED_DIR/downloads/" 2>/dev/null || true
                MIGRATED=true
            fi
        fi
    fi
    
    # 5. 报告结果
    if [ "$MIGRATED" = true ]; then
        local final_count=$(find "$SHARED_DIR/downloads" -type f 2>/dev/null | wc -l)
        print_success "数据迁移完成 ($final_count 个文件)"
    else
        print_warning "未找到可迁移的数据，shared/downloads 目录为空"
    fi
}

# 清理旧的构建文件
clean_build() {
    print_info "清理旧的构建文件..."
    rm -rf build/ dist/ *.egg-info src/*.egg-info
    print_success "清理完成"
}

# 构建新的包
build_package() {
    print_info "开始构建新的包..."
    
    # 检查并激活虚拟环境（如果存在）
    if [ -d ".venv" ]; then
        # 检查虚拟环境是否完整
        if [ ! -f ".venv/bin/python" ]; then
            print_warning "虚拟环境不完整，重新创建..."
            rm -rf .venv
            python3 -m venv .venv
        fi
        
        print_info "激活项目虚拟环境..."
        source .venv/bin/activate
        # 确保使用虚拟环境中的 Python
        PYTHON_BIN=".venv/bin/python"
        
        # 使用 python -m pip 方式（更可靠）
        PIP_CMD="$PYTHON_BIN -m pip"
        
        # 确保 pip 可用
        if ! $PYTHON_BIN -m pip --version >/dev/null 2>&1; then
            print_warning "虚拟环境中没有 pip，尝试安装..."
            curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON_BIN
        fi
    elif [ -d "venv" ]; then
        # 检查虚拟环境是否完整
        if [ ! -f "venv/bin/python" ]; then
            print_warning "虚拟环境不完整，重新创建..."
            rm -rf venv
            python3 -m venv venv
        fi
        
        print_info "激活项目虚拟环境..."
        source venv/bin/activate
        PYTHON_BIN="venv/bin/python"
        PIP_CMD="$PYTHON_BIN -m pip"
        
        # 确保 pip 可用
        if ! $PYTHON_BIN -m pip --version >/dev/null 2>&1; then
            print_warning "虚拟环境中没有 pip，尝试安装..."
            curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON_BIN
        fi
    else
        print_warning "未找到虚拟环境，使用系统 Python"
        PYTHON_BIN="python3"
        PIP_CMD="python3 -m pip"
    fi
    
    # 确保有构建工具
    print_info "安装构建依赖..."
    $PIP_CMD install --upgrade pip setuptools wheel build
    
    # 检查 build 模块是否安装成功
    if ! $PYTHON_BIN -c "import build" 2>/dev/null; then
        print_error "build 模块安装失败，尝试重新安装..."
        $PIP_CMD install --force-reinstall build
        
        # 再次检查
        if ! $PYTHON_BIN -c "import build" 2>/dev/null; then
            print_error "无法安装 build 模块，请检查 Python 环境"
            exit 1
        fi
    fi
    
    print_info "使用 Python: $($PYTHON_BIN --version)"
    print_info "构建工具已就绪"
    
    # 检查并显示 MANIFEST.in 配置
    if [ -f "MANIFEST.in" ]; then
        if grep -q "prune web/test" MANIFEST.in; then
            print_info "✓ 已配置排除 web/test 目录（生产环境优化）"
        else
            print_warning "未配置排除 web/test 目录，将包含测试文件"
        fi
    else
        print_warning "未找到 MANIFEST.in 文件"
    fi
    
    # 构建
    print_info "开始构建包（排除测试文件）..."
    $PYTHON_BIN -m build
    
    if [ $? -eq 0 ]; then
        print_success "构建成功"
        # 获取构建的文件名
        PACKAGE_FILE=$(ls -t dist/*.tar.gz | head -1)
        print_info "构建文件: $PACKAGE_FILE"
    else
        print_error "构建失败"
        exit 1
    fi
}

# 显示部署计划
show_deployment_plan() {
    echo ""
    echo "======================================"
    echo -e "${BLUE}部署计划总结 (软链接架构)${NC}"
    echo "======================================"
    
    # 检查现有部署
    if [ -L "$CURRENT_LINK" ]; then
        local current_release=$(readlink -f "$CURRENT_LINK")
        echo "• 当前版本: $(basename "$current_release")"
    else
        echo "• 当前版本: 无（首次部署）"
    fi
    
    # 检查 shared 数据
    if [ -d "$SHARED_DIR/downloads" ]; then
        FILE_COUNT=$(find "$SHARED_DIR/downloads" -type f 2>/dev/null | wc -l)
        echo "• 共享数据: $FILE_COUNT 个文件"
    fi
    
    # 检查配置文件
    if [ -f "$SHARED_DIR/config/.env" ]; then
        if ! grep -q "your-gemini-api-key-here" "$SHARED_DIR/config/.env" 2>/dev/null; then
            echo "• .env 配置: 已配置"
        else
            echo "• .env 配置: 示例文件"
        fi
    fi
    
    # 查找历史版本
    if [ -d "$RELEASES_DIR" ]; then
        local release_count=$(ls -d "$RELEASES_DIR"/*/ 2>/dev/null | wc -l)
        echo "• 历史版本: $release_count 个"
    fi
    
    # 查找历史备份
    if [ -d "$BACKUP_ROOT" ]; then
        local backup_count=$(ls -d "$BACKUP_ROOT"/backup_* 2>/dev/null | wc -l)
        if [ "$backup_count" -gt 0 ]; then
            echo "• 历史备份: $backup_count 个"
        fi
    fi
    
    echo "• 部署位置: $BASE_DIR"
    echo "• current 链接: $CURRENT_LINK"
    echo "• 服务端口: $PORT"
    echo "• 服务主机: $HOST"
    
    # 显示构建配置信息
    if [ -f "MANIFEST.in" ]; then
        if grep -q "prune web/test" MANIFEST.in; then
            echo "• 构建配置: 排除 test 目录 ✓"
        fi
    fi
    
    echo "======================================"
    
    if [ "$DRY_RUN" = true ]; then
        echo ""
        print_info "演练模式结束，未执行任何实际操作"
        exit 0
    fi
}

# 停止现有服务
stop_service() {
    print_info "检查并停止现有服务..."
    
    # 停止 Web 服务
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_info "停止 Web 服务..."
        sudo systemctl stop "$SERVICE_NAME"
        print_success "Web 服务已停止"
    fi
    
    # 检查是否有进程在运行
    if pgrep -f "reinvent-insight web" > /dev/null; then
        print_info "发现运行中的 Web 进程，正在停止..."
        pkill -f "reinvent-insight web"
        sleep 2
        print_success "Web 进程已停止"
    fi
}

# 预先准备新版本（在服务运行期间执行，不停服）
prepare_release() {
    print_info "开始准备新版本（服务仍在运行）..."
    
    # 生成新版本目录名
    NEW_RELEASE_DIR="$RELEASES_DIR/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$NEW_RELEASE_DIR"
    
    # 复制并解压包
    cp "$PACKAGE_FILE" "$NEW_RELEASE_DIR/"
    cd "$NEW_RELEASE_DIR"
    print_info "解压文件..."
    tar -xzf "$(basename "$PACKAGE_FILE")" --strip-components=1
    rm -f "$(basename "$PACKAGE_FILE")"
    
    # 检查是否可以复用旧的 venv
    local OLD_VENV=""
    if [ -L "$CURRENT_LINK" ] && [ -d "$CURRENT_LINK/$VENV_NAME" ]; then
        OLD_VENV="$CURRENT_LINK/$VENV_NAME"
    fi
    
    if [ "$FRESH_DEPLOY" = false ] && [ -n "$OLD_VENV" ] && [ -f "$OLD_VENV/bin/python" ]; then
        print_info "复用现有 venv（跳过依赖安装）..."
        cp -r "$OLD_VENV" "$VENV_NAME"
        
        # 修复 venv bin 目录（重建 python/pip 等可执行文件）
        # 不删除 bin 目录，直接 update
        python3 -m venv "$VENV_NAME"
        
        # 修复所有脚本的 shebang 路径（关键步骤！）
        # 旧 venv 中的脚本 shebang 仍指向旧路径，需要替换为新路径
        local old_venv_path=$(readlink -f "$OLD_VENV")
        local new_venv_path=$(readlink -f "$VENV_NAME")
        if [ "$old_venv_path" != "$new_venv_path" ]; then
            print_info "修复脚本 shebang 路径..."
            for script in "$VENV_NAME/bin"/*; do
                if [ -f "$script" ] && file "$script" | grep -q "text"; then
                    sed -i "s|${old_venv_path}|${new_venv_path}|g" "$script" 2>/dev/null || true
                fi
            done
            print_info "shebang 路径修复完成"
        fi
        
        # 强制尝试恢复 pip 启动器
        "$VENV_NAME/bin/python" -m ensurepip --upgrade --default-pip >/dev/null 2>&1 || true

        # 稳健地使用 python -m pip 安装
        "$VENV_NAME/bin/python" -m pip install . -q
        print_success "venv 复用完成"
    else
        print_info "创建新的虚拟环境..."
        python3 -m venv "$VENV_NAME"
        
        print_info "安装依赖（需要较长时间）..."
        "$VENV_NAME/bin/python" -m pip install --upgrade pip -q
        "$VENV_NAME/bin/python" -m pip install . -q
        
        # 验证核心依赖
        print_info "验证核心依赖..."
        if "$VENV_NAME/bin/python" -c "import google.generativeai" 2>/dev/null; then
            print_info "  ✓ Google Generative AI SDK 已安装"
        fi
        if "$VENV_NAME/bin/python" -c "import reportlab" 2>/dev/null; then
            print_info "  ✓ ReportLab PDF处理库已安装"
        fi
        
        # 安装 Playwright 浏览器
        if "$VENV_NAME/bin/python" -c "import playwright" 2>/dev/null; then
            print_info "安装 Chromium 浏览器..."
            "$VENV_NAME/bin/playwright" install chromium >/dev/null 2>&1 || true
            print_info "  ✓ Chromium 浏览器已安装"
        fi
    fi
    
    # 创建指向共享数据的软链接
    print_info "链接共享数据目录..."
    rm -rf downloads
    ln -s "$SHARED_DIR/downloads" downloads
    
    # 链接配置文件
    if [ -f "$SHARED_DIR/config/.env" ]; then
        ln -sf "$SHARED_DIR/config/.env" .env
    fi
    if [ -f "$SHARED_DIR/config/.cookies" ]; then
        ln -sf "$SHARED_DIR/config/.cookies" .cookies
    fi
    
    # 修复权限
    chmod -R u+rwX,g+rX,o+rX "$NEW_RELEASE_DIR"
    
    print_success "新版本准备完成: $NEW_RELEASE_DIR"
}

# 原子切换到新版本（停服后执行，秒级完成）
activate_release() {
    print_info "原子切换到新版本..."
    
    if [ -z "$NEW_RELEASE_DIR" ] || [ ! -d "$NEW_RELEASE_DIR" ]; then
        print_error "新版本目录不存在，无法切换"
        exit 1
    fi
    
    # 记录旧版本（用于回滚）
    if [ -L "$CURRENT_LINK" ]; then
        local OLD_RELEASE=$(readlink -f "$CURRENT_LINK")
        print_info "旧版本: $(basename "$OLD_RELEASE")"
    fi
    
    # 原子切换软链接（秒级操作）
    ln -sfn "$NEW_RELEASE_DIR" "$CURRENT_LINK"
    
    # 验证切换是否成功
    if [ -L "$CURRENT_LINK" ] && [ -d "$CURRENT_LINK" ]; then
        print_success "软链接切换成功: $CURRENT_LINK -> $NEW_RELEASE_DIR"
    else
        print_error "软链接切换失败"
        exit 1
    fi
    
    # 确保权限正确
    sudo chown -R "$USER:$USER" "$NEW_RELEASE_DIR"
    
    print_success "原子切换完成"
}

# 创建或更新 systemd 服务
update_systemd_service() {
    print_info "更新 systemd 服务配置..."
    
    # 创建服务文件内容（指向 current 软链接）
    SERVICE_FILE="/tmp/${SERVICE_NAME}.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=reinvent-insight Web Service
After=network.target
# 自动重启限制（防止无限重启死循环）
StartLimitIntervalSec=500
StartLimitBurst=5

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$CURRENT_LINK
Environment="PATH=$CURRENT_LINK/$VENV_NAME/bin"
Environment="ENVIRONMENT=production"
ExecStart=$CURRENT_LINK/$VENV_NAME/bin/reinvent-insight web --host $HOST --port $PORT
Restart=always
RestartSec=10
# 安全加固
ProtectSystem=full
# 注意: 不能启用 PrivateTmp，否则无法读取 Cookie Manager 的 PID 文件
PrivateTmp=false

[Install]
WantedBy=multi-user.target
EOF

    # 复制到 systemd 目录
    sudo cp "$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"
    
    # 重新加载 systemd
    sudo systemctl daemon-reload
    
    print_success "systemd 服务配置已更新"
}

# 启动服务
start_service() {
    print_info "启动服务..."
    
    # 检查 .env 文件（现在在 shared/config 目录）
    if [ ! -f "$SHARED_DIR/config/.env" ]; then
        print_warning ".env 文件不存在，创建文件..."
        
        # 检查环境变量，如果设置了就使用它们
        if [ -n "$GEMINI_API_KEY" ] && [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
            print_info "使用环境变量创建 .env 文件..."
            cat > "$SHARED_DIR/config/.env" << EOF
GEMINI_API_KEY=$GEMINI_API_KEY
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
PREFERRED_MODEL=Gemini
LOG_LEVEL=INFO
EOF
            print_success ".env 文件已使用环境变量创建"
        else
            # 创建示例文件
            cat > "$SHARED_DIR/config/.env" << EOF
# Gemini API 配置（PDF分析功能必需）
GEMINI_API_KEY=your-gemini-api-key-here

# 管理员账号配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# AI 模型配置
PREFERRED_MODEL=Gemini

# 日志级别
LOG_LEVEL=INFO
EOF
            print_info "已创建示例 .env 文件: $SHARED_DIR/config/.env"
            print_warning "请注意：PDF分析功能需要配置 GEMINI_API_KEY"
            
            echo ""
            echo -e "${YELLOW}是否现在编辑 .env 文件？${NC}"
            echo "1) 使用 nano 编辑"
            echo "2) 使用 vim 编辑"
            echo "3) 稍后手动编辑"
            echo -n "请选择 (1-3): "
            read -r choice
            
            case $choice in
                1) nano "$SHARED_DIR/config/.env" ;;
                2) vim "$SHARED_DIR/config/.env" ;;
                3)
                    print_info "请稍后编辑 .env 文件：$SHARED_DIR/config/.env"
                    print_warning "服务未启动，配置完成后请运行：sudo systemctl start $SERVICE_NAME"
                    return
                    ;;
                *)
                    print_warning "服务未启动，请手动编辑 .env 文件后运行：sudo systemctl start $SERVICE_NAME"
                    return
                    ;;
            esac
            
            echo ""
            echo -n -e "${YELLOW}是否现在启动服务？(y/N): ${NC}"
            read -r start_now
            if [[ ! "$start_now" =~ ^[Yy]$ ]]; then
                print_info "服务未启动，稍后可运行：sudo systemctl start $SERVICE_NAME"
                return
            fi
        fi
        
        # 确保配置文件已链接到当前版本
        if [ -d "$CURRENT_LINK" ] && [ ! -L "$CURRENT_LINK/.env" ]; then
            ln -sf "$SHARED_DIR/config/.env" "$CURRENT_LINK/.env"
        fi
    else
        # 验证现有 .env 文件的配置
        print_info "验证 .env 配置..."
        if grep -q "your-gemini-api-key-here" "$SHARED_DIR/config/.env" 2>/dev/null; then
            print_warning "GEMINI_API_KEY 仍为默认值，PDF分析功能不可用"
        else
            print_success "GEMINI_API_KEY 已配置，PDF分析功能可用"
        fi
    fi
    
    # 启动 Web 服务
    sudo systemctl enable "$SERVICE_NAME"
    
    # 先停止服务（如果正在运行）
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_info "Web 服务已在运行，先停止..."
        sudo systemctl stop "$SERVICE_NAME"
        sleep 2
    fi
    
    # 启动 Web 服务
    print_info "正在启动 Web 服务..."
    sudo systemctl start "$SERVICE_NAME"
    
    # 等待服务启动，最多等待 10 秒
    local max_wait=10
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            # 再检查一下进程是否真的在运行
            if pgrep -f "reinvent-insight web" > /dev/null; then
                print_success "Web 服务已成功启动"
                print_info "服务运行在: http://$HOST:$PORT"
                print_info "查看日志: sudo journalctl -u $SERVICE_NAME -f"
                
                # 测试服务是否响应
                sleep 2
                if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT" | grep -q "200\|302"; then
                    print_success "Web 服务正常响应 HTTP 请求"
                else
                    print_warning "Web 服务已启动但可能还在初始化"
                fi
                break
            fi
        fi
        sleep 1
        waited=$((waited + 1))
        echo -n "."
    done
    
    if [ $waited -ge $max_wait ]; then
        echo ""
        print_error "Web 服务启动失败或启动超时"
        print_info "查看错误: sudo journalctl -u $SERVICE_NAME -n 50"
        
        # 显示最近的错误日志
        echo ""
        echo "最近的错误日志："
        sudo journalctl -u "$SERVICE_NAME" -n 10 --no-pager | grep -E "(ERROR|CRITICAL|Failed)" || echo "没有发现明显错误"
    fi
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "======================================"
    echo -e "${GREEN}部署信息 (软链接架构)${NC}"
    echo "======================================"
    
    # 显示当前版本
    if [ -L "$CURRENT_LINK" ]; then
        local current_release=$(readlink -f "$CURRENT_LINK")
        echo "当前版本: $(basename "$current_release")"
    fi
    
    echo "部署目录: $BASE_DIR"
    echo "current 链接: $CURRENT_LINK"
    echo "shared 目录: $SHARED_DIR"
    echo "服务地址: http://$HOST:$PORT"
    echo ""
    echo "服务状态:"
    echo "  • Web 服务: $SERVICE_NAME"
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "    状态: ✓ 运行中"
    else
        echo "    状态: ✗ 未运行"
    fi
    
    echo ""
    echo "功能特性:"
    echo "  • YouTube 链接分析"
    
    # 检查PDF功能状态
    if [ -f "$SHARED_DIR/config/.env" ]; then
        if grep -q "your-gemini-api-key-here" "$SHARED_DIR/config/.env" 2>/dev/null; then
            echo "  • PDF 文件分析（需要配置 GEMINI_API_KEY）"
        else
            echo "  • PDF 文件分析（✓ 已配置）"
        fi
    fi
    
    echo "  • 网页内容分析"
    echo "  • Markdown 渲染和 PDF 导出"
    echo "  • Visual Insight 可视化解读"
    echo ""
    echo "常用命令:"
    echo "  查看状态: sudo systemctl status $SERVICE_NAME"
    echo "  查看日志: sudo journalctl -u $SERVICE_NAME -f"
    echo "  重启服务: sudo systemctl restart $SERVICE_NAME"
    echo "  回滚版本: ./redeploy.sh --rollback"
    echo ""
    
    # 显示历史版本
    if [ -d "$RELEASES_DIR" ]; then
        local releases=($(ls -t "$RELEASES_DIR" | head -3))
        if [ ${#releases[@]} -gt 1 ]; then
            echo "最近版本:"
            for release in "${releases[@]}"; do
                if [ "$(readlink -f "$CURRENT_LINK")" = "$RELEASES_DIR/$release" ]; then
                    echo "  • $release (当前)"
                else
                    echo "  • $release"
                fi
            done
            echo ""
        fi
    fi
    
    if [ -n "$LATEST_BACKUP" ]; then
        echo "最新备份: $LATEST_BACKUP"
    fi
    echo "======================================"
}

# 主流程
main() {
    if [ "$DRY_RUN" = true ]; then
        print_warning "演练模式：只显示将要执行的操作，不会实际执行"
        echo ""
    fi
    
    # 如果只是修复权限，执行权限修复后退出
    if [ "$FIX_PERMISSIONS" = true ]; then
        acquire_sudo
        fix_permissions_only
        exit 0
    fi
    
    # 如果是回滚操作
    if [ "$ROLLBACK" = true ]; then
        acquire_sudo
        rollback
        exit 0
    fi
    
    # 预先获取 sudo 权限（非演练模式）
    if [ "$DRY_RUN" = false ]; then
        acquire_sudo
    fi
    
    print_info "开始自动化部署流程..."
    
    # 检查是否在项目根目录
    check_project_root
    
    # 初始化目录结构
    init_structure
    
    # 迁移旧版部署数据（如果存在）
    migrate_old_deployment
    
    # 显示部署计划
    show_deployment_plan
    
    # ========== 第一阶段：服务运行中的准备工作 ==========
    echo ""
    echo -e "${BLUE}═════ 阶段 1/2: 准备新版本（服务仍在运行） ═════${NC}"
    
    # 清理旧的构建
    clean_build
    
    # 构建新包
    build_package
    
    # 准备新版本（在 releases 目录，不停服）
    prepare_release
    
    # 备份 shared 数据（可选）
    if [ "$BACKUP" = true ]; then
        backup_shared_data
    fi
    
    # ========== 第二阶段：停服切换（最小化停服时间） ==========
    echo ""
    echo -e "${YELLOW}═════ 阶段 2/2: 原子切换（停服开始） ═════${NC}"
    local switch_start=$(date +%s)
    
    # 停止现有服务
    stop_service
    
    # 原子切换软链接（ln -sfn，秒级操作）
    activate_release
    
    # 更新 systemd 服务（仅首次部署或配置变更时需要）
    update_systemd_service
    
    # 启动服务
    start_service
    
    local switch_end=$(date +%s)
    local switch_duration=$((switch_end - switch_start))
    echo -e "${GREEN}═════ 停服切换完成，耗时: ${switch_duration} 秒 ═════${NC}"
    
    # 最终权限检查
    print_info "执行最终权限检查..."
    if [ -d "$NEW_RELEASE_DIR" ]; then
        if find "$NEW_RELEASE_DIR" -user root 2>/dev/null | head -1 | grep -q .; then
            print_warning "发现 root 权限文件，正在修复..."
            sudo chown -R "$USER:$USER" "$NEW_RELEASE_DIR"
            print_success "权限修复完成"
        else
            print_success "权限检查通过"
        fi
    fi
    
    # 显示部署信息
    show_deployment_info
    
    # 清理旧备份和旧版本
    cleanup_old_backups
    cleanup_old_releases
    
    print_success "自动化部署完成！"
}

# 备份 shared 数据
backup_shared_data() {
    if [ -d "$SHARED_DIR" ] && [ "$(ls -A "$SHARED_DIR/downloads" 2>/dev/null)" ]; then
        local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
        LATEST_BACKUP="$BACKUP_ROOT/$backup_name"
        mkdir -p "$LATEST_BACKUP"
        
        print_info "备份 shared 数据..."
        cp -r "$SHARED_DIR/downloads" "$LATEST_BACKUP/" 2>/dev/null || true
        cp -r "$SHARED_DIR/config" "$LATEST_BACKUP/" 2>/dev/null || true
        
        local file_count=$(find "$LATEST_BACKUP" -type f 2>/dev/null | wc -l)
        print_success "已备份 $file_count 个文件到: $LATEST_BACKUP"
    fi
}

# 清理旧备份（保留最近的N个）
cleanup_old_backups() {
    local keep_count=5
    
    if [ -d "$BACKUP_ROOT" ]; then
        local backup_count=$(ls -d "$BACKUP_ROOT"/backup_* 2>/dev/null | wc -l)
        
        if [ "$backup_count" -gt "$keep_count" ]; then
            print_info "清理旧备份（保留最近的 $keep_count 个）..."
            local backups_to_delete=$(ls -d "$BACKUP_ROOT"/backup_* 2>/dev/null | sort -r | tail -n +$((keep_count + 1)))
            for backup in $backups_to_delete; do
                print_info "删除旧备份: $(basename "$backup")"
                rm -rf "$backup"
            done
            print_success "备份清理完成"
        fi
    fi
}

# 清理旧版本（保留最近的N个）
cleanup_old_releases() {
    local keep_count=5
    
    if [ -d "$RELEASES_DIR" ]; then
        local release_count=$(ls -d "$RELEASES_DIR"/*/ 2>/dev/null | wc -l)
        
        if [ "$release_count" -gt "$keep_count" ]; then
            print_info "清理旧版本（保留最近的 $keep_count 个）..."
            cd "$RELEASES_DIR"
            ls -t | tail -n +$((keep_count + 1)) | xargs -I {} rm -rf "{}"
            print_success "旧版本清理完成"
        fi
    fi
}

# 回滚到上一个版本
rollback() {
    print_info "开始回滚操作..."
    
    if [ ! -L "$CURRENT_LINK" ]; then
        print_error "当前没有有效的部署，无法回滚"
        exit 1
    fi
    
    local current_release=$(readlink -f "$CURRENT_LINK")
    local current_name=$(basename "$current_release")
    
    # 获取所有版本并排序
    local releases=($(ls -t "$RELEASES_DIR"))
    
    if [ ${#releases[@]} -lt 2 ]; then
        print_error "没有可以回滚的历史版本"
        exit 1
    fi
    
    # 找到上一个版本
    local previous_release=""
    for release in "${releases[@]}"; do
        if [ "$release" != "$current_name" ]; then
            previous_release="$RELEASES_DIR/$release"
            break
        fi
    done
    
    if [ -z "$previous_release" ] || [ ! -d "$previous_release" ]; then
        print_error "找不到可回滚的版本"
        exit 1
    fi
    
    print_info "当前版本: $current_name"
    print_info "回滚目标: $(basename "$previous_release")"
    
    # 确认回滚
    if ! confirm_with_countdown "确认回滚到上一个版本？" "n" 5; then
        print_info "回滚已取消"
        exit 0
    fi
    
    # 停止服务
    stop_service
    
    # 切换软链接
    ln -sfn "$previous_release" "$CURRENT_LINK"
    print_success "已回滚到: $(basename "$previous_release")"
    
    # 启动服务
    sudo systemctl start "$SERVICE_NAME"
    
    # 检查服务状态
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "服务已启动"
    else
        print_error "服务启动失败"
    fi
}

# 只修复文件权限
fix_permissions_only() {
    print_info "开始修复现有部署的文件权限..."
    
    if [ ! -L "$CURRENT_LINK" ]; then
        print_error "没有有效的部署: $CURRENT_LINK"
        exit 1
    fi
    
    local current_release=$(readlink -f "$CURRENT_LINK")
    print_info "检查当前版本: $current_release"
    
    # 检查权限问题
    local root_files=$(find "$current_release" -user root 2>/dev/null | wc -l)
    local shared_root_files=$(find "$SHARED_DIR" -user root 2>/dev/null | wc -l)
    local total_root_files=$((root_files + shared_root_files))
    
    if [ "$total_root_files" -gt 0 ]; then
        print_warning "发现 $total_root_files 个 root 权限文件"
        
        if [ "$DRY_RUN" = true ]; then
            print_info "演练模式：将执行以下命令修复权限："
            echo "  chown -R $USER:$USER $current_release"
            echo "  chown -R $USER:$USER $SHARED_DIR"
            return
        fi
        
        echo ""
        echo -n -e "${YELLOW}是否修复这些权限问题？(y/N): ${NC}"
        read -r confirm
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            print_info "正在修复权限..."
            sudo chown -R "$USER:$USER" "$current_release"
            sudo chown -R "$USER:$USER" "$SHARED_DIR"
            chmod -R u+rwX,g+rX,o+rX "$current_release"
            print_success "权限修复完成"
            
            # 重启服务
            if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
                print_info "重启服务以应用权限更改..."
                sudo systemctl restart "$SERVICE_NAME"
                sleep 2
                if systemctl is-active --quiet "$SERVICE_NAME"; then
                    print_success "服务重启成功"
                else
                    print_error "服务重启失败"
                fi
            fi
        else
            print_info "已取消权限修复"
        fi
    else
        print_success "所有文件权限正常，无需修复"
    fi
}

# 运行主流程
main