# Design Document

## Overview

本设计文档描述了可视化解读生成功能的完整实现方案。该功能在深度解读完成后，自动使用 AI 将文章内容转换为高度可视化的 HTML 网页，并在 ReadingView 中提供 Deep Insight（完整解读）和 Quick Insight（可视化解读）两种阅读模式的切换。Quick Insight 模式在桌面端提供沉浸式全屏体验。

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Web)                          │
├─────────────────────────────────────────────────────────────┤
│  ReadingView Component                                      │
│  ├── ModeToggle (Deep Insight / Quick Insight)             │
│  ├── Deep Insight View (现有深度解读)                       │
│  ├── Quick Insight View (可视化HTML iframe)                │
│  └── Fullscreen Controller (全屏控制)                       │
└─────────────────────────────────────────────────────────────┘
                          ↕ SSE/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                     Backend (Python)                        │
├─────────────────────────────────────────────────────────────┤
│  DeepSummaryWorkflow                                        │
│  ├── 步骤1-4: 生成深度解读 (现有)                           │
│  └── 步骤5: 启动可视化解读生成任务 (新增)                   │
│                                                             │
│  VisualInterpretationWorker (新增)                         │
│  ├── 读取 text2html.txt 提示词                             │
│  ├── 调用 Gemini API 生成 HTML                             │
│  ├── 验证和保存 HTML 文件                                   │
│  └── 更新文章元数据                                         │
│                                                             │
│  TaskManager                                                │
│  └── 管理任务状态和进度推送                                 │
└─────────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────────┐
│                  File System Storage                        │
├─────────────────────────────────────────────────────────────┤
│  downloads/summaries/                                       │
│  ├── {article}.md (深度解读)                                │
│  └── {article}_visual.html (可视化解读)                     │
└─────────────────────────────────────────────────────────────┘
```

### 工作流程

```
用户提交分析请求
    ↓
DeepSummaryWorkflow 执行步骤1-4
    ↓
深度解读完成 → 保存 .md 文件（可能带版本号 _v2.md）
    ↓
自动启动 VisualInterpretationWorker (后台任务)
    ↓
读取深度解读内容 + text2html.txt 提示词
    ↓
调用 Gemini API 生成可视化 HTML
    ↓
验证 HTML 格式 → 保存 _visual.html 或 _v2_visual.html 文件
    ↓
更新文章元数据 (visual_status: completed, version: 2)
    ↓
通过 SSE 推送完成通知到前端
    ↓
ReadingView 显示模式切换控件
```

**版本管理机制**:
```
FileWatcher 监测 downloads/summaries/ 目录
    ↓
检测到新的 .md 文件或版本更新
    ↓
检查是否已有对应的可视化 HTML
    ↓
如果没有或版本不匹配 → 自动启动 VisualInterpretationWorker
    ↓
