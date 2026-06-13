"""
Административные функции:
- Назначение модерации
- Редактирование списка клана
- Участники без ников
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_member, upsert_member, get_all_members, get_unregistered_members, get_clan_members, remove_member
from utils.permissions import can_edit_list, can_appoint_admins, is_any_admin
from utils.keyboards import appoint_role_keyboard, back_keyboard, main_menu
from utils.roster_sync import sync_clan_roster
from config import ROLE_LABELS, CLAN_DISPLAY

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_appoint_user = State()
    waiting_edit_member_id = State()
    waiting_new_nick_for_member = State()


# ─── Назначение модерации ─────────────────────────────────────────────────────

@router.message(F.text == "⚙️ Назначить модерацию")
async def appoint_start(message: Message, state: FSMContext):
    member = await get_member(message.from_user.id)
    if not member or not can_appoint_admins(member):
        await message.answer("⛔ У тебя нет прав для назначения модерации.")
        return

    await message.answer(
        "Напиши <b>user_id</b> или <b>@username</b> участника, "
        "которому хочешь назначить роль:",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_appoint_user)


@router.message(AdminStates.waiting_appoint_user)
async def appoint_receive_user(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()

    target = None
    if text.lstrip("-").isdigit():
        target = await get_member(int(text))
    elif text.startswith("@"):
        uname = text[1:]
        all_members = await get_all_members()
        target = next((m for m in all_members if m.get("username") == uname), None)

    if not target:
        await message.answer("❌ Участник не найден в базе. Попробуй ещё раз:")
        return

    await state.update_data(target_id=target["user_id"])
    nick = target.get("game_nick") or target.get("username") or str(target["user_id"])
    await message.answer(
        f"Выбери роль для участника <b>{nick}</b>:",
        parse_mode="HTML",
        reply_markup=appoint_role_keyboard(target["user_id"]),
    )
    await state.clear()


@router.callback_query(lambda c: c.data and c.data.startswith("appoint:") and c.data != "appoint:cancel")
async def appoint_role_cb(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    if len(parts) < 3:
        return
    _, target_id_str, role = parts[0], parts[1], parts[2]

    # Проверяем права
    admin = await get_member(call.from_user.id)
    if not admin or not can_appoint_admins(admin):
        await call.answer("⛔ Нет прав.", show_alert=True)
        return

    try:
        target_id = int(target_id_str)
    except ValueError:
        return

    await upsert_member(user_id=target_id, role=role)
    target = await get_member(target_id)
    nick = target.get("game_nick") or target.get("username") or str(target_id)
    role_label = ROLE_LABELS.get(role, role)

    await call.message.edit_text(
        f"✅ Роль <b>{role_label}</b> назначена участнику <b>{nick}</b>.",
        parse_mode="HTML",
    )
    await call.answer()

    # Уведомляем участника
    try:
        await bot.send_message(
            target_id,
            f"🎉 Тебе назначена новая роль: <b>{role_label}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data == "appoint:cancel")
async def appoint_cancel(call: CallbackQuery):
    await call.message.delete()
    await call.answer()


# ─── Редактирование списка клана ──────────────────────────────────────────────

@router.message(F.text == "📋 Редактировать список клана")
async def edit_list_start(message: Message, state: FSMContext, bot: Bot):
    member = await get_member(message.from_user.id)
    if not member or not can_edit_list(member):
        await message.answer("⛔ Недостаточно прав. Требуется Вице Президент и выше.")
        return

    clan = member.get("clan")
    if not clan:
        await message.answer("❌ Твой клан не определён.")
        return

    members = await get_clan_members(clan)
    if not members:
        await message.answer("Список клана пуст.")
        return

    lines = ["<b>Список участников:</b>\n"]
    for m in members:
        uid = m["user_id"]
        nick = m.get("game_nick") or "—"
        uname = m.get("username") or str(uid)
        lines.append(f"• <code>{uid}</code> | @{uname} | {nick}")

    await message.answer(
        "\n".join(lines) + "\n\nВведи <b>user_id</b> участника "
        "которого хочешь отредактировать (или удалить из списка):",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_edit_member_id)


@router.message(AdminStates.waiting_edit_member_id)
async def edit_list_receive_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.lstrip("-").isdigit():
        await message.answer("Введи числовой user_id:")
        return

    target_id = int(text)
    target = await get_member(target_id)
    if not target:
        await message.answer("❌ Участник не найден.")
        await state.clear()
        return

    nick = target.get("game_nick") or "—"
    await state.update_data(edit_target_id=target_id)
    await message.answer(
        f"Участник: <b>{nick}</b>\n\n"
        "Напиши новый ник (или /delete чтобы удалить из списка):",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_new_nick_for_member)


@router.message(AdminStates.waiting_new_nick_for_member)
async def edit_list_set_nick(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_id = data.get("edit_target_id")
    editor = await get_member(message.from_user.id)

    if message.text.strip() == "/delete":
        await remove_member(target_id)
        target_clan = editor.get("clan")
        await state.clear()
        await message.answer("🗑 Участник удалён из списка.")
        await sync_clan_roster(bot, target_clan)
        return

    new_nick = message.text.strip()
    if not new_nick:
        await message.answer("Ник не может быть пустым.")
        return

    target = await get_member(target_id)
    target_clan = target.get("clan") if target else editor.get("clan")

    await upsert_member(user_id=target_id, game_nick=new_nick)
    await state.clear()
    await message.answer(f"✅ Ник обновлён на <b>{new_nick}</b>.", parse_mode="HTML")
    if target_clan:
        await sync_clan_roster(bot, target_clan)


# ─── Участники без ников ──────────────────────────────────────────────────────

@router.message(F.text == "👤 Участники без ников")
async def unregistered_list(message: Message):
    member = await get_member(message.from_user.id)
    if not member or not is_any_admin(member):
        await message.answer("⛔ Нет прав.")
        return

    clan = member.get("clan")
    members = await get_unregistered_members(clan)

    if not members:
        await message.answer("✅ Все участники прошли регистрацию!")
        return

    lines = [f"<b>Участники без ника ({CLAN_DISPLAY.get(clan, clan)}):</b>\n"]
    for m in members:
        uname = m.get("username")
        name = f"@{uname}" if uname else m.get("first_name") or str(m["user_id"])
        lines.append(f"• {name} — <code>{m['user_id']}</code>")

    await message.answer("\n".join(lines), parse_mode="HTML")
