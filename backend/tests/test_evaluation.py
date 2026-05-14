"""
评估系统综合测试
测试指标计算、回放分析、排行榜、归因分析等功能
"""
import json
import sys
from pathlib import Path

# 添加项目根目录到path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from backend.evaluation.metrics import (
    calculate_action_accuracy,
    calculate_comprehensive_metrics,
    calculate_game_duration_stats,
    calculate_role_win_rate,
    calculate_round_by_round_performance,
    calculate_speech_consistency,
    calculate_survival_rate,
    calculate_team_contribution,
    aggregate_player_stats,
)
from backend.evaluation.replay import (
    analyze_attribution,
    generate_game_summary,
    identify_turning_points,
    reconstruct_game_replay,
)
from backend.evaluation.leaderboard import (
    get_agent_comparison,
    get_leaderboard,
    get_role_leaderboard,
    merge_leaderboard_entries,
    update_leaderboard_entry,
    _calculate_leaderboard_score,
)
from backend.game_engine.roles import Role


# ========== Test Fixtures ==========

@pytest.fixture
def sample_game_results():
    """样本游戏结果数据"""
    return [
        {
            "game_id": "g1",
            "winner": "good",
            "round_count": 3,
            "game_duration_seconds": 120.0,
            "players": [
                {"id": "p1", "name": "玩家1", "role": "werewolf", "is_alive": False, "team": "evil"},
                {"id": "p2", "name": "玩家2", "role": "werewolf", "is_alive": False, "team": "evil"},
                {"id": "p3", "name": "玩家3", "role": "werewolf", "is_alive": False, "team": "evil"},
                {"id": "p4", "name": "玩家4", "role": "werewolf", "is_alive": False, "team": "evil"},
                {"id": "p5", "name": "玩家5", "role": "seer", "is_alive": True, "team": "good"},
                {"id": "p6", "name": "玩家6", "role": "witch", "is_alive": True, "team": "good"},
                {"id": "p7", "name": "玩家7", "role": "hunter", "is_alive": True, "team": "good"},
                {"id": "p8", "name": "玩家8", "role": "guard", "is_alive": True, "team": "good"},
                {"id": "p9", "name": "玩家9", "role": "villager", "is_alive": True, "team": "good"},
                {"id": "p10", "name": "玩家10", "role": "villager", "is_alive": True, "team": "good"},
                {"id": "p11", "name": "玩家11", "role": "villager", "is_alive": True, "team": "good"},
                {"id": "p12", "name": "玩家12", "role": "villager", "is_alive": True, "team": "good"},
            ],
            "logs": [],
        },
        {
            "game_id": "g2",
            "winner": "evil",
            "round_count": 5,
            "game_duration_seconds": 180.0,
            "players": [
                {"id": "p1", "name": "玩家1", "role": "werewolf", "is_alive": True, "team": "evil"},
                {"id": "p2", "name": "玩家2", "role": "werewolf", "is_alive": True, "team": "evil"},
                {"id": "p3", "name": "玩家3", "role": "werewolf", "is_alive": False, "team": "evil"},
                {"id": "p4", "name": "玩家4", "role": "werewolf", "is_alive": True, "team": "evil"},
                {"id": "p5", "name": "玩家5", "role": "seer", "is_alive": False, "team": "good"},
                {"id": "p6", "name": "玩家6", "role": "witch", "is_alive": False, "team": "good"},
                {"id": "p7", "name": "玩家7", "role": "hunter", "is_alive": False, "team": "good"},
                {"id": "p8", "name": "玩家8", "role": "guard", "is_alive": False, "team": "good"},
                {"id": "p9", "name": "玩家9", "role": "villager", "is_alive": False, "team": "good"},
                {"id": "p10", "name": "玩家10", "role": "villager", "is_alive": False, "team": "good"},
                {"id": "p11", "name": "玩家11", "role": "villager", "is_alive": False, "team": "good"},
                {"id": "p12", "name": "玩家12", "role": "villager", "is_alive": False, "team": "good"},
            ],
            "logs": [],
        },
    ]


