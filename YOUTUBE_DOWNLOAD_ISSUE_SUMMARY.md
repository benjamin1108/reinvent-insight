# YouTube 下载问题快速解决方案

## 问题现象

生产环境下载 YouTube 视频时报错：
```
ERROR: [youtube] n challenge solving failed
WARNING: Some formats may be missing. Ensure you have a supported JavaScript runtime
```

## 根本原因

❌ **不是 Cookie 的问题**  
✅ **是缺少 JavaScript 运行时（Node.js）**

开发环境和生产环境使用的是同一个 cookie 文件（`~/.cookies`），但：
- 开发环境：有 Node.js → 正常工作 ✓
- 生产环境：没有 Node.js → 下载失败 ✗

## 快速修复（3 步）

### 1. 在生产服务器上安装 Node.js

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**CentOS/RHEL:**
```bash
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

### 2. 验证安装

```bash
node --version
# 应该输出: v18.x.x
```

### 3. 重启服务

```bash
sudo systemctl restart reinvent-insight
```

## 或者使用自动修复脚本

```bash
# 在项目根目录
./fix-youtube-download.sh
```

## 技术说明

YouTube 的 "n parameter" 反爬虫机制需要执行 JavaScript 代码来解密。yt-dlp 会自动调用 Node.js 来完成这个过程。

**Cookie 的作用**：访问需要登录的视频、绕过地区限制  
**Node.js 的作用**：解决反爬虫挑战、获取视频格式列表

两者都需要，但解决不同的问题。

## 验证修复

测试下载：
```bash
yt-dlp --dump-json --no-playlist "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

如果输出 JSON 数据，说明修复成功。

## 详细文档

查看 `docs/YOUTUBE_DOWNLOAD_FIX.md` 了解更多技术细节。
