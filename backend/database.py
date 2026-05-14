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

            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT DEFAULT '',
                role TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                survival_count INTEGER DEFAULT 0,
                action_accuracy REAL DEFAULT 0.0,
                speech_consistency REAL DEFAULT 0.0,
                avg_contribution REAL DEFAULT 0.0,
                total_correct_votes INTEGER DEFAULT 0,
                total_votes INTEGER DEFAULT 0,
                total_correct_checks INTEGER DEFAULT 0,
                total_checks INTEGER DEFAULT 0,
                total_correct_protects INTEGER DEFAULT 0,
                total_protects INTEGER DEFAULT 0,
                total_correct_kills INTEGER DEFAULT 0,
                total_kills INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                survival_rate REAL DEFAULT 0.0,
                vote_accuracy REAL DEFAULT 0.0,
                model_version TEXT DEFAULT 'default',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(player_id, role)
            );

            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT DEFAULT '',
                role TEXT,
                model_version TEXT DEFAULT 'default',
                win_rate REAL DEFAULT 0.0,
                survival_rate REAL DEFAULT 0.0,
                avg_contribution REAL DEFAULT 0.0,
                avg_vote_accuracy REAL DEFAULT 0.0,
                avg_action_accuracy REAL DEFAULT 0.0,
                games_count INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                total_score REAL DEFAULT 0.0,
                rank INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(player_id, role)
            );

            CREATE TABLE IF NOT EXISTS game_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL UNIQUE,
                winner TEXT,
                round_count INTEGER DEFAULT 0,
                turning_points_json TEXT,
                attribution_json TEXT,
                summary TEXT,
                player_metrics_json TEXT,
                team_metrics_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (game_id) REFERENCES games(id)
            );

            CREATE INDEX IF NOT EXISTS idx_game_logs_game_id
                ON game_logs(game_id);
            CREATE INDEX IF NOT EXISTS idx_game_logs_round
                ON game_logs(game_id, round_num);
            CREATE INDEX IF NOT EXISTS idx_player_stats_player_id
                ON player_stats(player_id);
            CREATE INDEX IF NOT EXISTS idx_player_stats_role
                ON player_stats(role);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_role
                ON leaderboard(role);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_score
                ON leaderboard(total_score DESC);
            CREATE INDEX IF NOT EXISTS idx_game_analysis_game_id
                ON game_analysis(game_id);
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


# ========== Player Stats ==========

