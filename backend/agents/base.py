"""
基础Agent类 - 所有AI玩家的基类
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.game_engine.roles import ROLE_NAME_CN, ROLE_DESCRIPTION, Role

logger = logging.getLogger(__name__)


class BaseAgent:
    """AI玩家基类"""

    def __init__(
        self,
        player_id: str,
        player_name: str,
        role: Role,
        game_state_ref: Any,
        llm_client: Any,
    ):
        """
        初始化代理

        Args:
            player_id: 玩家ID
            player_name: 玩家名称
            role: 角色
            game_state_ref: 游戏状态引用
            llm_client: LLM客户端
        """
        self.player_id = player_id
        self.player_name = player_name
        self.role = role
        self.state = game_state_ref  # GameState引用
        self.llm = llm_client
        self.memory: list[dict] = []  # 个人记忆

        logger.info(f"Agent创建: {player_name} ({ROLE_NAME_CN.get(role, role.value)})")

    async def decide(self, action_type: str, context: dict) -> dict:
        """
        做出决策 - 子类必须实现

        Args:
            action_type: 操作类型 (kill, check, protect, antidote, poison, speech, vote, hunter_shoot, witch_action)
            context: 操作上下文

        Returns:
            决策字典
        """
        raise NotImplementedError(f"{self.__class__.__name__} 必须实现 decide 方法")

    def get_public_info(self) -> dict:
        """获取本玩家视角的公开信息"""
        return self.state.get_public_state(self.player_id)

    def add_memory(self, entry: dict) -> None:
        """添加记忆条目"""
        self.memory.append(entry)
        # 限制记忆大小
        if len(self.memory) > 100:
            self.memory = self.memory[-80:]

    def _get_system_prompt(self) -> str:
        """获取系统提示词（基础角色描述）"""
        role_desc = ROLE_DESCRIPTION.get(self.role, f"你是{ROLE_NAME_CN.get(self.role, '未知')}。")
        return (
            f"你正在玩一局12人的狼人杀游戏。\n"
            f"你的名字是{self.player_name}。\n"
            f"{role_desc}\n\n"
            f"游戏规则：\n"
            f"- 4个狼人，1个预言家，1个女巫，1个猎人，1个守卫，4个村民\n"
            f"- 狼人每晚可以击杀一名玩家\n"
            f"- 预言家每晚可以查验一名玩家的身份\n"
            f"- 女巫有一瓶解药和一瓶毒药，各只能用一次\n"
            f"- 守卫每晚可以守护一名玩家，不能连续两晚守同一人\n"
            f"- 猎人被投票放逐或被狼杀时可以开枪带走一人\n"
            f"- 白天发言后投票放逐一名玩家\n"
            f"- 狼人全部死亡 -> 好人胜利\n"
            f"- 存活狼人 >= 存活好人 -> 狼人胜利\n\n"
            f"请根据你的角色，做出最合理的选择。你必须严格以JSON格式回复。"
        )

    def _get_public_context_str(self) -> str:
        """获取当前公开信息字符串"""
        info = self.get_public_info()
        alive_players = [p for p in info.get("players", []) if p.get("is_alive")]
        dead_players = [p for p in info.get("players", []) if not p.get("is_alive")]

        ctx = f"当前轮次: 第{info.get('round_number', 0)}轮\n"
        ctx += f"当前阶段: {info.get('phase', '')}\n"
        ctx += f"存活玩家({len(alive_players)}): "
        ctx += ", ".join([f"{p['name']}(座位{p['seat']})" for p in alive_players])
        ctx += "\n"
        if dead_players:
            ctx += f"已死亡玩家({len(dead_players)}): "
            ctx += ", ".join([f"{p['name']}(座位{p['seat']})" for p in dead_players])
            ctx += "\n"

        # 夜晚死亡
        night_deaths = info.get("night_deaths", [])
        if night_deaths:
            ctx += f"昨晚死亡: {night_deaths}\n"

        # 发言记录
        speeches = info.get("speeches", [])
        if speeches:
            ctx += "本轮发言记录:\n"
            for s in speeches:
                ctx += f"  {s.get('player_name', '')}(座位{s.get('seat', '')}): {s.get('content', '')}\n"

        # 投票记录
        votes = info.get("votes", {})
        if votes:
            ctx += "投票记录:\n"
            for voter_id, target_id in votes.items():
                voter = next((p for p in info.get("players", []) if p["id"] == voter_id), None)
                target = next((p for p in info.get("players", []) if p["id"] == target_id), None)
                if voter and target:
                    ctx += f"  {voter['name']} -> {target['name']}\n"

        return ctx