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
| 2026-04-24 | `scraper/cev/scraper.py` | CEV external_id для команд = имя команды — заменить на числовой ID когда найдём его в HTML/API (ребрендинг создаёт дубли) | открыт |
| 2026-04-24 | `scraper/scraper_for_FIVB.py` | `match_date` всегда None — проверить поле (`matchDate`? `localDate`?) в реальном ответе volleyballworld API и распарсить | открыт |
| 2026-04-24 | `scraper/database.py` | `insert_team` без `ON CONFLICT` — нарушает конвенцию идемпотентности; вызывать только через `get_or_create_team` | открыт |
| 2026-04-24 | `scraper/database.py` | `insert_tournament` ON CONFLICT обновляет `season` — семантически неверно, season иммутабелен для данного (source, external_id) | открыт |
| 2026-04-24 | `scraper/` | Стандартизировать логирование: FIVB-скрапер переведён на `logging`, но стоит добавить общий `logging.basicConfig` в точку входа pipeline | открыт |
| 2026-04-24 | `scraper/cev/scraper.py` | `_is_placeholder` — substring match; ужесточить до `^(Loser\|Winner) of ` чтобы не ловить реальный клуб с этим словом в названии | открыт |
| 2026-04-24 | `scraper/cev/scraper.py` | `sys.path.insert` — хрупкий паттерн; решить до добавления нацлиговых скраперов (опции: `python -m scraper.cev.scraper` или flatten структуры) | открыт |
| 2026-04-24 | `scraper/cev/parser.py` | `from parser import` — конфликтует с бывшим stdlib-модулем `parser`; переименовать файл или переключиться на пакетный импорт | открыт |
| 2026-04-24 | `scraper/database.py` | `insert_team_alias` не обновляет `team_id` на конфликте — задокументировано, но нужен отдельный merge-инструмент для склейки дублей команд | открыт |
| 2026-04-24 | `scraper/` | Пул соединений размером 10 при последовательных скраперах избыточен — пересмотреть при параллельном запуске engine + scraper | открыт |
| 2026-04-24 | `scraper/cev/scraper.py` | Инкрементальный запуск: два списка TOURNAMENTS_ARCHIVE и TOURNAMENTS_CURRENT, или флаг full_run — запуск привязан к этапам турнира, не к расписанию | открыт |
| 2026-04-24 | `scraper/cev/scraper.py` | Автопарсинг comp_id: функция get_competitions(season), которая сама вытаскивает ID новых турниров с сайта CEV по сезону | открыт |
| 2026-04-24 | `scraper/cev/scraper.py` | Триггер запуска по этапам: логика "когда запускать" привязана к расписанию фаз турнира, не к календарному расписанию | открыт |
