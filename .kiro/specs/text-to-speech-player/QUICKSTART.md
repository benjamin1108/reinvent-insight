# TTS 功能快速启动指南

## 🚀 5 分钟快速开始

### 1. 设置 API Key

```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

**获取 API Key**:
1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建或选择项目
3. 生成 API Key
4. 复制并设置环境变量

### 2. 验证配置

```bash
# 检查配置文件
cat config/model_config.yaml | grep -A 20 "text_to_speech"

# 应该看到:
# text_to_speech:
#   provider: gemini
#   model_name: gemini-2.5-flash-preview-tts
```

### 3. 测试 TTS 功能

#### 方式 A: 后端测试（推荐）

```bash
python tests/test_gemini_tts.py
```

**预期输出**:
```
============================================================
Gemini TTS 功能测试
============================================================

============================================================
测试 1: 基本 TTS 生成
============================================================
✓ 配置加载成功
  Provider: gemini
  Model: gemini-2.5-flash-preview-tts
  API Key: 已设置
✓ Gemini 客户端创建成功

测试文本: 你好，这是一个测试。Gemini TTS 功能正常工作。

开始生成音频...
✓ 收到音频数据
✓ Base64 解码成功
  PCM 数据大小: 115200 bytes
  预计时长: 2.40 秒
✓ 音频已保存到: test_output.wav
  WAV 文件大小: 115244 bytes

...

🎉 所有测试通过！Gemini TTS 功能正常工作。
```

#### 方式 B: 前端测试

1. 启动服务:
```bash
./run-dev.sh
# 或
python src/reinvent_insight/main.py
```

2. 打开浏览器:
```
http://localhost:8000/test/test-tts-streaming.html
```

3. 点击"播放"按钮，观察日志输出

#### 方式 C: 在 ReadingView 中测试

1. 访问主页:
```
http://localhost:8000
```

2. 打开任意文章

3. 点击底部的播放按钮 ▶️

## 🎵 使用音色

### 推荐音色

**中文内容**:
- `Kore` - 坚定，适合正式内容
- `Puck` - 欢快，适合轻松内容
- `Aoede` - 轻快，适合故事叙述

**英文内容**:
- `Charon` - 知性，适合技术文档
- `Leda` - 年轻，适合教育内容
- `Sulafat` - 温暖，适合人文内容

### 在代码中使用

```python
# Python
async for chunk in client.generate_tts_stream(
    text="你好世界",
    voice="Kore",  # 选择音色
    language="zh-CN"
):
    # 处理音频数据
    pass
```

```javascript
// JavaScript
const requestData = {
    article_hash: 'test_123',
    text: '你好世界',
    voice: 'Kore',  // 选择音色
    language: 'zh-CN',
    use_cache: true,
    skip_code_blocks: true
};

await audioPlayer.loadFromStream(requestData);
```

## 🔧 常见问题

### Q1: API Key 错误

**错误信息**:
```
❌ 错误: GEMINI_API_KEY 环境变量未设置
```

**解决方案**:
```bash
# 设置环境变量
export GEMINI_API_KEY="your-key-here"

