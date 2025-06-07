import os
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from utils import markups, prompts
from utils.i18n import t, get_user_language


class PhotoStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_bust_size = State()


async def send_photo_api_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    repo_user = callback.bot["repo_user"]
    user_lang = await get_user_language(user_id, repo_user)

    # 1. Инструкция
    caption = t(user_lang, "captions_send_photo_api")
    await callback.message.edit_text(caption, parse_mode="Markdown")

    # 2. Запрос фото
    msg = await callback.message.bot.send_message(
        chat_id=callback.message.chat.id,
        text=t(user_lang, "please_send_photo"),  # <- добавь этот ключ в YAML если нет
        reply_markup=markups.create_cancel_keyboard(user_lang),
    )
    await state.update_data(photo_request_message_id=msg.message_id)
    await PhotoStates.waiting_for_photo.set()


async def handle_photo(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    repo_user = message.bot["repo_user"]
    user_lang = await get_user_language(user_id, repo_user)

    data = await state.get_data()
    request_id = data.get("photo_request_message_id")
    if request_id:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=request_id)

    file_info = await message.bot.get_file(message.photo[-1].file_id)
    file_path = file_info.file_path

    os.makedirs("./tmp/files/photos", exist_ok=True)
    file_name = os.path.join(
        os.getcwd(), "./tmp/files/photos", os.path.basename(file_path)
    )
    await message.bot.download_file(file_path, file_name)
    await state.update_data(photo_path=file_name)

    ikb_bust = markups.create_bust_size_keyboard(user_lang)
    msg = await message.answer(
        t(user_lang, "captions_bust_size"), reply_markup=ikb_bust
    )
    await state.update_data(bust_size_message_id=msg.message_id)
    await PhotoStates.waiting_for_bust_size.set()


async def handle_bust_size_selection(callback: types.CallbackQuery, state: FSMContext):
    bust_size = callback.data
    user_id = str(callback.from_user.id)

    repo_user = callback.bot["repo_user"]
    repo_transaction = callback.bot["repo_transaction"]
    payment_service = callback.bot["payment_service"]
    user_lang = await get_user_language(user_id, repo_user)

    await state.update_data(bust_size=bust_size)
    data = await state.get_data()
    bust_msg_id = data.get("bust_size_message_id")
    if bust_msg_id:
        await callback.message.bot.delete_message(callback.message.chat.id, bust_msg_id)

    selected_preset = prompts.get_prompt("prompt_women")
    photo_path = data["photo_path"]
    bust_size_text = prompts.get_bust(bust_size)

    process_message = await callback.message.answer(
        t(user_lang, "processing_status", status="⏳", current_time="...")
    )

    if await repo_transaction.deduct_credits(user_id, 20):
        final_prompt = f"{selected_preset}, {bust_size_text}"
        result_path = await payment_service.paymont_create_picture(
            photo_path, process_message, final_prompt
        )

        if result_path:
            with open(result_path, "rb") as photo:
                await callback.message.answer_photo(photo=photo)
            os.remove(result_path)
        else:
            await callback.message.answer(t(user_lang, "paymont_edit_error"))
    else:
        img = callback.bot["image_editor"].edit_photo(photo_path)
        if img:
            with open(img, "rb") as photo:
                await callback.message.answer_photo(
                    photo=photo, caption=t(user_lang, "captions_watermark_succs")
                )
            os.remove(img)
        else:
            await callback.message.answer(
                t(user_lang, "paymont_edit_error"),
                reply_markup=markups.create_back_keyboard(user_lang),
            )

    os.remove(photo_path)
    await state.finish()


async def cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    repo_user = callback.bot["repo_user"]
    user_lang = await get_user_language(str(callback.from_user.id), repo_user)

    await state.finish()
    ikb_menu = markups.create_menu_keyboard(user_lang)
    await callback.message.edit_text(
        text=t(user_lang, "captions_menu"), reply_markup=ikb_menu
    )


def register_photo_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        send_photo_api_callback, lambda c: c.data == "send_photo_api", state="*"
    )
    dp.register_message_handler(
        handle_photo,
        content_types=types.ContentType.PHOTO,
        state=PhotoStates.waiting_for_photo,
    )
    dp.register_callback_query_handler(
        handle_bust_size_selection,
        lambda c: c.data.startswith("bust_"),
        state=PhotoStates.waiting_for_bust_size,
    )
    dp.register_callback_query_handler(
        cancel_callback, lambda c: c.data == "cancel", state="*"
    )
