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
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

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

start_photo = 'https://img.freepik.com/free-vector/young-people-talking-in-different-languages-illustrations-set_23' \
              '-2148370672.jpg?size=626&ext=jpg&ga=GA1.1.1518270500.1713312000&semt=ais '


class PhotoStates(StatesGroup):
    waiting_for_preset = State()
    waiting_for_photo = State()


# open menu photo to send
with open(settings.menu_photo_path, 'rb') as f:
    menu_photo = f.read()


# Commands handlers ___________________________________________________________
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or 'unknown'
    ref_code = message.get_args()  # Получаем реферальный код из аргументов команды /start

    user_lang = await db.get_user_language(dp['db_pool'], user_id)

    replay_keyboard = markups.replay_keyboard()
    await bot.send_message(chat_id=message.chat.id,
                           text='''Welocme!
                           /menu - menu
                           /language - change language''',

                           reply_markup=replay_keyboard,
                           parse_mode='Markdown')

    if not user_lang:
        ref_link = generate_referral_link(user_id)
        invited_by = ref_code if ref_code else None

        await db.add_user(dp['db_pool'], user_id, username, 'en', False, ref_link, invited_by)

        if invited_by:
            await db.record_invitation(dp['db_pool'], invited_by, user_id)
            await db.add_referral_credits(dp['db_pool'], invited_by)

        caption = "Welcome! Please select your language."
        await bot.send_photo(chat_id=message.chat.id, photo=start_photo, caption=caption,
                             reply_markup=markups.ikb_start)
    else:
        caption = tr.translations_list[user_lang]['captions_terms']
        ikb_terms = markups.create_terms_keyboard(user_lang)
        await bot.send_photo(chat_id=message.chat.id,
                             photo=menu_photo,
                             caption=caption,
                             reply_markup=ikb_terms,
                             parse_mode='Markdown')


# Menu buttons handlers___________________________________________________________________
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
                await bot.send_photo(chat_id=message.chat.id,
                                     photo=menu_photo,
                                     caption=caption,
                                     reply_markup=ikb_menu,
                                     parse_mode='Markdown')
            else:
                text = 'unset user language. Use /start'
                await bot.send_message(chat_id=message.chat.id,
                                       text=text)
        except Exception as e:
            print(f'Error! Unset user_lang: {e}')


@dp.callback_query_handler(lambda callback: callback.data in ['ru', 'en', 'chinese', 'fr', 'es'])
async def lang_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)  # Получаем ID пользователя
    user_lang = callback.data  # Язык, выбранный пользователем

    # Сохраняем выбранный язык пользователя в базе данных
    await db.update_user_language(dp['db_pool'], user_id, user_lang)

    # Удаляем предыдущее сообщение с клавиатурой выбора языка
    await bot.delete_message(chat_id=callback.message.chat.id,
                             message_id=callback.message.message_id)

    # Получаем обновленные переводы для нового выбранного языка
    translations = tr.translations_list[user_lang]

    ikb_menu = markups.create_menu_keyboard(user_lang)

    # Отправляем фото с новым описанием и клавиатурой
    caption = translations['captions_menu']
    await bot.send_photo(chat_id=callback.message.chat.id,
                         photo=menu_photo,
                         caption=caption,
                         reply_markup=ikb_menu,
                         parse_mode='Markdown')


@dp.callback_query_handler(lambda callback: callback.data in ['terms_yes', 'terms_no'])
async def terms_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    # Извлекаем язык пользователя
    user_lang = await db.get_user_language(dp['db_pool'], user_id)

    if callback.data == 'terms_yes':
        ikb_menu = markups.create_menu_keyboard(user_lang)
        caption = tr.translations_list[user_lang]['captions_menu']
        await bot.edit_message_caption(chat_id=callback.message.chat.id,
                                       message_id=callback.message.message_id,
                                       caption=caption,
                                       reply_markup=ikb_menu,
                                       parse_mode='Markdown')
    else:
        caption = tr.translations_list[user_lang]['captions_terms_no']
        await bot.edit_message_caption(chat_id=callback.message.chat.id,
                                       message_id=callback.message.message_id,
                                       caption=caption)


