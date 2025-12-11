"""文档摘要列表缓存服务

解决性能问题：每次请求 /api/public/summaries 都需要遍历、读取、解析所有文档。
通过内存缓存，显著提升列表接口的响应速度。
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from reinvent_insight.core import config
from reinvent_insight.core.utils.file_utils import generate_doc_hash, is_pdf_document

logger = logging.getLogger(__name__)


class SummaryCache:
    """文档摘要列表缓存（单例）
    
    缓存策略：
    1. 启动时初始化完整缓存
    2. 新增/更新文档时增量更新缓存
    3. 提供快速的列表查询接口
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 缓存数据：doc_hash -> summary_data
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # 文件名到 hash 的映射（快速查找）
        self._filename_to_hash: Dict[str, str] = {}
        
        # 按 video_url 分组（用于版本去重）
        self._video_url_to_hash: Dict[str, str] = {}
        
        # 缓存版本号（用于前端判断是否需要更新）
        self._cache_version: int = 0
        
        # 最后更新时间
        self._last_updated: float = 0
        
        # 文件修改时间记录（用于增量更新检测）
        self._file_mtimes: Dict[str, float] = {}
        
        self._initialized = True
    
    @property
    def cache_version(self) -> int:
        """获取缓存版本号"""
        return self._cache_version
    
    @property
    def last_updated(self) -> float:
        """获取最后更新时间戳"""
        return self._last_updated
    
    @property
    def document_count(self) -> int:
        """获取缓存中的文档数量"""
        return len(self._cache)
    
    def init_cache(self) -> None:
        """初始化完整缓存（启动时调用）"""
        start_time = time.time()
        
        # 导入依赖（延迟导入避免循环依赖）
        from reinvent_insight.services.document.metadata_service import (
            parse_metadata_from_md,
            extract_text_from_markdown,
            count_chinese_words,
        )
        from reinvent_insight.services.document.hash_registry import filename_to_hash
        from reinvent_insight.api.routes.ultra_deep import count_toc_chapters
        
        self._cache.clear()
        self._filename_to_hash.clear()
        self._video_url_to_hash.clear()
        self._file_mtimes.clear()
        
        if not config.OUTPUT_DIR.exists():
            logger.warning("OUTPUT_DIR 不存在，跳过缓存初始化")
            return
        
        # video_url 分组（用于版本去重，只保留最新版本）
        video_url_map: Dict[str, Dict[str, Any]] = {}
        processed = 0
        errors = 0
        
        for md_file in config.OUTPUT_DIR.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                metadata = parse_metadata_from_md(content)
                
                # 获取标题
                title_cn = metadata.get("title_cn")
                title_en = metadata.get("title_en", metadata.get("title", ""))
                
                if not title_cn:
                    for line in content.splitlines():
                        stripped = line.strip()
                        if stripped.startswith('# '):
                            title_cn = stripped[2:].strip()
                            break
                
                if not title_cn:
                    title_cn = title_en if title_en else md_file.stem
                
                # 获取 doc_hash
                doc_hash = filename_to_hash.get(md_file.name)
                if not doc_hash:
                    continue
                
                # 计算字数
                pure_text = extract_text_from_markdown(content)
                word_count = count_chinese_words(pure_text)
                
                # 计算章节数
                chapter_count = count_toc_chapters(content)
                
                # 获取文件时间
                stat = md_file.stat()
                video_url = metadata.get("video_url", "")
                is_pdf = is_pdf_document(video_url)
                
                # 解析时间
                created_at_value = stat.st_ctime
                modified_at_value = stat.st_mtime
                
                if metadata.get("created_at"):
                    try:
                        dt = datetime.fromisoformat(metadata.get("created_at").replace('Z', '+00:00'))
                        created_at_value = dt.timestamp()
                        modified_at_value = created_at_value
                    except (ValueError, AttributeError):
                        pass
                elif metadata.get("upload_date"):
                    try:
                        upload_date_str = str(metadata.get("upload_date")).replace('-', '')
                        if len(upload_date_str) == 8:
                            year = int(upload_date_str[0:4])
                            month = int(upload_date_str[4:6])
                            day = int(upload_date_str[6:8])
                            dt = datetime(year, month, day)
                            created_at_value = dt.timestamp()
                            modified_at_value = created_at_value
                    except (ValueError, AttributeError):
                        pass
                
                summary_data = {
                    "filename": md_file.name,
                    "title_cn": title_cn,
                    "title_en": title_en,
                    "size": stat.st_size,
                    "word_count": word_count,
                    "created_at": created_at_value,
                    "modified_at": modified_at_value,
                    "upload_date": metadata.get("upload_date", "1970-01-01"),
                    "video_url": video_url,
                    "is_reinvent": metadata.get("is_reinvent", False),
                    "course_code": metadata.get("course_code"),
                    "level": metadata.get("level"),
                    "hash": doc_hash,
                    "version": metadata.get("version", 0),
                    "is_pdf": is_pdf,
                    "content_type": "PDF文档" if is_pdf else "YouTube视频",
                    "chapter_count": chapter_count,
                    "source_type": "pdf" if is_pdf else "youtube"
                }
                
                # 记录文件修改时间
                self._file_mtimes[md_file.name] = stat.st_mtime
                self._filename_to_hash[md_file.name] = doc_hash
                
                # 按 video_url 分组，只保留最新版本
                if video_url:
                    if video_url not in video_url_map:
                        video_url_map[video_url] = summary_data
                    else:
                        existing_version = video_url_map[video_url].get("version", 0)
                        new_version = summary_data.get("version", 0)
                        if new_version > existing_version:
                            video_url_map[video_url] = summary_data
                
                processed += 1
                
            except Exception as e:
                errors += 1
                logger.warning(f"缓存初始化: 处理文件 {md_file.name} 失败: {e}")
        
        # 将去重后的结果存入缓存
        for video_url, summary_data in video_url_map.items():
            doc_hash = summary_data["hash"]
            self._cache[doc_hash] = summary_data
            self._video_url_to_hash[video_url] = doc_hash
        
        self._cache_version += 1
        self._last_updated = time.time()
        
        elapsed = time.time() - start_time
        logger.info(
            f"文档缓存初始化完成: {len(self._cache)} 篇文档, "
            f"处理 {processed} 个文件, {errors} 个错误, 耗时 {elapsed:.2f}s"
        )
    
    def get_all_summaries(self, sort_by: str = "upload_date", reverse: bool = True) -> List[Dict[str, Any]]:
        """获取所有文档摘要（已排序）
        
        Args:
            sort_by: 排序字段
            reverse: 是否降序
            
        Returns:
            排序后的文档列表
        """
        summaries = list(self._cache.values())
        
        # 排序
        if sort_by == "upload_date":
            summaries.sort(key=lambda x: x.get("upload_date", "1970-01-01"), reverse=reverse)
        elif sort_by == "modified_at":
            summaries.sort(key=lambda x: x.get("modified_at", 0), reverse=reverse)
        elif sort_by == "title":
            summaries.sort(key=lambda x: x.get("title_cn", ""), reverse=reverse)
        
        return summaries
    
    def get_paginated_summaries(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "upload_date",
        reverse: bool = True
    ) -> Dict[str, Any]:
        """获取分页的文档摘要
        
        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            sort_by: 排序字段
            reverse: 是否降序
            
        Returns:
            包含分页信息和数据的字典
        """
        all_summaries = self.get_all_summaries(sort_by, reverse)
        total = len(all_summaries)
        
        # 计算分页
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_data = all_summaries[start_idx:end_idx]
        
        return {
            "summaries": page_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "cache_version": self._cache_version
        }
    
    def update_document(self, filename: str) -> None:
        """更新单个文档的缓存（新增或修改时调用）
        
        Args:
            filename: 文件名
        """
        from reinvent_insight.services.document.metadata_service import (
            parse_metadata_from_md,
            extract_text_from_markdown,
            count_chinese_words,
        )
        from reinvent_insight.services.document.hash_registry import filename_to_hash
        from reinvent_insight.api.routes.ultra_deep import count_toc_chapters
        
        file_path = config.OUTPUT_DIR / filename
        if not file_path.exists():
            # 文件被删除，移除缓存
            self.remove_document(filename)
            return
        
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            
            title_cn = metadata.get("title_cn")
            title_en = metadata.get("title_en", metadata.get("title", ""))
            
            if not title_cn:
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('# '):
                        title_cn = stripped[2:].strip()
                        break
            
            if not title_cn:
                title_cn = title_en if title_en else file_path.stem
            
            doc_hash = filename_to_hash.get(filename)
            if not doc_hash:
                return
            
            pure_text = extract_text_from_markdown(content)
            word_count = count_chinese_words(pure_text)
            chapter_count = count_toc_chapters(content)
            stat = file_path.stat()
            video_url = metadata.get("video_url", "")
            is_pdf = is_pdf_document(video_url)
            
            created_at_value = stat.st_ctime
            modified_at_value = stat.st_mtime
            
            if metadata.get("created_at"):
                try:
                    dt = datetime.fromisoformat(metadata.get("created_at").replace('Z', '+00:00'))
                    created_at_value = dt.timestamp()
                    modified_at_value = created_at_value
                except (ValueError, AttributeError):
                    pass
            elif metadata.get("upload_date"):
                try:
                    upload_date_str = str(metadata.get("upload_date")).replace('-', '')
                    if len(upload_date_str) == 8:
                        year = int(upload_date_str[0:4])
                        month = int(upload_date_str[4:6])
                        day = int(upload_date_str[6:8])
                        dt = datetime(year, month, day)
                        created_at_value = dt.timestamp()
                        modified_at_value = created_at_value
                except (ValueError, AttributeError):
                    pass
            
            summary_data = {
                "filename": filename,
                "title_cn": title_cn,
                "title_en": title_en,
                "size": stat.st_size,
                "word_count": word_count,
                "created_at": created_at_value,
                "modified_at": modified_at_value,
                "upload_date": metadata.get("upload_date", "1970-01-01"),
                "video_url": video_url,
                "is_reinvent": metadata.get("is_reinvent", False),
                "course_code": metadata.get("course_code"),
                "level": metadata.get("level"),
                "hash": doc_hash,
                "version": metadata.get("version", 0),
                "is_pdf": is_pdf,
                "content_type": "PDF文档" if is_pdf else "YouTube视频",
                "chapter_count": chapter_count,
                "source_type": "pdf" if is_pdf else "youtube"
            }
            
            # 更新缓存
            self._cache[doc_hash] = summary_data
            self._filename_to_hash[filename] = doc_hash
            self._file_mtimes[filename] = stat.st_mtime
            
            if video_url:
                self._video_url_to_hash[video_url] = doc_hash
            
            self._cache_version += 1
            self._last_updated = time.time()
            
            logger.info(f"文档缓存已更新: {filename}")
            
        except Exception as e:
            logger.error(f"更新文档缓存失败 {filename}: {e}")
    
    def remove_document(self, filename: str) -> None:
        """从缓存中移除文档
        
        Args:
            filename: 文件名
        """
        doc_hash = self._filename_to_hash.get(filename)
        if doc_hash and doc_hash in self._cache:
            video_url = self._cache[doc_hash].get("video_url")
            del self._cache[doc_hash]
            
            if video_url and video_url in self._video_url_to_hash:
                del self._video_url_to_hash[video_url]
        
        if filename in self._filename_to_hash:
            del self._filename_to_hash[filename]
        
        if filename in self._file_mtimes:
            del self._file_mtimes[filename]
        
        self._cache_version += 1
        self._last_updated = time.time()
        
        logger.info(f"文档已从缓存移除: {filename}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存状态信息"""
        return {
            "document_count": len(self._cache),
            "cache_version": self._cache_version,
            "last_updated": self._last_updated,
            "last_updated_str": datetime.fromtimestamp(self._last_updated).isoformat() if self._last_updated else None
        }


# 全局单例
_summary_cache = SummaryCache()


def get_summary_cache() -> SummaryCache:
    """获取摘要缓存单例"""
    return _summary_cache


def init_summary_cache() -> None:
    """初始化摘要缓存"""
    _summary_cache.init_cache()
