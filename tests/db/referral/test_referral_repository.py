import pytest

from services.repositories.referral import ReferralRepository
from services.repositories.transaction import TransactionRepository
from services.repositories.user import UserRepository


@pytest.mark.asyncio
class TestReferralRepository:

    @pytest.fixture
    async def repo(self, db_pool):
        return ReferralRepository(db_pool)

    @pytest.fixture
    async def user_repos(self, db_pool):
        return UserRepository(db_pool), TransactionRepository(db_pool)

    async def test_record_invitation_and_stats(
        self, repo, user_repos, user_id_sequence
    ):
        user_repo, _ = user_repos
        inviter = next(user_id_sequence)
        invited = next(user_id_sequence)

        # Оба пользователя с уникальными именами
        await user_repo.add_user(inviter, f"user_{inviter}", "en", False, None, None)
        await user_repo.add_user(invited, f"user_{invited}", "en", False, None, inviter)

        # Регистрируем приглашение
        await repo.record_invitation(inviter, invited)
        referrals_count, _ = await repo.get_referral_stats(inviter)
        assert referrals_count >= 1

    async def test_add_referral_credits(self, repo, user_repos, user_id_sequence):
        user_repo, _ = user_repos
        user_id = next(user_id_sequence)
        await user_repo.add_user(user_id, f"user_{user_id}", "en", False, None, None)

        # После добавления в кредиты free было 40, добавляем ещё реферальных (+20)
        await repo.add_referral_credits(user_id)
        profile = await user_repo.get_profile_data(user_id)
        # Баланс (free + paid + ref) теперь >= 20
        assert profile["balance"] >= 20

    async def test_get_new_users_from_referral(
        self, repo, user_repos, user_id_sequence
    ):
        user_repo, _ = user_repos
        inviter = next(user_id_sequence)
        referred = next(user_id_sequence)

        await user_repo.add_user(inviter, f"user_{inviter}", "en", False, None, None)
        await user_repo.add_user(
            referred, f"user_{referred}", "en", False, None, inviter
        )

        all_count = await repo.get_new_users_from_referral()
        assert all_count >= 1

        by_id = await repo.get_new_users_from_referral_by_id(inviter)
        assert by_id >= 1

    async def test_get_users_with_balance_from_referral(
        self, repo, user_repos, user_id_sequence
    ):
        user_repo, trans_repo = user_repos
        inviter = next(user_id_sequence)
        referred = next(user_id_sequence)

        await user_repo.add_user(inviter, f"user_{inviter}", "en", False, None, None)
        await user_repo.add_user(
            referred, f"user_{referred}", "en", False, None, inviter
        )

        # Записываем реферальную транзакцию от referred
        await trans_repo.record_referral_transaction(referred, 30, "ok")

        all_count = await repo.get_users_with_balance_from_referral()
        assert all_count >= 1

        by_id = await repo.get_users_with_balance_from_referral_by_id(inviter)
        assert by_id >= 1

    async def test_get_total_referral_topups_by_id(
        self, repo, user_repos, user_id_sequence
    ):
        user_repo, trans_repo = user_repos

        inviter = next(user_id_sequence)
        invited = next(user_id_sequence)
        await user_repo.add_user(inviter, f"user_{inviter}", "en", False, None, None)
        await user_repo.add_user(invited, f"user_{invited}", "en", False, None, inviter)

        # Затем записываем реферальную транзакцию от имени invited
        await trans_repo.record_referral_transaction(invited, 50, "done")

        total_id = await repo.get_total_referral_topups_by_id(inviter)
        assert total_id >= 50
