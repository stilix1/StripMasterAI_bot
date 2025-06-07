from datetime import datetime, timedelta


class UserRepository:
    def __init__(self, pool):
        self.pool = pool

    async def add_user(
        self,
        user_id,
        username,
        language_code,
        is_premium,
        ref_link=None,
        invited_by=None,
    ):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO core.users (id, username, language_code, selected_language, is_premium, ref_link, invited_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    language_code = EXCLUDED.language_code,
                    is_premium = EXCLUDED.is_premium,
                    ref_link = EXCLUDED.ref_link,
                    invited_by = EXCLUDED.invited_by;
                """,
                int(user_id),
                username,
                language_code,
                language_code,
                is_premium,
                ref_link,
                int(invited_by) if invited_by else None,
            )

            await conn.execute(
                """
                INSERT INTO core.credits (user_id, credits_free, credits_paid, credits_ref)
                VALUES ($1, 40, 0, 0)
                ON CONFLICT (user_id) DO NOTHING;
                """,
                int(user_id),
            )

    async def get_language(self, user_id):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT selected_language FROM core.users WHERE id = $1", int(user_id)
            )
            return result["selected_language"] if result else None

    async def update_language(self, user_id, language_code):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE core.users SET selected_language = $1 WHERE id = $2",
                language_code,
                int(user_id),
            )

    async def get_profile_data(self, user_id):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT u.username, u.created_at, u.ref_link,
                       c.credits_ref,
                       (c.credits_paid + c.credits_free + c.credits_ref) as balance
                FROM core.users u
                LEFT JOIN core.credits c ON u.id = c.user_id
                WHERE u.id = $1;
                """,
                int(user_id),
            )
            if result:
                return {
                    "username": result["username"],
                    "created_at": result["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    "ref_link": result["ref_link"],
                    "balance": result["balance"],
                    "ref_balance": result["credits_ref"],
                }
            return None

    async def get_referral_link(self, user_id):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT ref_link FROM core.users WHERE id = $1", int(user_id)
            )
            return result["ref_link"] if result else None

    async def get_total_users(self):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM core.users")

    async def get_users_last_week(self):
        async with self.pool.acquire() as conn:
            one_week_ago = datetime.now() - timedelta(weeks=1)
            return await conn.fetchval(
                "SELECT COUNT(*) FROM core.users WHERE created_at >= $1", one_week_ago
            )

    async def get_users_last_month(self):
        async with self.pool.acquire() as conn:
            one_month_ago = datetime.now() - timedelta(days=30)
            return await conn.fetchval(
                "SELECT COUNT(*) FROM core.users WHERE created_at >= $1", one_month_ago
            )

    async def get_all_users(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT u.serial_id, u.id, u.username, u.created_at, u.selected_language, u.ref_link, u.invited_by,
                       c.credits_free, c.credits_paid, c.credits_ref
                FROM core.users u
                LEFT JOIN core.credits c ON u.id = c.user_id;
            """
            )
