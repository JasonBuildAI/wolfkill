"""
游戏状态定义 - 完整的游戏状态数据结构和信息隔离
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

from backend.game_engine.roles import Phase, ROLE_TEAM, Role, Team


@dataclass
class Player:
    """玩家数据类"""
    id: str
    seat: int
    name: str
    role: Role
    is_alive: bool = True
    is_human: bool = False

    @property
    def team(self) -> Team:
        """获取玩家阵营"""
        return ROLE_TEAM[self.role]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seat": self.seat,
            "name": self.name,
            "is_alive": self.is_alive,
            "is_human": self.is_human,
        }

    def to_public_dict(self) -> dict:
        """公开信息（不含角色）"""
        return {
            "id": self.id,
            "seat": self.seat,
            "name": self.name,
            "is_alive": self.is_alive,
            "is_human": self.is_human,
        }

    def to_private_dict(self) -> dict:
        """私有信息（含角色）"""
        d = self.to_public_dict()
        d["role"] = self.role.value
        d["team"] = self.team.value
        return d


@dataclass
class GameState:
    """完整游戏状态"""
    game_id: str
    players: list[Player] = field(default_factory=list)
    phase: Phase = Phase.SETUP
    round_number: int = 1

    # 存活/死亡跟踪
    alive_player_ids: list[str] = field(default_factory=list)
    dead_player_ids: list[str] = field(default_factory=list)

    # 夜间行动
    night_kill_target: Optional[str] = None          # 狼人击杀目标
    night_deaths: list[str] = field(default_factory=list)  # 当夜死亡列表
    witch_saved_target: Optional[str] = None         # 女巫解药目标
    witch_poison_target: Optional[str] = None        # 女巫毒药目标
    guard_protected_target: Optional[str] = None     # 守卫守护目标
    protected_player: Optional[str] = None           # 当前被保护的玩家（整合后）
    seer_check_result: dict[str, bool] = field(default_factory=dict)  # player_id -> is_werewolf

    # 女巫道具状态
    witch_antidote_available: bool = True
    witch_poison_available: bool = True

    # 守卫上轮守护目标（用于判断连续守护限制）
    guard_last_protected: Optional[str] = None

    # 投票
    votes: dict[str, str] = field(default_factory=dict)        # voter_id -> target_id
    eliminated_player_id: Optional[str] = None

    # 发言
    speeches: list[dict] = field(default_factory=list)
    turn_index: int = 0     # 当前发言/行动顺序

    # 猎人开枪（被投票放逐或被狼杀时）
    hunter_shot_target: Optional[str] = None
    hunter_can_shoot: bool = False  # 被毒杀时不能开枪

    # 游戏结束
    game_over: bool = False
    winner: Optional[str] = None

    # 人类玩家交互
    waiting_for_player: Optional[str] = None
    pending_action: Optional[str] = None

    def get_player(self, player_id: str) -> Optional[Player]:
        """获取玩家对象"""
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def get_player_by_seat(self, seat: int) -> Optional[Player]:
        """按座位获取玩家"""
        for p in self.players:
            if p.seat == seat:
                return p
        return None

    def get_alive_players(self) -> list[Player]:
        """获取存活玩家列表"""
        return [p for p in self.players if p.is_alive]

    def get_dead_players(self) -> list[Player]:
        """获取死亡玩家列表"""
        return [p for p in self.players if not p.is_alive]

    def get_werewolves(self) -> list[Player]:
        """获取狼人玩家列表"""
        return [p for p in self.players if p.role == Role.WEREWOLF]

    def get_alive_werewolves(self) -> list[Player]:
        """获取存活狼人列表"""
        return [p for p in self.players if p.role == Role.WEREWOLF and p.is_alive]

    def get_alive_good_players(self) -> list[Player]:
        """获取存活好人列表"""
        return [p for p in self.players if p.team == Team.GOOD and p.is_alive]

    def get_alive_evil_players(self) -> list[Player]:
        """获取存活狼人（邪恶阵营）列表"""
        return self.get_alive_werewolves()

    def kill_player(self, player_id: str) -> None:
        """标记玩家死亡"""
        p = self.get_player(player_id)
        if p:
            p.is_alive = False
            if player_id in self.alive_player_ids:
                self.alive_player_ids.remove(player_id)
            if player_id not in self.dead_player_ids:
                self.dead_player_ids.append(player_id)

    def to_dict(self) -> dict:
        """完整状态转字典"""
        return {
            "game_id": self.game_id,
            "players": [p.to_private_dict() for p in self.players],
            "phase": self.phase.value,
            "round_number": self.round_number,
            "alive_player_ids": self.alive_player_ids,
            "dead_player_ids": self.dead_player_ids,
            "night_kill_target": self.night_kill_target,
            "night_deaths": self.night_deaths,
            "witch_saved_target": self.witch_saved_target,
            "witch_poison_target": self.witch_poison_target,
            "guard_protected_target": self.guard_protected_target,
            "protected_player": self.protected_player,
            "seer_check_result": self.seer_check_result,
            "witch_antidote_available": self.witch_antidote_available,
            "witch_poison_available": self.witch_poison_available,
            "guard_last_protected": self.guard_last_protected,
            "votes": self.votes,
            "eliminated_player_id": self.eliminated_player_id,
            "speeches": self.speeches,
            "turn_index": self.turn_index,
            "hunter_shot_target": self.hunter_shot_target,
            "hunter_can_shoot": self.hunter_can_shoot,
            "game_over": self.game_over,
            "winner": self.winner,
            "waiting_for_player": self.waiting_for_player,
            "pending_action": self.pending_action,
        }

    def get_public_state(self, requesting_player_id: str) -> dict:
        """
        获取某个玩家视角的公开状态（信息隔离）
        不同角色可见的信息不同:
        - 狼人：知道其他狼人身份
        - 预言家：知道自己的查验结果
        - 女巫：知道夜晚被杀的人
        - 其他人：只知道公开信息
        """
        player = self.get_player(requesting_player_id)
        if not player:
            return self._get_spectator_state()

        base = {
            "game_id": self.game_id,
            "phase": self.phase.value,
            "round_number": self.round_number,
            "your_role": player.role.value if player.is_alive else None,
            "your_team": player.team.value if player.is_alive else None,
            "your_id": requesting_player_id,
            "your_name": player.name,
            "your_seat": player.seat,
            "is_your_turn": (self.waiting_for_player == requesting_player_id),
            "pending_action": self.pending_action if self.waiting_for_player == requesting_player_id else None,
            "players": [],
            "night_deaths": self.night_deaths,
            "eliminated_player_id": self.eliminated_player_id,
            "speeches": self.speeches,
            "votes": self.votes,
            "game_over": self.game_over,
            "winner": self.winner,
        }

        # 构建玩家列表，根据角色决定可见信息
        for p in self.players:
            pd = p.to_public_dict()

            # 如果是自己
            if p.id == requesting_player_id:
                pd["role"] = p.role.value

            # 狼人可以看到其他狼人的角色
            if (player.role == Role.WEREWOLF and p.role == Role.WEREWOLF
                    and p.id != requesting_player_id and player.is_alive):
                pd["role"] = Role.WEREWOLF.value

            base["players"].append(pd)

        # 预言家的查验结果
        if player.role == Role.SEER and player.is_alive:
            base["seer_check_result"] = self.seer_check_result

        # 女巫知道夜晚被杀目标
        if player.role == Role.WITCH and player.is_alive:
            base["night_kill_target"] = self.night_kill_target
            base["witch_antidote_available"] = self.witch_antidote_available
            base["witch_poison_available"] = self.witch_poison_available

        # 守卫知道上轮守护目标
        if player.role == Role.GUARD and player.is_alive:
            base["guard_last_protected"] = self.guard_last_protected

        # 猎人开枪
        if player.role == Role.HUNTER and not player.is_alive:
            base["hunter_can_shoot"] = self.hunter_can_shoot

        return base

    def _get_spectator_state(self) -> dict:
        """旁观者视角（能看到所有信息）"""
        base = self.to_dict()
        base["is_spectator"] = True
        return base

    def clone(self) -> GameState:
        """深拷贝状态"""
        return copy.deepcopy(self)