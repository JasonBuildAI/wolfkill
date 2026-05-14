"""
Leaderboard management module
排行榜管理模块 - 追踪agent性能，支持不同版本/模型
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from backend.game_engine.roles import ROLE_TEAM, Role, Team

logger = logging.getLogger(__name__)

# 排行榜权重配置
LEADERBOARD_WEIGHTS = {
    "win_rate": 0.35,
    "survival_rate": 0.20,
    "avg_contribution": 0.25,
    "avg_vote_accuracy": 0.10,
    "avg_action_accuracy": 0.10,
}

# 最少游戏场次才计入排行榜
MIN_GAMES_FOR_RANKING = 3


def update_leaderboard_entry(
    player_id: str,
    role: Role,
    game_result: dict,
    metrics: dict,
    player_name: str = "",
    model_version: str = "default",
) -> dict[str, Any]:
    """
    更新排行榜条目（内存计算版本）

    Args:
        player_id: 玩家ID
        role: 角色
        game_result: 游戏结果
        metrics: 玩家指标
        player_name: 玩家名称
        model_version: 模型版本

    Returns:
        dict: 更新后的排行榜条目数据
    """
    winner = game_result.get("winner", "")
    team = ROLE_TEAM.get(role, Team.GOOD).value
    is_winner = team == winner

    # 从metrics中提取数据
    contribution = metrics.get("contribution_score", 0.5)
    vote_accuracy = metrics.get("vote_accuracy", 0.0)
    action_accuracy = metrics.get("check_accuracy", 0.0) or metrics.get("protect_accuracy", 0.0) or \
                      metrics.get("kill_accuracy", 0.0) or vote_accuracy
    survived = metrics.get("survived", False)

    entry = {
        "player_id": player_id,
        "player_name": player_name or player_id,
        "role": role.value,
        "model_version": model_version,
        "games_count": 1,
        "wins": 1 if is_winner else 0,
        "win_rate": 1.0 if is_winner else 0.0,
        "survival_rate": 1.0 if survived else 0.0,
        "avg_contribution": contribution,
        "avg_vote_accuracy": vote_accuracy,
        "avg_action_accuracy": action_accuracy,
        "total_score": _calculate_leaderboard_score(
            1.0 if is_winner else 0.0,
            1.0 if survived else 0.0,
            contribution,
            vote_accuracy,
            action_accuracy,
        ),
        "updated_at": datetime.now().isoformat(),
    }

    return entry


def merge_leaderboard_entries(
    existing: dict[str, Any],
    new_entry: dict[str, Any],
) -> dict[str, Any]:
    """
    合并排行榜条目（用于更新已有记录）

    Args:
        existing: 现有记录
        new_entry: 新记录

    Returns:
        dict: 合并后的记录
    """
    old_games = existing.get("games_count", 0)
    new_games = new_entry.get("games_count", 0)
    total_games = old_games + new_games

    if total_games == 0:
        return new_entry

    # 加权平均更新
    merged = {
        "player_id": existing.get("player_id", new_entry.get("player_id", "")),
        "player_name": new_entry.get("player_name") or existing.get("player_name", ""),
        "role": existing.get("role", new_entry.get("role")),
        "model_version": existing.get("model_version", new_entry.get("model_version", "default")),
        "games_count": total_games,
        "wins": existing.get("wins", 0) + new_entry.get("wins", 0),
        "win_rate": round(
            (existing.get("wins", 0) + new_entry.get("wins", 0)) / total_games, 4
        ),
        "survival_rate": round(
            (existing.get("survival_rate", 0) * old_games +
             new_entry.get("survival_rate", 0) * new_games) / total_games, 4
        ),
        "avg_contribution": round(
            (existing.get("avg_contribution", 0) * old_games +
             new_entry.get("avg_contribution", 0) * new_games) / total_games, 4
        ),
        "avg_vote_accuracy": round(
            (existing.get("avg_vote_accuracy", 0) * old_games +
             new_entry.get("avg_vote_accuracy", 0) * new_games) / total_games, 4
        ),
        "avg_action_accuracy": round(
            (existing.get("avg_action_accuracy", 0) * old_games +
             new_entry.get("avg_action_accuracy", 0) * new_games) / total_games, 4
        ),
        "updated_at": datetime.now().isoformat(),
    }

    # 重新计算综合评分
    merged["total_score"] = _calculate_leaderboard_score(
        merged["win_rate"],
        merged["survival_rate"],
        merged["avg_contribution"],
        merged["avg_vote_accuracy"],
        merged["avg_action_accuracy"],
    )

    return merged


def get_leaderboard(
    entries: list[dict[str, Any]],
    role: Optional[Role] = None,
    metric: str = "win_rate",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    获取排行榜

    Args:
        entries: 排行榜条目列表
        role: 可选的角色过滤
        metric: 排序指标 (win_rate, survival_rate, avg_contribution, total_score)
        limit: 返回数量限制

    Returns:
        list: 排序后的排行榜
    """
    if not entries:
        return []

    # 过滤
    filtered = entries
    if role:
        filtered = [e for e in entries if e.get("role") == role.value]

    # 过滤掉游戏场次不足的
    filtered = [e for e in filtered if e.get("games_count", 0) >= MIN_GAMES_FOR_RANKING]

    # 排序
    valid_metrics = {"win_rate", "survival_rate", "avg_contribution",
                     "avg_vote_accuracy", "avg_action_accuracy", "total_score", "games_count"}
    sort_key = metric if metric in valid_metrics else "total_score"

    sorted_entries = sorted(
        filtered,
        key=lambda x: x.get(sort_key, 0),
        reverse=True,
    )

    # 添加排名
    for i, entry in enumerate(sorted_entries[:limit], 1):
        entry["rank"] = i

    return sorted_entries[:limit]


