#!/usr/bin/env python3
"""
Worker Pool 功能测试脚本

用法:
    python test_worker_pool.py --test basic      # 基础功能测试
    python test_worker_pool.py --test priority   # 优先级测试
    python test_worker_pool.py --test stress     # 压力测试
    python test_worker_pool.py --test all        # 全部测试
"""

import sys
import asyncio
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from reinvent_insight.worker_pool import WorkerPool, TaskPriority, WorkerTask
from reinvent_insight import config


async def test_basic():
    """基础功能测试"""
    print("\n" + "="*60)
    print("测试 1: 基础功能")
    print("="*60)
    
    # 创建 Worker Pool
    pool = WorkerPool(max_workers=2, max_queue_size=10, task_timeout=5)
    
    # 启动 pool
    await pool.start()
    print("✅ Worker Pool 启动成功")
    
    # 模拟任务执行函数
    async def mock_task(task_id):
        print(f"  执行任务: {task_id}")
        await asyncio.sleep(1)  # 模拟工作
        print(f"  完成任务: {task_id}")
    
    # 添加几个任务
    for i in range(5):
        task_id = f"task_{i}"
        await pool.add_task(
            task_id=task_id,
            task_type="test",
            url_or_path="test_url",
            priority=TaskPriority.NORMAL
        )
    
    # 等待队列完成
    print(f"等待任务完成...")
    await pool.queue.join()
    
    # 获取统计
    stats = pool.get_stats()
    print(f"\n📊 统计信息:")
    print(f"  - 总处理: {stats['total_processed']}")
    print(f"  - 成功: {stats['total_success']}")
    print(f"  - 失败: {stats['total_failed']}")
    print(f"  - 队列大小: {stats['queue_size']}")
    
    # 停止 pool
    await pool.stop()
    print("✅ Worker Pool 已停止")


async def test_priority():
    """优先级测试"""
    print("\n" + "="*60)
    print("测试 2: 优先级队列")
    print("="*60)
    
    pool = WorkerPool(max_workers=1, max_queue_size=20, task_timeout=5)
    await pool.start()
    
    # 添加不同优先级的任务
    tasks = [
        ("task_low", TaskPriority.LOW),
        ("task_normal", TaskPriority.NORMAL),
        ("task_high", TaskPriority.HIGH),
        ("task_urgent", TaskPriority.URGENT),
        ("task_low2", TaskPriority.LOW),
        ("task_normal2", TaskPriority.NORMAL),
    ]
    
    print("添加任务（顺序）:")
    for task_id, priority in tasks:
        await pool.add_task(
            task_id=task_id,
            task_type="test",
            url_or_path="test",
            priority=priority
        )
        print(f"  - {task_id}: {priority.name}")
    
    print("\n期望执行顺序: URGENT → HIGH → NORMAL → NORMAL → LOW → LOW")
    print("(同优先级按 FIFO)")
    
    # 等待完成
    await pool.queue.join()
    
    stats = pool.get_stats()
    print(f"\n✅ 所有任务已完成: {stats['total_processed']} 个")
    
    await pool.stop()


async def test_stress():
    """压力测试"""
    print("\n" + "="*60)
    print("测试 3: 压力测试")
    print("="*60)
    
    pool = WorkerPool(max_workers=3, max_queue_size=50, task_timeout=2)
    await pool.start()
    
    # 快速添加大量任务
    task_count = 30
    print(f"快速添加 {task_count} 个任务...")
    
    for i in range(task_count):
        priority = TaskPriority.NORMAL if i % 3 != 0 else TaskPriority.HIGH
        await pool.add_task(
            task_id=f"stress_task_{i}",
            task_type="test",
            url_or_path="test",
            priority=priority
        )
    
    print(f"✅ 已添加 {task_count} 个任务到队列")
    
    # 监控队列
    print("\n实时监控:")
    while pool.get_queue_size() > 0 or pool.get_stats()['current_processing'] > 0:
        stats = pool.get_stats()
        print(f"\r  队列: {stats['queue_size']:2d} | "
              f"处理中: {stats['current_processing']} | "
              f"完成: {stats['total_success']:2d} | "
              f"失败: {stats['total_failed']:2d}",
              end='', flush=True)
        await asyncio.sleep(0.5)
    
    print("\n")
    
    # 最终统计
    stats = pool.get_stats()
    print(f"📊 压力测试结果:")
    print(f"  - 总处理: {stats['total_processed']}")
    print(f"  - 成功: {stats['total_success']}")
    print(f"  - 失败: {stats['total_failed']}")
    print(f"  - 超时: {stats['total_timeout']}")
    
    await pool.stop()


async def test_queue_full():
    """测试队列已满"""
    print("\n" + "="*60)
    print("测试 4: 队列已满处理")
    print("="*60)
    
    pool = WorkerPool(max_workers=1, max_queue_size=5, task_timeout=10)
    await pool.start()
    
    # 尝试添加超过容量的任务
    print("添加任务（队列容量: 5）...")
    
    success_count = 0
    failed_count = 0
    
    for i in range(10):
        result = await pool.add_task(
            task_id=f"task_{i}",
            task_type="test",
            url_or_path="test",
            priority=TaskPriority.NORMAL
        )
        
        if result:
            success_count += 1
            print(f"  ✅ task_{i}: 成功加入队列")
        else:
            failed_count += 1
            print(f"  ❌ task_{i}: 队列已满，拒绝")
    
    print(f"\n结果:")
    print(f"  - 成功: {success_count}")
    print(f"  - 拒绝: {failed_count}")
    print(f"  - 队列大小: {pool.get_queue_size()}")
    
    await pool.stop(wait_completion=False)


async def test_timeout():
    """测试任务超时"""
    print("\n" + "="*60)
    print("测试 5: 任务超时处理")
    print("="*60)
    
    pool = WorkerPool(max_workers=2, max_queue_size=10, task_timeout=2)
    await pool.start()
    
    # 模拟长时间运行的任务
    async def long_task(task_id):
        print(f"  开始长任务: {task_id}")
        await asyncio.sleep(5)  # 超过 timeout=2
        print(f"  完成长任务: {task_id}")  # 不会执行到这里
    
    print("添加会超时的任务（超时设置: 2秒）...")
    
    await pool.add_task(
        task_id="timeout_task",
        task_type="test",
        url_or_path="test",
        priority=TaskPriority.NORMAL
    )
    
    # 等待一段时间
    await asyncio.sleep(4)
    
    stats = pool.get_stats()
    print(f"\n📊 超时统计:")
    print(f"  - 超时任务数: {stats['total_timeout']}")
    print(f"  - 失败任务数: {stats['total_failed']}")
    
    if stats['total_timeout'] > 0:
        print("✅ 超时处理正常工作")
    else:
        print("❌ 超时未正确触发")
    
    await pool.stop()


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Worker Pool 完整测试套件")
    print("="*60)
    
    await test_basic()
    await test_priority()
    await test_queue_full()
    # await test_timeout()  # 需要较长时间
    await test_stress()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成!")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Worker Pool 测试脚本")
    parser.add_argument(
        "--test",
        choices=["basic", "priority", "stress", "queue_full", "timeout", "all"],
        default="all",
        help="选择要运行的测试"
    )
    
    args = parser.parse_args()
    
    if args.test == "basic":
        asyncio.run(test_basic())
    elif args.test == "priority":
        asyncio.run(test_priority())
    elif args.test == "stress":
        asyncio.run(test_stress())
    elif args.test == "queue_full":
        asyncio.run(test_queue_full())
    elif args.test == "timeout":
        asyncio.run(test_timeout())
    elif args.test == "all":
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
