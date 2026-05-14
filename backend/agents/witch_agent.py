"""
女巫Agent - 拥有解药和毒药，夜间决定使用策略
"""
import logging

from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class WitchAgent(BaseAgent):
    """女巫AI玩家"""

    async def decide(self, action_type: str, context: dict) -> dict:
        if action_type == "witch_action":
            return await self._decide_witch_action(context)
        elif action_type == "speech":
            return await self._decide_speech(context)
        elif action_type == "vote":
            return await self._decide_vote(context)
        else:
            logger.warning(f"女巫收到未知操作类型: {action_type}")
            return {}

    async def _decide_witch_action(self, context: dict) -> dict:
        """决定是否使用解药和毒药"""
        night_kill_target = context.get("night_kill_target")
        antidote_available = context.get("antidote_available", False)
        poison_available = context.get("poison_available", False)
        valid_poison_targets = context.get("valid_poison_targets", [])

        system = self._get_system_prompt()
        system += (
            "\n\n你的药物策略：\n"
            "解药：\n"
            "- 第一轮尽量使用解药救人，因为不知道谁会死\n"
            "- 如果被杀的是预言家等关键角色，一定要救\n"
            "- 如果游戏后期，考虑是否值得使用解药\n"
            "毒药：\n"
            "- 毒药要留到信息比较明确时使用\n"
            "- 当你比较确定某人是狼人时，可以使用毒药\n"
            "- 不要毒杀预言家或确认的好人\n"
            "- 毒药在确定目标后可以果断使用\n"
        )

        kill_info = ""
        if night_kill_target:
            target = self.state.get_player(night_kill_target)
            if target:
                kill_info = f"今晚被狼人杀害的是: {target.name}(座位{target.seat})"

        user = (
            f"{self._get_public_context_str()}\n"
            f"{kill_info}\n\n"
            f"解药可用: {'是' if antidote_available else '否'}\n"
            f"毒药可用: {'是' if poison_available else '否'}\n"
        )

        if valid_poison_targets:
            user += "可毒杀目标:\n" + "\n".join([
                f"- {t['name']}(座位{t['seat']}) [ID: {t['id']}]"
                for t in valid_poison_targets
            ])

        user += (
            f"\n\n请决定你的行动。以JSON格式回复：\n"
            f'{{"use_antidote": true/false, "use_poison": true/false, "poison_target": "玩家ID或null", "reasoning": "你的理由"}}'
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.3)
            # 确保返回格式正确
            decision = {
                "use_antidote": result.get("use_antidote", False),
                "use_poison": result.get("use_poison", False),
                "poison_target": result.get("poison_target"),
                "reasoning": result.get("reasoning", ""),
            }
            # 验证毒药目标
            if decision["use_poison"] and decision["poison_target"]:
                valid_ids = [t["id"] for t in valid_poison_targets]
                if decision["poison_target"] not in valid_ids:
                    decision["use_poison"] = False
                    decision["poison_target"] = None
            return decision
        except Exception as e:
            logger.error(f"女巫决策失败: {e}")
            # 默认：第一轮用解药，不用毒药
            return {
                "use_antidote": antidote_available and night_kill_target is not None,
                "use_poison": False,
                "poison_target": None,
                "reasoning": "默认策略（回退）",
            }

    async def _decide_speech(self, context: dict) -> dict:
        """白天发言 - 参与讨论"""
        system = self._get_system_prompt()
        system += (
            "\n\n你的发言策略：\n"
            "1. 你是女巫，但一般不应该过早暴露身份\n"
            "2. 如果你使用了解药救了某人，可以适当暗示来建立信任\n"
            "3. 分析发言，帮助好人阵营找出狼人\n"
            "4. 如果使用了解药或毒药，可以考虑适时公布信息\n"
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
            return {"speech": "我仔细听了大家的发言，有一些分析想和大家分享。", "strategy": "安全发言"}
        except Exception as e:
            logger.error(f"女巫发言决策失败: {e}")
            return {"speech": "我觉得我们应该更多关注发言中的矛盾之处。", "strategy": "安全发言（回退）"}

    async def _decide_vote(self, context: dict) -> dict:
        """投票"""
        valid_targets = context.get("valid_targets", [])

        if not valid_targets:
            return {"target": "abstain"}

        system = self._get_system_prompt()
        system += (
            "\n\n投票策略：根据发言分析，投票给最像狼人的玩家。"
            "如果你毒杀了某人且确认是狼人，可以放心投票。"
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
            logger.error(f"女巫投票决策失败: {e}")
            return {"target": "abstain"}