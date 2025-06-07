from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.executor import start_polling

import services.image  # для watermark обработки
from handlers import register_handlers
from services.payment.payment import PaymentService
from services.repositories.referral import ReferralRepository
from services.repositories.system import SystemRepository
from services.repositories.transaction import TransactionRepository
from services.repositories.user import UserRepository
from utils import settings

bot = Bot(token=settings.Token)
dp = Dispatcher(bot, storage=MemoryStorage())


async def on_startup(dispatcher: Dispatcher):
    # 1. Подключение к базе данных
    pool = await SystemRepository.create_pool(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE,
        host=settings.DB_HOST,
    )

    # 2. Создание таблиц, если их нет
    await SystemRepository.create_tables(pool)

    # 3. Инициализация репозиториев и сервисов
    repo_user = UserRepository(pool)
    repo_referral = ReferralRepository(pool)
    repo_transaction = TransactionRepository(pool)
    payment_service = PaymentService(bot, repo_user, repo_transaction, repo_referral)

    # 4. Регистрация зависимостей в dispatcher и bot
    dispatcher["db_pool"] = pool
    dispatcher["repo_user"] = repo_user
    dispatcher["repo_referral"] = repo_referral
    dispatcher["repo_transaction"] = repo_transaction

    bot["repo_user"] = repo_user
    bot["repo_referral"] = repo_referral
    bot["repo_transaction"] = repo_transaction
    bot["payment_service"] = payment_service
    bot["image_editor"] = services.image


async def on_shutdown(dispatcher: Dispatcher):
    pool = dispatcher.get("db_pool")
    if pool:
        await pool.close()


register_handlers(dp)

if __name__ == "__main__":
    start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