生成对应版本的可视化 HTML
```

## Components and Interfaces

### 1. Backend: VisualInterpretationWorker

**文件位置**: `src/reinvent_insight/visual_worker.py`

**职责**: 负责生成可视化 HTML 的后台工作器

**类定义**:
```python
class VisualInterpretationWorker:
    def __init__(self, task_id: str, article_path: str, model_name: str, version: int = 0):
        """
        Args:
            task_id: 任务ID（用于进度推送）
            article_path: 深度解读文章的文件路径
            model_name: AI模型名称（复用现有配置）
            version: 文章版本号（默认0表示无版本）
        """
        self.task_id = task_id
        self.article_path = Path(article_path)
        self.model_name = model_name
        self.version = version
        self.summarizer = get_summarizer(model_name)
        self.text2html_prompt = self._load_text2html_prompt()
        self.max_retries = 3
    
    def _load_text2html_prompt(self) -> str:
        """加载 text2html.txt 提示词"""
        prompt_path = Path("./prompt/text2html.txt")
        return prompt_path.read_text(encoding="utf-8")
    
    async def run(self) -> Optional[str]:
        """
        执行可视化解读生成
        
        Returns:
            生成的 HTML 文件路径，失败返回 None
        """
        try:
            # 1. 读取深度解读内容
            article_content = await self._read_article_content()
            
            # 2. 构建完整提示词
            full_prompt = self._build_prompt(article_content)
            
            # 3. 调用 AI 生成 HTML
            html_content = await self._generate_html(full_prompt)
            
            # 4. 验证 HTML 格式
            if not self._validate_html(html_content):
                raise ValueError("生成的 HTML 格式无效")
            
            # 5. 保存 HTML 文件
            html_path = await self._save_html(html_content)
            
            # 6. 更新文章元数据
            await self._update_article_metadata(html_path)
            
            return str(html_path)
            
        except Exception as e:
            logger.error(f"可视化解读生成失败: {e}", exc_info=True)
            await task_manager.set_task_error(
                self.task_id, 
                "可视化解读生成失败"
            )
            return None
    
    async def _read_article_content(self) -> str:
        """读取深度解读文章内容，移除 YAML front matter"""
        content = self.article_path.read_text(encoding="utf-8")
        
        # 移除 YAML front matter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        
        return content
    
    def _build_prompt(self, article_content: str) -> str:
        """构建完整的提示词"""
        return f"{self.text2html_prompt}\n\n---\n{article_content}\n---"
    
    async def _generate_html(self, prompt: str) -> str:
        """调用 AI 生成 HTML，包含重试逻辑"""
        for attempt in range(self.max_retries):
            try:
                html = await self.summarizer.generate_content(prompt)
                if html and html.strip():
                    return html
                raise ValueError("AI 返回空内容")
            except Exception as e:
                logger.warning(
                    f"生成 HTML 失败 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数退避
        
        raise RuntimeError("达到最大重试次数")
    
    def _validate_html(self, html: str) -> bool:
        """验证 HTML 格式"""
        # 基本验证：检查必要的标签
        required_tags = ["<html", "<head", "<style", "<body"]
        return all(tag in html.lower() for tag in required_tags)
    
    async def _save_html(self, html_content: str) -> Path:
        """保存 HTML 文件，保持与深度解读相同的版本号"""
        # 生成文件名：{原文件名}_visual.html 或 {原文件名}_v2_visual.html
        base_name = self.article_path.stem
        
        # 如果原文件名包含版本号（如 article_v2），提取基础名称
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
            self.version = int(version_match.group(2))
        
        # 构建 HTML 文件名
        if self.version > 0:
            html_filename = f"{base_name}_v{self.version}_visual.html"
        else:
            html_filename = f"{base_name}_visual.html"
        
        html_path = self.article_path.parent / html_filename
        
        # 保存文件
        html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"可视化 HTML 已保存: {html_path} (版本: {self.version})")
        
        return html_path
    
    async def _update_article_metadata(self, html_path: Path):
        """更新文章元数据，记录可视化解读状态"""
        import yaml
        
        content = self.article_path.read_text(encoding="utf-8")
        
        # 解析 YAML front matter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                article_body = parts[2]
                
                # 更新元数据
                metadata["visual_interpretation"] = {
                    "status": "completed",
                    "file": html_path.name,
                    "generated_at": datetime.now().isoformat()
                }
                
                # 重新组装文件
                new_yaml = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
                new_content = f"---\n{new_yaml}---\n{article_body}"
                
                # 保存更新后的文件
                self.article_path.write_text(new_content, encoding="utf-8")
                logger.info(f"文章元数据已更新: {self.article_path}")
