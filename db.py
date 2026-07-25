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


def get_skill_groups(division_id: int):
    """Get all active skill groups for a division."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_skill_group, group_name
                FROM public.skill_groups
                WHERE id_div = %s
                  AND active = 'y'
                ORDER BY group_name
                """,
                (division_id,),
            )
            return cur.fetchall()


def get_skills_in_group(skill_group_id: int):
    """Get all skills in a group, ordered by position."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sgs.order_seq, es.id_eval_skill, es.skill, es.min_score, es.max_score
                FROM public.skill_group_skills sgs
                JOIN public.eval_skill es ON sgs.id_eval_skill = es.id_eval_skill
                WHERE sgs.id_skill_group = %s
                ORDER BY sgs.order_seq
                """,
                (skill_group_id,),
            )
            return cur.fetchall()


def get_skill_at_position(skill_group_id: int, position: int):
    """Get the skill at a specific position in a group (1-indexed)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sgs.order_seq, es.id_eval_skill, es.skill, es.min_score, es.max_score
                FROM public.skill_group_skills sgs
                JOIN public.eval_skill es ON sgs.id_eval_skill = es.id_eval_skill
                WHERE sgs.id_skill_group = %s AND sgs.order_seq = %s
                """,
                (skill_group_id, position),
            )
            return cur.fetchone()


def get_unevaluated_players_for_group(division: str, sport: str, year: int, season: str, skill_group_id: int):
    """Get players who haven't evaluated ALL skills in this group yet."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT r.id_reg, r.player_first_name AS first_name, r.player_last_name AS last_name
                FROM public.registrations r
                WHERE r.division = %s
                  AND r.sport = %s
                  AND r.year = %s
                  AND r.season = %s
                  AND r.id_reg NOT IN (
                        -- Players who have evaluated ALL skills in this group
                        SELECT id_player_reg
                        FROM public.eval_results
                        WHERE id_eval_skill IN (
                            SELECT id_eval_skill FROM public.skill_group_skills WHERE id_skill_group = %s
                        )
                        GROUP BY id_player_reg
                        HAVING COUNT(DISTINCT id_eval_skill) = (
                            SELECT COUNT(*) FROM public.skill_group_skills WHERE id_skill_group = %s
                        )
                  )
                ORDER BY r.player_first_name, r.player_last_name
                """,
                (division, sport, year, season, skill_group_id, skill_group_id),
            )
            return cur.fetchall()
    """Get the id_div for a division name."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id_div FROM public.divisions WHERE division = %s', (division,))
            result = cur.fetchone()
            return result[0] if result else None


def get_skills(division_id: int):
    """Return only skills that have at least one active criterion for this division."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_eval_skill, skill, min_score, max_score
                FROM public.eval_skill
                WHERE EXISTS (
                    SELECT 1
                    FROM public.eval_skill_criteria
                    WHERE eval_skill_criteria.id_eval_skill = eval_skill.id_eval_skill
                    AND id_div = %s
                    AND active = 'y'
                )
                ORDER BY skill
                """,
                (division_id,),
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
                ORDER BY score_level DESC
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


def get_player_by_id(player_id: int, division: str, sport: str, year: int, season: str):
    """Get player info if they exist in this division/sport/year/season."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_reg, player_first_name AS first_name, player_last_name AS last_name
                FROM public.registrations
                WHERE id_reg = %s
                  AND division = %s
                  AND sport = %s
                  AND year = %s
                  AND season = %s
                """,
                (player_id, division, sport, year, season),
            )
            return cur.fetchone()


def get_position_in_group(skill_group_id: int, skill_id: int) -> int:
    """Get the position (1-indexed) of a skill within a group."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT order_seq
                FROM public.skill_group_skills
                WHERE id_skill_group = %s AND id_eval_skill = %s
                """,
                (skill_group_id, skill_id),
            )
            result = cur.fetchone()
            return result[0] if result else None
