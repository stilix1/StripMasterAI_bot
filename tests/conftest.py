import pytest
from unittest.mock import AsyncMock

import asyncio
import random
from types import SimpleNamespace


from services.repositories.system import SystemRepository
from utils import settings  # Чтобы взять настройки подключения к БД


@pytest.fixture(scope="session")
def event_loop():
    """
    Создаём отдельный loop для pytest‐asyncio.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_pool():
    """
    Фикстура, создающая тестовый пул и инициализирующая таблицы через SystemRepository.
    """
    pool = await SystemRepository.create_pool(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE,
        host=settings.DB_HOST,
    )
    # Инициализируем схему и таблицы
    await SystemRepository.create_tables(pool)
    yield pool
    await pool.close()


@pytest.fixture(scope="session")
def user_id_sequence():
    """
    Возвращает Python‐генератор для уникальных user_id.
    """
    base = 100000

    def gen():
        while True:
            yield random.randint(base, base + 99999)

    return gen()


@pytest.fixture
def user_factory(db_pool, user_id_sequence):
    """
    Фабрика для быстрого создания пользователя в БД через UserRepository.
    """

    async def _create_user(
        username="testuser",
        language_code="en",
        is_premium=False,
        ref_link=None,
        invited_by=None,
    ):
        from services.repositories.user import UserRepository

        user_id = next(user_id_sequence)
        repo = UserRepository(db_pool)
        # Задаём username на основе user_id, чтобы не было коллизий
        uname = f"user_{user_id}"
        await repo.add_user(
            user_id=user_id,
            username=uname,
            language_code=language_code,
            is_premium=is_premium,
            ref_link=ref_link,
            invited_by=invited_by,
        )
        return user_id

    return _create_user


@pytest.fixture
def fake_message():
    """
    Фабрика для "простого" сообщения Telegram (Message).
    """

    def _fake_message(user_id, chat_id, text="", args=""):
        message = SimpleNamespace()
        message.from_user = SimpleNamespace(id=user_id, username="user")
        message.chat = SimpleNamespace(id=chat_id)
        message.text = text
        message.get_args = lambda: args
        # Добавляем методы, которые могут вызывать хэндлеры:
        message.reply = AsyncMock()
        message.answer = AsyncMock()
        message.delete = AsyncMock()
        # "bot" остаётся пустым словарём
        message.bot = {}
        return message

    return _fake_message


@pytest.fixture
def fake_callback_query():
    """
    Фабрика для "фейкового" CallbackQuery.
    """

    def _fake_callback(user_id, chat_id, data=""):
        callback = SimpleNamespace()
        callback.from_user = SimpleNamespace(id=user_id)
        callback.data = data

        # Митим поведение callback.message
        callback.message = SimpleNamespace()
        callback.message.chat = SimpleNamespace(id=chat_id)
        callback.message.message_id = 1
        callback.message.edit_text = AsyncMock()
        callback.message.answer = AsyncMock()
        callback.message.delete = AsyncMock()
        # "answer_photo" требуется для Photo-хэндлеров
        callback.message.answer_photo = AsyncMock()

        # callback.message.bot нужен для delete_message и send_message
        callback.message.bot = SimpleNamespace(
            delete_message=AsyncMock(), send_message=AsyncMock()
        )

        # Словарь для репозиториев и сервисов
        callback.bot = {}
        return callback

    return _fake_callback


@pytest.fixture(autouse=True)
def patch_payment_monitor(monkeypatch):
    monkeypatch.setattr(
        "services.payment.payment.PaymentService.monitor_payment",
        AsyncMock(return_value=None),
    )
