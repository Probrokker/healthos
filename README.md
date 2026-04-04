# 🏥 Health-OS — Семейный медицинский ассистент

AI-агент для управления здоровьем семьи: Кирилл, София, Аня, Лука, Фёдор.

## Архитектура

```
health-os/
├── backend/          # Python FastAPI + Telegram Bot + AI-агенты
│   ├── bot.py        # Telegram Bot (все команды)
│   ├── api.py        # REST API для дашборда
│   ├── main.py       # Точка входа (запускает оба)
│   ├── agents/
│   │   ├── base_agent.py       # AI специалисты (Claude API)
│   │   ├── lab_parser.py       # Парсинг анализов (Claude Vision)
│   │   ├── who_percentiles.py  # Перцентили ВОЗ
│   │   └── vaccines_calendar.py # Нацкалендарь прививок РФ
│   ├── models/
│   │   ├── database.py         # SQLAlchemy модели
│   │   └── profiles_seed.py    # Начальные профили
│   └── services/
│       └── context_builder.py  # Сборка контекста для агентов
└── dashboard/        # Next.js 14 дашборд
```

## Деплой на Railway

### 1. PostgreSQL
Добавьте PostgreSQL плагин в Railway → скопируйте DATABASE_URL

### 2. Backend сервис
- Root Directory: `backend`
- Environment Variables:
  ```
  DATABASE_URL=<из PostgreSQL плагина>
  TELEGRAM_BOT_TOKEN=8354787604:AAHPU5FlrOMkkIJ2Do3IugHIfnXu03pXlzI
  CLAUDE_API_KEY=<ваш ключ>
  ALLOWED_USER_IDS=<ваш Telegram ID>
  RUN_MODE=both
  PORT=8000
  ```

### 3. Dashboard сервис
- Root Directory: `dashboard`
- Environment Variables:
  ```
  NEXT_PUBLIC_API_URL=<URL бэкенда с Railway>
  ```

### Получить свой Telegram ID
Напишите [@userinfobot](https://t.me/userinfobot) в Telegram

## Локальный запуск (Docker Compose)

```bash
cp .env.example .env
# отредактируйте .env
docker-compose up -d
```

Дашборд: http://localhost:3000  
API docs: http://localhost:8000/docs

## Команды Telegram-бота

| Команда | Описание |
|---------|----------|
| `/start` | Список команд |
| `/профиль [имя]` | Показать профиль |
| `/labs [имя] [показатель]` | Тренд показателя |
| `/рост [имя] [рост] [вес]` | Записать/показать рост/вес |
| `/прививки [имя]` | Статус вакцинации |
| `/консилиум [имя] [проблема]` | Полный AI-анализ |
| `/врач [имя] подготовь к [специальность]` | Чеклист к врачу |
| `/врач [имя] был у [специальность]` | Записать визит |
| `/лекарство [имя]` | Список/добавление лекарств |
| 📸 Фото/PDF анализа | Автораспознавание и сохранение |

## AI-агенты

### Взрослый профиль (Кирилл)
- Кардиолог, Эндокринолог, Гематолог
- Гастроэнтеролог, Невролог, Нутрициолог

### Детские профили
- Педиатр, Гематолог (дет.), Аллерголог
- ЛОР, Стоматолог, Ортопед, Офтальмолог, Невролог (дет.)

Команда `/консилиум` запускает всех агентов параллельно → синтезирующий агент создаёт единый отчёт.
