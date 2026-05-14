"""
Replay/attribution analysis module
游戏回放与归因分析模块
"""
from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from backend.game_engine.roles import ROLE_NAME_CN, ROLE_TEAM, Role, Team

logger = logging.getLogger(__name__)

# 关键行为类型及其重要性权重
ACTION_SIGNIFICANCE = {
    "game_start": 0.3,
    "role_assignment": 0.2,
    "werewolf_info": 0.2,
    "phase_start": 0.1,
    "phase_skip": 0.1,
    "guard_protect": 0.6,
    "guard_skip": 0.2,
    "werewolf_vote": 0.5,
    "werewolf_kill_decision": 0.8,
    "werewolf_kill_random": 0.6,
    "seer_check": 0.7,
    "seer_skip": 0.2,
    "witch_info": 0.3,
    "witch_antidote": 0.8,
    "witch_poison": 0.8,
    "witch_skip": 0.2,
    "guard_saved": 0.7,
    "witch_saved": 0.7,
    "player_death": 0.9,
    "peaceful_night": 0.5,
    "hunter_trigger": 0.7,
    "hunter_shoot": 0.8,
    "speech": 0.4,
    "vote_cast": 0.5,
    "vote_abstain": 0.2,
    "vote_result": 0.6,
    "vote_tie": 0.5,
    "vote_eliminate": 0.9,
    "round_start": 0.2,
    "round_end": 0.3,
    "game_end": 1.0,
}

# 可能导致局势转折的行为
TURNING_POINT_ACTIONS = {
    "witch_antidote", "witch_poison", "guard_protect",
    "werewolf_kill_decision", "vote_eliminate", "hunter_shoot",
    "player_death",
}


def reconstruct_game_replay(game_id: str, logs: list[dict]) -> dict[str, Any]:
    """
    从日志重建游戏回放

    Args:
        game_id: 游戏ID
        logs: 游戏日志列表

    Returns:
        dict: 回放数据，包含时间线和事件分析
    """
    if not logs:
        return {
            "game_id": game_id,
            "timeline": [],
            "events_by_round": {},
            "key_moments": [],
            "total_events": 0,
        }

    timeline = []
    events_by_round = defaultdict(list)
    key_moments = []

    for log in logs:
        event = _log_to_replay_event(game_id, log)
        timeline.append(event)

        round_num = log.get("round_num", 0)
        events_by_round[round_num].append(event)

        # 识别关键时刻
        if event.get("is_turning_point") or event.get("significance", 0) >= 0.7:
            key_moments.append({
                "event_id": event["event_id"],
                "round": event["round_num"],
                "phase": event["phase"],
                "event_type": event["event_type"],
                "description": event["content"],
                "significance": event["significance"],
            })

    return {
        "game_id": game_id,
        "timeline": timeline,
        "events_by_round": dict(events_by_round),
        "key_moments": key_moments,
        "total_events": len(timeline),
    }


def _log_to_replay_event(game_id: str, log: dict) -> dict[str, Any]:
    """将日志条目转换为回放事件"""
    action_type = log.get("action_type", "")
    significance = ACTION_SIGNIFICANCE.get(action_type, 0.3)

    # 判断是否为转折点
    is_turning_point = action_type in TURNING_POINT_ACTIONS and significance >= 0.6

    # 从content中提取目标信息
    target_info = _extract_target_from_content(action_type, log.get("content", ""))

    event = {
        "event_id": str(uuid.uuid4())[:8],
        "game_id": game_id,
        "round_num": log.get("round_num", 0),
        "phase": log.get("phase", ""),
        "timestamp": log.get("timestamp", datetime.now().isoformat()),
        "event_type": action_type,
        "player_id": log.get("player_id"),
        "player_name": None,
        "role": log.get("role"),
        "target_id": target_info.get("target_id"),
        "target_name": target_info.get("target_name"),
        "target_role": target_info.get("target_role"),
        "content": log.get("content", ""),
        "context": {},
        "significance": significance,
        "is_turning_point": is_turning_point,
    }

    return event