async def update_player_stats(
    player_id: str,
    role: str,
    game_won: bool,
    survived: bool,
    contribution: float = 0.0,
    vote_accuracy: float = 0.0,
    action_accuracy: float = 0.0,
    speech_consistency: float = 0.0,
    player_name: str = "",
    model_version: str = "default",
) -> None:
    """
    更新玩家统计数据

    Args:
        player_id: 玩家ID
        role: 角色
        game_won: 是否获胜
        survived: 是否存活
        contribution: 贡献分
        vote_accuracy: 投票准确率
        action_accuracy: 行动准确率
        speech_consistency: 发言一致性
        player_name: 玩家名称
        model_version: 模型版本
    """
    db = await get_db()
    try:
        # 先查询是否存在
        cursor = await db.execute(
            "SELECT * FROM player_stats WHERE player_id = ? AND role = ?",
            (player_id, role),
        )
        row = await cursor.fetchone()

        now = datetime.now().isoformat()

        if row:
            # 更新现有记录
            old = dict(row)
            games_played = old["games_played"] + 1
            games_won = old["games_won"] + (1 if game_won else 0)
            survival_count = old["survival_count"] + (1 if survived else 0)

            # 加权平均更新
            old_games = old["games_played"]
            new_avg_contribution = round(
                (old["avg_contribution"] * old_games + contribution) / games_played, 4
            )
            new_action_accuracy = round(
                (old["action_accuracy"] * old_games + action_accuracy) / games_played, 4
            )
            new_speech_consistency = round(
                (old["speech_consistency"] * old_games + speech_consistency) / games_played, 4
            )

            win_rate = round(games_won / games_played, 4)
            survival_rate = round(survival_count / games_played, 4)

            await db.execute(
                """
                UPDATE player_stats SET
                    player_name = ?,
                    games_played = ?,
                    games_won = ?,
                    survival_count = ?,
                    action_accuracy = ?,
                    speech_consistency = ?,
                    avg_contribution = ?,
                    win_rate = ?,
                    survival_rate = ?,
                    model_version = ?,
                    updated_at = ?
                WHERE player_id = ? AND role = ?
                """,
                (
                    player_name or old.get("player_name", ""),
                    games_played,
                    games_won,
                    survival_count,
                    new_action_accuracy,
                    new_speech_consistency,
                    new_avg_contribution,
                    win_rate,
                    survival_rate,
                    model_version,
                    now,
                    player_id,
                    role,
                ),
            )
        else:
            # 插入新记录
            await db.execute(
                """
                INSERT INTO player_stats (
                    player_id, player_name, role, games_played, games_won,
                    survival_count, action_accuracy, speech_consistency,
                    avg_contribution, win_rate, survival_rate, model_version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player_id,
                    player_name,
                    role,
                    1,
                    1 if game_won else 0,
                    1 if survived else 0,
                    action_accuracy,
                    speech_consistency,
                    contribution,
                    1.0 if game_won else 0.0,
                    1.0 if survived else 0.0,
                    model_version,
                    now,
                    now,
                ),
            )

        await db.commit()
        logger.debug(f"玩家统计已更新: {player_id} ({role})")
    finally:
        await db.close()


async def get_player_stats(player_id: Optional[str] = None, role: Optional[str] = None) -> list[dict]:
    """
    获取玩家统计数据

    Args:
        player_id: 可选的玩家ID过滤
        role: 可选的角色过滤

    Returns:
        list: 玩家统计列表
    """
    db = await get_db()
    try:
        query = "SELECT * FROM player_stats WHERE 1=1"
        params = []

        if player_id:
            query += " AND player_id = ?"
            params.append(player_id)
        if role:
            query += " AND role = ?"
            params.append(role)

        query += " ORDER BY updated_at DESC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_role_stats() -> list[dict]:
    """获取各角色的综合统计数据"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT
                role,
                COUNT(*) as player_count,
                SUM(games_played) as total_games,
                SUM(games_won) as total_wins,
                ROUND(AVG(win_rate), 4) as avg_win_rate,
                ROUND(AVG(survival_rate), 4) as avg_survival_rate,
                ROUND(AVG(avg_contribution), 4) as avg_contribution,
                ROUND(AVG(action_accuracy), 4) as avg_action_accuracy
            FROM player_stats
            WHERE role IS NOT NULL
            GROUP BY role
            ORDER BY avg_win_rate DESC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# ========== Leaderboard ==========

async def update_leaderboard_db(
    player_id: str,
    role: str,
    player_name: str = "",
    model_version: str = "default",
    win_rate: float = 0.0,
    survival_rate: float = 0.0,
    avg_contribution: float = 0.0,
    avg_vote_accuracy: float = 0.0,
    avg_action_accuracy: float = 0.0,
    games_count: int = 0,
    wins: int = 0,
    total_score: float = 0.0,
) -> None:
    """
    更新排行榜数据库记录

    Args:
        player_id: 玩家ID
        role: 角色
        player_name: 玩家名称
        model_version: 模型版本
        win_rate: 胜率
        survival_rate: 生存率
        avg_contribution: 平均贡献分
        avg_vote_accuracy: 平均投票准确率
        avg_action_accuracy: 平均行动准确率
        games_count: 游戏场次
        wins: 胜利场次
        total_score: 综合评分
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM leaderboard WHERE player_id = ? AND role = ?",
            (player_id, role),
        )
        row = await cursor.fetchone()

        now = datetime.now().isoformat()

        if row:
            await db.execute(
                """
                UPDATE leaderboard SET
                    player_name = ?,
                    model_version = ?,
                    win_rate = ?,
                    survival_rate = ?,
                    avg_contribution = ?,
                    avg_vote_accuracy = ?,
                    avg_action_accuracy = ?,
                    games_count = ?,
                    wins = ?,
                    total_score = ?,
                    updated_at = ?
                WHERE player_id = ? AND role = ?
                """,
                (
                    player_name,
                    model_version,
                    win_rate,
                    survival_rate,
                    avg_contribution,
                    avg_vote_accuracy,
                    avg_action_accuracy,
                    games_count,
                    wins,
                    total_score,
                    now,
                    player_id,
                    role,
                ),
            )
        else:
            await db.execute(
                """
                INSERT INTO leaderboard (
                    player_id, player_name, role, model_version,
                    win_rate, survival_rate, avg_contribution,
                    avg_vote_accuracy, avg_action_accuracy,
                    games_count, wins, total_score, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player_id,
                    player_name,
                    role,
                    model_version,
                    win_rate,
                    survival_rate,
                    avg_contribution,
                    avg_vote_accuracy,
                    avg_action_accuracy,
                    games_count,
                    wins,
                    total_score,
                    now,
                ),
            )

        await db.commit()
        logger.debug(f"排行榜已更新: {player_id} ({role})")
    finally:
        await db.close()


