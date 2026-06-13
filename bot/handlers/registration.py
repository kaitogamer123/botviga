"""
Регистрация участника: получение ника в игре.
"""

import logging
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database import get_member, upsert_member
from database import get_push_pending, remove_push_pending
from utils.keyboards import main_menu
from utils.formatting import welcome_text, PUSH_GOAL_TEXT
from utils.keyboards import push_goal_keyboard
from utils.roster_sync import sync_clan_roster

logger = logging.getLogger(__name__)
router = Router()


class RegStates(StatesGroup):
    waiting_nick = State()
    waiting_new_nick = State()


@router.message(RegStates.waiting_nick)
async def receive_game_nick(message: Message, state: FSMContext):
    nick = message.text.strip()
    if not nick:
        await message.answer("Ник не может быть пустым. Попробуй ещё раз:")
        return

    user_id = message.from_user.id
    await upsert_member(user_id=user_id, game_nick=nick, registered=1)

    member = await get_member(user_id)
    clan = member.get("clan", "")

    # Синхронизируем список клана
    from main import bot as _bot
    await sync_clan_roster(_bot, clan)

    await state.clear()
    await message.answer(
        "✅ <b>Спасибо, регистрация прошла успешно!</b>",
        parse_mode="HTML",
    )
    await message.answer(
        welcome_text(member, clan),
        parse_mode="HTML",
        reply_markup=main_menu(member),
    )

    # Проверяем — ждёт ли этого пользователя вопрос о цели пуша
    pending = await get_push_pending()
    pending_ids = [p["user_id"] for p in pending]
    if user_id in pending_ids:
        await remove_push_pending(user_id)
        await message.answer(PUSH_GOAL_TEXT, parse_mode="HTML", reply_markup=push_goal_keyboard())


@router.message(RegStates.waiting_new_nick)
async def receive_new_nick(message: Message, state: FSMContext):
    nick = message.text.strip()
    if not nick:
        await message.answer("Ник не может быть пустым. Попробуй ещё раз:")
        return

    user_id = message.from_user.id
    await upsert_member(user_id=user_id, game_nick=nick)

    member = await get_member(user_id)
    clan = member.get("clan", "")

    from main import bot as _bot
    await sync_clan_roster(_bot, clan)

    await state.clear()
    await message.answer(
        "✅ Ник обновлён! Список клана обновлён.",
        reply_markup=main_menu(member),
    )


# ─── Кнопка «Изменить текущий ник» ───────────────────────────────────────────

@router.message(lambda m: m.text == "✏️ Изменить текущий ник")
async def change_nick_button(message: Message, state: FSMContext):
    member = await get_member(message.from_user.id)
    if not member or not member.get("registered"):
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return

    current = member.get("game_nick", "не установлен")
    await message.answer(
        f"Текущий ник: <b>{current}</b>\n\nНапиши новый ник в игре:",
        parse_mode="HTML",
    )
    await state.set_state(RegStates.waiting_new_nick)