def _extract_target_from_content(action_type: str, content: str) -> dict[str, Any]:
    """从日志内容中提取目标信息"""
    result = {"target_id": None, "target_name": None, "target_role": None}

    if not content:
        return result

    # 尝试提取目标名称（简化解析）
    if "守护了" in content:
        parts = content.split("守护了")
        if len(parts) > 1:
            result["target_name"] = parts[1].strip().split("(")[0].strip()
    elif "查验了" in content:
        parts = content.split("查验了")
        if len(parts) > 1:
            result["target_name"] = parts[1].strip().split("(")[0].strip()
    elif "投票击杀" in content:
        parts = content.split("投票击杀")
        if len(parts) > 1:
            result["target_name"] = parts[1].strip().split("(")[0].strip()
    elif "救了" in content:
        parts = content.split("救了")
        if len(parts) > 1:
            result["target_name"] = parts[1].strip().split("(")[0].strip()
    elif "毒杀了" in content:
        parts = content.split("毒杀了")
        if len(parts) > 1:
            result["target_name"] = parts[1].strip().split("(")[0].strip()
    elif "投票放逐" in content:
        parts = content.split("投票放逐")
        if len(parts) > 1:
            result["target_name"] = parts[1].strip().split("(")[0].strip()
    elif "带走了" in content:
        parts = content.split("带走了")
        if len(parts) > 1:
            result["target_name"] = parts[1].strip().split("(")[0].strip()
    elif "在夜晚死亡" in content or "被放逐" in content:
        # 死亡信息中提取玩家名
        result["target_name"] = content.split("(")[0].strip()

    return result


def identify_turning_points(logs: list[dict]) -> list[dict[str, Any]]:
    """
    识别游戏中的关键转折点

    Args:
        logs: 游戏日志列表

    Returns:
        list: 转折点列表，每个元素包含 round, phase, description, impact_score
    """
    if not logs:
        return []

    turning_points = []
    last_werewolf_count = None
    last_good_count = None

    # 追踪每轮结束时的局势变化
    round_events = defaultdict(list)
    for log in logs:
        round_num = log.get("round_num", 0)
        round_events[round_num].append(log)

    for round_num in sorted(round_events.keys()):
        events = round_events[round_num]
        round_turning = []

        for log in events:
            action_type = log.get("action_type", "")
            content = log.get("content", "")
            significance = ACTION_SIGNIFICANCE.get(action_type, 0.3)

            # 识别高影响力事件
            if action_type in TURNING_POINT_ACTIONS and significance >= 0.6:
                impact_score = significance

                # 根据事件类型调整影响力
                if action_type == "witch_antidote":
                    impact_score = 0.85  # 救活关键角色可能改变局势
                elif action_type == "witch_poison":
                    impact_score = 0.9  # 毒杀可能直接减少对方战力
                elif action_type == "vote_eliminate":
                    impact_score = 0.8  # 放逐可能改变阵营平衡
                elif action_type == "hunter_shoot":
                    impact_score = 0.85  # 猎人开枪可能带走关键角色
                elif action_type == "player_death" and "预言家" in content:
                    impact_score = 0.95  # 预言家死亡是重大转折
                elif action_type == "player_death" and "女巫" in content:
                    impact_score = 0.9  # 女巫死亡是重大转折

                round_turning.append({
                    "round": round_num,
                    "phase": log.get("phase", ""),
                    "description": content,
                    "impact_score": round(impact_score, 2),
                    "action_type": action_type,
                    "player_id": log.get("player_id"),
                    "role": log.get("role"),
                })

        # 如果一轮内有多个转折点，只保留影响最大的
        if round_turning:
            round_turning.sort(key=lambda x: x["impact_score"], reverse=True)
            turning_points.extend(round_turning[:2])  # 每轮最多保留2个

    # 按影响力排序
    turning_points.sort(key=lambda x: x["impact_score"], reverse=True)

    return turning_points


