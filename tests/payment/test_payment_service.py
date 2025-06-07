from unittest.mock import AsyncMock, MagicMock

import pytest

import utils.settings as test_settings
from services.payment.payment import PaymentService


@pytest.mark.asyncio
class TestPaymentService:

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

    @pytest.fixture
    def mock_bot(self):
        bot = MagicMock()
        # Чтобы delete_message, send_message и edit_message_text можно было await
        bot.delete_message = AsyncMock()
        bot.send_message = AsyncMock()
        bot.edit_message_text = AsyncMock()
        return bot

    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        repo.get_language.return_value = "en"
        repo.get_referrer_id.return_value = None
        return repo

    @pytest.fixture
    def mock_trans_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_ref_repo(self):
        return AsyncMock()

    @pytest.fixture
    def payment_service(self, mock_bot, mock_user_repo, mock_trans_repo, mock_ref_repo):
        return PaymentService(
            bot=mock_bot,
            repo_user=mock_user_repo,
            repo_transaction=mock_trans_repo,
            repo_referral=mock_ref_repo,
        )

    async def test_process_payment_command_unknown_method(self, payment_service):
        mock_callback = MagicMock()
        mock_callback.from_user.id = 1
        mock_callback.message.chat.id = 123
        mock_callback.message.message_id = 456

        text, order_id = await payment_service.process_payment_command(
            mock_callback, 50, "en", "unknown"
        )
        assert order_id is None
        # text[0] содержит ключ-кортеж, начинающийся с create_url_error
        assert isinstance(text, str)
        assert text.startswith("Please proceed to the payment link")

    async def test_process_payment_command_rukassa(self, payment_service, monkeypatch):
        # Патчим тот путь, который реально используется внутри PaymentService:
        async def fake_create_rukassa(shop_id, order_id, amount, token, user_code):
            return {"url": "http://paylink"}

        monkeypatch.setattr(
            "services.payment.payment.create_payment_rukassa", fake_create_rukassa
        )

        mock_callback = MagicMock()
        mock_callback.from_user.id = 2
        mock_callback.message.chat.id = 234
        mock_callback.message.message_id = 567

        text, transaction_id = await payment_service.process_payment_command(
            mock_callback, 75, "en", "rukassa"
        )
        # Должен вернуть ссылку на оплату и целочисленный transaction_id
        assert "http://" in text
        assert isinstance(transaction_id, int)
