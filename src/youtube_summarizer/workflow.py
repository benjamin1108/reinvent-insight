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

logger = logging.getLogger(__name__)

# 定义一个任务根目录
TASKS_ROOT_DIR = "./tasks"
BASE_PROMPT_PATH = "./prompt/youtbe-deep-summary.txt"

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
    def __init__(self, task_id: str, model_name: str, transcript: str, video_title: str | None = None):
        self.task_id = task_id
        self.model_name = model_name
        self.transcript = transcript
        # 原始视频标题（已过 sanitize，可直接用于文件名）
        self.video_title = video_title
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

            title, chapters = parse_outline(outline_content)
            if not title or not chapters:
                raise Exception("解析大纲失败")
            
            await self._log(f"成功解析出标题: {title}")
            await self._log(f"成功解析出 {len(chapters)} 个章节。")

            # 步骤 2: 并行生成章节内容
            success = await self._generate_chapters_parallel(chapters, title, outline_content)
            if not success:
                raise Exception("部分或全部章节内容生成失败")
            
            # 步骤 3: 生成引言、洞见和金句
            conclusion_content = await self._generate_conclusion(chapters)
            if not conclusion_content:
                raise Exception("生成收尾内容失败")
            
            # 步骤 4: 组装最终报告
            final_report = await self._assemble_final_report(title, outline_content, conclusion_content, len(chapters))
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
        """为单个章节生成内容，包含重试逻辑"""
        prompt = prompts.CHAPTER_PROMPT_TEMPLATE.format(
            base_prompt=self.base_prompt,
            full_transcript=self.transcript,
            full_outline=outline_content,
            current_chapter_title=chapter_title
        )

        for attempt in range(self.max_retries + 1):
            try:
                chapter_content = await self.summarizer.generate_content(prompt)
                if chapter_content:
                    chapter_path = os.path.join(self.task_dir, f"chapter_{index + 1}.md")
                    with open(chapter_path, "w", encoding="utf-8") as f:
                        f.write(chapter_content)
                    return chapter_content
                
                raise ValueError("模型返回了空内容")

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

    async def _assemble_final_report(self, title: str, outline_md: str, conclusion_md: str, chapter_count: int) -> Optional[str]:
        """步骤4：在本地组装所有部分以生成最终的Markdown文件"""
        await self._log("步骤 4/4: 正在组装最终报告...")
        try:
            chapter_contents = []
            for i in range(chapter_count):
                chapter_path = os.path.join(self.task_dir, f"chapter_{i + 1}.md")
                with open(chapter_path, 'r', encoding='utf-8') as f:
                    chapter_contents.append(f.read().strip())
            
            final_report = _perform_assembly(title, outline_md, conclusion_md, chapter_contents)

            # 先保存在任务目录
            temp_report_path = os.path.join(self.task_dir, "final_report.md")
            with open(temp_report_path, "w", encoding="utf-8") as f:
                f.write(final_report)
            
            # 移动并重命名到最终的输出目录
            preferred_title = self.video_title or title
            final_filename = f"{preferred_title}.md"
            final_path = config.OUTPUT_DIR / final_filename
            config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # 确保目录存在
            shutil.move(temp_report_path, final_path)

            await self._log(f"最终报告已成功组装并移动到: {final_path}")
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

def _perform_assembly(title: str, outline_md: str, conclusion_md: str, chapter_contents: List[str]) -> str:
    """
    可复用的核心拼接逻辑。
    接收所有内容的字符串，返回最终的报告字符串。
    """
    # 1. 从 conclusion.md 中更稳健地解析出引言、洞见和金句
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

    # 2. 从 outline.md 中提取目录
    # 我们只想要 '### 主要目录' 及之后的部分
    toc_parts = re.split(r"###\s*主要目录\s*", outline_md, flags=re.IGNORECASE)
    toc = "### 主要目录\n" + toc_parts[1].strip() if len(toc_parts) > 1 else ""

    # 3. 按正确的顺序拼接
    final_report_parts = [
        f"# {title}",
        introduction,
        toc,
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

        title, _ = parse_outline(outline_md)
        if not title:
            raise ValueError("无法从 outline.md 解析出标题")
        
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
        final_report = _perform_assembly(title, outline_md, conclusion_md, chapter_contents)
        
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
            except Exception:
                pass

        # 移动并重命名到最终的输出目录
        final_filename = f"{preferred_title} (Reassembled).md"
        final_path = config.OUTPUT_DIR / final_filename
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(temp_output_path, final_path)

        logger.success(f"重新组装成功！报告已保存到: {final_path}")

    except FileNotFoundError as e:
        logger.error(f"重新组装失败：缺少必要的中间文件 - {e.filename}")
    except Exception as e:
        logger.error(f"重新组装时发生未知错误: {e}", exc_info=True)

async def run_deep_summary_workflow(task_id: str, model_name: str, transcript: str, video_title: str | None = None):
    """工作流的入口函数"""
    workflow = DeepSummaryWorkflow(task_id, model_name, transcript, video_title=video_title)
    await workflow.run() 