"""Ultra DeepInsight routes"""

import logging
import uuid
import re
import tempfile
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks

from reinvent_insight.core import config
from reinvent_insight.api.routes.auth import verify_token
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
    hash_to_versions,
)
from reinvent_insight.services.document.metadata_service import (
    parse_metadata_from_md,
    extract_text_from_markdown,
    count_chinese_words,
)
from reinvent_insight.services.analysis.task_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/article", tags=["ultra_deep"])


def count_toc_chapters(content: str) -> int:
    """计算文档中的章节数量
    
    支持多种格式：
    1. 目录中的 `- [xxx](...)` 链接
    2. 正文中的编号章节标题 `## 1.` 或 `### 1.`
    """
    lines = content.splitlines()
    chapter_count = 0
    in_toc = False
    
    # 方法 1: 统计目录中的链接
    for line in lines:
        stripped = line.strip()
        if '目录' in stripped or 'Table of Contents' in stripped:
            in_toc = True
            continue
        if in_toc:
            if stripped.startswith('##') or stripped.startswith('###'):
                # 检查是否是新章节开始（非目录类标题）
                if '目录' not in stripped and 'Table of Contents' not in stripped:
                    in_toc = False
            elif stripped.startswith('- ['):
                chapter_count += 1
    
    # 如果从目录找到了章节，直接返回
    if chapter_count > 0:
        return chapter_count
    
    # 方法 2: 统计编号章节标题（如 ### 1. xxx 或 ## 1. xxx）
    import re
    chapter_pattern = re.compile(r'^#{2,3}\s+(\d+)\.\s+')
    seen_numbers = set()
    
    for line in lines:
        match = chapter_pattern.match(line)
        if match:
            num = int(match.group(1))
            seen_numbers.add(num)
    
    if seen_numbers:
        return len(seen_numbers)
    
    # 方法 3: 统计所有 ## 标题（排除目录、引言、结语等）
    excluded_titles = {'目录', '主要目录', 'table of contents', '引言', '结语', '结论', '总结'}
    h2_count = 0
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith('## '):
            title = stripped[3:].strip()
            if title not in excluded_titles:
                h2_count += 1
    
    return h2_count


