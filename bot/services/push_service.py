"""
Push Goal Service (ядро системы выбора цели сезона)
"""

import logging
from typing import List, Dict, Optional

from aiogram import Bot

from database import (
    get_all_members,
    get_push_goal,
    add_push_pending,
    set_push_goal,
    get_unregistered_members,
)
from config import ADMIN_NEWS_TARGETS
from utils.formatting import PUSH_GOAL_TEXT
from utils.keyboards import push_goal_keyboard
from utils.push_limiter import is_locked

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. РАССЫЛКА ГОЛОСОВАНИЯ
# ─────────────────────────────────────────────────────────────

async def launch_push_vote(bot: Bot) -> None:
    """
    Рассылает выбор цели сезона всем участникам.
    Незаполненных (unregistered) кладёт в pending.
    """

    members = await get_all_members()

    for m in members:
        user_id = m["user_id"]

        # не зарегистрирован → отложить
        if not m.get("registered"):
            await add_push_pending(user_id)
            continue

        try:
            await bot.send_message(
                user_id,
                PUSH_GOAL_TEXT,
                parse_mode="HTML",
                reply_markup=push_goal_keyboard(),
            )
        except Exception as e:
            logger.warning(f"Failed to send push goal to {user_id}: {e}")


# ─────────────────────────────────────────────────────────────
# 2. СОХРАНЕНИЕ ВЫБОРА
# ─────────────────────────────────────────────────────────────

async def save_push_goal(user_id: int, goal: str) -> bool:
    """
    Сохраняет цель пользователя.
    Возвращает True если сохранено, False если заблокировано.
    """

    existing = await get_push_goal(user_id)

    if existing and is_locked(existing["chosen_at"]):
        return False

    await set_push_goal(user_id, goal)
    return True


# ─────────────────────────────────────────────────────────────
# 3. ПОЛУЧЕНИЕ НЕОПРЕДЕЛИВШИХСЯ
# ─────────────────────────────────────────────────────────────

async def get_undecided_members() -> List[Dict]:
    """
    Возвращает всех зарегистрированных пользователей без выбора цели.
    """

    members = await get_all_members()
    result = []

    for m in members:
        if not m.get("registered"):
            continue

        goal = await get_push_goal(m["user_id"])
        if not goal:
            result.append(m)

    return result


# ─────────────────────────────────────────────────────────────
# 4. РАССЫЛКА НАПОМИНАНИЙ
# ─────────────────────────────────────────────────────────────

async def notify_undecided_users(bot: Bot) -> None:
    """
    Личное уведомление всем, кто не выбрал цель.
    """

    undecided = await get_undecided_members()

    for u in undecided:
        try:
            await bot.send_message(
                u["user_id"],
                "⏰ Напоминание: выбери цель сезона в боте!",
            )
        except Exception as e:
            logger.warning(f"Failed reminder to {u['user_id']}: {e}")


# ─────────────────────────────────────────────────────────────
# 5. РАССЫЛКА В НОВОСТИ КЛАНОВ
# ─────────────────────────────────────────────────────────────

async def notify_clan_news(bot: Bot) -> None:
    """
    Отправляет уведомление в news-топики всех кланов.
    """

    undecided = await get_undecided_members()

    mentions = []

    for u in undecided:
        username = u.get("username")
        if username:
            mentions.append(f"@{username}")

    text = (
        f"{' '.join(mentions) if mentions else 'Нет участников'}\n"
        "❗ Не выбрали цель сезона. Осталось 48 часов!"
    )

    for clan, data in ADMIN_NEWS_TARGETS.items():
        try:
            await bot.send_message(
                chat_id=data["chat_id"],
                message_thread_id=data["thread_id"],
                text=text,
            )
        except Exception as e:
            logger.warning(f"News notify failed for {clan}: {e}")


# ─────────────────────────────────────────────────────────────
# 6. УТИЛИТЫ (для handlers)
# ─────────────────────────────────────────────────────────────

async def user_can_change_goal(user_id: int) -> bool:
    """
    Проверка: может ли пользователь менять выбор.
    """
    goal = await get_push_goal(user_id)

    if not goal:
        return True

    return not is_locked(goal["chosen_at"])