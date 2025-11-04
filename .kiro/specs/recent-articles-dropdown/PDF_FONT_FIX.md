# PDF中文字体问题修复

## 问题描述

生成的PDF文件中中文显示为空白或方框，无法正常阅读。

## 根本原因

系统缺少中文字体。PDF生成使用WeasyPrint库，它依赖系统安装的字体。如果系统只有英文字体（如DejaVu），中文字符将无法渲染。

## 解决方案

### 1. 更新CSS字体配置

修改了 `web/css/pdf_style.css`，添加了完整的中文字体回退链：

```css
html, body {
    font-family: "Noto Serif SC", "Source Han Serif SC", "Source Han Serif CN", 
                 "Songti SC", "SimSun", "STSong", "Microsoft YaHei", 
                 "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", serif;
}
```

这样即使首选字体不可用，也会尝试使用其他中文字体。

### 2. 创建字体安装脚本

创建了 `scripts/install_chinese_fonts.sh`，支持自动检测操作系统并安装合适的中文字体：

- Ubuntu/Debian: Noto CJK + WenQuanYi
- CentOS/RHEL/Fedora: Google Noto CJK + WenQuanYi
- Arch/Manjaro: Noto CJK + WenQuanYi
- Alpine: Noto CJK + WenQuanYi Zen Hei

### 3. 创建详细文档

创建了 `docs/PDF_CHINESE_FONT_SETUP.md`，包含：
- 各操作系统的手动安装指南
- Docker环境配置
- 字体验证方法
- 常见问题解答
- 技术细节说明

### 4. 更新README

在README的"快速开始"部分添加了字体安装步骤，确保用户在初次设置时就安装字体。

## 使用方法

### 快速安装（推荐）

```bash
./scripts/install_chinese_fonts.sh
```

### 手动安装

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk fonts-wqy-microhei
fc-cache -fv
```

#### CentOS/RHEL/Fedora
```bash
sudo dnf install -y google-noto-sans-cjk-fonts wqy-microhei-fonts
fc-cache -fv
```

### 验证安装

```bash
# 检查中文字体
fc-list :lang=zh-cn

# 测试PDF生成
python src/reinvent_insight/tools/generate_pdfs.py -f "downloads/summaries/测试文件.md" -o test_output --overwrite
```

## 推荐字体

1. **Noto CJK** (首选)
   - Google开源
   - 字形优美
   - 支持多种字重
   - 适合正式文档

2. **WenQuanYi** (备选)
   - 开源免费
   - 体积较小
   - 适合屏幕显示

## 技术细节

### 字体查找机制

WeasyPrint通过fontconfig库查找字体：

1. 读取CSS中的 `font-family` 列表
2. 按顺序在系统字体目录中查找
3. 使用第一个找到的可用字体
4. 如果都不可用，使用系统默认字体

### 字体目录

- Linux: `/usr/share/fonts/`, `~/.fonts/`
- macOS: `/Library/Fonts/`, `~/Library/Fonts/`
- Windows: `C:\Windows\Fonts\`

### 字体缓存

fontconfig使用缓存加速字体查找：
- 缓存位置: `~/.cache/fontconfig/`
- 更新命令: `fc-cache -fv`
- 清理命令: `rm -rf ~/.cache/fontconfig/`

## 相关文件

### 新增文件
- `scripts/install_chinese_fonts.sh` - 字体自动安装脚本
- `docs/PDF_CHINESE_FONT_SETUP.md` - 详细配置文档
- `.kiro/specs/recent-articles-dropdown/PDF_FONT_FIX.md` - 本文档

### 修改文件
- `web/css/pdf_style.css` - 添加中文字体回退链
- `README.md` - 添加字体安装步骤

## Docker部署注意事项

如果使用Docker部署，需要在Dockerfile中添加字体安装：

```dockerfile
# Debian/Ubuntu基础镜像
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv
```

## 测试清单

- [ ] 安装中文字体
- [ ] 验证字体可用性 (`fc-list :lang=zh-cn`)
- [ ] 生成测试PDF
- [ ] 检查PDF中文显示正常
- [ ] 测试不同字体效果
- [ ] 验证Docker环境（如适用）

## 参考资源

- [Noto CJK字体](https://github.com/googlefonts/noto-cjk)
- [文泉驿字体](http://wenq.org/)
- [WeasyPrint文档](https://doc.courtbouillon.org/weasyprint/)
- [fontconfig配置](https://www.freedesktop.org/wiki/Software/fontconfig/)