@pytest.fixture
def sample_game_logs():
    """样本游戏日志"""
    return [
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "night_guard",
            "player_id": "p8",
            "role": "guard",
            "action_type": "guard_protect",
            "content": "守卫守护了 玩家5(座位5)",
            "timestamp": "2024-01-01T00:01:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "night_werewolf",
            "player_id": "p1",
            "role": "werewolf",
            "action_type": "werewolf_vote",
            "content": "狼人 玩家1 投票击杀 玩家5",
            "timestamp": "2024-01-01T00:02:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "night_werewolf",
            "player_id": "p1",
            "role": "werewolf",
            "action_type": "werewolf_kill_decision",
            "content": "狼人最终决定击杀 玩家5(座位5)",
            "timestamp": "2024-01-01T00:02:30",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "night_seer",
            "player_id": "p5",
            "role": "seer",
            "action_type": "seer_check",
            "content": "预言家查验了 玩家1(座位1)，结果是: 狼人",
            "timestamp": "2024-01-01T00:03:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "night_witch",
            "player_id": "p6",
            "role": "witch",
            "action_type": "witch_antidote",
            "content": "女巫使用了解药，救了 玩家5(座位5)",
            "timestamp": "2024-01-01T00:04:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "day_announce",
            "player_id": None,
            "role": None,
            "action_type": "peaceful_night",
            "content": "昨晚是平安夜，无人死亡",
            "timestamp": "2024-01-01T00:05:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "day_speech",
            "player_id": "p5",
            "role": "seer",
            "action_type": "speech",
            "content": "我是预言家，昨晚查验了玩家1，他是狼人！",
            "timestamp": "2024-01-01T00:06:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "day_vote",
            "player_id": "p5",
            "role": "seer",
            "action_type": "vote_cast",
            "content": "玩家5(座位5) 投票放逐 玩家1(座位1)",
            "timestamp": "2024-01-01T00:07:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "day_result",
            "player_id": None,
            "role": None,
            "action_type": "vote_eliminate",
            "content": "玩家1(座位1, 狼人) 以 8 票被放逐",
            "timestamp": "2024-01-01T00:08:00",
        },
        {
            "game_id": "g1",
            "round_num": 1,
            "phase": "day_result",
            "player_id": "p1",
            "role": "werewolf",
            "action_type": "player_death",
            "content": "玩家1(座位1, 狼人) 在夜晚死亡",
            "timestamp": "2024-01-01T00:08:30",
        },
        {
            "game_id": "g1",
            "round_num": 2,
            "phase": "night_werewolf",
            "player_id": "p2",
            "role": "werewolf",
            "action_type": "werewolf_kill_decision",
            "content": "狼人最终决定击杀 玩家6(座位6)",
            "timestamp": "2024-01-01T00:10:00",
        },
        {
            "game_id": "g1",
            "round_num": 2,
            "phase": "day_result",
            "player_id": "p6",
            "role": "witch",
            "action_type": "player_death",
            "content": "玩家6(座位6, 女巫) 在夜晚死亡",
            "timestamp": "2024-01-01T00:12:00",
        },
        {
            "game_id": "g1",
            "round_num": 3,
            "phase": "day_result",
            "player_id": None,
            "role": None,
            "action_type": "game_end",
            "content": "所有狼人已被消灭，好人阵营获胜！",
            "timestamp": "2024-01-01T00:20:00",
        },
    ]


@pytest.fixture
def sample_players_config():
    """样本玩家配置"""
    return [
        {"id": "p1", "name": "玩家1", "role": "werewolf", "is_human": False},
        {"id": "p2", "name": "玩家2", "role": "werewolf", "is_human": False},
        {"id": "p3", "name": "玩家3", "role": "werewolf", "is_human": False},
        {"id": "p4", "name": "玩家4", "role": "werewolf", "is_human": False},
        {"id": "p5", "name": "玩家5", "role": "seer", "is_human": False},
        {"id": "p6", "name": "玩家6", "role": "witch", "is_human": False},
        {"id": "p7", "name": "玩家7", "role": "hunter", "is_human": False},
        {"id": "p8", "name": "玩家8", "role": "guard", "is_human": False},
        {"id": "p9", "name": "玩家9", "role": "villager", "is_human": False},
        {"id": "p10", "name": "玩家10", "role": "villager", "is_human": False},
        {"id": "p11", "name": "玩家11", "role": "villager", "is_human": False},
        {"id": "p12", "name": "玩家12", "role": "villager", "is_human": False},
    ]


# ========== Metrics Tests ==========

