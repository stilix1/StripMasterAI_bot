import asyncio

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.markdown import text

from utils import markups, settings
from utils.i18n import t


class NewsletterState(StatesGroup):
    waiting_for_message = State()


async def send_stats(message: types.Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.reply("You do not have permission to use this command.")
        return

    repo_user = message.bot["repo_user"]
    repo_ref = message.bot["repo_referral"]

    total_users = await repo_user.get_total_users()
    users_last_week = await repo_user.get_users_last_week()
    users_last_month = await repo_user.get_users_last_month()
    new_users_count = await repo_ref.get_new_users_from_referral()
    users_with_balance = await repo_ref.get_users_with_balance_from_referral()
    total_referral_topups = await repo_ref.get_total_referral_topups()

    stats_message = text(
        f"📊 Статистика бота:\n\n"
        f"👥 Новые пользователи по реферальной ссылке: {new_users_count}\n"
        f"💳 Пользователи, пополнившие баланс: {users_with_balance}\n"
        f"💰 Общая сумма пополнений по рефералам: {total_referral_topups} единиц\n"
        f"👤 Всего пользователей: {total_users}\n"
        f"📅 За неделю: {users_last_week}\n"
        f"🗓️ За месяц: {users_last_month}\n"
    )

    await message.reply(stats_message)

    # отправка списка пользователей
    user_details = await repo_user.get_all_users()
    file_path = "users.txt"
    with open(file_path, "w", encoding="utf-8") as file:
        for user in user_details:
            file.write(
                f"DB ID: {user['serial_id']}, Telegram ID: {user['id']}, "
                f"Username: {user['username']}, Created at: {user['created_at']}, "
                f"Language: {user['selected_language']}, Ref Link: {user['ref_link']}, "
                f"Invited By: {user['invited_by']}, Credits Free: {user['credits_free']}, "
                f"Credits Paid: {user['credits_paid']}, Credits Ref: {user['credits_ref']}\n"
            )

    with open(file_path, "rb") as file:
        await message.bot.send_document(message.chat.id, file, caption="User Details")


async def handle_ref_info(message: types.Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return

    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.reply("Использование: /ref_info id")
        return

    user_id = int(command_parts[1])
    repo_ref = message.bot["repo_referral"]

    try:
        new_users_count = await repo_ref.get_new_users_from_referral_by_id(user_id)
        users_with_balance = await repo_ref.get_users_with_balance_from_referral_by_id(
            user_id
        )
        total_referral_topups = await repo_ref.get_total_referral_topups_by_id(user_id)

        message_text = (
            f"Информация о пользователе с ID {user_id}:\n"
            f"🔗 Кол-во рефералов: {new_users_count}\n"
            f"💸 С пополнением: {users_with_balance}\n"
            f"💰 Общая сумма: {total_referral_topups}"
        )
        await message.reply(message_text)

    except Exception as e:
        await message.reply(f"Ошибка при получении информации: {str(e)}")


async def newsletter_command(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    repo_user = message.bot["repo_user"]
    user_lang = await repo_user.get_language(user_id) or "en"

    markup = markups.create_back_keyboard()
    await message.answer(
        (
            t("newsletter_prompt")
            if t("newsletter_prompt")
            else "Введите текст рассылки. Для отмены нажмите кнопку ниже."
        ),
        reply_markup=markup,
    )
    await NewsletterState.waiting_for_message.set()


async def process_newsletter_text(message: types.Message, state: FSMContext):
    newsletter_text = message.text
    repo_user = message.bot["repo_user"]

    users = await repo_user.get_all_users()
    success_msg = "✅ Успешно отправлено:\n"
    failure_msg = "❌ Не удалось отправить:\n"

    for user in users:
        try:
            await message.bot.send_message(user["id"], newsletter_text)
            success_msg += f"{user['id']} 👍\n"
            await asyncio.sleep(0.05)
        except Exception:
            failure_msg += f"{user['id']} 👎\n"
            continue

    await message.reply(success_msg)
    await message.reply(failure_msg)
    await state.finish()


def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(send_stats, commands=["stats"], state="*")
    dp.register_message_handler(handle_ref_info, commands=["ref_info"], state="*")
    dp.register_message_handler(
        newsletter_command,
        commands=["newsletter"],
        user_id=settings.ADMIN_IDS,
        state="*",
    )
    dp.register_message_handler(
        process_newsletter_text,
        state=NewsletterState.waiting_for_message,
        content_types=types.ContentType.TEXT,
    )
