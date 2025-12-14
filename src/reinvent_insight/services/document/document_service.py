"""Document service - high-level document management"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

from reinvent_insight.core import config
from reinvent_insight.core.utils.file_utils import generate_doc_hash, is_pdf_document, get_source_identifier
from reinvent_insight.core.utils.text_utils import extract_text_from_markdown, count_chinese_words
from .metadata_service import (
    parse_metadata_from_md,
    clean_content_metadata,
    discover_versions,
)
from .hash_registry import HashRegistry

logger = logging.getLogger(__name__)


class DocumentService:
    """文档管理服务（高层业务逻辑）"""
    
    def __init__(
        self, 
        hash_registry: HashRegistry,
        output_dir: Path = None
    ):
        self.hash_registry = hash_registry
        self.output_dir = output_dir or config.OUTPUT_DIR
    
    def list_documents(self, include_versions: bool = False) -> List[Dict]:
        """列出所有文档
        
        Args:
            include_versions: 是否包含所有版本（默认只返回最新版本）
            
        Returns:
            文档信息列表
        """
        documents = []
        source_id_map = {}  # 用于去重，只保留最新版本
        
        if not self.output_dir.exists():
            return documents
        
        for md_file in self.output_dir.glob("*.md"):
            try:
                doc_info = self._build_document_info(md_file)
                if not doc_info:
                    continue
                
                source_id = doc_info.get("content_identifier") or doc_info.get("video_url", "")
                
                if include_versions:
                    # 包含所有版本
                    documents.append(doc_info)
                else:
                    # 只保留每个 source_id 的最新版本
                    if source_id:
                        if source_id not in source_id_map:
                            source_id_map[source_id] = doc_info
                        else:
                            existing_version = source_id_map[source_id].get("version", 0)
                            new_version = doc_info.get("version", 0)
                            if new_version > existing_version:
                                source_id_map[source_id] = doc_info
            except Exception as e:
                logger.warning(f"处理文件 {md_file.name} 时出错: {e}")
        
        if not include_versions:
            documents = list(source_id_map.values())
        
        # 按上传日期倒序排序
        documents.sort(key=lambda x: x.get("upload_date", "1970-01-01"), reverse=True)
        return documents
    
    def get_document(self, doc_hash: str, version: Optional[int] = None) -> Optional[Dict]:
        """获取文档内容
        
        Args:
            doc_hash: 文档哈希
            version: 版本号（可选，默认获取最新版本）
            
        Returns:
            文档信息字典，包含content字段
        """
        if version is not None:
            # 获取指定版本
            filename = self._find_version_file(doc_hash, version)
        else:
            # 获取默认版本
            filename = self.hash_registry.get_filename(doc_hash)
        
        if not filename:
            return None
        
        file_path = self.output_dir / filename
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            title_cn, title_en = self._extract_title(content, metadata)
            
            # 清理内容
            cleaned_content = clean_content_metadata(content, title_cn)
            
            # 发现版本
            source_id = get_source_identifier(metadata)
            versions = []
            if source_id:
                versions = discover_versions(source_id, self.output_dir)
            
            return {
                "filename": filename,
                "hash": doc_hash,
                "title_cn": title_cn,
                "title_en": title_en,
                "content": cleaned_content,
                "video_url": metadata.get("video_url", ""),
                "content_identifier": metadata.get("content_identifier", ""),
                "versions": versions,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"读取文档 {filename} 失败: {e}", exc_info=True)
            return None
    
    def check_exists_by_video_id(self, video_id: str) -> Optional[Dict]:
        """根据YouTube video_id检查文档是否存在
        
        Args:
            video_id: YouTube视频ID（11位）
            
        Returns:
            存在则返回 {exists: True, hash: xxx, title: xxx}，否则返回None
        """
        import re
        
        if not video_id or not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            return {"exists": False, "error": "无效的 video_id 格式"}
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        doc_hash = generate_doc_hash(video_url)
        
        if not doc_hash:
            return {"exists": False}
        
        filename = self.hash_registry.get_filename(doc_hash)
        if not filename:
            return {"exists": False}
        
        try:
            file_path = self.output_dir / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                metadata = parse_metadata_from_md(content)
                title = metadata.get("title_cn") or metadata.get("title_en") or metadata.get("title", "")
                
                return {"exists": True, "hash": doc_hash, "title": title}
        except Exception as e:
            logger.warning(f"读取文档 {filename} 失败: {e}")
        
        return {"exists": False}
    
    def get_versions(self, doc_hash: str) -> List[Dict]:
        """获取文档的所有版本
        
        Args:
            doc_hash: 文档哈希
            
        Returns:
            版本信息列表
        """
        filename = self.hash_registry.get_filename(doc_hash)
        if not filename:
            return []
        
        file_path = self.output_dir / filename
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            source_id = get_source_identifier(metadata)
            
            if source_id:
                return discover_versions(source_id, self.output_dir)
        except Exception as e:
            logger.warning(f"获取版本信息失败: {e}")
        
        return []
    
    def refresh_hash_mappings(self):
        """刷新哈希映射（扫描所有文件重建映射）"""
        self.hash_registry.clear()
        
        if not self.output_dir.exists():
            return
        
        source_id_to_files = {}
        skipped_count = 0
        error_count = 0
        
        # 第一遍：基于 content_identifier 或 video_url 对所有文件进行分组
        for md_file in self.output_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                metadata = parse_metadata_from_md(content)
                source_id = get_source_identifier(metadata)
                
                if source_id:
                    if source_id not in source_id_to_files:
                        source_id_to_files[source_id] = []
                    source_id_to_files[source_id].append({
                        'filename': md_file.name,
                        'version': metadata.get('version', 0)
                    })
                else:
                    skipped_count += 1
                    logger.debug(f"跳过文件 {md_file.name}（无标识符）")
            except Exception as e:
                error_count += 1
                logger.error(f"解析文件 {md_file.name} 时出错: {e}")
        
        # 第二遍：为每个分组生成和注册唯一的统一hash
        for source_id, files in source_id_to_files.items():
            doc_hash = generate_doc_hash(source_id)
            if not doc_hash:
                continue
            
            # 按版本号排序，最新版本在前
            files.sort(key=lambda x: x['version'], reverse=True)
            latest_file = files[0]['filename']
            
            # 注册映射
            for i, file_info in enumerate(files):
                self.hash_registry.register(
                    doc_hash, 
                    file_info['filename'],
                    is_default=(i == 0)  # 第一个为默认版本
                )
        
        stats = self.hash_registry.stats()
        log_msg = f"--- 统一Hash映射初始化完成，共处理 {stats['total_documents']} 个独立文档"
        if skipped_count > 0:
            log_msg += f"，跳过 {skipped_count} 个文件（无标识符）"
        if error_count > 0:
            log_msg += f"，{error_count} 个文件解析失败"
        log_msg += "。 ---"
        logger.info(log_msg)
    
    def _build_document_info(self, md_file: Path) -> Optional[Dict]:
        """构建文档信息字典
        
        Args:
            md_file: Markdown文件路径
            
        Returns:
            文档信息字典
        """
        try:
            content = md_file.read_text(encoding="utf-8")
            metadata = parse_metadata_from_md(content)
            
            title_cn, title_en = self._extract_title(content, metadata)
            if not title_cn:
                title_cn = title_en if title_en else md_file.stem
            
            doc_hash = self.hash_registry.get_hash(md_file.name)
            if not doc_hash:
                return None
            
            # 计算字数
            pure_text = extract_text_from_markdown(content)
            word_count = count_chinese_words(pure_text)
            
            # 获取时间戳
            stat = md_file.stat()
            created_at, modified_at = self._extract_timestamps(metadata, stat)
            
            # 检查是否为PDF文档
            source_id = get_source_identifier(metadata)
            is_pdf = is_pdf_document(source_id) if source_id else False
            is_document = bool(metadata.get('content_identifier'))
            
            return {
                "filename": md_file.name,
                "title_cn": title_cn,
                "title_en": title_en,
                "size": stat.st_size,
                "word_count": word_count,
                "created_at": created_at,
                "modified_at": modified_at,
                "upload_date": metadata.get("upload_date", "1970-01-01"),
                "video_url": metadata.get("video_url", ""),
                "content_identifier": metadata.get("content_identifier", ""),
                "is_reinvent": metadata.get("is_reinvent", False),
                "course_code": metadata.get("course_code"),
                "level": metadata.get("level"),
                "hash": doc_hash,
                "version": metadata.get("version", 0),
                "is_pdf": is_pdf,
                "is_document": is_document,
                "content_type": "文档" if is_document else ("PDF文档" if is_pdf else "YouTube视频")
            }
        except Exception as e:
            logger.warning(f"构建文档信息失败 {md_file.name}: {e}")
            return None
    
    def _find_version_file(self, doc_hash: str, version: int) -> Optional[str]:
        """查找指定版本的文件名
        
        Args:
            doc_hash: 文档哈希
            version: 版本号
            
        Returns:
            文件名或None
        """
        versions = self.get_versions(doc_hash)
        for v in versions:
            if v.get("version") == version:
                return v.get("filename")
        return None
    
    def _extract_title(self, content: str, metadata: Dict) -> tuple:
        """从内容和元数据中提取标题
        
        Args:
            content: 文档内容
            metadata: 元数据字典
            
        Returns:
            (title_cn, title_en) 元组
        """
        title_cn = metadata.get("title_cn")
        title_en = metadata.get("title_en", metadata.get("title", ""))
        
        if not title_cn:
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('# '):
                    title_cn = stripped[2:].strip()
                    break
        
        return title_cn, title_en
    
    def _extract_timestamps(self, metadata: Dict, stat) -> tuple:
        """从元数据和文件统计信息中提取时间戳
        
        Args:
            metadata: 元数据字典
            stat: 文件统计信息
            
        Returns:
            (created_at, modified_at) 元组
        """
        from datetime import datetime
        
        created_at = stat.st_ctime
        modified_at = stat.st_mtime
        
        if metadata.get("created_at"):
            try:
                dt = datetime.fromisoformat(metadata.get("created_at").replace('Z', '+00:00'))
                created_at = dt.timestamp()
                modified_at = created_at
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
                    created_at = dt.timestamp()
                    modified_at = created_at
            except (ValueError, AttributeError):
                pass
        
        return created_at, modified_at


# 创建全局单例实例
from .hash_registry import get_registry

document_service = DocumentService(
    hash_registry=get_registry()
)
