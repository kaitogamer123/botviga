"""
Слой базы данных (SQLite через aiosqlite).
Все операции с данными — только здесь.
"""

import aiosqlite
import json
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "vigarik.db"


async def init_db() -> None:
    """Создаёт все таблицы если их нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            -- Участники (включая модерацию)
            CREATE TABLE IF NOT EXISTS members (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                last_name   TEXT,
                game_nick   TEXT,          -- ник в игре
                clan        TEXT,          -- academy / squad / events
                role        TEXT DEFAULT 'member',
                registered  INTEGER DEFAULT 0,  -- 1 = прошёл регистрацию
                joined_at   TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );

            -- Хранилище сообщений-предложений
            CREATE TABLE IF NOT EXISTS proposals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id     INTEGER NOT NULL,
                text        TEXT,
                media_json  TEXT,          -- JSON-список file_id фото/документов
                sent_at     TEXT DEFAULT (datetime('now')),
                status      TEXT DEFAULT 'pending'  -- pending / answered / rejected
            );

            -- Цели пуша на сезон
            CREATE TABLE IF NOT EXISTS push_goals (
                user_id     INTEGER PRIMARY KEY,
                goal        TEXT,          -- 'trophies' / 'league'
                chosen_at   TEXT DEFAULT (datetime('now')),
                season_id   TEXT DEFAULT 'current'
            );

            -- Очередь «нужно спросить цель пуша» (ещё не зарегались)
            CREATE TABLE IF NOT EXISTS push_pending (
                user_id     INTEGER PRIMARY KEY,
                season_id   TEXT DEFAULT 'current'
            );

            -- Сообщения списков в топиках (для редактирования)
            CREATE TABLE IF NOT EXISTS roster_messages (
                clan        TEXT PRIMARY KEY,
                message_id  INTEGER
            );
            """
        )
        await db.commit()


# ─── Members ──────────────────────────────────────────────────────────────────

async def get_member(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM members WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def upsert_member(
    user_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    game_nick: str = None,
    clan: str = None,
    role: str = None,
    registered: int = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await get_member(user_id)
        if not existing:
            await db.execute(
                """
                INSERT INTO members
                    (user_id, username, first_name, last_name, game_nick, clan, role, registered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    first_name,
                    last_name,
                    game_nick,
                    clan,
                    role or "member",
                    registered if registered is not None else 0,
                ),
            )
        else:
            fields, values = [], []
            for field, val in [
                ("username", username),
                ("first_name", first_name),
                ("last_name", last_name),
                ("game_nick", game_nick),
                ("clan", clan),
                ("role", role),
                ("registered", registered),
            ]:
                if val is not None:
                    fields.append(f"{field} = ?")
                    values.append(val)
            if fields:
                fields.append("updated_at = datetime('now')")
                values.append(user_id)
                await db.execute(
                    f"UPDATE members SET {', '.join(fields)} WHERE user_id = ?",
                    values,
                )
        await db.commit()


async def get_clan_members(clan: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM members WHERE clan = ? ORDER BY role, joined_at",
            (clan,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_members() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM members ORDER BY clan, role") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_unregistered_members(clan: str = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if clan:
            async with db.execute(
                "SELECT * FROM members WHERE registered = 0 AND clan = ?", (clan,)
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]
        async with db.execute(
            "SELECT * FROM members WHERE registered = 0"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def remove_member(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM members WHERE user_id = ?", (user_id,))
        await db.commit()


# ─── Proposals ────────────────────────────────────────────────────────────────

async def add_proposal(from_id: int, text: str, media: list) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO proposals (from_id, text, media_json) VALUES (?, ?, ?)",
            (from_id, text, json.dumps(media)),
        )
        await db.commit()
        return cur.lastrowid


async def get_proposals(status: str = "pending") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM proposals WHERE status = ? ORDER BY sent_at DESC",
            (status,),
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
            for r in rows:
                r["media_json"] = json.loads(r["media_json"] or "[]")
            return rows


async def get_proposal(proposal_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            r = dict(row)
            r["media_json"] = json.loads(r["media_json"] or "[]")
            return r


async def update_proposal_status(proposal_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE proposals SET status = ? WHERE id = ?", (status, proposal_id)
        )
        await db.commit()


# ─── Push goals ───────────────────────────────────────────────────────────────

async def set_push_goal(user_id: int, goal: str, season_id: str = "current") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO push_goals (user_id, goal, chosen_at, season_id)
            VALUES (?, ?, datetime('now'), ?)
            ON CONFLICT(user_id) DO UPDATE SET
                goal = excluded.goal,
                chosen_at = excluded.chosen_at,
                season_id = excluded.season_id
            """,
            (user_id, goal, season_id),
        )
        await db.commit()


async def get_push_goal(user_id: int, season_id: str = "current") -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM push_goals WHERE user_id = ? AND season_id = ?",
            (user_id, season_id),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_push_goals(season_id: str = "current") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM push_goals WHERE season_id = ?", (season_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_push_pending(user_id: int, season_id: str = "current") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO push_pending (user_id, season_id) VALUES (?, ?)",
            (user_id, season_id),
        )
        await db.commit()


async def remove_push_pending(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM push_pending WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_push_pending() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM push_pending") as cur:
            return [dict(r) for r in await cur.fetchall()]


# ─── Roster messages ──────────────────────────────────────────────────────────

async def save_roster_message_id(clan: str, message_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO roster_messages (clan, message_id) VALUES (?, ?)
            ON CONFLICT(clan) DO UPDATE SET message_id = excluded.message_id
            """,
            (clan, message_id),
        )
        await db.commit()


async def get_roster_message_id(clan: str) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id FROM roster_messages WHERE clan = ?", (clan,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None
