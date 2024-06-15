from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import translations


# Replay keyboard commands
def replay_keyboard():
    ikb_reply_start = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    reply1_start = KeyboardButton(text='💼Menu')
    ikb_reply_start.add(reply1_start)
    return ikb_reply_start


# Start command keyboard _________________________________________________________
ikb_start = InlineKeyboardMarkup(row_width=2)
ib1_start = InlineKeyboardButton(text='Русский', callback_data='ru')
ib2_start = InlineKeyboardButton(text='English', callback_data='en')
ib3_start = InlineKeyboardButton(text='中国人', callback_data='chinese')
ib4_start = InlineKeyboardButton(text='Français', callback_data='fr')
ib5_start = InlineKeyboardButton(text='Español', callback_data='es')

ikb_start.add(ib1_start, ib2_start, ib3_start, ib4_start, ib5_start)


def create_terms_keyboard(user_lang):
    # Terms of use keyboard _________________________________________________________
    ikb_terms = InlineKeyboardMarkup(row_width=1)
    ib1_terms = InlineKeyboardButton(text=translations.translations_list[user_lang]['button_terms_yes'] + "👍",
                                     callback_data='terms_yes')
    ib2_terms = InlineKeyboardButton(text=translations.translations_list[user_lang]['button_terms_no'] + "👎",
                                     callback_data='terms_no')
    ikb_terms.add(ib1_terms, ib2_terms)
    return ikb_terms


def create_cancel_keyboard(user_lang):
    ikb_cancel = InlineKeyboardMarkup(row_width=1)
    ib_cancel = InlineKeyboardButton(text="❌ Cancel", callback_data='cancel')
    ikb_cancel.add(ib_cancel)
    return ikb_cancel


def create_menu_keyboard(user_lang):
    # Main menu keyboard _________________________________________________________
    ikb_menu = InlineKeyboardMarkup(row_width=2)
    ib1_menu = InlineKeyboardButton(text="🔞 " + translations.translations_list[user_lang]['button_send_photo_api'],
                                    callback_data='send_photo_api')
    ib2_menu = InlineKeyboardButton(text="🪪 " + translations.translations_list[user_lang]['button_profile'],
                                    callback_data='profile')
    ib3_menu = InlineKeyboardButton(text="📣 " + translations.translations_list[user_lang]['button_supp'],
                                    url='t.me/vladimirskiyandrey')
    ib4_menu = InlineKeyboardButton(text="🚻" + translations.translations_list[user_lang]['button_referral'],
                                    callback_data='referral')
    ikb_menu.add(ib1_menu).add(ib2_menu, ib3_menu).add(ib4_menu)
    return ikb_menu


def create_preset_keyboard(user_lang):
    # Preset keyboard _________________________________________________________
    ikb_preset = InlineKeyboardMarkup(row_width=1)
    ib_preset3 = InlineKeyboardButton(text="Women", callback_data='prompt_women3')
    ib_preset_back = InlineKeyboardButton(text="⬅️ " + translations.translations_list[user_lang]['button_back'],
                                          callback_data='back')
    ikb_preset.add(ib_preset3).add(ib_preset_back)
    return ikb_preset


def create_profile_keyboard(user_lang):
    # Profile keyboard _________________________________________________________
    ikb_profile = InlineKeyboardMarkup(row_width=2)
    ib1_profile = InlineKeyboardButton(text="🔞 " + translations.translations_list[user_lang]['button_send_photo_api'],
                                       callback_data='send_photo_api')
    ib2_profile = InlineKeyboardButton(text="🚻 " + translations.translations_list[user_lang]['button_referral'],
                                       callback_data='referral')
    ib3_profile = InlineKeyboardButton(text=translations.translations_list[user_lang]['button_donate'],
                                       callback_data='donate')
    ib4_profile = InlineKeyboardButton(text="⬅️ " + translations.translations_list[user_lang]['button_back'],
                                       callback_data='back')
    ikb_profile.add(ib1_profile).add(ib2_profile, ib3_profile).add(ib4_profile)
    return ikb_profile


def create_ref_keyboard(user_lang):
    # Referral keyboard _________________________________________________________
    ikb_ref = InlineKeyboardMarkup(row_width=1)
    ib1_ref = InlineKeyboardButton(text=translations.translations_list[user_lang]['button_donate'],
                                   callback_data='donate')
    ib3_ref = InlineKeyboardButton(text="⬅️ " + translations.translations_list[user_lang]['button_back'],
                                   callback_data='back')
    ikb_ref.add(ib1_ref).add(ib3_ref)
    return ikb_ref


def create_back_keyboard(user_lang):
    # Back keyboard _________________________________________________________
    ikb_back = InlineKeyboardMarkup(row_width=1)
    ib_back = InlineKeyboardButton(text="⬅️ " + translations.translations_list[user_lang]['button_back'],
                                   callback_data='back')
    ikb_back.add(ib_back)
    return ikb_back


def create_donate_keyboard(user_lang):
    # Donate keyboard _________________________________________________________
    ikb_donate = InlineKeyboardMarkup(row_width=1)
    ib1_donate = InlineKeyboardButton(text=translations.translations_list[user_lang]['donate_300'],
                                      callback_data='donate_300')
    ib2_donate = InlineKeyboardButton(text=translations.translations_list[user_lang]['donate_500'],
                                      callback_data='donate_500')
    ib3_donate = InlineKeyboardButton(text=translations.translations_list[user_lang]['donate_700'],
                                      callback_data='donate_700')
    ib4_donate = InlineKeyboardButton(text="⬅️ " + translations.translations_list[user_lang]['button_back'],
                                      callback_data='back')
    ikb_donate.add(ib1_donate, ib2_donate, ib3_donate).add(ib4_donate)
    return ikb_donate


def create_paymont2_keyboard(user_lang, amount):
    ikb_paymont2 = InlineKeyboardMarkup(row_width=1)
    ikb1_paymont2 = InlineKeyboardButton(text="Aaio.so", callback_data=f'pay_aaio_{amount}')
    ikb2_paymont2 = InlineKeyboardButton(text="RuKassa", callback_data=f'pay_rukassa_{amount}')
    ib4_paymont2 = InlineKeyboardButton(text="⬅️ " + translations.translations_list[user_lang]['button_back'], callback_data='back')

    ikb_paymont2.add(ikb1_paymont2, ikb2_paymont2, ib4_paymont2)
    return ikb_paymont2


def create_bust_size_keyboard(user_lang):
    # Bust size keyboard _________________________________________________________
    ikb_bust_size = InlineKeyboardMarkup(row_width=2)
    ib1_bust_size = InlineKeyboardButton(text="Small", callback_data='bust_small')
    ib2_bust_size = InlineKeyboardButton(text="Medium", callback_data='bust_medium')
    ib3_bust_size = InlineKeyboardButton(text="Large", callback_data='bust_large')
    ib4_bust_size = InlineKeyboardButton(text="Extra Large", callback_data='bust_xlarge')
    ikb_bust_size.add(ib1_bust_size, ib2_bust_size).add(ib3_bust_size, ib4_bust_size)
    ikb_bust_size.add(InlineKeyboardButton(text="⬅️ " + translations.translations_list[user_lang]['button_back'],
                                           callback_data='back'))
    return ikb_bust_size
