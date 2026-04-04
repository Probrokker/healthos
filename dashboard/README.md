# Health-OS Dashboard

Семейный медицинский дашборд на Next.js 14 (App Router).

## Запуск

```bash
# Установка зависимостей
npm install

# Разработка
npm run dev

# Продакшн-сборка
npm run build
npm start
```

## Конфигурация

Создайте `.env.local` (или используйте `.env.example` как шаблон):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Страницы

| URL | Описание |
|---|---|
| `/` | Семейный обзор — карточки всех членов семьи |
| `/profile/[id]` | Профиль: статистика, последние визиты, лекарства |
| `/profile/[id]/labs` | Все анализы с выделением отклонений |
| `/profile/[id]/trend?marker=NAME` | Динамика маркера во времени |
| `/profile/[id]/growth` | График роста (рост/вес на двойной оси) |

## API Endpoints

- `GET /family/overview` — сводка по всем профилям
- `GET /profiles` — список профилей
- `GET /profiles/{id}` — профиль
- `GET /profiles/{id}/labs` — анализы
- `GET /profiles/{id}/labs/trend?marker=NAME` — тренд маркера
- `GET /profiles/{id}/visits` — визиты к врачу
- `GET /profiles/{id}/growth` — рост/вес
- `GET /profiles/{id}/medications?active_only=true` — лекарства
- `GET /profiles/{id}/stats` — сводная статистика

## Стек

- **Next.js 14** (App Router, серверные компоненты)
- **Recharts** — все графики
- **Tailwind CSS** — стилизация
- **TypeScript**

## Цветовая схема

| Назначение | Цвет |
|---|---|
| Фон | `#0f1117` |
| Карточки | `#1a1d27` |
| Акцент | `#6366f1` |
| Норма | `#22c55e` |
| Отклонение | `#f59e0b` |
| Критично | `#ef4444` |

## Семья

| Имя | Дата рождения |
|---|---|
| Кирилл | 14.09.1989 |
| София | 28.11.2015 |
| Аня | 04.03.2019 |
| Лука | 06.04.2023 |
| Федор | 12.09.2025 |
