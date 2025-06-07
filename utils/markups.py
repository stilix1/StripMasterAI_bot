from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from utils.i18n import t


# ✅ Reply keyboard
def replay_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="💼Menu")]], resize_keyboard=True
    )


# ✅ Start language selection keyboard (без перевода — фиксированные флаги)
ikb_start = InlineKeyboardMarkup(row_width=2)
ikb_start.add(
    InlineKeyboardButton(text="Русский", callback_data="ru"),
    InlineKeyboardButton(text="English", callback_data="en"),
    InlineKeyboardButton(text="中国人", callback_data="chinese"),
    InlineKeyboardButton(text="Français", callback_data="fr"),
    InlineKeyboardButton(text="Español", callback_data="es"),
)


# ✅ Terms of use keyboard
def create_terms_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "button_terms_yes") + " 👍", callback_data="terms_yes"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "button_terms_no") + " 👎", callback_data="terms_no"
                )
            ],
        ]
    )


# ✅ Cancel button
def create_cancel_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
        ]
    )


# ✅ Main menu keyboard
def create_menu_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔞 " + t(lang, "button_send_photo_api"),
                    callback_data="send_photo_api",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🪪 " + t(lang, "button_profile"), callback_data="profile"
                ),
                InlineKeyboardButton(
                    text="📣 " + t(lang, "button_supp"), url="t.me/vladimirskiyandrey"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚻 " + t(lang, "button_referral"), callback_data="referral"
                )
            ],
        ]
    )


# ✅ Prompt selection keyboard
def create_preset_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Women", callback_data="prompt_women3")],
            [
                InlineKeyboardButton(
                    text="⬅️ " + t(lang, "button_back"), callback_data="back"
                )
            ],
        ]
    )


# ✅ Profile screen keyboard
def create_profile_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔞 " + t(lang, "button_send_photo_api"),
                    callback_data="send_photo_api",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚻 " + t(lang, "button_referral"), callback_data="referral"
                ),
                InlineKeyboardButton(
                    text=t(lang, "button_donate"), callback_data="donate"
                ),
                InlineKeyboardButton(
                    text=t(lang, "referral_text"), callback_data="ref_stats"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ " + t(lang, "button_back"), callback_data="back"
                )
            ],
        ]
    )


# ✅ Referral screen keyboard
def create_ref_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "button_donate"), callback_data="donate"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ " + t(lang, "button_back"), callback_data="back"
                )
            ],
        ]
    )


# ✅ Just back button
def create_back_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ " + t(lang, "button_back"), callback_data="back"
                )
            ]
        ]
    )


# ✅ Donation amounts
def create_donate_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "donate_300"), callback_data="donate_300"
                ),
                InlineKeyboardButton(
                    text=t(lang, "donate_500"), callback_data="donate_500"
                ),
                InlineKeyboardButton(
                    text=t(lang, "donate_700"), callback_data="donate_700"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ " + t(lang, "button_back"), callback_data="back"
                )
            ],
        ]
    )


# ✅ Donation providers
def create_paymont2_keyboard(lang: str, amount: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Aaio.so", callback_data=f"pay_aaio_{amount}")],
            [
                InlineKeyboardButton(
                    text="RuKassa", callback_data=f"pay_rukassa_{amount}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ " + t(lang, "button_back"), callback_data="back"
                )
            ],
        ]
    )


# ✅ Bust size options
def create_bust_size_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Small", callback_data="bust_small"),
                InlineKeyboardButton(text="Medium", callback_data="bust_medium"),
            ],
            [
                InlineKeyboardButton(text="Large", callback_data="bust_large"),
                InlineKeyboardButton(text="Extra Large", callback_data="bust_xlarge"),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ " + t(lang, "button_back"), callback_data="back"
                )
            ],
        ]
    )
