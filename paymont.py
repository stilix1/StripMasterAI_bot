import json
import time
from urllib.parse import urlencode

import aiohttp
import asyncio
import hashlib

import db
import settings
import translations as tr


async def monitor_payment(bot, order_id, shop_id, token, chat_id, message_id, user_id, amount,
                          user_lang, db_pool, transaction_id, method):
    while True:
        if method == 'rukassa':
            payment_status = await check_payment_rukassa(order_id, shop_id, token)
        elif method == 'aaio':
            payment_status = await check_payment_status_aaio(token, shop_id, order_id)
        else:
            return f"Unknown payment method: {method}"

        current_time = time.strftime('%Y-%m-%d %H:%M:%S')

        if isinstance(payment_status, dict) and 'status' in payment_status:
            status = payment_status['status']
            expired_date = payment_status.get('expired_date', 'N/A')

            if status in ['PAID', 'success', 'expired', 'CANCEL']:
                # Сохранение основной транзакции в базе данных с использованием transaction_id
                await db.record_transaction(db_pool, transaction_id, user_id, status, amount)

                if status in ['PAID', 'success']:
                    # Добавление кредитов пользователю
                    await db.add_user_credits(db_pool, user_id, amount)

                    # Находим пригласившего пользователя
                    referrer_id = await db.get_referrer_id(db_pool, user_id)

                    if referrer_id:
                        # Рассчитываем реферальный бонус
                        referral_bonus = int(amount * 0.1)  # 10% от суммы платежа

                        # Сохраняем реферальную транзакцию в базе данных
                        await db.record_referral_transaction(db_pool, referrer_id, user_id, referral_bonus)

                        # Добавляем реферальный бонус пригласившему пользователю
                        await db.add_user_credits(db_pool, referrer_id, referral_bonus)

                return f"Payment status for order {order_id}: {status}"
            else:
                status_message = tr.translations_list[user_lang]['paymnt_task_status'].format(
                    status=status,
                    current_time=current_time,
                    expired_date=expired_date
                )
                await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=status_message)
        else:
            status_message = tr.translations_list[user_lang]['paymnt_task_status'].format(
                status='unknown',
                current_time=current_time,
                expired_date='N/A'
            )
            await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=status_message)

        await asyncio.sleep(30)


async def process_payment_command(bot, callback, amount, user_lang, db_pool, method):
    order_id = str(callback.from_user.id + int(time.time())) + str(time.time()).split('.')[1]
    user_code = str(callback.from_user.id)

    # Удаление сообщения с кнопками
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)

    if method == 'rukassa':
        shop_id = settings.RUKASSA_SHOP_ID
        token = settings.RUKASSA_TOKEN
        payment_result = await create_payment_rukassa(shop_id, order_id, amount, token, user_code)
        if payment_result and 'url' in payment_result:
            payment_link = payment_result['url']
        else:
            text = tr.translations_list[user_lang]['create_url_error'], \
                   f'Error: {callback}, {amount}, {user_lang}, {db_pool}, {method}'
            return text, None
    elif method == 'aaio':
        shop_id = settings.AAIO_SHOP_ID
        token = settings.AAIO_TOKEN
        payment_result = await create_payment_aaio(shop_id, order_id, amount)
        payment_link = payment_result
    else:
        text = tr.translations_list[user_lang]['create_url_error'], f'Error: {callback}, {amount}, {user_lang},' \
                                                                    f' {db_pool}, {method}'
        return text, None

    if payment_result:
        transaction_id = callback.from_user.id
        text = tr.translations_list[user_lang]['create_url_succs'] + payment_link
        message = await bot.send_message(chat_id=callback.message.chat.id, text=text)

        asyncio.create_task(monitor_payment(bot, order_id, shop_id, token, callback.message.chat.id,
                                            message.message_id, callback.from_user.id,
                                            amount, user_lang, db_pool, transaction_id, method))
        return text, None


# aaio ____________________________________________________________________________
async def create_payment_aaio(shop_id, order_id, amount):
    url = 'https://aaio.so/merchant/pay'
    api_key = settings.AAIO_TOKEN
    secret = settings.AAIO_secret1

    params = {
        'merchant_id': shop_id,
        'amount': amount,
        'currency': 'RUB',
        'order_id': order_id,
        'sign': hashlib.sha256(f'{shop_id}:{amount}:RUB:{secret}:{order_id}'.encode('utf-8')).hexdigest(),
        'desc': 'Order Payment',
        'lang': 'ru'
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Api-Key': api_key
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=params, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    sign = ':'.join([
                        str(shop_id),
                        str(amount),
                        'RUB',
                        str(secret),
                        str(order_id)
                    ])

                    params = {
                        'merchant_id': shop_id,
                        'amount': amount,
                        'currency': 'RUB',
                        'order_id': order_id,
                        'sign': hashlib.sha256(sign.encode('utf-8')).hexdigest(),
                        'desc': 'Order Payment',
                        'lang': 'ru'
                    }

                    return "https://aaio.so/merchant/pay?" + urlencode(params)
                else:
                    raise Exception(f"Failed to create payment: status {response.status}")
        except aiohttp.ClientError as e:
            raise Exception(f"AIOHTTP Client Error: {e}")
        except Exception as e:
            raise Exception(f"Error creating payment: {str(e)}")


async def check_payment_status_aaio(api_key, merchant_id, order_id):
    url = 'https://aaio.so/api/info-pay'

    params = {
        'merchant_id': merchant_id,
        'order_id': order_id
    }

    headers = {
        'Accept': 'application/json',
        'X-Api-Key': api_key
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=params, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=60)) as response:

                if response.status in [200, 400, 401]:
                    response_json = await response.json()

                    if response_json.get('type') == 'success':
                        return response_json  # Возвращаем весь ответ JSON
                    else:
                        error_message = response_json.get('message', 'Unknown error')
                        return {'status': 'error', 'message': error_message}
                else:
                    return {'status': 'error', 'message': f"Unexpected response status: {response.status}"}
        except aiohttp.ClientError as e:
            return {'status': 'error', 'message': f"AIOHTTP Client Error: {str(e)}"}
        except Exception as e:
            return {'status': 'error', 'message': f"Error checking payment status: {str(e)}"}


# RUKASSA ____________________________________________________________________________
async def create_payment_rukassa(shop_id, order_id, amount, token, user_code):
    # создание платежа через RUKassa
    API_URL_CREATE = 'https://lk.rukassa.is/api/v1/create'

    data = {
        'shop_id': shop_id,
        'order_id': order_id,
        'amount': amount,
        'token': token,
        'user_code': user_code,
        'json': True  # Если вы используете H2H интеграцию
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL_CREATE, data=data) as response:
            response_text = await response.text()
            try:
                response_data = json.loads(response_text)
                return response_data
            except json.JSONDecodeError:
                return {'message': response_text}


async def check_payment_rukassa(order_id, shop_id, token):
    API_URL_CHECK = 'https://lk.rukassa.is/api/v1/getPayInfo'
    params = {
        'order_id': order_id,
        'shop_id': shop_id,
        'token': token
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL_CHECK, data=params) as response:
            response_text = await response.text()
            try:
                response_data = json.loads(response_text)
                return response_data
            except json.JSONDecodeError:
                return {'message': response_text}
