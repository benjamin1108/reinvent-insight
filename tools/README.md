# AWS re:Invent Insights 工具集

本目录包含了项目的辅助工具脚本。

## 工具列表

### 1. generate_pdfs.py - PDF批量生成工具

将 `downloads/summaries` 目录下的所有 Markdown 文件批量转换为精美的 PDF 文档。

**使用方法：**

```bash
# 批量转换所有文件（默认）
python tools/generate_pdfs.py

# 指定输入输出目录
python tools/generate_pdfs.py -i downloads/summaries -o downloads/pdfs

# 处理单个文件
python tools/generate_pdfs.py -f downloads/summaries/specific-file.md -o downloads/pdfs

# 覆盖已存在的PDF文件
python tools/generate_pdfs.py --overwrite

# 使用自定义CSS样式
python tools/generate_pdfs.py --css path/to/custom.css
```

**功能特点：**
- 🚀 批量处理所有 Markdown 文件
- 📄 支持单文件处理
- 🎨 使用专业的 CSS 样式
- 🇨🇳 完美支持中文字体
- ⚡ 智能跳过已存在的文件
- 📊 实时显示处理进度

### 2. update_metadata.py - 元数据批量更新工具

批量更新 Markdown 文档的 YAML front matter，将原有的 `title` 字段改为 `title_en`，并从文档 H1 标题提取 `title_cn`。

**使用方法：**

```bash
# 运行更新脚本
python tools/update_metadata.py
```

**功能说明：**
- 自动扫描 `downloads/summaries` 目录下的所有 `.md` 文件
- 将 YAML 中的 `title` 字段重命名为 `title_en`
- 从文档的第一个 H1 标题提取中文标题作为 `title_cn`
- 智能跳过已经更新过的文件
- 完整的错误处理和日志记录

## 安装依赖

确保已安装所有必要的 Python 依赖：

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -r requirements.txt
```

主要依赖包括：
- `markdown` - Markdown 解析
- `beautifulsoup4` - HTML 处理
- `weasyprint` - PDF 生成
- `PyYAML` - YAML 解析

## 注意事项

1. **路径说明**：所有工具都会自动识别项目根目录，无需担心相对路径问题
2. **字体文件**：PDF 生成需要 `web/fonts/NotoSerifSC-VF.ttf` 字体文件
3. **CSS 样式**：默认使用 `web/css/pdf_style.css` 样式文件

## 故障排除

### WeasyPrint 安装问题

- Ubuntu/Debian:
  ```bash
  sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
  ```

- macOS:
  ```bash
  brew install pango
  ```

### 常见错误

1. **找不到字体文件**：确保 `web/fonts/NotoSerifSC-VF.ttf` 文件存在
2. **CSS 文件缺失**：确保 `web/css/pdf_style.css` 文件存在
3. **权限问题**：确保对输出目录有写入权限 