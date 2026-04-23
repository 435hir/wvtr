# CLAUDE.md

Context for Claude Code working on the WVTR project. Read before touching code.

---

## What this project is

**WVTR (World Volleyball Team Rating)** — a cross-league ranking system for professional volleyball clubs. Scrapes match data from CEV, FIVB and national league sites, calculates club and league ratings using a two-tier Glicko-1 methodology, publishes results on a public web frontend.

Solo-built portfolio project. MVP target: May–June 2026.

---

## Stack

- **Language:** Python 3 (scraper + engine)
- **Database:** PostgreSQL on Supabase (free tier)
- **DB driver:** `psycopg2`
- **Frontend:** Vercel (planned, not built yet)
- **Scheduler:** GitHub Actions (cron)
- **OS (author's local):** Ubuntu via WSL2 on Windows 11, bash shell
- **IDE:** VS Code with WSL extension + Python venv

---

## Project structure

```
wvtr/
├── scraper/              # Data collection
│   ├── config.py         # DB config — GITIGNORED, never commit
│   ├── database.py       # psycopg2 connection + insert helpers
│   └── scraper.py        # FIVB scraper (migrated from scrapper_for_FIVB.py)
├── engine/               # Rating calculation
│   └── rating.py         # Glicko-1 per methodology below
├── data/                 # Local cache / exports
├── frontend/             # UI (pending)
├── .claude/              # Claude Code local config (agents etc.)
├── .venv/                # Python virtual environment — GITIGNORED
├── .env.example          # Template for environment variables
├── .gitignore
├── requirements.txt      # Project-wide Python dependencies
├── README.md
└── CLAUDE.md
```

---

## Database schema

Tables (PostgreSQL, Supabase):

- **`tournaments`** — `id`, `name`, `type`
- **`teams`** — `id`, `name`, `code`
- **`matches`** — `id`, `tournament_id`, `team_a_id`, `team_b_id`, `score_a`, `score_b`, `match_date`, `status`
- **`sets`** — `match_id`, `set_number`, `points_a`, `points_b`

All insert operations use `ON CONFLICT ... DO NOTHING` or `DO UPDATE` for idempotency. Connections use `psycopg2.connect(**DB_CONFIG)` pattern where `DB_CONFIG` is imported from `scraper/config.py`.

Example pattern (already in `scraper/database.py`):

```python
import psycopg2
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def insert_match(match_id, tournament_id, team_a_id, team_b_id,
                 score_a, score_b, match_date, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO matches
        (id, tournament_id, team_a_id, team_b_id, score_a, score_b, match_date, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            score_a = EXCLUDED.score_a,
            score_b = EXCLUDED.score_b,
            status  = EXCLUDED.status
        """,
        (match_id, tournament_id, team_a_id, team_b_id,
         score_a, score_b, match_date, status)
    )
    conn.commit()
    cur.close()
    conn.close()
```

Follow this pattern for any new DB operation.

---

## Rating methodology (what the code must implement)

Two coupled rating systems on the same match data.

### Tier 1 — League Rating

Sources (international tournaments only — domestic matches cancel out by zero-sum):

| Tournament | Weight |
|---|---|
| FIVB Club World Championship | 1.0 |
| CEV Champions League | 1.0 |
| CEV Cup | 0.7 |
| CEV Challenge Cup | 0.4 |

Per-match points:
```
points = (wonSets - lostSets) * 50 + (pointsFor - pointsAgainst) * 1
```

Algorithm:
1. For each tournament × season, sum each team's points across its matches
2. Group teams by national league; league rating = mean of its teams' points for that tournament/season
3. Apply time decay: season t ×1.0, t−1 ×0.5, t−2 ×0.25. Drop anything older than 3 seasons.
4. Apply tournament weight, sum across tournaments → final league rating

### Tier 2 — Team Rating (Glicko-1)

Season start rating:
```
start_rating = historical_component + league_bonus
historical_component = R(t-1) * 0.5 + R(t-2) * 0.25
```
If a team didn't play in t−1 or t−2, the corresponding term = 0.

League bonus by league rank: 1st = 1000, 2nd = 900, 3rd = 800, ... Step recalibrated annually as `avg_spread * k`.

In-season: standard Glicko-1 with rating R and rating deviation RD. RD starts ~200–300 for clubs that missed seasons, ~50–100 for consistent clubs. Shrinks as matches are played.

Match modifiers applied via K-factor:
- Home advantage
- Match importance (final > playoff > regular season)

Specific coefficient values are not yet calibrated — leave them as named constants at the top of `engine/rating.py`.

**Any change to formulas, weights, or decay coefficients is a methodology change — flag it explicitly, don't slip it in.**

---

## Commands

All commands run in the WSL Ubuntu terminal (not PowerShell, not CMD). If you see PowerShell-style commands (`.\venv\Scripts\activate`) anywhere — those are wrong for this project.

### Setup (first time)
```bash
cd ~/projects/wvtr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Daily
```bash
cd ~/projects/wvtr
source .venv/bin/activate            # activate venv at the start of each session
pip freeze > requirements.txt        # after adding new deps
```

### Running the scraper
```bash
cd ~/projects/wvtr
source .venv/bin/activate
python scraper/scraper.py
```

### Git (author runs these manually — NOT Claude Code, see Hard rule #7)
```bash
git status
git diff
git add <specific files>
git commit -m "feat: <what>"
git push
```

---

## Conventions

### Code style
- Python 3, idiomatic, PEP 8
- Docstrings on every function (one-line minimum)
- Type hints encouraged but not mandatory yet
- snake_case for variables/functions, PascalCase for classes

### SQL
- **Always** use parameterized queries with `%s` placeholders
- **Never** use f-strings or `.format()` to build SQL — SQL injection risk
- Every write uses `ON CONFLICT` clause for idempotency
- Close cursor and connection explicitly (or use context managers)

### Naming
- Tables: plural lowercase (`teams`, `matches`, `sets`, `tournaments`)
- Columns: snake_case (`team_a_id`, `match_date`)
- Python constants: UPPER_SNAKE (`DB_CONFIG`, `TOURNAMENT_WEIGHTS`)

### Git workflow
- Commits in English, conventional format: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Branch: working directly on `main` for now (solo dev); switch to feature branches when frontend starts
- All git state-changing commands are run manually by the author. Claude Code never commits, pushes, or resets — see Hard rule #7.

---

## Hard rules — do not violate

1. **Never commit `scraper/config.py` or `.env`.** Both are gitignored. If you see credentials in a paste from the author, tell them immediately.
2. **Never write credentials (DB password, API keys) inline in code.** Always read from `config.py` or env vars.
3. **Never use string concatenation / f-strings to build SQL queries.** Parameterized queries only.
4. **Never change rating formulas silently.** Any methodology edit = explicit flag + reasoning + version note.
5. **Never add dependencies without asking.** Propose any new library with a one-line reason. The author approves before `pip install`, then `pip freeze > requirements.txt` is run.
6. **Never delete match data.** Use `ON CONFLICT ... DO UPDATE` to refresh, never `DELETE` + `INSERT`.
7. **Never run any git command that changes state.** This includes `git add`, `git commit`, `git push`, `git reset`, `git checkout`, `git merge`, `git rebase`, `git stash`. The author handles all git operations manually. You MAY run read-only git commands: `git status`, `git diff`, `git log`.
8. **Never use bare `except:` or `except Exception: pass`.** Every caught exception must be logged with context (at minimum, the exception type and a message describing what operation failed). Silent failures are forbidden.
9. **Do not auto-format entire files.** Touch only the function or block you were asked to change. Massive reformatting makes diffs unreadable.
10. **Do not assume PowerShell or Windows paths.** This project runs in WSL Ubuntu. Use bash syntax, forward slashes, and Unix-style paths (`~/projects/wvtr`, not `C:\...`).
11. Always present a plan (5–10 lines) before writing any code. Wait for explicit approval ("пиши код" / "go") before implementing. Never write code and plan in the same response.
12. After completing a task, review CLAUDE.md and list any updates needed: Current Status, file structure, new dependencies, or other sections that should reflect the changes made. Do not edit CLAUDE.md yourself — list the changes for the author to approve.
13. Maintain BACKLOG.md: when code review produces deferred items, add them (no duplicates). When a fix addresses a backlog item, mark it "done" with date. If an item is no longer relevant (code deleted, approach changed, superseded by another fix), mark it "wontfix" with one-line reason. Check for duplicates and resolved items before adding. When the author says "обнови бэклог", review all open items against current codebase and update statuses.

---

## MVP scope — what the code must support

**In scope:**
- Scrape CEV CL, CEV Cup, CEV Challenge Cup, FIVB Club World Championship + top-tier men's and women's leagues of Italy, Poland, Germany, France, Turkey
- Store matches + sets in Supabase
- Calculate league and team ratings per methodology above
- Current season 2025/26 + 2 historical seasons (2023/24, 2024/25)
- Update pipeline runs within 48h of each game round
- Public web frontend: team ranking table, league ranking table, search by team, methodology page

**Out of scope (do not build):**
- Match history views, player stats, predictions
- Mobile app
- Juniors / amateur / lower divisions / beach volleyball
- National team rankings
- User accounts, personalization, monetization
- Seasons before 2023/24

If a request looks like it falls into "out of scope," flag it and propose deferring to v1.1+.

---

## Current status (April 2026)

- ✅ Stage 0 done: Git, GitHub repo, WSL Ubuntu, VS Code + WSL extension, venv, folder structure, CLAUDE.md, local agents
- 🔄 Stage 1 in progress: scraper → Supabase
  - Local working MVP exists for FIVB Men's Club World Championship 2023/2024/2025 (previously pointed at local Postgres)
  - Migration to Supabase: credentials swap + schema applied in Supabase
  - Known tech debt: `match_date` not parsed from API (always NULL), per-query connections instead of single reused connection, no error handling around API requests
- ⏭️ Stage 2 next: `engine/rating.py` — implement Glicko-1 per methodology
- ⏭️ Stage 3 pending: frontend on Vercel

---

## Working style (for AI assistance)

- **Language for conversation:** Russian. **Language for code, comments, commits, docs:** English.
- **Be direct.** Push back on weak approaches with reasoning. No agreement-for-agreement's-sake.
- **No filler.** No "as an AI", no "great question", no apology chains.
- **Plan before code.** For any non-trivial task, first produce a 5–10 line plan and wait for explicit approval ("ok, code"). Do not start writing code until you get that approval. "Non-trivial" = anything beyond a 1–2 line fix.
- **One task, one file, one commit.** Do not modify multiple unrelated files in a single response. If the task requires touching multiple files, split it into sequential sub-tasks and confirm each one before moving on.
- **State scope before editing.** Before writing code, list which files you will touch and which you will not.
- **Summarise after editing.** After writing code, give a 2–3 line summary of what changed and why.
- **Two options when unsure.** If there is a design choice, present 2 options with trade-offs instead of picking silently.
- **Run before handing over.** Any code you write must be executed at least once and must not error. If it errors, fix first, report second. No "should work" handovers.
- **When in doubt, ask.** If a code request is ambiguous, ask one clarifying question before writing.
- **Show, don't tell.** If suggesting a refactor, include a concrete diff or code snippet, not prose.
- **Respect existing patterns.** The `database.py` patterns are canonical — match them in new code.
- **Migrating existing code: don't silently improve it.** If you see bugs or anti-patterns in source the author is moving into the project, list them first and wait for a decision on which to fix now vs. later. Do not bundle fixes into the migration commit.