# 验证
echo $GEMINI_API_KEY
```

### Q2: 音频无法播放

**可能原因**:
1. 浏览器不支持 Web Audio API
2. 音频数据损坏
3. 网络连接问题

**解决方案**:
1. 使用现代浏览器（Chrome, Firefox, Safari）
2. 检查浏览器控制台错误
3. 查看后端日志

### Q3: 生成速度慢

**可能原因**:
1. 文本过长
2. 网络延迟
3. API 速率限制

**解决方案**:
1. 分块处理长文本
2. 使用缓存功能
3. 检查网络连接

### Q4: 音色不生效

**可能原因**:
1. 音色名称拼写错误
2. 使用了旧的 Qwen 音色名称

**解决方案**:
1. 使用正确的 Gemini 音色名称（见下方列表）
2. 检查浏览器 localStorage 中的偏好设置

## 📋 音色速查表

### 按风格分类

**明亮 (Bright)**
- Zephyr, Autonoe

**欢快 (Upbeat)**
- Puck, Fenrir, Laomedeia

**坚定 (Firm)**
- Kore ⭐, Orus, Alnilam

**知性 (Informative)**
- Charon, Rasalgethi

**随和 (Easy-going)**
- Callirrhoe, Umbriel

**清晰 (Clear)**
- Iapetus, Erinome

**流畅 (Smooth)**
- Algieba, Despina

**其他特色**
- Leda (年轻)
- Aoede (轻快)
- Enceladus (气声)
- Algenib (沙哑)
- Achernar (柔和)
- Schedar (平稳)
- Gacrux (成熟)
- Pulcherrima (直接)
- Achird (友好)
- Zubenelgenubi (随意)
- Vindemiatrix (温和)
- Sadachbia (活泼)
- Sadaltager (博学)
- Sulafat (温暖)

⭐ = 默认音色

## 🎯 快速测试命令

### 测试单个音色
```bash
python -c "
import asyncio
from src.reinvent_insight.model_config import ModelConfigManager, GeminiClient

async def test():
    config = ModelConfigManager.get_instance().get_config('text_to_speech')
    client = GeminiClient(config)
    async for chunk in client.generate_tts_stream('测试', 'Kore', 'zh-CN'):
        print(f'✓ 收到 {len(chunk)} bytes')
        break

asyncio.run(test())
"
```

### 测试缓存
```bash
# 第一次生成（无缓存）
curl -X POST http://localhost:8000/api/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"article_hash":"test","text":"测试","voice":"Kore","language":"zh-CN","use_cache":true}'

# 第二次生成（使用缓存）
# 应该立即返回 cached 事件
```

### 清空缓存
```bash
rm -rf downloads/tts_cache/*
```

## 📊 性能基准

### 典型响应时间

| 文本长度 | 生成时间 | 音频时长 |
|---------|---------|---------|
| 50 字符 | 1-2 秒 | 3-5 秒 |
| 200 字符 | 2-3 秒 | 12-15 秒 |
| 500 字符 | 3-5 秒 | 30-35 秒 |
| 1000 字符 | 5-8 秒 | 60-70 秒 |

### 缓存效果

| 场景 | 首次 | 缓存命中 | 改进 |
|------|------|---------|------|
| 短文本 | 2 秒 | 0.1 秒 | 20x |
| 长文本 | 5 秒 | 0.2 秒 | 25x |

## 🔍 调试技巧

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 查看 SSE 事件

```javascript
// 在浏览器控制台
const eventSource = new EventSource('/api/tts/stream?...');
eventSource.onmessage = (e) => console.log('Event:', e);
```

### 检查音频数据

```python
import base64

# 解码 Base64
pcm_data = base64.b64decode(audio_chunk)

# 检查大小
print(f"PCM size: {len(pcm_data)} bytes")
print(f"Duration: {len(pcm_data) / (24000 * 2):.2f} seconds")
```

## 📚 更多资源

- [完整文档](./SUMMARY.md)
- [迁移指南](./MIGRATION-to-gemini.md)
- [设计文档](./design.md)
- [Gemini TTS API](https://ai.google.dev/gemini-api/docs/speech-generation)

## 💡 提示

1. **首次使用**: 建议先运行 `tests/test_gemini_tts.py` 验证配置
2. **音色选择**: 在 AI Studio 中试听音色效果
3. **长文本**: 系统会自动分块处理
4. **缓存**: 默认启用，可节省 API 调用
5. **速度**: 可在 UI 中调整播放速度（0.5x-2x）

## ✅ 检查清单

开始使用前，确保：

- [ ] 已设置 `GEMINI_API_KEY` 环境变量
- [ ] 配置文件中 `provider` 为 `gemini`
- [ ] 后端测试通过
- [ ] 浏览器支持 Web Audio API
- [ ] 网络连接正常

全部完成？开始享受 TTS 功能吧！🎉
