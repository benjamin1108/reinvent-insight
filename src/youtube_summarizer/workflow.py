import asyncio
import logging
import os
import re
import shutil
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from .summarizer import get_summarizer
from .task_manager import manager as task_manager
from . import prompts
from . import config
from .downloader import VideoMetadata, sanitize_filename

logger = logging.getLogger(__name__)

# 定义一个任务根目录
TASKS_ROOT_DIR = "./downloads/tasks"
BASE_PROMPT_PATH = "./prompt/youtbe-deep-summary.txt"

def create_anchor(text: str) -> str:
    """根据给定的标题文本创建一个 Markdown 锚点链接。"""
    # 转换为小写
    text = text.lower()
    # 移除 Markdown 标题标记, e.g., '### '
    text = text.strip().lstrip('#').strip()
    # 移除大部分标点符号, 但保留连字符. \w 匹配字母、数字、下划线.
    # 添加了中文字符范围 \u4e00-\u9fa5
    text = re.sub(r'[^\w\s\-\u4e00-\u9fa5]', '', text, flags=re.UNICODE)
    # 将一个或多个空格替换为单个连字符
    text = re.sub(r'\s+', '-', text)
    return text

def generate_toc_with_links(chapters: List[str]) -> str:
    """根据章节列表生成带锚点链接的 Markdown 目录。"""
    toc_md_lines = ["### 主要目录"]
    for i, chapter_title in enumerate(chapters):
        # 最终报告中的标题格式是 "1. Chapter Title"
        heading_for_anchor = f"{i + 1}. {chapter_title}"
        anchor = create_anchor(heading_for_anchor)
        toc_md_lines.append(f"{i + 1}. [{chapter_title}](#{anchor})")
    return "\n".join(toc_md_lines)

# ---- Helper Functions ----
def load_base_prompt() -> str:
    """加载基础提示词模板"""
    try:
        with open(BASE_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"基础提示词文件未找到: {BASE_PROMPT_PATH}")
        return ""

