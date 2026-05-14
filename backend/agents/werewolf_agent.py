"""
狼人Agent - 知道其他狼人身份，夜间协同击杀，白天伪装
"""
import json
import logging

from backend.agents.base import BaseAgent
from backend.game_engine.roles import Role

logger = logging.getLogger(__name__)


class WerewolfAgent(BaseAgent):
    """狼人AI玩家"""

    async def decide(self, action_type: str, context: dict) -> dict:
        if action_type == "kill":
            return await self._decide_kill(context)
        elif action_type == "speech":
            return await self._decide_speech(context)
        elif action_type == "vote":
            return await self._decide_vote(context)
        else:
            logger.warning(f"狼人收到未知操作类型: {action_type}")
            return {}

    async def _decide_kill(self, context: dict) -> dict:
        """决定击杀目标"""
        valid_targets = context.get("valid_targets", [])
        fellow_wolves = context.get("fellow_werewolves", [])

        if not valid_targets:
            return {"target": None}

        system = self._get_system_prompt()
        system += (
            "\n\n你的狼人同伴：\n"
            + "\n".join([f"- {w['name']}(座位{w['seat']})" for w in fellow_wolves])
            + "\n\n作为狼人，你和同伴需要统一击杀一个目标。"
            "优先击杀有特殊能力的好人（如预言家、女巫、守卫），"
            "或击杀那些发言最有说服力、最可能威胁狼人的玩家。"
            "避免击杀狼人同伴！"
        )

        targets_str = "\n".join([
            f"- {t['name']}(座位{t['seat']}) [ID: {t['id']}]"
            for t in valid_targets
        ])

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"可选攻击目标:\n{targets_str}\n\n"
            f"请选择今晚要击杀的目标。以JSON格式回复：\n"
            f'{{"target": "玩家ID", "reasoning": "你的理由"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.5)
            if result.get("target") and result["target"] in [t["id"] for t in valid_targets]:
                return result
            # 回退：随机选择
            import random
            return {"target": random.choice(valid_targets)["id"], "reasoning": "随机选择（回退）"}
        except Exception as e:
            logger.error(f"狼人击杀决策失败: {e}")
            import random
            return {"target": random.choice(valid_targets)["id"] if valid_targets else None}

    async def _decide_speech(self, context: dict) -> dict:
        """白天发言 - 伪装成村民"""
        system = self._get_system_prompt()
        system += (
            "\n\n你是狼人，但白天你必须伪装成好人。你的发言策略：\n"
            "1. 表现得像一个普通村民，分析场上局势\n"
            "2. 可以适当怀疑某些玩家，但不要指控狼人同伴\n"
            "3. 可以假装分析狼人可能的策略，但不要暴露真实信息\n"
            "4. 如果你被怀疑，要为自己辩护\n"
            "5. 自然、合理，不要过于激进或过于保守\n"
            "6. 尽量把怀疑引向好人阵营的玩家\n"
        )

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"现在轮到你发言。请发表你的看法。以JSON格式回复：\n"
            f'{{"speech": "你的发言内容", "strategy": "你的策略简述"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.7)
            if result.get("speech"):
                return result
            return {"speech": "我觉得我们应该仔细分析每个人的发言，找出可疑之处。", "strategy": "安全发言"}
        except Exception as e:
            logger.error(f"狼人发言决策失败: {e}")
            return {"speech": "我暂时没有什么特别的发现，想听听大家的看法。", "strategy": "安全发言（回退）"}

    async def _decide_vote(self, context: dict) -> dict:
        """投票 - 投票淘汰好人"""
        valid_targets = context.get("valid_targets", [])

        if not valid_targets:
            return {"target": "abstain"}

        system = self._get_system_prompt()
        system += (
            "\n\n作为狼人，投票时你应该：\n"
            "1. 投票给好人阵营玩家，避免投票给狼人同伴\n"
            "2. 可以选择跟票大多数人，避免显得过于突兀\n"
            "3. 如果有狼人同伴被怀疑，尽量投票给其他人分散火力\n"
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
            logger.error(f"狼人投票决策失败: {e}")
            return {"target": "abstain"}