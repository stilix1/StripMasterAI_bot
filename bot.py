import asyncio
import base64
import logging
import os
import time
from datetime import datetime

import aiogram
import requests
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.dispatcher.filters import state
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.utils.markdown import bold, text

import db
import edit_img
import markups
import paymont
import settings
import translations as tr

TOKEN = settings.Token
RUKASSA_TOKEN = settings.RUKASSA_TOKEN

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

user_lang = None


class NewsletterState(StatesGroup):
    waiting_for_message = State()


class PhotoStates(StatesGroup):
    waiting_for_preset = State()
    waiting_for_photo = State()
    waiting_for_bust_size = State()


# Commands handlers ___________________________________________________________
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or 'unknown'
    ref_code = message.get_args()  # Получаем реферальный код из аргументов команды /start

    user_lang = await db.get_user_language(dp['db_pool'], user_id)

    replay_keyboard = markups.replay_keyboard()

    if message.chat.id in settings.ADMIN_IDS:
        text = f'''
Welcome!
/menu - menu
/language - change language


Admin menu:
/ref_info - статистка по рефералам по id
/stats - статистика пользователей
/newsletter - рассылка
'''
    else:
        text = 'Welcome!\n/menu - menu\n/language - change language'

    await bot.send_message(chat_id=message.chat.id,
                           text=text,
                           reply_markup=replay_keyboard)

    if not user_lang:
        ref_link = generate_referral_link(user_id)
        invited_by = ref_code if ref_code else None

        await db.add_user(dp['db_pool'], user_id, username, 'en', False, ref_link, invited_by)

        if invited_by:
            await db.record_invitation(dp['db_pool'], invited_by, user_id)
            await db.add_referral_credits(dp['db_pool'], invited_by)

        caption = "Welcome! Please select your language."
        await bot.send_message(chat_id=message.chat.id,
                               text=caption,
                               reply_markup=markups.ikb_start)
    else:
        caption = tr.translations_list[user_lang]['captions_terms']
        ikb_terms = markups.create_terms_keyboard(user_lang)
        await bot.send_message(chat_id=message.chat.id, text=caption,
                               reply_markup=ikb_terms,
                               parse_mode='Markdown')


