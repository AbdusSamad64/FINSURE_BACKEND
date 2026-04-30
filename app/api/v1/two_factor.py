import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.db.database import get_db_connection
from app.models.two_factor_models import (
    TwoFactorDisableRequest,
    TwoFactorLoginRequest,
    TwoFactorRegenerateRequest,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    TwoFactorVerifySetupRequest,
    TwoFactorVerifySetupResponse,
)
from app.services.rate_limit_service import (
    check_rate_limit,
    clear_rate_limit,
    raise_rate_limit_error,
    record_failed_attempt,
)
from app.services.totp_service import (
    build_provisioning_uri,
    clear_totp_state,
    count_unused_backup_codes,
    generate_backup_codes,
    generate_qr_code_data_url,
    generate_totp_secret,
    get_decrypted_totp_secret,
    store_backup_codes,
    store_totp_secret,
    update_totp_last_used_timecode,
    update_totp_state,
    verify_and_consume_backup_code,
    verify_totp_code,
)
from app.utils.hash_util import verify_password
from app.utils.jwt_util import (
    create_access_token,
    get_current_user,
    get_pending_2fa_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Two Factor Authentication"])

TOTP_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("TOTP_RATE_LIMIT_MAX_ATTEMPTS", 5))
TOTP_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("TOTP_RATE_LIMIT_WINDOW_SECONDS", 300))


def connect_to_db():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        yield conn
    finally:
        conn.close()


def _rate_limit_key(prefix: str, user_id: int, request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{prefix}:{user_id}:{client_ip}"


def _get_user_profile(conn, user_id: int) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT "userID", name, email, "userType", "createdAt" FROM users WHERE "userID" = %s;',
            (user_id,),
        )
        user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _get_user_security_state(conn, user_id: int) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT totp_enabled, totp_last_used_timecode FROM users WHERE "userID" = %s;',
            (user_id,),
        )
        row = cursor.fetchone()
    return row or {"totp_enabled": False, "totp_last_used_timecode": None}


def _ensure_rate_limit(conn, key: str) -> None:
    allowed, blocked_until = check_rate_limit(
        conn,
        key,
        TOTP_RATE_LIMIT_MAX_ATTEMPTS,
        TOTP_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise_rate_limit_error(blocked_until)


def _record_failed(conn, key: str) -> None:
    _, blocked_until = record_failed_attempt(
        conn,
        key,
        TOTP_RATE_LIMIT_MAX_ATTEMPTS,
        TOTP_RATE_LIMIT_WINDOW_SECONDS,
    )
    if blocked_until:
        raise_rate_limit_error(blocked_until)


def _validate_code_payload(code: Optional[str], backup_code: Optional[str]) -> None:
    if (not code and not backup_code) or (code and backup_code):
        raise HTTPException(
            status_code=400,
            detail="Provide either an authenticator code or a backup code",
        )


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
def get_two_factor_status(
    curr_user: dict = Depends(get_current_user),
    conn=Depends(connect_to_db),
):
    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT totp_enabled FROM users WHERE "userID" = %s;',
            (curr_user["userID"],),
        )
        row = cursor.fetchone()

    enabled = bool(row["totp_enabled"]) if row else False
    remaining = count_unused_backup_codes(conn, curr_user["userID"]) if enabled else 0

    return {"enabled": enabled, "backup_codes_remaining": remaining}


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def start_two_factor_setup(
    curr_user: dict = Depends(get_current_user),
    conn=Depends(connect_to_db),
):
    secret = generate_totp_secret()
    store_totp_secret(conn, curr_user["userID"], secret)

    otpauth_uri = build_provisioning_uri(secret, curr_user["email"])
    qr_code_data_url = generate_qr_code_data_url(otpauth_uri)

    return {
        "otpauth_uri": otpauth_uri,
        "qr_code_data_url": qr_code_data_url,
        "manual_entry_key": secret,
    }


@router.post("/2fa/setup/verify", response_model=TwoFactorVerifySetupResponse)
def verify_two_factor_setup(
    payload: TwoFactorVerifySetupRequest,
    request: Request,
    curr_user: dict = Depends(get_current_user),
    conn=Depends(connect_to_db),
):
    rate_key = _rate_limit_key("2fa-setup", curr_user["userID"], request)
    _ensure_rate_limit(conn, rate_key)

    secret = get_decrypted_totp_secret(conn, curr_user["userID"])
    if not secret:
        raise HTTPException(status_code=400, detail="No pending 2FA setup")

    valid, timecode = verify_totp_code(secret, payload.code)
    if not valid:
        _record_failed(conn, rate_key)
        raise HTTPException(status_code=401, detail="Invalid verification code")

    update_totp_state(
        conn,
        curr_user["userID"],
        True,
        datetime.now(timezone.utc),
        timecode,
    )

    backup_codes = generate_backup_codes()
    store_backup_codes(conn, curr_user["userID"], backup_codes)
    clear_rate_limit(conn, rate_key)

    return {"backup_codes": backup_codes}


