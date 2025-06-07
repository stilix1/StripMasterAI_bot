import yaml
from pathlib import Path
from typing import Dict

TRANSLATIONS_DIR = Path(__file__).parent.parent / "locales"


class Translator:
    def __init__(self, default_lang: str = "en"):
        self.default_lang = default_lang
        self.translations: Dict[str, Dict[str, str]] = {}
        self.load_all()

    def load_all(self):
        for file in TRANSLATIONS_DIR.glob("*.yaml"):
            lang = file.stem
            with open(file, "r", encoding="utf-8") as f:
                self.translations[lang] = yaml.safe_load(f)

    def get(self, key: str, lang: str = None, **kwargs) -> str:
        lang = lang or self.default_lang
        entry = self.translations.get(lang, {}).get(key)

        if not entry:
            entry = self.translations.get(self.default_lang, {}).get(key, f"[{key}]")

        if kwargs:
            try:
                return entry.format(**kwargs)
            except Exception:
                return entry
        return entry


# Создаём синглтон-переводчик
translator = Translator()
