"""
游戏引擎综合测试
测试角色分配、游戏流程、胜负判定、信息隔离等
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# 添加项目根目录到path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from backend.game_engine.roles import (
    DEFAULT_ROLES,
    ROLE_NAME_CN,
    ROLE_TEAM,
    Phase,
    Role,
    Team,
)
from backend.game_engine.state import GameState, Player
from backend.game_engine.engine import GameEngine, PHASE_ORDER


# ========== Mock Agent ==========

class MockAgent:
    """模拟AI代理，返回预设决策"""

    def __init__(self, player_id, player_name, role, decisions=None):
        self.player_id = player_id
        self.player_name = player_name
        self.role = role
        self.decisions = decisions or {}  # action_type -> decision
        self.memory = []
        self.state = None

    async def decide(self, action_type, context):
        decision = self.decisions.get(action_type, {})
        if not decision:
            # 默认决策
            if action_type == "protect":
                valid = context.get("valid_targets", [])
                return {"target": valid[0]["id"] if valid else None}
            elif action_type == "kill":
                valid = context.get("valid_targets", [])
                return {"target": valid[0]["id"] if valid else None}
            elif action_type == "check":
                valid = context.get("valid_targets", [])
                return {"target": valid[0]["id"] if valid else None}
            elif action_type == "witch_action":
                return {"use_antidote": True, "use_poison": False, "poison_target": None}
            elif action_type == "speech":
                return {"speech": "测试发言内容"}
            elif action_type == "vote":
                valid = context.get("valid_targets", [])
                return {"target": valid[0]["id"] if valid else "abstain"}
            elif action_type == "hunter_shoot":
                valid = context.get("valid_targets", [])
                return {"target": valid[0]["id"] if valid else None}
        return decision

    def add_memory(self, entry):
        self.memory.append(entry)


def mock_agent_factory(game_engine, decisions_by_role=None):
    """创建模拟代理工厂"""
    decisions_by_role = decisions_by_role or {}

    def factory(player_id, player_name, role):
        return MockAgent(player_id, player_name, role, decisions_by_role.get(role, {}))

    return factory


def make_player_configs(human_ids=None):
    """创建12名玩家的配置"""
    human_ids = human_ids or []
    configs = []
    for i in range(12):
        pid = f"p{i+1}"
        configs.append({
            "id": pid,
            "name": f"玩家{i+1}",
            "is_human": pid in human_ids,
        })
    return configs


# ========== 引擎集成测试 ==========

class TestGameEngineIntegration:
    """游戏引擎集成测试"""

    def _make_engine(self, decisions_by_role=None):
        """创建测试用引擎"""
        configs = make_player_configs()
        engine = GameEngine(
            game_id="test_game",
            player_configs=configs,
            agent_factory=mock_agent_factory(None, decisions_by_role),
        )
        return engine, configs

    @pytest.mark.asyncio
    async def test_role_assignment(self):
        """测试角色分配"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 验证12个玩家都有角色
        assert len(engine.state.players) == 12

        # 验证角色数量
        role_counts = {}
        for p in engine.state.players:
            role_counts[p.role] = role_counts.get(p.role, 0) + 1

        assert role_counts.get(Role.WEREWOLF, 0) == 4
        assert role_counts.get(Role.SEER, 0) == 1
        assert role_counts.get(Role.WITCH, 0) == 1
        assert role_counts.get(Role.HUNTER, 0) == 1
        assert role_counts.get(Role.GUARD, 0) == 1
        assert role_counts.get(Role.VILLAGER, 0) == 4

        # 验证所有玩家存活
        assert len(engine.state.alive_player_ids) == 12

    @pytest.mark.asyncio
    async def test_initial_phase_order(self):
        """测试初始阶段顺序"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 验证阶段顺序
        expected_order = [
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
        assert PHASE_ORDER == expected_order

    @pytest.mark.asyncio
    async def test_information_isolation(self):
        """测试信息隔离 - 不同角色看到的信息不同"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 找出各角色玩家
        werewolf = next(p for p in engine.state.players if p.role == Role.WEREWOLF)
        seer = next(p for p in engine.state.players if p.role == Role.SEER)
        villager = next(p for p in engine.state.players if p.role == Role.VILLAGER)

        # 狼人视角 - 应该能看到其他狼人身份
        ww_state = engine.state.get_public_state(werewolf.id)
        ww_players = ww_state["players"]
        werewolf_count = sum(1 for p in ww_players if p.get("role") == Role.WEREWOLF.value)
        assert werewolf_count >= 1  # 至少自己能看到
        # 应该知道自己的角色
        assert ww_state["your_role"] == Role.WEREWOLF.value

        # 村民视角 - 不应该看到任何特殊角色信息
        villager_state = engine.state.get_public_state(villager.id)
        for p in villager_state["players"]:
            if p["id"] != villager.id:
                assert "role" not in p, f"村民不应该看到 {p['name']} 的角色"

        # 预言家视角 - 有查验结果字段
        seer_state = engine.state.get_public_state(seer.id)
        assert "seer_check_result" in seer_state

    @pytest.mark.asyncio
    async def test_night_guard_phase(self):
        """测试守卫阶段"""
        engine, configs = self._make_engine()
        await engine._phase_setup()
        engine.state.phase = Phase.NIGHT_GUARD
        await engine._phase_night_guard()

        # 守卫应该选择了一个守护目标
        assert engine.state.guard_protected_target is not None
        # 守卫上轮守护应该为None（第一轮）
        assert engine.state.guard_last_protected is None

    @pytest.mark.asyncio
    async def test_night_werewolf_phase(self):
        """测试狼人阶段"""
        engine, configs = self._make_engine()
        await engine._phase_setup()
        engine.state.phase = Phase.NIGHT_WEREWOLF
        await engine._phase_night_werewolf()

        # 狼人应该选择了一个击杀目标
        assert engine.state.night_kill_target is not None
        # 击杀目标不应该是狼人
        target = engine.state.get_player(engine.state.night_kill_target)
        assert target is not None
        assert target.role != Role.WEREWOLF

    @pytest.mark.asyncio
    async def test_night_seer_phase(self):
        """测试预言家阶段"""
        engine, configs = self._make_engine()
        await engine._phase_setup()
        engine.state.phase = Phase.NIGHT_SEER
        await engine._phase_night_seer()

        # 预言家应该查验了一个目标
        assert len(engine.state.seer_check_result) >= 1

    @pytest.mark.asyncio
    async def test_night_witch_phase(self):
        """测试女巫阶段"""
        engine, configs = self._make_engine()
        await engine._phase_setup()
        await engine._phase_night_werewolf()  # 先有击杀目标
        engine.state.phase = Phase.NIGHT_WITCH
        await engine._phase_night_witch()

        # 第一轮女巫应该使用了解药
        assert engine.state.witch_antidote_available is False
        assert engine.state.witch_saved_target == engine.state.night_kill_target

    @pytest.mark.asyncio
    async def test_day_speech_phase(self):
        """测试发言阶段"""
        engine, configs = self._make_engine()
        await engine._phase_setup()
        engine.state.phase = Phase.DAY_SPEECH
        await engine._phase_day_speech()

        # 所有存活的12名玩家都应该发言了
        assert len(engine.state.speeches) == 12

    @pytest.mark.asyncio
    async def test_day_vote_phase(self):
        """测试投票阶段"""
        engine, configs = self._make_engine()
        await engine._phase_setup()
        engine.state.phase = Phase.DAY_SPEECH
        await engine._phase_day_speech()
        engine.state.phase = Phase.DAY_VOTE
        await engine._phase_day_vote()

        # 应该有投票记录
        assert len(engine.state.votes) == 12

    @pytest.mark.asyncio
    async def test_win_condition_good_wins(self):
        """测试好人胜利条件 - 所有狼人死亡"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 手动杀死所有狼人
        for p in engine.state.players:
            if p.role == Role.WEREWOLF:
                engine.state.kill_player(p.id)

        await engine._phase_check_end()

        assert engine.state.game_over is True
        assert engine.state.winner == Team.GOOD.value

    @pytest.mark.asyncio
    async def test_win_condition_werewolves_win(self):
        """测试狼人胜利条件 - 狼人数>=好人数"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 手动杀死足够多的好人
        good_players = [p for p in engine.state.players if p.team == Team.GOOD]
        werewolves = engine.state.get_alive_werewolves()

        # 杀死好人使狼人数>=好人数
        to_kill = len(good_players) - len(werewolves) + 1
        for p in good_players[:to_kill]:
            engine.state.kill_player(p.id)

        await engine._phase_check_end()

        assert engine.state.game_over is True
        assert engine.state.winner == Team.EVIL.value

    @pytest.mark.asyncio
    async def test_guard_cannot_protect_same_player(self):
        """测试守卫不能连续守护同一玩家"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 模拟第一晚守护
        guard = next(p for p in engine.state.players if p.role == Role.GUARD)
        engine.state.guard_last_protected = "p1"

        # 第二晚尝试守护同一人
        engine.state.phase = Phase.NIGHT_GUARD

        # 重设MockAgent返回p1
        guard_agent = engine.agents.get(guard.id)
        if guard_agent:
            guard_agent.decisions["protect"] = {"target": "p1"}

        await engine._phase_night_guard()

        # 不应该守护p1
        assert engine.state.guard_protected_target != "p1" or engine.state.guard_protected_target is None

    @pytest.mark.asyncio
    async def test_witch_cannot_save_twice(self):
        """测试女巫不能使用两次解药"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        witch = next(p for p in engine.state.players if p.role == Role.WITCH)
        engine.state.witch_antidote_available = False  # 已使用
        engine.state.night_kill_target = "p1"
        engine.state.phase = Phase.NIGHT_WITCH

        witch_agent = engine.agents.get(witch.id)
        if witch_agent:
            witch_agent.decisions["witch_action"] = {
                "use_antidote": True,
                "use_poison": False,
                "poison_target": None,
            }

        await engine._phase_night_witch()

        # 不应该保存成功
        assert engine.state.witch_saved_target is None

    @pytest.mark.asyncio
    async def test_hunter_shoots_on_death(self):
        """测试猎人死亡时开枪"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        hunter = next(p for p in engine.state.players if p.role == Role.HUNTER)

        # 设定猎人被投票放逐
        engine.state.hunter_can_shoot = True
        alive_others = [p for p in engine.state.players if p.id != hunter.id]

        # 设定MockAgent返回一个目标
        hunter_agent = engine.agents.get(hunter.id)
        if hunter_agent and alive_others:
            hunter_agent.decisions["hunter_shoot"] = {"target": alive_others[0].id}

        await engine._handle_hunter_shot(hunter, "被投票放逐")

        assert engine.state.hunter_shot_target is not None

    @pytest.mark.asyncio
    async def test_human_action_submission(self):
        """测试人类玩家操作提交"""
        configs = make_player_configs(human_ids=["p1"])
        engine = GameEngine(
            game_id="test_human",
            player_configs=configs,
            agent_factory=mock_agent_factory(None),
        )
        await engine._phase_setup()

        # 模拟等待人类操作
        engine.state.waiting_for_player = "p1"
        engine.state.pending_action = "vote"
        engine._human_event.clear()

        # 提交操作
        success = await engine.submit_human_action("p1", {
            "target": "p2",
            "speech": "我是人类玩家",
        })

        assert success is True

    @pytest.mark.asyncio
    async def test_get_public_state_for_dead_player(self):
        """测试死亡玩家的视角"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 杀死一个玩家
        dead_player = engine.state.players[0]
        engine.state.kill_player(dead_player.id)

        public_state = engine.state.get_public_state(dead_player.id)
        # 死亡玩家角色应该为None（看不到）
        assert public_state["your_role"] is None

    @pytest.mark.asyncio
    async def test_speeches_preserved(self):
        """测试发言记录保留"""
        engine, configs = self._make_engine()
        await engine._phase_setup()
        engine.state.phase = Phase.DAY_SPEECH

        # 设置MockAgent返回不同发言
        for player in engine.state.players:
            agent = engine.agents.get(player.id)
            if agent:
                agent.decisions["speech"] = {"speech": f"{player.name}的测试发言"}

        await engine._phase_day_speech()

        # 验证发言记录
        assert len(engine.state.speeches) == 12
        for i, speech in enumerate(engine.state.speeches):
            assert "player_id" in speech
            assert "content" in speech
            assert "seat" in speech

    @pytest.mark.asyncio
    async def test_vote_tie_no_elimination(self):
        """测试平票时无人被放逐"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        # 手动制造平票
        alive = engine.state.get_alive_players()
        for i, p in enumerate(alive):
            target_idx = (i + 1) % 6  # 轮流投给下一个人
            engine.state.votes[p.id] = alive[target_idx].id

        engine.state.eliminated_player_id = None
        engine.state.phase = Phase.DAY_RESULT
        await engine._phase_day_result()

        # 6人各投一票给不同的人 -> 平票，无人被放逐
        assert engine.state.eliminated_player_id is None

    @pytest.mark.asyncio
    async def test_complete_round_flow(self):
        """测试完整的单轮游戏流程"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        engine.state.phase = Phase.NIGHT_GUARD
        await engine._phase_night_guard()
        assert engine.state.phase == Phase.NIGHT_GUARD

        engine.state.phase = Phase.NIGHT_WEREWOLF
        await engine._phase_night_werewolf()
        assert engine.state.night_kill_target is not None

        engine.state.phase = Phase.NIGHT_SEER
        await engine._phase_night_seer()
        assert len(engine.state.seer_check_result) >= 1

        engine.state.phase = Phase.NIGHT_WITCH
        await engine._phase_night_witch()

        engine.state.phase = Phase.DAY_ANNOUNCE
        await engine._phase_day_announce()

        engine.state.phase = Phase.DAY_SPEECH
        await engine._phase_day_speech()
        assert len(engine.state.speeches) > 0

        engine.state.phase = Phase.DAY_VOTE
        await engine._phase_day_vote()
        assert len(engine.state.votes) > 0

        engine.state.phase = Phase.DAY_RESULT
        await engine._phase_day_result()

        engine.state.phase = Phase.CHECK_END
        await engine._phase_check_end()

        # 一轮后游戏应该还在继续（除非极端情况）
        # 手动逐阶段执行没有通过_start_new_round，所以round_number保持为0
        assert engine.state.round_number == 0

    @pytest.mark.asyncio
    async def test_witch_poison(self):
        """测试女巫使用毒药"""
        engine, configs = self._make_engine()
        await engine._phase_setup()

        witch = next(p for p in engine.state.players if p.role == Role.WITCH)
        engine.state.night_kill_target = "p5"
        engine.state.phase = Phase.NIGHT_WITCH

        # 让女巫选择毒杀
        witch_agent = engine.agents.get(witch.id)
        if witch_agent:
            # 找一个不是witch的玩家
            poison_target = next(p.id for p in engine.state.players if p.id != witch.id)
            witch_agent.decisions["witch_action"] = {
                "use_antidote": False,
                "use_poison": True,
                "poison_target": poison_target,
            }

        await engine._phase_night_witch()

        assert engine.state.witch_saved_target is None
        assert engine.state.witch_poison_target is not None
        assert engine.state.witch_poison_available is False


