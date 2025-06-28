#!/usr/bin/env python3
"""
AWS re:Invent Insights PDF批量生成工具

该工具用于将downloads/summaries目录下的所有Markdown文件批量转换为PDF格式。
支持自定义输入输出目录、单文件处理等功能。
"""

import markdown
import os
import re
import argparse
import sys
import yaml
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from typing import List, Optional, Tuple


def parse_front_matter(markdown_text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str]:
    """
    解析Markdown文件的YAML front matter
    
    Returns:
        (title_cn, title_en, video_url, upload_date, content)
    """
    title_cn = None
    title_en = None
    video_url = None
    upload_date = None
    content = markdown_text
    
    if markdown_text.startswith('---'):
        # 查找第二个 ---
        end_index = markdown_text.find('---', 3)
        if end_index != -1:
            # 提取 YAML front matter 内容
            yaml_content = markdown_text[3:end_index].strip()
            try:
                # 解析 YAML
                metadata = yaml.safe_load(yaml_content)
                if metadata and isinstance(metadata, dict):
                    title_cn = metadata.get('title_cn')
                    title_en = metadata.get('title_en')
                    video_url = metadata.get('video_url')
                    upload_date = metadata.get('upload_date')
            except yaml.YAMLError:
                pass  # 忽略YAML解析错误
            
            # 移除 YAML front matter 部分
            content = markdown_text[end_index + 3:].lstrip()
    
    return title_cn, title_en, video_url, upload_date, content


