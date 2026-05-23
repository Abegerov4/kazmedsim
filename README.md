# 🏥 KazMedSim — Симулятор поликлиники

Браузерный симулятор поликлиники для обучения студентов-медиков Казахстана.  
Интерфейс и диалоги на **русском и казахском** языках.

---

## Стек

| Часть | Технологии |
|-------|-----------|
| Фронтенд | Next.js 14, TypeScript, Tailwind CSS |
| Бэкенд | FastAPI (Python), Anthropic Claude API |
| База данных | SQLite |
| AI агенты | Claude Sonnet (пациент + куратор) |

---

## Быстрый старт

### 1. Клонировать и установить зависимости

```bash
# Фронтенд
npm install

# Бэкенд
pip install -r backend/requirements.txt
```

### 2. Настроить переменные окружения

```bash
cp .env.local.example .env.local
```

Открой `.env.local` и добавь ключи:

```env
ANTHROPIC_API_KEY=sk-ant-...       # Обязательно!
ELEVENLABS_API_KEY=...             # Опционально (TTS)
DEEPGRAM_API_KEY=...               # Опционально (STT)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Инициализировать базу данных

```bash
python scripts/seed_db.py
```

Создаст 3 сценария: ОРВИ, Внебольничная пневмония, Бруцеллёз.

### 4. Запустить

```bash
# Терминал 1 — бэкенд (FastAPI)
uvicorn backend.main:app --reload --port 8000

# Терминал 2 — фронтенд (Next.js)
npm run dev
```

Открой: [http://localhost:3000](http://localhost:3000)

---

## Поток приложения

```
1. Главный экран → выбор языка (RU/KK) + имя студента
2. Выбор сценария → карточки с уровнем сложности
3. Кабинет врача:
   - Чат с пациентом (агент Claude)
   - Назначить анализы → мгновенные результаты
   - Поставить диагноз и лечение
   - Завершить приём
4. Оценка куратора → 5 рубрик, баллы, обратная связь
```

---

## Сценарии

| Slug | Болезнь | Сложность |
|------|---------|-----------|
| `arvi_adult` | ОРВИ у взрослого | Лёгкий |
| `pneumonia_community` | Внебольничная пневмония | Средний |
| `brucellosis` | Бруцеллёз | Средний |

Добавить новый сценарий: отредактируй `scripts/seed_db.py` и запусти снова.

---

## API эндпоинты

```
GET  /api/scenarios?lang=ru&difficulty=easy
POST /api/session/start      { scenario_id, student_name, language }
POST /api/session/message    { session_id, message }
GET  /api/session/{id}/labs
POST /api/session/end        { session_id, student_diagnosis, student_treatment }
```

Документация Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Структура проекта

```
├── src/                    # Next.js фронтенд
│   ├── app/                # App Router страницы
│   ├── i18n/               # Переводы RU/KK
│   └── lib/api.ts          # HTTP клиент
├── backend/
│   ├── main.py             # FastAPI роуты
│   ├── scenarios.py        # Загрузка сценариев
│   ├── grader.py           # Оценка куратором
│   └── prompts/            # Системные промпты (patient/grader × ru/kk)
├── db/
│   ├── schema.sql          # Схема базы данных
│   └── kazmeds im.db       # SQLite (не коммитить)
└── scripts/
    └── seed_db.py          # Начальные данные
```

---

## Дисклеймер

> Этот симулятор предназначен исключительно для учебных целей.  
> Клинические случаи синтетические. Не является медицинской рекомендацией.

---

*Вдохновлён MedKit by Bedirhan Keskin — победитель хакатона Built with Claude Opus 4.7.*
