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
from backend.database import get_game, get_game_logs, list_games, update_game_status
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