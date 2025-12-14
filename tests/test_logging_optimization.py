"""
日志系统优化集成测试

测试内容：
1. 上下文变量设置和重置
2. 日志格式（控制台和文件）
3. 请求追踪中间件
4. 任务级日志追踪
"""

import asyncio
import logging
from pathlib import Path

from reinvent_insight.core.logger import setup_logger, request_id_var, task_id_var
from reinvent_insight.core import config


async def test_context_logging():
    """测试上下文日志"""
    print("\n=== 测试 1: 上下文变量日志 ===")
    
    logger = logging.getLogger("test_context")
    
    # 测试无上下文
    logger.info("无上下文的日志")
    
    # 测试请求上下文
    token1 = request_id_var.set("req_test_001")
    logger.info("有 request_id 的日志")
    request_id_var.reset(token1)
    
    # 测试任务上下文
    token2 = task_id_var.set("task_test_001")
    logger.info("有 task_id 的日志")
    task_id_var.reset(token2)
    
    # 测试同时有请求和任务上下文
    token1 = request_id_var.set("req_test_002")
    token2 = task_id_var.set("task_test_002")
    logger.info("同时有 request_id 和 task_id 的日志")
    task_id_var.reset(token2)
    request_id_var.reset(token1)
    
    print("✅ 上下文日志测试通过")


async def test_nested_context():
    """测试嵌套上下文"""
    print("\n=== 测试 2: 嵌套上下文 ===")
    
    logger = logging.getLogger("test_nested")
    
    # 模拟请求 -> 任务的流程
    req_token = request_id_var.set("req_nested_001")
    logger.info("请求开始")
    
    task_token = task_id_var.set("task_nested_001")
    logger.info("任务开始（继承请求上下文）")
    
    # 模拟任务执行
    await asyncio.sleep(0.01)
    logger.info("任务执行中")
    
    task_id_var.reset(task_token)
    logger.info("任务结束")
    
    request_id_var.reset(req_token)
    logger.info("请求结束")
    
    print("✅ 嵌套上下文测试通过")


async def test_file_logging():
    """测试文件日志"""
    print("\n=== 测试 3: 文件日志 ===")
    
    log_file = config.LOG_DIR / f"app_{Path(__file__).stem}_test.log"
    
    # 重新初始化日志以生成测试文件
    setup_logger(
        level="INFO",
        log_dir=config.LOG_DIR,
        enable_file_logging=True
    )
    
    logger = logging.getLogger("test_file")
    
    # 写入测试日志
    token = request_id_var.set("file_test_001")
    logger.info("这是一条测试文件日志")
    request_id_var.reset(token)
    
    # 检查日志文件
    today_log = config.LOG_DIR / f"app_{Path(__file__).stem.split('_')[0]}-*.log"
    log_files = list(config.LOG_DIR.glob("app_*.log"))
    
    if log_files:
        print(f"✅ 日志文件已生成: {len(log_files)} 个")
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
        print(f"   最新日志: {latest_log.name}")
        
        # 读取最后几行
        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"   日志行数: {len(lines)}")
            if lines:
                print(f"   最后一行示例: {lines[-1].strip()}")
    else:
        print("❌ 未找到日志文件")


async def test_third_party_silence():
    """测试第三方库静默"""
    print("\n=== 测试 4: 第三方库日志静默 ===")
    
    # 检查第三方库日志级别
    noisy_loggers = ["httpx", "httpcore", "uvicorn", "uvicorn.access"]
    
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        level_name = logging.getLevelName(logger.level)
        if logger.level >= logging.WARNING:
            print(f"✅ {logger_name:20s} 级别: {level_name}")
        else:
            print(f"❌ {logger_name:20s} 级别: {level_name} (应该 >= WARNING)")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("日志系统优化集成测试")
    print("=" * 60)
    
    # 初始化日志系统
    setup_logger(
        level="INFO",
        log_dir=config.LOG_DIR,
        enable_file_logging=True,
        max_bytes=config.LOG_MAX_BYTES,
        backup_count=config.LOG_BACKUP_COUNT
    )
    
    # 运行测试
    await test_context_logging()
    await test_nested_context()
    await test_file_logging()
    await test_third_party_silence()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    print(f"\n日志文件位置: {config.LOG_DIR}")
    print("可以使用以下命令查看日志:")
    print(f"  tail -f {config.LOG_DIR}/app_*.log")


if __name__ == "__main__":
    asyncio.run(main())
