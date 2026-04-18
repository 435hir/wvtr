import psycopg2
from config import DB_CONFIG

def get_connection():
    """connection creation to DB""" 
    return psycopg2.connect(**DB_CONFIG)

def insert_tournament(tournament_id, name, tournament_type):
    """Adding a tournaments into DB"""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        insert into tournaments (id, name, type)
        values (%s, %s, %s)
        on conflict (id) do nothing
        """,
        (tournament_id, name, tournament_type)
    )
    
    conn.commit()
    cur.close()
    conn.close()

def insert_team(team_id, name, code):
    '''Adding a team into DB'''

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        '''
        insert into teams (id, name, code)
        values (%s, %s, %s)
        on conflict (id) do nothing
        ''',
        (team_id, name, code)
    )

    conn.commit()
    cur.close()
    conn.close()

def insert_match(match_id, tournament_id, team_a_id, team_b_id, score_a, score_b, match_date, status):
    '''Adding a match into DB'''

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        '''
        insert into matches 
        (id, tournament_id, team_a_id, team_b_id, score_a, score_b, match_date, status)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (id) do update set
            score_a = excluded.score_a,
            score_b = excluded.score_b,
            status = excluded.status
        ''',
        (match_id, tournament_id, team_a_id, team_b_id, score_a, score_b, match_date, status)
    )

    conn.commit()
    cur.close()  
    conn.close()

def insert_set(match_id, set_number, points_a, points_b):
    '''Adding a set into DB'''

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        '''
        insert into sets (match_id, set_number, points_a, points_b)
        values (%s, %s, %s, %s)
        ''',
        (match_id, set_number, points_a, points_b)
    )

    conn.commit()
    cur.close()
    conn.close()