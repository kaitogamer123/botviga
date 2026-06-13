"""
Синхронизация списков участников с топиками чатов кланов.
"""

import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config import ROSTER_TOPICS
from database import get_clan_members, save_roster_message_id, get_roster_message_id
from utils.formatting import format_roster

logger = logging.getLogger(__name__)


async def sync_clan_roster(bot: Bot, clan: str) -> None:
    """
    Обновляет (или создаёт) сообщение со списком клана в нужном топике.
    """
    topic = ROSTER_TOPICS.get(clan)
    if not topic or not topic.get("thread_id"):
        logger.warning("Топик для клана %s не настроен — пропускаю синхронизацию", clan)
        return

    chat_id   = topic["chat_id"]
    thread_id = topic["thread_id"]

    members    = await get_clan_members(clan)
    text       = format_roster(clan, members)
    msg_id     = await get_roster_message_id(clan)

    try:
        if msg_id:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                message_thread_id=thread_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            raise ValueError("no message id")
    except (TelegramBadRequest, ValueError):
        # Сообщения нет — отправляем новое
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await save_roster_message_id(clan, msg.message_id)
        except TelegramBadRequest as e:
            logger.error("Не удалось отправить список клана %s: %s", clan, e)


async def sync_all_rosters(bot: Bot) -> None:
    for clan in ROSTER_TOPICS:
        await sync_clan_roster(bot, clan)
