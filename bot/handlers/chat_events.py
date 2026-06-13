import logging
from aiogram import Router, F, Bot
from aiogram.types import ChatMemberUpdated

from config import CLAN_CHATS, CLAN_DISPLAY
from database import get_member, upsert_member, remove_member, add_push_pending
from utils.roster_sync import sync_clan_roster

logger = logging.getLogger(__name__)
router = Router()


def detect_clan_by_chat(chat_id: int):
    for clan, data in CLAN_CHATS.items():
        if data["chat_id"] == chat_id:
            return clan
    return None


def build_user_link(user):
    if user.username:
        return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{user.first_name or user.id}</a>'


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, bot: Bot):
    chat_id = event.chat.id
    clan = detect_clan_by_chat(chat_id)

    if not clan:
        return

    user = event.new_chat_member.user
    user_id = user.id

    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    # ─── ВХОД В КЛАН ─────────────────────────────
    if new_status in ("member", "administrator") and old_status in ("left", "kicked"):

        member = await get_member(user_id)

        if not member:
            await upsert_member(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                clan=clan,
                registered=0,
            )
        else:
            await upsert_member(
                user_id=user_id,
                clan=clan,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )

        # ─── сообщение в чат клана ───────────────
        try:
            await bot.send_message(
                chat_id,
                f"👋 Добро пожаловать в <b>{CLAN_DISPLAY.get(clan, clan)}</b>, {build_user_link(user)}!\n"
                f"Пройди регистрацию в боте, чтобы попасть в список участников.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"welcome msg failed: {e}")

        # ─── ЛС пользователю ─────────────────────
        try:
            await bot.send_message(
                user_id,
                f"👋 Ты вступил в клан <b>{CLAN_DISPLAY.get(clan, clan)}</b>.\n\n"
                f"Обязательно пройди регистрацию в боте через /start."
            )
        except Exception:
            pass  # у пользователя может быть закрыт ЛС

        # ─── если не зарегистрирован → очередь пуша ─────
        if not member or not member.get("registered"):
            await add_push_pending(user_id)

        await sync_clan_roster(bot, clan)

    # ─── ВЫХОД ИЗ КЛАНА ─────────────────────────
    elif new_status in ("left", "kicked"):

        member = await get_member(user_id)
        if member:
            await upsert_member(user_id=user_id, clan=None)

        await sync_clan_roster(bot, clan)


@router.chat_member(F.new_chat_member.status == "administrator")
async def on_admin_added(event: ChatMemberUpdated):
    pass