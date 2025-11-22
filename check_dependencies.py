#!/usr/bin/env python3
"""
依赖检查脚本
检查项目所需的所有Python包是否已安装
"""

import sys
import importlib
from typing import List, Tuple

# 定义所有需要检查的依赖
DEPENDENCIES = [
    ("rich", "Rich"),
    ("dotenv", "python-dotenv"),
    ("questionary", "Questionary"),
    ("google.generativeai", "google-generativeai"),
    ("loguru", "Loguru"),
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("websockets", "WebSockets"),
    ("yt_dlp", "yt-dlp"),
    ("markdown", "Markdown"),
    ("bs4", "BeautifulSoup4"),
    ("weasyprint", "WeasyPrint"),
    ("yaml", "PyYAML"),
    ("pydantic", "Pydantic"),
    ("zhon", "Zhon"),
    ("watchdog", "Watchdog"),
    ("reportlab", "ReportLab"),
    ("packaging", "Packaging"),
    ("playwright", "Playwright"),
    ("apscheduler", "APScheduler"),
    ("click", "Click"),
    ("dashscope", "DashScope"),
]


def check_dependency(module_name: str, package_name: str) -> Tuple[bool, str]:
    """
    检查单个依赖是否已安装
    
    Args:
        module_name: Python模块名
        package_name: 包的显示名称
        
    Returns:
        (是否安装, 版本信息或错误信息)
    """
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "未知版本")
        return True, version
    except ImportError:
        return False, "未安装"
    except Exception as e:
        return False, f"错误: {e}"


def main():
    """主函数"""
    print("=" * 70)
    print("检查 reinvent-insight 项目依赖")
    print("=" * 70)
    print()
    
    missing_deps: List[str] = []
    installed_deps: List[Tuple[str, str]] = []
    
    for module_name, package_name in DEPENDENCIES:
        is_installed, info = check_dependency(module_name, package_name)
        
        if is_installed:
            installed_deps.append((package_name, info))
            print(f"✓ {package_name:<25} {info}")
        else:
            missing_deps.append(package_name)
            print(f"✗ {package_name:<25} {info}")
    
    print()
    print("=" * 70)
    print(f"总计: {len(DEPENDENCIES)} 个依赖")
    print(f"已安装: {len(installed_deps)} 个")
    print(f"缺失: {len(missing_deps)} 个")
    print("=" * 70)
    
    if missing_deps:
        print()
        print("缺失的依赖:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print()
        print("安装方法:")
        print("  pip install -e .")
        print("  或")
        print("  pip install " + " ".join(missing_deps))
        print()
        return 1
    else:
        print()
        print("✓ 所有依赖已正确安装！")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
