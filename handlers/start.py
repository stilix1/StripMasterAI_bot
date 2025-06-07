from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from utils import markups, settings
from utils.i18n import t, get_user_language


def generate_referral_link(user_id):
    return f"https://t.me/{settings.bot_name}?start={user_id}"


async def start_command(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "unknown"
    ref_code = message.get_args()

    repo_user = message.bot["repo_user"]
    repo_ref = message.bot["repo_referral"]

    user_lang = await repo_user.get_language(user_id)
    if not user_lang:
        ref_link = generate_referral_link(user_id)
        invited_by = ref_code if ref_code else None
        await repo_user.add_user(user_id, username, "en", False, ref_link, invited_by)

        if invited_by:
            await repo_ref.record_invitation(invited_by, user_id)
            await repo_ref.add_referral_credits(invited_by)

        caption = "Welcome! Please select your language."
        await message.answer(caption, reply_markup=markups.ikb_start)
        return

    user_lang = await get_user_language(user_id, repo_user)
    if message.chat.id in settings.ADMIN_IDS:
        text = (
            "Welcome!\n/menu - menu\n/language - change language\n\n"
            "Admin menu:\n/ref_info - рефералы по ID\n/stats - статистика\n/newsletter - рассылка"
        )
    else:
        text = "Welcome!\n/menu - menu\n/language - change language"

    await message.answer(text, reply_markup=markups.replay_keyboard())

    caption = t(user_lang, "captions_terms")
    await message.answer(
        caption,
        reply_markup=markups.create_terms_keyboard(user_lang),
        parse_mode="Markdown",
    )


async def language_command(message: types.Message):
    await message.answer("Please select your language.", reply_markup=markups.ikb_start)


def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_command, commands=["start"], state="*")
    dp.register_message_handler(language_command, commands=["language"], state="*")