# ========== 单元测试 ==========

class TestGameState:
    """GameState单元测试"""

    def test_player_creation(self):
        """测试Player数据类创建"""
        player = Player(
            id="p1",
            seat=3,
            name="测试玩家",
            role=Role.WEREWOLF,
            is_alive=True,
        )

        assert player.id == "p1"
        assert player.seat == 3
        assert player.role == Role.WEREWOLF
        assert player.team == Team.EVIL
        assert player.is_alive is True

    def test_player_to_dict(self):
        """测试Player序列化"""
        player = Player(id="p1", seat=1, name="玩家1", role=Role.SEER)
        d = player.to_dict()
        assert d["id"] == "p1"
        assert "role" not in d  # to_dict不包含角色

    def test_player_public_dict(self):
        """测试Player公开信息"""
        player = Player(id="p1", seat=1, name="玩家1", role=Role.SEER)
        d = player.to_public_dict()
        assert "role" not in d
        assert d["is_alive"] is True

    def test_player_private_dict(self):
        """测试Player私有信息"""
        player = Player(id="p1", seat=1, name="玩家1", role=Role.SEER)
        d = player.to_private_dict()
        assert d["role"] == "seer"
        assert d["team"] == "good"

    def test_game_state_initialization(self):
        """测试GameState初始化"""
        state = GameState(game_id="test")
        assert state.game_id == "test"
        assert state.phase == Phase.SETUP
        assert state.round_number == 1
        assert state.game_over is False
        assert state.winner is None

    def test_game_state_kill_player(self):
        """测试标记玩家死亡"""
        state = GameState(game_id="test")
        p = Player(id="p1", seat=1, name="玩家1", role=Role.VILLAGER)
        p2 = Player(id="p2", seat=2, name="玩家2", role=Role.WEREWOLF)
        state.players = [p, p2]
        state.alive_player_ids = ["p1", "p2"]

        state.kill_player("p1")

        assert not p.is_alive
        assert "p1" not in state.alive_player_ids
        assert "p1" in state.dead_player_ids

    def test_game_state_get_player(self):
        """测试通过ID获取玩家"""
        state = GameState(game_id="test")
        p = Player(id="p1", seat=1, name="玩家1", role=Role.VILLAGER)
        state.players = [p]

        found = state.get_player("p1")
        assert found is not None
        assert found.id == "p1"

        not_found = state.get_player("p99")
        assert not_found is None

    def test_game_state_get_alive_werewolves(self):
        """测试获取存活狼人"""
        state = GameState(game_id="test")
        w1 = Player(id="w1", seat=1, name="狼1", role=Role.WEREWOLF)
        w2 = Player(id="w2", seat=2, name="狼2", role=Role.WEREWOLF)
        v1 = Player(id="v1", seat=3, name="村民1", role=Role.VILLAGER)
        state.players = [w1, w2, v1]
        state.alive_player_ids = ["w1", "w2", "v1"]

        wolves = state.get_alive_werewolves()
        assert len(wolves) == 2

        state.kill_player("w1")
        wolves = state.get_alive_werewolves()
        assert len(wolves) == 1


