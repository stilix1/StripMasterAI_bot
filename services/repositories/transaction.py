import logging


class TransactionRepository:
    def __init__(self, pool):
        self.pool = pool

    async def record_transaction(self, transaction_id, user_id, status, amount):
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO data.transactions (id, user_id, status, amount)
                    VALUES ($1, $2, $3, $4);
                    """,
                    int(transaction_id),
                    int(user_id),
                    status,
                    amount,
                )
                logging.info(
                    f"Transaction recorded: user {user_id},"
                    f" amount {amount},"
                    f" status {status}"
                )
            except Exception as e:
                logging.error(f"Error recording transaction: {e}")
                raise

    async def record_referral_transaction(self, user_id, amount, status):
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO data.referral_transactions (user_id, amount, status)
                    VALUES ($1, $2, $3);
                    """,
                    int(user_id),
                    amount,
                    status,
                )
                logging.info(
                    f"Referral transaction: user {user_id} credited with {amount}"
                )
            except Exception as e:
                logging.error(f"Error recording referral transaction: {e}")
                raise

    async def add_user_credits(self, user_id, amount):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE core.credits
                SET credits_paid = credits_paid + $2
                WHERE user_id = $1;
                """,
                int(user_id),
                amount,
            )

    async def deduct_credits(self, user_id, amount):
        async with self.pool.acquire() as conn:
            credits = await conn.fetchrow(
                """
                SELECT credits_paid, credits_free, credits_ref
                FROM core.credits
                WHERE user_id = $1;
                """,
                int(user_id),
            )
            if not credits:
                return False

            paid, free, ref = (
                credits["credits_paid"],
                credits["credits_free"],
                credits["credits_ref"],
            )
            total = paid + free + ref

            if total < amount:
                return False

            new_free = max(free - amount, 0)
            amount -= free - new_free
            new_ref = max(ref - amount, 0) if amount > 0 else ref
            amount -= ref - new_ref
            new_paid = max(paid - amount, 0) if amount > 0 else paid

            await conn.execute(
                """
                UPDATE core.credits
                SET credits_paid = $2, credits_free = $3, credits_ref = $4
                WHERE user_id = $1;
                """,
                int(user_id),
                new_paid,
                new_free,
                new_ref,
            )
            return True
