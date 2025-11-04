#!/bin/bash
# 安装中文字体脚本
# 用于PDF生成时支持中文显示

set -e

echo "========================================="
echo "安装中文字体"
echo "========================================="
echo ""

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ 无法检测操作系统"
    exit 1
fi

echo "检测到操作系统: $OS"
echo ""

# 根据不同操作系统安装字体
case "$OS" in
    ubuntu|debian)
        echo "📦 使用 apt 安装中文字体..."
        sudo apt-get update
        sudo apt-get install -y \
            fonts-noto-cjk \
            fonts-noto-cjk-extra \
            fonts-wqy-microhei \
            fonts-wqy-zenhei
        ;;
    
    centos|rhel|fedora)
        echo "📦 使用 yum/dnf 安装中文字体..."
        if command -v dnf &> /dev/null; then
            sudo dnf install -y \
                google-noto-sans-cjk-fonts \
                google-noto-serif-cjk-fonts \
                wqy-microhei-fonts \
                wqy-zenhei-fonts
        else
            sudo yum install -y \
                google-noto-sans-cjk-fonts \
                google-noto-serif-cjk-fonts \
                wqy-microhei-fonts \
                wqy-zenhei-fonts
        fi
        ;;
    
    arch|manjaro)
        echo "📦 使用 pacman 安装中文字体..."
        sudo pacman -S --noconfirm \
            noto-fonts-cjk \
            wqy-microhei \
            wqy-zenhei
        ;;
    
    alpine)
        echo "📦 使用 apk 安装中文字体..."
        sudo apk add --no-cache \
            font-noto-cjk \
            font-wqy-zenhei
        ;;
    
    *)
        echo "❌ 不支持的操作系统: $OS"
        echo ""
        echo "请手动安装以下字体之一："
        echo "  - Noto Sans CJK / Noto Serif CJK"
        echo "  - Source Han Sans / Source Han Serif"
        echo "  - WenQuanYi Micro Hei / WenQuanYi Zen Hei"
        echo ""
        exit 1
        ;;
esac

echo ""
echo "✅ 字体安装完成！"
echo ""

# 刷新字体缓存
echo "🔄 刷新字体缓存..."
fc-cache -fv

echo ""
echo "📋 已安装的中文字体："
fc-list :lang=zh-cn | head -10

echo ""
echo "========================================="
echo "✅ 安装完成！"
echo "========================================="
echo ""
echo "现在可以生成包含中文的PDF了。"
echo ""
