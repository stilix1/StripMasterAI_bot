import json

import aiohttp


async def create_payment_rukassa(shop_id, order_id, amount, token, user_code):
    # создание платежа через RUKassa
    API_URL_CREATE = "https://lk.rukassa.is/api/v1/create"

    data = {
        "shop_id": shop_id,
        "order_id": order_id,
        "amount": amount,
        "token": token,
        "user_code": user_code,
        "json": True,  # Если вы используете H2H интеграцию
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL_CREATE, data=data) as response:
            response_text = await response.text()
            try:
                response_data = json.loads(response_text)
                return response_data
            except json.JSONDecodeError:
                return {"message": response_text}


async def check_payment_rukassa(order_id, shop_id, token):
    API_URL_CHECK = "https://lk.rukassa.is/api/v1/getPayInfo"
    params = {"order_id": order_id, "shop_id": shop_id, "token": token}
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL_CHECK, data=params) as response:
            response_text = await response.text()
            try:
                response_data = json.loads(response_text)
                return response_data
            except json.JSONDecodeError:
                return {"message": response_text}
