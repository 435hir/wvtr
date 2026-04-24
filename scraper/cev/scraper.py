"""CEV scraper: fetches phases, matches, and set scores via parser.py,
then writes results to the database using the canonical schema.
"""

import logging
import os
import sys
import time

import requests

# Allow `from database import ...` the same way scraper_for_FIVB.py does it.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import psycopg2
from database import get_or_create_team, insert_match, insert_set, insert_tournament
from parser import get_matches, get_phases, get_set_scores

logger = logging.getLogger(__name__)

_REQUEST_DELAY = 0.5  # seconds between MatchPage requests
_PLACEHOLDER_MARKERS = ("Loser", "Winner")

# TODO: fill in comp_ids from www-old.cev.eu/Competition-Area/Competition.aspx?ID=<comp_id>
TOURNAMENTS = [
    {'comp_id': 1799, 'name': "CEV Champions League Men 2025/26",    'season': '2025/2026', 'tournament_type': 'champions_league', 'gender': 'M', 'weight': 1.0},
    {'comp_id': 1802, 'name': "CEV ZEREN Group Champions League Women 2025/26",  'season': '2025/2026', 'tournament_type': 'champions_league', 'gender': 'W', 'weight': 1.0},
    {'comp_id': 1647, 'name': "CEV Champions League Men 2024/25",    'season': '2024/2025', 'tournament_type': 'champions_league', 'gender': 'M', 'weight': 1.0},
    {'comp_id': 1648, 'name': "CEV Champions League Women 2024/25",  'season': '2024/2025', 'tournament_type': 'champions_league', 'gender': 'W', 'weight': 1.0},
    {'comp_id': 1551, 'name': "CEV Champions League Men 2023/24",    'season': '2023/2024', 'tournament_type': 'champions_league', 'gender': 'M', 'weight': 1.0},
    {'comp_id': 1554, 'name': "CEV Champions League Women 2023/24",  'season': '2023/2024', 'tournament_type': 'champions_league', 'gender': 'W', 'weight': 1.0},
    {'comp_id': 1441, 'name': "CEV Champions League Men 2022/23",    'season': '2022/2023', 'tournament_type': 'champions_league', 'gender': 'M', 'weight': 1.0},
    {'comp_id': 1442, 'name': "CEV Champions League Women 2022/23",  'season': '2022/2023', 'tournament_type': 'champions_league', 'gender': 'W', 'weight': 1.0},
    {'comp_id': 1800, 'name': "CEV Cup Men 2025/26",                 'season': '2025/2026', 'tournament_type': 'cev_cup',          'gender': 'M', 'weight': 0.7},
    {'comp_id': 1803, 'name': "CEV Cup Women 2025/26",               'season': '2025/2026', 'tournament_type': 'cev_cup',          'gender': 'W', 'weight': 0.7},
    {'comp_id': 1651, 'name': "CEV Cup Men 2024/25",                 'season': '2024/2025', 'tournament_type': 'cev_cup',          'gender': 'M', 'weight': 0.7},
    {'comp_id': 1649, 'name': "CEV Cup Women 2024/25",               'season': '2024/2025', 'tournament_type': 'cev_cup',          'gender': 'W', 'weight': 0.7},
    {'comp_id': 1552, 'name': "CEV Cup Men 2023/24",                 'season': '2023/2024', 'tournament_type': 'cev_cup',          'gender': 'M', 'weight': 0.7},
    {'comp_id': 1555, 'name': "CEV Cup Women 2023/24",               'season': '2023/2024', 'tournament_type': 'cev_cup',          'gender': 'W', 'weight': 0.7},
    {'comp_id': 1445, 'name': "CEV Cup Men 2022/23",                 'season': '2022/2023', 'tournament_type': 'cev_cup',          'gender': 'M', 'weight': 0.7},
    {'comp_id': 1443, 'name': "CEV Cup Women 2022/23",               'season': '2022/2023', 'tournament_type': 'cev_cup',          'gender': 'W', 'weight': 0.7},
    {'comp_id': 1801, 'name': "CEV Challenge Cup Men 2025/26",       'season': '2025/2026', 'tournament_type': 'challenge_cup',    'gender': 'M', 'weight': 0.4},
    {'comp_id': 1804, 'name': "CEV Challenge Cup Women 2025/26",     'season': '2025/2026', 'tournament_type': 'challenge_cup',    'gender': 'W', 'weight': 0.4},
    {'comp_id': 1652, 'name': "CEV Challenge Cup Men 2024/25",       'season': '2024/2025', 'tournament_type': 'challenge_cup',    'gender': 'M', 'weight': 0.4},
    {'comp_id': 1650, 'name': "CEV Challenge Cup Women 2024/25",     'season': '2024/2025', 'tournament_type': 'challenge_cup',    'gender': 'W', 'weight': 0.4},
    {'comp_id': 1553, 'name': "CEV Challenge Cup Men 2023/24",       'season': '2023/2024', 'tournament_type': 'challenge_cup',    'gender': 'M', 'weight': 0.4},
    {'comp_id': 1556, 'name': "CEV Challenge Cup Women 2023/24",     'season': '2023/2024', 'tournament_type': 'challenge_cup',    'gender': 'W', 'weight': 0.4},
    {'comp_id': 1446, 'name': "CEV Challenge Cup Men 2022/23",       'season': '2022/2023', 'tournament_type': 'challenge_cup',    'gender': 'M', 'weight': 0.4},
    {'comp_id': 1444, 'name': "CEV Challenge Cup Women 2022/23",     'season': '2022/2023', 'tournament_type': 'challenge_cup',    'gender': 'W', 'weight': 0.4},
]