class TestRoles:
    """角色模块测试"""

    def test_role_enum(self):
        assert Role.WEREWOLF.value == "werewolf"
        assert Role.SEER.value == "seer"
        assert Role.WITCH.value == "witch"
        assert Role.HUNTER.value == "hunter"
        assert Role.GUARD.value == "guard"
        assert Role.VILLAGER.value == "villager"

    def test_team_mapping(self):
        assert ROLE_TEAM[Role.WEREWOLF] == Team.EVIL
        assert ROLE_TEAM[Role.SEER] == Team.GOOD
        assert ROLE_TEAM[Role.WITCH] == Team.GOOD
        assert ROLE_TEAM[Role.HUNTER] == Team.GOOD
        assert ROLE_TEAM[Role.GUARD] == Team.GOOD
        assert ROLE_TEAM[Role.VILLAGER] == Team.GOOD

    def test_default_roles(self):
        assert len(DEFAULT_ROLES) == 12
        assert DEFAULT_ROLES.count(Role.WEREWOLF) == 4
        assert DEFAULT_ROLES.count(Role.SEER) == 1
        assert DEFAULT_ROLES.count(Role.WITCH) == 1
        assert DEFAULT_ROLES.count(Role.HUNTER) == 1
        assert DEFAULT_ROLES.count(Role.GUARD) == 1
        assert DEFAULT_ROLES.count(Role.VILLAGER) == 4

    def test_role_name_cn(self):
        assert ROLE_NAME_CN[Role.WEREWOLF] == "狼人"
        assert ROLE_NAME_CN[Role.SEER] == "预言家"
        assert ROLE_NAME_CN[Role.WITCH] == "女巫"
        assert ROLE_NAME_CN[Role.HUNTER] == "猎人"
        assert ROLE_NAME_CN[Role.GUARD] == "守卫"
        assert ROLE_NAME_CN[Role.VILLAGER] == "村民"


class TestPhaseOrder:
    """阶段顺序测试"""

    def test_phase_order_length(self):
        assert len(PHASE_ORDER) == 9

    def test_phase_order_starts_with_guard(self):
        assert PHASE_ORDER[0] == Phase.NIGHT_GUARD

    def test_phase_order_ends_with_check_end(self):
        assert PHASE_ORDER[-1] == Phase.CHECK_END

    def test_day_phases_after_night(self):
        guard_idx = PHASE_ORDER.index(Phase.NIGHT_GUARD)
        announce_idx = PHASE_ORDER.index(Phase.DAY_ANNOUNCE)
        assert guard_idx < announce_idx  # 黑夜阶段在白天之前