class MarkdownToPDFConverter:
    """Markdown到PDF转换器类"""
    
    def __init__(self, css_paths: List[str]):
        """
        初始化转换器
        
        Args:
            css_paths: CSS文件路径列表
        """
        self.css_paths = css_paths
        self._validate_css_files()
        
    def _validate_css_files(self):
        """验证CSS文件是否存在"""
        for css_path in self.css_paths:
            if not os.path.exists(css_path):
                raise FileNotFoundError(f"CSS文件不存在: {css_path}")
    
    @staticmethod
    def markdown_to_custom_html(markdown_text: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        """
        将Markdown转换为特定的HTML结构
        
        Returns:
            (html_content, title_cn, title_en, video_url)
        """
        # 解析front matter
        title_cn, title_en, video_url, upload_date, content = parse_front_matter(markdown_text)
        
        # 基础Markdown到HTML转换
        base_html = markdown.markdown(
            content, 
            extensions=['tables', 'fenced_code']
        )
        soup = BeautifulSoup(base_html, 'html.parser')

        # 包装标题内容
        for tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for header in soup.find_all(tag_name):
                content_text = header.get_text()
                header.string = ''
                
                prefix_span = soup.new_tag('span', attrs={'class': 'prefix'})
                content_span = soup.new_tag('span', attrs={'class': 'content'})
                content_span.string = content_text
                suffix_span = soup.new_tag('span', attrs={'class': 'suffix'})
                
                header.append(prefix_span)
                header.append(content_span)
                header.append(suffix_span)

        # 包装blockquote内容
        for bq in soup.find_all('blockquote'):
            if len(bq.contents) == 1 and bq.contents[0].name == 'p':
                continue
            
            p_tag = soup.new_tag('p')
            while bq.contents:
                p_tag.append(bq.contents[0].extract())
            bq.append(p_tag)

        # 包装图片
        for img in soup.find_all('img'):
            if img.parent.name != 'figure':
                figure = soup.new_tag('figure')
                img.wrap(figure)
                alt_text = img.get('alt', '')
                if alt_text:
                    figcaption = soup.new_tag('figcaption')
                    figcaption.string = alt_text
                    figure.append(figcaption)

        return str(soup), title_cn, title_en, video_url

    def generate_pdf(self, markdown_content: str, output_pdf_path: str) -> None:
        """
        将Markdown内容生成PDF文件
        
        Args:
            markdown_content: Markdown内容
            output_pdf_path: 输出PDF文件路径
        """
        # 转换Markdown到HTML
        html_body, title_cn, title_en, video_url = self.markdown_to_custom_html(markdown_content)
        
        # 如果没有获取到标题，尝试从HTML中提取第一个H1
        if not title_cn:
            soup = BeautifulSoup(html_body, 'html.parser')
            h1 = soup.find('h1')
            if h1:
                title_cn = h1.get_text().strip()
            else:
                title_cn = "AWS re:Invent Insight"
        
        # 创建完整的HTML文档，包含Hero头部
        full_html = f'''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>{title_cn}</title>
        </head>
        <body>
            <div id="nice">
        '''
        
        # 解析HTML body，在第一个H1后添加英文标题
        soup = BeautifulSoup(html_body, 'html.parser')
        h1_tag = soup.find('h1')
        if h1_tag and title_en and video_url:
            # 创建英文标题链接
            link_tag = soup.new_tag('a', href=video_url, target='_blank', attrs={'class': 'english-title-link'})
            link_tag.string = title_en
            
            # 在H1后插入
            h1_tag.insert_after(link_tag)
        
        full_html += str(soup)
        full_html += '''
            </div>
            <footer class="page-footer">
                <span class="footer-reinvent">re:Invent </span><span class="footer-insight">Insight</span>
            </footer>
        </body>
        </html>
        '''

        # 读取和准备CSS样式表
        stylesheets = []
        font_config = FontConfiguration()
        
        for css_path in self.css_paths:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_string = f.read()
            stylesheets.append(CSS(string=css_string, font_config=font_config))
        
        # 创建WeasyPrint HTML对象
        base_url = os.path.dirname(os.path.abspath(self.css_paths[0])) if self.css_paths else '.'
        html = HTML(string=full_html, base_url=base_url)

        # 生成PDF
        html.write_pdf(
            output_pdf_path,
            stylesheets=stylesheets,
            font_config=font_config
        )


class PDFBatchGenerator:
    """PDF批量生成器类"""
    
    def __init__(self, converter: MarkdownToPDFConverter):
        """
        初始化批量生成器
        
        Args:
            converter: Markdown到PDF转换器实例
        """
        self.converter = converter
        self.success_count = 0
        self.error_count = 0
        self.errors: List[Tuple[str, str]] = []
        
    def process_directory(self, input_dir: str, output_dir: str, 
                         overwrite: bool = False) -> None:
        """
        处理目录中的所有Markdown文件
        
        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            overwrite: 是否覆盖已存在的PDF文件
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取所有Markdown文件
        md_files = self._find_markdown_files(input_dir)
        
        if not md_files:
            print(f"❌ 在目录 {input_dir} 中未找到任何Markdown文件")
            return
            
        print(f"📁 找到 {len(md_files)} 个Markdown文件待处理")
        print(f"📂 输出目录: {output_dir}")
        print("-" * 60)
        
        # 处理每个文件
        for i, md_file in enumerate(md_files, 1):
            self._process_single_file(md_file, output_dir, overwrite, i, len(md_files))
            
        # 打印总结
        self._print_summary()
        
    def process_single_file(self, input_file: str, output_dir: str, 
                           overwrite: bool = False) -> None:
        """
        处理单个Markdown文件
        
        Args:
            input_file: 输入文件路径
            output_dir: 输出目录路径
            overwrite: 是否覆盖已存在的PDF文件
        """
        os.makedirs(output_dir, exist_ok=True)
        self._process_single_file(input_file, output_dir, overwrite, 1, 1)
        self._print_summary()
        
    def _find_markdown_files(self, directory: str) -> List[str]:
        """查找目录中的所有Markdown文件"""
        md_files = []
        for file in sorted(os.listdir(directory)):
            if file.endswith('.md'):
                md_files.append(os.path.join(directory, file))
        return md_files
        
    def _process_single_file(self, md_file: str, output_dir: str, 
                            overwrite: bool, current: int, total: int) -> None:
        """处理单个文件的内部方法"""
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        output_pdf = os.path.join(output_dir, f"{base_name}.pdf")
        
        # 检查是否需要跳过
        if os.path.exists(output_pdf) and not overwrite:
            print(f"⏭️  [{current}/{total}] 跳过（已存在）: {base_name}")
            return
            
        try:
            # 读取Markdown文件
            with open(md_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
                
            # 生成PDF
            print(f"🔄 [{current}/{total}] 正在处理: {base_name}")
            start_time = datetime.now()
            
            self.converter.generate_pdf(markdown_content, output_pdf)
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"✅ [{current}/{total}] 完成: {base_name} (耗时 {duration:.2f}秒)")
            self.success_count += 1
            
        except Exception as e:
            print(f"❌ [{current}/{total}] 失败: {base_name}")
            print(f"   错误: {str(e)}")
            self.error_count += 1
            self.errors.append((base_name, str(e)))
            
    def _print_summary(self) -> None:
        """打印处理总结"""
        print("-" * 60)
        print(f"📊 处理总结:")
        print(f"   ✅ 成功: {self.success_count} 个文件")
        print(f"   ❌ 失败: {self.error_count} 个文件")
        
        if self.errors:
            print("\n❌ 错误详情:")
            for filename, error in self.errors:
                print(f"   - {filename}: {error}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AWS re:Invent Insights PDF批量生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 批量转换默认目录下的所有文件
  python generate_pdfs.py
  
  # 转换特定目录下的所有文件
  python generate_pdfs.py -i path/to/markdown -o path/to/pdf
  
  # 转换单个文件
  python generate_pdfs.py -f path/to/file.md -o path/to/output
  
  # 覆盖已存在的PDF文件
  python generate_pdfs.py --overwrite
        """
    )
    
    parser.add_argument(
        '-i', '--input-dir',
        default='downloads/summaries',
        help='输入目录路径（默认: downloads/summaries）'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='downloads/pdfs',
        help='输出目录路径（默认: downloads/pdfs）'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='处理单个文件（指定此参数时忽略-i）'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='覆盖已存在的PDF文件'
    )
    
    parser.add_argument(
        '--css',
        help='自定义CSS文件路径（可选）'
    )
    
    args = parser.parse_args()
    
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 脚本现在在 src/reinvent_insight/tools 目录下，向上三级是项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    
    # 设置CSS文件路径
    if args.css:
        css_paths = [args.css]
    else:
        css_paths = [os.path.join(project_root, 'web', 'css', 'pdf_style.css')]
    
    try:
        # 创建转换器
        converter = MarkdownToPDFConverter(css_paths)
        
        # 创建批量生成器
        generator = PDFBatchGenerator(converter)
        
        # 处理文件
        if args.file:
            # 处理单个文件
            if not os.path.exists(args.file):
                print(f"❌ 错误: 文件不存在 - {args.file}")
                sys.exit(1)
            generator.process_single_file(args.file, args.output_dir, args.overwrite)
        else:
            # 批量处理目录
            if not os.path.exists(args.input_dir):
                print(f"❌ 错误: 输入目录不存在 - {args.input_dir}")
                sys.exit(1)
            generator.process_directory(args.input_dir, args.output_dir, args.overwrite)
            
    except Exception as e:
        print(f"❌ 致命错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main() 