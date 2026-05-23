# CLAUDE.md — KazMedSim: Симулятор поликлиники (KZ/RU)

> Этот файл — главная инструкция для Claude Code.
> Читай его полностью перед тем как писать любой код.

---

## 🎯 Цель проекта

Создать браузерный симулятор поликлиники для обучения студентов-медиков Казахстана.
Вдохновлён проектом MedKit (https://github.com/bedriyan/medkit-app), победителем хакатона Built with Opus 4.7.

**Режим: Поликлиника**
- Один амбулаторный пациент за раз
- Результаты анализов — мгновенные
- Студент играет роль врача
- ИИ-куратор оценивает каждую сессию

---

## 🌐 Языки

Интерфейс и все диалоги поддерживают два языка:
- **Русский (ru)** — по умолчанию
- **Казахский (kk)** — полноценный, не машинный перевод

Переключение языка — кнопка в шапке. Язык сохраняется в localStorage.
Все клинические сценарии хранятся в обоих языках параллельно.

---

## 🏗️ Архитектура

```
kazmeds im/
├── src/                  # Next.js фронтенд (TypeScript)
│   ├── app/              # App Router
│   ├── components/       # UI компоненты
│   ├── i18n/             # Переводы kk / ru
│   └── lib/              # API клиент, утилиты
├── backend/              # FastAPI (Python)
│   ├── main.py           # Роуты API
│   ├── scenarios.py      # Загрузка сценариев из БД
│   ├── grader.py         # Логика оценки куратором
│   └── prompts/          # Системные промпты для Claude
├── db/
│   └── kazmeds im.db     # SQLite база данных
├── scripts/
│   └── seed_db.py        # Заполнение БД сценариями
└── .env.local            # Ключи API (не коммитить!)
```

---

## 🔑 API ключи и окружение

Используй **Anthropic API** (не OpenAI). Ключ берётся из переменной окружения.

Файл `.env.local` в корне проекта:
```env
ANTHROPIC_API_KEY=sk-ant-...       # Твой ключ Anthropic
ELEVENLABS_API_KEY=...             # Для TTS (опционально)
DEEPGRAM_API_KEY=...               # Для STT (опционально)
```

**Никогда не хардкодь ключи в коде. Всегда читай из process.env.**

В backend Python:
```python
import os
from anthropic import Anthropic
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
```

В frontend Next.js — ключи только серверные, браузер их никогда не видит.

---

## 🤖 Модель Claude

Используй: `claude-opus-4-5` или `claude-sonnet-4-5` (проверь актуальность через context7 MCP)

**Два агента в системе:**

### 1. Агент-пациент
- Играет роль больного
- Говорит от первого лица
- Отвечает на вопросы студента
- Жалуется, уточняет, иногда нервничает
- Не знает своего диагноза
- Язык ответа = язык интерфейса

### 2. Агент-куратор (после сессии)
- Оценивает действия студента
- Даёт развёрнутую обратную связь
- Ссылается на протоколы МЗ РК и международные руководства
- Выставляет баллы по рубрикам
- Пишет на языке интерфейса

---

## 📋 Системные промпты

### Промпт пациента (файл: `backend/prompts/patient_ru.txt`)
```
Ты — пациент на приёме у врача в поликлинике Казахстана.
Имя: {name}, возраст: {age}, пол: {gender}.
Твои жалобы: {chief_complaint}.
История болезни: {history}.
Аллергии: {allergies}.

Правила поведения:
- Отвечай коротко, как обычный человек (2-4 предложения)
- Не называй диагноз сам — ты не врач
- Если тебя спросят о симптомах — описывай их своими словами
- Можешь быть немного тревожным или усталым
- Если вопрос непонятен — переспроси
- Отвечай строго на {language}
```

### Промпт куратора (файл: `backend/prompts/grader_ru.txt`)
```
Ты — опытный врач-куратор, оцениваешь работу студента-медика.

Транскрипт сессии:
{transcript}

Диагноз сценария: {correct_diagnosis}
Назначенное лечение студентом: {student_treatment}
Язык оценки: {language}

Оцени по рубрикам (каждая 0-10 баллов):
1. Сбор анамнеза
2. Общение с пациентом
3. Клиническое мышление
4. Правильность диагноза
5. Адекватность лечения

Для каждой рубрики:
- Балл
- Что сделано хорошо
- Что можно улучшить
- Ссылка на протокол (МЗРК / NICE / ESC / ВОЗ если применимо)

Итоговый балл = среднее. Заверши ободряющим комментарием.
```

---

## 🗄️ База данных SQLite

### Схема (файл: `db/schema.sql`)

```sql
CREATE TABLE scenarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,           -- 'pneumonia_adult'
  difficulty TEXT NOT NULL,            -- 'easy' | 'medium' | 'hard'
  disease_ru TEXT NOT NULL,
  disease_kk TEXT NOT NULL,
  patient_name_ru TEXT NOT NULL,
  patient_name_kk TEXT NOT NULL,
  patient_age INTEGER NOT NULL,
  patient_gender TEXT NOT NULL,        -- 'male' | 'female'
  chief_complaint_ru TEXT NOT NULL,
  chief_complaint_kk TEXT NOT NULL,
  history_ru TEXT NOT NULL,
  history_kk TEXT NOT NULL,
  allergies_ru TEXT DEFAULT 'Нет',
  allergies_kk TEXT DEFAULT 'Жоқ',
  lab_results_json TEXT NOT NULL,      -- JSON: {name_ru, name_kk, value, unit, normal}[]
  correct_diagnosis_ru TEXT NOT NULL,
  correct_diagnosis_kk TEXT NOT NULL,
  treatment_protocol_ru TEXT NOT NULL,
  treatment_protocol_kk TEXT NOT NULL,
  sources TEXT NOT NULL,               -- JSON: [{name, url}]
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
  student_name TEXT,
  language TEXT NOT NULL DEFAULT 'ru',
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at DATETIME,
  student_diagnosis_ru TEXT,
  student_diagnosis_kk TEXT,
  score_anamnesis REAL,
  score_communication REAL,
  score_reasoning REAL,
  score_diagnosis REAL,
  score_treatment REAL,
  score_total REAL,
  feedback_json TEXT
);

CREATE TABLE dialog_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES sessions(id),
  role TEXT NOT NULL,                  -- 'student' | 'patient'
  message TEXT NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🏥 Клинические сценарии — Казахстан

Приоритизируй болезни, актуальные для РК. Вот стартовый список:

### Лёгкие (easy)
| Slug | Болезнь (ru) | Болезнь (kk) |
|------|-------------|-------------|
| `arvi_adult` | ОРВИ у взрослого | Ересектердегі ЖРВИ |
| `hypertension_crisis` | Гипертонический криз | Гипертониялық дағдарыс |
| `gastritis_acute` | Острый гастрит | Жедел гастрит |
| `iron_deficiency_anemia` | Железодефицитная анемия | Темір тапшылығы анемиясы |
| `cystitis_female` | Цистит у женщины | Әйелдерде цистит |

### Средние (medium)
| Slug | Болезнь (ru) | Болезнь (kk) |
|------|-------------|-------------|
| `pneumonia_community` | Внебольничная пневмония | Аурухана сыртылық пневмония |
| `diabetes_t2_debut` | Дебют сахарного диабета 2 типа | 2 тип қант диабетінің дебюті |
| `tuberculosis_pulmonary` | Туберкулёз лёгких | Өкпе туберкулёзі |
| `brucellosis` | Бруцеллёз | Бруцеллёз |
| `cholecystitis_chronic` | Хронический холецистит | Созылмалы холецистит |

### Сложные (hard)
| Slug | Болезнь (ru) | Болезнь (kk) |
|------|-------------|-------------|
| `echinococcosis` | Эхинококкоз печени | Бауырдың эхинококкозы |
| `ischemic_heart_disease` | ИБС, стабильная стенокардия | Жүрек ишемиялық ауруы |
| `copd_exacerbation` | Обострение ХОБЛ | СОЗТ өршуі |
| `hypothyroidism` | Гипотиреоз | Гипотиреоз |
| `peptic_ulcer` | Язвенная болезнь желудка | Асқазан ойық жарасы |

---

## 📚 Медицинские источники (для куратора)

Куратор ОБЯЗАН ссылаться только на реальные источники:

### Казахстанские протоколы
- **МЗ РК** — https://diseases.medelement.com/list (клинические протоколы)
- **КазМедЛайн** — https://www.kazmedialine.kz
- **РЦРЗ** — https://rcrz.kz (Республиканский центр развития здравоохранения)

### Международные руководства
- **ВОЗ** — https://www.who.int/publications
- **NICE** (Великобритания) — https://www.nice.org.uk/guidance
- **ESC** (кардиология) — https://www.escardio.org/Guidelines
- **AHA** (кардиология) — https://www.heart.org/en/professional/quality-improvement
- **GOLD** (ХОБЛ) — https://goldcopd.org/2024-gold-report
- **GINA** (астма) — https://ginasthma.org/reports
- **IDF** (диабет) — https://www.idf.org/guidelines

### МКБ-10 (казахстанская классификация)
- Используй коды МКБ-10 в диагнозах
- Формат: `J18.9 — Пневмония неуточнённая`

---

## 🎨 UI/UX требования

### Стек фронтенда
```
Next.js 14+ (App Router)
TypeScript
Tailwind CSS
shadcn/ui компоненты
```

### Экраны

**1. Главный экран (`/`)**
- Выбор языка (RU / KK) — флаги + текст
- Ввод имени студента
- Кнопка "Начать приём"

**2. Выбор сценария (`/scenarios`)**
- Карточки сценариев с уровнем сложности
- Фильтр по сложности
- Название болезни на выбранном языке

**3. Кабинет врача (`/session/[id]`)**
- Слева: карточка пациента (имя, возраст, жалоба)
- Центр: чат с пациентом
- Справа: панель инструментов врача:
  - "Назначить анализы" → мгновенные результаты
  - "Поставить диагноз" → текстовое поле
  - "Назначить лечение" → текстовое поле
  - "Завершить приём"

**4. Оценка куратора (`/session/[id]/grade`)**
- Таблица баллов по рубрикам
- Развёрнутый текст обратной связи
- Итоговый балл
- Кнопка "Новый пациент"

### Дизайн
- Медицинский стиль: белый, синий (#0EA5E9), зелёный (#10B981)
- Шрифт: Inter
- Адаптивный (mobile + desktop)
- Тёмная тема не обязательна для MVP

---

## 🔄 Поток приложения

```
1. Студент выбирает язык и вводит имя
2. Выбирает сценарий из списка
3. Начинается сессия → создаётся запись в sessions
4. Студент пишет вопросы → агент-пациент отвечает (Claude API)
5. Студент нажимает "Назначить анализы" → мгновенно из lab_results_json
6. Студент вводит диагноз и лечение
7. Нажимает "Завершить приём"
8. Агент-куратор оценивает сессию (Claude API)
9. Показывается экран оценки с баллами и обратной связью
10. Студент может начать новую сессию
```

---

## ⚡ API эндпоинты (FastAPI backend)

```
POST /api/session/start
  body: { scenario_id, student_name, language }
  returns: { session_id, patient_intro }

POST /api/session/message
  body: { session_id, message }
  returns: { patient_response }

GET  /api/session/{id}/labs
  returns: { lab_results: [{name, value, unit, normal, is_abnormal}] }

POST /api/session/end
  body: { session_id, student_diagnosis, student_treatment }
  returns: { grade: { scores, feedback, total } }

GET  /api/scenarios?lang=ru&difficulty=easy
  returns: { scenarios: [...] }
```

---

## 🚀 Запуск проекта

```bash
# 1. Установка зависимостей
npm install          # фронтенд
pip install fastapi uvicorn anthropic python-dotenv  # бэкенд

# 2. Создать .env.local с ключами

# 3. Инициализировать БД
python scripts/seed_db.py

# 4. Запуск
npm run dev          # фронтенд → http://localhost:3000
uvicorn backend.main:app --reload --port 8000  # бэкенд
```

---

## ✅ Правила для Claude Code

1. **Всегда читай этот файл целиком** перед началом работы
2. **Используй context7 MCP** для проверки актуальной документации Next.js, FastAPI, Anthropic SDK
3. **Используй sqlite MCP** для работы с базой данных
4. **Используй filesystem MCP** для создания и чтения файлов
5. **Используй sequential-thinking MCP** при проектировании архитектуры и медицинской логики
6. **Не создавай моков** — всё должно работать реально
7. **Проверяй, что ключи не попадают в код** — только env переменные
8. **Каждый сценарий** должен быть на обоих языках полностью
9. **Куратор** не должен выдумывать источники — только из списка в этом файле
10. **Сначала MVP** — текстовый чат без голоса, голос добавить потом через ElevenLabs + Deepgram

---

## 📝 Дисклеймер (показывать в UI)

```
RU: Этот симулятор предназначен исключительно для учебных целей.
    Клинические случаи синтетические. Не является медицинской рекомендацией.

KK: Бұл симулятор тек оқу мақсаттары үшін арналған.
    Клиникалық жағдайлар жасанды. Бұл медициналық кеңес емес.
```

---

*Создано для хакатона. Вдохновлено MedKit by Bedirhan Keskin (Istanbul, 2026).*
