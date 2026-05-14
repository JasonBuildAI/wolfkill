"""
LLM客户端 - 支持多模型服务商动态切换
使用OpenAI兼容API进行语言模型调用
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from backend.config import Config, ModelConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """异步LLM客户端 - 支持动态配置"""

    def __init__(self, model_config: Optional[ModelConfig] = None):
        self._config = model_config or Config.get_model_config()
        self._client: Optional[AsyncOpenAI] = None
        self._refresh_client()

    def _refresh_client(self) -> None:
        """刷新底层OpenAI客户端"""
        self._client = AsyncOpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            timeout=Config.LLM_TIMEOUT,
            max_retries=Config.LLM_MAX_RETRIES,
        )

    def update_config(self, model_config: ModelConfig) -> None:
        """更新配置并刷新客户端"""
        self._config = model_config
        self._refresh_client()
        logger.info(f"LLM配置已更新: provider={model_config.provider}, model={model_config.model}")

    @property
    def model(self) -> str:
        return self._config.model

    @property
    def config(self) -> ModelConfig:
        return self._config

    async def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        发送聊天请求并返回文本响应
        """
        temp = temperature if temperature is not None else self._config.temperature
        tokens = max_tokens if max_tokens is not None else self._config.max_tokens

        for attempt in range(Config.LLM_MAX_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    model=self._config.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                )
                content = response.choices[0].message.content
                return content.strip() if content else ""

            except Exception as e:
                logger.warning(
                    f"LLM调用失败 (尝试 {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}"
                )
                if attempt < Config.LLM_MAX_RETRIES - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                else:
                    logger.error(f"LLM调用最终失败: {e}")
                    raise

    async def chat_json(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """
        发送聊天请求并解析JSON响应
        """
        temp = temperature if temperature is not None else self._config.temperature
        tokens = max_tokens if max_tokens is not None else self._config.max_tokens

        for attempt in range(Config.LLM_MAX_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    model=self._config.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if content:
                    return json.loads(content.strip())
                return {}

            except json.JSONDecodeError as e:
                logger.warning(
                    f"JSON解析失败 (尝试 {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}"
                )
                if attempt < Config.LLM_MAX_RETRIES - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error(f"JSON解析最终失败")
                    return {}

            except Exception as e:
                logger.warning(
                    f"LLM调用失败 (尝试 {attempt + 1}/{Config.LLM_MAX_RETRIES}): {e}"
                )
                if attempt < Config.LLM_MAX_RETRIES - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                else:
                    logger.error(f"LLM调用最终失败: {e}")
                    return {}


# 全局LLM客户端单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局LLM客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def update_llm_client(model_config: ModelConfig) -> LLMClient:
    """更新全局LLM客户端配置"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(model_config)
    else:
        _llm_client.update_config(model_config)
    return _llm_client
