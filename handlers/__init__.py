from aiogram import Dispatcher

from .admin import register_admin_handlers
from .donate import register_donate_handlers
from .menu import register_menu_handlers
from .photo import register_photo_handlers
from .start import register_start_handlers


def register_handlers(dp: Dispatcher):
    register_start_handlers(dp)
    register_admin_handlers(dp)
    register_menu_handlers(dp)
    register_photo_handlers(dp)
    register_donate_handlers(dp)
