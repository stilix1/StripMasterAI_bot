from unittest.mock import AsyncMock

import pytest

from handlers.start import language_command, start_command
from services.repositories.user import UserRepository


@pytest.mark.asyncio
class TestStartHandlers:

    async def test_start_creates_new_user_and_sends_language_prompt(
        self, db_pool, fake_message
    ):
        new_user_id = 5001
        chat_id = 5001
        msg = fake_message(new_user_id, chat_id, text="/start", args="")

        # Внедряем UserRepository
        msg.bot["repo_user"] = UserRepository(db_pool)
        # ReferralRepository не нужен в этом тесте, поэтому оставляем None
        msg.bot["repo_referral"] = None

        await start_command(msg, state=None)

        repo = UserRepository(db_pool)
        lang = await repo.get_language(new_user_id)
        assert lang == "en"

    async def test_language_command_prompts_language_selection(self, fake_message):
        user_id = 5002
        chat_id = 5002
        msg = fake_message(user_id, chat_id, text="/language", args="")

        dummy_repo = UserRepository(None)
        dummy_repo.get_language = AsyncMock(return_value="en")
        msg.bot["repo_user"] = dummy_repo

        await language_command(msg)
        # Метод answer должен быть вызван
        assert msg.answer.await_count == 1
