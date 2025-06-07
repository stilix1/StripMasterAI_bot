import os
from unittest.mock import AsyncMock

import pytest

from handlers.photo import (
    PhotoStates,
    cancel_callback,
    handle_bust_size_selection,
    send_photo_api_callback,
)
from services.payment.payment import PaymentService
from services.repositories.transaction import TransactionRepository
from services.repositories.user import UserRepository


@pytest.mark.asyncio
class TestPhotoHandlers:

    async def test_send_photo_api_callback_sends_prompt(self, fake_callback_query):
        # Чтобы PhotoStates.waiting_for_photo.set() не падал:
        PhotoStates.waiting_for_photo.set = AsyncMock()

        user_id = 9001
        chat_id = 9001
        cb = fake_callback_query(user_id, chat_id, data="send_photo_api")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        fake_state = AsyncMock()
        fake_state.update_data = AsyncMock()
        await send_photo_api_callback(cb, fake_state)
        assert cb.message.edit_text.await_count == 1

    async def test_cancel_callback_resets_to_menu(self, fake_callback_query):
        user_id = 9002
        chat_id = 9002
        cb = fake_callback_query(user_id, chat_id, data="cancel")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        state = AsyncMock()
        await cancel_callback(cb, state)
        state.finish.assert_awaited_once()
        assert cb.message.edit_text.await_count == 1

    async def test_handle_bust_size_selection_deducts_and_processes(
        self, fake_callback_query, tmp_path
    ):
        user_id = 9003
        chat_id = 9003
        cb = fake_callback_query(user_id, chat_id, data="bust_L")

        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        repo_trans = TransactionRepository(None)
        repo_trans.deduct_credits = AsyncMock(return_value=True)
        cb.bot["repo_transaction"] = repo_trans

        ps = PaymentService(
            bot=cb.message.bot,
            repo_user=repo_user,
            repo_transaction=repo_trans,
            repo_referral=None,
        )
        ps.paymont_create_picture = AsyncMock(return_value=str(tmp_path / "result.png"))
        cb.bot["payment_service"] = ps

        fake_state = AsyncMock()
        fake_state.update_data = AsyncMock()
        fake_state.get_data.return_value = {
            "photo_path": str(tmp_path / "orig.png"),
            "bust_size_message_id": 1234,
        }
        (tmp_path / "result.png").write_text("fake")
        (tmp_path / "orig.png").write_text("orig")

        await handle_bust_size_selection(cb, fake_state)
        ps.paymont_create_picture.assert_awaited_once()
        assert not os.path.exists(str(tmp_path / "orig.png"))
