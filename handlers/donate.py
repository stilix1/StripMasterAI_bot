import asyncio
from aiogram import Dispatcher, types

from utils import markups, settings
from utils.i18n import t, get_user_language


async def donate_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]

    user_lang = await get_user_language(user_id, repo_user)
    ikb_donate = markups.create_donate_keyboard(user_lang)

    caption = t(user_lang, "captions_donate")
    await callback.message.edit_text(text=caption, reply_markup=ikb_donate)


async def ref_stats_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]
    repo_referral = callback.bot["repo_referral"]

    user_lang = await get_user_language(user_id, repo_user)
    referrals, total_ref_credit = await repo_referral.get_referral_stats(user_id)

    # Пример без total_spent, можно расширить если нужно
    message = t(
        user_lang,
        "referral_stats_template",
        referrals=referrals,
        total_spent="—",
        total_referral_credit=total_ref_credit,
    )

    await callback.message.edit_text(
        text=message, reply_markup=markups.create_back_keyboard(user_lang)
    )


async def handle_pay_amount(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]

    user_lang = await get_user_language(user_id, repo_user)
    amount = int(callback.data.split("_")[1])

    keyboard = markups.create_paymont2_keyboard(user_lang, amount)
    await callback.message.edit_text(
        text=t(user_lang, "create_url_succs"), reply_markup=keyboard
    )


async def handle_payment_method_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]
    payment_service = callback.bot["payment_service"]

    user_lang = await get_user_language(user_id, repo_user)

    _, method, amount = callback.data.split("_")
    amount = int(amount)

    text, order_id = await payment_service.process_payment_command(
        callback, amount, user_lang, method
    )

    await callback.message.answer(text)

    if order_id:
        status_msg = await callback.message.answer(
            t(user_lang, "task_status", status="processing", current_time="—")
        )

        asyncio.create_task(
            payment_service.monitor_payment(
                order_id,
                settings.RUKASSA_SHOP_ID,
                settings.RUKASSA_TOKEN,
                status_msg.chat.id,
                status_msg.message_id,
                user_id,
                amount,
                user_lang,
                order_id,
                method,
            )
        )


def register_donate_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(donate_callback, lambda c: c.data == "donate")
    dp.register_callback_query_handler(
        ref_stats_callback, lambda c: c.data == "ref_stats"
    )
    dp.register_callback_query_handler(
        handle_pay_amount, lambda c: c.data.startswith("donate_")
    )
    dp.register_callback_query_handler(
        handle_payment_method_callback, lambda c: c.data.startswith("pay_")
    )
