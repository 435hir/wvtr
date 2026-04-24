import datetime
import logging
import time

import requests

from database import get_or_create_team, insert_match, insert_set, insert_tournament

logger = logging.getLogger(__name__)

_FIVB_STATUS_FINISHED = 2  # volleyballworld API numeric status for completed matches
_REQUEST_DELAY = 0.5       # seconds between team API calls

TOURNAMENTS = [
    {
        'id': 1632,
        'name': "FIVB Men's Club World Championship 2025",
        'season': '2025',
        'gender': 'M',
        'weight': 1.0,
    },
    {
        'id': 1445,
        'name': "FIVB Men's Club World Championship 2024",
        'season': '2024',
        'gender': 'M',
        'weight': 1.0,
    },
    {
        'id': 1358,
        'name': "FIVB Men's Club World Championship 2023",
        'season': '2023',
        'gender': 'M',
        'weight': 1.0,
    },
]


def _parse_match_date(match):
    """Extract and parse match date from a FIVB API match object, or return None."""
    # TODO: verify field name — volleyballworld API may use 'matchDate', 'localDate', or 'startDateTimeUTC'
    raw = match.get('matchDate')
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(str(raw)[:10])
    except ValueError:
        logger.warning("Could not parse matchDate %r for match %s", raw, match.get('no'))
        return None


def scrape_tournament(tournament):
    """Scrape matches and teams for a single tournament entry from TOURNAMENTS."""
    fivb_id = tournament['id']
    logger.info("Parsing: %s", tournament['name'])

    internal_tournament_id = insert_tournament(
        source='fivb',
        external_id=str(fivb_id),
        name=tournament['name'],
        season=tournament['season'],
        tournament_type='club_world_championship',
        gender=tournament['gender'],
        weight=tournament['weight'],
    )

    matches_url = (
        f"https://en-live.volleyballworld.com/api/v1/live/matches/bytournaments/{fivb_id}"
    )
    try:
        matches_response = requests.get(matches_url, timeout=(10, 30))
        matches_response.raise_for_status()
        matches_data = matches_response.json()
    except requests.RequestException as e:
        logger.error("Failed to fetch matches for tournament %s: %s", fivb_id, e)
        raise

    external_team_ids = set()
    for match in matches_data:
        external_team_ids.add(match['noTeamA'])
        external_team_ids.add(match['noTeamB'])

    logger.info("Total teams: %d", len(external_team_ids))

    team_id_map = {}  # external_team_id (int) -> internal team_id
    for ext_id in external_team_ids:
        team_url = f"https://en-live.volleyballworld.com/api/v1/teams/{ext_id}"
        try:
            team_response = requests.get(team_url, timeout=(10, 30))
            team_response.raise_for_status()
            team_data_list = team_response.json()
        except requests.RequestException as e:
            logger.error("Failed to fetch team %s — skipping: %s", ext_id, e)
            continue

        team_data = team_data_list[0] if isinstance(team_data_list, list) else team_data_list

        team_id = get_or_create_team(
            source='fivb',
            external_id=str(ext_id),
            name=team_data['teamName'],
            # FIVB API does not expose country; populate manually or via CEV data
            country=None,
            gender=tournament['gender'],
            code=team_data.get('teamCode'),
        )
        team_id_map[ext_id] = team_id
        time.sleep(_REQUEST_DELAY)

    matches_count = 0
    for match in matches_data:
        if match['status'] != _FIVB_STATUS_FINISHED:
            logger.debug(
                "Skipping match %s: status=%s (%s)",
                match['no'], match['status'], match.get('statusLabel'),
            )
            continue

        if match['noTeamA'] not in team_id_map or match['noTeamB'] not in team_id_map:
            logger.warning(
                "Skipping match %s — one or both teams failed to fetch", match['no'],
            )
            continue

        internal_match_id = insert_match(
            source='fivb',
            external_id=str(match['no']),
            tournament_id=internal_tournament_id,
            team_a_id=team_id_map[match['noTeamA']],
            team_b_id=team_id_map[match['noTeamB']],
            score_a=match['matchPointsA'],
            score_b=match['matchPointsB'],
            match_date=_parse_match_date(match),
            status=match['statusLabel'],
        )

        for set_data in match['sets']:
            if set_data['no'] == 0:
                continue
            insert_set(
                match_id=internal_match_id,
                set_number=set_data['no'],
                points_a=set_data['pointsTeamA'],
                points_b=set_data['pointsTeamB'],
            )

        matches_count += 1

    logger.info("Total matches written: %d", matches_count)


def scrape_all_tournaments():
    """Scrape all tournaments defined in TOURNAMENTS."""
    for tournament in TOURNAMENTS:
        scrape_tournament(tournament)
    logger.info("Done!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    scrape_all_tournaments()
