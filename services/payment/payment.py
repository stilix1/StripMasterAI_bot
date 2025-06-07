import asyncio
import base64
import os
import time
from datetime import datetime

import aiogram
import requests

from services.payment.payment_aaio import check_payment_status_aaio, create_payment_aaio
from services.payment.payment_rukassa import (
    check_payment_rukassa,
    create_payment_rukassa,
)
from utils import settings
from utils import translations as tr


class PaymentService:
    def __init__(self, bot, repo_user, repo_transaction, repo_referral):
        self.bot = bot
        self.repo_user = repo_user
        self.repo_transaction = repo_transaction
        self.repo_referral = repo_referral

    async def paymont_create_picture(self, image_path, process_message, prompt):
        user_lang = (
            await self.repo_user.get_language(str(process_message.chat.id)) or "en"
        )

        base_url = "https://api.generativecore.ai"
        url_create_task = f"{base_url}/api/v3/tasks"
        url_task_status = f"{base_url}/api/v3/tasks/{{task_id}}"

        username = settings.username
        password = settings.password
        output_dir = "./tmp/files/results"

        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        payload = {
            "type": "dress-on-image",
            "payload": {"image": image_data, "gender": "auto", "prompt": prompt},
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(
            url_create_task, headers=headers, json=payload, auth=(username, password)
        )

        if response.status_code == 201:
            task_info = response.json()
            task_id = task_info["id"]
        else:
            print("Error creating task:", response.status_code, response.text)
            return None

        start_time = time.time()
        timeout = 300

        while True:
            response = requests.get(
                url_task_status.format(task_id=task_id),
                headers=headers,
                auth=(username, password),
            )

            if response.status_code == 200:
                task_info = response.json()
                status = task_info["status"]
                current_time = datetime.now().strftime("%H:%M:%S")
                status_message = tr.translations_list[user_lang]["task_status"].format(
                    status=status, current_time=current_time
                )

                try:
                    await self.bot.edit_message_text(
                        status_message,
                        chat_id=process_message.chat.id,
                        message_id=process_message.message_id,
                    )
                except aiogram.utils.exceptions.MessageNotModified:
                    pass

                if status == "completed":
                    results = task_info["results"]["data"]
                    if "images" in results:
                        image_info = results["images"][0]
                        if "base64" in image_info:
                            image_data = image_info["base64"]
                            image_bytes = base64.b64decode(image_data)
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            image_file_path = os.path.join(
                                output_dir, f"{task_id}_{timestamp}.png"
                            )
                            with open(image_file_path, "wb") as f:
                                f.write(image_bytes)
                            return image_file_path
                    break
                elif status in ["failed", "timeout"]:
                    await self.bot.edit_message_text(
                        f"Task {status}",
                        chat_id=process_message.chat.id,
                        message_id=process_message.message_id,
                    )
                    break
            else:
                await self.bot.edit_message_text(
                    "Error fetching task status",
                    chat_id=process_message.chat.id,
                    message_id=process_message.message_id,
                )
                break

            if time.time() - start_time > timeout:
                break
            await asyncio.sleep(10)

        return None

    async def monitor_payment(
        self,
        order_id,
        shop_id,
        token,
        chat_id,
        message_id,
        user_id,
        amount,
        user_lang,
        transaction_id,
        method,
    ):
        while True:
            if method == "rukassa":
                payment_status = await check_payment_rukassa(order_id, shop_id, token)
            elif method == "aaio":
                payment_status = await check_payment_status_aaio(
                    token, shop_id, order_id
                )
            else:
                return f"Unknown payment method: {method}"

            current_time = time.strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(payment_status, dict) and "status" in payment_status:
                status = payment_status["status"]
                expired_date = payment_status.get("expired_date", "N/A")

                if status in ["PAID", "success", "expired", "CANCEL"]:
                    await self.repo_transaction.record_transaction(
                        transaction_id, user_id, status, amount
                    )

                    if status in ["PAID", "success"]:
                        await self.repo_transaction.add_user_credits(user_id, amount)
                        referrer_id = await self.repo_user.get_referrer_id(user_id)
                        if referrer_id:
                            referral_bonus = int(amount * 0.1)
                            await self.repo_referral.record_referral_transaction(
                                referrer_id, user_id, referral_bonus
                            )
                            await self.repo_transaction.add_user_credits(
                                referrer_id, referral_bonus
                            )

                    return f"Payment status for order {order_id}: {status}"
                else:
                    status_message = tr.translations_list[user_lang][
                        "paymnt_task_status"
                    ].format(
                        status=status,
                        current_time=current_time,
                        expired_date=expired_date,
                    )
                    await self.bot.edit_message_text(
                        chat_id=chat_id, message_id=message_id, text=status_message
                    )
            else:
                status_message = tr.translations_list[user_lang][
                    "paymnt_task_status"
                ].format(
                    status="unknown", current_time=current_time, expired_date="N/A"
                )
                await self.bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=status_message
                )

            await asyncio.sleep(30)

    async def process_payment_command(self, callback, amount, user_lang, method):
        order_id = (
            str(callback.from_user.id + int(time.time()))
            + str(time.time()).split(".")[1]
        )
        user_code = str(callback.from_user.id)
        await self.bot.delete_message(
            chat_id=callback.message.chat.id, message_id=callback.message.message_id
        )

        if method == "rukassa":
            shop_id = settings.RUKASSA_SHOP_ID
            token = settings.RUKASSA_TOKEN
            payment_result = await create_payment_rukassa(
                shop_id, order_id, amount, token, user_code
            )
            payment_link = payment_result.get("url") if payment_result else None
        elif method == "aaio":
            shop_id = settings.AAIO_SHOP_ID
            token = settings.AAIO_TOKEN
            payment_link = await create_payment_aaio(shop_id, order_id, amount)
        else:
            return (tr.translations_list[user_lang]["create_url_error"], None)

        if payment_link:
            transaction_id = callback.from_user.id
            text = tr.translations_list[user_lang]["create_url_succs"] + payment_link
            message = await self.bot.send_message(
                chat_id=callback.message.chat.id, text=text
            )

            asyncio.create_task(
                self.monitor_payment(
                    order_id,
                    shop_id,
                    token,
                    callback.message.chat.id,
                    message.message_id,
                    callback.from_user.id,
                    amount,
                    user_lang,
                    transaction_id,
                    method,
                )
            )
            return text, transaction_id

        return (tr.translations_list[user_lang]["create_url_error"], None)
