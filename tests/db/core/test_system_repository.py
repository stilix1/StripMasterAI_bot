import asyncpg
import pytest

from services.repositories.system import SystemRepository


@pytest.mark.asyncio
async def test_create_tables_and_pool():
    pool = await SystemRepository.create_pool(
        user="postgres", password="postgres", database="postgres", host="localhost"
    )
    assert isinstance(pool, asyncpg.pool.Pool)

    # Создаём таблицы
    await SystemRepository.create_tables(pool)

    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema='core' AND table_name='users');"
        )
        assert exists

    await pool.close()
