# Visual Insight 转长图 - 快速开始

## 🚀 5分钟快速上手

### 前提条件

✅ Playwright 已安装  
✅ Chromium 浏览器已安装  
✅ 已有 Visual Insight HTML 文件

### 快速部署（3 步）

#### 1. 安装浏览器（如果未安装）

```bash
playwright install chromium
```

#### 2. 创建图片目录

```bash
mkdir -p downloads/summaries/images
```

#### 3. 重启应用

```bash
# 开发环境
./run-dev.sh

# 或生产环境
./redeploy.sh
```

### 快速测试

#### 方法 1：使用测试脚本

```bash
# 运行简单测试
python tests/test_screenshot_simple.py

# 预期输出
✅ 截图成功！
   路径: downloads/summaries/images/test_screenshot.png
   尺寸: 1920x1080px
   大小: 0.11MB
   耗时: 4.60s
```

#### 方法 2：API 调用

假设你已有一个 Visual Insight 文档（doc_hash: `abc123`）：

**生成长图**：
```bash
curl -X POST "http://localhost:8002/api/article/abc123/visual/to-image" \
  -H "Content-Type: application/json"
```

**获取长图**：
```bash
curl "http://localhost:8002/api/article/abc123/visual/image" \
  -o my_visual_insight.png
```

**带参数生成**：
```bash
curl -X POST "http://localhost:8002/api/article/abc123/visual/to-image?viewport_width=2560&force_regenerate=true" \
  -H "Content-Type: application/json"
```

### 配置说明（可选）

在 `.env` 文件中自定义配置：

```bash
# 功能开关
VISUAL_LONG_IMAGE_ENABLED=true

# 截图视口宽度（像素）
VISUAL_SCREENSHOT_VIEWPORT_WIDTH=1920

# 等待时间（秒，用于图表渲染）
VISUAL_SCREENSHOT_WAIT_TIME=2

# 浏览器启动超时（秒）
VISUAL_SCREENSHOT_BROWSER_TIMEOUT=30
```

### 常见问题

**Q: 如何查看生成的图片？**

A: 图片保存在 `downloads/summaries/images/` 目录，文件名格式为 `{doc_hash}_visual.png`

**Q: 截图时间太长怎么办？**

A: 增加超时时间：`VISUAL_SCREENSHOT_BROWSER_TIMEOUT=60`

**Q: 如何强制重新生成？**

A: 在 API 调用时添加参数：`?force_regenerate=true`

**Q: 如何生成不同尺寸？**

A: 使用参数：`?viewport_width=2560` （支持 1280、1920、2560 等）

### 下一步

- 📖 查看完整部署文档：[DEPLOYMENT.md](visual-insight-to-long-image-DEPLOYMENT.md)
- 🎯 查看设计文档：[visual-insight-to-long-image.md](visual-insight-to-long-image.md)
- 🐛 遇到问题？查看故障排查章节

---

**需要帮助？** 查看部署清单中的故障排查部分
