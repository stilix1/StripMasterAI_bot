import pytest

from services.repositories.transaction import TransactionRepository
from services.repositories.user import UserRepository


@pytest.mark.asyncio
class TestTransactionRepository:

    @pytest.fixture
    async def repo(self, db_pool):
        return TransactionRepository(db_pool)

    @pytest.fixture
    async def user_repo(self, db_pool):
        return UserRepository(db_pool)

    async def test_record_transaction_and_add_credits(
        self, repo, user_repo, user_id_sequence
    ):
        user_id = next(user_id_sequence)
        await user_repo.add_user(user_id, f"user_{user_id}", "en", False, None, None)

        tx_id = next(user_id_sequence)
        # Удаляем старую транзакцию, если случайно есть с тем же ID
        async with repo.pool.acquire() as conn:
            await conn.execute("DELETE FROM data.transactions WHERE id = $1", tx_id)

        await repo.record_transaction(tx_id, user_id, "success", 100)
        await repo.add_user_credits(user_id, 100)

        profile = await user_repo.get_profile_data(user_id)
        assert profile["balance"] >= 100

    async def test_deduct_credits(self, repo, user_repo, user_id_sequence):
        user_id = next(user_id_sequence)
        await user_repo.add_user(user_id, f"user_{user_id}", "en", False, None, None)

        # Явно добавляем кредиты, чтобы списание прошло
        await repo.add_user_credits(user_id, 40)  # теперь balance ≥ 40

        result = await repo.deduct_credits(user_id, 20)
        assert result is True

        profile = await user_repo.get_profile_data(user_id)
        assert (
            profile["balance"] == 60
        )  # 40 (free) + 40 (paid) = 80, после deduct_credits(20): 80 - 20 = 60

        # Попытка списать больше, чем доступно
        result_false = await repo.deduct_credits(user_id, 100)
        assert result_false is False