```

### 2. Backend: File Watcher for Auto-Generation

**文件位置**: `src/reinvent_insight/visual_watcher.py`

**职责**: 监测新的深度解读文件，自动触发可视化生成

**类定义**:
```python
class VisualInterpretationWatcher:
    """监测深度解读文件变化，自动生成可视化解读"""
    
    def __init__(self, watch_dir: Path, model_name: str):
        self.watch_dir = watch_dir
        self.model_name = model_name
        self.processed_files = set()  # 已处理的文件集合
        self._load_processed_files()
    
    def _load_processed_files(self):
        """从持久化存储加载已处理文件列表"""
        cache_file = self.watch_dir / ".visual_processed.json"
        if cache_file.exists():
            import json
            self.processed_files = set(json.loads(cache_file.read_text()))
    
    def _save_processed_files(self):
        """保存已处理文件列表"""
        cache_file = self.watch_dir / ".visual_processed.json"
        import json
        cache_file.write_text(json.dumps(list(self.processed_files)))
    
    async def start_watching(self):
        """开始监测文件变化"""
        logger.info(f"开始监测目录: {self.watch_dir}")
        
        while True:
            try:
                await self._check_new_files()
                await asyncio.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"文件监测出错: {e}", exc_info=True)
                await asyncio.sleep(60)  # 出错后等待更长时间
    
    async def _check_new_files(self):
        """检查新文件或版本更新"""
        for md_file in self.watch_dir.glob("*.md"):
            file_key = self._get_file_key(md_file)
            
            # 检查是否需要生成可视化
            if await self._should_generate_visual(md_file, file_key):
                await self._trigger_visual_generation(md_file)
                self.processed_files.add(file_key)
                self._save_processed_files()
    
    def _get_file_key(self, md_file: Path) -> str:
        """生成文件的唯一标识（包含修改时间）"""
        stat = md_file.stat()
        return f"{md_file.name}:{stat.st_mtime}"
    
    async def _should_generate_visual(self, md_file: Path, file_key: str) -> bool:
        """判断是否需要生成可视化"""
        # 1. 检查是否已处理过
        if file_key in self.processed_files:
            return False
        
        # 2. 检查对应的可视化 HTML 是否存在
        visual_html = self._get_visual_html_path(md_file)
        if not visual_html.exists():
            logger.info(f"发现新文件需要生成可视化: {md_file.name}")
            return True
        
        # 3. 检查版本是否匹配
        md_version = self._extract_version(md_file.stem)
        html_version = self._extract_version(visual_html.stem)
        
        if md_version != html_version:
            logger.info(f"版本不匹配，需要重新生成: {md_file.name} (v{md_version} vs v{html_version})")
            return True
        
        return False
    
    def _get_visual_html_path(self, md_file: Path) -> Path:
        """获取对应的可视化 HTML 文件路径"""
        base_name = md_file.stem
        
        # 移除版本号后缀
        version_match = re.match(r'^(.+)_v(\d+)$', base_name)
        if version_match:
            base_name = version_match.group(1)
            version = int(version_match.group(2))
            html_filename = f"{base_name}_v{version}_visual.html"
        else:
            html_filename = f"{base_name}_visual.html"
        
        return md_file.parent / html_filename
    
    def _extract_version(self, filename: str) -> int:
        """从文件名中提取版本号"""
        # 匹配 _v2 或 _v2_visual 格式
        version_match = re.search(r'_v(\d+)', filename)
        return int(version_match.group(1)) if version_match else 0
    
    async def _trigger_visual_generation(self, md_file: Path):
        """触发可视化生成任务"""
        try:
            # 生成任务ID
            task_id = f"visual_{md_file.stem}_{int(time.time())}"
            
            # 提取版本号
            version = self._extract_version(md_file.stem)
            
            # 创建工作器
            from .visual_worker import VisualInterpretationWorker
            worker = VisualInterpretationWorker(
                task_id=task_id,
                article_path=str(md_file),
                model_name=self.model_name,
                version=version
            )
            
            # 创建后台任务
            from .task_manager import manager as task_manager
            task_manager.create_task(task_id, worker.run())
            
            logger.info(f"已触发可视化生成任务: {task_id} for {md_file.name}")
            
        except Exception as e:
            logger.error(f"触发可视化生成失败: {e}", exc_info=True)
```

### 3. Backend: Workflow Integration

**修改文件**: `src/reinvent_insight/workflow.py`

**在 `DeepSummaryWorkflow._assemble_final_report` 方法末尾添加**:

```python
async def _assemble_final_report(self, ...):
    # ... 现有代码 ...
    
    # 在保存深度解读后，启动可视化解读生成任务
    await self._start_visual_interpretation_task(final_path, version)
    
    return final_report, final_filename, doc_hash