def analyze_attribution(game_result: dict, logs: list[dict]) -> dict[str, Any]:
    """
    归因分析 - 分析哪些决策导致了胜利/失败

    Args:
        game_result: 游戏结果
        logs: 游戏日志

    Returns:
        dict: 归因分析结果
    """
    winner = game_result.get("winner", "")
    players = game_result.get("players", [])

    if not players or not logs:
        return {
            "game_id": game_result.get("game_id", ""),
            "winner": winner,
            "key_decisions": [],
            "winning_factors": [],
            "losing_factors": [],
            "critical_mistakes": [],
            "mvp_players": [],
            "analysis_summary": "数据不足，无法分析",
        }

    key_decisions = []
    winning_factors = []
    losing_factors = []
    critical_mistakes = []
    mvp_candidates = []

    # 分析关键决策
    for log in logs:
        action_type = log.get("action_type", "")
        content = log.get("content", "")
        player_id = log.get("player_id", "")
        role = log.get("role", "")

        # 女巫救人的决策
        if action_type == "witch_antidote":
            key_decisions.append({
                "round": log.get("round_num", 0),
                "phase": log.get("phase", ""),
                "player_id": player_id,
                "role": role,
                "decision": "use_antidote",
                "description": content,
                "impact": "high" if winner == "good" else "medium",
            })

        # 女巫毒人的决策
        if action_type == "witch_poison":
            key_decisions.append({
                "round": log.get("round_num", 0),
                "phase": log.get("phase", ""),
                "player_id": player_id,
                "role": role,
                "decision": "use_poison",
                "description": content,
                "impact": "high",
            })

        # 守卫守护决策
        if action_type == "guard_protect":
            key_decisions.append({
                "round": log.get("round_num", 0),
                "phase": log.get("phase", ""),
                "player_id": player_id,
                "role": role,
                "decision": "protect",
                "description": content,
                "impact": "medium",
            })

        # 预言家查验决策
        if action_type == "seer_check":
            key_decisions.append({
                "round": log.get("round_num", 0),
                "phase": log.get("phase", ""),
                "player_id": player_id,
                "role": role,
                "decision": "check",
                "description": content,
                "impact": "medium",
            })

        # 狼人击杀决策
        if action_type == "werewolf_kill_decision":
            key_decisions.append({
                "round": log.get("round_num", 0),
                "phase": log.get("phase", ""),
                "player_id": player_id,
                "role": role,
                "decision": "kill",
                "description": content,
                "impact": "high",
            })

        # 投票放逐决策
        if action_type == "vote_eliminate":
            key_decisions.append({
                "round": log.get("round_num", 0),
                "phase": log.get("phase", ""),
                "player_id": None,  # 群体决策
                "role": None,
                "decision": "vote_eliminate",
                "description": content,
                "impact": "high",
            })

    # 分析胜利/失败因素
    if winner == "good":
        winning_factors = _analyze_good_victory_factors(logs, players)
        losing_factors = _analyze_evil_defeat_factors(logs, players)
    else:
        winning_factors = _analyze_evil_victory_factors(logs, players)
        losing_factors = _analyze_good_defeat_factors(logs, players)

    # 识别关键错误
    critical_mistakes = _identify_critical_mistakes(logs, players, winner)

    # 评选MVP候选人
    mvp_candidates = _identify_mvp_players(logs, players, winner)

    # 生成分析摘要
    analysis_summary = _generate_attribution_summary(
        winner, key_decisions, winning_factors, losing_factors, critical_mistakes
    )

    return {
        "game_id": game_result.get("game_id", ""),
        "winner": winner,
        "key_decisions": key_decisions,
        "winning_factors": winning_factors,
        "losing_factors": losing_factors,
        "critical_mistakes": critical_mistakes,
        "mvp_players": mvp_candidates,
        "analysis_summary": analysis_summary,
    }


