# Chestniy Znak Desktop

Desktop-клиент для сценариев Честного знака. Приложение пишется на Python 3 и
PySide6 Widgets. Основной ввод кодов идет через COM/SPP-сканер, без камеры.

## Архитектурные правила

- UI живет только в `ui/` и не содержит бизнес-логики.
- Связь UI с сервисами живет в `controllers/`.
- Работа с backend живет в `api/`.
- Предметные модели и нормализация кодов живут в `domain/`.
- COM/SPP-сканер живет в `scanner/`.
- WebSocket и глобальное состояние приложения живут в `runtime/`.
- Звуки и другие прикладные сервисы живут в `services/`.
- Каждая функция и класс получают короткий docstring на русском.
- Новая логика покрывается unit-тестами и mock-тестами.

## Структура

```text
src/chestniy_znak_desktop/
  app/          # запуск, bootstrap, конфигурация, логирование
  controllers/  # orchestration между UI и сервисами
  api/          # HTTP-клиент, DTO, сервисы backend
  domain/       # предметная логика без UI и сети
  runtime/      # состояние приложения и WebSocket
  scanner/      # COM/SPP-ввод
  services/     # прикладные сервисы приложения
  ui/           # окна, экраны, виджеты, темы
  resources/    # звуки и иконки
tests/          # unit и mock-тесты
```

## Локальная проверка

```bash
python -m pip install -e ".[dev,build]"
pre-commit install
python -m black --check .
python -m flake8
python -m mypy
python -m pytest
```

## Сборка Windows

Windows-сборку нужно выполнять на Windows с Windows Python. PyInstaller не
собирает корректный `.exe` из Linux/Docker Linux-окружения, потому что для
PySide6 нужны Windows wheels и Windows Qt DLL.

### Требования

- Windows 10/11 x64 или Windows Server x64.
- Python 3.11+ x64. На Python 3.14 можно пробовать сборку, если `pip`
  смог поставить Windows wheels для PySide6 и PyInstaller.
- Доступ к интернету для установки зависимостей через `pip`.
- PowerShell от обычного пользователя. Администратор не нужен.
- Inno Setup 6, если нужен установщик `setup.exe`.
- Опционально: Microsoft Visual C++ Redistributable 2015-2022 x64, если на
  целевом ПК еще не стоит runtime для приложений на C++.

Проверка Python:

```powershell
py -3.14 --version
py -3.14 -c "import struct; print(struct.calcsize('P') * 8)"
```

Вторая команда должна вывести `64`.

### Подготовка проекта

Открыть PowerShell в корне проекта:

```powershell
cd C:\path\to\ChestniyZnakDescktop
```

Перед каждой сборкой сначала забрать свежий код:

```powershell
git fetch origin
git status
git pull --ff-only
git log -1 --oneline
py -3.14 -c "import sys; sys.path.insert(0, 'src'); import chestniy_znak_desktop; print(chestniy_znak_desktop.__version__)"
```

Последняя команда должна вывести актуальную версию приложения, например `1.0.0`.
Если выводится старая версия, сборка идет не из свежего checkout или не из этой
папки проекта.

Создать виртуальное окружение:

```powershell
py -3.14 -m venv .venv
```

Обновить `pip`:

```powershell
.\.venv\Scripts\python.exe -m pip install -U pip setuptools wheel
```

Поставить зависимости для сборки:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Проверить, что зависимости поставились именно в это окружение:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import httpx, pydantic, serial, PySide6, PyInstaller; print('deps ok')"
```

Для полной локальной проверки перед сборкой:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Если на Python 3.14 `pip` не найдет wheels для PySide6/PyInstaller, нужно
поставить Python 3.11/3.12 x64, удалить `.venv` и повторить шаги подготовки.

### Сборка

Запустить сборку portable-папки:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows.py
```

Результат появится здесь:

```text
dist\ChestniyZnakDesktop\ChestniyZnakDesktop.exe
```

Сборка использует `packaging/chestniy_znak_desktop.spec`, кладет результат в
`dist/ChestniyZnakDesktop/` и включает runtime-ресурсы приложения: звуки,
иконки и Qt-модули для WebSocket/Multimedia.

### Сборка установщика setup.exe

Установить Inno Setup 6:

```text
https://jrsoftware.org/isinfo.php
```

При установке можно оставить параметры по умолчанию. Скрипт сборки сам ищет
`ISCC.exe` в `PATH` и в стандартной папке `Program Files`.

