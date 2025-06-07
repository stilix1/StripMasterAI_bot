from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from utils import markups
from utils.i18n import t, get_user_language


async def reply_start(message: types.Message):
    if message.text == "💼Menu":
        user_id = str(message.from_user.id)
        repo_user = message.bot["repo_user"]
        user_lang = await get_user_language(user_id, repo_user)
        caption = t(user_lang, "captions_menu")
        await message.answer(
            caption,
            reply_markup=markups.create_menu_keyboard(user_lang),
            parse_mode="Markdown",
        )


async def lang_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = callback.data
    repo_user = callback.bot["repo_user"]
    await repo_user.update_language(user_id, user_lang)
    await callback.message.delete()
    caption = t(user_lang, "captions_menu")
    await callback.message.answer(
        caption,
        reply_markup=markups.create_menu_keyboard(user_lang),
        parse_mode="Markdown",
    )


async def terms_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]
    user_lang = await get_user_language(user_id, repo_user)

    if callback.data == "terms_yes":
        caption = t(user_lang, "captions_menu")
        await callback.message.edit_text(
            caption,
            reply_markup=markups.create_menu_keyboard(user_lang),
            parse_mode="Markdown",
        )
    else:
        caption = t(user_lang, "captions_terms_no")
        await callback.message.edit_text(caption)


async def back_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]
    user_lang = await get_user_language(user_id, repo_user)
    caption = t(user_lang, "captions_menu")
    await callback.message.edit_text(
        caption,
        reply_markup=markups.create_menu_keyboard(user_lang),
        parse_mode="Markdown",
    )


async def profile_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]
    user_lang = await get_user_language(user_id, repo_user)
    data = await repo_user.get_profile_data(user_id)
    text = t(
        user_lang,
        "captions_profile",
        username=data["username"],
        user_id=user_id,
        balance=data["balance"],
        ref_balance=data["ref_balance"],
        ref_link=data["ref_link"],
        processing=data["balance"] // 20,
    )
    await callback.message.edit_text(
        text, reply_markup=markups.create_profile_keyboard(user_lang)
    )


async def referral_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]
    user_lang = await get_user_language(user_id, repo_user)
    data = await repo_user.get_profile_data(user_id)
    text = t(
        user_lang,
        "captions_ref",
        balance=data["balance"],
        ref_balance=data["ref_balance"],
        ref_link=data["ref_link"],
        processing=data["balance"] // 20,
    )
    await callback.message.edit_text(
        text, reply_markup=markups.create_ref_keyboard(user_lang)
    )


def register_menu_handlers(dp: Dispatcher):
    dp.register_message_handler(reply_start, content_types=["text"], state="*")
    dp.register_callback_query_handler(
        lang_callback, lambda c: c.data in ["ru", "en", "chinese", "fr", "es"]
    )
    dp.register_callback_query_handler(
        terms_callback, lambda c: c.data in ["terms_yes", "terms_no"]
    )
    dp.register_callback_query_handler(
        back_callback, lambda c: c.data == "back", state="*"
    )
    dp.register_callback_query_handler(profile_callback, lambda c: c.data == "profile")
    dp.register_callback_query_handler(
        referral_callback, lambda c: c.data == "referral"
    )