@router.get("/{doc_hash}/ultra-deep/status")
async def get_ultra_deep_status(doc_hash: str):
    """
    检查Ultra DeepInsight版本的状态
    
    Args:
        doc_hash: 文档哈希
        
    Returns:
        Ultra版本状态信息
    """
    try:
        # 首先检查任务队列中是否有Ultra生成任务
        from reinvent_insight.services.analysis.worker_pool import worker_pool
        
        # 检查正在执行的任务(processing_tasks)
        try:
            for task_id, task in worker_pool.processing_tasks.items():
                if hasattr(task, 'task_type') and task.task_type == 'ultra_deep_insight':
                    if hasattr(task, 'doc_hash') and task.doc_hash == doc_hash:
                        return {
                            "exists": False,
                            "status": "generating",
                            "task_info": {
                                "task_id": task_id,
                                "created_at": getattr(task, 'created_at', None),
                                "current_stage": "正在生成中..."
                            },
                            "version": None,
                            "word_count": None
                        }
        except Exception as proc_err:
            logger.warning(f"检查正在执行的任务时出错: {proc_err}")
        
        # 检查排队任务(使用 queue._queue 访问内部队列)
        try:
            queue_items = list(worker_pool.queue._queue) if hasattr(worker_pool.queue, '_queue') else []
            for queued_task in queue_items:
                # PriorityQueue 中的元素可能是元组 (priority, task) 或直接是 task
                task = queued_task[1] if isinstance(queued_task, tuple) else queued_task
                if hasattr(task, 'task_type') and task.task_type == 'ultra_deep_insight':
                    if hasattr(task, 'doc_hash') and task.doc_hash == doc_hash:
                        return {
                            "exists": False,
                            "status": "generating",
                            "task_info": {
                                "task_id": getattr(task, 'task_id', None),
                                "created_at": getattr(task, 'created_at', None),
                                "queue_position": getattr(task, 'queue_position', 0),
                                "current_stage": "排队中..."
                            },
                            "version": None,
                            "word_count": None
                        }
        except Exception as queue_err:
            logger.warning(f"检查队列任务时出错: {queue_err}")
        
        # 检查进行中的任务
        for task_id, task_state in manager.tasks.items():
            if (hasattr(task_state, 'is_ultra_deep') and 
                task_state.is_ultra_deep and
                hasattr(task_state, 'doc_hash') and 
                task_state.doc_hash == doc_hash and
                task_state.status in ['queued', 'running', 'processing']):
                
                progress = getattr(task_state, 'progress', 0)
                current_stage = getattr(task_state, 'current_stage', 'Ultra生成中...')
                
                return {
                    "exists": False,
                    "status": "generating",
                    "task_info": {
                        "task_id": task_id,
                        "created_at": getattr(task_state, 'created_at', None),
                        "progress": progress,
                        "current_stage": current_stage
                    },
                    "version": None,
                    "word_count": None
                }
        
        # 查找该doc_hash的所有版本
        versions = hash_to_versions.get(doc_hash, [])
        
        if not versions:
            return {
                "exists": False,
                "status": "not_exists",
                "version": None,
                "filename": None,
                "word_count": None,
                "generated_at": None
            }
        
        # 遍历所有版本，查找Ultra版本
        for filename in versions:
            try:
                file_path = config.OUTPUT_DIR / filename
                if not file_path.exists():
                    continue
                    
                content = file_path.read_text(encoding="utf-8")
                metadata = parse_metadata_from_md(content)
                
                # 检查是否为Ultra版本
                if metadata.get("is_ultra_deep", False):
                    # 提取版本号
                    version_match = re.search(r'_v(\d+)\.md$', filename)
                    version_num = int(version_match.group(1)) if version_match else 0
                    
                    # 计算字数
                    pure_text = extract_text_from_markdown(content)
                    word_count = count_chinese_words(pure_text)
                    
                    return {
                        "exists": True,
                        "status": "completed",
                        "version": version_num,
                        "filename": filename,
                        "word_count": word_count,
                        "chapter_count": metadata.get("chapter_count"),
                        "generated_at": metadata.get("created_at")
                    }
            except Exception as e:
                logger.warning(f"解析文件 {filename} 时出错: {e}")
                continue
        
        # 没有找到带 is_ultra_deep 标记的版本
        # 检查默认版本的章节数，如果超过15章则视为Ultra
        default_filename = hash_to_filename.get(doc_hash)
        if default_filename:
            try:
                default_file_path = config.OUTPUT_DIR / default_filename
                if default_file_path.exists():
                    default_content = default_file_path.read_text(encoding="utf-8")
                    chapter_count = count_toc_chapters(default_content)
                    
                    if chapter_count > 15:
                        # 章节数超过15，视为已是Ultra级别内容
                        version_match = re.search(r'_v(\d+)\.md$', default_filename)
                        version_num = int(version_match.group(1)) if version_match else 0
                        
                        pure_text = extract_text_from_markdown(default_content)
                        word_count = count_chinese_words(pure_text)
                        
                        return {
                            "exists": True,
                            "status": "completed",
                            "version": version_num,
                            "filename": default_filename,
                            "word_count": word_count,
                            "chapter_count": chapter_count,
                            "generated_at": parse_metadata_from_md(default_content).get("created_at"),
                            "reason": "章节数超过15章，已是深度内容"
                        }
            except Exception as e:
                logger.warning(f"检查默认文件章节数时出错: {e}")
        
        return {
            "exists": False,
            "status": "not_exists",
            "version": None,
            "filename": None,
            "word_count": None,
            "generated_at": None
        }
        
    except Exception as e:
        logger.error(f"获取Ultra状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器错误")


# 存储校对任务状态
proofreading_tasks = {}


@router.get("/{doc_hash}/proofread/status")
async def get_proofread_status(doc_hash: str):
    """
    获取文章校对状态
    
    Args:
        doc_hash: 文档哈希
        
    Returns:
        校对状态信息
    """
    task_info = proofreading_tasks.get(doc_hash)
    
    if not task_info:
        return {
            "status": "idle",
            "can_proofread": True,
            "message": None
        }
    
    return task_info


