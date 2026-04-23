"""CEV scraper for www-old.cev.eu.

Provides three public functions that cover the three-step fetch chain:
  get_phases(comp_id)            → Competition.aspx
  get_matches(comp_id, pid)      → CompetitionView.aspx
  get_set_scores(mid, comp_id, cid, pid) → MatchPage.aspx
"""

import re
import logging
import datetime
from typing import TypedDict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_CEV_BASE = "https://www-old.cev.eu/Competition-Area"

# All regexes compiled once at import.
_CTRL_RE        = re.compile(r"CompetitionPhases_ctrl(\d+)_(LB_PhaseTitle|Label3)")
_PID_RE         = re.compile(r"[?&]PID=(\d+)")
_MID_RE         = re.compile(r"[?&]mID=(\d+)")
_CID_RE         = re.compile(r"[?&]CID=(\d+)")
_DATE_RE         = re.compile(r"\d{2}/\d{2}/\d{4}")
# MatchPage.aspx span ids: LB_Set{N}Casa (home points), LB_Set{N}Ospiti (away points)
_SET_SCORE_ID_RE = re.compile(r"LB_Set(\d+)(Casa|Ospiti)$")

# ASP.NET Telerik RadListView row classes on CompetitionView.aspx.
_ROW_CLASSES = {"rlvI", "rlvA"}

# Span id suffixes used by the match-row template on CompetitionView.aspx.
# All anchored at $ so that e.g. "Label20" does not match "Label2".
_HOME_TEAM_ID_RE = re.compile(r"RADLIST_Matches_ctrl\d+_Label2$")
_AWAY_TEAM_ID_RE = re.compile(r"RADLIST_Matches_ctrl\d+_Label4$")
_HOME_SETS_ID_RE = re.compile(r"RADLIST_Matches_ctrl\d+_LB_SetCasa$")
_AWAY_SETS_ID_RE = re.compile(r"RADLIST_Matches_ctrl\d+_LB_SetOspiti$")
_DATAORA_ID_RE   = re.compile(r"RADLIST_Matches_ctrl\d+_LB_DataOra$")

_HTTP_TIMEOUT = 10

# Avoids 403s on servers that reject the default python-requests UA.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class Phase(TypedDict):
    pid: int
    name: str
    dates: str


class Match(TypedDict):
    match_id: int
    home_team: str
    away_team: str
    home_sets: int
    away_sets: int
    date: datetime.date | None
    cid: int