async def _start_visual_interpretation_task(self, article_path: str, version: int = 0):
    """启动可视化解读生成的后台任务"""
    try:
        # 生成新的任务ID
        visual_task_id = f"{self.task_id}_visual"
        
        # 创建工作器
        from .visual_worker import VisualInterpretationWorker
        worker = VisualInterpretationWorker(
            task_id=visual_task_id,
            article_path=article_path,
            model_name=self.model_name,
            version=version
        )
        
        # 创建后台任务
        task_manager.create_task(
            visual_task_id,
            worker.run()
        )
        
        logger.info(f"可视化解读生成任务已启动: {visual_task_id} (版本: {version})")
        
    except Exception as e:
        logger.error(f"启动可视化解读任务失败: {e}", exc_info=True)
        # 不影响主流程，只记录错误
```

### 4. Backend: Main Application Integration

**修改文件**: `src/reinvent_insight/main.py`

**在应用启动时启动文件监测器**:

```python
async def start_visual_watcher():
    """启动可视化解读文件监测器"""
    if not config.VISUAL_INTERPRETATION_ENABLED:
        logger.info("可视化解读功能已禁用")
        return
    
    from .visual_watcher import VisualInterpretationWatcher
    
    watcher = VisualInterpretationWatcher(
        watch_dir=config.OUTPUT_DIR,
        model_name=config.PREFERRED_MODEL
    )
    
    # 在后台运行监测器
    asyncio.create_task(watcher.start_watching())
    logger.info("可视化解读文件监测器已启动")

# 在 main() 函数中调用
async def main():
    # ... 现有代码 ...
    
    # 启动可视化监测器
    await start_visual_watcher()
    
    # ... 其他启动代码 ...
```

### 5. Backend: API Endpoints

**修改文件**: `src/reinvent_insight/api.py`

**新增端点**:

```python
@app.get("/api/article/{doc_hash}/visual")
async def get_visual_interpretation(doc_hash: str, version: Optional[int] = None):
    """
    获取文章的可视化解读 HTML（版本跟随深度解读）
    
    Args:
        doc_hash: 文档哈希
        version: 可选的版本号（如果不指定，使用默认版本）
        
    Returns:
        HTML 内容或错误信息
    """
    try:
        # 获取文章文件名（可能包含版本号）
        if version is not None:
            # 如果指定了版本，从版本列表中查找
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")
        else:
            # 使用默认版本
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise HTTPException(status_code=404, detail="文章未找到")
        
        # 构建可视化 HTML 文件路径（保持与深度解读相同的版本号）
        base_name = Path(filename).stem
        visual_filename = f"{base_name}_visual.html"
        visual_path = config.OUTPUT_DIR / visual_filename
        
        if not visual_path.exists():
            raise HTTPException(status_code=404, detail="可视化解读尚未生成")
        
        # 读取 HTML 内容
        html_content = visual_path.read_text(encoding="utf-8")
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Security-Policy": "default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化解读失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")

@app.get("/api/article/{doc_hash}/visual/status")
async def get_visual_status(doc_hash: str, version: Optional[int] = None):
    """
    获取可视化解读的生成状态（版本跟随深度解读）
    
    Args:
        doc_hash: 文档哈希
        version: 可选的版本号（如果不指定，使用默认版本）
        
    Returns:
        状态信息: {status: 'pending'|'processing'|'completed'|'failed', version: int}
    """
    try:
        # 获取文章文件名（可能包含版本号）
        if version is not None:
            # 如果指定了版本，从版本列表中查找
            versions = hash_to_versions.get(doc_hash, [])
            filename = None
            for v_filename in versions:
                if f"_v{version}.md" in v_filename or (version == 0 and "_v" not in v_filename):
                    filename = v_filename
                    break
            if not filename:
                raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")
        else:
            # 使用默认版本
            filename = hash_to_filename.get(doc_hash)
            if not filename:
                raise HTTPException(status_code=404, detail="文章未找到")
        
        # 读取文章元数据
        article_path = config.OUTPUT_DIR / filename
        content = article_path.read_text(encoding="utf-8")
        
        # 解析元数据
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                metadata = yaml.safe_load(parts[1])
                visual_info = metadata.get("visual_interpretation", {})
                
                # 提取当前文件的版本号
                import re
                version_match = re.search(r'_v(\d+)\.md$', filename)
                current_version = int(version_match.group(1)) if version_match else 0
                
                return {
                    "status": visual_info.get("status", "pending"),
                    "file": visual_info.get("file"),
                    "generated_at": visual_info.get("generated_at"),
                    "version": current_version
                }
        
        return {"status": "pending", "version": 0}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")
