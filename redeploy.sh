#!/bin/bash

# reinvent-insight 自动化重新打包和部署脚本
# 使用方法: ./redeploy.sh [选项]
# 选项:
#   --no-backup  不备份现有数据
#   --port PORT  指定端口号（默认：8001）
#   --host HOST  指定主机地址（默认：0.0.0.0）
#   --dry-run    显示将要执行的操作但不实际执行
#   --fix-permissions 只修复现有部署的文件权限

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
PORT=8001
HOST="0.0.0.0"
BACKUP=true
PROJECT_NAME="reinvent-insight"
DEPLOY_DIR="$HOME/${PROJECT_NAME}-prod"
BACKUP_ROOT="$HOME/${PROJECT_NAME}-backups"  # 统一的备份根目录
SERVICE_NAME="${PROJECT_NAME}"
VENV_NAME=".venv-dist"
FIX_PERMISSIONS=false

# 状态变量
LATEST_BACKUP=""  # 最新的备份目录
FRESH_INSTALL=false  # 是否为全新安装
DRY_RUN=false  # 是否为演练模式

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-backup)
      BACKUP=false
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

# 检查是否在项目根目录
check_project_root() {
    if [ ! -f "pyproject.toml" ] || [ ! -d "src/reinvent_insight" ]; then
        print_error "请在项目根目录下运行此脚本"
        exit 1
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
    echo -e "${BLUE}部署计划总结${NC}"
    echo "======================================"
    
    # 检查现有部署
    if [ -d "$DEPLOY_DIR" ]; then
        echo "• 现有部署: 存在"
        if [ "$BACKUP" = true ]; then
            echo "• 数据备份: 将备份当前生产数据"
            # 检查当前 .env 是否为真实配置
            if [ -f "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" ]; then
                if ! grep -q "your-gemini-api-key-here" "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" 2>/dev/null; then
                    echo "  - .env: 真实配置（将备份）"
                else
                    echo "  - .env: 示例配置（跳过备份）"
                fi
            fi
            # 检查 .cookies 文件
            if [ -f "$DEPLOY_DIR/reinvent_insight-0.1.0/.cookies" ]; then
                echo "  - .cookies: 存在（将备份）"
            fi
            # 检查 downloads 目录
            if [ -d "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads" ]; then
                FILE_COUNT=$(find "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads" -type f 2>/dev/null | wc -l)
                echo "  - downloads: $FILE_COUNT 个文件"
            fi
        else
            echo "• 数据备份: 跳过（--no-backup）"
        fi
    else
        echo "• 现有部署: 不存在"
    fi
    
    # 查找历史备份
    if [ -d "$BACKUP_ROOT" ]; then
        local old_backups=$(ls -d "$BACKUP_ROOT"/backup_* 2>/dev/null | sort -r)
        if [ -n "$old_backups" ]; then
            echo "• 历史备份: $(echo "$old_backups" | wc -l) 个"
            echo "  最新: $(basename $(echo "$old_backups" | head -1))"
            echo "  位置: $BACKUP_ROOT"
        else
            echo "• 历史备份: 无"
        fi
    else
        echo "• 历史备份: 无"
    fi
    
    echo "• 部署位置: $DEPLOY_DIR"
    echo "• 服务端口: $PORT"
    echo "• 服务主机: $HOST"
    
    # 显示构建配置信息
    if [ -f "MANIFEST.in" ]; then
        if grep -q "prune web/test" MANIFEST.in; then
            echo "• 构建配置: 排除 test 目录 ✓"
        else
            echo "• 构建配置: 包含 test 目录 ⚠️"
        fi
    fi
    
    echo "======================================"
    
    if [ "$DRY_RUN" = true ]; then
        echo ""
        print_info "演练模式结束，未执行任何实际操作"
        exit 0
    else
        echo ""
        echo -n -e "${YELLOW}是否继续执行？(y/N): ${NC}"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            print_info "部署已取消"
            exit 0
        fi
    fi
}

