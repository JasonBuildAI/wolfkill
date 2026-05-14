"""
配置文件 - 支持多模型服务商动态切换
模型列表基于2025-2026年最新信息更新
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# 预定义的模型服务商配置 - 2026年5月最新
PROVIDER_CONFIGS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": [
            {"id": "gpt-5.5", "name": "GPT-5.5"},
            {"id": "gpt-5.5-pro", "name": "GPT-5.5 Pro"},
            {"id": "gpt-5.4", "name": "GPT-5.4"},
            {"id": "gpt-5.4-pro", "name": "GPT-5.4 Pro"},
            {"id": "gpt-4.1", "name": "GPT-4.1 (1M上下文)"},
            {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"},
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "o3", "name": "o3 (推理模型)"},
            {"id": "o3-pro", "name": "o3 Pro (推理模型)"},
            {"id": "o4-mini", "name": "o4 Mini (推理模型)"},
            {"id": "o4-mini-high", "name": "o4 Mini High (推理模型)"},
        ],
        "key_url": "https://platform.openai.com/api-keys",
    },
    "azure": {
        "name": "Azure OpenAI",
        "base_url": "",
        "models": [
            {"id": "gpt-5.5", "name": "GPT-5.5"},
            {"id": "gpt-4.1", "name": "GPT-4.1"},
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "o3", "name": "o3"},
        ],
        "key_url": "https://portal.azure.com",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "models": [
            {"id": "claude-opus-4-6", "name": "Claude Opus 4.6"},
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
        ],
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": [
            {"id": "deepseek-v4-pro", "name": "DeepSeek-V4-Pro (1.6T/49B, 1M上下文)"},
            {"id": "deepseek-v4-flash", "name": "DeepSeek-V4-Flash (284B/13B, 1M上下文)"},
            {"id": "deepseek-chat", "name": "DeepSeek-V3.2 (兼容旧版)"},
            {"id": "deepseek-reasoner", "name": "DeepSeek-R1 (兼容旧版)"},
        ],
        "key_url": "https://platform.deepseek.com/api_keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            {"id": "openai/gpt-5.5", "name": "GPT-5.5 (via OpenRouter)"},
            {"id": "openai/gpt-5.5-pro", "name": "GPT-5.5 Pro (via OpenRouter)"},
            {"id": "openai/gpt-4.1", "name": "GPT-4.1 (via OpenRouter)"},
            {"id": "anthropic/claude-opus-4-6", "name": "Claude Opus 4.6 (via OpenRouter)"},
            {"id": "anthropic/claude-sonnet-4-5", "name": "Claude Sonnet 4.5 (via OpenRouter)"},
            {"id": "deepseek/deepseek-v4-pro", "name": "DeepSeek-V4-Pro (via OpenRouter)"},
            {"id": "deepseek/deepseek-v4-flash", "name": "DeepSeek-V4-Flash (via OpenRouter)"},
            {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro (via OpenRouter)"},
            {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash (via OpenRouter)"},
            {"id": "x-ai/grok-4", "name": "Grok 4 (via OpenRouter)"},
            {"id": "meta-llama/llama-4-maverick", "name": "Llama 4 Maverick (via OpenRouter)"},
            {"id": "qwen/qwen3-235b-a22b", "name": "Qwen3-235B (via OpenRouter)"},
            {"id": "openrouter/owl-alpha", "name": "Owl Alpha (via OpenRouter)"},
            {"id": "openrouter/hunter-alpha", "name": "Hunter Alpha 1T/1M (via OpenRouter)"},
        ],
        "key_url": "https://openrouter.ai/keys",
    },
    "siliconflow": {
        "name": "硅基流动 (SiliconFlow)",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": [
            {"id": "deepseek-ai/DeepSeek-V4-Pro", "name": "DeepSeek-V4-Pro"},
            {"id": "deepseek-ai/DeepSeek-V4-Flash", "name": "DeepSeek-V4-Flash"},
            {"id": "zhipuai/glm-4.5", "name": "GLM-4.5"},
            {"id": "zhipuai/glm-4.5-air", "name": "GLM-4.5-Air"},
            {"id": "zhipuai/glm-5", "name": "GLM-5"},
            {"id": "zhipuai/glm-5-turbo", "name": "GLM-5-Turbo"},
            {"id": "Qwen/Qwen3-235B-A22B", "name": "Qwen3-235B"},
            {"id": "Qwen/Qwen3-Coder-480B-A35B", "name": "Qwen3-Coder-480B"},
            {"id": "meta-llama/Llama-4-Maverick", "name": "Llama 4 Maverick"},
            {"id": "Pro/Qwen/Qwen3-8B", "name": "Qwen3-8B (免费)"},
        ],
        "key_url": "https://cloud.siliconflow.cn/account/ak",
    },
    "zhipu": {
        "name": "智谱AI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            {"id": "glm-5", "name": "GLM-5 (最新旗舰, 200K上下文)"},
            {"id": "glm-5-turbo", "name": "GLM-5-Turbo"},
            {"id": "glm-5.1", "name": "GLM-5.1 (长程任务, 8小时)"},
            {"id": "glm-4.7", "name": "GLM-4.7"},
            {"id": "glm-4.6", "name": "GLM-4.6 (高智能旗舰, 200K)"},
            {"id": "glm-4.5", "name": "GLM-4.5 (355B MoE, 128K)"},
            {"id": "glm-4.5-air", "name": "GLM-4.5-Air (高性价比)"},
            {"id": "glm-4-plus", "name": "GLM-4-Plus"},
            {"id": "glm-4.5-flash", "name": "GLM-4.5-Flash (免费)"},
            {"id": "glm-4.7-flash", "name": "GLM-4.7-Flash (免费)"},
        ],
        "key_url": "https://open.bigmodel.cn/usercenter/apikeys",
    },
    "moonshot": {
        "name": "Moonshot (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "models": [
            {"id": "kimi-k2", "name": "Kimi K2 (MoE, 免费)"},
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
            {"id": "qwen3-235b-a22b", "name": "Qwen3-235B"},
            {"id": "deepseek-v4-pro", "name": "DeepSeek-V4-Pro"},
            {"id": "deepseek-v4-flash", "name": "DeepSeek-V4-Flash"},
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
    max_tokens: int = 500


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