class TestMetrics:
    """测试指标计算模块"""

    def test_calculate_role_win_rate(self, sample_game_results):
        """测试角色胜率计算"""
        result = calculate_role_win_rate(sample_game_results)

        assert "werewolf" in result
        assert "seer" in result
        assert "villager" in result

        # 狼人：1胜1负
        assert result["werewolf"]["games"] == 8  # 4狼人 * 2局
        assert result["werewolf"]["wins"] == 4   # 第二局4狼人全赢
        assert result["werewolf"]["win_rate"] == 0.5

        # 预言家：1胜1负
        assert result["seer"]["games"] == 2
        assert result["seer"]["wins"] == 1
        assert result["seer"]["win_rate"] == 0.5

    def test_calculate_role_win_rate_empty(self):
        """测试空数据角色胜率"""
        result = calculate_role_win_rate([])
        assert result == {}

    def test_calculate_survival_rate(self, sample_game_results):
        """测试生存率计算"""
        result = calculate_survival_rate(sample_game_results)

        # p5 (预言家) 在第一局存活，第二局死亡
        assert result["p5"]["games"] == 2
        assert result["p5"]["survived"] == 1
        assert result["p5"]["survival_rate"] == 0.5

        # p1 (狼人) 在第一局死亡，第二局存活
        assert result["p1"]["survival_rate"] == 0.5

    def test_calculate_survival_rate_empty(self):
        """测试空数据生存率"""
        result = calculate_survival_rate([])
        assert result == {}

    def test_calculate_action_accuracy(self, sample_game_logs, sample_players_config):
        """测试行动准确率计算"""
        result = calculate_action_accuracy(sample_game_logs, sample_players_config)

        # 检查返回了所有玩家的数据
        assert len(result) == len(sample_players_config)

        # 预言家有查验记录
        assert "p5" in result
        assert result["p5"]["check_accuracy"] > 0

        # 守卫有守护记录
        assert "p8" in result
        assert result["p8"]["protect_accuracy"] > 0

    def test_calculate_action_accuracy_empty(self):
        """测试空数据行动准确率"""
        result = calculate_action_accuracy([], [])
        assert result == {}

    def test_calculate_speech_consistency(self, sample_game_logs):
        """测试发言一致性计算"""
        result = calculate_speech_consistency(sample_game_logs)

        # p5有发言和投票
        assert "p5" in result
        assert 0 <= result["p5"] <= 1

    def test_calculate_speech_consistency_empty(self):
        """测试空数据发言一致性"""
        result = calculate_speech_consistency([])
        assert result == {}

    def test_calculate_team_contribution(self, sample_game_results):
        """测试团队贡献分计算"""
        result = calculate_team_contribution(sample_game_results[0])

        # 所有玩家都有贡献分
        assert len(result) == 12

        # 获胜阵营的贡献分应该更高
        good_players = ["p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12"]
        for pid in good_players:
            assert pid in result
            assert result[pid] > 0.5  # 获胜方基础分更高

    def test_calculate_team_contribution_empty(self):
        """测试空数据团队贡献"""
        result = calculate_team_contribution({})
        assert result == {}

    def test_aggregate_player_stats(self, sample_game_results):
        """测试聚合玩家统计"""
        result = aggregate_player_stats(sample_game_results)

        # p1 参加了2局
        assert "p1" in result
        assert result["p1"]["games_played"] == 2
        assert result["p1"]["win_rate"] == 0.5
        assert result["p1"]["survival_rate"] == 0.5

    def test_aggregate_player_stats_empty(self):
        """测试空数据聚合统计"""
        result = aggregate_player_stats([])
        assert result == {}

    def test_calculate_game_duration_stats(self, sample_game_results):
        """测试游戏时长统计"""
        result = calculate_game_duration_stats(sample_game_results)

        assert result["total_games"] == 2
        assert result["avg_rounds"] == 4.0  # (3+5)/2
        assert result["min_rounds"] == 3
        assert result["max_rounds"] == 5
        assert result["avg_duration_seconds"] == 150.0  # (120+180)/2

    def test_calculate_game_duration_stats_empty(self):
        """测试空数据时长统计"""
        result = calculate_game_duration_stats([])
        assert result["total_games"] == 0

    def test_calculate_round_by_round_performance(self, sample_game_logs, sample_players_config):
        """测试逐轮表现计算"""
        result = calculate_round_by_round_performance(sample_game_logs, sample_players_config)

        assert "p5" in result
        assert len(result["p5"]) > 0
        assert "round" in result["p5"][0]
        assert "score" in result["p5"][0]

    def test_calculate_comprehensive_metrics(self, sample_game_results, sample_game_logs, sample_players_config):
        """测试综合指标计算"""
        result = calculate_comprehensive_metrics(
            sample_game_results[0],
            sample_game_logs,
            sample_players_config,
        )

        assert result["game_id"] == "g1"
        assert result["winner"] == "good"
        assert "player_metrics" in result
        assert "team_metrics" in result

        # 检查玩家指标
        p5_metrics = result["player_metrics"].get("p5", {})
        assert p5_metrics.get("role") == "seer"
        assert p5_metrics.get("is_winner") == True


# ========== Replay Tests ==========

