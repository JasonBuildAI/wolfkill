"""
配置文件 - 从环境变量/.env文件加载配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """全局配置类"""

    # LLM 配置
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "60.0"))

    # 数据库
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./werewolf.db")

    # 服务器
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 游戏配置
    MAX_PLAYERS: int = 12
    SPEECH_TIMEOUT: int = int(os.getenv("SPEECH_TIMEOUT", "60"))
    VOTE_TIMEOUT: int = int(os.getenv("VOTE_TIMEOUT", "30"))
    NIGHT_ACTION_TIMEOUT: int = int(os.getenv("NIGHT_ACTION_TIMEOUT", "30"))

    @classmethod
    def validate(cls) -> None:
        """验证必要配置"""
        if not cls.LLM_API_KEY:
            raise ValueError(
                "LLM_API_KEY 未设置。请在 .env 文件中设置 LLM_API_KEY，"
                "或设置环境变量 LLM_API_KEY"
            )


config = Config()