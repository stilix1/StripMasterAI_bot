import asyncio
import logging

import asyncpg

DB_USER = 'postgres'
DB_PASSWORD = '666'
DB_DATABASE = 'postgres'
DB_HOST = 'localhost'

CREATE_TABLES_SQL = """
-- Команды для создания таблиц и схем
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS data;

CREATE TABLE IF NOT EXISTS core.users (
    id BIGINT PRIMARY KEY,  -- Указываем, что тип данных BIGINT
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    language_code VARCHAR(10),
    selected_language VARCHAR(10),
    is_premium BOOLEAN DEFAULT FALSE,
    ref_link VARCHAR(255),
    invited_by BIGINT  -- BIGINT, совместимо с `id`
);

CREATE TABLE IF NOT EXISTS core.credits (
    user_id BIGINT PRIMARY KEY REFERENCES core.users(id),  -- Теперь здесь BIGINT
    credits_paid INTEGER DEFAULT 0,
    credits_free INTEGER DEFAULT 0,
    credits_ref INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS core.invites (
    user_id BIGINT REFERENCES core.users(id),  -- BIGINT, совместимо с `id`
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    invited BIGINT  -- BIGINT, совместимо с `id`
);

CREATE TABLE IF NOT EXISTS data.transactions (
    id BIGINT PRIMARY KEY,
    user_id BIGINT REFERENCES core.users(id),  -- Теперь BIGINT
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50),
    amount INTEGER
);

CREATE TABLE IF NOT EXISTS data.processings (
    id UUID PRIMARY KEY,
    user_id BIGINT REFERENCES core.users(id),  -- Теперь BIGINT
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50),
    paid BOOLEAN
);
"""


async def create_pool():
    return await asyncpg.create_pool(user=DB_USER, password=DB_PASSWORD,
                                     database=DB_DATABASE, host=DB_HOST)


async def add_user(pool, user_id, username, language_code, is_premium, ref_link=None, invited_by=None):
    async with pool.acquire() as conn:
        try:
            # Добавление или обновление пользователя
            await conn.execute('''
                INSERT INTO core.users (id, username, language_code, selected_language, is_premium, ref_link, invited_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    language_code = EXCLUDED.language_code,
                    is_premium = EXCLUDED.is_premium,
                    ref_link = EXCLUDED.ref_link,
                    invited_by = EXCLUDED.invited_by;
            ''', int(user_id), username, language_code, language_code, is_premium, ref_link,
                               int(invited_by) if invited_by else None)

            # Добавление записи в таблицу credits
            await conn.execute('''
                INSERT INTO core.credits (user_id, credits_free, credits_paid, credits_ref)
                VALUES ($1, 40, 0, 0)
                ON CONFLICT (user_id) DO NOTHING;
            ''', int(user_id))

        except Exception as e:
            logging.error(f"Error adding/updating user in DB: {e}")
            raise


async def add_referral_credits(pool, inviter_id):
    async with pool.acquire() as conn:
        try:
            # Увеличение credits_ref для пригласившего пользователя
            await conn.execute('''
                UPDATE core.credits
                SET credits_ref = credits_ref + 20
                WHERE user_id = $1;
            ''', int(inviter_id))
            logging.info(f"Referral credits added: {inviter_id} gets 20 credits")
        except Exception as e:
            logging.error(f"Error adding referral credits in DB: {e}")
            raise