class TestReplay:
    """测试回放分析模块"""

    def test_reconstruct_game_replay(self, sample_game_logs):
        """测试游戏回放重建"""
        result = reconstruct_game_replay("g1", sample_game_logs)

        assert result["game_id"] == "g1"
        assert result["total_events"] == len(sample_game_logs)
        assert len(result["timeline"]) == len(sample_game_logs)
        assert len(result["key_moments"]) > 0

    def test_reconstruct_game_replay_empty(self):
        """测试空日志回放"""
        result = reconstruct_game_replay("g1", [])
        assert result["total_events"] == 0
        assert result["timeline"] == []

    def test_identify_turning_points(self, sample_game_logs):
        """测试转折点识别"""
        result = identify_turning_points(sample_game_logs)

        assert len(result) > 0
        # 检查转折点包含关键字段
        for tp in result:
            assert "round" in tp
            assert "phase" in tp
            assert "description" in tp
            assert "impact_score" in tp
            assert 0 <= tp["impact_score"] <= 1

    def test_identify_turning_points_empty(self):
        """测试空日志转折点"""
        result = identify_turning_points([])
        assert result == []

    def test_analyze_attribution(self, sample_game_results, sample_game_logs):
        """测试归因分析"""
        game_result = sample_game_results[0]
        game_result["logs"] = sample_game_logs

        result = analyze_attribution(game_result, sample_game_logs)

        assert result["game_id"] == "g1"
        assert result["winner"] == "good"
        assert "key_decisions" in result
        assert "winning_factors" in result
        assert "losing_factors" in result
        assert "mvp_players" in result
        assert "analysis_summary" in result
        assert len(result["analysis_summary"]) > 0

    def test_analyze_attribution_empty(self):
        """测试空数据归因分析"""
        result = analyze_attribution({}, [])
        assert result["analysis_summary"] == "数据不足，无法分析"

    def test_generate_game_summary(self, sample_game_results, sample_game_logs):
        """测试游戏总结生成"""
        game_result = sample_game_results[0]
        game_result["logs"] = sample_game_logs

        result = generate_game_summary("g1", game_result, sample_game_logs)

        assert result["game_id"] == "g1"
        assert result["winner"] == "good"
        assert "players" in result
        assert "timeline" in result
        assert "turning_points" in result
        assert "attribution" in result
        assert "statistics" in result

    def test_generate_game_summary_no_data(self):
        """测试无数据游戏总结"""
        result = generate_game_summary("g1")
        assert result["game_id"] == "g1"
        assert result["winner"] == "unknown"


# ========== Leaderboard Tests ==========