@dp.message_handler(commands=['language'])
async def language_command(message: types.Message):
    user_id = str(message.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    caption = "Please select your language."

    await bot.send_message(chat_id=message.chat.id,
                           text=caption,
                           reply_markup=markups.ikb_start)


@dp.message_handler(commands=['stats'])
async def send_stats(message: types.Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.reply("You do not have permission to use this command.")
        return

    # Статистика пользователей за все время
    total_users = await db.get_total_users(dp['db_pool'])

    # Статистика новых пользователей за неделю
    users_last_week = await db.get_users_last_week(dp['db_pool'])

    # Статистика новых пользователей за месяц
    users_last_month = await db.get_users_last_month(dp['db_pool'])

    # Статистика новых пользователей по реферальной ссылке
    new_users_count = await db.get_new_users_from_referral(dp['db_pool'])

    # Статистика пользователей, перешедших по ссылке и пополнивших баланс
    users_with_balance = await db.get_users_with_balance_from_referral(dp['db_pool'])

    # Общая сумма пополнений всех пользователей по реферальной ссылке
    total_referral_topups = await db.get_total_referral_topups(dp['db_pool'])

    stats_message = text(
            f"Статистика бота:\n\n"
            f"👥 Новые пользователи по реферальной ссылке: {new_users_count}\n"
            f"💳 Пользователи, перешедшие и пополнившие баланс: {users_with_balance}\n"
            f"💰 Общая сумма пополнений по реферальной ссылке: {total_referral_topups} единиц\n"
            f"Всего пользователей: {total_users}\n",
            f"Пользователей за неделю: {users_last_week}\n",
            f"Пользователей за месяц: {users_last_month}\n"
        )

    await message.reply(stats_message)

    user_details = await db.get_all_users(dp['db_pool'])
    file_path = 'users.txt'
    with open(file_path, 'w') as file:
        for user in user_details:
            file.write(f"DB ID: {user['serial_id']}, Telegram ID: {user['id']}, Username: {user['username']}, Created at: {user['created_at']}, "
                       f"Language: {user['selected_language']}, Ref Link: {user['ref_link']}, Invited By: {user['invited_by']}, "
                       f"Credits Free: {user['credits_free']}, Credits Paid: {user['credits_paid']}, Credits Ref: {user['credits_ref']}\n")

    with open(file_path, 'rb') as file:
        await bot.send_document(message.chat.id, file, caption="User Details")


@dp.message_handler(commands=['ref_info'])
async def handle_ref_info(message: types.Message):
    # Проверяем, что команда отправлена администратором
    if message.from_user.id not in settings.ADMIN_IDS:
        return

    # Получаем айди пользователя из сообщения
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.reply("Использование: /ref_info id")
        return

    user_id = int(command_parts[1])

    try:
        # Получаем информацию о реферальной активности пользователя
        new_users_count = await db.get_new_users_from_referral_by_id(dp['db_pool'], user_id)
        users_with_balance = await db.get_users_with_balance_from_referral_by_id(dp['db_pool'], user_id)
        total_referral_topups = await db.get_total_referral_topups_by_id(dp['db_pool'], user_id)

        # Формируем сообщение с информацией
        message_text = (
            f"Информация о пользователе с ID {user_id}:\n"
            f"Количество рефералов: {new_users_count}\n"
            f"Количество пользователей с пополнением: {users_with_balance}\n"
            f"Общая сумма пополнений: {total_referral_topups}\n"
        )

        # Отправляем сообщение с информацией
        await message.reply(message_text)

    except Exception as e:
        await message.reply(f"Ошибка при получении информации: {str(e)}")


# Функция для отправки рассылки всем пользователям
async def send_newsletter_to_all_users(text):
    try:
        # Получаем список всех зарегистрированных пользователей
        users = await db.get_all_registered_users(dp['db_pool'])
        success_msg = "Успешно отправлено:\n"
        failure_msg = "Не удалось отправить:\n"

        for user_id in users:
            try:
                await bot.send_message(user_id, text)
                success_msg += f"{user_id} 👍🏻\n"
                print(f"Сообщение успешно отправлено пользователю с ID {user_id}")
                await asyncio.sleep(0.05)  # Делаем небольшую паузу между отправками
            except Exception as e:
                failure_msg += f"{user_id} 👎🏻\n"
                print(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")
                continue

        print("Рассылка завершена.")
        return success_msg, failure_msg
    except Exception as ex:
        print(f"Ошибка при выполнении рассылки: {ex}")
        return "Ошибка при выполнении рассылки", ""

    except Exception as e:
        print(f"Ошибка при получении списка пользователей из базы данных: {e}")


# Обработчик команды /newsletter для администраторов
@dp.message_handler(commands=['newsletter'], user_id=settings.ADMIN_IDS, state="*")
async def newsletter_command(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    # Отправляем сообщение с приглашением ввести текст рассылки и кнопкой для отмены
    markup = markups.create_back_keyboard(user_lang)
    await message.answer("Введите текст рассылки. Для отмены нажмите кнопку ниже.", reply_markup=markup)

    # Устанавливаем состояние FSM, ожидающее текста рассылки
    await NewsletterState.waiting_for_message.set()


# Обработчик ответа на текст рассылки
@dp.message_handler(state=NewsletterState.waiting_for_message, content_types=types.ContentType.TEXT)
async def process_newsletter_text(message: types.Message, state: FSMContext):
    # Получаем текст рассылки из сообщения
    newsletter_text = message.text

    # Отправляем рассылку всем зарегистрированным пользователям
    success_msg, failure_msg = await send_newsletter_to_all_users(newsletter_text)

    await message.reply(success_msg)
    await message.reply(failure_msg)

    # Сбрасываем состояние FSM
    await state.finish()


# Обработчик кнопки отмены рассылки
@dp.callback_query_handler(lambda query: query.data == 'cancel_newsletter')
async def cancel_newsletter(query: types.CallbackQuery):
    await query.message.answer("Рассылка отменена.")
    await query.answer()


# Menu buttons handlers ___________________________________________________________________
@dp.message_handler(content_types=["text"])
async def reply_start(message: types.Message):
    if message.text == '💼Menu':
        try:
            user_id = str(message.from_user.id)
            user_lang = await db.get_user_language(dp['db_pool'], user_id)
            if user_lang:
                translations = tr.translations_list[user_lang]

                ikb_menu = markups.create_menu_keyboard(user_lang)

                # Отправляем меню и клавиатуру
                caption = translations['captions_menu']
                await bot.send_message(chat_id=message.chat.id, text=caption, reply_markup=ikb_menu,
                                       parse_mode='Markdown')
            else:
                text = 'unset user language. Use /start'
                await bot.send_message(chat_id=message.chat.id, text=text)
        except Exception as e:
            print(f'Error! Unset user_lang: {e}')


@dp.callback_query_handler(lambda callback: callback.data in ['ru', 'en', 'chinese', 'fr', 'es'])
async def lang_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)  # Получаем ID пользователя
    user_lang = callback.data  # Язык, выбранный пользователем

    # Сохраняем выбранный язык пользователя в базе данных
    await db.update_user_language(dp['db_pool'], user_id, user_lang)

    # Удаляем предыдущее сообщение с клавиатурой выбора языка
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)

    # Получаем обновленные переводы для нового выбранного языка
    translations = tr.translations_list[user_lang]

    ikb_menu = markups.create_menu_keyboard(user_lang)

    # Отправляем фото с новым описанием и клавиатурой
    caption = translations['captions_menu']
    await bot.send_message(chat_id=callback.message.chat.id, text=caption, reply_markup=ikb_menu, parse_mode='Markdown')


@dp.callback_query_handler(lambda callback: callback.data in ['terms_yes', 'terms_no'])
async def terms_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    # Извлекаем язык пользователя
    user_lang = await db.get_user_language(dp['db_pool'], user_id)

    if callback.data == 'terms_yes':
        ikb_menu = markups.create_menu_keyboard(user_lang)
        caption = tr.translations_list[user_lang]['captions_menu']
        await bot.edit_message_text(chat_id=callback.message.chat.id,
                                    message_id=callback.message.message_id,
                                    text=caption,
                                    reply_markup=ikb_menu,
                                    parse_mode='Markdown')
    else:
        caption = tr.translations_list[user_lang]['captions_terms_no']
        await bot.edit_message_text(chat_id=callback.message.chat.id,
                                    message_id=callback.message.message_id,
                                    text=caption)


# Handler for the "Back" button
@dp.callback_query_handler(lambda callback: callback.data == 'back', state='*')
async def back_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()  # Finish the current state
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Get user language

    if user_lang is None:
        user_lang = 'en'  # Default language if not found

    ikb_menu = markups.create_menu_keyboard(user_lang)
    caption = tr.translations_list[user_lang]['captions_menu']
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=caption,
                                reply_markup=ikb_menu,
                                parse_mode='Markdown')


@dp.callback_query_handler(lambda callback: callback.data == 'profile')
async def profile_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    # Извлекаем язык пользователя
    user_lang = await db.get_user_language(dp['db_pool'], user_id)
    # Получаем данные о пользователе
    user_data = await db.get_user_profile_data(dp['db_pool'], user_id)

    profile_message = tr.translations_list[user_lang]['captions_profile'].format(username=user_data['username'],
                                                                                 user_id=user_id,
                                                                                 balance=user_data['balance'],
                                                                                 ref_balance=user_data['ref_balance'],
                                                                                 ref_link=user_data['ref_link'],
                                                                                 processing=user_data['balance'] // 20,
                                                                                 created_at=user_data['created_at'])

    ikb_profile = markups.create_profile_keyboard(user_lang)
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=profile_message,
                                reply_markup=ikb_profile)