```

### 6. Frontend: ModeToggle Component

**文件位置**: `web/components/shared/ModeToggle/`

**文件结构**:
- `ModeToggle.js`
- `ModeToggle.html`
- `ModeToggle.css`

**ModeToggle.js**:
```javascript
export default {
    name: 'ModeToggle',
    
    props: {
        currentMode: {
            type: String,
            default: 'deep',
            validator: (value) => ['deep', 'quick'].includes(value)
        },
        visualAvailable: {
            type: Boolean,
            default: false
        },
        visualStatus: {
            type: String,
            default: 'pending',  // 'pending' | 'processing' | 'completed' | 'failed'
        }
    },
    
    emits: ['mode-change'],
    
    data() {
        return {
            modes: [
                {
                    id: 'deep',
                    label: 'Deep Insight',
                    icon: '📖',
                    description: '完整深度解读'
                },
                {
                    id: 'quick',
                    label: 'Quick Insight',
                    icon: '⚡',
                    description: '可视化解读'
                }
            ]
        };
    },
    
    computed: {
        isQuickModeDisabled() {
            return !this.visualAvailable || this.visualStatus !== 'completed';
        },
        
        quickModeTooltip() {
            if (!this.visualAvailable) {
                return '可视化解读尚未生成';
            }
            if (this.visualStatus === 'processing') {
                return '正在生成可视化解读...';
            }
            if (this.visualStatus === 'failed') {
                return '可视化解读生成失败';
            }
            return '切换到可视化解读';
        }
    },
    
    methods: {
        handleModeChange(modeId) {
            if (modeId === 'quick' && this.isQuickModeDisabled) {
                return;
            }
            this.$emit('mode-change', modeId);
        }
    }
};
```

### 7. Frontend: ReadingView Updates

**修改文件**: `web/components/views/ReadingView/ReadingView.js`

**新增状态和方法**:
```javascript
data() {
    return {
        // ... 现有字段
        displayMode: 'deep',  // 'deep' | 'quick'
        visualAvailable: false,
        visualStatus: 'pending',
        visualHtmlUrl: null,
        isFullscreen: false,
        currentVersion: 0,  // 当前查看的版本号
        availableVersions: []  // 可用的版本列表
    };
},

computed: {
    shouldShowToc() {
        return this.displayMode === 'deep';
    },
    
    shouldShowFullscreenExit() {
        return this.isFullscreen && this.displayMode === 'quick';
    }
},

methods: {
    async checkVisualStatus() {
        if (!this.currentHash) return;
        
        try {
            // 检查当前版本的可视化状态
            const response = await fetch(
                `/api/article/${this.currentHash}/visual/status?version=${this.currentVersion}`
            );
            const data = await response.json();
            
            this.visualStatus = data.status;
            this.visualAvailable = data.status === 'completed';
            
            if (this.visualAvailable) {
                // 可视化 URL 自动匹配当前版本
                this.visualHtmlUrl = `/api/article/${this.currentHash}/visual?version=${this.currentVersion}`;
            }
        } catch (error) {
            console.error('检查可视化状态失败:', error);
        }
    },
    
    async handleVersionChange(version) {
        // 当用户切换深度解读版本时，自动同步切换可视化解读版本
        this.currentVersion = version;
        
        // 重新检查当前版本的可视化状态
        await this.checkVisualStatus();
        
        // 如果当前在 Quick Insight 模式，iframe 会自动重新加载新版本
    },
    
    async handleModeChange(mode) {
        if (mode === this.displayMode) return;
        
        this.displayMode = mode;
        
        if (mode === 'quick') {
            // 切换到 Quick Insight，进入全屏
            await this.enterFullscreen();
        } else {
            // 切换到 Deep Insight，退出全屏
            await this.exitFullscreen();
        }
    },
    
    async enterFullscreen() {
        if (!document.fullscreenEnabled) {
            console.warn('浏览器不支持全屏API');
            return;
        }
        
        try {
            const container = this.$refs.readingContainer;
            await container.requestFullscreen();
            this.isFullscreen = true;
        } catch (error) {
            console.error('进入全屏失败:', error);
        }
    },
    
    async exitFullscreen() {
        if (!document.fullscreenElement) {
            this.isFullscreen = false;
            return;
        }
        
        try {
            await document.exitFullscreen();
            this.isFullscreen = false;
        } catch (error) {
            console.error('退出全屏失败:', error);
        }
    },
    
    handleFullscreenChange() {
        // 监听全屏状态变化
        this.isFullscreen = !!document.fullscreenElement;
        
        // 如果用户通过 ESC 退出全屏，保持当前模式
        if (!this.isFullscreen && this.displayMode === 'quick') {
            // 不自动切换模式，只更新状态
        }
    },
    
    handleEscapeKey(event) {
        if (event.key === 'Escape' && this.isFullscreen) {
            this.exitFullscreen();
        }
    }
},

