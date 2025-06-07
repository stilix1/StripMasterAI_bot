import os
import yaml


PROMPTS = {}
BUSTS = {}


def _load_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_prompts():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    global PROMPTS, BUSTS
    PROMPTS = _load_yaml(os.path.join(base_dir, "prompts.yaml"))
    BUSTS = _load_yaml(os.path.join(base_dir, "busts.yaml"))


def get_prompt(key: str) -> str:
    return PROMPTS.get(key, "")


def get_bust(key: str) -> str:
    return BUSTS.get(key, "")


# Автозагрузка при импорте
load_all_prompts()