# Profile buttons handlers _________________________________________________
def generate_referral_link(user_id):
    bot_name = settings.bot_name
    base_url = f"https://t.me/{bot_name}?start="
    referral_code = str(user_id)  # используем ID пользователя как код
    return base_url + referral_code


@dp.callback_query_handler(lambda callback: callback.data == 'referral')
async def referral_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    user_data = await db.get_user_profile_data(dp['db_pool'], user_id)
    ref_message = tr.translations_list[user_lang]['captions_ref'].format(balance=user_data['balance'],
                                                                         ref_balance=user_data['ref_balance'],
                                                                         ref_link=user_data['ref_link'],
                                                                         processing=user_data['balance'] // 20)

    ikb_ref = markups.create_ref_keyboard(user_lang)
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=ref_message,
                                reply_markup=ikb_ref)


# SendPhoto handlers + save photo in local files _________________________________________________
@dp.callback_query_handler(lambda callback: callback.data == 'send_photo_api')
async def send_photo_api_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    caption = tr.translations_list[user_lang]['captions_send_photo_api']
    ikb_back = markups.create_back_keyboard(user_lang)
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=caption,
                                parse_mode='Markdown')

    photo_request_message = await bot.send_message(chat_id=callback.message.chat.id,
                                                   text="Please send a photo for processing.",
                                                   reply_markup=ikb_back)
    await state.update_data(photo_request_message_id=photo_request_message.message_id)
    await PhotoStates.waiting_for_photo.set()


