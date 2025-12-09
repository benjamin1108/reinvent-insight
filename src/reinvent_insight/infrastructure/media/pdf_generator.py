import markdown
import os
import argparse
from bs4 import BeautifulSoup, NavigableString
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def markdown_to_custom_html(markdown_text: str) -> str:
    """
    Converts Markdown to a basic HTML, then uses BeautifulSoup to
    restructure it to match the specific target DOM structure.
    """
    # Step 1: Basic Markdown to HTML conversion
    base_html = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])

    # Step 2: Restructure the HTML with BeautifulSoup
    soup = BeautifulSoup(base_html, 'html.parser')

    # Rule: Wrap header content
    for tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        for header in soup.find_all(tag_name):
            content_text = header.get_text()
            header.string = '' # Clear existing content
            
            prefix_span = soup.new_tag('span', attrs={'class': 'prefix'})
            content_span = soup.new_tag('span', attrs={'class': 'content'})
            content_span.string = content_text
            suffix_span = soup.new_tag('span', attrs={'class': 'suffix'})
            
            header.append(prefix_span)
            header.append(content_span)
            header.append(suffix_span)

    # Rule: Wrap list item content in <section>
    for li in soup.find_all('li'):
        # Create a new section tag
        section = soup.new_tag('section')
        
        # Move all children of li into the new section
        # We use a while loop because moving a child modifies the contents list
        while li.contents:
            child = li.contents[0]
            section.append(child.extract())
            
        li.append(section)

    # Rule: Wrap blockquote content in <p> if it's not already
    for bq in soup.find_all('blockquote'):
        # Check if the only child is already a <p> tag
        if len(bq.contents) == 1 and bq.contents[0].name == 'p':
            continue # Already correct structure
        
        # If not, wrap everything in a <p> tag
        p_tag = soup.new_tag('p')
        while bq.contents:
             p_tag.append(bq.contents[0].extract())
        bq.append(p_tag)

    # Rule: Wrap images in <figure> and add <figcaption>
    for img in soup.find_all('img'):
        if img.parent.name != 'figure':
            figure = soup.new_tag('figure')
            img.wrap(figure)
            alt_text = img.get('alt', '')
            if alt_text:
                figcaption = soup.new_tag('figcaption')
                figcaption.string = alt_text
                figure.append(figcaption)
                
    # Note: Complex rules for Code Blocks, TOC, Footnotes, etc. would require
    # a much more sophisticated parser or pre-processing of the markdown text.
    # The current implementation handles the most critical structural changes.

    return str(soup)


def generate_pdf_from_markdown(markdown_content: str, output_pdf_path: str, css_paths: list[str]):
    """
    Converts a Markdown string to a styled PDF file using WeasyPrint.

    Args:
        markdown_content (str): The string containing Markdown content.
        output_pdf_path (str): The file path where the output PDF will be saved.
        css_paths (list[str]): A list of file paths to the CSS stylesheets to apply.
    """
    # 1. Convert Markdown to our custom HTML structure
    html_body = markdown_to_custom_html(markdown_content)

    # 2. Wrap the HTML body in our styled container
    full_html = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Summary Report</title>
    </head>
    <body>
        <footer class="page-footer">
            <span class="footer-reinvent">re:Invent </span><span class="footer-insight">Insight</span>
        </footer>
        <div id="nice">
            {html_body}
        </div>
    </body>
    </html>
    '''

    # 3. Read and combine CSS stylesheets
    stylesheets = []
    font_config = FontConfiguration()
    for css_path in css_paths:
        try:
            # WeasyPrint can take file paths directly, but reading them allows us
            # to share a single FontConfiguration object, which is good practice.
            with open(css_path, 'r', encoding='utf-8') as f:
                css_string = f.read()
            stylesheets.append(CSS(string=css_string, font_config=font_config))
        except FileNotFoundError:
            print(f"Warning: CSS file not found at {css_path}. Skipping.")
            continue
    
    # 4. Create WeasyPrint HTML object
    # The base_url is crucial for WeasyPrint to find relative paths for assets like images or fonts
    base_url = os.path.dirname(os.path.abspath(css_paths[0])) if css_paths else '.'
    html = HTML(string=full_html, base_url=base_url)

    # 5. Write the PDF to a file
    html.write_pdf(
        output_pdf_path,
        stylesheets=stylesheets,
        font_config=font_config
    )
    print(f"Successfully generated PDF at {output_pdf_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Convert a Markdown file to a styled PDF using WeasyPrint."
    )
    parser.add_argument(
        "input_markdown",
        help="Path to the input Markdown file."
    )
    parser.add_argument(
        "output_pdf",
        help="Path for the output PDF file."
    )
    args = parser.parse_args()

    # Get the absolute path to the project root to locate the CSS files
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # --- Load only the main CSS file ---
    style_css_path = os.path.join(project_root, 'web', 'css', 'pdf_style.css')
    css_files_to_load = [style_css_path]
    # ---

    try:
        with open(args.input_markdown, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
    except FileNotFoundError:
        print(f"Error: Input markdown file not found at {args.input_markdown}")
        exit(1)
    except Exception as e:
        print(f"Error reading markdown file: {e}")
        exit(1)

    generate_pdf_from_markdown(
        markdown_content=markdown_text,
        output_pdf_path=args.output_pdf,
        css_paths=css_files_to_load
    ) 