async def set_language(pool, user_id, language):
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE core.users SET selected_language = $1 WHERE id = $2;
        ''', language, user_id)


async def update_user_language(pool, user_id, language_code):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE core.users SET selected_language = $1 WHERE id = $2",
            language_code, int(user_id)
        )


async def create_tables():
    conn = await asyncpg.connect(user=DB_USER, password=DB_PASSWORD,
                                 database=DB_DATABASE, host=DB_HOST)
    try:
        await conn.execute(CREATE_TABLES_SQL)
        print("Таблицы созданы")
    finally:
        await conn.close()


async def get_user_language(pool, user_id):
    async with pool.acquire() as conn:
        # Выполните запрос к базе данных, чтобы получить выбранный язык пользователя
        result = await conn.fetchrow(
            "SELECT selected_language FROM core.users WHERE id = $1",
            int(user_id)  # Приводим user_id к типу int, если ваш id теперь BIGINT
        )
        if result:
            return result['selected_language']  # Возвращает выбранный язык, если пользователь найден
        else:
            return None  # Возвращает None, если пользователь не найден


async def record_invitation(pool, inviter_id, new_user_id):
    async with pool.acquire() as conn:
        try:
            await conn.execute('''
                INSERT INTO core.invites (user_id, invited)
                VALUES ($1, $2);
            ''', int(inviter_id), int(new_user_id))
            logging.info(f"Invitation recorded: {inviter_id} invited {new_user_id}")
        except Exception as e:
            logging.error(f"Error recording invitation in DB: {e}")
            raise


async def record_transaction(pool, transaction_id, user_id, status, amount):
    async with pool.acquire() as conn:
        try:
            await conn.execute('''
                INSERT INTO data.transactions (id, user_id, status, amount)
                VALUES ($1, $2, $3, $4);
            ''', int(transaction_id), int(user_id), status, amount)
            logging.info(
                f"Transaction recorded: {transaction_id} for user {user_id} with status {status} and amount {amount}")
        except Exception as e:
            logging.error(f"Error recording transaction in DB: {e}")
            raise


async def add_user_credits(pool, user_id, amount):
    async with pool.acquire() as conn:
        try:
            await conn.execute('''
                UPDATE core.credits
                SET credits_paid = credits_paid + $2
                WHERE user_id = $1;
            ''', int(user_id), amount)
            logging.info(f"Credits added: {user_id} gets {amount} credits")
        except Exception as e:
            logging.error(f"Error adding credits in DB: {e}")
            raise


async def deduct_credits(pool, user_id, amount):
    async with pool.acquire() as conn:
        # Получаем текущие кредиты пользователя
        credits = await conn.fetchrow('''
            SELECT credits_paid, credits_free, credits_ref FROM core.credits WHERE user_id = $1;
        ''', int(user_id))

        if credits:
            paid, free, ref = credits['credits_paid'], credits['credits_free'], credits['credits_ref']

            # Проверяем общее количество доступных кредитов
            total_credits = paid + free + ref
            if total_credits < amount:
                return False  # Недостаточно кредитов для выполнения операции

            # Расчет новых значений
            new_free = max(free - amount, 0)
            amount -= (free - new_free)
            new_ref = max(ref - amount, 0) if amount > 0 else ref
            amount -= (ref - new_ref)
            new_paid = max(paid - amount, 0) if amount > 0 else paid

            # Обновление записей кредитов в базе данных
            await conn.execute('''
                UPDATE core.credits SET credits_paid = $2, credits_free = $3, credits_ref = $4 WHERE user_id = $1;
            ''', int(user_id), new_paid, new_free, new_ref)
            return True
        else:
            # Если записи не было, можно рассмотреть вариант создания новой записи или возврата ошибки
            return False


async def get_user_profile_data(pool, user_id):
    async with pool.acquire() as conn:
        # Извлекаем данные о пользователе из таблицы core.users и core.credits
        query = """
        SELECT u.username, u.created_at, u.ref_link, 
                c.credits_free,
               (c.credits_paid + c.credits_free + c.credits_ref) as balance
        FROM core.users u
        LEFT JOIN core.credits c ON u.id = c.user_id
        WHERE u.id = $1;
        """
        result = await conn.fetchrow(query, int(user_id))
        if result:
            return {
                'username': result['username'],
                'created_at': result['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'ref_link': result['ref_link'],
                'balance': result['balance'],
                'ref_balance': result['credits_free']
            }
        else:
            return None  # В случае отсутствия пользователя в базе


async def get_referral_link(pool, user_id):
    async with pool.acquire() as conn:
        # Выполните запрос к базе данных, чтобы получить реферальную ссылку пользователя
        result = await conn.fetchrow(
            "SELECT ref_link FROM core.users WHERE id = $1",
            int(user_id)  # Приводим user_id к типу int, если ваш id теперь BIGINT
        )
        if result:
            return result['ref_link']  # Возвращает реферальную ссылку, если пользователь найден
        else:
            return None  # Возвращает None, если пользователь не найден или ссылка не задана


# Запускаем создание таблиц
loop = asyncio.get_event_loop()
loop.run_until_complete(create_tables())