def parse_outline(content: str) -> Tuple[Optional[str], Optional[List[str]]]:
    """从Markdown文本中解析标题和章节列表"""
    title_match = re.search(r"^#\s*(.*)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else None

    chapters = re.findall(r"^\d+\.\s*(.*)", content, re.MULTILINE)
    
    if not title or not chapters:
        logger.warning(f"无法从内容中解析出完整的标题和章节: {content[:500]}")
        return None, None
        
    return title, chapters

# ---- Main Workflow Class ----
class DeepSummaryWorkflow:
    def __init__(self, task_id: str, model_name: str, transcript: str, video_metadata: VideoMetadata):
        self.task_id = task_id
        self.model_name = model_name
        self.transcript = transcript
        self.metadata = video_metadata
        self.task_dir = os.path.join(TASKS_ROOT_DIR, self.task_id)
        self.summarizer = get_summarizer(model_name)
        self.base_prompt = load_base_prompt()
        self.max_retries = 2
        
        # 确保任务目录存在
        os.makedirs(self.task_dir, exist_ok=True)

    async def run(self):
        """执行完整的深度摘要工作流"""
        try:
            await self._log("工作流启动：开始生成深度摘要。")
            task_manager.tasks[self.task_id].status = "running"

            # 步骤 1: 生成大纲
            outline_content = await self._generate_outline()
            if not outline_content:
                raise Exception("生成大纲失败")

            title, chapters_raw = parse_outline(outline_content)
            if not title or not chapters_raw:
                raise Exception("解析大纲失败")
            
            # 清理章节标题，移除所有方括号，作为保险措施
            chapters = [re.sub(r'[\[\]]', '', c).strip() for c in chapters_raw]

            await self._log(f"成功解析出标题: {title}")
            await self._log(f"成功解析出 {len(chapters)} 个章节。")
            
            # 生成带链接的目录
            toc_md = generate_toc_with_links(chapters)

            # 步骤 2: 并行生成章节内容
            success = await self._generate_chapters_parallel(chapters, title, outline_content)
            if not success:
                raise Exception("部分或全部章节内容生成失败")
            
            # 步骤 3: 生成引言、洞见和金句
            conclusion_content = await self._generate_conclusion(chapters)
            if not conclusion_content:
                raise Exception("生成收尾内容失败")
            
            # 步骤 4: 组装最终报告
            final_report = await self._assemble_final_report(title, toc_md, conclusion_content, len(chapters), self.metadata)
            if not final_report:
                raise Exception("组装最终报告失败")

            await self._log("工作流完成。", progress=100)
            await task_manager.send_result(title, final_report, self.task_id)

        except Exception as e:
            error_message = f"工作流遇到严重错误: {e}"
            logger.error(f"任务 {self.task_id} - {error_message}", exc_info=True)
            await task_manager.set_task_error(self.task_id, str(error_message))

    async def _generate_chapters_parallel(self, chapters: List[str], title: str, outline_content: str) -> bool:
        """步骤2：并行生成所有章节的内容"""
        await self._log(f"步骤 2/4: 开始并行生成 {len(chapters)} 个章节...")

        tasks = []
        for i, chapter_title in enumerate(chapters):
            task = self._generate_single_chapter(i, chapter_title, outline_content)
            tasks.append(task)
            # 在启动每个任务后，增加一个固定的延迟，以避免瞬间请求过多
            await asyncio.sleep(config.CHAPTER_GENERATION_DELAY_SECONDS)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_chapters = 0
        for i, result in enumerate(results):
            if isinstance(result, str):
                # 章节成功生成，只在本地记录日志，避免刷屏
                logger.info(f"任务 {self.task_id} - 章节 '{chapters[i]}' 已成功生成。")
                successful_chapters += 1
            else:
                logger.error(f"任务 {self.task_id} - 生成章节 '{chapters[i]}' 失败: {result}", exc_info=result)
        
        progress = 25 + int(50 * (successful_chapters / len(chapters)))
        await self._log(f"章节生成完成，成功 {successful_chapters}/{len(chapters)}。", progress=progress)

        return successful_chapters == len(chapters)

    async def _generate_single_chapter(self, index: int, chapter_title: str, outline_content: str) -> str:
        """为单个章节生成内容，包含重试和标题校验修复逻辑"""
        prompt = prompts.CHAPTER_PROMPT_TEMPLATE.format(
            base_prompt=self.base_prompt,
            full_transcript=self.transcript,
            full_outline=outline_content,
            chapter_number=index + 1,
            current_chapter_title=chapter_title
        )

        for attempt in range(self.max_retries + 1):
            try:
                chapter_content = await self.summarizer.generate_content(prompt)
                
                if not chapter_content or not chapter_content.strip():
                    raise ValueError("模型返回了空内容")

                # ---- Start: 标题校验和修复逻辑 ----
                # 移除 chapter_title 中可能存在的 Markdown 链接语法
                clean_chapter_title = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', chapter_title).strip()
                
                expected_title_prefix = f"### {index + 1}. {clean_chapter_title}"
                
                # 为了稳健比较，将实际内容的第一行提取出来处理
                content_lines = chapter_content.strip().split('\n')
                first_line = content_lines[0].strip()
                
                # 如果第一行不是以 '###' 开头，或者与预期的标题不符（忽略前后空格和末尾标点）
                # 检查时不考虑标题末尾的微小差异，比如中英文句号
                if not first_line.startswith("###") or \
                   not first_line.lstrip('# ').lstrip(f"{index + 1}.").strip().startswith(clean_chapter_title):
                    
                    logger.warning(
                        f"任务 {self.task_id} - 章节 '{chapter_title}' 的标题格式不正确。 "
                        f"预期开头: '{expected_title_prefix}', "
                        f"实际开头: '{first_line}'. "
                        "正在自动修复..."
                    )
                    # 移除可能存在的错误标题
                    if first_line.startswith("###"):
                        chapter_content = '\n'.join(content_lines[1:]).lstrip()

                    # 添加正确的标题
                    chapter_content = f"{expected_title_prefix}\n\n{chapter_content}"
                # ---- End: 标题校验和修复逻辑 ----

                chapter_path = os.path.join(self.task_dir, f"chapter_{index + 1}.md")
                with open(chapter_path, "w", encoding="utf-8") as f:
                    f.write(chapter_content)
                return chapter_content
                
            except Exception as e:
                logger.warning(f"任务 {self.task_id} - 生成章节 '{chapter_title}' 失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    # 当所有重试都失败时，抛出异常由 gather 捕获
                    raise e
                await asyncio.sleep(2 * (attempt + 1)) # 增加重试等待时间
        
        # 此处理论上不会到达，因为上面会抛出异常
        raise RuntimeError(f"未能为章节 '{chapter_title}' 生成内容。")

    async def _generate_outline(self) -> Optional[str]:
        """步骤1：生成大纲和标题，包含重试逻辑"""
        await self._log("步骤 1/4: 正在生成大纲和标题...")
        
        prompt = prompts.OUTLINE_PROMPT_TEMPLATE.format(
            base_prompt=self.base_prompt,
            full_transcript=self.transcript
        )
        
        for attempt in range(self.max_retries + 1):
            try:
                outline = await self.summarizer.generate_content(prompt)
                if outline:
                    outline_path = os.path.join(self.task_dir, "outline.md")
                    with open(outline_path, "w", encoding="utf-8") as f:
                        f.write(outline)
                    await self._log("大纲和标题已生成。", progress=25)
                    return outline
                
                # 如果返回空内容，也视为一种失败
                raise ValueError("模型返回了空内容")

            except Exception as e:
                logger.warning(f"任务 {self.task_id} - 生成大纲失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"任务 {self.task_id} - 生成大纲达到最大重试次数，失败。", exc_info=True)
                    # 向上抛出异常，由主 run 方法捕获
                    raise e
                await self._log(f"生成大纲时遇到问题，正在重试 ({attempt + 2}/{self.max_retries + 1})...")
                await asyncio.sleep(2) # 等待2秒再重试
        return None

    async def _generate_conclusion(self, chapters: List[str]) -> Optional[str]:
        """步骤3：生成引言、洞见和金句"""
        await self._log("步骤 3/4: 正在生成引言、洞见和金句...")

        # 从文件中读取所有章节内容
        all_chapters_content = []
        for i in range(len(chapters)):
            try:
                chapter_path = os.path.join(self.task_dir, f"chapter_{i + 1}.md")
                with open(chapter_path, "r", encoding="utf-8") as f:
                    all_chapters_content.append(f.read())
            except FileNotFoundError:
                logger.error(f"任务 {self.task_id} - 未找到章节文件: chapter_{i + 1}.md")
                return None
        
        full_chapters_text = "\n\n".join(all_chapters_content)

        prompt = prompts.CONCLUSION_PROMPT_TEMPLATE.format(
            base_prompt=self.base_prompt,
            full_transcript=self.transcript,
            all_generated_chapters=full_chapters_text
        )

        for attempt in range(self.max_retries + 1):
            try:
                conclusion_content = await self.summarizer.generate_content(prompt)
                if conclusion_content:
                    conclusion_path = os.path.join(self.task_dir, "conclusion.md")
                    with open(conclusion_path, "w", encoding="utf-8") as f:
                        f.write(conclusion_content)
                    await self._log("引言、洞见和金句已生成。", progress=90)
                    return conclusion_content
                raise ValueError("模型返回了空内容")
            except Exception as e:
                logger.warning(f"任务 {self.task_id} - 生成收尾内容失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"任务 {self.task_id} - 生成收尾内容达到最大重试次数，失败。", exc_info=True)
                    await self._log(f"错误：生成收尾内容时发生严重错误 - {e}", error=True)
                    return None
                await asyncio.sleep(2)
        return None

    async def _assemble_final_report(self, title: str, toc_md: str, conclusion_md: str, chapter_count: int, metadata: VideoMetadata) -> Optional[str]:
        """步骤4：在本地组装所有部分以生成最终的Markdown文件"""
        await self._log("步骤 4/4: 正在组装最终报告...")
        try:
            chapter_contents = []
            for i in range(chapter_count):
                chapter_path = os.path.join(self.task_dir, f"chapter_{i + 1}.md")
                with open(chapter_path, 'r', encoding='utf-8') as f:
                    chapter_contents.append(f.read().strip())
            
            final_report = _perform_assembly(title, toc_md, conclusion_md, chapter_contents, metadata)

            # 先保存在任务目录
            temp_report_path = os.path.join(self.task_dir, "final_report.md")
            with open(temp_report_path, "w", encoding="utf-8") as f:
                f.write(final_report)
            
            # 移动并重命名到最终的输出目录
            final_filename = f"{metadata.sanitized_title}.md"
            final_path = config.OUTPUT_DIR / final_filename
            config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # 确保目录存在
            shutil.move(temp_report_path, final_path)

            await self._log(f"最终报告已成功组装并移动到: {final_path}")
            # 更新任务状态，包含最终文件路径
            task_manager.set_task_result(self.task_id, str(final_path))
            return final_report
        except Exception as e:
            logger.error(f"任务 {self.task_id} - 组装最终报告时出错: {e}", exc_info=True)
            return None

    async def _log(self, message: str, progress: int = None, error: bool = False):
        """向 TaskManager 发送日志和进度更新"""
        logger.info(f"任务 {self.task_id}: {message}")
        if progress is not None:
            await task_manager.update_progress(self.task_id, progress, message)
        else:
            await task_manager.send_message(message, self.task_id)
        
        if error:
             await task_manager.set_task_error(self.task_id, message)

def _perform_assembly(title: str, toc_md: str, conclusion_md: str, chapter_contents: List[str], metadata: Optional[VideoMetadata] = None) -> str:
    """
    可复用的核心拼接逻辑。
    接收所有内容的字符串，返回最终的报告字符串。
    """
    # 1. 生成 YAML Front Matter
    metadata_yaml = ""
    if metadata:
        # 使用PyYAML来生成格式规范的YAML
        try:
            import yaml
            from dataclasses import asdict
            
            # 创建一个字典，只包含我们想输出的字段
            # 注意：这里我们假设title是AI生成的中文标题（在上面的_assemble_final_report中传入）
            # metadata.title是原始的英文视频标题
            metadata_dict = {
                "title_en": metadata.title,  # 原始英文视频标题
                "title_cn": title,  # AI生成的中文标题
                "upload_date": metadata.upload_date,
                "video_url": metadata.video_url,
                "is_reinvent": metadata.is_reinvent,
                "course_code": metadata.course_code,
                "level": metadata.level
            }
            # allow_unicode=True 保证中文字符正确显示
            metadata_yaml = f"---\n{yaml.dump(metadata_dict, allow_unicode=True, sort_keys=False)}---\n\n"
        except ImportError:
            logger.warning("PyYAML 未安装，无法生成 YAML front matter。请运行 'pip install pyyaml'。")
            metadata_yaml = ""
        except Exception as e:
            logger.error(f"生成 YAML front matter 时出错: {e}")
            metadata_yaml = ""


    # 2. 从 conclusion.md 中更稳健地解析出引言、洞见和金句
    introduction = ""
    insights = ""
    quotes = ""

    # 使用 ### 作为分隔符来切分收尾部分的内容
    # 我们在前面加上换行符，以确保能正确处理文件开头的第一个部分
    conclusion_parts = re.split(r'\n###\s+', '\n' + conclusion_md)

    for part in conclusion_parts:
        part = part.strip()
        if not part:
            continue
        
        # 还原被切掉的 ### 标记，因为 split 会消耗掉分隔符
        full_part = "### " + part
        
        if part.lower().startswith('引言'):
            introduction = full_part
        elif part.lower().startswith('洞见延伸'):
            insights = full_part
        elif part.lower().startswith('金句&原声引用'):
            quotes = full_part

    # 3. 从 outline.md 中提取目录 - > 已被废弃，现在直接使用传入的 toc_md

    # 4. 按正确的顺序拼接
    final_report_parts = [
        metadata_yaml, # 在最前面加入元数据
        f"# {title}",
        introduction,
        toc_md, # 使用预先生成的、带链接的目录
        "\n\n---\n\n".join(chapter_contents),
        insights,
        quotes
    ]
    
    return "\n\n".join(part for part in final_report_parts if part and part.strip())

async def reassemble_from_task_id(task_id: str):
    """根据给定的 task_id 重新组装报告"""
    task_dir = os.path.join(TASKS_ROOT_DIR, task_id)
    if not os.path.isdir(task_dir):
        logger.error(f"任务目录未找到: {task_dir}")
        return

    try:
        logger.info(f"开始从目录 {task_dir} 重新组装报告...")

        # 加载所有中间文件
        with open(os.path.join(task_dir, "outline.md"), "r", encoding="utf-8") as f:
            outline_md = f.read()
        
        with open(os.path.join(task_dir, "conclusion.md"), "r", encoding="utf-8") as f:
            conclusion_md = f.read()

        title, chapters_raw = parse_outline(outline_md)
        if not title or not chapters_raw:
            raise ValueError("无法从 outline.md 解析出标题")
        
        # 清理并生成带链接的目录
        chapters = [re.sub(r'[\[\]]', '', c).strip() for c in chapters_raw]
        toc_md = generate_toc_with_links(chapters)
        
        def natural_sort_key(path):
            # 从文件名 chapter_1.md 中提取数字 1 用于排序
            match = re.search(r'chapter_(\d+)\.md', path.name)
            return int(match.group(1)) if match else -1

        chapter_files = sorted(Path(task_dir).glob("chapter_*.md"), key=natural_sort_key)
        chapter_contents = []
        for chapter_file in chapter_files:
            with open(chapter_file, "r", encoding="utf-8") as f:
                chapter_contents.append(f.read().strip())
        
        logger.info(f"加载了 {len(chapter_contents)} 个章节文件。")

        # 调用核心拼接逻辑
        final_report = _perform_assembly(title, toc_md, conclusion_md, chapter_contents) # reassemble 时 metadata 为 None
        
        # 保存为新文件
        temp_output_path = os.path.join(task_dir, "final_report_reassembled.md")
        with open(temp_output_path, "w", encoding="utf-8") as f:
            f.write(final_report)
        
        # 如果存在 video_title.txt 则优先使用其中的标题
        video_title_path = Path(task_dir) / "video_title.txt"
        preferred_title = title
        if video_title_path.exists():
            try:
                preferred_title = video_title_path.read_text(encoding="utf-8").strip() or title
                # 重新组装时，我们没有完整的 metadata，但可以创建一个临时的
                # 注意：这部分可能需要未来进一步完善，如果需要 reassemble 也有完整 metadata 的话
                reassembled_metadata = VideoMetadata(title=preferred_title, upload_date="N/A", video_url="N/A")
                final_filename = f"{reassembled_metadata.sanitized_title} (Reassembled).md"
            except Exception:
                final_filename = f"{sanitize_filename(preferred_title)} (Reassembled).md"
        else:
             final_filename = f"{sanitize_filename(preferred_title)} (Reassembled).md"

        # 移动并重命名到最终的输出目录
        final_path = config.OUTPUT_DIR / final_filename
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(temp_output_path, final_path)

        logger.success(f"重新组装成功！报告已保存到: {final_path}")

    except FileNotFoundError as e:
        logger.error(f"重新组装失败：缺少必要的中间文件 - {e.filename}")
    except Exception as e:
        logger.error(f"重新组装时发生未知错误: {e}", exc_info=True)

async def run_deep_summary_workflow(task_id: str, model_name: str, transcript: str, video_metadata: VideoMetadata):
    """工作流的入口函数"""
    workflow = DeepSummaryWorkflow(task_id, model_name, transcript, video_metadata=video_metadata)
    await workflow.run() 