@dp.message_handler(content_types=types.ContentType.PHOTO, state=PhotoStates.waiting_for_photo)
async def handle_photo(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    data = await state.get_data()
    photo_request_message_id = data.get('photo_request_message_id')

    # Удаляем сообщение "Please send a photo for processing."
    if photo_request_message_id:
        await bot.delete_message(chat_id=message.chat.id, message_id=photo_request_message_id)

    file_info = await bot.get_file(message.photo[-1].file_id)
    file_path = file_info.file_path

    # Создаем папку, если она не существует
    os.makedirs('./tmp/files/photos', exist_ok=True)

    # Получаем абсолютный путь к файлу
    file_name = os.path.join(os.getcwd(), './tmp/files/photos', os.path.basename(file_path))

    # Скачиваем файл
    await bot.download_file(file_path, file_name)

    # Сохраняем путь к фото в состоянии
    await state.update_data(photo_path=file_name)

    # Отправляем сообщение с выбором размера бюста
    ikb_bust_size = markups.create_bust_size_keyboard(user_lang)
    bust_size_message = await bot.send_message(chat_id=message.chat.id,
                                               text=tr.translations_list[user_lang]['captions_bust_size'],
                                               reply_markup=ikb_bust_size)
    await state.update_data(bust_size_message_id=bust_size_message.message_id)
    await PhotoStates.waiting_for_bust_size.set()


@dp.callback_query_handler(lambda callback: callback.data.startswith('bust_'), state=PhotoStates.waiting_for_bust_size)
async def handle_bust_size_selection(callback: types.CallbackQuery, state: FSMContext):
    bust_size = callback.data  # Получаем размер бюста из callback data
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    # Сохраняем выбранный размер бюста в состоянии
    await state.update_data(bust_size=bust_size)

    # Получаем сохраненные данные
    data = await state.get_data()
    bust_size_message_id = data.get('bust_size_message_id')

    # Удаляем сообщение с выбором размера бюста
    if bust_size_message_id:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=bust_size_message_id)

    # # Предложите пользователю выбрать пресет
    # ikb_preset = markups.create_preset_keyboard(user_lang)
    # preset_message = await bot.send_message(chat_id=callback.message.chat.id,
    #                                         text='Please, select preset ',
    #                                         reply_markup=ikb_preset)
    # await state.update_data(preset_message_id=preset_message.message_id)
    await PhotoStates.waiting_for_preset.set()

    # @dp.callback_query_handler(lambda callback: callback.data.startswith('prompt_'), state=PhotoStates.waiting_for_preset)
    # async def handle_preset_selection(callback: types.CallbackQuery, state: FSMContext):
    #     preset_key = callback.data  # Получаем ключ пресета из callback data
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    # Получаем текст пресета из словаря prompts
    selected_preset = tr.prompts.get('prompt_women', "")

    # Получаем сохраненные данные
    data = await state.get_data()
    photo_path = data['photo_path']
    bust_size = data['bust_size']
    preset_message_id = data.get('preset_message_id')

    # Получаем текст пресета из словаря prompts
    bust_size_text = tr.busts.get(bust_size, "")

    # Удаляем сообщение с выбором пресета
    if preset_message_id:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=preset_message_id)

    # Обработка фото и отправка результата
    process_message = await bot.send_message(chat_id=callback.message.chat.id, text="In process. Wait Please")

    # Попытка списания кредитов
    if await db.deduct_credits(dp['db_pool'], user_id, 20):
        final_prompt = f"{selected_preset}, {bust_size_text}"
        results = await paymont_create_picture(photo_path, process_message, final_prompt)
        if results:
            with open(results, 'rb') as photo:
                await bot.send_photo(chat_id=callback.message.chat.id,
                                     photo=photo)

            # Удаляем обработанный файл
            os.remove(results)

            ikb_menu = markups.create_menu_keyboard(user_lang)
            caption = tr.translations_list[user_lang]['captions_menu']
            await bot.send_message(chat_id=callback.message.chat.id,
                                   text=caption,
                                   reply_markup=ikb_menu,
                                   parse_mode='Markdown')
        else:
            text = tr.translations_list[user_lang]['paymont_edit_error']
            await bot.send_message(chat_id=callback.message.chat.id,
                                   text=text)
    else:
        # Обработка файла с вотемаркой
        img = edit_img.edit_photo(photo_path)
        text = tr.translations_list[user_lang]['captions_watermark_succs']
        if img:
            with open(img, 'rb') as photo:
                await bot.send_photo(chat_id=callback.message.chat.id,
                                     caption=text,
                                     photo=photo)
                # Удаляем файл с вотемаркой
                os.remove(img)

            ikb_menu = markups.create_menu_keyboard(user_lang)
            caption = tr.translations_list[user_lang]['captions_menu']
            await bot.send_message(chat_id=callback.message.chat.id,
                                   text=caption,
                                   reply_markup=ikb_menu,
                                   parse_mode='Markdown')
        else:
            ikb_back = markups.create_back_keyboard(user_lang)
            text = tr.translations_list[user_lang]['paymont_edit_error']
            await bot.send_message(chat_id=callback.message.chat.id,
                                   text=text,
                                   reply_markup=ikb_back)

    # Удаляем исходный файл
    os.remove(photo_path)

    # Завершаем состояние
    await state.finish()