def get_agent_comparison(
    entries: list[dict[str, Any]],
    agent_ids: list[str],
) -> dict[str, Any]:
    """
    比较多个agent的表现

    Args:
        entries: 排行榜条目列表
        agent_ids: 要比较的agent ID列表

    Returns:
        dict: 对比结果
    """
    if not entries or not agent_ids:
        return {"agents": [], "comparison": {}}

    # 收集每个agent的数据
    agent_data = defaultdict(list)
    for entry in entries:
        player_id = entry.get("player_id", "")
        if player_id in agent_ids:
            agent_data[player_id].append(entry)

    # 聚合每个agent的跨角色数据
    agents_summary = []
    for agent_id in agent_ids:
        agent_entries = agent_data.get(agent_id, [])
        if not agent_entries:
            continue

        total_games = sum(e.get("games_count", 0) for e in agent_entries)
        total_wins = sum(e.get("wins", 0) for e in agent_entries)

        summary = {
            "player_id": agent_id,
            "player_name": agent_entries[0].get("player_name", agent_id),
            "model_version": agent_entries[0].get("model_version", "default"),
            "total_games": total_games,
            "total_wins": total_wins,
            "overall_win_rate": round(total_wins / total_games, 4) if total_games > 0 else 0.0,
            "roles": {},
        }

        for entry in agent_entries:
            role = entry.get("role", "unknown")
            summary["roles"][role] = {
                "games_count": entry.get("games_count", 0),
                "win_rate": entry.get("win_rate", 0.0),
                "survival_rate": entry.get("survival_rate", 0.0),
                "avg_contribution": entry.get("avg_contribution", 0.0),
            }

        agents_summary.append(summary)

    # 生成对比数据
    comparison = {
        "metrics": ["overall_win_rate", "survival_rate", "avg_contribution"],
        "best_by_metric": {},
    }

    for metric in comparison["metrics"]:
        best_agent = None
        best_value = -1
        for agent in agents_summary:
            if metric == "overall_win_rate":
                value = agent["overall_win_rate"]
            else:
                # 跨角色平均
                values = [r.get(metric, 0) for r in agent["roles"].values()]
                value = sum(values) / len(values) if values else 0.0

            if value > best_value:
                best_value = value
                best_agent = agent["player_id"]

        comparison["best_by_metric"][metric] = {
            "agent_id": best_agent,
            "value": round(best_value, 4),
        }

    return {
        "agents": agents_summary,
        "comparison": comparison,
    }


