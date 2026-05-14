"""
FastAPI服务器 - REST API + WebSocket
管理游戏生命周期、人类玩家交互、实时状态推送
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.agents.guard_agent import GuardAgent
from backend.agents.hunter_agent import HunterAgent
from backend.agents.llm_client import get_llm_client
from backend.agents.seer_agent import SeerAgent
from backend.agents.villager_agent import VillagerAgent
from backend.agents.werewolf_agent import WerewolfAgent
from backend.agents.witch_agent import WitchAgent
from backend.config import config
from backend.database import create_game as db_create_game
from backend.database import (
    get_game,
    get_game_analysis,
    get_game_logs,
    get_leaderboard_db,
    get_player_stats,
    get_role_stats,
    list_game_analysis,
    list_games,
    save_game_analysis,
    update_game_status,
    update_leaderboard_db,
    update_player_stats,
)
from backend.evaluation.leaderboard import (
    get_agent_comparison,
    get_leaderboard,
    merge_leaderboard_entries,
    update_leaderboard_entry,
)
from backend.evaluation.metrics import (
    calculate_action_accuracy,
    calculate_comprehensive_metrics,
    calculate_role_win_rate,
    calculate_speech_consistency,
    calculate_survival_rate,
    calculate_team_contribution,
)
from backend.evaluation.replay import (
    analyze_attribution,
    generate_game_summary,
    identify_turning_points,
    reconstruct_game_replay,
)
from backend.game_engine.engine import GameEngine
from backend.game_engine.roles import ROLE_NAME_CN, Phase, Role

logger = logging.getLogger(__name__)

# ========== FastAPI App ==========

app = FastAPI(
    title="Werewolf Game Server",
    description="狼人杀多智能体游戏系统后端",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Pydantic Models ==========

class PlayerConfig(BaseModel):
    id: str
    name: str
    is_human: bool = False
    seat: Optional[int] = None


class CreateGameRequest(BaseModel):
    players: list[PlayerConfig] = Field(
        default_factory=lambda: [
            PlayerConfig(id=f"p{i}", name=f"玩家{i}", is_human=False)
            for i in range(1, 13)
        ]
    )
    auto_play: bool = True  # 是否自动运行（纯AI对战）
    speed: float = 0.5  # 自动运行时的阶段间延迟（秒）


class HumanAction(BaseModel):
    player_id: str
    action_type: str
    target: Optional[str] = None
    speech: Optional[str] = None
    use_antidote: Optional[bool] = None
    use_poison: Optional[bool] = None
    poison_target: Optional[str] = None


class JoinGameRequest(BaseModel):
    seat: int  # 要替换的座位号（1-12）
    name: str


# ========== Game Manager ==========

class GameManager:
    """管理所有活跃游戏"""

    def __init__(self):
        self.games: dict[str, GameEngine] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.ws_connections: dict[str, list[WebSocket]] = {}  # game_id -> [ws, ...]
        self.llm_client = get_llm_client()

    def agent_factory(self, player_id: str, player_name: str, role: Role) -> BaseAgent:
        """创建AI代理"""
        # 获取对应的引擎状态引用
        # 我们使用闭包来获取状态
        agent_classes = {
            Role.WEREWOLF: WerewolfAgent,
            Role.SEER: SeerAgent,
            Role.WITCH: WitchAgent,
            Role.HUNTER: HunterAgent,
            Role.GUARD: GuardAgent,
            Role.VILLAGER: VillagerAgent,
        }
        agent_cls = agent_classes.get(role, VillagerAgent)
        return agent_cls(
            player_id=player_id,
            player_name=player_name,
            role=role,
            game_state_ref=None,  # 将在引擎中设置
            llm_client=self.llm_client,
        )

    async def broadcast(self, game_id: str, message: dict) -> None:
        """向游戏的所有WebSocket连接广播消息"""
        connections = self.ws_connections.get(game_id, [])
        dead_connections = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)

        for ws in dead_connections:
            if ws in connections:
                connections.remove(ws)

    async def cleanup_game(self, game_id: str) -> None:
        """清理已结束的游戏"""
        if game_id in self.tasks:
            task = self.tasks.pop(game_id)
            if not task.done():
                task.cancel()
        if game_id in self.games:
            self.games.pop(game_id, None)
        # 保持WebSocket连接存活一段时间后关闭
        await asyncio.sleep(30)
        old_connections = self.ws_connections.pop(game_id, [])
        for ws in old_connections:
            try:
                await ws.close()
            except Exception:
                pass


# 全局游戏管理器
game_manager = GameManager()


# ========== Evaluation Helper ==========

async def _process_game_evaluation(game_id: str, engine: GameEngine) -> None:
    """
    游戏结束后自动处理评估流程
    1. 计算指标
    2. 更新玩家统计
    3. 更新排行榜
    4. 生成并保存游戏分析
    """
    try:
        logs = await get_game_logs(game_id)
        db_game = await get_game(game_id)

        if not db_game:
            logger.warning(f"游戏 {game_id} 未找到，跳过评估")
            return

        players_config = json.loads(db_game.get("players_config", "[]"))
        winner = engine.state.winner or db_game.get("winner", "")
        round_count = engine.state.round_number

        # 构建游戏结果字典
        game_result = {
            "game_id": game_id,
            "winner": winner,
            "round_count": round_count,
            "players": [],
            "logs": logs,
        }

        for player in engine.state.players:
            game_result["players"].append({
                "id": player.id,
                "name": player.name,
                "role": player.role.value,
                "is_alive": player.is_alive,
                "team": player.team.value,
            })

        # 1. 计算综合指标
        comprehensive = calculate_comprehensive_metrics(game_result, logs, players_config)
        player_metrics = comprehensive.get("player_metrics", {})

        # 2. 计算各项具体指标
        action_accuracy = calculate_action_accuracy(logs, players_config)
        speech_consistency = calculate_speech_consistency(logs)
        contribution_scores = calculate_team_contribution(game_result)

        # 3. 更新每个玩家的统计和排行榜
        for player in engine.state.players:
            player_id = player.id
            role = player.role
            role_str = role.value
            team = player.team.value
            is_winner = team == winner
            survived = player.is_alive
            player_name = player.name

            # 获取该玩家的指标
            p_metrics = player_metrics.get(player_id, {})
            p_action = action_accuracy.get(player_id, {})
            p_speech = speech_consistency.get(player_id, 0.5)
            p_contribution = contribution_scores.get(player_id, 0.5)

            vote_acc = p_action.get("vote_accuracy", 0.0)
            action_acc = (
                p_action.get("check_accuracy", 0.0) or
                p_action.get("protect_accuracy", 0.0) or
                p_action.get("kill_accuracy", 0.0) or
                vote_acc
            )

            # 更新玩家统计
            await update_player_stats(
                player_id=player_id,
                role=role_str,
                game_won=is_winner,
                survived=survived,
                contribution=p_contribution,
                vote_accuracy=vote_acc,
                action_accuracy=action_acc,
                speech_consistency=p_speech,
                player_name=player_name,
            )

            # 更新排行榜
            lb_entry = update_leaderboard_entry(
                player_id=player_id,
                role=role,
                game_result=game_result,
                metrics={
                    "contribution_score": p_contribution,
                    "vote_accuracy": vote_acc,
                    "survived": survived,
                },
                player_name=player_name,
            )

            # 获取现有排行榜记录并合并
            existing_lb = await get_leaderboard_db(role=role_str, limit=1, min_games=0)
            existing = None
            for e in existing_lb:
                if e.get("player_id") == player_id:
                    existing = e
                    break

            if existing:
                merged = merge_leaderboard_entries(existing, lb_entry)
                await update_leaderboard_db(
                    player_id=player_id,
                    role=role_str,
                    player_name=player_name,
                    win_rate=merged["win_rate"],
                    survival_rate=merged["survival_rate"],
                    avg_contribution=merged["avg_contribution"],
                    avg_vote_accuracy=merged["avg_vote_accuracy"],
                    avg_action_accuracy=merged["avg_action_accuracy"],
                    games_count=merged["games_count"],
                    wins=merged["wins"],
                    total_score=merged["total_score"],
                )
            else:
                await update_leaderboard_db(
                    player_id=player_id,
                    role=role_str,
                    player_name=player_name,
                    win_rate=lb_entry["win_rate"],
                    survival_rate=lb_entry["survival_rate"],
                    avg_contribution=lb_entry["avg_contribution"],
                    avg_vote_accuracy=lb_entry["avg_vote_accuracy"],
                    avg_action_accuracy=lb_entry["avg_action_accuracy"],
                    games_count=lb_entry["games_count"],
                    wins=lb_entry["wins"],
                    total_score=lb_entry["total_score"],
                )

        # 4. 生成并保存游戏分析
        turning_points = identify_turning_points(logs)
        attribution = analyze_attribution(game_result, logs)
        summary = generate_game_summary(game_id, game_result, logs)

        await save_game_analysis(
            game_id=game_id,
            winner=winner,
            round_count=round_count,
            turning_points=turning_points,
            attribution=attribution,
            summary=attribution.get("analysis_summary", ""),
            player_metrics=player_metrics,
            team_metrics=comprehensive.get("team_metrics", {}),
        )

        logger.info(f"游戏 {game_id} 评估完成")

    except Exception as e:
        logger.exception(f"游戏评估失败: {e}")


# ========== REST Endpoints ==========

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "active_games": len(game_manager.games),
    }


@app.post("/api/games")
async def create_game(request: CreateGameRequest):
    """创建新游戏"""
    if len(request.players) != 12:
        raise HTTPException(status_code=400, detail="必须恰好12名玩家")

    game_id = str(uuid.uuid4())[:8]

    # 持久化
    players_config = [p.model_dump() for p in request.players]
    await db_create_game(game_id, players_config)
    await update_game_status(game_id, status="created")

    return {
        "game_id": game_id,
        "players": players_config,
        "auto_play": request.auto_play,
        "speed": request.speed,
    }


@app.get("/api/games")
async def list_all_games():
    """列出所有游戏"""
    games = await list_games(limit=50)
    return {
        "games": games,
        "active_games": list(game_manager.games.keys()),
    }


@app.get("/api/games/{game_id}")
async def get_game_info(game_id: str, player_id: Optional[str] = None):
    """获取游戏信息"""
    db_game = await get_game(game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    engine = game_manager.games.get(game_id)
    if engine and hasattr(engine, 'state'):
        state_data = engine.state.get_public_state(player_id) if player_id else engine.state.to_dict()
        return {
            "game": db_game,
            "state": state_data,
        }
    return {"game": db_game, "state": None}


@app.get("/api/games/{game_id}/logs")
async def get_game_logs_endpoint(game_id: str, limit: int = 500):
    """获取游戏日志"""
    logs = await get_game_logs(game_id, limit=limit)
    return {"logs": logs}


@app.post("/api/games/{game_id}/join")
async def join_game(game_id: str, request: JoinGameRequest):
    """人类玩家加入游戏（替换AI位置）"""
    db_game = await get_game(game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    if db_game.get("status") != "created":
        raise HTTPException(status_code=400, detail="游戏已开始，无法加入")

    players_config = json.loads(db_game["players_config"])
    if request.seat < 1 or request.seat > 12:
        raise HTTPException(status_code=400, detail="座位号必须在1-12之间")

    target = players_config[request.seat - 1]
    if target["is_human"]:
        raise HTTPException(status_code=400, detail="该座位已被人类玩家占用")

    target["is_human"] = True
    target["name"] = request.name

    # 更新持久化
    await update_game_status(game_id, status="created",
                             game_state=json.dumps(players_config, ensure_ascii=False))

    return {"message": f"成功加入游戏，座位{request.seat}", "player": target}


@app.post("/api/games/{game_id}/start")
async def start_game(game_id: str, auto_play: bool = True, speed: float = 0.5):
    """启动游戏"""
    db_game = await get_game(game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    if db_game.get("status") not in ("created",):
        raise HTTPException(status_code=400, detail="游戏状态不允许启动")

    players_config = json.loads(db_game["players_config"])

    # 检查是否所有玩家都是AI（auto_play模式）
    human_players = [p for p in players_config if p.get("is_human")]

    # 创建引擎和代理
    async def _create_agent(player_id: str, player_name: str, role: Role) -> BaseAgent:
        agent_classes = {
            Role.WEREWOLF: WerewolfAgent,
            Role.SEER: SeerAgent,
            Role.WITCH: WitchAgent,
            Role.HUNTER: HunterAgent,
            Role.GUARD: GuardAgent,
            Role.VILLAGER: VillagerAgent,
        }
        agent_cls = agent_classes.get(role, VillagerAgent)
        # engine.state会在start_game时赋值
        engine = game_manager.games.get(game_id)
        state_ref = engine.state if engine else None
        return agent_cls(
            player_id=player_id,
            player_name=player_name,
            role=role,
            game_state_ref=state_ref,
            llm_client=game_manager.llm_client,
        )

    # 创建回调
    async def on_state_update(state):
        await game_manager.broadcast(game_id, {
            "type": "state_update",
            "data": state.to_dict(),
        })

    async def on_phase_change(phase, round_num, state):
        await game_manager.broadcast(game_id, {
            "type": "phase_change",
            "data": {
                "phase": phase,
                "round_number": round_num,
            },
        })

    async def on_log(log_entry):
        await game_manager.broadcast(game_id, {
            "type": "log",
            "data": log_entry,
        })

    async def on_human_action_required(player_id, action_type, state):
        await game_manager.broadcast(game_id, {
            "type": "your_turn",
            "data": {
                "player_id": player_id,
                "action_type": action_type,
                "state": state.get_public_state(player_id),
            },
        })

    engine = GameEngine(
        game_id=game_id,
        player_configs=players_config,
        agent_factory=_create_agent,
        callbacks={
            "on_state_update": on_state_update,
            "on_phase_change": on_phase_change,
            "on_log": on_log,
            "on_human_action_required": on_human_action_required,
        },
    )

    game_manager.games[game_id] = engine

    # 初始化并开始游戏
    await engine.start_game()
    await update_game_status(game_id, status="running", round_number=0,
                             current_phase=Phase.SETUP.value)

    # 如果有纯AI玩家，启动游戏循环
    if auto_play or len(human_players) == 0:
        async def run_game():
            try:
                while not engine.state.game_over:
                    await engine.process_next_phase()
                    await asyncio.sleep(speed)
                    # 检查是否需要等待人类玩家
                    if engine.state.waiting_for_player:
                        await asyncio.sleep(1.0)
                        continue
                # 游戏结束
                await game_manager.broadcast(game_id, {
                    "type": "game_over",
                    "data": {
                        "winner": engine.state.winner,
                        "state": engine.state.to_dict(),
                    },
                })

                # 自动执行评估流程
                await _process_game_evaluation(game_id, engine)

                await asyncio.sleep(5)
                await game_manager.cleanup_game(game_id)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.exception(f"游戏循环异常: {e}")

        task = asyncio.create_task(run_game())
        game_manager.tasks[game_id] = task
    else:
        # 人类玩家模式，启动逐步处理的任务
        async def run_human_game():
            try:
                # 先处理setup
                await engine.process_next_phase()  # 进入NIGHT_GUARD
                while not engine.state.game_over:
                    if engine.state.waiting_for_player:
                        await asyncio.sleep(0.5)
                        continue
                    await engine.process_next_phase()
                    await asyncio.sleep(speed)

                await game_manager.broadcast(game_id, {
                    "type": "game_over",
                    "data": {
                        "winner": engine.state.winner,
                        "state": engine.state.to_dict(),
                    },
                })

                # 自动执行评估流程
                await _process_game_evaluation(game_id, engine)

                await asyncio.sleep(15)
                await game_manager.cleanup_game(game_id)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.exception(f"人类游戏循环异常: {e}")

        task = asyncio.create_task(run_human_game())
        game_manager.tasks[game_id] = task

    return {
        "message": "游戏已启动",
        "game_id": game_id,
        "auto_play": auto_play or len(human_players) == 0,
        "human_players": [p for p in players_config if p.get("is_human")],
    }


@app.post("/api/games/{game_id}/action")
async def submit_action(game_id: str, action: HumanAction):
    """提交人类玩家操作"""
    engine = game_manager.games.get(game_id)
    if not engine:
        raise HTTPException(status_code=404, detail="游戏不存在或已结束")

    if not engine.state.waiting_for_player:
        raise HTTPException(status_code=400, detail="当前不需要玩家操作")

    if engine.state.waiting_for_player != action.player_id:
        raise HTTPException(status_code=400, detail="不是该玩家的操作回合")

    # 构建操作字典
    action_dict = {}
    if action.target:
        action_dict["target"] = action.target
    if action.speech:
        action_dict["speech"] = action.speech
    if action.use_antidote is not None:
        action_dict["use_antidote"] = action.use_antidote
    if action.use_poison is not None:
        action_dict["use_poison"] = action.use_poison
    if action.poison_target:
        action_dict["poison_target"] = action.poison_target
    if action.action_type:
        action_dict["action_type"] = action.action_type

    success = await engine.submit_human_action(action.player_id, action_dict)
    if not success:
        raise HTTPException(status_code=400, detail="操作提交失败")

    return {"message": "操作已提交", "player_id": action.player_id}


# ========== Evaluation Endpoints ==========

@app.get("/api/evaluation/games/{game_id}/replay")
async def get_game_replay(game_id: str):
    """获取游戏回放与分析"""
    db_game = await get_game(game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    logs = await get_game_logs(game_id)
    replay = reconstruct_game_replay(game_id, logs)

    return {
        "game_id": game_id,
        "status": db_game.get("status"),
        "winner": db_game.get("winner"),
        "replay": replay,
    }


@app.get("/api/evaluation/games/{game_id}/attribution")
async def get_game_attribution(game_id: str):
    """获取归因分析"""
    # 先尝试从数据库获取已保存的分析
    analysis = await get_game_analysis(game_id)
    if analysis and analysis.get("attribution"):
        return {
            "game_id": game_id,
            "attribution": analysis["attribution"],
        }

    # 实时计算
    db_game = await get_game(game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    logs = await get_game_logs(game_id)
    players_config = json.loads(db_game.get("players_config", "[]"))

    game_result = {
        "game_id": game_id,
        "winner": db_game.get("winner", ""),
        "round_count": db_game.get("round_number", 0),
        "players": players_config,
        "logs": logs,
    }

    attribution = analyze_attribution(game_result, logs)
    return {
        "game_id": game_id,
        "attribution": attribution,
    }


@app.get("/api/evaluation/games/{game_id}/summary")
async def get_game_summary_endpoint(game_id: str):
    """获取游戏总结"""
    # 先尝试从数据库获取
    analysis = await get_game_analysis(game_id)
    if analysis:
        return {
            "game_id": game_id,
            "summary": analysis,
        }

    # 实时生成
    db_game = await get_game(game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    logs = await get_game_logs(game_id)
    players_config = json.loads(db_game.get("players_config", "[]"))

    game_result = {
        "game_id": game_id,
        "winner": db_game.get("winner", ""),
        "round_count": db_game.get("round_number", 0),
        "players": players_config,
        "logs": logs,
    }

    summary = generate_game_summary(game_id, game_result, logs)
    return {
        "game_id": game_id,
        "summary": summary,
    }


# ========== Leaderboard Endpoints ==========

@app.get("/api/leaderboard")
async def get_overall_leaderboard(
    role: Optional[str] = None,
    metric: str = "total_score",
    limit: int = 50,
    min_games: int = 1,
):
    """获取总排行榜"""
    entries = await get_leaderboard_db(
        role=role,
        metric=metric,
        limit=limit,
        min_games=min_games,
    )
    return {
        "leaderboard": entries,
        "count": len(entries),
        "role": role,
        "metric": metric,
    }


@app.get("/api/leaderboard/role/{role}")
async def get_role_leaderboard_endpoint(
    role: str,
    metric: str = "total_score",
    limit: int = 20,
    min_games: int = 1,
):
    """获取角色特定排行榜"""
    try:
        role_enum = Role(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效角色: {role}")

    entries = await get_leaderboard_db(
        role=role,
        metric=metric,
        limit=limit,
        min_games=min_games,
    )
    return {
        "role": role,
        "role_name": ROLE_NAME_CN.get(role_enum, ""),
        "leaderboard": entries,
        "count": len(entries),
        "metric": metric,
    }


@app.get("/api/leaderboard/agents/compare")
async def compare_agents(agent_ids: str):
    """比较多个agent的表现"""
    if not agent_ids:
        raise HTTPException(status_code=400, detail="请提供agent_ids参数")

    ids = [a.strip() for a in agent_ids.split(",") if a.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个agent进行比较")

    # 获取所有相关排行榜数据
    all_entries = []
    for agent_id in ids:
        entries = await get_leaderboard_by_player(agent_id)
        all_entries.extend(entries)

    comparison = get_agent_comparison(all_entries, ids)
    return comparison


# ========== Stats Endpoints ==========

@app.get("/api/stats/players/{player_id}")
async def get_player_statistics(player_id: str):
    """获取玩家统计"""
    stats = await get_player_stats(player_id=player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="未找到该玩家的统计数据")

    # 计算总体统计
    total_games = sum(s.get("games_played", 0) for s in stats)
    total_wins = sum(s.get("games_won", 0) for s in stats)
    total_survival = sum(s.get("survival_count", 0) for s in stats)

    return {
        "player_id": player_id,
        "total_games": total_games,
        "total_wins": total_wins,
        "overall_win_rate": round(total_wins / total_games, 4) if total_games > 0 else 0.0,
        "overall_survival_rate": round(total_survival / total_games, 4) if total_games > 0 else 0.0,
        "role_stats": stats,
    }


@app.get("/api/stats/roles")
async def get_role_statistics():
    """获取角色统计"""
    stats = await get_role_stats()
    return {
        "roles": stats,
        "count": len(stats),
    }


@app.get("/api/stats/overview")
async def get_statistics_overview():
    """获取统计概览"""
    games = await list_games(limit=1000)
    finished_games = [g for g in games if g.get("status") == "finished"]

    # 角色胜率统计
    game_results = []
    for game in finished_games:
        try:
            players_config = json.loads(game.get("players_config", "[]"))
            game_results.append({
                "winner": game.get("winner", ""),
                "players": players_config,
                "round_count": game.get("round_number", 0),
            })
        except json.JSONDecodeError:
            continue

    role_win_rates = calculate_role_win_rate(game_results)

    # 好人/狼人总体胜率
    good_wins = sum(1 for g in game_results if g.get("winner") == "good")
    evil_wins = sum(1 for g in game_results if g.get("winner") == "evil")
    total_finished = len(game_results)

    return {
        "total_games": len(games),
        "finished_games": total_finished,
        "good_wins": good_wins,
        "evil_wins": evil_wins,
        "good_win_rate": round(good_wins / total_finished, 4) if total_finished > 0 else 0.0,
        "evil_win_rate": round(evil_wins / total_finished, 4) if total_finished > 0 else 0.0,
        "role_win_rates": role_win_rates,
    }


# ========== WebSocket ==========

@app.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    player_id: Optional[str] = Query(default=None),
):
    """WebSocket连接 - 用于实时游戏通信"""
    await websocket.accept()

    # 注册连接
    if game_id not in game_manager.ws_connections:
        game_manager.ws_connections[game_id] = []
    game_manager.ws_connections[game_id].append(websocket)

    logger.info(f"WebSocket连接: game={game_id}, player={player_id}")

    try:
        # 发送当前游戏状态
        engine = game_manager.games.get(game_id)
        if engine and hasattr(engine, 'state'):
            state_data = engine.state.get_public_state(player_id) if player_id else engine.state._get_spectator_state()
            await websocket.send_json({
                "type": "connected",
                "data": {
                    "game_id": game_id,
                    "player_id": player_id,
                    "state": state_data,
                },
            })

        # 接收人类玩家操作
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "action" and player_id:
                engine = game_manager.games.get(game_id)
                if engine:
                    action_data = data.get("data", {})
                    await engine.submit_human_action(player_id, action_data)
                    await websocket.send_json({
                        "type": "action_received",
                        "data": {"status": "ok"},
                    })

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: game={game_id}, player={player_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        connections = game_manager.ws_connections.get(game_id, [])
        if websocket in connections:
            connections.remove(websocket)


# ========== Startup ==========

@app.on_event("startup")
async def startup_event():
    """服务器启动事件"""
    logger.info(f"服务器启动于 {config.HOST}:{config.PORT}")
    logger.info(f"LLM模型: {config.LLM_MODEL}")


@app.on_event("shutdown")
async def shutdown_event():
    """服务器关闭事件"""
    logger.info("服务器关闭中...")
    # 停止所有活跃游戏
    for game_id, engine in list(game_manager.games.items()):
        engine.stop()
    for task in list(game_manager.tasks.values()):
        task.cancel()
    logger.info("服务器已关闭")