class TestLeaderboard:
    """测试排行榜模块"""

    def test_update_leaderboard_entry(self, sample_game_results):
        """测试排行榜条目更新"""
        game_result = sample_game_results[0]
        metrics = {"contribution_score": 0.8, "vote_accuracy": 0.7, "survived": True}

        result = update_leaderboard_entry(
            player_id="p5",
            role=Role.SEER,
            game_result=game_result,
            metrics=metrics,
            player_name="玩家5",
        )

        assert result["player_id"] == "p5"
        assert result["role"] == "seer"
        assert result["player_name"] == "玩家5"
        assert result["games_count"] == 1
        assert result["wins"] == 1
        assert result["win_rate"] == 1.0
        assert result["survival_rate"] == 1.0
        assert "total_score" in result

    def test_merge_leaderboard_entries(self):
        """测试排行榜条目合并"""
        existing = {
            "player_id": "p5",
            "role": "seer",
            "games_count": 5,
            "wins": 3,
            "win_rate": 0.6,
            "survival_rate": 0.4,
            "avg_contribution": 0.5,
            "avg_vote_accuracy": 0.5,
            "avg_action_accuracy": 0.5,
            "total_score": 0.5,
        }
        new_entry = {
            "player_id": "p5",
            "role": "seer",
            "games_count": 1,
            "wins": 1,
            "win_rate": 1.0,
            "survival_rate": 1.0,
            "avg_contribution": 0.8,
            "avg_vote_accuracy": 0.7,
            "avg_action_accuracy": 0.6,
            "total_score": 0.8,
        }

        result = merge_leaderboard_entries(existing, new_entry)

        assert result["games_count"] == 6
        assert result["wins"] == 4
        assert result["win_rate"] == round(4 / 6, 4)

    def test_get_leaderboard(self):
        """测试获取排行榜"""
        entries = [
            {"player_id": "p1", "role": "werewolf", "games_count": 5, "total_score": 0.8, "win_rate": 0.8},
            {"player_id": "p2", "role": "seer", "games_count": 5, "total_score": 0.9, "win_rate": 0.9},
            {"player_id": "p3", "role": "werewolf", "games_count": 2, "total_score": 0.7, "win_rate": 0.7},
        ]

        # 获取全部排行榜
        result = get_leaderboard(entries, limit=10)
        assert len(result) == 2  # p3 games_count=2 < MIN_GAMES_FOR_RANKING=3

        # 按角色过滤
        result = get_leaderboard(entries, role=Role.WEREWOLF, limit=10)
        assert len(result) == 1
        assert result[0]["player_id"] == "p1"

    def test_get_leaderboard_empty(self):
        """测试空排行榜"""
        result = get_leaderboard([], limit=10)
        assert result == []

    def test_get_agent_comparison(self):
        """测试Agent对比"""
        entries = [
            {"player_id": "agent_a", "role": "seer", "games_count": 5, "win_rate": 0.8, "survival_rate": 0.6, "avg_contribution": 0.7},
            {"player_id": "agent_a", "role": "werewolf", "games_count": 5, "win_rate": 0.7, "survival_rate": 0.5, "avg_contribution": 0.6},
            {"player_id": "agent_b", "role": "seer", "games_count": 5, "win_rate": 0.6, "survival_rate": 0.7, "avg_contribution": 0.5},
            {"player_id": "agent_b", "role": "werewolf", "games_count": 5, "win_rate": 0.9, "survival_rate": 0.8, "avg_contribution": 0.8},
        ]

        result = get_agent_comparison(entries, ["agent_a", "agent_b"])

        assert len(result["agents"]) == 2
        assert "comparison" in result
        assert "best_by_metric" in result["comparison"]

    def test_get_agent_comparison_empty(self):
        """测试空Agent对比"""
        result = get_agent_comparison([], ["agent_a"])
        assert result == {"agents": [], "comparison": {}}

    def test_get_role_leaderboard(self):
        """测试角色排行榜"""
        entries = [
            {"player_id": "p1", "role": "seer", "games_count": 5, "total_score": 0.8},
            {"player_id": "p2", "role": "seer", "games_count": 5, "total_score": 0.9},
            {"player_id": "p3", "role": "werewolf", "games_count": 5, "total_score": 0.95},
        ]

        result = get_role_leaderboard(entries, Role.SEER, limit=10)
        assert len(result) == 2
        assert result[0]["player_id"] == "p2"  # 分数最高

    def test_calculate_leaderboard_score(self):
        """测试排行榜评分计算"""
        score = _calculate_leaderboard_score(
            win_rate=1.0,
            survival_rate=1.0,
            avg_contribution=1.0,
            avg_vote_accuracy=1.0,
            avg_action_accuracy=1.0,
        )
        assert score == 1.0

        score = _calculate_leaderboard_score(
            win_rate=0.0,
            survival_rate=0.0,
            avg_contribution=0.0,
            avg_vote_accuracy=0.0,
            avg_action_accuracy=0.0,
        )
        assert score == 0.0


# ========== Edge Cases ==========

class TestEdgeCases:
    """测试边界情况"""

    def test_missing_game_data(self):
        """测试缺失游戏数据"""
        result = calculate_role_win_rate([{"winner": "good"}])
        assert result == {}

    def test_player_with_no_actions(self, sample_players_config):
        """测试无行动玩家"""
        logs = []  # 空日志
        result = calculate_action_accuracy(logs, sample_players_config)

        # 空日志返回空结果
        assert result == {}

    def test_single_game_result(self, sample_game_results):
        """测试单局游戏结果"""
        result = calculate_role_win_rate([sample_game_results[0]])

        # 只有一局，胜率只能是0或1
        for role_data in result.values():
            assert role_data["win_rate"] in [0.0, 1.0]

    def test_logs_with_no_player_id(self):
        """测试无player_id的日志"""
        logs = [
            {"action_type": "phase_start", "content": "夜晚降临", "round_num": 1, "phase": "night"},
            {"action_type": "game_end", "content": "游戏结束", "round_num": 3, "phase": "game_over"},
        ]
        result = calculate_speech_consistency(logs)
        assert result == {}

    def test_replay_with_system_events(self):
        """测试系统事件回放"""
        logs = [
            {"action_type": "game_start", "content": "游戏开始", "round_num": 0, "phase": "setup"},
            {"action_type": "role_assignment", "content": "角色分配", "round_num": 0, "phase": "setup"},
            {"action_type": "game_end", "content": "游戏结束", "round_num": 3, "phase": "game_over"},
        ]
        result = reconstruct_game_replay("g1", logs)
        assert result["total_events"] == 3
        # game_end 重要性为1.0，其他系统事件较低
        for event in result["timeline"]:
            assert 0 <= event["significance"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
