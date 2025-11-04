# PDF中文字体配置指南

## 问题描述

生成的PDF文件中中文显示为空白或方框，这是因为系统缺少中文字体。

## 快速解决方案

### 方法1：使用自动安装脚本（推荐）

```bash
# 运行字体安装脚本
./scripts/install_chinese_fonts.sh
```

脚本会自动检测操作系统并安装合适的中文字体。

### 方法2：手动安装

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra fonts-wqy-microhei fonts-wqy-zenhei
fc-cache -fv
```

#### CentOS/RHEL/Fedora

```bash
# Fedora/RHEL 8+
sudo dnf install -y google-noto-sans-cjk-fonts google-noto-serif-cjk-fonts wqy-microhei-fonts wqy-zenhei-fonts

# CentOS 7/RHEL 7
sudo yum install -y google-noto-sans-cjk-fonts google-noto-serif-cjk-fonts wqy-microhei-fonts wqy-zenhei-fonts

# 刷新字体缓存
fc-cache -fv
```

#### Arch Linux/Manjaro

```bash
sudo pacman -S noto-fonts-cjk wqy-microhei wqy-zenhei
fc-cache -fv
```

#### Alpine Linux

```bash
sudo apk add font-noto-cjk font-wqy-zenhei
fc-cache -fv
```

#### macOS

```bash
# macOS通常已经包含中文字体，如果需要额外安装：
brew tap homebrew/cask-fonts
brew install --cask font-noto-serif-cjk-sc
```

## 验证安装

安装完成后，运行以下命令验证中文字体是否可用：

```bash
# 列出所有中文字体
fc-list :lang=zh-cn

# 检查特定字体
fc-list | grep -i "noto\|source\|han\|wqy"
```

应该能看到类似以下的输出：

```
/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc: Noto Serif CJK SC:style=Regular
/usr/share/fonts/truetype/wqy/wqy-microhei.ttc: WenQuanYi Micro Hei:style=Regular
```

## 测试PDF生成

安装字体后，重新生成PDF：

```bash
# 生成单个PDF测试
python src/reinvent_insight/tools/generate_pdfs.py -f "downloads/summaries/你的文件.md" -o test_output --overwrite

# 检查生成的PDF
ls -lh test_output/
```

## 字体优先级

PDF生成使用以下字体优先级（从高到低）：

1. **Noto Serif SC** - Google开源字体，优先推荐
2. **Source Han Serif SC/CN** - Adobe开源字体
3. **Songti SC** - macOS系统字体
4. **SimSun** - Windows系统字体
5. **STSong** - 华文宋体
6. **Microsoft YaHei** - 微软雅黑
7. **PingFang SC** - 苹方字体
8. **Hiragino Sans GB** - 冬青黑体
9. **WenQuanYi Micro Hei** - 文泉驿微米黑
10. **serif** - 系统默认衬线字体

## 推荐字体

### 最佳选择：Noto CJK 系列

```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk fonts-noto-cjk-extra

# 优点：
# - Google开源，免费使用
# - 支持简体中文、繁体中文、日文、韩文
# - 字形优美，适合正式文档
# - 包含多种字重（Regular, Bold等）
```

### 备选方案：WenQuanYi（文泉驿）

```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei

# 优点：
# - 开源免费
# - 体积较小
# - 适合屏幕显示
```

## Docker环境配置

如果在Docker容器中运行，需要在Dockerfile中添加字体安装：

```dockerfile
# Debian/Ubuntu基础镜像
FROM python:3.11-slim

# 安装中文字体
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# ... 其他配置
```

或者使用Alpine基础镜像：

```dockerfile
FROM python:3.11-alpine

# 安装中文字体
RUN apk add --no-cache \
    font-noto-cjk \
    font-wqy-zenhei \
    && fc-cache -fv

# ... 其他配置
```

## 常见问题

### Q: 安装字体后PDF仍然没有中文？

A: 尝试以下步骤：

1. 刷新字体缓存：
   ```bash
   fc-cache -fv
   ```

2. 重启应用服务器

3. 验证字体是否正确安装：
   ```bash
   fc-list :lang=zh-cn
   ```

4. 检查PDF生成日志是否有字体相关错误

### Q: 不同字体生成的PDF效果有什么区别？

A: 
- **Noto Serif CJK**: 衬线字体，适合正式文档，阅读体验好
- **Noto Sans CJK**: 无衬线字体，现代简洁
- **WenQuanYi Micro Hei**: 黑体，适合标题和强调
- **WenQuanYi Zen Hei**: 黑体，字形较粗

### Q: 如何更改PDF使用的字体？

A: 编辑 `web/css/pdf_style.css` 文件，修改 `font-family` 属性：

```css
html, body {
    font-family: "你想要的字体", "备用字体1", "备用字体2", serif;
    /* ... */
}
```

### Q: 字体文件占用空间太大怎么办？

A: 
- Noto CJK完整版约100-200MB
- 可以只安装简体中文版本（SC）
- 或使用更轻量的WenQuanYi字体（约10-20MB）

## 相关文件

- `web/css/pdf_style.css` - PDF样式配置（包含字体设置）
- `src/reinvent_insight/tools/generate_pdfs.py` - PDF生成脚本
- `scripts/install_chinese_fonts.sh` - 字体自动安装脚本

## 技术细节

PDF生成使用WeasyPrint库，它依赖系统字体。字体查找顺序：

1. CSS中指定的字体名称
2. 系统字体目录（`/usr/share/fonts/`等）
3. 用户字体目录（`~/.fonts/`）
4. 字体配置文件（`/etc/fonts/`）

WeasyPrint通过fontconfig库查找字体，因此需要确保：
- 字体文件正确安装
- 字体缓存已更新（`fc-cache`）
- 字体名称在CSS中正确指定

## 参考资源

- [Noto CJK字体项目](https://github.com/googlefonts/noto-cjk)
- [文泉驿字体项目](http://wenq.org/)
- [WeasyPrint文档](https://doc.courtbouillon.org/weasyprint/)
- [fontconfig配置指南](https://www.freedesktop.org/wiki/Software/fontconfig/)
