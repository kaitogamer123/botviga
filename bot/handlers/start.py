"""
Обработчик /start — приветствие, идентификация участника.
"""

import logging
from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import CLAN_CHATS, ADMIN_CHAT_ID, INITIAL_ADMINS, CLAN_DISPLAY
from database import get_member, upsert_member
from utils.permissions import is_top_admin
from utils.formatting import welcome_text
from utils.keyboards import main_menu, choose_clan_keyboard, back_keyboard
from handlers.registration import RegStates

logger = logging.getLogger(__name__)
router = Router()


async def detect_user_clans(bot: Bot, user_id: int) -> list[str]:
    """Возвращает список кланов, в чатах которых состоит пользователь."""
    found = []
    for clan, info in CLAN_CHATS.items():
        try:
            member = await bot.get_chat_member(info["chat_id"], user_id)
            if member.status not in ("left", "kicked", "banned"):
                found.append(clan)
        except Exception:
            pass
    return found


async def detect_is_admin_chat(bot: Bot, user_id: int) -> bool:
    """Проверяет состоит ли пользователь в чате администрации."""
    if not ADMIN_CHAT_ID:
        return False
    try:
        m = await bot.get_chat_member(ADMIN_CHAT_ID, user_id)
        return m.status not in ("left", "kicked", "banned")
    except Exception:
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    await state.clear()

    # Загружаем или создаём запись
    member = await get_member(user_id)

    # Первичная проверка на президентов из конфига
    if not member and user_id in INITIAL_ADMINS:
        init = INITIAL_ADMINS[user_id]
        await upsert_member(
            user_id=user_id,
            username=message.from_user.username or init["username"],
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=init["role"],
            clan=init["clan"],
            registered=1,
        )
        member = await get_member(user_id)

    # Определяем клан(ы) пользователя через проверку чатов
    user_clans = await detect_user_clans(bot, user_id)
    is_admin_chat = await detect_is_admin_chat(bot, user_id)

    # Новый пользователь — не найден в БД
    if not member:
        if not user_clans:
            await message.answer(
                "👋 Привет!\n\n"
                "Ты не состоишь ни в одном клане ViGarik Squad.\n"
                "Если это ошибка — обратись к администратору."
            )
            return

        # Создаём запись
        role = "member"
        if is_admin_chat:
            role = "helper"  # минимальная роль из администрации — уточнят вручную

        chosen_clan = user_clans[0] if len(user_clans) == 1 else None

        await upsert_member(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=role,
            clan=chosen_clan,
            registered=0,
        )
        member = await get_member(user_id)

        if len(user_clans) > 1:
            await message.answer(
                "👋 Привет! Ты состоишь в нескольких кланах.\n"
                "Укажи, в каком из них ты основной участник:",
                reply_markup=choose_clan_keyboard(user_clans),
            )
            return

    # Обновляем данные из Telegram
    await upsert_member(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    member = await get_member(user_id)

    # Если клан не определён — спрашиваем
    if not member.get("clan"):
        if user_clans:
            if len(user_clans) == 1:
                await upsert_member(user_id=user_id, clan=user_clans[0])
                member = await get_member(user_id)
            else:
                await message.answer(
                    "В каком клане ты основной участник?",
                    reply_markup=choose_clan_keyboard(user_clans),
                )
                return

    clan = member.get("clan")

    if not member.get("registered"):
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"Ты состоишь в клане <b>{CLAN_DISPLAY.get(clan, clan)}</b>.\n\n"
            "Для завершения регистрации напиши свой <b>ник в игре</b>:",
            parse_mode="HTML",
        )
        await state.set_state(RegStates.waiting_nick)
        return

    await message.answer(
        welcome_text(member, clan),
        parse_mode="HTML",
        reply_markup=main_menu(member),
    )


# ─── Выбор клана из инлайн-кнопок ────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("choose_clan:"))
async def cb_choose_clan(call: CallbackQuery, state: FSMContext, bot: Bot):
    clan = call.data.split(":")[1]
    user_id = call.from_user.id

    await upsert_member(user_id=user_id, clan=clan)
    await call.message.delete()

    member = await get_member(user_id)
    if not member or not member.get("registered"):
        await call.message.answer(
            f"Отлично! Клан: <b>{CLAN_DISPLAY.get(clan, clan)}</b>.\n\n"
            "Теперь напиши свой <b>ник в игре</b>:",
            parse_mode="HTML",
        )
        from handlers.registration import RegStates
        await state.set_state(RegStates.waiting_nick)
    else:
        await call.message.answer(
            welcome_text(member, clan),
            parse_mode="HTML",
            reply_markup=main_menu(member),
        )
    await call.answer()