def _analyze_good_victory_factors(logs: list[dict], players: list[dict]) -> list[dict]:
    """分析好人胜利因素"""
    factors = []

    # 检查是否有平安夜
    peaceful_nights = sum(1 for log in logs if log.get("action_type") == "peaceful_night")
    if peaceful_nights > 0:
        factors.append({
            "factor": "peaceful_nights",
            "description": f"出现了 {peaceful_nights} 个平安夜，好人阵营成功保护了关键角色",
            "weight": 0.8,
        })

    # 检查预言家存活情况
    seer_alive = any(p.get("role") == Role.SEER.value and p.get("is_alive")
                     for p in players)
    if seer_alive:
        factors.append({
            "factor": "seer_survived",
            "description": "预言家存活到最后，为好人阵营提供了重要信息",
            "weight": 0.7,
        })

    # 检查女巫解药使用
    antidote_used = any(log.get("action_type") == "witch_antidote" for log in logs)
    if antidote_used:
        factors.append({
            "factor": "antidote_used",
            "description": "女巫成功使用解药救活了关键角色",
            "weight": 0.75,
        })

    # 检查狼人被放逐情况
    eliminated_werewolves = sum(
        1 for log in logs
        if log.get("action_type") == "vote_eliminate"
        and any(p.get("role") == Role.WEREWOLF.value for p in players)
    )
    if eliminated_werewolves >= 2:
        factors.append({
            "factor": "werewolves_eliminated",
            "description": f"成功放逐了 {eliminated_werewolves} 名狼人",
            "weight": 0.9,
        })

    if not factors:
        factors.append({
            "factor": "teamwork",
            "description": "好人阵营通过良好的协作和推理取得了胜利",
            "weight": 0.6,
        })

    return factors


def _analyze_evil_victory_factors(logs: list[dict], players: list[dict]) -> list[dict]:
    """分析狼人胜利因素"""
    factors = []

    # 检查狼人击杀效率
    kill_decisions = [log for log in logs if log.get("action_type") == "werewolf_kill_decision"]
    if len(kill_decisions) >= 2:
        factors.append({
            "factor": "efficient_kills",
            "description": f"狼人连续 {len(kill_decisions)} 晚成功击杀目标",
            "weight": 0.85,
        })

    # 检查是否击杀关键神职
    key_deaths = sum(
        1 for log in logs
        if log.get("action_type") == "player_death"
        and any(role in log.get("content", "")
                for role in ["预言家", "女巫", "猎人", "守卫"])
    )
    if key_deaths >= 2:
        factors.append({
            "factor": "key_roles_killed",
            "description": f"狼人成功击杀 {key_deaths} 名关键神职角色",
            "weight": 0.9,
        })

    # 检查女巫毒药是否浪费
    poison_used = any(log.get("action_type") == "witch_poison" for log in logs)
    if not poison_used:
        factors.append({
            "factor": "poison_unused",
            "description": "女巫未能使用毒药，狼人少了一个威胁",
            "weight": 0.5,
        })

    if not factors:
        factors.append({
            "factor": "deception",
            "description": "狼人通过出色的伪装和欺骗取得了胜利",
            "weight": 0.7,
        })

    return factors


def _analyze_good_defeat_factors(logs: list[dict], players: list[dict]) -> list[dict]:
    """分析好人失败因素"""
    factors = []

    # 检查关键神职过早死亡
    early_deaths = sum(
        1 for log in logs
        if log.get("action_type") == "player_death"
        and log.get("round_num", 0) <= 2
        and any(role in log.get("content", "")
                for role in ["预言家", "女巫"])
    )
    if early_deaths > 0:
        factors.append({
            "factor": "key_roles_died_early",
            "description": f"关键神职在第2轮前死亡，信息链断裂",
            "weight": 0.9,
        })

    # 检查是否放逐了好人
    wrong_votes = sum(
        1 for log in logs
        if log.get("action_type") == "vote_eliminate"
        and any(p.get("role") != Role.WEREWOLF.value for p in players)
    )
    if wrong_votes >= 2:
        factors.append({
            "factor": "wrong_eliminations",
            "description": f"好人阵营错误放逐了 {wrong_votes} 名同伴",
            "weight": 0.85,
        })

    return factors