mounted() {
    // ... 现有代码
    
    // 检查可视化状态
    this.checkVisualStatus();
    
    // 监听全屏变化
    document.addEventListener('fullscreenchange', this.handleFullscreenChange);
    
    // 监听 ESC 键
    document.addEventListener('keydown', this.handleEscapeKey);
    
    // 监听 SSE 消息，更新可视化状态
    this.eventBus.on('visual-generation-complete', () => {
        this.checkVisualStatus();
    });
},

beforeUnmount() {
    // ... 现有代码
    
    document.removeEventListener('fullscreenchange', this.handleFullscreenChange);
    document.removeEventListener('keydown', this.handleEscapeKey);
}
```

## Version Synchronization Mechanism

### 版本同步策略

**核心原则**: 可视化解读的版本完全跟随深度解读的版本，无需单独的版本切换控件。

**工作流程**:

1. **用户切换深度解读版本**
   - 用户在版本选择器中选择版本（如 v2）
   - ReadingView 触发 `handleVersionChange(2)` 方法
   - 更新 `currentVersion = 2`

2. **自动同步可视化版本**
   - 调用 `checkVisualStatus()` 检查 v2 的可视化状态
   - 如果 v2 的可视化已生成，更新 `visualHtmlUrl`
   - 如果当前在 Quick Insight 模式，iframe 自动加载 v2 的可视化 HTML

3. **文件名对应关系**
   ```
   深度解读版本          可视化解读版本
   article.md      →    article_visual.html
   article_v2.md   →    article_v2_visual.html
   article_v3.md   →    article_v3_visual.html
   ```

4. **用户体验**
   - 用户只需操作一个版本选择器
   - 深度解读和可视化解读始终保持版本一致
   - 切换版本时，两种模式的内容同步更新

**优势**:
- 简化用户界面，避免两个版本选择器造成混淆
- 保证内容一致性，深度解读和可视化解读始终对应
- 降低实现复杂度，复用现有的版本管理逻辑

## Data Models

### Article Metadata Extension

在文章的 YAML front matter 中添加可视化解读信息：

```yaml
---
title_en: "Original English Title"
title_cn: "中文标题"
upload_date: "2024-01-01"
video_url: "https://..."
visual_interpretation:
  status: "completed"  # pending | processing | completed | failed
  file: "article_visual.html"
  generated_at: "2024-01-01T12:00:00"
---
```

### Visual Generation Task State

```python
@dataclass
class VisualTaskState:
    task_id: str
    article_path: str
    status: str  # "pending" | "processing" | "completed" | "failed"
    progress: int  # 0-100
    html_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

## Error Handling

### Backend Error Scenarios

1. **AI API 调用失败**
   - 自动重试 3 次，使用指数退避
   - 记录详细错误日志
   - 更新任务状态为 failed
   - 不影响深度解读的正常使用

2. **HTML 验证失败**
   - 记录生成的 HTML 内容用于调试
   - 标记任务为失败
   - 提供重新生成选项

3. **文件保存失败**
   - 检查磁盘空间
   - 检查文件权限
   - 记录错误并通知用户

### Frontend Error Scenarios

1. **可视化 HTML 加载失败**
   - 显示友好的错误提示
   - 提供"重新加载"按钮
   - 允许切换回 Deep Insight 模式

2. **全屏 API 不可用**
   - 检测浏览器支持
   - 降级为普通显示模式
   - 显示提示信息

