import asyncio
import json
import time

import aiohttp

import db
import settings
import translations as tr

API_URL_CREATE = 'https://lk.rukassa.is/api/v1/create'
API_URL_CHECK = 'https://lk.rukassa.is/api/v1/getPayInfo'


async def create_payment(shop_id, order_id, amount, token, user_data, user_code):
    data = {
        'shop_id': shop_id,
        'order_id': order_id,
        'amount': amount,
        'token': token,
        'data': json.dumps(user_data),
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


async def check_payment_status(order_id, shop_id, token):
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


async def monitor_payment(bot, order_id, shop_id, token, chat_id, message_id, user_id, amount,
                          user_lang, db_pool, transaction_id):
    while True:
        payment_status = await check_payment_status(order_id, shop_id, token)
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')

        if isinstance(payment_status, dict):
            status = payment_status.get('status', 'Unknown')

            if status in ['PAID', 'CANCEL']:
                # Сохранение транзакции в базе данных с использованием transaction_id
                await db.record_transaction(db_pool, transaction_id, user_id, status, amount)

                if status == 'PAID':
                    # Добавление кредитов пользователю
                    await db.add_user_credits(db_pool, user_id, amount)

                return f"Payment status for order {order_id}: {status}"
            else:
                status_message = tr.translations_list[user_lang]['task_status'].format(status=status,
                                                                                       current_time=current_time)
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=status_message)

        await asyncio.sleep(30)


async def process_payment_command(bot, callback, amount, user_lang, db_pool, ):
    shop_id = settings.RUKASSA_SHOP_ID
    token = settings.RUKASSA_TOKEN
    order_id = str(int(time.time())) + str(time.time()).split('.')[1]
    user_data = {'param1': 'value1'}
    user_code = str(callback.from_user.id)

    payment_result = await create_payment(shop_id, order_id, amount, token, user_data, user_code)

    if isinstance(payment_result, dict) and 'error' in payment_result:
        text = tr.translations_list[user_lang]['create_url_create_error'] + payment_result['message']
        return text, None
    elif isinstance(payment_result, dict) and 'url' in payment_result:
        text = tr.translations_list[user_lang]['create_url_succs'] + payment_result['url']
        transaction_id = payment_result.get('id')  # Получаем id из ответа
        asyncio.create_task(monitor_payment(bot, order_id, shop_id, token, callback.message.chat.id,
                                            callback.message.message_id, callback.from_user.id,
                                            amount, user_lang, db_pool, transaction_id))
        return text, order_id
    else:
        text = tr.translations_list[user_lang]['create_url_error'] + payment_result
        return text, None
