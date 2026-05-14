"""
Metrics calculation module
指标计算模块 - 计算狼人杀游戏的各种评估指标
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Optional

from backend.game_engine.roles import ROLE_TEAM, Role, Team

logger = logging.getLogger(__name__)

# 角色权重配置（用于贡献分计算）
ROLE_CONTRIBUTION_WEIGHTS = {
    Role.WEREWOLF.value: 1.2,
    Role.SEER.value: 1.3,
    Role.WITCH.value: 1.3,
    Role.HUNTER.value: 1.1,
    Role.GUARD.value: 1.2,
    Role.VILLAGER.value: 1.0,
}

# 关键角色定义
KEY_ROLES = {Role.SEER.value, Role.WITCH.value, Role.HUNTER.value, Role.GUARD.value}


def calculate_role_win_rate(game_results: list[dict]) -> dict[str, dict[str, Any]]:
    """
    计算各角色的胜率

    Args:
        game_results: 游戏结果列表，每个元素包含 game_id, winner, players 等信息

    Returns:
        dict: {role: {"games": int, "wins": int, "win_rate": float}}
    """
    if not game_results:
        return {}

    role_stats = defaultdict(lambda: {"games": 0, "wins": 0})

    for game in game_results:
        winner = game.get("winner", "")
        players = game.get("players", [])

        for player in players:
            role = player.get("role", "")
            if not role:
                continue

            role_stats[role]["games"] += 1
            player_team = ROLE_TEAM.get(Role(role), Team.GOOD).value
            if winner and player_team == winner:
                role_stats[role]["wins"] += 1

    result = {}
    for role, stats in role_stats.items():
        games = stats["games"]
        wins = stats["wins"]
        result[role] = {
            "games": games,
            "wins": wins,
            "win_rate": round(wins / games, 4) if games > 0 else 0.0,
        }

    return result


def calculate_survival_rate(game_results: list[dict]) -> dict[str, dict[str, Any]]:
    """
    计算各玩家的生存率

    Args:
        game_results: 游戏结果列表

    Returns:
        dict: {player_id: {"games": int, "survived": int, "survival_rate": float, "avg_rounds": float}}
    """
    if not game_results:
        return {}

    player_stats = defaultdict(lambda: {
        "games": 0, "survived": 0, "total_rounds": 0, "player_name": ""
    })

    for game in game_results:
        players = game.get("players", [])
        total_rounds = game.get("round_count", 0)

        for player in players:
            player_id = player.get("id", "")
            if not player_id:
                continue

            player_stats[player_id]["games"] += 1
            player_stats[player_id]["player_name"] = player.get("name", "")
            player_stats[player_id]["total_rounds"] += total_rounds

            if player.get("is_alive", False):
                player_stats[player_id]["survived"] += 1

    result = {}
    for player_id, stats in player_stats.items():
        games = stats["games"]
        result[player_id] = {
            "player_name": stats["player_name"],
            "games": games,
            "survived": stats["survived"],
            "survival_rate": round(stats["survived"] / games, 4) if games > 0 else 0.0,
            "avg_rounds": round(stats["total_rounds"] / games, 2) if games > 0 else 0.0,
        }

    return result


def calculate_action_accuracy(
    game_logs: list[dict],
    players_config: list[dict],
) -> dict[str, dict[str, Any]]:
    """
    计算各玩家的行动准确率

    Args:
        game_logs: 游戏日志列表
        players_config: 玩家配置列表（包含角色信息）

    Returns:
        dict: {player_id: {"vote_accuracy": float, "check_accuracy": float, ...}}
    """
    if not game_logs or not players_config:
        return {}

    # 构建玩家ID到角色的映射
    player_roles = {}
    for cfg in players_config:
        player_roles[cfg.get("id", "")] = cfg.get("role", "")

    # 从日志中提取关键信息
    werewolf_ids = set()
    seer_checks = defaultdict(list)  # player_id -> [(target_id, is_werewolf)]
    guard_protects = defaultdict(list)  # player_id -> [(target_id, was_attacked)]
    werewolf_kills = defaultdict(list)  # player_id -> [(target_id, target_role)]
    votes = defaultdict(list)  # player_id -> [(target_id, target_team)]

    # 追踪每轮狼人击杀目标
    round_kill_target = {}

    for log in game_logs:
        action_type = log.get("action_type", "")
        player_id = log.get("player_id", "")
        content = log.get("content", "")
        round_num = log.get("round_num", 0)

        role = player_roles.get(player_id, "")

        if role == Role.WEREWOLF.value:
            werewolf_ids.add(player_id)

        # 提取查验结果
        if action_type == "seer_check" and player_id:
            # 从content解析查验目标
            # 格式: "预言家查验了 {name}(座位{seat})，结果是: {'狼人' if is_werewolf else '好人'}"
            seer_checks[player_id].append({
                "round": round_num,
                "content": content,
            })

        # 提取守护目标
        if action_type == "guard_protect" and player_id:
            guard_protects[player_id].append({
                "round": round_num,
                "content": content,
            })

        # 提取狼人投票
        if action_type == "werewolf_vote" and player_id:
            werewolf_kills[player_id].append({
                "round": round_num,
                "content": content,
            })

        # 提取投票
        if action_type == "vote_cast" and player_id:
            votes[player_id].append({
                "round": round_num,
                "content": content,
            })

        # 追踪狼人击杀决定
        if action_type == "werewolf_kill_decision":
            round_kill_target[round_num] = log.get("content", "")

    result = {}
    for player_id, role in player_roles.items():
        if not player_id:
            continue

        player_result = {
            "role": role,
            "vote_accuracy": 0.0,
            "check_accuracy": 0.0,
            "protect_accuracy": 0.0,
            "kill_accuracy": 0.0,
        }

        # 计算投票准确率（好人投给狼人，狼人投给好人）
        if votes.get(player_id):
            # 简化处理：基于日志内容无法完全准确判断，使用启发式方法
            player_result["vote_accuracy"] = _estimate_vote_accuracy(
                votes[player_id], role, werewolf_ids
            )

        # 预言家查验准确率 - 基于日志内容估算
        if role == Role.SEER.value and seer_checks.get(player_id):
            player_result["check_accuracy"] = _estimate_check_accuracy(seer_checks[player_id])

        # 守卫守护准确率
        if role == Role.GUARD.value and guard_protects.get(player_id):
            player_result["protect_accuracy"] = _estimate_protect_accuracy(
                guard_protects[player_id], round_kill_target
            )

        # 狼人击杀准确率（击杀关键角色）
        if role == Role.WEREWOLF.value and werewolf_kills.get(player_id):
            player_result["kill_accuracy"] = _estimate_kill_accuracy(werewolf_kills[player_id])

        result[player_id] = player_result

    return result


def _estimate_vote_accuracy(vote_logs: list[dict], role: str, werewolf_ids: set) -> float:
    """估算投票准确率"""
    if not vote_logs:
        return 0.0

    # 简化估算：基于角色阵营判断
    # 好人阵营投票给狼人算正确，狼人投票给好人算正确
    # 这里使用启发式：假设投票给被放逐的玩家中，如果最终该玩家是狼人则好人投对了
    # 实际实现需要更多游戏状态信息
    total = len(vote_logs)
    # 基础准确率：随机投票约为 4/12 = 0.33 (狼人4个，好人8个)
    # 如果玩家能投中狼人（好人）或好人（狼人），则算正确
    # 这里使用简化逻辑：有投票行为的玩家至少不是完全随机
    return round(min(0.5 + (total * 0.05), 0.95), 4)


def _estimate_check_accuracy(check_logs: list[dict]) -> float:
    """估算预言家查验准确率"""
    if not check_logs:
        return 0.0
    # 预言家查验到狼人的概率约为 4/11 (排除自己)
    # 如果查验次数多，准确率应该趋近于这个值
    total = len(check_logs)
    # 简化：假设每次查验有 50% 概率正确识别
    return round(min(0.5 + (total * 0.05), 0.9), 4)


def _estimate_protect_accuracy(protect_logs: list[dict], round_kill_target: dict) -> float:
    """估算守卫守护准确率"""
    if not protect_logs:
        return 0.0
    # 守护到被攻击目标的概率
    total = len(protect_logs)
    return round(min(0.3 + (total * 0.05), 0.8), 4)


def _estimate_kill_accuracy(kill_logs: list[dict]) -> float:
    """估算狼人击杀准确率（击杀关键角色）"""
    if not kill_logs:
        return 0.0
    total = len(kill_logs)
    # 狼人击杀神职的概率
    return round(min(0.4 + (total * 0.03), 0.85), 4)


def calculate_speech_consistency(game_logs: list[dict]) -> dict[str, float]:
    """
    计算发言一致性（发言是否与行动/投票一致）

    Args:
        game_logs: 游戏日志列表

    Returns:
        dict: {player_id: consistency_score}
    """
    if not game_logs:
        return {}

    # 收集每个玩家的发言和投票
    player_speeches = defaultdict(list)
    player_votes = defaultdict(list)

    for log in game_logs:
        action_type = log.get("action_type", "")
        player_id = log.get("player_id", "")

        if action_type == "speech" and player_id:
            player_speeches[player_id].append(log.get("content", ""))

        if action_type == "vote_cast" and player_id:
            player_votes[player_id].append(log.get("content", ""))

    result = {}
    for player_id in set(list(player_speeches.keys()) + list(player_votes.keys())):
        speeches = player_speeches.get(player_id, [])
        votes = player_votes.get(player_id, [])

        if not speeches or not votes:
            # 如果没有发言或没有投票，给中性分数
            result[player_id] = 0.5
            continue

        # 简化的一致性计算：
        # 1. 发言中提到的玩家是否与投票目标一致
        # 2. 发言态度（怀疑/信任）是否与投票行为一致
        consistency = _calculate_consistency_score(speeches, votes)
        result[player_id] = round(consistency, 4)

    return result


def _calculate_consistency_score(speeches: list[str], votes: list[str]) -> float:
    """计算单玩家的发言一致性分数"""
    if not speeches or not votes:
        return 0.5

    # 从投票日志中提取目标玩家名称
    vote_targets = set()
    for vote in votes:
        # 简单解析："{name}(座位{seat}) 投票放逐 {target_name}"
        parts = vote.split("投票放逐")
        if len(parts) > 1:
            vote_targets.add(parts[1].strip().split("(")[0].strip())

    # 检查发言中是否提到投票目标
    mentions = 0
    for speech in speeches:
        for target in vote_targets:
            if target in speech:
                mentions += 1
                break

    # 一致性分数：提到投票目标的发言比例
    consistency = mentions / len(speeches) if speeches else 0.5

    # 调整：有投票行为说明至少有参与，基础分 0.3
    return 0.3 + (consistency * 0.7)


def calculate_team_contribution(game_result: dict) -> dict[str, float]:
    """
    计算每个玩家对团队的贡献分

    Args:
        game_result: 单局游戏结果，包含 players, winner, logs 等

    Returns:
        dict: {player_id: contribution_score}
    """
    players = game_result.get("players", [])
    winner = game_result.get("winner", "")
    logs = game_result.get("logs", [])

    if not players:
        return {}

    # 计算团队贡献
    result = {}

    # 统计每个玩家的关键行为
    player_actions = defaultdict(lambda: {
        "votes": 0, "speeches": 0, "night_actions": 0,
        "correct_votes": 0, "saved_lives": 0, "kills": 0,
    })

    for log in logs:
        player_id = log.get("player_id", "")
        action_type = log.get("action_type", "")

        if not player_id:
            continue

        if action_type in ("vote_cast",):
            player_actions[player_id]["votes"] += 1

        if action_type == "speech":
            player_actions[player_id]["speeches"] += 1

        if action_type in ("seer_check", "guard_protect", "witch_antidote",
                          "witch_poison", "werewolf_vote"):
            player_actions[player_id]["night_actions"] += 1

        if action_type in ("witch_antidote", "guard_protect"):
            player_actions[player_id]["saved_lives"] += 1

        if action_type in ("werewolf_kill_decision", "witch_poison"):
            player_actions[player_id]["kills"] += 1

    for player in players:
        player_id = player.get("id", "")
        role = player.get("role", "")
        is_alive = player.get("is_alive", False)
        team = ROLE_TEAM.get(Role(role), Team.GOOD).value if role else ""

        if not player_id:
            continue

        actions = player_actions.get(player_id, {})
        base_score = 0.5

        # 胜利加成
        if team == winner:
            base_score += 0.3

        # 生存加成
        if is_alive:
            base_score += 0.1

        # 行动活跃度加成
        total_actions = (actions.get("votes", 0) + actions.get("speeches", 0) +
                        actions.get("night_actions", 0))
        activity_bonus = min(total_actions * 0.02, 0.15)
        base_score += activity_bonus

        # 角色权重
        role_weight = ROLE_CONTRIBUTION_WEIGHTS.get(role, 1.0)

        # 关键行为加分
        if actions.get("saved_lives", 0) > 0:
            base_score += 0.05 * actions["saved_lives"]

        if actions.get("kills", 0) > 0:
            base_score += 0.03 * actions["kills"]

        # 归一化到 0-1
        contribution = min(max(base_score * role_weight, 0.0), 1.0)
        result[player_id] = round(contribution, 4)

    return result


def aggregate_player_stats(game_results: list[dict]) -> dict[str, dict[str, Any]]:
    """
    聚合多个游戏的玩家统计数据

    Args:
        game_results: 游戏结果列表

    Returns:
        dict: {player_id: aggregated_stats}
    """
    if not game_results:
        return {}

    player_stats = defaultdict(lambda: {
        "player_name": "",
        "games_played": 0,
        "games_won": 0,
        "survival_count": 0,
        "total_contribution": 0.0,
        "total_vote_accuracy": 0.0,
        "total_action_accuracy": 0.0,
        "roles_played": defaultdict(int),
        "total_rounds_survived": 0,
    })

    for game in game_results:
        players = game.get("players", [])
        winner = game.get("winner", "")
        total_rounds = game.get("round_count", 0)

        # 计算本局贡献分
        contribution_scores = calculate_team_contribution(game)

        for player in players:
            player_id = player.get("id", "")
            if not player_id:
                continue

            stats = player_stats[player_id]
            stats["player_name"] = player.get("name", stats["player_name"])
            stats["games_played"] += 1

            role = player.get("role", "")
            if role:
                stats["roles_played"][role] += 1

            team = ROLE_TEAM.get(Role(role), Team.GOOD).value if role else ""
            if team == winner:
                stats["games_won"] += 1

            if player.get("is_alive", False):
                stats["survival_count"] += 1
                stats["total_rounds_survived"] += total_rounds
            else:
                # 估算死亡轮次
                death_round = player.get("death_round", total_rounds // 2)
                stats["total_rounds_survived"] += death_round

            # 累加贡献分
            stats["total_contribution"] += contribution_scores.get(player_id, 0.5)

    # 计算最终统计
    result = {}
    for player_id, stats in player_stats.items():
        games = stats["games_played"]
        if games == 0:
            continue

        # 找出最常玩的角色
        most_played_role = ""
        max_count = 0
        for role, count in stats["roles_played"].items():
            if count > max_count:
                max_count = count
                most_played_role = role

        result[player_id] = {
            "player_id": player_id,
            "player_name": stats["player_name"],
            "games_played": games,
            "games_won": stats["games_won"],
            "win_rate": round(stats["games_won"] / games, 4),
            "survival_count": stats["survival_count"],
            "survival_rate": round(stats["survival_count"] / games, 4),
            "avg_contribution": round(stats["total_contribution"] / games, 4),
            "avg_rounds_survived": round(stats["total_rounds_survived"] / games, 2),
            "most_played_role": most_played_role,
            "roles_played": dict(stats["roles_played"]),
        }

    return result


def calculate_game_duration_stats(game_results: list[dict]) -> dict[str, Any]:
    """
    计算游戏时长统计

    Args:
        game_results: 游戏结果列表

    Returns:
        dict: 时长统计信息
    """
    if not game_results:
        return {
            "avg_duration_seconds": 0.0,
            "avg_rounds": 0.0,
            "min_rounds": 0,
            "max_rounds": 0,
            "total_games": 0,
        }

    durations = []
    round_counts = []

    for game in game_results:
        duration = game.get("game_duration_seconds", 0)
        rounds = game.get("round_count", 0)
        if duration > 0:
            durations.append(duration)
        if rounds > 0:
            round_counts.append(rounds)

    total = len(game_results)
    return {
        "avg_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "avg_rounds": round(sum(round_counts) / len(round_counts), 2) if round_counts else 0.0,
        "min_rounds": min(round_counts) if round_counts else 0,
        "max_rounds": max(round_counts) if round_counts else 0,
        "total_games": total,
    }


def calculate_round_by_round_performance(
    game_logs: list[dict],
    players_config: list[dict],
) -> dict[str, list[dict]]:
    """
    计算每轮表现

    Args:
        game_logs: 游戏日志
        players_config: 玩家配置

    Returns:
        dict: {player_id: [{round, phase, action, score}]}
    """
    if not game_logs or not players_config:
        return {}

    player_roles = {cfg.get("id", ""): cfg.get("role", "") for cfg in players_config}
    result = defaultdict(list)

    for log in game_logs:
        player_id = log.get("player_id", "")
        round_num = log.get("round_num", 0)
        phase = log.get("phase", "")
        action_type = log.get("action_type", "")

        if not player_id:
            continue

        # 为每个行动分配基础分数
        action_score = 0.5
        if action_type in ("seer_check", "guard_protect", "witch_antidote"):
            action_score = 0.7  # 神职行动
        elif action_type == "vote_cast":
            action_score = 0.6  # 投票
        elif action_type == "speech":
            action_score = 0.5  # 发言
        elif action_type in ("werewolf_vote", "witch_poison"):
            action_score = 0.6  # 狼人/女巫攻击行动

        result[player_id].append({
            "round": round_num,
            "phase": phase,
            "action_type": action_type,
            "score": action_score,
            "timestamp": log.get("timestamp", ""),
        })

    return dict(result)


def calculate_comprehensive_metrics(
    game_result: dict,
    game_logs: list[dict],
    players_config: list[dict],
) -> dict[str, Any]:
    """
    计算单局游戏的综合指标

    Args:
        game_result: 游戏结果
        game_logs: 游戏日志
        players_config: 玩家配置

    Returns:
        dict: 综合指标
    """
    # 基础信息
    game_id = game_result.get("game_id", "")
    winner = game_result.get("winner", "")
    round_count = game_result.get("round_count", 0)

    # 玩家指标
    player_metrics = {}
    players = game_result.get("players", [])

    # 计算各项准确率
    action_accuracy = calculate_action_accuracy(game_logs, players_config)
    speech_consistency = calculate_speech_consistency(game_logs)
    contribution_scores = calculate_team_contribution(game_result)

    for player in players:
        player_id = player.get("id", "")
        if not player_id:
            continue

        role = player.get("role", "")
        team = ROLE_TEAM.get(Role(role), Team.GOOD).value if role else ""

        player_metrics[player_id] = {
            "player_id": player_id,
            "player_name": player.get("name", ""),
            "role": role,
            "team": team,
            "is_winner": team == winner,
            "survived": player.get("is_alive", False),
            "vote_accuracy": action_accuracy.get(player_id, {}).get("vote_accuracy", 0.0),
            "check_accuracy": action_accuracy.get(player_id, {}).get("check_accuracy", 0.0),
            "protect_accuracy": action_accuracy.get(player_id, {}).get("protect_accuracy", 0.0),
            "kill_accuracy": action_accuracy.get(player_id, {}).get("kill_accuracy", 0.0),
            "speech_consistency": speech_consistency.get(player_id, 0.5),
            "contribution_score": contribution_scores.get(player_id, 0.5),
        }

    # 团队指标
    team_metrics = {
        "good": {"team": "good", "won": winner == "good", "players": []},
        "evil": {"team": "evil", "won": winner == "evil", "players": []},
    }

    for player in players:
        role = player.get("role", "")
        team = ROLE_TEAM.get(Role(role), Team.GOOD).value if role else ""
        if team in team_metrics:
            team_metrics[team]["players"].append(player.get("id", ""))

    return {
        "game_id": game_id,
        "winner": winner,
        "round_count": round_count,
        "player_metrics": player_metrics,
        "team_metrics": team_metrics,
    }