Собрать приложение и установщик одной командой:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows_installer.py
```

Команда делает три шага:

- собирает приложение через PyInstaller в `dist\ChestniyZnakDesktop\`;
- рендерит векторные SVG-картинки установщика в BMP для Inno Setup;
- компилирует `setup.exe` через `packaging\windows_installer.iss`.

Готовый установщик появится здесь:

```text
installer\ChestniyZnakDesktopSetup-1.0.0.exe
```

Установщик делает:

- установку в `C:\Program Files\ChestniyZnakDesktop`;
- ярлык в меню Пуск;
- опциональный ярлык на рабочем столе;
- запись uninstall в Windows;
- запуск приложения после установки, если пользователь оставит галочку.

Картинки мастера установки лежат в векторном виде:

```text
packaging\installer_assets\installer_wizard.svg
packaging\installer_assets\installer_small.svg
```

BMP-файлы рядом с ними генерируются автоматически при сборке установщика и не
нужны в git.

### Проверка собранного приложения

Запустить из PowerShell:

```powershell
.\dist\ChestniyZnakDesktop\ChestniyZnakDesktop.exe
```

Проверить:

- открывается экран авторизации;
- QR логина читается HID-сканером или COM/SPP-сканером;
- в настройках виден нужный COM-порт, например `COM3`;
- WebSocket соединение активно;
- звук проигрывается при успешной отправке автоскана-бокса в коробку;
- экран автоупаковки показывает вкладки `Локальный бокс` и `Текущая коробка`.

Папка пользовательских настроек на Windows:

```text
C:\Users\<user>\.chestniy_znak_desktop\
```

Там хранятся настройки, cookies и логи приложения.

### Передача на рабочий ПК

Копировать нужно всю папку:

```text
dist\ChestniyZnakDesktop\
```

Не копировать только один `.exe`, потому что рядом лежат Qt DLL, Python DLL,
модули PySide6 и ресурсы приложения.

### Чистая пересборка

Если нужно пересобрать с нуля или на Windows собирается старая версия, сначала
остановить приложение и удалить старые артефакты сборки:

```powershell
Get-Process ChestniyZnakDesktop -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item -Recurse -Force build, dist, installer -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache, .mypy_cache -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
.\.venv\Scripts\python.exe scripts\build_windows.py
```

Для максимально чистой пересборки можно пересоздать виртуальное окружение:

```powershell
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\build_windows.py
```

Если собирается установщик:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows_installer.py
```

После установки `setup.exe` убедиться, что запускается новая установленная
версия, а не старый portable `.exe` из другой папки. Если сомневаетесь, удалить
старую установленную программу через `Параметры Windows -> Приложения` и
поставить новый `installer\ChestniyZnakDesktopSetup-1.0.0.exe`.

### Частые проблемы

Собирается старая версия:

- Проверить, что PowerShell открыт именно в свежей папке проекта:

```powershell
pwd
git log -1 --oneline
git status
```

- Проверить версию из исходников:

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import chestniy_znak_desktop; print(chestniy_znak_desktop.__version__)"
```

- Удалить `build`, `dist`, `installer`, `__pycache__` и при необходимости
  пересоздать `.venv` по инструкции `Чистая пересборка`.
- Проверить, что запускается новый файл из `dist\ChestniyZnakDesktop\`, а не
  старый `.exe` или старый ярлык после установки.

`py -3.11` не найден:

- Python 3.11 не установлен или не добавлен Python Launcher.
- Установить Python 3.11 x64 с python.org.

`running scripts is disabled`:

- Не обязательно активировать `.venv`; команды выше вызывают
  `.\.venv\Scripts\python.exe` напрямую.
- Если все же нужна активация:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Антивирус ругается на `.exe`:

- Для внутренних PyInstaller-сборок это бывает.
- Добавить папку сборки в исключения или подписать бинарник корпоративным
  сертификатом, если он есть.

COM-порт не виден:

- Проверить `Диспетчер устройств -> Порты COM и LPT`.
- Проверить драйвер USB-COM адаптера.
- Проверить, что порт не занят другой программой.
- HID-сканер можно использовать без COM-порта, но для надежного промышленного
  сценария предпочтительнее COM/SPP.

Приложение не стартует после переноса:

- Запускать `.exe` из папки `dist\ChestniyZnakDesktop\`.
- Не удалять соседние `.dll`, `_internal` и ресурсные файлы.
- Запустить из PowerShell, чтобы увидеть возможный текст ошибки.

### Что коммитить после сборки

Папки `build/` и `dist/` не коммитятся. Это артефакты сборки, они уже
исключены в `.gitignore`.

Папка `installer/` тоже не коммитится. Готовый `setup.exe` является артефактом
сборки.
