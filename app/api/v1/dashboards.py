"""Superset embedded-dashboard bridge.

Mints a short-lived Superset "guest token" for the currently authenticated
FINSURE user. The token is scoped to a single dashboard and carries a
row-level-security clause so the user only sees their own transactions.

Flow:
    1. Frontend calls POST /api/v1/dashboards/guest-token with FINSURE JWT.
    2. This endpoint (server-to-server) logs into Superset as admin, gets a
       Superset access token, then requests a guest token for the current
       user via Superset's /security/guest_token/ API.
    3. Frontend passes the guest token to @superset-ui/embedded-sdk, which
       renders the dashboard in an iframe.
"""

from __future__ import annotations

import os
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.db.database import get_db_connection
from app.utils.jwt_util import get_current_user

router = APIRouter(prefix="/api/v1/dashboards", tags=["Dashboards"])


def _superset_public_url() -> str:
    """URL that the user's browser should load Superset from (iframe domain).

    Local dev default is localhost because the Superset container is published
    to the host on port 8088.
    """
    return os.getenv("SUPERSET_URL", "http://localhost:8088").rstrip("/")


def _superset_internal_url() -> str:
    """URL the backend container should use to talk to Superset server-to-server.

    When the backend runs in Docker, `localhost` points at the backend container
    itself, not the Superset container. In that case set:
        SUPERSET_INTERNAL_URL=http://superset:8088

    If unset, we fall back to the public URL for non-Docker / single-host setups.
    """
    return os.getenv("SUPERSET_INTERNAL_URL", _superset_public_url()).rstrip("/")


def _dashboard_uuid() -> str:
    uuid = os.getenv("SUPERSET_DASHBOARD_UUID", "").strip()
    if not uuid:
        raise HTTPException(
            status_code=503,
            detail=(
                "SUPERSET_DASHBOARD_UUID is not set. Enable embedding on the "
                "dashboard in the Superset UI (... menu -> Embed dashboard) "
                "and paste the UUID into your .env."
            ),
        )
    return uuid


async def _get_superset_access_token(client: httpx.AsyncClient) -> str:
    """Log in to Superset as the admin user and return a short-lived access
    token. The admin credentials only live on the backend; the frontend never
    sees them."""
    username = os.getenv("SUPERSET_ADMIN_USERNAME")
    password = os.getenv("SUPERSET_ADMIN_PASSWORD")
    if not username or not password:
        raise HTTPException(
            status_code=503,
            detail="SUPERSET_ADMIN_USERNAME / SUPERSET_ADMIN_PASSWORD are not set.",
        )

    resp = await client.post(
        f"{_superset_internal_url()}/api/v1/security/login",
        json={
            "username": username,
            "password": password,
            "provider": "db",
            "refresh": True,
        },
        timeout=15.0,
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Superset login failed ({resp.status_code}): {resp.text[:200]}",
        )
    token = resp.json().get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Superset returned no access_token.")
    return token


async def _get_csrf_token(client: httpx.AsyncClient, access_token: str) -> str:
    """Fetch a CSRF token for use with the guest_token endpoint."""
    resp = await client.get(
        f"{_superset_internal_url()}/api/v1/security/csrf_token/",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10.0,
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Superset CSRF fetch failed ({resp.status_code}): {resp.text[:200]}",
        )
    return resp.json().get("result", "")


def _user_transaction_count(user_id: int) -> int:
    """Return how many transactions the current FINSURE user has. Used by the
    frontend to decide between rendering the embedded dashboard and a friendly
    empty-state card."""
    conn = get_db_connection()
    if conn is None:
        # Don't fail the whole request just because the count query blew up;
        # assume "has data" so the dashboard still mounts.
        return 1
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT COUNT(*) AS c FROM transactions WHERE "userID" = %s',
                (user_id,),
            )
            row = cur.fetchone()
            return int(row["c"]) if row else 0
    except Exception:
        return 1
    finally:
        conn.close()


@router.post("/guest-token")
async def mint_guest_token(curr_user: dict = Depends(get_current_user)) -> dict:
    """Return a Superset guest token + dashboard UUID for the current user.

    The guest token carries an RLS clause that filters the `transactions`
    table down to rows where `userID` matches the caller's FINSURE userID,
    so each logged-in user only sees their own data even though they all
    hit the same Superset dashboard.
    """
    dashboard_uuid = _dashboard_uuid()
    user_id = str(curr_user["userID"])
    first = (curr_user.get("name") or "FINSURE").split(" ", 1)[0]
    last = (curr_user.get("name") or "User").split(" ", 1)[-1]

    # Cheap pre-check: if the user has no transactions yet, tell the frontend
    # to render a friendly empty state instead of a dashboard full of
    # "No results for this query" tiles.
    txn_count = _user_transaction_count(int(user_id))
    if txn_count == 0:
        return {
            "hasData": False,
            "transactionCount": 0,
            "dashboardId": dashboard_uuid,
            "supersetDomain": _superset_public_url(),
        }

    payload = {
        "user": {
            "username": user_id,            # Superset sees this as the username
            "first_name": first,
            "last_name": last,
        },
        "resources": [
            {"type": "dashboard", "id": dashboard_uuid},
        ],
        "rls": [
            # Matches the RLS rule you set up in the Superset UI; belt-and-braces.
            {"clause": f'"userID" = {int(user_id)}'},
        ],
    }

    async with httpx.AsyncClient() as client:
        access_token = await _get_superset_access_token(client)
        csrf_token = await _get_csrf_token(client, access_token)

        resp = await client.post(
            f"{_superset_internal_url()}/api/v1/security/guest_token/",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-CSRFToken": csrf_token,
                "Referer": _superset_internal_url(),
            },
            timeout=15.0,
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Superset guest_token request failed ({resp.status_code}): "
                f"{resp.text[:300]}"
            ),
        )

    token = resp.json().get("token")
    if not token:
        raise HTTPException(status_code=502, detail="Superset returned no guest token.")

    return {
        "hasData": True,
        "transactionCount": txn_count,
        "token": token,
        "dashboardId": dashboard_uuid,
        "supersetDomain": _superset_public_url(),
    }
