"""Exposes the list of banks FINSURE can parse statements for.

The frontend calls this to populate the 'Add Account' bank dropdown, the
per-file bank picker on the Upload page, and the 'Supported banks' hint.
The source of truth is the `banks` table — adding a row there (plus wiring
a parser in routes_files.py) makes the new bank show up in the UI
automatically.

Alongside the name we return two flags the frontend needs to adapt its UI:
    - isMobileWallet:   drives what we send in the `file_type` form field
                        when uploading (wallet vs bank statement)
    - requiresPassword: drives whether the password input is shown / enabled
                        next to a file on the upload screen
"""

from fastapi import APIRouter, Depends

from app.api.v1.auth import connect_to_db

router = APIRouter(prefix="/api/v1/banks", tags=["Banks"])

# Slugs that are actually mobile-wallet platforms rather than traditional banks.
# Matches the `bank_name` values routes_files.py branches on (lowercased).
_MOBILE_WALLET_SLUGS = {"easypaisa"}

# Banks whose statement PDFs are password-protected and therefore require the
# user to enter a password before we can parse them.
_PASSWORD_PROTECTED_SLUGS = {"meezan"}


@router.get("")
def list_banks(conn=Depends(connect_to_db)) -> dict:
    with conn.cursor() as cursor:
        cursor.execute('SELECT "bankID", name FROM banks ORDER BY "bankID"')
        rows = cursor.fetchall()

    banks = []
    for r in rows:
        slug = r["name"].strip().lower()
        banks.append(
            {
                "id": r["bankID"],
                "name": r["name"],
                "slug": slug,
                "isMobileWallet": slug in _MOBILE_WALLET_SLUGS,
                "requiresPassword": slug in _PASSWORD_PROTECTED_SLUGS,
            }
        )
    return {"banks": banks}