@dp.callback_query_handler(lambda callback: callback.data == 'cancel', state='*')
async def cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await db.get_user_language(dp['db_pool'], str(callback.from_user.id))
    if user_lang is None:
        user_lang = 'en'

    await state.finish()

    ikb_menu = markups.create_menu_keyboard(user_lang)
    caption = tr.translations_list[user_lang]['captions_menu']
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=caption,
                                reply_markup=ikb_menu)


async def paymont_create_picture(image_path, process_message, prompt):
    user_lang = await db.get_user_language(dp['db_pool'], process_message.chat.id)  # Получение языка пользователя
    # URL API для создания задачи и проверки статуса
    base_url = 'https://api.generativecore.ai'
    url_create_task = f'{base_url}/api/v3/tasks'
    url_task_status = f'{base_url}/api/v3/tasks/{{task_id}}'

    # Учетные данные для авторизации
    username = settings.username
    password = settings.password

    # Путь для сохранения результата
    output_dir = './tmp/files/results'

    # Открываем изображение в бинарном режиме и кодируем его в base64
    with open(image_path, 'rb') as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Данные задачи
    payload = {
        "type": "dress-on-image",
        "payload": {
            "image": image_data,
            "gender": "auto",
            "prompt": prompt
        }
    }

    headers = {
        'Content-Type': 'application/json'
    }

    # Выполнение POST-запроса для создания задачи с авторизацией
    response = requests.post(url_create_task, headers=headers, json=payload, auth=(username, password))

    if response.status_code == 201:
        task_info = response.json()
        task_id = task_info['id']
    else:
        print('Error creating task:', response.status_code, response.text)
        return None

    # Время начала отслеживания
    start_time = time.time()
    timeout = 300  # Таймаут в секундах (5 минут)

    # Проверка статуса задачи
    while True:
        response = requests.get(url_task_status.format(task_id=task_id), headers=headers, auth=(username, password))

        if response.status_code == 200:
            task_info = response.json()
            status = task_info['status']
            current_time = datetime.now().strftime("%H:%M:%S")
            status_message = tr.translations_list[user_lang]['task_status'].format(status=status,
                                                                                   current_time=current_time)

            # Обновление сообщения статуса
            try:
                await bot.edit_message_text(status_message, chat_id=process_message.chat.id,
                                            message_id=process_message.message_id)
            except aiogram.utils.exceptions.MessageNotModified:
                # Игнорируем ошибку, если сообщение не было изменено
                pass

            if status == 'completed':
                # Получение результатов задачи
                results = task_info['results']['data']
                if 'images' in results:
                    image_info = results['images'][0]
                    if 'base64' in image_info:
                        # Если изображение представлено в base64
                        image_data = image_info['base64']
                        image_bytes = base64.b64decode(image_data)
                        # Формируем путь для сохранения изображения
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        image_file_path = os.path.join(output_dir, f"{task_id}_{timestamp}.png")
                        with open(image_file_path, 'wb') as f:
                            f.write(image_bytes)

                        return image_file_path

                    else:
                        print('No base64 data found in task results')
                break
            elif status in ['failed', 'timeout']:
                print('Task failed or timed out')
                await bot.edit_message_text(f'Task {status}', chat_id=process_message.chat.id,
                                            message_id=process_message.message_id)
                break
        else:
            print('Error fetching task status:', response.status_code, response.text)
            await bot.edit_message_text('Error fetching task status', chat_id=process_message.chat.id,
                                        message_id=process_message.message_id)
            break

        # Проверка таймаута
        if time.time() - start_time > timeout:
            break

        # Ожидание перед следующей проверкой статуса
        await asyncio.sleep(10)


