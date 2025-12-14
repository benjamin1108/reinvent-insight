"""Document version management routes"""

import logging
from fastapi import APIRouter, HTTPException

from reinvent_insight.core import config

# Import from legacy for compatibility
from reinvent_insight.services.document.hash_registry import (
    hash_to_filename,
)
from reinvent_insight.services.document.metadata_service import (
    parse_metadata_from_md,
    discover_versions,
)
from reinvent_insight.core.utils.file_utils import get_source_identifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/doc", tags=["versions"])


@router.get("/{doc_hash}/{version}")
async def get_public_summary_by_hash_and_version(doc_hash: str, version: int):
    """通过hash和version获取指定摘要文件的公开内容。"""
    # 查找默认文件名以获取video_url
    default_filename = hash_to_filename.get(doc_hash)
    if not default_filename:
        raise HTTPException(status_code=404, detail="主文档未找到")
        
    default_file_path = config.OUTPUT_DIR / default_filename
    if not default_file_path.exists():
        raise HTTPException(status_code=404, detail="主文档文件不存在")

    content = default_file_path.read_text(encoding="utf-8")
    metadata = parse_metadata_from_md(content)
    source_id = get_source_identifier(metadata)

    if not source_id:
        # 如果没有标识符，说明没有多版本
        if version == metadata.get("version", 1):
            # 导入文档路由的函数
            from reinvent_insight.api.routes.documents import get_public_summary
            return await get_public_summary(default_filename)
        else:
             raise HTTPException(status_code=404, detail=f"版本 {version} 未找到")

    # 根据 source_id 和 version 查找目标文件名
    versions = discover_versions(source_id, config.OUTPUT_DIR)
    target_version_info = next((v for v in versions if v.get("version") == version), None)

    if not target_version_info or not target_version_info.get("filename"):
        raise HTTPException(status_code=404, detail=f"版本 {version} 的文件未找到")

    # 导入文档路由的函数
    from reinvent_insight.api.routes.documents import get_public_summary
    return await get_public_summary(target_version_info["filename"])
