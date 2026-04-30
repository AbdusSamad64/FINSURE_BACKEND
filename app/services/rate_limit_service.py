from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def check_rate_limit(
    conn,
    rate_limit_key: str,
    max_attempts: int,
    window_seconds: int,
) -> Tuple[bool, Optional[datetime]]:
    now = _utc_now()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT rate_limit_key, window_start, attempts, blocked_until
            FROM auth_rate_limits
            WHERE rate_limit_key = %s
            FOR UPDATE;
            """,
            (rate_limit_key,),
        )
        row = cursor.fetchone()

        if not row:
            cursor.execute(
                """
                INSERT INTO auth_rate_limits (rate_limit_key, window_start, attempts, blocked_until, updated_at)
                VALUES (%s, %s, 0, NULL, NOW());
                """,
                (rate_limit_key, now),
            )
            conn.commit()
            return True, None

        blocked_until = row["blocked_until"]
        if blocked_until and blocked_until > now:
            return False, blocked_until

        window_start = row["window_start"]
        if now - window_start > timedelta(seconds=window_seconds):
            cursor.execute(
                """
                UPDATE auth_rate_limits
                SET window_start = %s,
                    attempts = 0,
                    blocked_until = NULL,
                    updated_at = NOW()
                WHERE rate_limit_key = %s;
                """,
                (now, rate_limit_key),
            )
            conn.commit()

    return True, None


def record_failed_attempt(
    conn,
    rate_limit_key: str,
    max_attempts: int,
    window_seconds: int,
) -> Tuple[int, Optional[datetime]]:
    now = _utc_now()
    blocked_until: Optional[datetime] = None

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT rate_limit_key, window_start, attempts, blocked_until
            FROM auth_rate_limits
            WHERE rate_limit_key = %s
            FOR UPDATE;
            """,
            (rate_limit_key,),
        )
        row = cursor.fetchone()

        if not row:
            attempts = 1
            window_start = now
        else:
            window_start = row["window_start"]
            attempts = int(row["attempts"]) + 1

            if now - window_start > timedelta(seconds=window_seconds):
                window_start = now
                attempts = 1

        if attempts >= max_attempts:
            blocked_until = window_start + timedelta(seconds=window_seconds)

        cursor.execute(
            """
            INSERT INTO auth_rate_limits (rate_limit_key, window_start, attempts, blocked_until, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (rate_limit_key)
            DO UPDATE SET
                window_start = EXCLUDED.window_start,
                attempts = EXCLUDED.attempts,
                blocked_until = EXCLUDED.blocked_until,
                updated_at = NOW();
            """,
            (rate_limit_key, window_start, attempts, blocked_until),
        )

    conn.commit()
    return attempts, blocked_until


def clear_rate_limit(conn, rate_limit_key: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM auth_rate_limits WHERE rate_limit_key = %s;",
            (rate_limit_key,),
        )
    conn.commit()


def raise_rate_limit_error(blocked_until: Optional[datetime]) -> None:
    detail = "Too many attempts. Please try again later."
    if blocked_until:
        detail = f"Too many attempts. Try again after {blocked_until.isoformat()}."
    raise HTTPException(status_code=429, detail=detail)