def _analyze_evil_defeat_factors(logs: list[dict], players: list[dict]) -> list[dict]:
    """分析狼人失败因素"""
    factors = []

    # 检查狼人是否被快速找出
    werewolf_deaths = sum(
        1 for log in logs
        if log.get("action_type") == "vote_eliminate"
        and any(p.get("role") == Role.WEREWOLF.value for p in players)
    )
    if werewolf_deaths >= 2:
        factors.append({
            "factor": "werewolves_exposed",
            "description": f"{werewolf_deaths} 名狼人被投票放逐",
            "weight": 0.9,
        })

    # 检查是否有平安夜
    peaceful_nights = sum(1 for log in logs if log.get("action_type") == "peaceful_night")
    if peaceful_nights >= 2:
        factors.append({
            "factor": "failed_kills",
            "description": f"连续 {peaceful_nights} 个平安夜，狼人未能有效击杀",
            "weight": 0.8,
        })

    return factors


def _identify_critical_mistakes(logs: list[dict], players: list[dict], winner: str) -> list[dict]:
    """识别关键错误"""
    mistakes = []

    # 检查女巫是否毒杀好人
    for log in logs:
        if log.get("action_type") == "witch_poison":
            content = log.get("content", "")
            # 简化判断：如果毒杀了村民或神职（基于最终角色分配）
            # 实际判断需要更多信息
            mistakes.append({
                "round": log.get("round_num", 0),
                "player_id": log.get("player_id"),
                "role": Role.WITCH.value,
                "mistake": "poison_used",
                "description": f"女巫使用毒药: {content}",
                "severity": "medium",
            })

    # 检查守卫是否连续守护同一人（从日志中无法直接判断，需要状态信息）
    # 检查狼人是否投票分散
    for round_num in set(log.get("round_num", 0) for log in logs):
        round_logs = [l for l in logs if l.get("round_num") == round_num]
        wolf_votes = [l for l in round_logs if l.get("action_type") == "werewolf_vote"]
        if len(wolf_votes) >= 3:
            # 如果有3个或以上狼人投票，检查是否一致
            targets = set()
            for vote in wolf_votes:
                content = vote.get("content", "")
                if "投票击杀" in content:
                    target = content.split("投票击杀")[-1].strip().split("(")[0].strip()
                    targets.add(target)
            if len(targets) > 1:
                mistakes.append({
                    "round": round_num,
                    "player_id": None,
                    "role": Role.WEREWOLF.value,
                    "mistake": "split_votes",
                    "description": f"狼人投票分散，目标不一致: {', '.join(targets)}",
                    "severity": "high",
                })

    return mistakes


def _identify_mvp_players(logs: list[dict], players: list[dict], winner: str) -> list[str]:
    """识别MVP候选人"""
    player_scores = defaultdict(float)

    for player in players:
        player_id = player.get("id", "")
        role = player.get("role", "")
        team = ROLE_TEAM.get(Role(role), Team.GOOD).value if role else ""

        if not player_id:
            continue

        # 胜利阵营基础分
        if team == winner:
            player_scores[player_id] += 1.0

        # 存活加分
        if player.get("is_alive", False):
            player_scores[player_id] += 0.5

    # 根据关键行为加分
    for log in logs:
        player_id = log.get("player_id", "")
        action_type = log.get("action_type", "")

        if not player_id:
            continue

        if action_type == "witch_antidote":
            player_scores[player_id] += 0.8
        elif action_type == "guard_protect":
            player_scores[player_id] += 0.5
        elif action_type == "seer_check":
            player_scores[player_id] += 0.3
        elif action_type == "werewolf_kill_decision":
            player_scores[player_id] += 0.4

    # 排序取前3
    sorted_players = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)
    return [player_id for player_id, _ in sorted_players[:3]]


