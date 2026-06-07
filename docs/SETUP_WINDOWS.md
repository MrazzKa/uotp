# Настройка UOTP на Windows с диском D:

Проект рассчитан на разработку на Windows, при этом тяжелые данные Docker, WSL и репозиторий лучше держать на диске `D:`.

## 1. Репозиторий

```powershell
New-Item -ItemType Directory -Force D:\dev | Out-Null
git clone <repo-url> D:\dev\uotp
Set-Location D:\dev\uotp
```

## 2. Docker Desktop на D:

В Docker Desktop откройте:

`Settings -> Resources -> Advanced -> Disk image location`

Укажите:

```text
D:\docker-data
```

Нажмите `Apply & Restart`.

## 3. Перенос WSL2-дистрибутива на D:

Список дистрибутивов:

```powershell
wsl -l -v
```

Остановить WSL:

```powershell
wsl --shutdown
```

Экспортировать дистрибутив, например `Ubuntu`:

```powershell
New-Item -ItemType Directory -Force D:\wsl | Out-Null
wsl --export Ubuntu D:\wsl\Ubuntu.tar
```

Удалить старую регистрацию:

```powershell
wsl --unregister Ubuntu
```

Импортировать на диск `D:`:

```powershell
wsl --import Ubuntu D:\wsl\Ubuntu D:\wsl\Ubuntu.tar --version 2
```

Проверить:

```powershell
wsl -l -v
```

## 4. Проверка инструментов

```powershell
docker --version
docker compose version
wsl -l -v
```

## 5. Первый запуск UOTP

Скопируйте пример env-файла:

```powershell
Copy-Item infra\.env.example infra\.env
```

Запустите инфраструктуру:

```powershell
docker compose -f infra\docker-compose.yml --env-file infra\.env up --build
```

Проверка расширений PostgreSQL:

```powershell
docker compose -f infra\docker-compose.yml --env-file infra\.env exec db psql -U uotp -d uotp -c "\dx"
```