3. **iframe 安全策略限制**
   - 配置正确的 CSP 头
   - 使用 sandbox 属性隔离
   - 处理跨域问题

## Testing Strategy

### Backend Testing

**单元测试** (可选):
- `VisualInterpretationWorker._load_text2html_prompt()`
- `VisualInterpretationWorker._validate_html()`
- `VisualInterpretationWorker._build_prompt()`

**集成测试** (可选):
- 完整的可视化生成流程
- API 端点响应
- 元数据更新逻辑

### Frontend Testing

**手动测试** (必需):
1. 模式切换功能
2. 全屏进入/退出
3. ESC 键退出全屏
4. 可视化 HTML 渲染
5. 移动端响应式布局
6. 不同浏览器兼容性

### End-to-End Testing

**测试场景**:
1. 提交文章分析 → 深度解读完成 → 可视化解读自动生成 → 前端显示切换控件
2. 切换到 Quick Insight → 自动全屏 → 显示可视化 HTML
3. 按 ESC 键 → 退出全屏 → 保持 Quick Insight 模式
4. 切换到 Deep Insight → 自动退出全屏 → 显示原文

## Performance Considerations

### Backend Optimization

1. **异步生成**: 可视化生成不阻塞深度解读完成
2. **任务队列**: 使用现有的 TaskManager 管理并发
3. **缓存策略**: 生成的 HTML 文件永久缓存，除非重新生成
4. **压缩**: 考虑对 HTML 文件进行 gzip 压缩

### Frontend Optimization

1. **懒加载**: 仅在切换到 Quick Insight 时加载 HTML
2. **iframe 优化**: 使用 `loading="lazy"` 属性
3. **全屏性能**: 使用 CSS transform 而非 position 变化
4. **内存管理**: 切换模式时正确清理 iframe 资源

## Security Considerations

### Content Security Policy

```http
Content-Security-Policy: 
    default-src 'self'; 
    style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; 
    font-src 'self' https://fonts.gstatic.com; 
    script-src 'self'; 
    frame-src 'self';
```

### iframe Sandbox

```html
<iframe 
    sandbox="allow-same-origin allow-scripts" 
    src="/api/article/{hash}/visual"
></iframe>
```

### XSS Prevention

1. 后端验证生成的 HTML 不包含恶意脚本
2. 使用 iframe 隔离可视化内容
3. 设置严格的 CSP 策略

## Deployment Considerations

### File Storage

```
downloads/summaries/
├── article1.md
├── article1_visual.html
├── article1_v2.md
├── article1_v2_visual.html
├── article2.md
├── article2_visual.html
├── .visual_processed.json  # 已处理文件缓存
└── ...
```

**版本对应关系**:
- `article.md` → `article_visual.html` (版本 0)
- `article_v2.md` → `article_v2_visual.html` (版本 2)
- `article_v3.md` → `article_v3_visual.html` (版本 3)

### Configuration

在 `config.py` 中添加：

```python
# 可视化解读配置
VISUAL_INTERPRETATION_ENABLED = os.getenv("VISUAL_INTERPRETATION_ENABLED", "true").lower() == "true"
VISUAL_HTML_DIR = OUTPUT_DIR  # 与深度解读同目录
TEXT2HTML_PROMPT_PATH = PROJECT_ROOT / "prompt" / "text2html.txt"
```

### Monitoring

1. 记录可视化生成的成功率
2. 监控生成时间
3. 跟踪 API 调用次数和成本
4. 记录用户模式切换行为

## Future Enhancements

### Phase 2

1. **批量生成**: 为现有文章批量生成可视化解读
2. **样式定制**: 允许用户选择不同的可视化主题
3. **导出功能**: 支持导出可视化 HTML 为独立文件

### Phase 3

1. **交互式元素**: 在可视化 HTML 中添加交互式图表
2. **多语言支持**: 生成多语言版本的可视化解读
3. **A/B 测试**: 测试不同的可视化风格效果

### Phase 4

1. **实时预览**: 在生成过程中提供实时预览
2. **协作编辑**: 允许用户手动调整可视化内容
3. **模板库**: 提供多种可视化模板供选择
