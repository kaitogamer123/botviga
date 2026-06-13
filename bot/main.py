import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import TOKEN
from database import init_db
from utils.roster_sync import sync_all_rosters

# handlers
from handlers.start import router as start_router
from handlers.registration import router as reg_router
from handlers.admin import router as admin_router
from handlers.proposals import router as proposals_router

# optional future modules
# from handlers.push_goal import router as push_router
# from handlers.clan_list import router as clan_router
# from handlers.chat_events import router as chat_router


logging.basicConfig(level=logging.INFO)


bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


async def on_startup():
    await init_db()
    logging.info("Database initialized")

    # первичная синхронизация списков
    await sync_all_rosters(bot)
    logging.info("Initial roster sync done")


async def main():
    dp.include_router(start_router)
    dp.include_router(reg_router)
    dp.include_router(admin_router)
    dp.include_router(proposals_router)

    # future
    # dp.include_router(push_router)
    # dp.include_router(clan_router)
    # dp.include_router(chat_router)

    await on_startup()

    logging.info("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())