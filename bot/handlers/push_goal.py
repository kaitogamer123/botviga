import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from database import get_member

from utils.permissions import can_launch_push_goal
from utils.keyboards import (
    launch_push_confirm_keyboard,
    push_goal_keyboard,
    confirm_push_goal_keyboard,
    notify_undecided_keyboard,
    confirm_notify_keyboard,
)
from utils.formatting import PUSH_GOAL_TEXT

from services.push_service import (
    launch_push_vote,
    save_push_goal,
    get_undecided_members,
    notify_undecided_users,
    notify_clan_news,
)

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────
# 1. ЗАПУСК ГОЛОСОВАНИЯ
# ─────────────────────────────────────────────

@router.message(F.text == "🎯 Запустить определение цели")
async def start_push_goal(message: Message):
    member = await get_member(message.from_user.id)

    if not member or not can_launch_push_goal(member):
        await message.answer("⛔ Нет прав.")
        return

    await message.answer(
        "⚠️ Ты уверен, что хочешь запустить выбор цели сезона?",
        reply_markup=launch_push_confirm_keyboard(),
    )


@router.callback_query(F.data == "launch_push:yes")
async def launch_push_yes(call: CallbackQuery, bot: Bot):
    await launch_push_vote(bot)
    await call.message.edit_text("📢 Голосование запущено всем участникам.")
    await call.answer()


@router.callback_query(F.data == "launch_push:no")
async def launch_push_no(call: CallbackQuery):
    await call.message.edit_text("❌ Отменено.")
    await call.answer()


# ─────────────────────────────────────────────
# 2. ВЫБОР ЦЕЛИ
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("push_goal:"))
async def choose_goal(call: CallbackQuery):
    goal = call.data.split(":")[1]

    await call.message.edit_text(
        f"Ты выбрал: <b>{'🏆 Трофеи' if goal == 'trophies' else '🏅 Лига'}</b>\n\n"
        "Подтверди выбор:",
        parse_mode="HTML",
        reply_markup=confirm_push_goal_keyboard(goal),
    )
    await call.answer()


# ─────────────────────────────────────────────
# 3. ПОДТВЕРЖДЕНИЕ ВЫБОРА
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("push_confirm:"))
async def confirm_goal(call: CallbackQuery):
    goal = call.data.split(":")[1]
    user_id = call.from_user.id

    ok = await save_push_goal(user_id, goal)

    if not ok:
        await call.answer(
            "⛔ Ты уже не можешь изменить выбор (48 часов).",
            show_alert=True,
        )
        return

    await call.message.edit_text(
        "✅ Твой выбор сохранён!\n\n"
        "Изменить его можно в течение 48 часов.",
    )
    await call.answer()


# ─────────────────────────────────────────────
# 4. НАЗАД
# ─────────────────────────────────────────────

@router.callback_query(F.data == "push_goal:back")
async def back_to_goal(call: CallbackQuery):
    await call.message.edit_text(
        PUSH_GOAL_TEXT,
        parse_mode="HTML",
        reply_markup=push_goal_keyboard(),
    )
    await call.answer()


# ─────────────────────────────────────────────
# 5. НЕОПРЕДЕЛИВШИЕСЯ
# ─────────────────────────────────────────────

@router.message(F.text == "❓ Кто не определился с пушем")
async def undecided_list(message: Message):
    member = await get_member(message.from_user.id)

    if not member:
        return

    undecided = await get_undecided_members()

    if not undecided:
        await message.answer("✅ Все определились.")
        return

    text = "<b>❗ Не определились:</b>\n\n"
    for u in undecided:
        nick = u.get("game_nick") or u.get("username") or str(u["user_id"])
        text += f"• {nick}\n"

    await message.answer(text, reply_markup=notify_undecided_keyboard())


# ─────────────────────────────────────────────
# 6. РАССЫЛКА НАПОМИНАНИЙ
# ─────────────────────────────────────────────

@router.callback_query(F.data == "notify:confirm")
async def notify_send(call: CallbackQuery, bot: Bot):
    await notify_undecided_users(bot)
    await notify_clan_news(bot)

    await call.message.edit_text("📢 Оповещение отправлено.")
    await call.answer()


@router.callback_query(F.data == "notify:cancel")
async def notify_cancel(call: CallbackQuery):
    await call.message.edit_text("❌ Отменено.")
    await call.answer()


# ─────────────────────────────────────────────
# 7. ОТМЕНА ОПОВЕЩЕНИЯ
# ─────────────────────────────────────────────

@router.callback_query(F.data == "undecided:back")
async def undecided_back(call: CallbackQuery):
    await call.message.delete()
    await call.answer()