# 检查并处理备份
check_and_handle_backup() {
    # 确保备份根目录存在
    mkdir -p "$BACKUP_ROOT"
    
    # 查找最新的备份目录
    LATEST_BACKUP=$(ls -d "$BACKUP_ROOT"/backup_* 2>/dev/null | sort -r | head -1)
    
    # 总是先备份当前的生产数据（如果存在）
    if [ -d "$DEPLOY_DIR" ] && [ "$BACKUP" = true ]; then
        print_info "发现现有部署，备份当前生产数据..."
        BACKUP_DIR="$BACKUP_ROOT/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # 备份下载目录
        if [ -d "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads" ]; then
            # 检查是否有任何文件（不限深度）
            if [ "$(find "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads" -type f 2>/dev/null | head -1)" ]; then
                cp -r "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads" "$BACKUP_DIR/"
                FILE_COUNT=$(find "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads" -type f 2>/dev/null | wc -l)
                print_info "已备份 downloads 目录（包含 $FILE_COUNT 个文件）"
            else
                # 即使没有文件，也备份目录结构
                cp -r "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads" "$BACKUP_DIR/"
                print_info "已备份 downloads 目录结构（空目录）"
            fi
        fi
        
        # 备份 .env 文件（只备份非示例文件）
        if [ -f "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" ]; then
            if ! grep -q "your-gemini-api-key-here" "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" 2>/dev/null; then
                cp "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" "$BACKUP_DIR/"
                print_info "已备份 .env 文件（真实配置）"
            else
                print_warning "现有 .env 是示例文件，跳过备份"
            fi
        fi
        
        # 备份 .cookies 文件
        if [ -f "$DEPLOY_DIR/reinvent_insight-0.1.0/.cookies" ]; then
            cp "$DEPLOY_DIR/reinvent_insight-0.1.0/.cookies" "$BACKUP_DIR/"
            print_info "已备份 .cookies 文件"
        fi
        
        # 检查备份目录是否有内容
        if [ -d "$BACKUP_DIR" ]; then
            if [ "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
                print_success "新备份完成: $BACKUP_DIR"
                LATEST_BACKUP="$BACKUP_DIR"  # 使用最新的备份
            else
                # 即使没有实际数据，也保留备份目录作为标记
                echo "$(date)" > "$BACKUP_DIR/backup_timestamp.txt"
                print_info "创建备份标记: $BACKUP_DIR"
                # 如果新备份为空，使用旧备份（如果存在）
                if [ -z "$LATEST_BACKUP" ]; then
                    LATEST_BACKUP="$BACKUP_DIR"
                fi
            fi
        fi
    fi
    
    # 判断是否为全新安装
    if [ -z "$LATEST_BACKUP" ]; then
        print_info "没有任何备份，执行全新部署"
        FRESH_INSTALL=true
    else
        print_info "将使用备份: $LATEST_BACKUP"
        FRESH_INSTALL=false
    fi
    
    # 清理旧的部署目录
    if [ -d "$DEPLOY_DIR" ]; then
        print_info "清理旧的部署目录..."
        rm -rf "$DEPLOY_DIR"
        print_success "已清理旧部署"
    fi
}

# 停止现有服务
stop_service() {
    print_info "检查并停止现有服务..."
    
    # 如果使用 systemd
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_info "停止 systemd 服务..."
        sudo systemctl stop "$SERVICE_NAME"
        print_success "systemd 服务已停止"
    fi
    
    # 检查是否有进程在运行
    if pgrep -f "reinvent-insight web" > /dev/null; then
        print_info "发现运行中的进程，正在停止..."
        pkill -f "reinvent-insight web"
        sleep 2
        print_success "进程已停止"
    fi
}

# 部署新版本
deploy_new_version() {
    print_info "开始部署新版本..."
    
    # 创建部署目录
    mkdir -p "$DEPLOY_DIR"
    
    # 复制包文件
    cp "$PACKAGE_FILE" "$DEPLOY_DIR/"
    
    # 进入部署目录
    cd "$DEPLOY_DIR"
    
    # 解压
    print_info "解压文件..."
    tar -xzf "$(basename "$PACKAGE_FILE")"
    
    # 进入解压后的目录
    cd reinvent_insight-0.1.0
    
    # 创建虚拟环境
    print_info "创建虚拟环境..."
    python3 -m venv "$VENV_NAME"
    
    # 激活虚拟环境并安装
    print_info "安装包..."
    source "$VENV_NAME/bin/activate"
    pip install --upgrade pip
    pip install .
    
    # 创建必要的目录
    mkdir -p downloads/subtitles downloads/summaries downloads/pdfs downloads/tasks
    
    # 验证PDF处理相关的Python模块是否正确安装
    print_info "验证PDF处理模块..."
    if $VENV_NAME/bin/python -c "from reinvent_insight.pdf_processor import PDFProcessor; print('PDF处理模块加载成功')" 2>/dev/null; then
        print_success "PDF处理功能已正确安装"
    else
        print_warning "PDF处理模块加载失败，请检查依赖"
    fi
    
    # 确保所有文件和目录的权限正确
    print_info "修复文件权限..."
    sudo chown -R "$USER:$USER" "$DEPLOY_DIR"
    chmod -R u+rwX,g+rX,o+rX "$DEPLOY_DIR"
    
    # 验证 test 目录是否被正确排除
    if [ ! -d "web/test" ]; then
        print_success "✓ test 目录已被正确排除"
    else
        print_warning "⚠️ test 目录仍然存在，请检查 MANIFEST.in 配置"
        print_info "test 目录内容: $(ls -la web/test | wc -l) 个文件"
    fi
    
    print_success "部署完成"
}

# 恢复数据
restore_data() {
    # 先处理备份数据
    if [ -n "$LATEST_BACKUP" ] && [ -d "$LATEST_BACKUP" ]; then
        print_info "从备份恢复数据: $LATEST_BACKUP"
        
        # 恢复 downloads 目录（整个目录，包括 subtitles、summaries、pdfs 等）
        if [ -d "$LATEST_BACKUP/downloads" ] && [ "$(ls -A "$LATEST_BACKUP/downloads" 2>/dev/null)" ]; then
            print_info "恢复 downloads 目录..."
            # 直接复制整个目录结构
            cp -r "$LATEST_BACKUP/downloads"/* "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads/" 2>/dev/null || true
            # 统计恢复的文件数量
            FILE_COUNT=$(find "$LATEST_BACKUP/downloads" -type f 2>/dev/null | wc -l)
            print_success "已恢复 $FILE_COUNT 个文件"
        else
            print_info "备份中没有 downloads 数据"
        fi
        
        # 恢复 .env 文件
        if [ -f "$LATEST_BACKUP/.env" ]; then
            # 再次检查是否是示例文件（以防万一）
            if grep -q "your-gemini-api-key-here" "$LATEST_BACKUP/.env" 2>/dev/null; then
                print_warning "备份的 .env 是示例配置，跳过恢复"
            else
                cp "$LATEST_BACKUP/.env" "$DEPLOY_DIR/reinvent_insight-0.1.0/"
                print_success "已恢复 .env 配置文件"
            fi
        else
            print_info "备份中没有 .env 文件"
        fi
        
        # 恢复 .cookies 文件
        if [ -f "$LATEST_BACKUP/.cookies" ]; then
            cp "$LATEST_BACKUP/.cookies" "$DEPLOY_DIR/reinvent_insight-0.1.0/"
            print_success "已恢复 .cookies 文件"
        else
            print_info "备份中没有 .cookies 文件"
        fi
        
        # 修复恢复数据的权限
        print_info "修复恢复数据的权限..."
        sudo chown -R "$USER:$USER" "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads/"
        if [ -f "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" ]; then
            sudo chown "$USER:$USER" "$DEPLOY_DIR/reinvent_insight-0.1.0/.env"
        fi
        if [ -f "$DEPLOY_DIR/reinvent_insight-0.1.0/.cookies" ]; then
            sudo chown "$USER:$USER" "$DEPLOY_DIR/reinvent_insight-0.1.0/.cookies"
        fi
    else
        if [ "$FRESH_INSTALL" = true ]; then
            print_info "全新安装，没有历史数据需要恢复"
        else
            print_warning "未找到可用的备份目录"
        fi
    fi
    
    # 备份恢复完成后，进行开发环境文章的增量复制
    print_info "检查开发环境文章..."
    DEV_SUMMARIES_DIR="$HOME/reinvent-insight/downloads/summaries"
    PROD_SUMMARIES_DIR="$DEPLOY_DIR/reinvent_insight-0.1.0/downloads/summaries"
    
    if [ -d "$DEV_SUMMARIES_DIR" ] && [ "$(ls -A "$DEV_SUMMARIES_DIR" 2>/dev/null)" ]; then
        DEV_FILE_COUNT=$(find "$DEV_SUMMARIES_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
        
        # 检查生产环境现有文章数量（包括从备份恢复的）
        EXISTING_PROD_COUNT=0
        if [ -d "$PROD_SUMMARIES_DIR" ]; then
            EXISTING_PROD_COUNT=$(find "$PROD_SUMMARIES_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
        fi
        
        print_info "开发环境: $DEV_FILE_COUNT 篇文章"
        print_info "生产环境现有: $EXISTING_PROD_COUNT 篇文章（备份恢复后）"
        
        print_info "执行增量同步检查..."
        
        # 增量复制：检查开发环境中是否有生产环境没有的文章
        COPIED_COUNT=0
        NEW_FILES=()
        
        for dev_file in "$DEV_SUMMARIES_DIR"/*.md; do
            if [ -f "$dev_file" ]; then
                filename=$(basename "$dev_file")
                if [ ! -f "$PROD_SUMMARIES_DIR/$filename" ]; then
                    cp "$dev_file" "$PROD_SUMMARIES_DIR/"
                    COPIED_COUNT=$((COPIED_COUNT + 1))
                    NEW_FILES+=("$filename")
                    print_info "新增: $filename"
                fi
            fi
        done
        
        if [ "$COPIED_COUNT" -gt 0 ]; then
            print_success "增量同步完成，新增 $COPIED_COUNT 篇文章"
            # 显示部分新增文章名称（避免输出过长）
            if [ "$COPIED_COUNT" -le 5 ]; then
                for file in "${NEW_FILES[@]}"; do
                    print_info "  - $file"
                done
            else
                for i in {0..4}; do
                    if [ -n "${NEW_FILES[$i]}" ]; then
                        print_info "  - ${NEW_FILES[$i]}"
                    fi
                done
                print_info "  ... 以及其他 $((COPIED_COUNT - 5)) 篇文章"
            fi
        else
            print_info "没有新文章需要同步，开发环境和生产环境文章已保持一致"
        fi
    else
        print_info "开发环境没有文章"
    fi
    
    # 最后统计总文章数
    TOTAL_SUMMARIES=$(find "$DEPLOY_DIR/reinvent_insight-0.1.0/downloads/summaries" -name "*.md" -type f 2>/dev/null | wc -l)
    print_success "部署环境总共有 $TOTAL_SUMMARIES 篇文章"
}

# 创建或更新 systemd 服务
update_systemd_service() {
    print_info "更新 systemd 服务配置..."
    
    # 创建服务文件内容
    SERVICE_FILE="/tmp/${SERVICE_NAME}.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=reinvent-insight Web Service
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$DEPLOY_DIR/reinvent_insight-0.1.0
Environment="PATH=$DEPLOY_DIR/reinvent_insight-0.1.0/$VENV_NAME/bin"
Environment="ENVIRONMENT=production"
ExecStart=$DEPLOY_DIR/reinvent_insight-0.1.0/$VENV_NAME/bin/reinvent-insight web --host $HOST --port $PORT
Restart=always
RestartSec=10

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
    
    # 检查 .env 文件
    if [ ! -f "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" ]; then
        print_warning ".env 文件不存在，创建文件..."
        
        # 检查环境变量，如果设置了就使用它们
        if [ -n "$GEMINI_API_KEY" ] && [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
            print_info "使用环境变量创建 .env 文件..."
            cat > "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" << EOF
GEMINI_API_KEY=$GEMINI_API_KEY
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
PREFERRED_MODEL=Gemini
LOG_LEVEL=INFO
EOF
            print_success ".env 文件已使用环境变量创建"
            # 如果使用了环境变量，直接继续启动服务
        else
            # 创建示例文件
            cat > "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" << EOF
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
            print_info "已创建示例 .env 文件"
            print_warning "请注意：PDF分析功能需要配置 GEMINI_API_KEY"
            
            # 询问用户是否要编辑
            echo ""
            echo -e "${YELLOW}是否现在编辑 .env 文件？${NC}"
            echo "1) 使用 nano 编辑"
            echo "2) 使用 vim 编辑"
            echo "3) 稍后手动编辑"
            echo -n "请选择 (1-3): "
            read -r choice
            
            case $choice in
                1)
                    nano "$DEPLOY_DIR/reinvent_insight-0.1.0/.env"
                    ;;
                2)
                    vim "$DEPLOY_DIR/reinvent_insight-0.1.0/.env"
                    ;;
                3)
                    print_info "请稍后编辑 .env 文件："
                    print_info "$DEPLOY_DIR/reinvent_insight-0.1.0/.env"
                    print_warning "服务未启动，配置完成后请运行："
                    print_warning "sudo systemctl start $SERVICE_NAME"
                    return
                    ;;
                *)
                    print_error "无效选择"
                    print_warning "服务未启动，请手动编辑 .env 文件后运行："
                    print_warning "sudo systemctl start $SERVICE_NAME"
                    return
                    ;;
            esac
            
            # 编辑完成后询问是否启动服务
            echo ""
            echo -n -e "${YELLOW}是否现在启动服务？(y/N): ${NC}"
            read -r start_now
            
            if [[ ! "$start_now" =~ ^[Yy]$ ]]; then
                print_info "服务未启动，稍后可运行："
                print_info "sudo systemctl start $SERVICE_NAME"
                return
            fi
        fi
    else
        # 验证现有.env文件的配置
        print_info "验证 .env 配置..."
        if grep -q "your-gemini-api-key-here" "$DEPLOY_DIR/reinvent_insight-0.1.0/.env" 2>/dev/null; then
            print_warning "GEMINI_API_KEY 仍为默认值，PDF分析功能不可用"
        else
            print_success "GEMINI_API_KEY 已配置，PDF分析功能可用"
        fi
    fi
    
    # 启动 systemd 服务
    sudo systemctl enable "$SERVICE_NAME"
    
    # 先停止服务（如果正在运行）
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_info "服务已在运行，先停止..."
        sudo systemctl stop "$SERVICE_NAME"
        sleep 2
    fi
    
    # 启动服务
    print_info "正在启动服务..."
    sudo systemctl start "$SERVICE_NAME"
    
    # 等待服务启动，最多等待 10 秒
    local max_wait=10
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            # 再检查一下进程是否真的在运行
            if pgrep -f "reinvent-insight web" > /dev/null; then
                print_success "服务已成功启动"
                print_info "服务运行在: http://$HOST:$PORT"
                print_info "查看日志: sudo journalctl -u $SERVICE_NAME -f"
                
                # 测试服务是否响应
                sleep 2
                if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT" | grep -q "200\|302"; then
                    print_success "服务正常响应 HTTP 请求"
                else
                    print_warning "服务已启动但可能还在初始化"
                fi
                return
            fi
        fi
        sleep 1
        waited=$((waited + 1))
        echo -n "."
    done
    
    echo ""
    print_error "服务启动失败或启动超时"
    print_info "查看错误: sudo journalctl -u $SERVICE_NAME -n 50"
    
    # 显示最近的错误日志
    echo ""
    echo "最近的错误日志："
    sudo journalctl -u "$SERVICE_NAME" -n 10 --no-pager | grep -E "(ERROR|CRITICAL|Failed)" || echo "没有发现明显错误"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "======================================"
    echo -e "${GREEN}部署信息${NC}"
    echo "======================================"
    echo "部署目录: $DEPLOY_DIR/reinvent_insight-0.1.0"
    echo "服务地址: http://$HOST:$PORT"
    echo "服务名称: $SERVICE_NAME"
    echo ""
    echo "功能特性:"
    echo "  • YouTube 链接分析"
    echo "  • PDF 文件分析（需要 GEMINI_API_KEY）"
    echo "  • 网页内容分析"
    echo "  • Markdown 渲染和 PDF 导出"
    echo ""
    echo "常用命令:"
    echo "  查看状态: sudo systemctl status $SERVICE_NAME"
    echo "  查看日志: sudo journalctl -u $SERVICE_NAME -f"
    echo "  停止服务: sudo systemctl stop $SERVICE_NAME"
    echo "  启动服务: sudo systemctl start $SERVICE_NAME"
    echo "  重启服务: sudo systemctl restart $SERVICE_NAME"
    echo ""
    
    if [ -n "$LATEST_BACKUP" ]; then
        echo "备份位置: $LATEST_BACKUP"
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
        fix_permissions_only
        exit 0
    fi
    
    print_info "开始自动化部署流程..."
    
    # 检查是否在项目根目录
    check_project_root
    
    # 显示部署计划
    show_deployment_plan
    
    # 清理旧的构建
    clean_build
    
    # 构建新包
    build_package
    
    # 检查备份并处理旧部署
    check_and_handle_backup
    
    # 停止现有服务
    stop_service
    
    # 部署新版本
    deploy_new_version
    
    # 恢复数据（如果有备份）
    restore_data
    
    # 更新 systemd 服务
    update_systemd_service
    
    # 启动服务
    start_service
    
    # 最终权限检查和修复（保险措施）
    print_info "执行最终权限检查..."
    if [ -d "$DEPLOY_DIR" ]; then
        # 检查是否有 root 权限的文件
        if find "$DEPLOY_DIR" -user root 2>/dev/null | head -1 | grep -q .; then
            print_warning "发现 root 权限文件，正在修复..."
            sudo chown -R "$USER:$USER" "$DEPLOY_DIR"
            print_success "权限修复完成"
        else
            print_success "权限检查通过"
        fi
    fi
    
    # 显示部署信息
    show_deployment_info
    
    # 清理旧备份
    cleanup_old_backups
    
    print_success "自动化部署完成！"
}

# 清理旧备份（保留最近的N个）
cleanup_old_backups() {
    local keep_count=5  # 保留最近的5个备份
    
    if [ -d "$BACKUP_ROOT" ]; then
        local backup_count=$(ls -d "$BACKUP_ROOT"/backup_* 2>/dev/null | wc -l)
        
        if [ "$backup_count" -gt "$keep_count" ]; then
            print_info "清理旧备份（保留最近的 $keep_count 个）..."
            
            # 获取要删除的备份列表（保留最新的N个）
            local backups_to_delete=$(ls -d "$BACKUP_ROOT"/backup_* 2>/dev/null | sort -r | tail -n +$((keep_count + 1)))
            
            for backup in $backups_to_delete; do
                print_info "删除旧备份: $(basename "$backup")"
                rm -rf "$backup"
            done
            
            print_success "备份清理完成"
        fi
    fi
}

# 只修复文件权限
fix_permissions_only() {
    print_info "开始修复现有部署的文件权限..."
    
    if [ ! -d "$DEPLOY_DIR" ]; then
        print_error "部署目录不存在: $DEPLOY_DIR"
        exit 1
    fi
    
    print_info "检查当前权限状态..."
    
    # 显示当前权限问题
    local root_files=$(find "$DEPLOY_DIR" -user root 2>/dev/null | wc -l)
    if [ "$root_files" -gt 0 ]; then
        print_warning "发现 $root_files 个 root 权限文件"
        
        echo ""
        echo "示例文件权限问题："
        find "$DEPLOY_DIR" -user root 2>/dev/null | head -5 | while read file; do
            ls -ld "$file"
        done
        
        if [ "$DRY_RUN" = true ]; then
            print_info "演练模式：将执行以下命令修复权限："
            echo "  chown -R $USER:$USER $DEPLOY_DIR"
            echo "  chmod -R u+rwX,g+rX,o+rX $DEPLOY_DIR"
            return
        fi
        
        echo ""
        echo -n -e "${YELLOW}是否修复这些权限问题？(y/N): ${NC}"
        read -r confirm
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            print_info "正在修复权限..."
            sudo chown -R "$USER:$USER" "$DEPLOY_DIR"
            chmod -R u+rwX,g+rX,o+rX "$DEPLOY_DIR"
            print_success "权限修复完成"
            
            # 重启服务确保使用正确权限
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