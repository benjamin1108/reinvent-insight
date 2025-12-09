"""Document download routes"""

import logging
import urllib.parse
import subprocess
import tempfile
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from urllib.parse import quote

from reinvent_insight.core import config

# Import from legacy for compatibility
from reinvent_insight.services.document.metadata_service import (
    parse_metadata_from_md,
    clean_content_metadata,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/summaries", tags=["downloads"])


@router.get("/{filename}/markdown")
async def get_summary_markdown(filename: str):
    """获取指定摘要的原始 Markdown 文件(去除元数据)。"""
    try:
        filename = urllib.parse.unquote(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
            
        if not filename.endswith(".md"):
            filename += ".md"
            
        file_path = config.OUTPUT_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
        
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
        
        cleaned_content = clean_content_metadata(content, title_cn)
        
        full_content = ''
        if title_en:
            full_content += f"# {title_en}\n\n"
        if title_cn and title_cn != title_en:
            full_content += f"{title_cn}\n\n"
        full_content += cleaned_content
        
        safe_title = title_en or title_cn or file_path.stem
        safe_title = safe_title.replace('/', '-').replace('\\', '-').replace(':', '-')
        safe_title = re.sub(r'[<>:"/\\|?*]', '-', safe_title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        safe_title = safe_title[:100]
        download_filename = f"{safe_title}.md"
        
        encoded_filename = quote(download_filename, safe='')
        
        return Response(
            content=full_content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Markdown 文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Markdown 文件失败: {str(e)}")


@router.get("/{filename}/pdf")
async def get_summary_pdf(filename: str, response: Response):
    """生成并下载指定摘要的PDF文件。"""
    try:
        filename = urllib.parse.unquote(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
            
        if not filename.endswith(".md"):
            filename += ".md"
            
        md_file_path = config.OUTPUT_DIR / filename
        if not md_file_path.exists():
            raise HTTPException(status_code=404, detail="摘要文件未找到")
        
        pdf_filename = filename.replace('.md', '.pdf')
        pdf_dir = config.OUTPUT_DIR.parent / "pdfs"
        pdf_dir.mkdir(exist_ok=True)
        pdf_file_path = pdf_dir / pdf_filename
        
        if not pdf_file_path.exists():
            logger.info(f"生成PDF文件: {pdf_filename}")
            
            script_path = Path(__file__).parent.parent.parent / "tools" / "generate_pdfs.py"
            logger.info(f"PDF生成脚本路径: {script_path}")
            
            if not script_path.exists():
                logger.error(f"PDF生成工具不存在: {script_path}")
                raise HTTPException(status_code=500, detail="PDF生成工具不存在")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_pdf_path = Path(temp_dir) / pdf_filename
                
                cmd = [
                    "python",
                    str(script_path),
                    "-f", str(md_file_path),
                    "-o", str(temp_dir),
                    "--css", str(config.PROJECT_ROOT / "web" / "css" / "pdf_style.css")
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"PDF生成失败: {result.stderr}")
                    raise HTTPException(status_code=500, detail=f"PDF生成失败: {result.stderr or '未知错误'}")
                
                if temp_pdf_path.exists():
                    temp_pdf_path.rename(pdf_file_path)
                else:
                    raise HTTPException(status_code=500, detail="PDF文件生成后未找到")
        
        if pdf_file_path.exists():
            logger.info(f"返回PDF文件: {pdf_filename}")
            
            encoded_filename = quote(pdf_filename, safe='')
            
            return FileResponse(
                path=str(pdf_file_path),
                media_type="application/pdf",
                filename=pdf_filename,
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
                }
            )
        else:
            raise HTTPException(status_code=500, detail="PDF文件不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取PDF文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取PDF文件失败: {str(e)}")
