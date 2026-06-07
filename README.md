# UOTP

UOTP (Urban Operations Task Platform) — платформа для акимата: регистрация, квалификация, исполнение и мониторинг городских задач. Сейчас в репозитории собран фундамент: окружение, авторизация, web-портал и мобильный каркас с ролевыми экранами-заглушками.

## Быстрый старт на Windows

Сначала проверьте [docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md), если Docker/WSL/репозиторий нужно держать на диске `D:`.

```powershell
Copy-Item infra\.env.example infra\.env
docker compose -f infra\docker-compose.yml --env-file infra\.env up --build
```

В отдельном терминале примените миграции и создайте demo-данные:

```powershell
Set-Location backend
alembic upgrade head
python -m app.seed
```

## Backend

```powershell
Set-Location backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Swagger доступен на `http://localhost:8000/docs`.

## Web

```powershell
Set-Location web
npm install
npm run dev
```

Портал доступен на `http://localhost:5173`.

## Mobile

Для телефона в локальной сети укажите IP машины с backend в `mobile/app.json`, поле `expo.extra.apiUrl`, например `http://192.168.1.10:8000/api/v1`.

```powershell
Set-Location mobile
npm install
npx expo start
```

## Demo-логины

Пароль для всех пользователей: `demo123`.

| Роль | Email |
| --- | --- |
| ADMIN | `admin@uotp.local` |
| DISPATCHER | `dispatcher@uotp.local` |
| EXECUTOR | `executor@uotp.local` |
| AKIM | `akim@uotp.local` |
| INSPECTOR | `inspector@uotp.local` |
