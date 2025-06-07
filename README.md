# 🤖 my_bot – Telegram AI бот с реферальной системой

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![Aiogram](https://img.shields.io/badge/Aiogram-2.14-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

---

## 📌 Описание

`my_bot` — это умный Telegram-бот, который:
- Обрабатывает пользовательские фото с помощью AI
- Имеет реферальную систему с начислением токенов
- Поддерживает мультиязычный интерфейс (EN, RU, 中文, FR, ES)
- Предлагает оплату через RuKassa и Aaio
- Имеет админ-панель для статистики и рассылок

---

## 🚀 Быстрый старт

1. **Клонируй проект:**

```bash
git clone https://github.com/stilix1/my_bot.git
cd my_bot
```

2. **Создай виртуальное окружение и активируй его:**

```bash
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate    # Linux/Mac
```

3. **Установи зависимости:**

```bash
pip install -r requirements.txt
```

4. **Создай `.env` файл:**

```env
BOT_TOKEN=your_telegram_token
RUKASSA_SHOP_ID=...
RUKASSA_TOKEN=...
AAIO_SHOP_ID=...
AAIO_TOKEN=...
DB_URL=postgresql://user:pass@localhost/dbname
```

5. **Запусти бота:**

```bash
python bot.py
```

---

## 🧪 Тестирование и покрытие

```bash
coverage run -m pytest
coverage report -m
```

---

## 🛠 Стек технологий

- **Python 3.10**
- **Aiogram 2.14**
- PostgreSQL
- AsyncPG
- Aiohttp / Requests
- YAML для переводов
- Docker (опционально)

---

## 📁 Структура проекта

```
my_bot/
├── handlers/         # Хендлеры команд и callback'ов
├── services/         # Работа с API и БД
├── utils/            # Утилиты, i18n, prompts
├── locales/          # Языковые файлы
├── prompts/          # YAML-файлы с пресетами и bust'ами
├── tests/            # Тесты
├── tmp/              # Временные файлы
├── bot.py            # Главный скрипт
└── requirements.txt
```

---

## 👨‍💻 Автор

**[@stilix1](https://github.com/stilix1)**  


---
