"""
村民Agent - 无特殊能力，依靠分析和投票
"""
import logging

from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class VillagerAgent(BaseAgent):
    """村民AI玩家"""

    async def decide(self, action_type: str, context: dict) -> dict:
        if action_type == "speech":
            return await self._decide_speech(context)
        elif action_type == "vote":
            return await self._decide_vote(context)
        else:
            logger.warning(f"村民收到未知操作类型: {action_type}")
            return {}

    async def _decide_speech(self, context: dict) -> dict:
        """白天发言 - 分析发言找出狼人"""
        system = self._get_system_prompt()
        system += (
            "\n\n作为村民，你没有特殊能力，但你的发言和投票至关重要。发言策略：\n"
            "1. 仔细分析其他玩家的发言，寻找矛盾和不自然之处\n"
            "2. 注意那些过于激进或过于沉默的玩家\n"
            "3. 尝试发现狼人可能的配合和协调\n"
            "4. 如果发现了可疑之处，明确指出并给出分析\n"
            "5. 保持理性冷静，不要情绪化\n"
            "6. 如果有人跳特殊身份（预言家、女巫等），仔细判断其可信度\n"
        )

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"现在轮到你发言。以JSON格式回复：\n"
            f'{{"speech": "你的发言内容", "suspicion": "你最怀疑的玩家及理由"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.7)
            if result.get("speech"):
                return result
            return {"speech": "我注意到有些玩家的发言有矛盾之处，我建议我们重点关注。", "suspicion": "需要更多信息"}
        except Exception as e:
            logger.error(f"村民发言决策失败: {e}")
            return {"speech": "我觉得我们需要更多讨论，现在下结论还为时过早。", "suspicion": "暂无"}

    async def _decide_vote(self, context: dict) -> dict:
        """投票"""
        valid_targets = context.get("valid_targets", [])

        if not valid_targets:
            return {"target": "abstain"}

        system = self._get_system_prompt()
        system += (
            "\n\n投票策略：\n"
            "1. 根据发言分析投票给最可疑的人\n"
            "2. 如果某人有明显的狼人特征（矛盾发言、跟风、保狼嫌疑），优先投票\n"
            "3. 避免弃权，每一票都可能决定胜负\n"
        )

        targets_str = "\n".join([
            f"- {t['name']}(座位{t['seat']}) [ID: {t['id']}]"
            for t in valid_targets
        ])

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"可投票目标:\n{targets_str}\n\n"
            f"请投票放逐一名玩家。以JSON格式回复：\n"
            f'{{"target": "玩家ID 或 abstain", "reasoning": "你的理由"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.5)
            target = result.get("target", "abstain")
            if target in [t["id"] for t in valid_targets] or target == "abstain":
                return result
            return {"target": "abstain"}
        except Exception as e:
            logger.error(f"村民投票决策失败: {e}")
            return {"target": "abstain"}