def get_role_leaderboard(
    entries: list[dict[str, Any]],
    role: Role,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    获取特定角色的排行榜

    Args:
        entries: 排行榜条目列表
        role: 角色
        limit: 返回数量

    Returns:
        list: 该角色的排行榜
    """
    return get_leaderboard(entries, role=role, metric="total_score", limit=limit)


def _calculate_leaderboard_score(
    win_rate: float,
    survival_rate: float,
    avg_contribution: float,
    avg_vote_accuracy: float,
    avg_action_accuracy: float,
) -> float:
    """
    计算综合排行榜评分

    Args:
        win_rate: 胜率
        survival_rate: 生存率
        avg_contribution: 平均贡献分
        avg_vote_accuracy: 平均投票准确率
        avg_action_accuracy: 平均行动准确率

    Returns:
        float: 综合评分 (0-1)
    """
    score = (
        win_rate * LEADERBOARD_WEIGHTS["win_rate"] +
        survival_rate * LEADERBOARD_WEIGHTS["survival_rate"] +
        avg_contribution * LEADERBOARD_WEIGHTS["avg_contribution"] +
        avg_vote_accuracy * LEADERBOARD_WEIGHTS["avg_vote_accuracy"] +
        avg_action_accuracy * LEADERBOARD_WEIGHTS["avg_action_accuracy"]
    )
    return round(min(max(score, 0.0), 1.0), 4)


def calculate_rank_changes(
    current_entries: list[dict[str, Any]],
    previous_entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    计算排名变化

    Args:
        current_entries: 当前排行榜
        previous_entries: 上一次排行榜

    Returns:
        dict: {player_id: {current_rank, previous_rank, change}}
    """
    # 构建上一次排名映射
    previous_ranks = {}
    for entry in previous_entries:
        player_id = entry.get("player_id", "")
        role = entry.get("role", "")
        key = f"{player_id}:{role}"
        previous_ranks[key] = entry.get("rank", 0)

    changes = {}
    for entry in current_entries:
        player_id = entry.get("player_id", "")
        role = entry.get("role", "")
        key = f"{player_id}:{role}"
        current_rank = entry.get("rank", 0)
        previous_rank = previous_ranks.get(key, current_rank)

        changes[key] = {
            "player_id": player_id,
            "role": role,
            "current_rank": current_rank,
            "previous_rank": previous_rank,
            "change": previous_rank - current_rank,  # 正值表示上升
        }

    return changes


def get_leaderboard_statistics(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """
    获取排行榜统计信息

    Args:
        entries: 排行榜条目列表

    Returns:
        dict: 统计信息
    """
    if not entries:
        return {
            "total_players": 0,
            "total_games": 0,
            "avg_win_rate": 0.0,
            "role_distribution": {},
            "model_versions": [],
        }

    total_games = sum(e.get("games_count", 0) for e in entries)
    total_wins = sum(e.get("wins", 0) for e in entries)

    # 角色分布
    role_dist = defaultdict(lambda: {"count": 0, "avg_win_rate": 0.0, "total_games": 0})
    for entry in entries:
        role = entry.get("role", "unknown")
        role_dist[role]["count"] += 1
        role_dist[role]["total_games"] += entry.get("games_count", 0)
        role_dist[role]["avg_win_rate"] += entry.get("win_rate", 0.0)

    for role_data in role_dist.values():
        if role_data["count"] > 0:
            role_data["avg_win_rate"] = round(
                role_data["avg_win_rate"] / role_data["count"], 4
            )

    # 模型版本
    model_versions = list(set(
        e.get("model_version", "default") for e in entries
    ))

    return {
        "total_players": len(set(e.get("player_id") for e in entries)),
        "total_entries": len(entries),
        "total_games": total_games,
        "avg_win_rate": round(total_wins / total_games, 4) if total_games > 0 else 0.0,
        "role_distribution": dict(role_dist),
        "model_versions": model_versions,
    }
