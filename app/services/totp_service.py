import base64
import io
import os
import secrets
import time
from datetime import datetime
from typing import List, Optional, Tuple

import pyotp
import qrcode
from fastapi import HTTPException

from app.utils.hash_util import hash_password, verify_password

TOTP_ISSUER_NAME = os.getenv("TOTP_ISSUER_NAME", "FINSURE")

_BACKUP_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_BACKUP_CODE_LENGTH = 8
_BACKUP_CODE_GROUP = 4


def _get_encryption_key() -> str:
    key = os.getenv("TOTP_SECRET_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="TOTP secret encryption key not configured")
    return key


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_provisioning_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=TOTP_ISSUER_NAME)


def generate_qr_code_data_url(otpauth_uri: str) -> str:
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(otpauth_uri)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def store_totp_secret(conn, user_id: int, secret: str) -> None:
    key = _get_encryption_key()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET totp_secret = pgp_sym_encrypt(%s, %s),
                totp_enabled = FALSE,
                totp_verified_at = NULL,
                totp_last_used_timecode = NULL
            WHERE "userID" = %s;
            """,
            (secret, key, user_id),
        )
    conn.commit()


def get_decrypted_totp_secret(conn, user_id: int) -> Optional[str]:
    key = _get_encryption_key()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT pgp_sym_decrypt(totp_secret, %s)::text AS secret
            FROM users
            WHERE "userID" = %s;
            """,
            (key, user_id),
        )
        row = cursor.fetchone()
    return row["secret"] if row else None


def verify_totp_code(secret: str, code: str) -> Tuple[bool, Optional[int]]:
    if not code or not code.isdigit():
        return False, None

    totp = pyotp.TOTP(secret)
    now = time.time()
    for offset in (-1, 0, 1):
        for_time = now + (offset * totp.interval)
        if totp.verify(code, for_time=for_time, valid_window=0):
            timecode = int(totp.timecode(datetime.utcfromtimestamp(for_time)))
            return True, timecode
    return False, None


def update_totp_state(
    conn,
    user_id: int,
    enabled: bool,
    verified_at: Optional[datetime],
    last_used_timecode: Optional[int],
) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET totp_enabled = %s,
                totp_verified_at = %s,
                totp_last_used_timecode = %s
            WHERE "userID" = %s;
            """,
            (enabled, verified_at, last_used_timecode, user_id),
        )
    conn.commit()


def update_totp_last_used_timecode(conn, user_id: int, last_used_timecode: Optional[int]) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET totp_last_used_timecode = %s
            WHERE "userID" = %s;
            """,
            (last_used_timecode, user_id),
        )
    conn.commit()


def clear_totp_state(conn, user_id: int) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET totp_enabled = FALSE,
                totp_secret = NULL,
                totp_verified_at = NULL,
                totp_last_used_timecode = NULL
            WHERE "userID" = %s;
            """,
            (user_id,),
        )
    conn.commit()


def generate_backup_codes(count: int = 8) -> List[str]:
    codes: List[str] = []
    for _ in range(count):
        raw = "".join(secrets.choice(_BACKUP_CODE_ALPHABET) for _ in range(_BACKUP_CODE_LENGTH))
        grouped = f"{raw[:_BACKUP_CODE_GROUP]}-{raw[_BACKUP_CODE_GROUP:]}"
        codes.append(grouped)
    return codes


def store_backup_codes(conn, user_id: int, codes: List[str]) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM user_backup_codes WHERE user_id = %s AND used_at IS NULL;",
            (user_id,),
        )
        for code in codes:
            cursor.execute(
                """
                INSERT INTO user_backup_codes (user_id, code_hash)
                VALUES (%s, %s);
                """,
                (user_id, hash_password(code)),
            )
    conn.commit()


def count_unused_backup_codes(conn, user_id: int) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS remaining
            FROM user_backup_codes
            WHERE user_id = %s AND used_at IS NULL;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
    return int(row["remaining"]) if row else 0


def verify_and_consume_backup_code(conn, user_id: int, code: str) -> bool:
    if not code:
        return False

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT backup_code_id, code_hash
            FROM user_backup_codes
            WHERE user_id = %s AND used_at IS NULL;
            """,
            (user_id,),
        )
        rows = cursor.fetchall() or []

        for row in rows:
            if verify_password(code, row["code_hash"]):
                cursor.execute(
                    """
                    UPDATE user_backup_codes
                    SET used_at = NOW()
                    WHERE backup_code_id = %s AND used_at IS NULL
                    RETURNING backup_code_id;
                    """,
                    (row["backup_code_id"],),
                )
                updated = cursor.fetchone()
                conn.commit()
                return bool(updated)

    return False