@router.post("/{doc_hash}/proofread")
async def trigger_proofread(
    doc_hash: str, 
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """
    触发文章后校验
    
    对已存在的文章进行全局校对优化，
    将碎片化章节重构为逻辑连贯的核心板块。
    
    Args:
        doc_hash: 文档哈希
        authorization: 认证令牌
        
    Returns:
        校对任务状态
    """
    verify_token(authorization)
    
    try:
        # 1. 检查是否已有进行中的校对任务
        if doc_hash in proofreading_tasks:
            status = proofreading_tasks[doc_hash].get("status")
            if status == "processing":
                raise HTTPException(
                    status_code=409,
                    detail="该文章正在校对中，请稍后重试"
                )
        
        # 2. 检查文档是否存在
        default_filename = hash_to_filename.get(doc_hash)
        if not default_filename:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        file_path = config.OUTPUT_DIR / default_filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文档文件不存在")
        
        # 3. 读取文档内容并检查章节数
        content = file_path.read_text(encoding="utf-8")
        chapter_count = count_toc_chapters(content)
        
        if chapter_count < 6:
            raise HTTPException(
                status_code=400,
                detail=f"该文章仅有 {chapter_count} 个章节，不需要校对"
            )
        
        # 4. 标记任务开始
        task_id = str(uuid.uuid4())
        proofreading_tasks[doc_hash] = {
            "status": "processing",
            "task_id": task_id,
            "can_proofread": False,
            "message": "校对进行中...",
            "chapter_count": chapter_count
        }
        
        # 5. 在后台执行校对任务
        background_tasks.add_task(
            run_proofreading_task,
            doc_hash=doc_hash,
            file_path=file_path,
            content=content,
            task_id=task_id
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "校对任务已启动",
            "chapter_count": chapter_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发校对失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


async def run_proofreading_task(
    doc_hash: str,
    file_path: Path,
    content: str,
    task_id: str
):
    """
    执行校对任务的后台函数
    
    Args:
        doc_hash: 文档哈希
        file_path: 文档文件路径
        content: 文档内容
        task_id: 任务ID
    """
    temp_dir = None
    
    try:
        from reinvent_insight.services.analysis.proofreader import ArticleProofreader
        from reinvent_insight.services.document.metadata_service import parse_metadata_from_md
        
        # 0. 从元数据中提取 video_url 和 source_type
        metadata = parse_metadata_from_md(content)
        video_url = metadata.get("video_url", "")
        # 判断来源类型
        if video_url and ("youtube.com" in video_url or "youtu.be" in video_url):
            source_type = "youtube"
        elif video_url and video_url.endswith(".pdf"):
            source_type = "pdf"
        else:
            source_type = "text"
        
        # 1. 创建临时目录
        temp_dir = Path(tempfile.mkdtemp(prefix="proofread_"))
        logger.info(f"校对任务 {task_id} - 创建临时目录: {temp_dir}")
        
        # 2. 将文章按章节拆分保存到临时目录
        chapters = split_article_to_temp_files(content, temp_dir)
        logger.info(f"校对任务 {task_id} - 拆分为 {len(chapters)} 个章节")
        
        if len(chapters) < 6:
            proofreading_tasks[doc_hash] = {
                "status": "failed",
                "can_proofread": True,
                "message": f"章节数不足 ({len(chapters)} 章)，无需校对"
            }
            return
        
        # 3. 执行校对（传入 video_url 和 source_type）
        proofreader = ArticleProofreader(
            task_id=task_id,
            task_dir=str(temp_dir),
            video_url=video_url,
            source_type=source_type
        )
        success = await proofreader.run()
        
        if not success:
            proofreading_tasks[doc_hash] = {
                "status": "failed",
                "can_proofread": True,
                "message": "校对失败，请稍后重试"
            }
            return
        
        # 4. 合并校对后的章节并覆盖原文件
        new_content = merge_proofread_chapters(temp_dir, content)
        
        # 5. 写回原文件
        file_path.write_text(new_content, encoding="utf-8")
        logger.info(f"校对任务 {task_id} - 已更新文件: {file_path}")
        
        # 6. 统计新章节数
        new_chapter_count = count_toc_chapters(new_content)
        
        proofreading_tasks[doc_hash] = {
            "status": "completed",
            "can_proofread": True,
            "message": f"校对完成，从 {len(chapters)} 章优化为 {new_chapter_count} 章"
        }
        
    except Exception as e:
        logger.error(f"校对任务 {task_id} 失败: {e}", exc_info=True)
        proofreading_tasks[doc_hash] = {
            "status": "failed",
            "can_proofread": True,
            "message": f"校对失败: {str(e)}"
        }
    finally:
        # 保存诊断文件到永久位置
        if temp_dir and temp_dir.exists():
            debug_src = temp_dir / "proofreading_debug"
            if debug_src.exists():
                debug_dst = config.OUTPUT_DIR / "proofreading_debug" / doc_hash
                debug_dst.mkdir(parents=True, exist_ok=True)
                for f in debug_src.glob("*"):
                    shutil.copy2(f, debug_dst / f.name)
                logger.info(f"校对任务 {task_id} - 诊断文件已保存到 {debug_dst}")
            
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"校对任务 {task_id} - 清理临时目录")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")


def split_article_to_temp_files(content: str, temp_dir: Path) -> list:
    """
    将文章内容按章节拆分保存到临时文件
    
    Args:
        content: 文章内容
        temp_dir: 临时目录
        
    Returns:
        章节列表
    """
    chapters = []
    
    # 提取文章正文部分（跳过元数据）
    lines = content.split('\n')
    in_metadata = False
    body_lines = []
    metadata_count = 0
    
    for line in lines:
        if line.strip() == '---':
            metadata_count += 1
            if metadata_count <= 2:  # 跳过 YAML 元数据块
                in_metadata = not in_metadata
                continue
        if in_metadata:
            continue
        body_lines.append(line)
    
    body_content = '\n'.join(body_lines)
    
    # 按 ## 或 ### 章节标题拆分（兼容两种格式）
    # 匹配 ## 或 ### 开头的行
    parts = re.split(r'\n(?=##+ )', body_content)
    
    chapter_index = 0
    excluded_titles = {'主要目录', '目录', 'table of contents', '引言', '导读'}
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # 检查是否是有效章节（以 ## 或 ### 开头）
        if not (part.startswith('## ') or part.startswith('### ')):
            continue
        
        # 提取标题并跳过目录/引言等
        first_line = part.split('\n')[0].lower()
        # 去掉 ## 或 ### 前缀
        title_text = re.sub(r'^#{2,3}\s*', '', first_line).strip()
        
        # 跳过目录和引言
        should_skip = False
        for excluded in excluded_titles:
            if excluded in title_text:
                should_skip = True
                break
        if should_skip:
            continue
        
        chapter_index += 1
        chapters.append({
            "index": chapter_index,
            "content": part
        })
        
        # 保存到临时文件
        chapter_file = temp_dir / f"chapter_{chapter_index}.md"
        chapter_file.write_text(part, encoding="utf-8")
    
    # 保存原始大纲（用于参考）
    outline_file = temp_dir / "outline.md"
    outline_content = "# 原始大纲\n\n"
    for ch in chapters:
        first_line = ch["content"].split('\n')[0]
        outline_content += f"- {first_line}\n"
    outline_file.write_text(outline_content, encoding="utf-8")
    
    return chapters


def merge_proofread_chapters(temp_dir: Path, original_content: str) -> str:
    """
    合并校对后的章节，保留原始元数据和目录结构
    
    Args:
        temp_dir: 临时目录
        original_content: 原始文章内容
        
    Returns:
        合并后的完整文章
    """
    # 1. 提取原始元数据部分
    lines = original_content.split('\n')
    header_lines = []
    in_metadata = False
    metadata_ended = False
    
    for line in lines:
        if line.strip() == '---' and not metadata_ended:
            in_metadata = not in_metadata
            header_lines.append(line)
            if not in_metadata:
                metadata_ended = True
            continue
        if in_metadata or not metadata_ended:
            header_lines.append(line)
            continue
        # 元数据结束后，跳过到第一个 ## 之前的内容（如标题、引言）
        if line.strip().startswith('## '):
            break
        header_lines.append(line)
    
    header = '\n'.join(header_lines)
    
    # 2. 读取校对后的章节
    chapter_files = sorted(
        temp_dir.glob("chapter_*.md"),
        key=lambda f: int(re.search(r'chapter_(\d+)', f.name).group(1))
    )
    
    chapters_content = []
    for chapter_file in chapter_files:
        chapter_content = chapter_file.read_text(encoding="utf-8")
        chapters_content.append(chapter_content)
    
    # 3. 生成新的目录
    toc_lines = ["### 主要目录\n"]
    for i, ch_content in enumerate(chapters_content, 1):
        first_line = ch_content.split('\n')[0]
        # 提取标题文本
        title_match = re.match(r'## \d+\.\s*(.+)', first_line)
        if title_match:
            title = title_match.group(1).strip()
            anchor = f"section-{i}"
            toc_lines.append(f"- [{i}. {title}](#{anchor})")
    toc_lines.append("")  # 空行
    toc = '\n'.join(toc_lines)
    
    # 4. 组合最终内容
    final_content = header.rstrip() + "\n\n" + toc + "\n" + "\n\n".join(chapters_content)
    
    # 5. 添加校对标记到元数据（如果有）
    if '---' in final_content:
        final_content = re.sub(
            r'(---\n)',
            r'\1proofread: true\n',
            final_content,
            count=1
        )
    
    return final_content


@router.post("/{doc_hash}/ultra-deep")
async def trigger_ultra_deep_generation(doc_hash: str, authorization: str = Header(None)):
    """
    触发Ultra DeepInsight生成任务
    
    Args:
        doc_hash: 文档哈希
        authorization: 认证令牌
        
    Returns:
        任务创建结果
    """
    verify_token(authorization)
    
    try:
        # 1. 检查文档是否存在
        default_filename = hash_to_filename.get(doc_hash)
        if not default_filename:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        # 2. 读取标准版本的内容和元数据
        file_path = config.OUTPUT_DIR / default_filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文档文件不存在")
        
        content = file_path.read_text(encoding="utf-8")
        metadata = parse_metadata_from_md(content)
        
        # 3. 检查章节数是否符合要求(不超过15章)
        chapter_count = count_toc_chapters(content)
        
        if chapter_count > 15:
            raise HTTPException(
                status_code=400, 
                detail=f"该文章已有{chapter_count}个章节，已是深度内容，不需要生成Ultra DeepInsight"
            )
        
        # 4. 检查是否已存在Ultra版本
        ultra_status = await get_ultra_deep_status(doc_hash)
        if ultra_status["exists"]:
            raise HTTPException(
                status_code=400,
                detail="该文章已存在Ultra DeepInsight版本"
            )
        
        # 5. 获取原始视频URL或文档路径
        video_url = metadata.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="无法获取原始内容来源")
        
        # 6. 确定新版本号
        versions = hash_to_versions.get(doc_hash, [])
        version_numbers = []
        for v_filename in versions:
            version_match = re.search(r'_v(\d+)\.md$', v_filename)
            if version_match:
                version_numbers.append(int(version_match.group(1)))
            elif "_v" not in v_filename:
                version_numbers.append(0)
        
        next_version = max(version_numbers) + 1 if version_numbers else 1
        
        # 7. 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 8. 在manager中创建占位状态
        from reinvent_insight.services.analysis.task_manager import TaskState
        state = TaskState(task_id=task_id, status="queued", task=None)
        state.doc_hash = doc_hash  # 添加doc_hash用于状态查询
        state.is_ultra_deep = True  # 标记为Ultra任务
        manager.tasks[task_id] = state
        
        # 9. 添加到任务队列
        from reinvent_insight.services.analysis.worker_pool import worker_pool, TaskPriority
        
        success = await worker_pool.add_task(
            task_id=task_id,
            task_type="ultra_deep_insight",
            url_or_path=video_url,
            priority=TaskPriority.LOW,
            # 额外参数
            doc_hash=doc_hash,
            base_version=metadata.get("version", 0),
            next_version=next_version
        )
        
        if not success:
            del manager.tasks[task_id]
            raise HTTPException(
                status_code=503,
                detail=f"任务队列已满，请稍后重试"
            )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Ultra DeepInsight生成任务已启动",
            "estimated_time": "15-20分钟",
            "target_version": next_version,
            "current_chapter_count": chapter_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发Ultra生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")
