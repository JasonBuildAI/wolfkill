"""
猎人Agent - 死亡时可以开枪带走一人
"""
import logging

from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class HunterAgent(BaseAgent):
    """猎人AI玩家"""

    async def decide(self, action_type: str, context: dict) -> dict:
        if action_type == "speech":
            return await self._decide_speech(context)
        elif action_type == "vote":
            return await self._decide_vote(context)
        elif action_type == "hunter_shoot":
            return await self._decide_shoot(context)
        else:
            logger.warning(f"猎人收到未知操作类型: {action_type}")
            return {}

    async def _decide_shoot(self, context: dict) -> dict:
        """死亡时开枪选择目标"""
        valid_targets = context.get("valid_targets", [])
        cause = context.get("cause", "死亡")

        if not valid_targets:
            return {"target": None}

        system = self._get_system_prompt()
        system += (
            f"\n\n你{cause}，可以开枪带走一名玩家！\n"
            "选择策略：\n"
            "1. 优先带走你怀疑是狼人的玩家\n"
            "2. 如果多人跳同一身份，带走最可疑的那个\n"
            "3. 带走发言最像狼人的玩家\n"
            "4. 如果完全不确定，可以选择不开枪（选null）\n"
        )

        targets_str = "\n".join([
            f"- {t['name']}(座位{t['seat']}) [ID: {t['id']}]"
            for t in valid_targets
        ])

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"可射击目标:\n{targets_str}\n\n"
            f"请选择开枪目标，或选null不开枪。以JSON格式回复：\n"
            f'{{"target": "玩家ID 或 null", "reasoning": "你的理由"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.5)
            target = result.get("target")
            if target and target in [t["id"] for t in valid_targets]:
                return result
            if target is None:
                return {"target": None, "reasoning": "选择不开枪"}
            # 回退：选择第一个
            import random
            return {"target": random.choice(valid_targets)["id"], "reasoning": "随机选择（回退）"}
        except Exception as e:
            logger.error(f"猎人开枪决策失败: {e}")
            import random
            return {"target": random.choice(valid_targets)["id"] if valid_targets else None}

    async def _decide_speech(self, context: dict) -> dict:
        """白天发言 - 可能暗示猎人身份"""
        system = self._get_system_prompt()
        system += (
            "\n\n作为猎人，你的发言策略：\n"
            "1. 正常分析发言，找出可疑之处\n"
            "2. 如果你被怀疑或被投票，可以适当暗示自己是猎人\n"
            "   （例如：'投票给我你会后悔的'）\n"
            "3. 不要过早暴露，保持信息优势\n"
            "4. 像普通村民一样参与推理和讨论\n"
        )

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"现在轮到你发言。以JSON格式回复：\n"
            f'{{"speech": "你的发言内容", "strategy": "你的策略"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.7)
            if result.get("speech"):
                return result
            return {"speech": "我同意大家应该理性分析，不放过任何可疑细节。", "strategy": "安全发言"}
        except Exception as e:
            logger.error(f"猎人发言决策失败: {e}")
            return {"speech": "我觉得我们需要冷静分析，不要被情绪左右。", "strategy": "安全发言（回退）"}

    async def _decide_vote(self, context: dict) -> dict:
        """投票"""
        valid_targets = context.get("valid_targets", [])

        if not valid_targets:
            return {"target": "abstain"}

        system = self._get_system_prompt()
        system += "\n\n投票策略：根据发言分析，投票给最像狼人的玩家。"

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
            logger.error(f"猎人投票决策失败: {e}")
            return {"target": "abstain"}