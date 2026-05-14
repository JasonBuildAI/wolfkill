"""
游戏引擎 - 狼人杀核心游戏逻辑
处理完整的游戏流程：角色分配、夜晚行动、白天发言投票、胜负判定
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from collections import Counter
from typing import Any, Callable, Optional

from backend.database import add_log, update_game_status
from backend.game_engine.roles import (
    DEFAULT_ROLES,
    ROLE_DESCRIPTION,
    ROLE_NAME_CN,
    Phase,
    Role,
    Team,
)
from backend.game_engine.state import GameState, Player

logger = logging.getLogger(__name__)

# 阶段流转顺序（除了SETUP和GAME_OVER外）
PHASE_ORDER: list[Phase] = [
    Phase.NIGHT_GUARD,
    Phase.NIGHT_WEREWOLF,
    Phase.NIGHT_SEER,
    Phase.NIGHT_WITCH,
    Phase.DAY_ANNOUNCE,
    Phase.DAY_SPEECH,
    Phase.DAY_VOTE,
    Phase.DAY_RESULT,
    Phase.CHECK_END,
]

# 需要人类玩家操作的动作类型映射
HUMAN_ACTION_PHASES: dict[Phase, str] = {
    Phase.NIGHT_GUARD: "protect",
    Phase.NIGHT_WEREWOLF: "kill",
    Phase.NIGHT_SEER: "check",
    Phase.NIGHT_WITCH: "witch_action",
    Phase.DAY_SPEECH: "speech",
    Phase.DAY_VOTE: "vote",
}


class GameEngine:
    """
    狼人杀游戏引擎
    管理游戏状态转换、玩家行动收集、阶段处理
    """

    def __init__(
        self,
        game_id: str,
        player_configs: list[dict],
        agent_factory: Callable[[str, str, Role], Any],
        callbacks: Optional[dict[str, Callable]] = None,
    ):
        """
        初始化引擎

        Args:
            game_id: 游戏ID
            player_configs: 玩家配置列表 [{"id": str, "name": str, "is_human": bool}, ...]
            agent_factory: AI代理工厂函数 (player_id, player_name, role) -> agent
            callbacks: 回调函数字典 {
                "on_state_update": async callable(state),
                "on_phase_change": async callable(phase, round_num, state),
                "on_log": async callable(log_entry),
                "on_human_action_required": async callable(player_id, action_type, state),
            }
        """
        self.game_id = game_id
        self.player_configs = player_configs
        self.agent_factory = agent_factory
        self.callbacks = callbacks or {}

        self.state = GameState(game_id=game_id)
        self.agents: dict[str, Any] = {}  # player_id -> agent
        self.human_decisions: dict[str, dict] = {}  # player_id -> decision

        self._running = False
        self._phase_lock = asyncio.Lock()
        self._human_event = asyncio.Event()
        self._current_human_player: Optional[str] = None

    # ========== 回调辅助 ==========

    async def _emit_state_update(self) -> None:
        """通知状态更新"""
        cb = self.callbacks.get("on_state_update")
        if cb:
            await cb(self.state)

    async def _emit_phase_change(self) -> None:
        """通知阶段变化"""
        cb = self.callbacks.get("on_phase_change")
        if cb:
            await cb(self.state.phase.value, self.state.round_number, self.state)

    async def _emit_log(self, action_type: str, content: str,
                        player_id: Optional[str] = None,
                        role: Optional[str] = None) -> None:
        """记录并通知日志"""
        log_entry = {
            "game_id": self.game_id,
            "round_num": self.state.round_number,
            "phase": self.state.phase.value,
            "player_id": player_id,
            "role": role,
            "action_type": action_type,
            "content": content,
        }
        # 持久化
        try:
            await add_log(
                game_id=self.game_id,
                round_num=self.state.round_number,
                phase=self.state.phase.value,
                player_id=player_id,
                role=role,
                action_type=action_type,
                content=content,
            )
        except Exception as e:
            logger.error(f"日志持久化失败: {e}")

        cb = self.callbacks.get("on_log")
        if cb:
            await cb(log_entry)

    async def _emit_human_action_required(self, player_id: str,
                                          action_type: str) -> None:
        """通知需要人类玩家操作"""
        cb = self.callbacks.get("on_human_action_required")
        if cb:
            await cb(player_id, action_type, self.state)

    # ========== 游戏流程入口 ==========

    async def start_game(self) -> None:
        """启动游戏 - 分配角色、通知玩家"""
        await self._phase_setup()
        await self._emit_state_update()
        await self._emit_phase_change()
        await self._emit_log("game_start", f"游戏开始，{len(self.state.players)}名玩家就位")

    async def process_next_phase(self) -> GameState:
        """
        处理下一个阶段
        返回更新后的状态
        """
        if self.state.game_over:
            return self.state

        async with self._phase_lock:
            # 确定当前/下一个阶段
            if self.state.phase == Phase.SETUP:
                await self._start_new_round()
                return self.state
            elif self.state.phase == Phase.GAME_OVER:
                return self.state
            elif self.state.phase == Phase.CHECK_END:
                # 检查胜负 -> 继续下一轮或结束
                await self._phase_check_end()
                if self.state.game_over:
                    return self.state
                # 新一轮
                await self._start_new_round()
                return self.state

            # 按阶段顺序推进
            current_idx = PHASE_ORDER.index(self.state.phase)
            next_phase = PHASE_ORDER[current_idx + 1] if current_idx + 1 < len(PHASE_ORDER) else None

            if next_phase is None:
                # 不应该到达这里
                await self._phase_check_end()
                return self.state

            self.state.phase = next_phase
            await self._emit_phase_change()

            await self._process_phase(next_phase)
            await self._emit_state_update()

        return self.state

    async def run_game_loop(self) -> GameState:
        """
        运行完整的游戏主循环（用于自动游戏）
        """
        self._running = True
        try:
            while self._running and not self.state.game_over:
                await self.process_next_phase()
                # 给异步任务一点时间
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.exception(f"游戏循环异常: {e}")
        finally:
            self._running = False

        return self.state

    async def submit_human_action(self, player_id: str, action: dict) -> bool:
        """
        提交人类玩家的操作

        Args:
            player_id: 玩家ID
            action: 操作数据 {"action_type": str, "target": str/None, "speech": str/None, ...}

        Returns:
            是否成功提交
        """
        if self.state.waiting_for_player != player_id:
            logger.warning(f"当前不是玩家 {player_id} 的行动回合")
            return False

        self.human_decisions[player_id] = action
        self._current_human_player = None
        self._human_event.set()
        return True

    # ========== 阶段处理 ==========

    async def _start_new_round(self) -> None:
        """开始新一轮"""
        self.state.round_number += 1
        self.state.night_kill_target = None
        self.state.night_deaths = []
        self.state.witch_saved_target = None
        self.state.witch_poison_target = None
        self.state.guard_protected_target = None
        self.state.protected_player = None
        self.state.votes = {}
        self.state.eliminated_player_id = None
        self.state.hunter_shot_target = None
        self.state.hunter_can_shoot = False
        self.state.speeches = []
        self.state.turn_index = 0
        self.state.waiting_for_player = None
        self.state.pending_action = None

        self.state.phase = PHASE_ORDER[0]  # NIGHT_GUARD
        await self._emit_phase_change()
        await self._emit_log("round_start", f"第 {self.state.round_number} 轮开始",
                             player_id=None, role=None)

        await self._process_phase(self.state.phase)
        await self._emit_state_update()

    async def _process_phase(self, phase: Phase) -> None:
        """根据阶段类型调用对应的处理器"""
        handlers = {
            Phase.SETUP: self._phase_setup,
            Phase.NIGHT_GUARD: self._phase_night_guard,
            Phase.NIGHT_WEREWOLF: self._phase_night_werewolf,
            Phase.NIGHT_SEER: self._phase_night_seer,
            Phase.NIGHT_WITCH: self._phase_night_witch,
            Phase.DAY_ANNOUNCE: self._phase_day_announce,
            Phase.DAY_SPEECH: self._phase_day_speech,
            Phase.DAY_VOTE: self._phase_day_vote,
            Phase.DAY_RESULT: self._phase_day_result,
            Phase.CHECK_END: self._phase_check_end,
        }
        handler = handlers.get(phase)
        if handler:
            await handler()
        else:
            logger.error(f"未知阶段: {phase}")

    # ========== 阶段实现 ==========

    async def _phase_setup(self) -> None:
        """SETUP阶段：分配角色，初始化状态"""
        # 随机分配角色
        shuffled_roles = list(DEFAULT_ROLES)
        random.shuffle(shuffled_roles)

        players = []
        for i, cfg in enumerate(self.player_configs):
            role = shuffled_roles[i]
            player = Player(
                id=cfg["id"],
                seat=i + 1,
                name=cfg.get("name", f"玩家{i + 1}"),
                role=role,
                is_alive=True,
                is_human=cfg.get("is_human", False),
            )
            players.append(player)

        self.state.players = players
        self.state.alive_player_ids = [p.id for p in players]
        self.state.dead_player_ids = []
        self.state.phase = Phase.SETUP
        self.state.round_number = 0

        # 创建AI代理
        for player in players:
            if not player.is_human:
                agent = self.agent_factory(player.id, player.name, player.role)
                self.agents[player.id] = agent

        # 通知各玩家角色
        await self._emit_log("role_assignment", "角色分配完成，各玩家查看自己的身份")

        # 通知狼人同伴
        werewolves = [p for p in players if p.role == Role.WEREWOLF]
        werewolf_names = [f"{w.name}(座位{w.seat})" for w in werewolves]
        for ww in werewolves:
            await self._emit_log(
                "werewolf_info",
                f"狼人同伴: {', '.join(werewolf_names)}",
                player_id=ww.id,
                role=Role.WEREWOLF.value,
            )

        self.state.phase = Phase.SETUP

    async def _phase_night_guard(self) -> None:
        """夜晚-守卫阶段：守卫选择守护目标"""
        await self._emit_log("phase_start", "夜晚降临，守卫请睁眼选择守护目标")

        guard = next((p for p in self.state.get_alive_players()
                      if p.role == Role.GUARD), None)

        if guard is None:
            await self._emit_log("phase_skip", "守卫已死亡，跳过守卫阶段")
            return

        # 守卫可选目标：所有存活玩家
        valid_targets = [p for p in self.state.get_alive_players()]

        decision = await self._get_decision(
            player=guard,
            action_type="protect",
            context={
                "valid_targets": [{"id": p.id, "name": p.name, "seat": p.seat}
                                  for p in valid_targets],
                "cannot_protect": self.state.guard_last_protected,
            },
        )

        target_id = decision.get("target") if decision else None

        if target_id and target_id != self.state.guard_last_protected:
            self.state.guard_protected_target = target_id
            target_obj = self.state.get_player(target_id)
            await self._emit_log(
                "guard_protect",
                f"守卫守护了 {target_obj.name}(座位{target_obj.seat})" if target_obj else "守卫守护了未知玩家",
                player_id=guard.id,
                role=Role.GUARD.value,
            )
        elif target_id == self.state.guard_last_protected:
            await self._emit_log(
                "guard_skip",
                "守卫不能连续两晚守护同一人，放弃守护",
                player_id=guard.id,
                role=Role.GUARD.value,
            )
            self.state.guard_protected_target = None
        else:
            self.state.guard_protected_target = None
            await self._emit_log(
                "guard_skip",
                "守卫选择不守护",
                player_id=guard.id,
                role=Role.GUARD.value,
            )

    async def _phase_night_werewolf(self) -> None:
        """夜晚-狼人阶段：狼人集体决定击杀目标"""
        await self._emit_log("phase_start", "狼人请睁眼，选择击杀目标")

        alive_wolves = self.state.get_alive_werewolves()
        if not alive_wolves:
            await self._emit_log("phase_skip", "没有存活的狼人，跳过狼人阶段")
            return

        # 候选目标：所有存活非狼人玩家
        valid_targets = [p for p in self.state.get_alive_players()
                         if p.role != Role.WEREWOLF]

        if not valid_targets:
            await self._emit_log("phase_skip", "没有可攻击的目标，跳过狼人阶段")
            return

        # 收集所有狼人的投票
        werewolf_votes: dict[str, str] = {}  # werewolf_id -> target_id
        for wolf in alive_wolves:
            decision = await self._get_decision(
                player=wolf,
                action_type="kill",
                context={
                    "valid_targets": [{"id": p.id, "name": p.name, "seat": p.seat,
                                       "is_alive": p.is_alive}
                                      for p in valid_targets],
                    "fellow_werewolves": [
                        {"id": w.id, "name": w.name, "seat": w.seat}
                        for w in alive_wolves if w.id != wolf.id
                    ],
                    "alive_count": len(self.state.get_alive_players()),
                },
            )
            target = decision.get("target") if decision else None
            if target:
                werewolf_votes[wolf.id] = target
                await self._emit_log(
                    "werewolf_vote",
                    f"狼人 {wolf.name} 投票击杀 {self.state.get_player(target).name if self.state.get_player(target) else target}",
                    player_id=wolf.id,
                    role=Role.WEREWOLF.value,
                )

        # 投票决定击杀目标（多数决，平票则随机选择）
        if werewolf_votes:
            vote_counts = Counter(werewolf_votes.values())
            max_count = max(vote_counts.values())
            top_targets = [t for t, c in vote_counts.items() if c == max_count]
            self.state.night_kill_target = random.choice(top_targets)
            target_obj = self.state.get_player(self.state.night_kill_target)
            await self._emit_log(
                "werewolf_kill_decision",
                f"狼人最终决定击杀 {target_obj.name}(座位{target_obj.seat})" if target_obj else f"狼人选择击杀 {self.state.night_kill_target}",
                player_id=None,
                role=Role.WEREWOLF.value,
            )
        else:
            self.state.night_kill_target = random.choice([t.id for t in valid_targets])
            target_obj = self.state.get_player(self.state.night_kill_target)
            await self._emit_log(
                "werewolf_kill_random",
                f"狼人未能达成一致，随机击杀 {target_obj.name}(座位{target_obj.seat})" if target_obj else f"随机击杀 {self.state.night_kill_target}",
                player_id=None,
                role=Role.WEREWOLF.value,
            )

    async def _phase_night_seer(self) -> None:
        """夜晚-预言家阶段：预言家查验一名玩家身份"""
        await self._emit_log("phase_start", "预言家请睁眼，选择查验目标")

        seer = next((p for p in self.state.get_alive_players()
                     if p.role == Role.SEER), None)

        if seer is None:
            await self._emit_log("phase_skip", "预言家已死亡，跳过查验阶段")
            return

        # 可选目标：所有存活玩家（除了已查验过的可以重复查验）
        valid_targets = [p for p in self.state.get_alive_players()
                         if p.id != seer.id]

        decision = await self._get_decision(
            player=seer,
            action_type="check",
            context={
                "valid_targets": [{"id": p.id, "name": p.name, "seat": p.seat}
                                  for p in valid_targets],
                "previous_checks": self.state.seer_check_result,
            },
        )

        target_id = decision.get("target") if decision else None

        if target_id:
            target_obj = self.state.get_player(target_id)
            is_werewolf = (target_obj.role == Role.WEREWOLF) if target_obj else False
            self.state.seer_check_result[target_id] = is_werewolf
            await self._emit_log(
                "seer_check",
                f"预言家查验了 {target_obj.name}(座位{target_obj.seat})，结果是: {'狼人' if is_werewolf else '好人'}" if target_obj else f"查验结果: {'狼人' if is_werewolf else '好人'}",
                player_id=seer.id,
                role=Role.SEER.value,
            )
        else:
            await self._emit_log(
                "seer_skip",
                "预言家未选择查验目标",
                player_id=seer.id,
                role=Role.SEER.value,
            )

    async def _phase_night_witch(self) -> None:
        """夜晚-女巫阶段：女巫决定使用解药和/或毒药"""
        await self._emit_log("phase_start", "女巫请睁眼")

        witch = next((p for p in self.state.get_alive_players()
                      if p.role == Role.WITCH), None)

        if witch is None:
            await self._emit_log("phase_skip", "女巫已死亡，跳过女巫阶段")
            return

        # 告知女巫当晚被杀的人
        kill_info = ""
        if self.state.night_kill_target:
            target_obj = self.state.get_player(self.state.night_kill_target)
            if target_obj:
                kill_info = f"今晚 {target_obj.name}(座位{target_obj.seat}) 被狼人杀害"
        else:
            kill_info = "今晚是平安夜，无人被杀"

        await self._emit_log(
            "witch_info",
            kill_info,
            player_id=witch.id,
            role=Role.WITCH.value,
        )

        # 构建女巫可选操作上下文
        alive_players = self.state.get_alive_players()
        valid_poison_targets = [p for p in alive_players if p.id != witch.id]

        context = {
            "night_kill_target": self.state.night_kill_target,
            "antidote_available": self.state.witch_antidote_available,
            "poison_available": self.state.witch_poison_available,
            "valid_poison_targets": [{"id": p.id, "name": p.name, "seat": p.seat}
                                     for p in valid_poison_targets],
            "alive_players": [{"id": p.id, "name": p.name, "seat": p.seat}
                              for p in alive_players],
        }

        decision = await self._get_decision(
            player=witch,
            action_type="witch_action",
            context=context,
        )

        if decision:
            use_antidote = decision.get("use_antidote", False)
            use_poison = decision.get("use_poison", False)
            poison_target = decision.get("poison_target")

            # 使用解药
            if use_antidote and self.state.witch_antidote_available and self.state.night_kill_target:
                self.state.witch_saved_target = self.state.night_kill_target
                self.state.witch_antidote_available = False
                target_obj = self.state.get_player(self.state.night_kill_target)
                await self._emit_log(
                    "witch_antidote",
                    f"女巫使用了解药，救了 {target_obj.name}(座位{target_obj.seat})" if target_obj else "女巫使用了解药",
                    player_id=witch.id,
                    role=Role.WITCH.value,
                )

            # 使用毒药
            if use_poison and self.state.witch_poison_available and poison_target:
                if poison_target != witch.id:
                    self.state.witch_poison_target = poison_target
                    self.state.witch_poison_available = False
                    target_obj = self.state.get_player(poison_target)
                    await self._emit_log(
                        "witch_poison",
                        f"女巫使用了毒药，毒杀了 {target_obj.name}(座位{target_obj.seat})" if target_obj else "女巫使用了毒药",
                        player_id=witch.id,
                        role=Role.WITCH.value,
                    )

            if not use_antidote and not use_poison:
                await self._emit_log(
                    "witch_skip",
                    "女巫选择不使用任何药物",
                    player_id=witch.id,
                    role=Role.WITCH.value,
                )

    async def _phase_day_announce(self) -> None:
        """白天-天亮阶段：结算夜晚死亡"""
        await self._emit_log("phase_start", "天亮了，公布夜晚结果")

        # 计算实际死亡
        night_deaths = []
        hunter_killed_by_wolf = False

        # 狼人击杀
        if self.state.night_kill_target:
            # 检查守护
            if (self.state.guard_protected_target
                    and self.state.guard_protected_target == self.state.night_kill_target):
                # 被守卫守护，免死
                self.state.protected_player = self.state.night_kill_target
                await self._emit_log(
                    "guard_saved",
                    f"守卫成功守护了 {self.state.get_player(self.state.night_kill_target).name}",
                    player_id=None,
                )
            elif (self.state.witch_saved_target
                  and self.state.witch_saved_target == self.state.night_kill_target):
                # 被女巫救活
                self.state.protected_player = self.state.night_kill_target
                await self._emit_log(
                    "witch_saved",
                    f"女巫成功救活了 {self.state.get_player(self.state.night_kill_target).name}",
                    player_id=None,
                )
            else:
                # 确认死亡
                killed = self.state.get_player(self.state.night_kill_target)
                if killed:
                    night_deaths.append(self.state.night_kill_target)
                    if killed.role == Role.HUNTER:
                        hunter_killed_by_wolf = True

        # 女巫毒杀
        if self.state.witch_poison_target:
            poisoned = self.state.get_player(self.state.witch_poison_target)
            if poisoned:
                night_deaths.append(self.state.witch_poison_target)
                # 被毒杀的猎人不能开枪
                if poisoned.role == Role.HUNTER:
                    hunter_killed_by_wolf = False

        # 去重
        night_deaths = list(set(night_deaths))
        self.state.night_deaths = night_deaths

        # 执行死亡
        for death_id in night_deaths:
            player = self.state.get_player(death_id)
            if player:
                # 如果是狼人杀的猎人，允许开枪
                if player.role == Role.HUNTER and hunter_killed_by_wolf and death_id == self.state.night_kill_target:
                    self.state.hunter_can_shoot = True

                self.state.kill_player(death_id)
                await self._emit_log(
                    "player_death",
                    f"{player.name}(座位{player.seat}, {ROLE_NAME_CN.get(player.role, '')}) 在夜晚死亡",
                    player_id=player.id,
                    role=player.role.value,
                )

        # 更新守卫上轮守护记录
        if self.state.guard_protected_target:
            self.state.guard_last_protected = self.state.guard_protected_target

        if not night_deaths:
            await self._emit_log(
                "peaceful_night",
                "昨晚是平安夜，无人死亡",
                player_id=None,
            )

        # 猎人开枪（被狼人杀死的情况）
        if hunter_killed_by_wolf and self.state.hunter_can_shoot:
            hunter = next((p for p in self.state.players
                           if p.role == Role.HUNTER
                           and p.id == self.state.night_kill_target), None)
            if hunter:
                await self._handle_hunter_shot(hunter, "被狼人杀害")

    async def _phase_day_speech(self) -> None:
        """白天-发言阶段：存活玩家按顺序发言"""
        alive = self.state.get_alive_players()
        if len(alive) <= 1:
            return

        await self._emit_log("phase_start", f"发言阶段开始，{len(alive)}名玩家将依次发言")

        # 按座位顺序发言
        # 从上轮被淘汰玩家的下一位开始（或从1号开始）
        start_seat = 1
        if self.state.eliminated_player_id:
            eliminated = self.state.get_player(self.state.eliminated_player_id)
            if eliminated:
                start_seat = (eliminated.seat % 12) + 1

        # 排序：从start_seat开始循环
        alive_sorted = sorted(alive, key=lambda p: (
            (p.seat - start_seat) % 12
        ))

        for i, player in enumerate(alive_sorted):
            self.state.turn_index = i

            context = {
                "speeches_today": self.state.speeches,
                "alive_players": [{"id": p.id, "name": p.name, "seat": p.seat}
                                  for p in alive],
                "dead_players": [{"id": p.id, "name": p.name, "seat": p.seat}
                                 for p in self.state.get_dead_players()],
                "night_deaths": self.state.night_deaths,
                "round_number": self.state.round_number,
                "speaking_order": i + 1,
                "total_speakers": len(alive_sorted),
            }

            decision = await self._get_decision(
                player=player,
                action_type="speech",
                context=context,
            )

            speech_content = decision.get("speech", "（沉默）") if decision else "（沉默）"
            speech_entry = {
                "player_id": player.id,
                "player_name": player.name,
                "seat": player.seat,
                "content": speech_content,
                "round": self.state.round_number,
            }
            self.state.speeches.append(speech_entry)

            await self._emit_log(
                "speech",
                f"{player.name}(座位{player.seat}): {speech_content}",
                player_id=player.id,
                role=player.role.value,
            )
            await self._emit_state_update()

    async def _phase_day_vote(self) -> None:
        """白天-投票阶段：存活玩家投票放逐"""
        alive = self.state.get_alive_players()
        if len(alive) <= 1:
            return

        await self._emit_log("phase_start", "投票阶段开始，请选择放逐目标")

        self.state.votes = {}
        valid_targets = [{"id": p.id, "name": p.name, "seat": p.seat}
                         for p in alive]

        for player in alive:
            context = {
                "valid_targets": valid_targets,
                "speeches": self.state.speeches,
                "round_number": self.state.round_number,
            }

            decision = await self._get_decision(
                player=player,
                action_type="vote",
                context=context,
            )

            target = decision.get("target") if decision else None

            if target and target in [t["id"] for t in valid_targets]:
                self.state.votes[player.id] = target
                target_obj = self.state.get_player(target)
                await self._emit_log(
                    "vote_cast",
                    f"{player.name}(座位{player.seat}) 投票放逐 {target_obj.name}(座位{target_obj.seat})" if target_obj else f"{player.name} 投票放逐 {target}",
                    player_id=player.id,
                    role=player.role.value,
                )
            elif target == "abstain" or target is None:
                await self._emit_log(
                    "vote_abstain",
                    f"{player.name}(座位{player.seat}) 弃权",
                    player_id=player.id,
                    role=player.role.value,
                )

        await self._emit_state_update()

    async def _phase_day_result(self) -> None:
        """白天-结果阶段：计票，放逐得票最多的玩家"""
        await self._emit_log("phase_start", "公布投票结果")

        if not self.state.votes:
            await self._emit_log("vote_result", "无人投票，本轮没有玩家被放逐")
            return

        # 计票
        vote_counts = Counter(self.state.votes.values())
        if not vote_counts:
            await self._emit_log("vote_result", "所有玩家弃权，本轮没有玩家被放逐")
            return

        max_count = max(vote_counts.values())
        top_targets = [t for t, c in vote_counts.items() if c == max_count]

        # 平票则无人被放逐
        if len(top_targets) > 1:
            top_names = [f"{self.state.get_player(t).name}(座位{self.state.get_player(t).seat})" if self.state.get_player(t) else t for t in top_targets]
            await self._emit_log(
                "vote_tie",
                f"平票! {' 和 '.join(top_names)} 各得 {max_count} 票，本轮无人被放逐",
                player_id=None,
            )
            self.state.eliminated_player_id = None
        else:
            eliminated_id = top_targets[0]
            self.state.eliminated_player_id = eliminated_id
            eliminated = self.state.get_player(eliminated_id)

            await self._emit_log(
                "vote_eliminate",
                f"{eliminated.name}(座位{eliminated.seat}, {ROLE_NAME_CN.get(eliminated.role, '')}) "
                f"以 {max_count} 票被放逐" if eliminated else f"{eliminated_id} 被放逐",
                player_id=eliminated_id,
                role=eliminated.role.value if eliminated else None,
            )

            # 执行放逐
            if eliminated:
                # 如果是猎人被放逐，可以开枪
                if eliminated.role == Role.HUNTER:
                    self.state.hunter_can_shoot = True

                self.state.kill_player(eliminated_id)

                # 猎人开枪
                if eliminated.role == Role.HUNTER and self.state.hunter_can_shoot:
                    await self._handle_hunter_shot(eliminated, "被投票放逐")

        await self._emit_state_update()

    async def _phase_check_end(self) -> None:
        """检查胜负条件"""
        alive_wolves = self.state.get_alive_werewolves()
        alive_good = self.state.get_alive_good_players()

        # 狼人全部死亡 -> 好人胜利
        if len(alive_wolves) == 0:
            self.state.game_over = True
            self.state.winner = Team.GOOD.value
            self.state.phase = Phase.GAME_OVER
            await self._emit_log("game_end", "所有狼人已被消灭，好人阵营获胜！")
            try:
                await update_game_status(
                    self.game_id,
                    status="finished",
                    winner=Team.GOOD.value,
                    current_phase=Phase.GAME_OVER.value,
                    round_number=self.state.round_number,
                    game_state=json.dumps(self.state.to_dict(), ensure_ascii=False),
                )
                # 触发游戏结束评估回调
                await self._emit_game_over()
            except Exception as e:
                logger.warning(f"更新游戏状态到数据库失败: {e}")
            return

        # 存活狼人 >= 存活好人 -> 狼人胜利
        if len(alive_wolves) >= len(alive_good):
            self.state.game_over = True
            self.state.winner = Team.EVIL.value
            self.state.phase = Phase.GAME_OVER
            await self._emit_log("game_end", "狼人数量已经不少于好人，狼人阵营获胜！")
            try:
                await update_game_status(
                    self.game_id,
                    status="finished",
                    winner=Team.EVIL.value,
                    current_phase=Phase.GAME_OVER.value,
                    round_number=self.state.round_number,
                    game_state=json.dumps(self.state.to_dict(), ensure_ascii=False),
                )
                # 触发游戏结束评估回调
                await self._emit_game_over()
            except Exception as e:
                logger.warning(f"更新游戏状态到数据库失败: {e}")
            return

        # 游戏继续
        await self._emit_log("round_end", f"第 {self.state.round_number} 轮结束，游戏继续")

    async def _emit_game_over(self) -> None:
        """触发游戏结束回调，用于评估系统"""
        cb = self.callbacks.get("on_game_over")
        if cb:
            try:
                await cb(self.state)
            except Exception as e:
                logger.warning(f"游戏结束回调执行失败: {e}")

    async def _handle_hunter_shot(self, hunter: Player, cause: str) -> None:
        """处理猎人开枪"""
        alive_others = [p for p in self.state.get_alive_players()
                        if p.id != hunter.id]

        if not alive_others:
            return

        await self._emit_log(
            "hunter_trigger",
            f"猎人 {hunter.name}(座位{hunter.seat}) {cause}，可以开枪带走一名玩家",
            player_id=hunter.id,
            role=Role.HUNTER.value,
        )

        decision = await self._get_decision(
            player=hunter,
            action_type="hunter_shoot",
            context={
                "valid_targets": [{"id": p.id, "name": p.name, "seat": p.seat}
                                  for p in alive_others],
                "cause": cause,
            },
        )

        target_id = decision.get("target") if decision else None

        if target_id:
            target_obj = self.state.get_player(target_id)
            if target_obj and target_obj.is_alive:
                self.state.hunter_shot_target = target_id
                self.state.kill_player(target_id)
                await self._emit_log(
                    "hunter_shoot",
                    f"猎人开枪带走了 {target_obj.name}(座位{target_obj.seat}, "
                    f"{ROLE_NAME_CN.get(target_obj.role, '')})",
                    player_id=hunter.id,
                    role=Role.HUNTER.value,
                )

    # ========== 决策获取 ==========

    async def _get_decision(self, player: Player, action_type: str,
                            context: dict) -> Optional[dict]:
        """
        获取玩家决策（AI或人类）

        Args:
            player: 玩家对象
            action_type: 操作类型
            context: 上下文信息

        Returns:
            决策字典，如果获取失败返回None
        """
        if player.is_human:
            return await self._get_human_decision(player, action_type, context)
        else:
            return await self._get_ai_decision(player, action_type, context)

    async def _get_ai_decision(self, player: Player, action_type: str,
                               context: dict) -> Optional[dict]:
        """获取AI玩家决策"""
        agent = self.agents.get(player.id)
        if not agent:
            logger.warning(f"AI玩家 {player.id} 没有对应的代理")
            return None

        try:
            decision = await agent.decide(action_type, context)
            # 更新AI的内存
            agent.add_memory({
                "action_type": action_type,
                "context": context,
                "decision": decision,
                "round": self.state.round_number,
                "phase": self.state.phase.value,
            })
            return decision
        except Exception as e:
            logger.error(f"AI玩家 {player.id} 决策失败: {e}")
            return None

    async def _get_human_decision(self, player: Player, action_type: str,
                                  context: dict) -> Optional[dict]:
        """获取人类玩家决策"""
        self.state.waiting_for_player = player.id
        self.state.pending_action = action_type
        self._current_human_player = player.id

        await self._emit_state_update()
        await self._emit_human_action_required(player.id, action_type)

        # 等待人类操作提交
        self._human_event.clear()
        try:
            await asyncio.wait_for(
                self._human_event.wait(),
                timeout=300.0,  # 5分钟超时
            )
        except asyncio.TimeoutError:
            logger.warning(f"人类玩家 {player.id} 操作超时")
            self.state.waiting_for_player = None
            self.state.pending_action = None
            return None

        self.state.waiting_for_player = None
        self.state.pending_action = None

        decision = self.human_decisions.pop(player.id, None)
        return decision

    # ========== 游戏控制 ==========

    def stop(self) -> None:
        """停止游戏"""
        self._running = False
        self._human_event.set()  # 解除等待