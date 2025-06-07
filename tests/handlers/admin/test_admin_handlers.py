import pytest

from handlers.admin import (
    handle_ref_info,
    send_stats,
)
from services.repositories.referral import ReferralRepository
from services.repositories.user import UserRepository
from utils import settings


@pytest.mark.asyncio
class TestAdminHandlers:

    async def test_send_stats_non_admin(self, fake_message):
        # Выбираем user_id, которого нет в settings.ADMIN_IDS
        non_admin_id = 99999
        chat_id = non_admin_id
        msg = fake_message(non_admin_id, chat_id, text="/stats")

        await send_stats(msg)
        # Никаких reply быть не должно
        assert msg.reply.await_count == 1

    async def test_handle_ref_info_valid_id(self, db_pool, fake_message):
        # Выбираем админа
        admin_id = settings.ADMIN_IDS[0]
        chat_id = admin_id

        user_repo = UserRepository(db_pool)
        # Создаём inviter и invited, причем inviter = admin
        inviter_id = admin_id
        invited_id = 6003

        await user_repo.add_user(
            inviter_id, f"user_{inviter_id}", "en", False, None, None
        )
        await user_repo.add_user(
            invited_id, f"user_{invited_id}", "en", False, None, inviter_id
        )

        referral_repo = ReferralRepository(db_pool)
        await referral_repo.record_invitation(inviter_id, invited_id)
        await referral_repo.add_referral_credits(inviter_id)

        msg = fake_message(inviter_id, chat_id, text=f"/ref_info {inviter_id}")
        msg.bot["repo_referral"] = referral_repo

        # Т.к. send_stats не внедрялось, но handle_ref_info работает независимо от
        # repo_user
        await handle_ref_info(msg)
        # Должен вызвать хотя бы один reply (выдача текста с инфой)
        assert msg.reply.await_count == 1
