"""
LLM客户端 - 使用OpenAI兼容API进行语言模型调用
支持重试、错误处理和结构化JSON输出
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from backend.config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """异步LLM客户端"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_API_BASE,
            timeout=config.LLM_TIMEOUT,
            max_retries=config.LLM_MAX_RETRIES,
        )
        self.model = config.LLM_MODEL

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """
        发送聊天请求并返回文本响应

        Args:
            messages: 消息列表 [{"role": "system"/"user"/"assistant", "content": str}]
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            模型响应文本
        """
        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                return content.strip() if content else ""

            except Exception as e:
                logger.warning(
                    f"LLM调用失败 (尝试 {attempt + 1}/{config.LLM_MAX_RETRIES}): {e}"
                )
                if attempt < config.LLM_MAX_RETRIES - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                else:
                    logger.error(f"LLM调用最终失败: {e}")
                    raise

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> dict:
        """
        发送聊天请求并解析JSON响应

        Args:
            messages: 消息列表
            temperature: 温度参数（JSON模式建议较低温度）
            max_tokens: 最大token数

        Returns:
            解析后的JSON字典
        """
        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if content:
                    return json.loads(content.strip())
                return {}

            except json.JSONDecodeError as e:
                logger.warning(
                    f"JSON解析失败 (尝试 {attempt + 1}/{config.LLM_MAX_RETRIES}): {e}"
                )
                if attempt < config.LLM_MAX_RETRIES - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error(f"JSON解析最终失败")
                    return {}

            except Exception as e:
                logger.warning(
                    f"LLM调用失败 (尝试 {attempt + 1}/{config.LLM_MAX_RETRIES}): {e}"
                )
                if attempt < config.LLM_MAX_RETRIES - 1:
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