def _is_placeholder(name: str) -> bool:
    """Return True if the team name is a bracket placeholder, not a real club."""
    return any(marker in name for marker in _PLACEHOLDER_MARKERS)


def _normalise_name(name: str) -> str:
    """Collapse whitespace for use as a stable external_id."""
    return " ".join(name.split())


def scrape_tournament(
    comp_id: int,
    name: str,
    season: str,
    tournament_type: str,
    gender: str,
    weight: float,
) -> None:
    """Scrape all phases and matches for one CEV competition and persist to DB."""
    logger.info("Scraping CEV competition %s — %s", comp_id, name)

    tournament_id = insert_tournament(
        source="cev",
        external_id=str(comp_id),
        name=name,
        season=season,
        tournament_type=tournament_type,
        gender=gender,
        weight=weight,
    )

    phases = get_phases(comp_id)
    if not phases:
        logger.warning("No phases found for comp_id=%s — nothing to scrape", comp_id)
        return

    total_matches = 0

    for phase in phases:
        pid = phase["pid"]
        logger.info("  Phase %s: %s", pid, phase["name"])

        matches = get_matches(comp_id, pid)

        for match in matches:
            try:
                home_team = match["home_team"]
                away_team = match["away_team"]

                if _is_placeholder(home_team) or _is_placeholder(away_team):
                    logger.debug(
                        "Skipping placeholder match mID=%s (%s vs %s)",
                        match["match_id"], home_team, away_team,
                    )
                    continue

                if match["home_sets"] == 0 and match["away_sets"] == 0:
                    logger.debug("Skipping unplayed match mID=%s", match["match_id"])
                    continue

                home_team_id = get_or_create_team(
                    source="cev",
                    external_id=_normalise_name(home_team),
                    name=home_team,
                    country=None,
                    gender=gender,
                )
                away_team_id = get_or_create_team(
                    source="cev",
                    external_id=_normalise_name(away_team),
                    name=away_team,
                    country=None,
                    gender=gender,
                )

                internal_match_id = insert_match(
                    source="cev",
                    external_id=str(match["match_id"]),
                    tournament_id=tournament_id,
                    team_a_id=home_team_id,
                    team_b_id=away_team_id,
                    score_a=match["home_sets"],
                    score_b=match["away_sets"],
                    match_date=match["date"],
                    status="finished",
                )

                time.sleep(_REQUEST_DELAY)
                set_scores = get_set_scores(
                    mid=match["match_id"],
                    comp_id=comp_id,
                    cid=match["cid"],
                    pid=pid,
                )

                for s in set_scores:
                    insert_set(
                        match_id=internal_match_id,
                        set_number=s["set_number"],
                        points_a=s["home_points"],
                        points_b=s["away_points"],
                    )

                total_matches += 1

            except requests.RequestException as e:
                logger.error(
                    "HTTP error processing mID=%s — skipping: %s",
                    match.get("match_id"), e,
                )
            except psycopg2.Error as e:
                logger.error(
                    "DB error processing mID=%s — skipping: %s",
                    match.get("match_id"), e,
                )
            except Exception as e:
                logger.error(
                    "Unexpected error processing mID=%s — skipping: %s",
                    match.get("match_id"), e, exc_info=True,
                )

    logger.info("Done — %d matches written for comp_id=%s", total_matches, comp_id)


def scrape_all():
    """Scrape all tournaments defined in TOURNAMENTS."""
    if not TOURNAMENTS:
        logger.warning("TOURNAMENTS list is empty — fill in comp_ids before running")
        return
    for t in TOURNAMENTS:
        scrape_tournament(
            comp_id=t['comp_id'],
            name=t['name'],
            season=t['season'],
            tournament_type=t['tournament_type'],
            gender=t['gender'],
            weight=t['weight'],
        )
    logger.info("All done!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    scrape_all()
