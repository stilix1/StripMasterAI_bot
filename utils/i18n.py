import yaml
import os
import re
from collections import defaultdict

# Загружаем переводы
TRANSLATIONS = {}
PROMPTS = {}
BUSTS = {}


def _load_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_translations():
    locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
    for filename in os.listdir(locales_dir):
        if filename.endswith(".yaml"):
            lang_code = filename.split(".")[0]
            TRANSLATIONS[lang_code] = _load_yaml(os.path.join(locales_dir, filename))


def load_prompts():
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    global PROMPTS, BUSTS
    PROMPTS = _load_yaml(os.path.join(prompts_dir, "prompts.yaml"))
    BUSTS = _load_yaml(os.path.join(prompts_dir, "busts.yaml"))


# Инициализация при импорте
load_translations()
load_prompts()


def t(lang: str, key: str, **kwargs) -> str:
    lang_data = TRANSLATIONS.get(lang, {})
    template = lang_data.get(key, key)

    template = re.sub(r"{{(\w+)}}", r"{\1}", template)
    return template.format_map(defaultdict(str, kwargs))


async def get_user_language(user_id: str, repo_user) -> str:
    lang = await repo_user.get_language(str(user_id))
    return lang or "en"
