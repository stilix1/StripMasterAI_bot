import asyncpg


class SystemRepository:
    def __init__(self, pool=None):
        self.pool = pool

    @staticmethod
    async def create_tables(pool):
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE SCHEMA IF NOT EXISTS core;
                CREATE SCHEMA IF NOT EXISTS data;

                CREATE TABLE IF NOT EXISTS core.users (
                    serial_id SERIAL PRIMARY KEY,
                    id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    language_code VARCHAR(10),
                    selected_language VARCHAR(10),
                    is_premium BOOLEAN DEFAULT FALSE,
                    ref_link VARCHAR(255),
                    invited_by BIGINT
                );

                CREATE TABLE IF NOT EXISTS core.credits (
                    user_id BIGINT PRIMARY KEY REFERENCES core.users(id),
                    credits_paid INTEGER DEFAULT 0,
                    credits_free INTEGER DEFAULT 0,
                    credits_ref INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS core.invites (
                    user_id BIGINT REFERENCES core.users(id),
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    invited BIGINT
                );

                CREATE TABLE IF NOT EXISTS data.transactions (
                    id BIGINT PRIMARY KEY,
                    user_id BIGINT REFERENCES core.users(id),
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50),
                    amount INTEGER
                );

                CREATE TABLE IF NOT EXISTS data.processings (
                    id UUID PRIMARY KEY,
                    user_id BIGINT REFERENCES core.users(id),
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50),
                    paid BOOLEAN
                );

                CREATE TABLE IF NOT EXISTS data.referral_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES core.users(id),
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    amount INTEGER,
                    status VARCHAR(50)
                );
            """
            )
            print("✅ Таблицы успешно созданы")

    @staticmethod
    async def create_pool(user, password, database, host):
        return await asyncpg.create_pool(
            user=user, password=password, database=database, host=host
        )
