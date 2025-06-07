import hashlib
from urllib.parse import urlencode

import aiohttp

from utils import settings


async def create_payment_aaio(shop_id, order_id, amount):
    url = "https://aaio.so/merchant/pay"
    api_key = settings.AAIO_TOKEN
    secret = settings.AAIO_secret1

    params = {
        "merchant_id": shop_id,
        "amount": amount,
        "currency": "RUB",
        "order_id": order_id,
        "sign": hashlib.sha256(
            f"{shop_id}:{amount}:RUB:{secret}:{order_id}".encode("utf-8")
        ).hexdigest(),
        "desc": "Order Payment",
        "lang": "ru",
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Api-Key": api_key,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url,
                data=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status == 200:
                    sign = ":".join(
                        [str(shop_id), str(amount), "RUB", str(secret), str(order_id)]
                    )

                    params = {
                        "merchant_id": shop_id,
                        "amount": amount,
                        "currency": "RUB",
                        "order_id": order_id,
                        "sign": hashlib.sha256(sign.encode("utf-8")).hexdigest(),
                        "desc": "Order Payment",
                        "lang": "ru",
                    }

                    return "https://aaio.so/merchant/pay?" + urlencode(params)
                else:
                    raise Exception(
                        f"Failed to create payment: status {response.status}"
                    )
        except aiohttp.ClientError as e:
            raise Exception(f"AIOHTTP Client Error: {e}")
        except Exception as e:
            raise Exception(f"Error creating payment: {str(e)}")


async def check_payment_status_aaio(api_key, merchant_id, order_id):
    url = "https://aaio.so/api/info-pay"

    params = {"merchant_id": merchant_id, "order_id": order_id}

    headers = {"Accept": "application/json", "X-Api-Key": api_key}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url,
                data=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:

                if response.status in [200, 400, 401]:
                    response_json = await response.json()

                    if response_json.get("type") == "success":
                        return response_json  # Возвращаем весь ответ JSON
                    else:
                        error_message = response_json.get("message", "Unknown error")
                        return {"status": "error", "message": error_message}
                else:
                    return {
                        "status": "error",
                        "message": f"Unexpected response status: {response.status}",
                    }
        except aiohttp.ClientError as e:
            return {"status": "error", "message": f"AIOHTTP Client Error: {str(e)}"}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking payment status: {str(e)}",
            }