@dp.callback_query_handler(lambda callback: callback.data == 'donate')
async def donate_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    ikb_donate = markups.create_donate_keyboard(user_lang)
    caption = tr.translations_list[user_lang]['captions_donate']
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=caption,
                                reply_markup=ikb_donate)


@dp.callback_query_handler(lambda callback: callback.data == 'ref_stats')
async def ref_stats_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)

    if user_lang is None:
        user_lang = 'en'

    # Используйте user_id, который вы уже извлекли
    referrals, total_referral_credit = await db.get_referral_stats(pool=dp['db_pool'], user_id=user_id)

    message = f"Реферальная статистика:\n\n"
    message += f"Приглашений по ссылке: {referrals}\n"
    message += f"Общее количество заработка по реферальной ссылке: {total_referral_credit} единиц\n"

    ref_stats_keyboard = markups.create_back_keyboard(user_lang)
    # Обновляем сообщение, показывая клавиатуру с выбором метода оплаты
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=message,
                                reply_markup=ref_stats_keyboard)


@dp.callback_query_handler(lambda callback: callback.data.startswith('donate_'))
async def handle_pay_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)
    if user_lang is None:
        user_lang = 'en'

    amount = int(callback.data.split('_')[1])

    # Создаем клавиатуру с выбором метода оплаты
    payment_method_keyboard = markups.create_paymont2_keyboard(user_lang, amount)
    text = 'Select payment method'

    # Обновляем сообщение, показывая клавиатуру с выбором метода оплаты
    await bot.edit_message_text(chat_id=callback.message.chat.id,
                                message_id=callback.message.message_id,
                                text=text,
                                reply_markup=payment_method_keyboard)


@dp.callback_query_handler(lambda callback: callback.data.startswith('pay_'))
async def handle_payment_method_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)
    if user_lang is None:
        user_lang = 'en'

    data = callback.data.split('_')
    method = data[1]  # Метод оплаты (aaio, rukassa, legitpay, и т.д.)
    amount = int(data[2])  # Сумма пополнения

    # Создание платежа и получение текста для отправки и order_id в зависимости от метода оплаты
    text, order_id = await paymont.process_payment_command(bot, callback, amount, user_lang, dp['db_pool'], method)

    # Отправляем сообщение с ссылкой на оплату
    await bot.send_message(chat_id=callback.message.chat.id, text=text)

    # Если order_id существует, отправляем отдельное сообщение для отслеживания статуса платежа
    if order_id:
        status_message = await bot.send_message(chat_id=callback.message.chat.id, text="Processing payment status...")

        # Начинаем отслеживание статуса платежа
        asyncio.create_task(
            paymont.monitor_payment(bot, order_id, settings.RUKASSA_SHOP_ID, settings.RUKASSA_TOKEN,
                                    status_message.chat.id,
                                    status_message.message_id, user_id, amount, user_lang, dp['db_pool'], order_id,
                                    method))


async def on_startup(dispatcher):
    try:
        dispatcher['db_pool'] = await db.create_pool()
    except Exception as e:
        logging.error(e)
        # TODO можно добавить дополнительную логику, если необходимо


async def on_shutdown(dispatcher):
    await dispatcher['db_pool'].close()


if __name__ == '__main__':
    # Запускаем long-polling и передаем функцию on_startup
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
