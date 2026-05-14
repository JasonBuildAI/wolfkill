"""
Pydantic models for evaluation data
评估数据模型定义
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.game_engine.roles import Role


class PlayerStats(BaseModel):
    """玩家统计信息"""
    player_id: str
    player_name: str = ""
    role: str = ""
    games_played: int = 0
    games_won: int = 0
    survival_count: int = 0
    action_accuracy: float = 0.0
    speech_consistency: float = 0.0
    avg_contribution: float = 0.0
    total_correct_votes: int = 0
    total_votes: int = 0
    total_correct_checks: int = 0
    total_checks: int = 0
    total_correct_protects: int = 0
    total_protects: int = 0
    total_correct_kills: int = 0
    total_kills: int = 0
    win_rate: float = 0.0
    survival_rate: float = 0.0
    vote_accuracy: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GameMetrics(BaseModel):
    """单局游戏指标"""
    game_id: str
    winner: str = ""
    round_count: int = 0
    game_duration_seconds: float = 0.0
    player_metrics: dict[str, PlayerGameMetrics] = Field(default_factory=dict)
    team_metrics: dict[str, TeamMetrics] = Field(default_factory=dict)
    key_events: list[dict] = Field(default_factory=list)
    created_at: Optional[str] = None


class PlayerGameMetrics(BaseModel):
    """单局游戏中单个玩家的指标"""
    player_id: str
    player_name: str = ""
    role: str = ""
    team: str = ""
    is_winner: bool = False
    survived: bool = False
    death_round: Optional[int] = None
    death_cause: Optional[str] = None  # "werewolf_kill", "vote", "poison", "hunter_shot"
    actions: list[dict] = Field(default_factory=list)
    speeches: list[dict] = Field(default_factory=list)
    votes_cast: list[dict] = Field(default_factory=list)
    vote_accuracy: float = 0.0  # 投票正确率（投给敌方）
    check_accuracy: float = 0.0  # 预言家查验正确率
    protect_accuracy: float = 0.0  # 守卫守护正确率
    kill_accuracy: float = 0.0  # 狼人击杀正确率（击杀神职/关键角色）
    contribution_score: float = 0.0  # 团队贡献分
    speech_consistency_score: float = 0.0  # 发言一致性


class TeamMetrics(BaseModel):
    """团队指标"""
    team: str = ""  # "good" or "evil"
    players: list[str] = Field(default_factory=list)
    total_players: int = 0
    alive_at_end: int = 0
    won: bool = False
    night_kills: int = 0
    vote_kills: int = 0
    poison_kills: int = 0
    saved_count: int = 0
    correct_checks: int = 0


class LeaderboardEntry(BaseModel):
    """排行榜条目"""
    id: Optional[int] = None
    player_id: str
    player_name: str = ""
    role: Optional[str] = None
    model_version: str = "default"
    games_count: int = 0
    wins: int = 0
    win_rate: float = 0.0
    survival_rate: float = 0.0
    avg_contribution: float = 0.0
    avg_vote_accuracy: float = 0.0
    avg_action_accuracy: float = 0.0
    rank: int = 0
    score: float = 0.0  # 综合评分
    updated_at: Optional[str] = None


class ReplayEvent(BaseModel):
    """回放事件"""
    event_id: str
    game_id: str
    round_num: int
    phase: str
    timestamp: str
    event_type: str  # "action", "speech", "vote", "death", "phase_change", "system"
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    role: Optional[str] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    target_role: Optional[str] = None
    content: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    significance: float = 0.0  # 重要性评分 0-1
    is_turning_point: bool = False


class AttributionResult(BaseModel):
    """归因分析结果"""
    game_id: str
    winner: str = ""
    key_decisions: list[dict] = Field(default_factory=list)
    winning_factors: list[dict] = Field(default_factory=list)
    losing_factors: list[dict] = Field(default_factory=list)
    critical_mistakes: list[dict] = Field(default_factory=list)
    mvp_players: list[str] = Field(default_factory=list)
    analysis_summary: str = ""
    created_at: Optional[str] = None


class GameSummary(BaseModel):
    """游戏总结"""
    game_id: str
    winner: str = ""
    round_count: int = 0
    duration_seconds: float = 0.0
    players: list[dict] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)
    turning_points: list[dict] = Field(default_factory=list)
    attribution: Optional[AttributionResult] = None
    statistics: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
