"""
入口文件 - 初始化数据库并启动服务器
"""
import asyncio
import logging
import sys

import uvicorn

from backend.config import config
from backend.database import init_db


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main():
    """主函数"""
    setup_logging()

    # 验证配置
    try:
        config.validate()
    except ValueError as e:
        logging.getLogger(__name__).error(f"配置错误: {e}")
        sys.exit(1)

    # 初始化数据库
    await init_db()

    # 启动服务器
    uvicorn.run(
        "backend.server:app",
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False,
    )


if __name__ == "__main__":
    asyncio.run(main())