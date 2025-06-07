import pytest

from services.repositories.user import UserRepository


@pytest.mark.asyncio
class TestUserRepository:

    @pytest.fixture
    async def repo(self, db_pool):
        return UserRepository(db_pool)

    async def test_add_user_creates_new(self, repo, user_id_sequence):
        user_id = next(user_id_sequence)
        # Делаем username уникальным, чтобы не было повторов
        await repo.add_user(
            user_id=user_id,
            username=f"user_{user_id}",
            language_code="en",
            is_premium=False,
            ref_link="ref_link_test",
            invited_by=None,
        )
        language = await repo.get_language(user_id)
        # После создания selected_language == language_code ("en")
        assert language == "en"

    async def test_update_user_language(self, repo, user_id_sequence):
        user_id = next(user_id_sequence)
        await repo.add_user(
            user_id=user_id,
            username=f"user_{user_id}",
            language_code="en",
            is_premium=False,
            ref_link=None,
            invited_by=None,
        )
        # Обновляем язык на "ru"
        await repo.update_language(user_id, "ru")
        language = await repo.get_language(user_id)
        assert language == "ru"

    async def test_get_total_users(self, repo, user_id_sequence):
        user_id = next(user_id_sequence)
        await repo.add_user(
            user_id=user_id,
            username=f"user_{user_id}",
            language_code="en",
            is_premium=False,
            ref_link=None,
            invited_by=None,
        )
        total = await repo.get_total_users()
        # Должен быть хотя бы 1 (минимум тот, что только что добавили)
        assert total >= 1

    async def test_get_users_last_week_and_month(self, repo, user_id_sequence):
        user_id = next(user_id_sequence)
        await repo.add_user(
            user_id=user_id,
            username=f"user_{user_id}",
            language_code="en",
            is_premium=False,
            ref_link=None,
            invited_by=None,
        )
        week_count = await repo.get_users_last_week()
        month_count = await repo.get_users_last_month()
        assert week_count >= 1
        assert month_count >= 1

    async def test_get_all_users_returns_list(self, repo, user_id_sequence):
        user_id = next(user_id_sequence)
        await repo.add_user(
            user_id=user_id,
            username=f"user_{user_id}",
            language_code="en",
            is_premium=False,
            ref_link=None,
            invited_by=None,
        )
        users = await repo.get_all_users()
        assert any(u["id"] == user_id for u in users)

    async def test_get_profile_data(self, repo, user_id_sequence):
        user_id = next(user_id_sequence)
        await repo.add_user(
            user_id=user_id,
            username=f"user_{user_id}",
            language_code="en",
            is_premium=False,
            ref_link=None,
            invited_by=None,
        )
        profile = await repo.get_profile_data(user_id)
        assert profile["username"] == f"user_{user_id}"
        assert isinstance(profile["balance"], int)
