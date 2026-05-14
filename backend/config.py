"""
配置文件 - 支持多模型服务商动态切换
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# 预定义的模型服务商配置
PROVIDER_CONFIGS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
        ],
        "key_url": "https://platform.openai.com/api-keys",
    },
    "azure": {
        "name": "Azure OpenAI",
        "base_url": "",
        "models": [
            {"id": "gpt-4", "name": "GPT-4"},
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-35-turbo", "name": "GPT-3.5 Turbo"},
        ],
        "key_url": "https://portal.azure.com",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "models": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
        ],
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek-V3"},
            {"id": "deepseek-reasoner", "name": "DeepSeek-R1"},
        ],
        "key_url": "https://platform.deepseek.com/api_keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            {"id": "openai/gpt-4o", "name": "GPT-4o (via OpenRouter)"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet (via OpenRouter)"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash"},
            {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek-V3"},
            {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B"},
            {"id": "01-ai/yi-34b-chat", "name": "Yi-34B"},
        ],
        "key_url": "https://openrouter.ai/keys",
    },
    "siliconflow": {
        "name": "硅基流动 (SiliconFlow)",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": [
            {"id": "deepseek-ai/DeepSeek-V3", "name": "DeepSeek-V3"},
            {"id": "deepseek-ai/DeepSeek-R1", "name": "DeepSeek-R1"},
            {"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen2.5-72B"},
            {"id": "Qwen/Qwen2.5-32B-Instruct", "name": "Qwen2.5-32B"},
            {"id": "meta-llama/Llama-3.3-70B-Instruct", "name": "Llama-3.3-70B"},
            {"id": "THUDM/glm-4-9b-chat", "name": "GLM-4-9B"},
            {"id": "Pro/Qwen/Qwen2.5-7B-Instruct", "name": "Qwen2.5-7B (免费)"},
        ],
        "key_url": "https://cloud.siliconflow.cn/account/ak",
    },
    "zhipu": {
        "name": "智谱AI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            {"id": "glm-4-plus", "name": "GLM-4-Plus"},
            {"id": "glm-4", "name": "GLM-4"},
            {"id": "glm-4-air", "name": "GLM-4-Air"},
            {"id": "glm-4-flash", "name": "GLM-4-Flash (免费)"},
        ],
        "key_url": "https://open.bigmodel.cn/usercenter/apikeys",
    },
    "moonshot": {
        "name": "Moonshot (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "models": [
            {"id": "moonshot-v1-8k", "name": "Moonshot-v1-8k"},
            {"id": "moonshot-v1-32k", "name": "Moonshot-v1-32k"},
            {"id": "moonshot-v1-128k", "name": "Moonshot-v1-128k"},
        ],
        "key_url": "https://platform.moonshot.cn/console/api-keys",
    },
    "dashscope": {
        "name": "阿里云百炼 (DashScope)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": [
            {"id": "qwen-max", "name": "Qwen-Max"},
            {"id": "qwen-plus", "name": "Qwen-Plus"},
            {"id": "qwen-turbo", "name": "Qwen-Turbo"},
            {"id": "deepseek-v3", "name": "DeepSeek-V3"},
            {"id": "deepseek-r1", "name": "DeepSeek-R1"},
        ],
        "key_url": "https://dashscope.console.aliyun.com/apiKey",
    },
    "custom": {
        "name": "自定义 (Custom)",
        "base_url": "",
        "models": [],
        "key_url": "",
    },
}


@dataclass
class ModelConfig:
    """模型配置"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 500  # 支持范围: 1 - 2,000,000


class Config:
    """全局配置类"""

    # LLM 配置（兼容旧版环境变量）
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

    # 动态模型配置（可被运行时覆盖）
    _model_config: Optional[ModelConfig] = None

    @classmethod
    def get_model_config(cls) -> ModelConfig:
        """获取当前模型配置"""
        if cls._model_config is None:
            cls._model_config = ModelConfig(
                provider="openai",
                model=cls.LLM_MODEL,
                api_key=cls.LLM_API_KEY,
                base_url=cls.LLM_API_BASE,
            )
        return cls._model_config

    @classmethod
    def set_model_config(cls, config: ModelConfig) -> None:
        """设置模型配置"""
        cls._model_config = config
        # 同时更新旧版配置以保持兼容
        cls.LLM_API_KEY = config.api_key
        cls.LLM_API_BASE = config.base_url
        cls.LLM_MODEL = config.model

    @classmethod
    def get_provider_config(cls, provider: str) -> dict:
        """获取指定服务商的配置模板"""
        return PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["custom"])

    @classmethod
    def validate(cls) -> None:
        """验证必要配置"""
        cfg = cls.get_model_config()
        if not cfg.api_key:
            raise ValueError(
                "LLM API Key 未设置。请在设置页面配置模型服务商和API Key，"
                "或在 .env 文件中设置 LLM_API_KEY"
            )
        if not cfg.base_url and cfg.provider != "custom":
            provider_cfg = cls.get_provider_config(cfg.provider)
            cfg.base_url = provider_cfg["base_url"]


config = Config()
