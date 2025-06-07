from unittest.mock import AsyncMock

import pytest

import utils.settings as test_settings
from handlers.donate import (
    donate_callback,
    handle_pay_amount,
    handle_payment_method_callback,
    ref_stats_callback,
)
from services.payment.payment import PaymentService
from services.repositories.referral import ReferralRepository
from services.repositories.user import UserRepository


@pytest.mark.asyncio
class TestDonateHandlers:

    @pytest.fixture(autouse=True)
    def patch_settings(self, monkeypatch):
        monkeypatch.setattr(
            test_settings, "RUKASSA_SHOP_ID", "dummy_shop", raising=False
        )
        monkeypatch.setattr(
            test_settings, "RUKASSA_TOKEN", "dummy_token", raising=False
        )
        monkeypatch.setattr(
            test_settings, "AAIO_SHOP_ID", "dummy_aaio_shop", raising=False
        )
        monkeypatch.setattr(
            test_settings, "AAIO_TOKEN", "dummy_aaio_token", raising=False
        )

    async def test_donate_callback_sends_donate_keyboard(self, fake_callback_query):
        user_id = 7001
        chat_id = 7001
        cb = fake_callback_query(user_id, chat_id, data="donate")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        await donate_callback(cb)
        assert cb.message.edit_text.await_count == 1

    async def test_ref_stats_callback_displays_stats(self, fake_callback_query):
        user_id = 7002
        chat_id = 7002
        cb = fake_callback_query(user_id, chat_id, data="ref_stats")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        repo_ref = ReferralRepository(None)
        repo_ref.get_referral_stats = AsyncMock(return_value=(5, 10))
        cb.bot["repo_referral"] = repo_ref

        await ref_stats_callback(cb)
        assert cb.message.edit_text.await_count == 1

    async def test_handle_pay_amount_edits_text(self, fake_callback_query):
        user_id = 7003
        chat_id = 7003
        cb = fake_callback_query(user_id, chat_id, data="donate_50")
        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        await handle_pay_amount(cb)
        assert cb.message.edit_text.await_count == 1

    async def test_handle_payment_method_callback_invokes_payment(
        self, fake_callback_query
    ):
        user_id = 7004
        chat_id = 7004
        cb = fake_callback_query(user_id, chat_id, data="pay_rukassa_20")

        repo_user = UserRepository(None)
        repo_user.get_language = AsyncMock(return_value="en")
        cb.bot["repo_user"] = repo_user

        # Подменяем PaymentService
        ps = AsyncMock(spec=PaymentService)
        ps.process_payment_command = AsyncMock(return_value=("http://paylink", 999))
        cb.bot["payment_service"] = ps

        # При вызове handle_payment_method_callback должен быть вызван
        # ps.process_payment_command
        await handle_payment_method_callback(cb)
        ps.process_payment_command.assert_awaited_once()
        # И callback.message.answer тоже должен вызвать
        assert cb.message.answer.await_count == 2
