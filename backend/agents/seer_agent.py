"""
预言家Agent - 夜间查验身份，白天分享信息
"""
import logging

from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class SeerAgent(BaseAgent):
    """预言家AI玩家"""

    async def decide(self, action_type: str, context: dict) -> dict:
        if action_type == "check":
            return await self._decide_check(context)
        elif action_type == "speech":
            return await self._decide_speech(context)
        elif action_type == "vote":
            return await self._decide_vote(context)
        else:
            logger.warning(f"预言家收到未知操作类型: {action_type}")
            return {}

    async def _decide_check(self, context: dict) -> dict:
        """决定查验目标"""
        valid_targets = context.get("valid_targets", [])
        previous_checks = context.get("previous_checks", {})

        if not valid_targets:
            return {"target": None}

        system = self._get_system_prompt()
        system += (
            "\n\n作为预言家，你需要选择查验目标。策略建议：\n"
            "1. 优先查验发言可疑或行为异常的玩家\n"
            "2. 可以查验关键位置（如中间座位）的玩家\n"
            "3. 避免重复查验已知身份的玩家\n"
        )

        if previous_checks:
            system += "\n之前查验结果：\n"
            for pid, is_wolf in previous_checks.items():
                player = self.state.get_player(pid)
                if player:
                    system += f"- {player.name}(座位{player.seat}): {'狼人' if is_wolf else '好人'}\n"

        targets_str = "\n".join([
            f"- {t['name']}(座位{t['seat']}) [ID: {t['id']}]"
            for t in valid_targets
            if t['id'] not in previous_checks
        ])

        user = (
            f"{self._get_public_context_str()}\n\n"
            f"可查验目标:\n{targets_str}\n\n"
            f"请选择今晚要查验的目标。以JSON格式回复：\n"
            f'{{"target": "玩家ID", "reasoning": "你的理由"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.3)
            if result.get("target") and result["target"] in [t["id"] for t in valid_targets]:
                return result
            import random
            uncheck = [t for t in valid_targets if t['id'] not in previous_checks]
            if uncheck:
                return {"target": random.choice(uncheck)["id"]}
            return {"target": random.choice(valid_targets)["id"] if valid_targets else None}
        except Exception as e:
            logger.error(f"预言家查验决策失败: {e}")
            import random
            return {"target": random.choice(valid_targets)["id"] if valid_targets else None}

    async def _decide_speech(self, context: dict) -> dict:
        """白天发言 - 分享查验信息"""
        system = self._get_system_prompt()
        system += (
            "\n\n你是预言家。你的发言策略：\n"
            "1. 如果你查验到了狼人，可以考虑适当方式告诉大家\n"
            "2. 如果你查验了多个好人，可以建立信任链\n"
            "3. 注意不要过早暴露自己是预言家，以免被狼人盯上\n"
            "4. 发言要有逻辑和分析，不要过于武断\n"
            "5. 如果形势危急（好人阵营处于劣势），可以跳预言家身份\n"
        )

        # 加入之前查验的信息
        info = self.get_public_info()
        checks = info.get("seer_check_result", {})
        if checks:
            system += "\n\n你已知的查验结果：\n"
            for pid, is_wolf in checks.items():
                player = self.state.get_player(pid)
                if player:
                    system += f"- {player.name}(座位{player.seat}): {'狼人' if is_wolf else '好人'}\n"

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
            return {"speech": "我仔细分析了大家的发言，有一些发现想和大家分享。", "strategy": "安全发言"}
        except Exception as e:
            logger.error(f"预言家发言决策失败: {e}")
            return {"speech": "我暂时没有特别确定的信息，想听听更多人的看法。", "strategy": "安全发言（回退）"}

    async def _decide_vote(self, context: dict) -> dict:
        """投票 - 投票给狼人"""
        valid_targets = context.get("valid_targets", [])

        if not valid_targets:
            return {"target": "abstain"}

        system = self._get_system_prompt()
        system += (
            "\n\n投票策略：优先投票给你查验到的狼人。" 
            "如果没有确定的狼人，根据发言分析投给最可疑的玩家。"
        )

        # 提示查验到的狼人
        info = self.get_public_info()
        checks = info.get("seer_check_result", {})
        wolf_candidates = []
        for pid, is_wolf in checks.items():
            if is_wolf and pid in [t["id"] for t in valid_targets]:
                player = self.state.get_player(pid)
                if player:
                    wolf_candidates.append(f"{player.name}(座位{player.seat}) [ID:{pid}]")

        if wolf_candidates:
            system += f"\n\n你查验到的狼人: {', '.join(wolf_candidates)}"

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
            result = await self.llm.chat_json(messages, temperature=0.3)
            target = result.get("target", "abstain")
            if target in [t["id"] for t in valid_targets] or target == "abstain":
                return result
            return {"target": "abstain"}
        except Exception as e:
            logger.error(f"预言家投票决策失败: {e}")
            return {"target": "abstain"}