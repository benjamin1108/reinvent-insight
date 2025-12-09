"""
TTS 预生成服务

负责管理 TTS 预生成任务队列和 Worker 处理逻辑。
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from reinvent_insight.core.config import (
    TTS_TEXT_DIR,
    TTS_QUEUE_MAX_SIZE,
    TTS_WORKER_DELAY,
    TTS_MAX_RETRIES,
    TTS_TASK_TIMEOUT,
    TTS_PREPROCESSING_VERSION,
    OUTPUT_DIR
)
from .tts_text_preprocessor import TTSTextPreprocessor
from .tts_service import TTSService
from .audio_cache import AudioCache
from reinvent_insight.infrastructure.audio.audio_utils import assemble_wav, decode_base64_pcm, calculate_audio_duration

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TTSTask:
    """TTS 预生成任务"""
    task_id: str                  # 任务 ID
    article_hash: str             # 文章哈希
    source_file: str              # 源文件名
    status: TaskStatus            # 任务状态
    created_at: str               # 创建时间
    started_at: Optional[str] = None      # 开始时间
    completed_at: Optional[str] = None    # 完成时间
    retry_count: int = 0                   # 重试次数
    error_message: Optional[str] = None    # 错误信息
    audio_hash: Optional[str] = None       # 生成的音频哈希
    partial_audio_hash: Optional[str] = None  # 部分音频哈希（渐进式）
    chunks_generated: int = 0              # 已生成的片段数
    total_chunks: int = 0                  # 总片段数


class TTSPregenerationService:
    """TTS 预生成服务
    
    功能：
    1. 管理任务队列
    2. Worker 处理任务
    3. 任务状态持久化
    4. 错误处理和重试
    """
    
    def __init__(
        self,
        tts_service: TTSService,
        audio_cache: AudioCache,
        text_preprocessor: TTSTextPreprocessor
    ):
        """初始化预生成服务
        
        Args:
            tts_service: TTS 服务实例
            audio_cache: 音频缓存实例
            text_preprocessor: 文本预处理器实例
        """
        self.tts_service = tts_service
        self.audio_cache = audio_cache
        self.text_preprocessor = text_preprocessor
        
        # 任务队列
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=TTS_QUEUE_MAX_SIZE)
        
        # 任务状态（内存 + 持久化）
        self.tasks: Dict[str, TTSTask] = {}
        self.tasks_file = Path(TTS_TEXT_DIR) / "tasks.json"
        
        # Worker 运行状态
        self.is_running = False
        self.worker_task: Optional[asyncio.Task] = None
        
        # 加载持久化任务
        self._load_tasks()
        
        logger.info("TTS 预生成服务初始化完成")
    
    def _load_tasks(self) -> None:
        """从文件加载任务状态"""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = {}
                    for k, v in data.items():
                        # 将字符串状态转换为枚举
                        if isinstance(v.get('status'), str):
                            v['status'] = TaskStatus(v['status'])
                        self.tasks[k] = TTSTask(**v)
                logger.info(f"加载了 {len(self.tasks)} 个任务")
            except Exception as e:
                logger.error(f"加载任务失败: {e}")
                self.tasks = {}
        else:
            self.tasks = {}
    
    def _save_tasks(self) -> None:
        """保存任务状态到文件"""
        try:
            # 确保目录存在
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为可序列化格式
            data = {}
            for k, v in self.tasks.items():
                task_dict = asdict(v)
                # 转换枚举为字符串
                task_dict['status'] = v.status.value
                data[k] = task_dict
            
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
    
    async def add_task(
        self,
        article_hash: str,
        source_file: str
    ) -> Optional[str]:
        """添加预生成任务
        
        Args:
            article_hash: 文章哈希
            source_file: 源文件名
            
        Returns:
            任务 ID，失败返回 None
        """
        # 检查是否已经有音频缓存
        existing_audio = self.audio_cache.find_by_article_hash(article_hash)
        if existing_audio:
            logger.info(f"文章 {article_hash} 已有音频缓存，跳过")
            return None
        
        # 检查是否已有任务
        for task in self.tasks.values():
            if task.article_hash == article_hash and task.status in [
                TaskStatus.PENDING,
                TaskStatus.PROCESSING
            ]:
                logger.info(f"文章 {article_hash} 已有进行中的任务，跳过")
                return task.task_id
        
        # 创建新任务
        task_id = f"tts_{article_hash}_{int(time.time())}"
        task = TTSTask(
            task_id=task_id,
            article_hash=article_hash,
            source_file=source_file,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        # 加入队列
        try:
            await self.queue.put(task)
            logger.info(f"任务已加入队列: {task_id}, 队列长度: {self.queue.qsize()}")
            return task_id
        except asyncio.QueueFull:
            logger.error(f"任务队列已满，无法添加任务: {task_id}")
            task.status = TaskStatus.FAILED
            task.error_message = "队列已满"
            self._save_tasks()
            return None
    
    async def process_task(self, task: TTSTask) -> bool:
        """处理单个任务
        
        Args:
            task: 任务对象
            
        Returns:
            是否成功
        """
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now().isoformat()
        self._save_tasks()
        
        try:
            logger.info(f"开始处理任务: {task.task_id}")
            
            # 1. 读取源文件
            source_path = OUTPUT_DIR / task.source_file
            if not source_path.exists():
                raise FileNotFoundError(f"源文件不存在: {source_path}")
            
            with open(source_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # 2. 文本预处理
            logger.info(f"任务 {task.task_id}: 开始文本预处理")
            preprocess_result = self.text_preprocessor.preprocess(markdown_content)
            
            if not preprocess_result:
                raise ValueError("文本预处理失败")
            
            # 保存预处理文本
            text_file = self.text_preprocessor.save_to_file(
                preprocess_result,
                TTS_TEXT_DIR
            )
            
            if not text_file:
                raise ValueError("保存预处理文本失败")
            
            logger.info(
                f"任务 {task.task_id}: 文本预处理完成, "
                f"原文 {preprocess_result.original_length} 字符 -> "
                f"处理后 {preprocess_result.processed_length} 字符"
            )
            
            # 3. 生成音频
            logger.info(f"任务 {task.task_id}: 开始生成音频")
            audio_chunks = []
            chunk_count = 0
            
            # 从配置获取默认音色和语言
            default_voice = getattr(self.tts_service.config, 'tts_default_voice', 'Kai')
            default_language = getattr(self.tts_service.config, 'tts_default_language', 'Chinese')
            
            # 计算音频哈希（用于部分和完整缓存）
            audio_hash = self.tts_service.calculate_hash(
                preprocess_result.text,
                default_voice,
                default_language
            )
            
            # 渐进式缓存：每 10 个片段保存一次部分音频（约 6-10 秒音频）
            PARTIAL_SAVE_INTERVAL = 10
            
            async for chunk in self.tts_service.generate_audio_stream(
                preprocess_result.text,
                voice=None,  # 使用配置默认值
                language=None,  # 使用配置默认值
                skip_code_blocks=True
            ):
                # 解码 Base64
                pcm_data = decode_base64_pcm(chunk)
                audio_chunks.append(pcm_data)
                chunk_count += 1
                
                # 更新任务进度
                task.chunks_generated = chunk_count
                
                # 每 N 个片段保存一次部分音频
                if chunk_count % PARTIAL_SAVE_INTERVAL == 0:
                    try:
                        partial_wav = assemble_wav(audio_chunks, sample_rate=24000)
                        partial_duration = calculate_audio_duration(len(partial_wav) - 44)
                        
                        # 使用 article_hash + "_partial" 作为部分音频的 hash
                        partial_hash = f"{audio_hash}_partial"
                        
                        # 缓存部分音频
                        self.audio_cache.put(
                            audio_hash=partial_hash,
                            audio_data=partial_wav,
                            text_hash=preprocess_result.article_hash,
                            voice=default_voice,
                            language=default_language,
                            duration=partial_duration,
                            article_hash=preprocess_result.article_hash,
                            source_file=task.source_file,
                            preprocessing_version=TTS_PREPROCESSING_VERSION,
                            is_pregenerated=False  # 标记为部分音频
                        )
                        
                        task.partial_audio_hash = partial_hash
                        self._save_tasks()
                        
                        logger.info(
                            f"任务 {task.task_id}: 保存部分音频 {chunk_count} 片段, "
                            f"时长 {partial_duration:.2f}s"
                        )
                    except Exception as e:
                        logger.warning(f"保存部分音频失败: {e}")
                
                if chunk_count % 10 == 0:
                    logger.debug(f"任务 {task.task_id}: 已生成 {chunk_count} 个音频块")
            
            # 记录总片段数
            task.total_chunks = chunk_count
            logger.info(f"任务 {task.task_id}: 音频流生成完成，共 {chunk_count} 块")
            
            # 4. 组装 WAV 文件
            wav_data = assemble_wav(audio_chunks, sample_rate=24000)
            duration = calculate_audio_duration(len(wav_data) - 44)  # 减去 WAV 头
            
            logger.info(
                f"任务 {task.task_id}: WAV 文件组装完成, "
                f"大小 {len(wav_data) / 1024:.2f}KB, "
                f"时长 {duration:.2f}s"
            )
            
            # 5. 缓存完整音频（替换部分缓存）
            self.audio_cache.put(
                audio_hash=audio_hash,
                audio_data=wav_data,
                text_hash=preprocess_result.article_hash,
                voice=default_voice,
                language=default_language,
                duration=duration,
                article_hash=preprocess_result.article_hash,
                source_file=task.source_file,
                preprocessing_version=TTS_PREPROCESSING_VERSION,
                is_pregenerated=True
            )
            
            # 删除部分缓存（如果存在）
            if task.partial_audio_hash:
                try:
                    partial_path = self.audio_cache.cache_dir / f"{task.partial_audio_hash}.wav"
                    if partial_path.exists():
                        partial_path.unlink()
                        logger.info(f"已删除部分缓存: {task.partial_audio_hash}")
                except Exception as e:
                    logger.warning(f"删除部分缓存失败: {e}")
            
            # 6. 更新任务状态
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.audio_hash = audio_hash
            self._save_tasks()
            
            logger.info(f"任务完成: {task.task_id}, 音频哈希: {audio_hash}")
            return True
            
        except Exception as e:
            logger.error(f"任务处理失败: {task.task_id}, 错误: {e}", exc_info=True)
            
            task.retry_count += 1
            task.error_message = str(e)
            
            if task.retry_count < TTS_MAX_RETRIES:
                # 重试
                task.status = TaskStatus.PENDING
                logger.info(f"任务 {task.task_id} 将重试，第 {task.retry_count} 次")
                
                # 指数退避
                await asyncio.sleep(2 ** task.retry_count)
                await self.queue.put(task)
            else:
                # 超过重试次数
                task.status = TaskStatus.FAILED
                logger.error(f"任务 {task.task_id} 超过最大重试次数，标记为失败")
            
            self._save_tasks()
            return False
    
    async def worker(self) -> None:
        """Worker 循环处理任务"""
        logger.info("TTS 预生成 Worker 启动")
        
        while self.is_running:
            try:
                # 从队列取出任务（带超时）
                task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=5.0
                )
                
                # 处理任务
                await self.process_task(task)
                
                # 任务间隔
                await asyncio.sleep(TTS_WORKER_DELAY)
                
            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"Worker 异常: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info("TTS 预生成 Worker 停止")
    
    async def start(self) -> None:
        """启动预生成服务"""
        if self.is_running:
            logger.warning("预生成服务已在运行")
            return
        
        self.is_running = True
        
        # 恢复未完成的任务到队列（包括 PENDING 和 PROCESSING）
        # PROCESSING 任务可能是上次服务中断时留下的，需要重置为 PENDING 并重试
        pending_tasks = [
            task for task in self.tasks.values()
            if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]
        ]
        
        for task in pending_tasks:
            # 将 PROCESSING 任务重置为 PENDING（可能是服务中断的）
            if task.status == TaskStatus.PROCESSING:
                task.status = TaskStatus.PENDING
                task.started_at = None
                logger.info(f"重置中断的任务: {task.task_id}")
            
            try:
                await self.queue.put(task)
                logger.info(f"恢复任务到队列: {task.task_id}")
            except asyncio.QueueFull:
                logger.warning(f"队列已满，无法恢复任务: {task.task_id}")
                break
        
        # 保存更新后的任务状态
        if pending_tasks:
            self._save_tasks()
        
        # 启动 Worker
        self.worker_task = asyncio.create_task(self.worker())
        logger.info("TTS 预生成服务已启动")
    
    async def stop(self) -> None:
        """停止预生成服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 等待 Worker 完成
        if self.worker_task:
            await self.worker_task
        
        logger.info("TTS 预生成服务已停止")
    
    def get_task_status(self, task_id: str) -> Optional[TTSTask]:
        """查询任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务对象，不存在返回 None
        """
        return self.tasks.get(task_id)
    
    def get_queue_stats(self) -> Dict:
        """获取队列统计信息
        
        Returns:
            统计信息字典
        """
        status_counts = {status.value: 0 for status in TaskStatus}
        for task in self.tasks.values():
            # 兼容字符串和枚举两种情况
            status_value = task.status.value if isinstance(task.status, TaskStatus) else task.status
            status_counts[status_value] += 1
        
        return {
            "queue_size": self.queue.qsize(),
            "total_tasks": len(self.tasks),
            "pending": status_counts[TaskStatus.PENDING.value],
            "processing": status_counts[TaskStatus.PROCESSING.value],
            "completed": status_counts[TaskStatus.COMPLETED.value],
            "failed": status_counts[TaskStatus.FAILED.value],
            "skipped": status_counts[TaskStatus.SKIPPED.value],
            "is_running": self.is_running
        }
    
    def get_task_list(self, status: Optional[str] = None, limit: int = 50) -> Dict:
        """获取任务列表
        
        Args:
            status: 可选，按状态筛选
            limit: 返回数量限制
            
        Returns:
            任务列表字典
        """
        tasks_list = []
        for task in self.tasks.values():
            task_status = task.status.value if isinstance(task.status, TaskStatus) else task.status
            
            # 筛选状态
            if status and task_status != status:
                continue
            
            tasks_list.append({
                "task_id": task.task_id,
                "article_hash": task.article_hash,
                "source_file": task.source_file,
                "status": task_status,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "retry_count": task.retry_count,
                "error_message": task.error_message,
                "audio_hash": task.audio_hash
            })
        
        # 按创建时间倒序排列
        tasks_list.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        return {
            "tasks": tasks_list[:limit],
            "total": len(tasks_list)
        }


# ==================== 全局单例 ====================

_service_instance: Optional[TTSPregenerationService] = None


def get_tts_pregeneration_service() -> TTSPregenerationService:
    """获取TTS预生成服务单例
    
    Returns:
        TTSPregenerationService实例
    """
    global _service_instance
    
    if _service_instance is None:
        from reinvent_insight.services.tts_service import TTSService
        from reinvent_insight.services.audio_cache import AudioCache
        from reinvent_insight.services.tts_text_preprocessor import TTSTextPreprocessor
        from reinvent_insight.infrastructure.ai.model_config import get_model_client
        from pathlib import Path
        
        # 初始化依赖
        model_client = get_model_client("text_to_speech")
        tts_service = TTSService(model_client)
        
        # 创建 audio cache 目录
        audio_cache_dir = Path(TTS_TEXT_DIR) / "audio_cache"
        audio_cache = AudioCache(cache_dir=audio_cache_dir)
        
        text_preprocessor = TTSTextPreprocessor()
        
        _service_instance = TTSPregenerationService(
            tts_service=tts_service,
            audio_cache=audio_cache,
            text_preprocessor=text_preprocessor
        )
        
        logger.info("TTS预生成服务单例已创建")
    
    return _service_instance
