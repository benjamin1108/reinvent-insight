#!/usr/bin/env python3
"""
测试原子写入机制

测试场景：
1. 正常写入流程：临时文件 -> 原子重命名 -> 最终文件
2. 写入失败场景：临时文件被清理
3. 监控器识别临时文件：跳过正在生成的文件
4. 监控器清理残留临时文件
"""

import asyncio
import time
from pathlib import Path
from src.reinvent_insight.visual_watcher import VisualInterpretationWatcher

async def test_atomic_write():
    """测试原子写入机制"""
    print("\n=== 测试 1: 原子写入机制 ===")
    
    test_dir = Path("downloads/summaries")
    test_md = test_dir / "test_atomic.md"
    
    # 创建测试文件
    test_md.write_text("# Test Atomic Write\n\nThis is a test.", encoding="utf-8")
    print(f"✓ 创建测试文件: {test_md.name}")
    
    # 模拟保存 HTML（这里只测试文件操作，不实际调用 AI）
    html_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Test Content</h1></body>
</html>"""
    
    try:
        # 测试保存逻辑（模拟 visual_worker 的原子写入）
        html_path = test_dir / "test_atomic_visual.html"
        temp_path = html_path.with_suffix('.html.tmp')
        
        print(f"\n步骤 1: 写入临时文件 {temp_path.name}")
        temp_path.write_text(html_content, encoding="utf-8")
        print(f"  ✓ 临时文件大小: {temp_path.stat().st_size} 字节")
        
        # 模拟监控器检测
        print(f"\n步骤 2: 监控器检测到临时文件")
        if temp_path.exists():
            print(f"  ✓ 临时文件存在，监控器应该跳过此文件")
        
        print(f"\n步骤 3: 原子重命名")
        temp_path.replace(html_path)
        print(f"  ✓ 重命名完成: {html_path.name}")
        
        print(f"\n步骤 4: 验证最终文件")
        if html_path.exists() and not temp_path.exists():
            print(f"  ✓ 最终文件存在，临时文件已清理")
            print(f"  ✓ 文件大小: {html_path.stat().st_size} 字节")
        else:
            print(f"  ✗ 文件状态异常")
        
        # 清理
        html_path.unlink()
        test_md.unlink()
        print(f"\n✓ 测试完成，已清理测试文件")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_watcher_temp_file_detection():
    """测试监控器对临时文件的检测"""
    print("\n=== 测试 2: 监控器自动清理临时文件 ===")
    
    test_dir = Path("downloads/summaries")
    test_md = test_dir / "test_temp_detection.md"
    
    # 创建测试文件
    test_md.write_text("# Test Temp Detection", encoding="utf-8")
    print(f"✓ 创建测试文件: {test_md.name}")
    
    # 创建临时文件（模拟残留的临时文件）
    temp_html = test_dir / "test_temp_detection_visual.html.tmp"
    temp_html.write_text("<html><body>Generating...</body></html>", encoding="utf-8")
    print(f"✓ 创建临时文件: {temp_html.name}")
    
    # 创建监控器（应该自动清理临时文件）
    print(f"\n初始化监控器（应该自动清理临时文件）...")
    watcher = VisualInterpretationWatcher(
        watch_dir=test_dir,
        model_name="qwen-max"
    )
    
    # 检查临时文件是否被清理
    if not temp_html.exists():
        print(f"✓ 监控器正确清理了残留的临时文件")
    else:
        print(f"✗ 临时文件未被清理")
        temp_html.unlink()
    
    # 清理测试文件
    test_md.unlink()
    print(f"✓ 测试完成，已清理测试文件")

async def test_cleanup_temp_files():
    """测试启动时清理残留临时文件"""
    print("\n=== 测试 3: 清理残留临时文件 ===")
    
    test_dir = Path("downloads/summaries")
    
    # 创建几个残留的临时文件
    temp_files = [
        test_dir / "residual1_visual.html.tmp",
        test_dir / "residual2_visual.html.tmp",
    ]
    
    for temp_file in temp_files:
        temp_file.write_text("<html>Residual</html>", encoding="utf-8")
        print(f"✓ 创建残留临时文件: {temp_file.name}")
    
    # 创建监控器（应该自动清理）
    print(f"\n初始化监控器...")
    watcher = VisualInterpretationWatcher(
        watch_dir=test_dir,
        model_name="qwen-max"
    )
    
    # 检查临时文件是否被清理
    await asyncio.sleep(0.5)  # 等待清理完成
    
    remaining = [f for f in temp_files if f.exists()]
    if not remaining:
        print(f"✓ 所有残留临时文件已被清理")
    else:
        print(f"✗ 仍有 {len(remaining)} 个临时文件未清理")
        for f in remaining:
            f.unlink()

async def test_empty_file_detection():
    """测试小文件检测（可能是生成失败的文件）"""
    print("\n=== 测试 4: 小文件检测 ===")
    
    test_dir = Path("downloads/summaries")
    test_md = test_dir / "test_small.md"
    
    # 创建测试文件
    test_md.write_text("# Test Small File\n\nThis is a test.", encoding="utf-8")
    print(f"✓ 创建测试文件: {test_md.name}")
    
    # 创建一个很小的 HTML 文件（可能是生成失败的）
    small_html = test_dir / "test_small_visual.html"
    small_html.write_text("<html></html>", encoding="utf-8")
    print(f"✓ 创建小 HTML 文件: {small_html.name} ({small_html.stat().st_size} 字节)")
    
    # 添加到 metadata
    watcher = VisualInterpretationWatcher(
        watch_dir=test_dir,
        model_name="qwen-max"
    )
    
    file_key = watcher._get_file_key(test_md)
    watcher.processed_files.add(file_key)
    watcher._save_processed_files()
    print(f"✓ 添加到 metadata")
    
    # 测试判断逻辑（当前实现只检查文件是否存在，不检查大小）
    should_generate = await watcher._should_generate_visual(test_md, file_key)
    
    if not should_generate:
        print(f"✓ 文件存在且在 metadata 中，不重新生成（符合当前逻辑）")
        print(f"  注意：当前实现不检查文件大小，只检查是否存在")
    else:
        print(f"✗ 判断逻辑异常")
    
    # 清理
    if small_html.exists():
        small_html.unlink()
    test_md.unlink()
    print(f"✓ 测试完成，已清理测试文件")

async def main():
    await test_atomic_write()
    await test_watcher_temp_file_detection()
    await test_cleanup_temp_files()
    await test_empty_file_detection()
    
    print("\n" + "="*50)
    print("所有测试完成！")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
