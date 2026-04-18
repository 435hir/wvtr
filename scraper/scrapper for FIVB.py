import requests, time
from database import insert_tournament, insert_team, insert_match, insert_set

TOURNAMENTS = [
    {
        'id': 1632,
        'name': 'FIVB Mens\'s Club World Championship 2025'
    },
    {
        'id': 1445,
        'name': 'FIVB Mens\'s Club World Championship 2024'
    },
    {
        'id': 1358,
        'name': 'FIVB Mens\'s Club World Championship 2023'
    },
]

def scrape_tournament(tournament_id, tournament_name):
    '''Scrapping datas about each tournament'''

    print(f"\n=== Parsing: {tournament_name} ===")
    
    insert_tournament(tournament_id, tournament_name, 'international')

    matches_url = f"https://en-live.volleyballworld.com/api/v1/live/matches/bytournaments/{tournament_id}"
    matches_response = requests.get(matches_url)
    matches_data = matches_response.json()

    team_ids = set()
    for match in matches_data:
        team_ids.add(match['noTeamA'])
        team_ids.add(match['noTeamB'])

    print(f"Total teams: {len(team_ids)}")

    for team_id in team_ids:
        team_url = f"https://en-live.volleyballworld.com/api/v1/teams/{team_id}"
        team_response = requests.get(team_url)
        team_data_list = team_response.json()

        if isinstance(team_data_list, list) and len(team_data_list) > 0:
            team_data = team_data_list[0]
        else:
            team_data = team_data_list
    
        insert_team(
            team_data['teamId'],
            team_data['teamName'],
            team_data.get('teamCode', None)
        )

        time.sleep(0.5)

    matches_count = 0
    for match in matches_data:
        if match['status'] != 2:
            continue

        match_id = match['no']

        insert_match(
            match_id,
            tournament_id,
            match['noTeamA'],
            match['noTeamB'],
            match['matchPointsA'],
            match['matchPointsB'],
            None,
            match['statusLabel']
        )

        for set_data in match['sets']:
            if set_data['no'] == 0:
                continue

            insert_set(
                match_id,
                set_data['no'],
                set_data['pointsTeamA'],
                set_data['pointsTeamB']
            )

        matches_count += 1

    print(f'Total matches: {matches_count}')

def scrape_all_tournaments():
    '''Parsing of all tournaments'''

    for tournament in TOURNAMENTS:
        scrape_tournament(
            tournament['id'],
            tournament['name']
        )

    print("\n=== Done! ===")

if __name__ == "__main__":
    scrape_all_tournaments()
    