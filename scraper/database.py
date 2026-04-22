import psycopg2
import psycopg2.pool
from config import DB_CONFIG

_POOL_MIN_CONN = 1
_POOL_MAX_CONN = 10

_pool = psycopg2.pool.SimpleConnectionPool(_POOL_MIN_CONN, _POOL_MAX_CONN, **DB_CONFIG)


def get_connection():
    """Get a connection from the pool. Caller must return it via _pool.putconn()."""
    return _pool.getconn()


def close_pool():
    """Close all connections in the pool. Call on application shutdown."""
    _pool.closeall()


def insert_tournament(tournament_id, name, tournament_type):
    """Insert a tournament into DB, do nothing on conflict."""
    conn = _pool.getconn()
    try:
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
    finally:
        _pool.putconn(conn)


def insert_team(team_id, name, code):
    """Insert a team into DB, do nothing on conflict."""
    conn = _pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            insert into teams (id, name, code)
            values (%s, %s, %s)
            on conflict (id) do nothing
            """,
            (team_id, name, code)
        )
        conn.commit()
        cur.close()
    finally:
        _pool.putconn(conn)


def insert_match(match_id, tournament_id, team_a_id, team_b_id, score_a, score_b, match_date, status):
    """Insert a match into DB, update scores and status on conflict."""
    conn = _pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            insert into matches
            (id, tournament_id, team_a_id, team_b_id, score_a, score_b, match_date, status)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (id) do update set
                score_a = excluded.score_a,
                score_b = excluded.score_b,
                status = excluded.status
            """,
            (match_id, tournament_id, team_a_id, team_b_id, score_a, score_b, match_date, status)
        )
        conn.commit()
        cur.close()
    finally:
        _pool.putconn(conn)


def insert_set(match_id, set_number, points_a, points_b):
    """Insert a set into DB."""
    conn = _pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            insert into sets (match_id, set_number, points_a, points_b)
            values (%s, %s, %s, %s)
            """,
            (match_id, set_number, points_a, points_b)
        )
        conn.commit()
        cur.close()
    finally:
        _pool.putconn(conn)