@router.post("/2fa")
def verify_two_factor_login(
    payload: TwoFactorLoginRequest,
    request: Request,
    pending_user_id: int = Depends(get_pending_2fa_user),
    conn=Depends(connect_to_db),
):
    _validate_code_payload(payload.code, payload.backup_code)

    rate_key = _rate_limit_key("2fa-login", pending_user_id, request)
    _ensure_rate_limit(conn, rate_key)

    security_state = _get_user_security_state(conn, pending_user_id)
    if not security_state.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")

    if payload.code:
        secret = get_decrypted_totp_secret(conn, pending_user_id)
        if not secret:
            raise HTTPException(status_code=400, detail="Two-factor authentication is not configured")

        valid, timecode = verify_totp_code(secret, payload.code)
        if not valid:
            _record_failed(conn, rate_key)
            raise HTTPException(status_code=401, detail="Invalid authentication code")

        last_timecode = security_state.get("totp_last_used_timecode")
        if timecode is not None and last_timecode == timecode:
            _record_failed(conn, rate_key)
            raise HTTPException(status_code=401, detail="Invalid authentication code")

        update_totp_last_used_timecode(conn, pending_user_id, timecode)
    else:
        if not verify_and_consume_backup_code(conn, pending_user_id, payload.backup_code or ""):
            _record_failed(conn, rate_key)
            raise HTTPException(status_code=401, detail="Invalid authentication code")

    clear_rate_limit(conn, rate_key)

    token = create_access_token({"user_id": pending_user_id})
    user = _get_user_profile(conn, pending_user_id)

    return {
        "message": "Login successful!",
        "access_token": token,
        "token_type": "bearer",
        "requires_2fa": False,
        "user": user,
    }


@router.delete("/2fa")
def disable_two_factor(
    payload: TwoFactorDisableRequest,
    request: Request,
    curr_user: dict = Depends(get_current_user),
    conn=Depends(connect_to_db),
):
    _validate_code_payload(payload.code, payload.backup_code)

    rate_key = _rate_limit_key("2fa-disable", curr_user["userID"], request)
    _ensure_rate_limit(conn, rate_key)

    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT password, totp_enabled FROM users WHERE "userID" = %s;',
            (curr_user["userID"],),
        )
        row = cursor.fetchone()

    if not row or not row.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")

    if not verify_password(payload.password, row["password"]):
        _record_failed(conn, rate_key)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if payload.code:
        secret = get_decrypted_totp_secret(conn, curr_user["userID"])
        if not secret:
            raise HTTPException(status_code=400, detail="Two-factor authentication is not configured")

        valid, timecode = verify_totp_code(secret, payload.code)
        if not valid:
            _record_failed(conn, rate_key)
            raise HTTPException(status_code=401, detail="Invalid authentication code")

        update_totp_last_used_timecode(conn, curr_user["userID"], timecode)
    else:
        if not verify_and_consume_backup_code(conn, curr_user["userID"], payload.backup_code or ""):
            _record_failed(conn, rate_key)
            raise HTTPException(status_code=401, detail="Invalid authentication code")

    clear_totp_state(conn, curr_user["userID"])
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM user_backup_codes WHERE user_id = %s;",
            (curr_user["userID"],),
        )
    conn.commit()
    clear_rate_limit(conn, rate_key)

    return {"message": "Two-factor authentication disabled"}


@router.post("/2fa/backup-codes/regenerate", response_model=TwoFactorVerifySetupResponse)
def regenerate_backup_codes(
    payload: TwoFactorRegenerateRequest,
    request: Request,
    curr_user: dict = Depends(get_current_user),
    conn=Depends(connect_to_db),
):
    rate_key = _rate_limit_key("2fa-backup", curr_user["userID"], request)
    _ensure_rate_limit(conn, rate_key)

    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT password, totp_enabled FROM users WHERE "userID" = %s;',
            (curr_user["userID"],),
        )
        row = cursor.fetchone()

    if not row or not row.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")

    if not verify_password(payload.password, row["password"]):
        _record_failed(conn, rate_key)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    secret = get_decrypted_totp_secret(conn, curr_user["userID"])
    if not secret:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not configured")

    valid, timecode = verify_totp_code(secret, payload.code)
    if not valid:
        _record_failed(conn, rate_key)
        raise HTTPException(status_code=401, detail="Invalid authentication code")

    update_totp_last_used_timecode(conn, curr_user["userID"], timecode)

    backup_codes = generate_backup_codes()
    store_backup_codes(conn, curr_user["userID"], backup_codes)
    clear_rate_limit(conn, rate_key)

    return {"backup_codes": backup_codes}
