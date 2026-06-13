from datetime import datetime, timezone, timedelta
from database import get_all_push_goals


DEADLINE_HOURS = 48


def is_locked(chosen_at: str) -> bool:
    """
    Проверяет, прошло ли 48 часов с выбора.
    chosen_at приходит из SQLite datetime('now')
    """
    try:
        chosen_time = datetime.fromisoformat(chosen_at)
    except Exception:
        return False

    return datetime.now() - chosen_time > timedelta(hours=DEADLINE_HOURS)


async def get_locked_users(season_id: str = "current") -> list[int]:
    """
    Возвращает user_id тех, у кого истёк лимит изменения выбора
    """
    rows = await get_all_push_goals(season_id)

    locked = []
    for r in rows:
        if is_locked(r.get("chosen_at", "")):
            locked.append(r["user_id"])

    return locked