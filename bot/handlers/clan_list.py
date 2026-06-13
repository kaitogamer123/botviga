"""
Система списков кланов:
- генерация
- обновление
- ручной вызов админом
"""

import logging

from aiogram import Router, Bot, F
from aiogram.types import Message

from config import ROSTER_TOPICS
from database import (
    get_clan_members,
    get_roster_message_id,
    save_roster_message_id,
)
from utils.formatting import format_roster
from utils.permissions import can_edit_list

logger = logging.getLogger(__name__)
router = Router()


# ─── Обновление одного клана ──────────────────────────────────────────────────

async def update_clan_list(bot: Bot, clan: str):
    """
    Создаёт или обновляет сообщение списка клана в топике.
    """

    topic = ROSTER_TOPICS.get(clan)
    if not topic or not topic.get("thread_id"):
        logger.warning(f"Clan {clan} has no roster topic configured")
        return

    chat_id = topic["chat_id"]
    thread_id = topic["thread_id"]

    members = await get_clan_members(clan)
    text = format_roster(clan, members)

    msg_id = await get_roster_message_id(clan)

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
            raise Exception("no message id")

    except Exception:
        msg = await bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await save_roster_message_id(clan, msg.message_id)


# ─── Обновление всех кланов ──────────────────────────────────────────────────

async def update_all_clans(bot: Bot):
    for clan in ROSTER_TOPICS.keys():
        await update_clan_list(bot, clan)


# ─── Ручной вызов админом ────────────────────────────────────────────────────

@router.message(F.text == "📋 Редактировать список клана")
async def manual_update(message: Message, bot: Bot):
    """
    Просто принудительный refresh списка.
    """

    member = message.middleware_data.get("member")

    if not member or not can_edit_list(member):
        await message.answer("⛔ Нет прав.")
        return

    clan = member.get("clan")
    if not clan:
        await message.answer("❌ Клан не найден.")
        return

    await update_clan_list(bot, clan)

    await message.answer("✅ Список клана обновлён.")