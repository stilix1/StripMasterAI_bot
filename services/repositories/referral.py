class ReferralRepository:
    def __init__(self, pool):
        self.pool = pool

    async def record_invitation(self, inviter_id, new_user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO core.invites (user_id, invited)
                VALUES ($1, $2);
                """,
                int(inviter_id),
                int(new_user_id),
            )

    async def add_referral_credits(self, inviter_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE core.credits
                SET credits_free = credits_ref + 20
                WHERE user_id = $1;
                """,
                int(inviter_id),
            )

    async def get_referral_stats(self, user_id):
        async with self.pool.acquire() as conn:
            user_id = int(user_id)
            referrals = await conn.fetchval(
                "SELECT COUNT(*) FROM core.invites WHERE user_id = $1;", user_id
            )
            total_referral_credit = await conn.fetchval(
                """
                SELECT COALESCE(SUM(rt.amount), 0)
                FROM data.referral_transactions rt
                JOIN core.users u ON rt.user_id = u.id
                WHERE u.id IN (
                    SELECT invited FROM core.invites WHERE user_id = $1
                );
                """,
                user_id,
            )
        return referrals, total_referral_credit

    async def get_new_users_from_referral(self):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM core.users WHERE invited_by IS NOT NULL;"
            )

    async def get_new_users_from_referral_by_id(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM core.users WHERE invited_by = $1;", int(user_id)
            )

    async def get_users_with_balance_from_referral(self):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(DISTINCT u.id)
                FROM core.users u
                JOIN data.referral_transactions rt ON u.id = rt.user_id;
                """
            )

    async def get_users_with_balance_from_referral_by_id(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(DISTINCT u.id)
                FROM core.users u
                JOIN data.referral_transactions rt ON u.id = rt.user_id
                WHERE u.invited_by = $1;
                """,
                int(user_id),
            )

    async def get_total_referral_topups(self):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COALESCE(SUM(rt.amount), 0) FROM data.referral_transactions rt;"
            )

    async def get_total_referral_topups_by_id(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COALESCE(SUM(rt.amount), 0)
                FROM data.referral_transactions rt
                JOIN core.users u ON rt.user_id = u.id
                WHERE u.invited_by = $1;
                """,
                int(user_id),
            )

    async def get_referrer_id(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT invited_by FROM core.users WHERE id = $1;", int(user_id)
            )
