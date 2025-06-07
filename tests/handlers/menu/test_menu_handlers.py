from unittest.mock import AsyncMock

import pytest

from handlers.menu import (
    back_callback,
    lang_callback,
    profile_callback,
    referral_callback,
    reply_start,
    terms_callback,
)
from services.repositories.user import UserRepository


@pytest.mark.asyncio
class TestMenuHandlers:

    async def test_reply_start_sends_menu(self, fake_message):
        user_id = 8001
        chat_id = 8001
        msg = fake_message(user_id, chat_id, text="💼Menu")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        msg.bot["repo_user"] = repo_user

        await reply_start(msg)
        assert msg.answer.await_count == 1

    async def test_lang_callback_updates_language_and_sends_menu(
        self, fake_callback_query
    ):
        user_id = 8002
        chat_id = 8002
        cb = fake_callback_query(user_id, chat_id, data="ru")
        repo_user = UserRepository(None)
        repo_user.update_language = AsyncMock()
        cb.bot["repo_user"] = repo_user

        await lang_callback(cb)
        repo_user.update_language.assert_awaited_once_with(str(user_id), "ru")
        assert cb.message.delete.await_count == 1

    async def test_terms_callback_yes(self, fake_callback_query):
        user_id = 8003
        chat_id = 8003
        cb = fake_callback_query(user_id, chat_id, data="terms_yes")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        await terms_callback(cb)
        assert cb.message.edit_text.await_count == 1

    async def test_back_callback_resets_menu(self, fake_callback_query):
        user_id = 8004
        chat_id = 8004
        cb = fake_callback_query(user_id, chat_id, data="back")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        state = AsyncMock()
        await back_callback(cb, state)
        state.finish.assert_awaited_once()
        assert cb.message.edit_text.await_count == 1

    async def test_profile_callback_displays_profile(self, fake_callback_query):
        user_id = 8005
        chat_id = 8005
        cb = fake_callback_query(user_id, chat_id, data="profile")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        repo_user.get_profile_data = AsyncMock(
            return_value={
                "username": "u",
                "balance": 100,
                "ref_balance": 20,
                "ref_link": "lk",
                "created_at": "2025-01-01 00:00:00",
            }
        )
        cb.bot["repo_user"] = repo_user

        await profile_callback(cb)
        assert cb.message.edit_text.await_count == 1

    async def test_referral_callback_displays_referral(self, fake_callback_query):
        user_id = 8006
        chat_id = 8006
        cb = fake_callback_query(user_id, chat_id, data="referral")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        repo_user.get_profile_data = AsyncMock(
            return_value={
                "username": "u",
                "balance": 200,
                "ref_balance": 40,
                "ref_link": "lk2",
                "created_at": "2025-02-02 00:00:00",
            }
        )
        cb.bot["repo_user"] = repo_user

        await referral_callback(cb)
        assert cb.message.edit_text.await_count == 1