def _generate_attribution_summary(
    winner: str,
    key_decisions: list[dict],
    winning_factors: list[dict],
    losing_factors: list[dict],
    critical_mistakes: list[dict],
) -> str:
    """生成归因分析摘要"""
    winner_name = "好人阵营" if winner == "good" else "狼人阵营"

    summary_parts = [f"本局游戏由 {winner_name} 获胜。"]

    if winning_factors:
        top_factor = winning_factors[0]
        summary_parts.append(f"主要胜利因素: {top_factor['description']}。")

    if critical_mistakes:
        summary_parts.append(f"出现了 {len(critical_mistakes)} 个关键错误。")

    if key_decisions:
        summary_parts.append(f"共记录了 {len(key_decisions)} 个关键决策。")

    return " ".join(summary_parts)


def generate_game_summary(game_id: str, game_result: Optional[dict] = None,
                         logs: Optional[list[dict]] = None) -> dict[str, Any]:
    """
    生成综合游戏总结

    Args:
        game_id: 游戏ID
        game_result: 游戏结果（可选，如不提供则生成简化版）
        logs: 游戏日志（可选）

    Returns:
        dict: 游戏总结
    """
    if game_result is None:
        return {
            "game_id": game_id,
            "winner": "unknown",
            "round_count": 0,
            "duration_seconds": 0.0,
            "players": [],
            "timeline": [],
            "turning_points": [],
            "attribution": None,
            "statistics": {},
            "created_at": datetime.now().isoformat(),
        }

    winner = game_result.get("winner", "")
    players = game_result.get("players", [])
    round_count = game_result.get("round_count", 0)

    # 生成回放
    replay = reconstruct_game_replay(game_id, logs or [])

    # 识别转折点
    turning_points = identify_turning_points(logs or [])

    # 归因分析
    attribution = analyze_attribution(game_result, logs or [])

    # 玩家统计
    player_summaries = []
    for player in players:
        player_summaries.append({
            "player_id": player.get("id", ""),
            "name": player.get("name", ""),
            "role": player.get("role", ""),
            "role_name": ROLE_NAME_CN.get(Role(player.get("role", "")), ""),
            "team": ROLE_TEAM.get(Role(player.get("role", "")), Team.GOOD).value,
            "is_alive": player.get("is_alive", False),
            "is_winner": ROLE_TEAM.get(Role(player.get("role", "")), Team.GOOD).value == winner,
        })

    # 基础统计
    alive_good = sum(1 for p in players
                     if p.get("is_alive", False)
                     and ROLE_TEAM.get(Role(p.get("role", "")), Team.GOOD) == Team.GOOD)
    alive_evil = sum(1 for p in players
                     if p.get("is_alive", False)
                     and ROLE_TEAM.get(Role(p.get("role", "")), Team.GOOD) == Team.EVIL)

    statistics = {
        "total_players": len(players),
        "alive_good": alive_good,
        "alive_evil": alive_evil,
        "total_rounds": round_count,
        "total_events": replay.get("total_events", 0),
        "turning_points_count": len(turning_points),
        "key_decisions_count": len(attribution.get("key_decisions", [])),
    }

    return {
        "game_id": game_id,
        "winner": winner,
        "winner_name": "好人阵营" if winner == "good" else "狼人阵营",
        "round_count": round_count,
        "duration_seconds": game_result.get("game_duration_seconds", 0.0),
        "players": player_summaries,
        "timeline": replay.get("timeline", []),
        "turning_points": turning_points,
        "attribution": attribution,
        "statistics": statistics,
        "created_at": datetime.now().isoformat(),
    }