class SetScore(TypedDict):
    set_number: int
    home_points: int
    away_points: int


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch(url: str) -> BeautifulSoup:
    """GET url, raise on HTTP error, return BeautifulSoup parsed from bytes.

    Bytes input lets BeautifulSoup detect charset from the HTML <meta> tag,
    avoiding mojibake on accented names (e.g. "Łódź", "Çankaya").

    Raises:
        requests.RequestException: on network error or non-2xx HTTP status.
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=_HTTP_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("HTTP error fetching %s — %s", url, exc, exc_info=True)
        raise
    return BeautifulSoup(response.content, "html.parser")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_phases(comp_id: int) -> list[Phase]:
    """Fetch all playable phases for a CEV competition.

    Scrapes Competition.aspx?ID={comp_id} and extracts phase blocks from
    ASP.NET-generated span ids sharing a ctrl{N} suffix:
      ...CompetitionPhases_ctrl{N}_LB_PhaseTitle[Selected]  → phase name + PID
      ...CompetitionPhases_ctrl{N}_Label3                   → date range

    Returns phases in DOM order (earliest phase first):
        [{"pid": int, "name": str, "dates": str}, ...]

    PID=-2 ("Final Standing") is never returned: _PID_RE matches only digits,
    so negative values are silently excluded.

    Raises:
        requests.RequestException: on network error or non-2xx HTTP status.
    """
    url = f"{_CEV_BASE}/Competition.aspx?ID={comp_id}"
    soup = _fetch(url)

    by_ctrl: dict[int, dict] = {}

    for span in soup.find_all("span", id=_CTRL_RE):
        ctrl_m = _CTRL_RE.search(span["id"])
        ctrl_n = int(ctrl_m.group(1))
        kind = ctrl_m.group(2)
        entry = by_ctrl.setdefault(ctrl_n, {})

        if kind == "LB_PhaseTitle":
            entry.setdefault("name", span.get_text(strip=True))
            link = span.find_parent("a", href=_PID_RE)
            if link:
                pid_m = _PID_RE.search(link["href"])
                if pid_m:
                    entry.setdefault("pid", int(pid_m.group(1)))
        elif kind == "Label3":
            entry.setdefault("dates", span.get_text(" ", strip=True))

    if not by_ctrl:
        logger.warning(
            "get_phases: no phases found for comp_id=%s — page layout may have changed",
            comp_id,
        )
        return []

    phases: list[Phase] = []
    for ctrl_n, entry in sorted(by_ctrl.items()):
        if "pid" not in entry:
            logger.warning(
                "get_phases: ctrl%d has no PID for comp_id=%s, skipping",
                ctrl_n,
                comp_id,
            )
            continue
        phases.append(Phase(
            pid=entry["pid"],
            name=entry.get("name", ""),
            dates=entry.get("dates", ""),
        ))

    return phases


def get_matches(comp_id: int, pid: int) -> list[Match]:
    """Fetch all matches for one phase of a CEV competition.

    Scrapes CompetitionView.aspx?ID={comp_id}&PID={pid}.

    Match data is encoded in Telerik RadListView rows (<tr class="rlvI|rlvA">).
    Each row carries ASP.NET span ids with predictable suffixes:
      Label2        → home team name
      Label4        → away team name
      LB_SetCasa    → home sets won
      LB_SetOspiti  → away sets won
      LB_DataOra    → match date/time text

    Unplayed matches (score 0-0) are included; callers decide on filtering.

    Returns:
        [{"match_id": int, "home_team": str, "away_team": str,
          "home_sets": int, "away_sets": int, "date": datetime.date | None, "cid": int}, ...]

    Raises:
        requests.RequestException: on network error or non-2xx HTTP status.
    """
    url = f"{_CEV_BASE}/CompetitionView.aspx?ID={comp_id}&PID={pid}"
    soup = _fetch(url)

    rows = soup.find_all("tr", class_=list(_ROW_CLASSES))

    if not rows:
        logger.warning(
            "get_matches: no match rows found for comp_id=%s pid=%s"
            " — page may be empty or layout changed",
            comp_id,
            pid,
        )
        return []

    matches: list[Match] = []
    for tr in rows:
        first_link = tr.find("a", href=_MID_RE)
        if not first_link:
            continue

        mid_m = _MID_RE.search(first_link["href"])
        cid_m = _CID_RE.search(first_link["href"])
        if not mid_m:
            continue
        mid = int(mid_m.group(1))
        if not cid_m:
            logger.warning(
                "get_matches: no CID in href for mID=%s — skipping", mid
            )
            continue
        cid = int(cid_m.group(1))

        home_span      = tr.find("span", id=_HOME_TEAM_ID_RE)
        away_span      = tr.find("span", id=_AWAY_TEAM_ID_RE)
        home_sets_span = tr.find("span", id=_HOME_SETS_ID_RE)
        away_sets_span = tr.find("span", id=_AWAY_SETS_ID_RE)
        date_span      = tr.find("span", id=_DATAORA_ID_RE)

        if not all([home_span, away_span, home_sets_span, away_sets_span]):
            logger.warning(
                "get_matches: missing required spans for mID=%s — skipping", mid
            )
            continue

        try:
            home_sets = int(home_sets_span.get_text(strip=True))
            away_sets = int(away_sets_span.get_text(strip=True))
        except ValueError:
            logger.warning(
                "get_matches: non-integer set score for mID=%s — skipping", mid
            )
            continue

        date: datetime.date | None = None
        if date_span:
            date_m = _DATE_RE.search(date_span.get_text(strip=True))
            if date_m:
                try:
                    date = datetime.datetime.strptime(date_m.group(0), "%d/%m/%Y").date()
                except ValueError:
                    logger.warning(
                        "get_matches: unparseable date %r for mID=%s", date_m.group(0), mid
                    )

        matches.append(Match(
            match_id=mid,
            home_team=home_span.get_text(strip=True),
            away_team=away_span.get_text(strip=True),
            home_sets=home_sets,
            away_sets=away_sets,
            date=date,
            cid=cid,
        ))

    return matches


def get_set_scores(mid: int, comp_id: int, cid: int, pid: int) -> list[SetScore]:
    """Fetch per-set scores for a completed CEV match.

    Scrapes MatchPage.aspx?mID={mid}&ID={comp_id}&CID={cid}&PID={pid}.
    Set scores are encoded in ASP.NET spans with ids:
      LB_Set{N}Casa    → home points for set N
      LB_Set{N}Ospiti  → away points for set N

    Returns an empty list with a WARNING log if no set spans are found
    (match unplayed, or page layout changed).

    Returns:
        [{"set_number": int, "home_points": int, "away_points": int}, ...]
        sorted by set_number.

    Raises:
        requests.RequestException: on network error or non-2xx HTTP status.
    """
    url = (
        f"{_CEV_BASE}/MatchPage.aspx"
        f"?mID={mid}&ID={comp_id}&CID={cid}&PID={pid}"
    )
    soup = _fetch(url)

    by_set: dict[int, dict] = {}
    for span in soup.find_all("span", id=_SET_SCORE_ID_RE):
        m = _SET_SCORE_ID_RE.search(span["id"])
        n = int(m.group(1))
        side = m.group(2)  # "Casa" (home) or "Ospiti" (away)

        try:
            points = int(span.get_text(strip=True))
        except ValueError:
            logger.warning(
                "get_set_scores: non-integer in Set %d for mID=%s — skipping set",
                n,
                mid,
            )
            continue

        entry = by_set.setdefault(n, {})
        if side == "Casa":
            entry["home_points"] = points
        else:
            entry["away_points"] = points

    if not by_set:
        logger.warning(
            "get_set_scores: no set scores found for mID=%s"
            " — match may be unplayed or layout changed",
            mid,
        )
        return []

    set_scores: list[SetScore] = []
    for n, entry in sorted(by_set.items()):
        if "home_points" not in entry or "away_points" not in entry:
            logger.warning(
                "get_set_scores: incomplete data for Set %d of mID=%s — skipping",
                n,
                mid,
            )
            continue
        set_scores.append(SetScore(
            set_number=n,
            home_points=entry["home_points"],
            away_points=entry["away_points"],
        ))

    return set_scores
