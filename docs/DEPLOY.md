# Deploy

Минимальный путь: **Fly.io (бэкенд)** + **Vercel (фронт)**. Полностью бесплатный, кроме ~$1/мес за volume на Fly (если включишь).

## 0. Перед началом — ОБЯЗАТЕЛЬНО

- [ ] Ротировать ключи `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` (они пастились в чате — считать скомпрометированными)
- [ ] Убедиться, что `.env.local` в `.gitignore` (уже там)
- [ ] `git init && git add .` если репозитория ещё нет

## 1. Backend → Fly.io (~15 мин)

```bash
# Установить CLI (если нет)
brew install flyctl
fly auth signup   # или fly auth login

# В корне проекта
fly launch --no-deploy --copy-config --name kazmedsim-api
# (при вопросе про Postgres → нет; про Redis → нет; volume — fly создаст из fly.toml)

# Создать volume (1 GB достаточно)
fly volumes create kazmedsim_data --size 1 --region fra

# Секреты
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set OPENAI_API_KEY=sk-proj-...
fly secrets set ALLOWED_ORIGINS=https://<твой-frontend>.vercel.app,http://localhost:3000

# Деплой
fly deploy
```

После деплоя URL бэкенда: `https://kazmedsim-api.fly.dev`. Проверь:

```bash
curl https://kazmedsim-api.fly.dev/api/scenarios?lang=ru | head -c 200
```

## 2. Frontend → Vercel (~5 мин)

1. Push в GitHub
2. На vercel.com → New Project → импорт репо
3. Framework auto-detect (Next.js) — оставить дефолты
4. **Environment Variables** → добавить:
   - `NEXT_PUBLIC_API_URL = https://kazmedsim-api.fly.dev`
5. Deploy → получишь URL `https://<project>.vercel.app`
6. **Вернуться к Fly** и обновить CORS:
   ```bash
   fly secrets set ALLOWED_ORIGINS=https://<project>.vercel.app,http://localhost:3000
   ```

## 3. Проверка

- Открой `https://<project>.vercel.app` → главная грузится
- «Начать приём» → онбординг → выбор пациента → должны прийти 49 случаев
- Запусти сессию → пациент отвечает → ИИ-ассистент отвечает
- Любая ошибка в DevTools Network — обычно CORS или env не подхватился

## Альтернативы

- **Railway** — тоже работает с Dockerfile, $5/мес минимум, но проще UI
- **Render** — нужен `Persistent Disk` ($1/мес) для SQLite, Dockerfile подхватится автоматически
- **Свой VPS** — `docker build -t kazmedsim . && docker run -p 8000:8000 -v $(pwd)/db:/app/db --env-file .env.local kazmedsim`

## Локальная проверка Docker (опционально, перед деплоем)

```bash
docker build -t kazmedsim-api .
docker run --rm -p 8000:8000 \
  -v "$(pwd)/db:/app/db" \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ALLOWED_ORIGINS=http://localhost:3000 \
  kazmedsim-api
```

Открой http://localhost:8000/api/scenarios?lang=ru — должен ответить.
