"""
守卫Agent - 每晚守护一名玩家，不能连续两晚守护同一人
"""
import logging

from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class GuardAgent(BaseAgent):
    """守卫AI玩家"""

    async def decide(self, action_type: str, context: dict) -> dict:
        if action_type == "protect":
            return await self._decide_protect(context)
        elif action_type == "speech":
            return await self._decide_speech(context)
        elif action_type == "vote":
            return await self._decide_vote(context)
        else:
            logger.warning(f"守卫收到未知操作类型: {action_type}")
            return {}

    async def _decide_protect(self, context: dict) -> dict:
        """决定守护目标"""
        valid_targets = context.get("valid_targets", [])
        cannot_protect = context.get("cannot_protect")

        if not valid_targets:
            return {"target": None}

        system = self._get_system_prompt()
        system += (
            "\n\n守护策略：\n"
            "1. 优先守护可能的预言家或已暴露的好人关键角色\n"
            "2. 如果没有明确目标，可以守护自己\n"
            "3. 注意！不能连续两晚守护同一人\n"
            "4. 如果某人被狼人盯上的可能性很大（如跳了预言家），重点守护\n"
            "5. 早期轮次可以守护发言较多的玩家（可能是关键角色）\n"
        )

        if cannot_protect:
            cp = self.state.get_player(cannot_protect)
            if cp:
                system += f"\n注意：你上轮守护了 {cp.name}(座位{cp.seat})，本轮不能再守护ta！"

        targets_str = "\n".join([
            f"- {t['name']}(座位{t['seat']}) [ID: {t['id']}]"
            + (" [自己]" if t['id'] == self.player_id else "")
            for t in valid_targets
        ])

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"可守护目标:\n{targets_str}\n\n"
            f"请选择今晚要守护的目标。以JSON格式回复：\n"
            f'{{"target": "玩家ID", "reasoning": "你的理由"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.3)
            target = result.get("target")
            if target and target in [t["id"] for t in valid_targets]:
                if target != cannot_protect:
                    return result
                # 如果选了不能守护的，默认守护自己
                if self.player_id in [t["id"] for t in valid_targets]:
                    return {"target": self.player_id, "reasoning": "不能连续守护同一人，改为守护自己"}
            # 回退：守护自己
            if self.player_id in [t["id"] for t in valid_targets]:
                return {"target": self.player_id, "reasoning": "默认守护自己（回退）"}
            import random
            return {"target": random.choice(valid_targets)["id"], "reasoning": "随机选择（回退）"}
        except Exception as e:
            logger.error(f"守卫守护决策失败: {e}")
            if self.player_id in [t["id"] for t in valid_targets]:
                return {"target": self.player_id, "reasoning": "默认守护自己（回退）"}
            import random
            return {"target": random.choice(valid_targets)["id"] if valid_targets else None}

    async def _decide_speech(self, context: dict) -> dict:
        """白天发言"""
        system = self._get_system_prompt()
        system += (
            "\n\n作为守卫，你的发言策略：\n"
            "1. 一般不应暴露自己是守卫\n"
            "2. 像普通村民一样参与讨论和分析\n"
            "3. 如果发现有人跳守卫身份而你知道是假的，可以适当质疑\n"
            "4. 保护好关键角色是守卫的职责\n"
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
            return {"speech": "我仔细分析了发言，觉得有些地方值得进一步讨论。", "strategy": "安全发言"}
        except Exception as e:
            logger.error(f"守卫发言决策失败: {e}")
            return {"speech": "我同意我们应该更加仔细地分析每个人的发言。", "strategy": "安全发言（回退）"}

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
            logger.error(f"守卫投票决策失败: {e}")
            return {"target": "abstain"}