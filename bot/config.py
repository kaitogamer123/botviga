"""
Конфигурация бота ViGarik Squad
"""

TOKEN = "8342840075:AAE5HdZ7L_QZSuQCDxpdevK2-HxDQ72ABw8"

# ─── Чаты кланов ───────────────────────────────────────────────────────────────
CLAN_CHATS = {
    "academy": {
        "title": "ViGarik Squad Academy",
        "chat_id": -1002237164277,
    },
    "squad": {
        "title": "ViGarik Squad",
        "chat_id": -1002187842577,
    },
    "events": {
        "title": "ViGarik Events",
        "chat_id": -1002451600406,
    },
}

# ─── Топики новостей кланов ────────────────────────────────────────────────────
ADMIN_NEWS_TARGETS = {
    "academy": {
        "title": "ViGarik Squad Academy",
        "chat_id": -1002237164277,
        "thread_id": 33272,
    },
    "squad": {
        "title": "ViGarik Squad",
        "chat_id": -1002187842577,
        "thread_id": 129460,
    },
    "events": {
        "title": "ViGarik Events",
        "chat_id": -1002451600406,
        "thread_id": 5361,
    },
}

# ─── Топики списков участников (впиши сам thread_id топика «Список» в каждом чате) ───
ROSTER_TOPICS = {
    "academy": {
        "chat_id": -1002237164277,
        "thread_id": None,   # <-- впиши thread_id топика со списком академии
    },
    "squad": {
        "chat_id": -1002187842577,
        "thread_id": None,   # <-- впиши thread_id топика со списком основного клана
    },
    "events": {
        "chat_id": -1002451600406,
        "thread_id": None,   # <-- впиши thread_id топика со списком клана Events
    },
}

# ─── Чат администрации ────────────────────────────────────────────────────────
ADMIN_CHAT_ID = None  # <-- впиши chat_id чата администрации

# ─── Иерархия ролей ───────────────────────────────────────────────────────────
ROLES = {
    "president":       0,   # Президент          (наивысший приоритет)
    "grand_vice":      1,   # Гранд Вице Президент
    "vice":            2,   # Вице Президент
    "veteran":         3,   # Ветеран
    "helper":          4,   # Помощник
    "member":          5,   # Участник
}

ROLE_LABELS = {
    "president":  "👑 Президент",
    "grand_vice": "🔱 Гранд Вице Президент",
    "vice":       "⚜️ Вице Президент",
    "veteran":    "🎖️ Ветеран",
    "helper":     "🤝 Помощник",
    "member":     "👤 Участник",
}

# ─── Начальные президенты / гранд-вице-президенты ─────────────────────────────
INITIAL_ADMINS = {
    5281584435: {"username": "dyadya_karlson", "role": "president",  "clan": None},
    7899153362: {"username": "Ka1D3en",        "role": "president",  "clan": None},
}

# Минимальная роль для редактирования списков
EDIT_LIST_MIN_ROLE = "vice"

# Минимальная роль для назначения модерации
APPOINT_ADMIN_MIN_ROLE = "president"

# Deadline смены решения о пуше (дней)
PUSH_CHANGE_DEADLINE_DAYS = 2

# Названия кланов (для отображения)
CLAN_DISPLAY = {
    "academy": "ViGarik Squad Academy",
    "squad":   "ViGarik Squad",
    "events":  "ViGarik Events",
}

# Emoji-шапки списков
CLAN_HEADER_EMOJI = {
    "academy": "🎓",
    "squad":   "👑",
    "events":  "🎉",
}
