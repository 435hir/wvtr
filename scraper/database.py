import logging

import psycopg2
import psycopg2.pool
from config import DB_CONFIG

logger = logging.getLogger(__name__)

_POOL_MIN_CONN = 1
_POOL_MAX_CONN = 10

_pool = psycopg2.pool.SimpleConnectionPool(_POOL_MIN_CONN, _POOL_MAX_CONN, **DB_CONFIG)


def get_connection():
    """Get a connection from the pool. Caller must return it via _pool.putconn()."""
    return _pool.getconn()


def close_pool():
    """Close all connections in the pool. Call on application shutdown."""
    _pool.closeall()


def insert_tournament(source, external_id, name, season, tournament_type, gender, weight):
    """Insert or update a tournament; return its internal id."""
    conn = _pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tournaments (source, external_id, name, season, type, gender, weight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source, external_id) DO UPDATE SET
                        name   = EXCLUDED.name,
                        season = EXCLUDED.season,
                        type   = EXCLUDED.type,
                        gender = EXCLUDED.gender,
                        weight = EXCLUDED.weight
                    RETURNING id
                    """,
                    (source, external_id, name, season, tournament_type, gender, weight),
                )
                return cur.fetchone()[0]
    except psycopg2.Error as e:
        logger.error(
            "insert_tournament failed for source=%s external_id=%s: %s",
            source, external_id, e,
        )
        raise
    finally:
        _pool.putconn(conn)


def insert_team(name, country, gender):
    """Insert a new canonical team; return its internal id."""
    conn = _pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO teams (name, country, gender)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, country, gender),
                )
                return cur.fetchone()[0]
    except psycopg2.Error as e:
        logger.error("insert_team failed for name=%s: %s", name, e)
        raise
    finally:
        _pool.putconn(conn)


def insert_team_alias(team_id, source, external_id, name, code):
    """Insert or update a team alias linking an external source to an internal team.

    team_id is not updated on conflict — rebind aliases via a separate merge tool.
    """
    conn = _pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO team_aliases (team_id, source, external_id, name, code)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source, external_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        code = EXCLUDED.code
                    """,
                    (team_id, source, external_id, name, code),
                )
    except psycopg2.Error as e:
        logger.error(
            "insert_team_alias failed for source=%s external_id=%s: %s",
            source, external_id, e,
        )
        raise
    finally:
        _pool.putconn(conn)


def get_team_id_by_alias(source, external_id):
    """Return internal team_id for a given source + external_id, or None if not found."""
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT team_id FROM team_aliases
                WHERE source = %s AND external_id = %s
                """,
                (source, external_id),
            )
            row = cur.fetchone()
        return row[0] if row else None
    except psycopg2.Error as e:
        logger.error(
            "get_team_id_by_alias failed for source=%s external_id=%s: %s",
            source, external_id, e,
        )
        raise
    finally:
        _pool.putconn(conn)


def get_or_create_team(source, external_id, name, country, gender, code=None):
    """Return internal team_id, creating team and alias in one transaction if not known."""
    conn = _pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT team_id FROM team_aliases WHERE source = %s AND external_id = %s",
                    (source, external_id),
                )
                row = cur.fetchone()
                if row:
                    return row[0]

                logger.info(
                    "New team: source=%s external_id=%s name=%s",
                    source, external_id, name,
                )
                cur.execute(
                    "INSERT INTO teams (name, country, gender) VALUES (%s, %s, %s) RETURNING id",
                    (name, country, gender),
                )
                team_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO team_aliases (team_id, source, external_id, name, code)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source, external_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        code = EXCLUDED.code
                    """,
                    (team_id, source, external_id, name, code),
                )
                return team_id
    except psycopg2.Error as e:
        logger.error(
            "get_or_create_team failed for source=%s external_id=%s: %s",
            source, external_id, e,
        )
        raise
    finally:
        _pool.putconn(conn)


def insert_match(source, external_id, tournament_id, team_a_id, team_b_id,
                 score_a, score_b, match_date, status):
    """Insert or update a match; return its internal id."""
    conn = _pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO matches
                        (source, external_id, tournament_id, team_a_id, team_b_id,
                         score_a, score_b, match_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source, external_id) DO UPDATE SET
                        score_a    = EXCLUDED.score_a,
                        score_b    = EXCLUDED.score_b,
                        match_date = EXCLUDED.match_date,
                        status     = EXCLUDED.status
                    RETURNING id
                    """,
                    (source, external_id, tournament_id, team_a_id, team_b_id,
                     score_a, score_b, match_date, status),
                )
                return cur.fetchone()[0]
    except psycopg2.Error as e:
        logger.error(
            "insert_match failed for source=%s external_id=%s: %s",
            source, external_id, e,
        )
        raise
    finally:
        _pool.putconn(conn)


def insert_set(match_id, set_number, points_a, points_b):
    """Insert or update a set result for a match."""
    conn = _pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sets (match_id, set_number, points_a, points_b)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (match_id, set_number) DO UPDATE SET
                        points_a = EXCLUDED.points_a,
                        points_b = EXCLUDED.points_b
                    """,
                    (match_id, set_number, points_a, points_b),
                )
    except psycopg2.Error as e:
        logger.error(
            "insert_set failed for match_id=%s set_number=%s: %s",
            match_id, set_number, e,
        )
        raise
    finally:
        _pool.putconn(conn)