async def get_leaderboard_db(
    role: Optional[str] = None,
    metric: str = "total_score",
    limit: int = 50,
    min_games: int = 1,
) -> list[dict]:
    """
    从数据库获取排行榜

    Args:
        role: 可选的角色过滤
        metric: 排序指标
        limit: 返回数量限制
        min_games: 最少游戏场次

    Returns:
        list: 排行榜条目列表
    """
    db = await get_db()
    try:
        valid_metrics = {
            "win_rate", "survival_rate", "avg_contribution",
            "avg_vote_accuracy", "avg_action_accuracy", "total_score", "games_count"
        }
        sort_column = metric if metric in valid_metrics else "total_score"

        query = f"""
            SELECT * FROM leaderboard
            WHERE games_count >= ?
        """
        params = [min_games]

        if role:
            query += " AND role = ?"
            params.append(role)

        query += f" ORDER BY {sort_column} DESC LIMIT ?"
        params.append(limit)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        result = []
        for i, row in enumerate(rows, 1):
            entry = dict(row)
            entry["rank"] = i
            result.append(entry)

        return result
    finally:
        await db.close()


async def get_leaderboard_by_player(player_id: str) -> list[dict]:
    """获取指定玩家的所有排行榜记录"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM leaderboard WHERE player_id = ? ORDER BY total_score DESC",
            (player_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# ========== Game Analysis ==========

async def save_game_analysis(
    game_id: str,
    winner: str = "",
    round_count: int = 0,
    turning_points: Optional[list] = None,
    attribution: Optional[dict] = None,
    summary: str = "",
    player_metrics: Optional[dict] = None,
    team_metrics: Optional[dict] = None,
) -> None:
    """
    保存游戏分析结果

    Args:
        game_id: 游戏ID
        winner: 获胜方
        round_count: 回合数
        turning_points: 转折点列表
        attribution: 归因分析结果
        summary: 总结文本
        player_metrics: 玩家指标
        team_metrics: 团队指标
    """
    db = await get_db()
    try:
        now = datetime.now().isoformat()

        await db.execute(
            """
            INSERT OR REPLACE INTO game_analysis (
                game_id, winner, round_count,
                turning_points_json, attribution_json, summary,
                player_metrics_json, team_metrics_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                winner,
                round_count,
                json.dumps(turning_points or [], ensure_ascii=False),
                json.dumps(attribution or {}, ensure_ascii=False),
                summary,
                json.dumps(player_metrics or {}, ensure_ascii=False),
                json.dumps(team_metrics or {}, ensure_ascii=False),
                now,
            ),
        )

        await db.commit()
        logger.info(f"游戏分析已保存: {game_id}")
    finally:
        await db.close()


async def get_game_analysis(game_id: str) -> Optional[dict]:
    """
    获取游戏分析结果

    Args:
        game_id: 游戏ID

    Returns:
        dict or None: 分析结果
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM game_analysis WHERE game_id = ?",
            (game_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        result = dict(row)
        # 解析JSON字段
        for field in ["turning_points_json", "attribution_json",
                      "player_metrics_json", "team_metrics_json"]:
            if result.get(field):
                try:
                    result[field.replace("_json", "")] = json.loads(result[field])
                except json.JSONDecodeError:
                    result[field.replace("_json", "")] = {}
                del result[field]

        return result
    finally:
        await db.close()


async def list_game_analysis(limit: int = 20) -> list[dict]:
    """列出最近的游戏分析"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM game_analysis ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            entry = dict(row)
            for field in ["turning_points_json", "attribution_json",
                          "player_metrics_json", "team_metrics_json"]:
                if entry.get(field):
                    try:
                        entry[field.replace("_json", "")] = json.loads(entry[field])
                    except json.JSONDecodeError:
                        entry[field.replace("_json", "")] = {}
                    del entry[field]
            result.append(entry)

        return result
    finally:
        await db.close()
