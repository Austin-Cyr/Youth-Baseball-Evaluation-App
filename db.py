import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def division_sport_valid(division: str, sport: str) -> bool:
    """Check the division and sport both exist in the lookup tables."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM public.divisions WHERE division = %s', (division,))
            div_ok = cur.fetchone() is not None
            cur.execute('SELECT 1 FROM public.sport WHERE sport = %s', (sport,))
            sport_ok = cur.fetchone() is not None
    return div_ok and sport_ok


def get_division_id(division: str) -> int:
    """Get the id_div for a division name."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id_div FROM public.divisions WHERE division = %s', (division,))
            result = cur.fetchone()
            return result[0] if result else None


def get_skills():
    """Return all skills being evaluated, with their score range."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_eval_skill, skill, min_score, max_score
                FROM public.eval_skill
                ORDER BY skill
                """
            )
            return cur.fetchall()


def get_skill(skill_id: int):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_eval_skill, skill, min_score, max_score
                FROM public.eval_skill
                WHERE id_eval_skill = %s
                """,
                (skill_id,),
            )
            return cur.fetchone()


def get_skill_criteria(skill_id: int, division_id: int):
    """Get all criteria for a skill/division combo, ordered by score level."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT score_level, criteria
                FROM public.eval_skill_criteria
                WHERE id_eval_skill = %s
                  AND id_div = %s
                  AND active = 'y'
                ORDER BY score_level
                """,
                (skill_id, division_id),
            )
            return cur.fetchall()


def get_unevaluated_players(division: str, sport: str, year: int, season: str, skill_id: int):
    """Registered players in this division/sport/year/season who have no eval_results row for this skill."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_reg, player_first_name AS first_name,
                       player_last_name AS last_name
                FROM public.registrations
                WHERE division = %s
                  AND sport = %s
                  AND year = %s
                  AND season = %s
                  AND id_reg NOT IN (
                        SELECT id_player_reg
                        FROM public.eval_results
                        WHERE id_eval_skill = %s
                          AND id_player_reg IS NOT NULL
                  )
                ORDER BY player_first_name, player_last_name
                """,
                (division, sport, year, season, skill_id),
            )
            return cur.fetchall()


def insert_registered_eval(id_player_reg: int, id_eval_skill: int, eval_score: int, eval_evaluator_ip: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.eval_results
                    (id_player_reg, id_eval_skill, eval_score, date, eval_evaluator_ip)
                VALUES (%s, %s, %s, CURRENT_DATE, %s)
                """,
                (id_player_reg, id_eval_skill, eval_score, eval_evaluator_ip),
            )


def insert_manual_eval(first_name: str, last_name: str, id_eval_skill: int, eval_score: int, eval_evaluator_ip: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.eval_results_manual_players
                    (id_eval_skill, eval_score, date, eval_evaluator_ip,
                     player_first_name, player_last_name)
                VALUES (%s, %s, CURRENT_DATE, %s, %s, %s)
                """,
                (id_eval_skill, eval_score, eval_evaluator_ip, first_name, last_name),
            )