@dp.callback_query_handler(lambda callback: callback.data == 'back')
async def back_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    ikb_menu = markups.create_menu_keyboard(user_lang)
    caption = tr.translations_list[user_lang]['captions_menu']
    await bot.edit_message_caption(chat_id=callback.message.chat.id,
                                   message_id=callback.message.message_id,
                                   caption=caption,
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
    await bot.edit_message_caption(chat_id=callback.message.chat.id,
                                   message_id=callback.message.message_id,
                                   caption=profile_message,
                                   reply_markup=ikb_profile)


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
    await bot.edit_message_caption(chat_id=callback.message.chat.id,
                                   message_id=callback.message.message_id,
                                   caption=ref_message,
                                   reply_markup=ikb_ref)


# SendPhoto handlers + save photo in local files _________________________________________________
@dp.callback_query_handler(lambda callback: callback.data == 'send_photo_api')
async def send_photo_api_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    ikb_preset = markups.create_preset_keyboard(user_lang)
    caption = tr.translations_list[user_lang]['captions_send_photo_api']

    await bot.edit_message_caption(chat_id=callback.message.chat.id,
                                   message_id=callback.message.message_id,
                                   caption=caption,
                                   reply_markup=ikb_preset,
                                   parse_mode='Markdown')

    # Устанавливаем состояние ожидания выбора пресета
    await PhotoStates.waiting_for_preset.set()


@dp.callback_query_handler(lambda callback: callback.data.startswith('prompt_'), state=PhotoStates.waiting_for_preset)
async def handle_preset_selection(callback: types.CallbackQuery, state: FSMContext):
    preset_key = callback.data  # Получаем ключ пресета из callback data
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    # Получаем текст пресета из словаря prompts
    selected_preset = tr.prompts.get(preset_key, "")

    # Сохраняем выбранный пресет в состоянии
    await state.update_data(selected_preset=selected_preset)

    # Предложите пользователю отправить фото
    await bot.send_message(chat_id=callback.message.chat.id, text="Please send a photo for processing.")

    # Устанавливаем состояние ожидания фотографии
    await PhotoStates.waiting_for_photo.set()


@dp.message_handler(content_types=types.ContentType.PHOTO, state=PhotoStates.waiting_for_photo)
async def handle_photo(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    # Получаем выбранный пресет из состояния
    data = await state.get_data()
    selected_preset = data.get('selected_preset', '')

    file_info = await bot.get_file(message.photo[-1].file_id)
    file_path = file_info.file_path

    # Создаем папку, если она не существует
    os.makedirs('./tmp/files/photos', exist_ok=True)

    # Получаем абсолютный путь к файлу
    file_name = os.path.join(os.getcwd(), './tmp/files/photos', os.path.basename(file_path))

    # Скачиваем файл
    await bot.download_file(file_path, file_name)

    # Отправляем сообщение с надписью "In process. Wait Please"
    process_message = await message.reply("In process. Wait Please")

    # Попытка списания кредитов
    if await db.deduct_credits(dp['db_pool'], user_id, 20):

        results = await paymont_create_picture(file_name, process_message, selected_preset)
        if results:
            with open(results, 'rb') as photo:
                await bot.send_photo(chat_id=message.chat.id,
                                     photo=photo)

            # Удаляем обработанный файл
            os.remove(results)

            ikb_menu = markups.create_menu_keyboard(user_lang)
            caption = tr.translations_list[user_lang]['captions_menu']

            await bot.send_photo(chat_id=message.chat.id,
                                 photo=menu_photo,
                                 caption=caption,
                                 reply_markup=ikb_menu,
                                 parse_mode='Markdown')
        else:
            text = tr.translations_list[user_lang]['paymont_edit_error']
            await bot.send_message(chat_id=message.chat.id,
                                   text=text)
    else:
        # Обработка файла с вотемаркой
        img = edit_img.edit_photo(file_name)
        text = tr.translations_list[user_lang]['captions_watermark_succs']
        if img:
            with open(img, 'rb') as photo:
                await bot.send_photo(chat_id=message.chat.id,
                                     caption=text,
                                     photo=photo)

            # Удаляем файл с вотемаркой
            os.remove(img)

            ikb_menu = markups.create_menu_keyboard(user_lang)
            caption = tr.translations_list[user_lang]['captions_menu']

            await bot.send_photo(chat_id=message.chat.id,
                                 photo=menu_photo,
                                 caption=caption,
                                 reply_markup=ikb_menu,
                                 parse_mode='Markdown')
        else:
            ikb_back = markups.create_back_keyboard(user_lang)
            text = tr.translations_list[user_lang]['paymont_edit_error']
            await bot.send_message(chat_id=message.chat.id,
                                   text=text,
                                   reply_markup=ikb_back)

    # Удаляем исходный файл
    os.remove(file_name)

    # Завершаем состояние
    await state.finish()


# Функция для создания и отслеживания задачи
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


# Donate handlers
@dp.callback_query_handler(lambda callback: callback.data == 'donate')
async def donate_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя

    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден

    ikb_donate = markups.create_donate_keyboard(user_lang)
    caption = tr.translations_list[user_lang]['captions_donate']
    await bot.edit_message_caption(chat_id=callback.message.chat.id,
                                   message_id=callback.message.message_id,
                                   caption=caption,
                                   reply_markup=ikb_donate)


@dp.callback_query_handler(lambda callback: callback.data.startswith('donate_'))
async def handle_pay_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_lang = await db.get_user_language(dp['db_pool'], user_id)  # Получение языка пользователя
    if user_lang is None:
        user_lang = 'en'  # Дефолтное значение, если язык не найден
    amount = int(callback.data.split('_')[1])  # Преобразуем amount в int

    # Создание платежа и получение текста для отправки и order_id
    text, order_id = await paymont.process_payment_command(bot, callback, amount, user_lang, dp['db_pool'])

    # Отправляем сообщение с ссылкой на оплату
    await bot.send_message(chat_id=callback.message.chat.id, text=text)

    # Если order_id существует, отправляем отдельное сообщение для отслеживания статуса платежа
    if order_id:
        status_message = await bot.send_message(chat_id=callback.message.chat.id, text="Processing payment status...")

        # Начинаем отслеживание статуса платежа
        asyncio.create_task(
            paymont.monitor_payment(bot, order_id, settings.RUKASSA_SHOP_ID, settings.RUKASSA_TOKEN,
                                    status_message.chat.id,
                                    status_message.message_id, user_id, amount, user_lang, dp['db_pool'], order_id))


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
