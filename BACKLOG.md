# Backlog

| Дата | Файл | Описание | Статус |
|------|------|----------|--------|
| 2026-04-23 | `scraper/cev/parser.py:26` | Косметика: лишний пробел в выравнивании константы `_DATE_RE` | открыт |
| 2026-04-23 | `scraper/cev/parser.py:31` | `_ROW_CLASSES` — `set`, поэтому `list(_ROW_CLASSES)` недетерминирован; заменить на `tuple` | открыт |
| 2026-04-23 | `scraper/cev/parser.py` | Косметика: `import datetime` → `from datetime import date, datetime` для краткости call sites | открыт |
| 2026-04-23 | `scraper/cev/parser.py:222` | Задокументировать, что `date_span` намеренно не входит в `all([...])` — матч с `date=None` корректно включается | открыт |
| 2026-04-23 | `scraper/cev/parser.py` | Нет тестов; особенно ветка date-parse fallback легко покрывается фикстурой | открыт |
| 2026-04-23 | `scraper/cev/parser.py` | `requests.Session()` на уровне модуля вместо нового TCP/TLS соединения на каждый `_fetch` | открыт |
| 2026-04-23 | `scraper/cev/parser.py` | Нет retry/backoff на transient HTTP failures (5xx, timeout) — один сбой обрывает весь скрейп | открыт |
| 2026-04-23 | `scraper/cev/parser.py:10` | `www-old.cev.eu` — legacy-домен; логировать base URL при старте, мониторить на случай отключения | открыт |
| 2026-04-23 | `scraper/` | Архитектура: унифицировать flat `scraper_for_FIVB.py` и package-style `scraper/cev/` в рамках Stage 1 | открыт |
