"""
数据库模块 - 使用 aiosqlite 进行异步 SQLite 操作
存储游戏记录和日志
"""
import json
import logging
from datetime import datetime
from typing import Optional

import aiosqlite

from backend.config import config

logger = logging.getLogger(__name__)


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接"""
    db = await aiosqlite.connect(config.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """初始化数据库表结构"""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                players_config TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'created',
                winner TEXT,
                current_phase TEXT,
                round_number INTEGER DEFAULT 0,
                game_state TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS game_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                round_num INTEGER NOT NULL,
                phase TEXT NOT NULL,
                player_id TEXT,
                role TEXT,
                action_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (game_id) REFERENCES games(id)
            );

            CREATE INDEX IF NOT EXISTS idx_game_logs_game_id
                ON game_logs(game_id);
            CREATE INDEX IF NOT EXISTS idx_game_logs_round
                ON game_logs(game_id, round_num);
        """)
        await db.commit()
        logger.info("数据库初始化完成")
    finally:
        await db.close()


async def create_game(
    game_id: str,
    players_config: list[dict],
) -> str:
    """创建新游戏记录"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO games (id, players_config, status) VALUES (?, ?, ?)",
            (game_id, json.dumps(players_config, ensure_ascii=False), "created"),
        )
        await db.commit()
        logger.info(f"游戏 {game_id} 创建成功")
        return game_id
    finally:
        await db.close()


async def update_game_status(
    game_id: str,
    status: str,
    winner: Optional[str] = None,
    current_phase: Optional[str] = None,
    round_number: Optional[int] = None,
    game_state: Optional[str] = None,
    ended_at: Optional[str] = None,
) -> None:
    """更新游戏状态"""
    db = await get_db()
    try:
        updates = ["status = ?"]
        params: list = [status]

        if winner is not None:
            updates.append("winner = ?")
            params.append(winner)
        if current_phase is not None:
            updates.append("current_phase = ?")
            params.append(current_phase)
        if round_number is not None:
            updates.append("round_number = ?")
            params.append(round_number)
        if game_state is not None:
            updates.append("game_state = ?")
            params.append(game_state)
        if ended_at is not None:
            updates.append("ended_at = ?")
            params.append(ended_at)

        params.append(game_id)
        query = f"UPDATE games SET {', '.join(updates)} WHERE id = ?"
        await db.execute(query, params)
        await db.commit()
    finally:
        await db.close()


async def add_log(
    game_id: str,
    round_num: int,
    phase: str,
    action_type: str,
    content: str,
    player_id: Optional[str] = None,
    role: Optional[str] = None,
) -> None:
    """添加游戏日志"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO game_logs (game_id, round_num, phase, player_id, role, action_type, content) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (game_id, round_num, phase, player_id, role, action_type, content),
        )
        await db.commit()
    finally:
        await db.close()


async def get_game(game_id: str) -> Optional[dict]:
    """获取游戏信息"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await db.close()


async def list_games(limit: int = 20) -> list[dict]:
    """列出最近的游戏"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM games ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_game_logs(game_id: str, limit: int = 500) -> list[dict]:
    """获取游戏日志"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM game_logs WHERE game_id = ? ORDER BY id ASC LIMIT ?",
            (game_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()