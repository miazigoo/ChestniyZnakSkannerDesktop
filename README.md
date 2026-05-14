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
