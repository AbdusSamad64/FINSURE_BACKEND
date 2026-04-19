"""Remove the dashboard/dataset-level RLS filter that was set up in the
Superset UI.

Why:
    That filter uses `{{current_username()}}` which resolves to None for
    guest-token users in our setup, producing broken SQL:
        WHERE ("userID" = CAST(None AS INTEGER))

    The backend's guest-token endpoint already injects a concrete, per-user
    RLS clause (`"userID" = <int>`) before minting the token. That alone
    provides per-user isolation -- the UI-level filter is redundant and
    harmful.

Run inside the Superset container:
    docker cp drop_ui_rls.py finsure-superset:/tmp/drop_ui_rls.py
    docker exec -i finsure-superset superset shell < /tmp/drop_ui_rls.py
"""

from superset import db  # type: ignore  # noqa: E402
from superset.connectors.sqla.models import RowLevelSecurityFilter  # type: ignore  # noqa: E402


deleted = 0
for f in db.session.query(RowLevelSecurityFilter).all():
    clause = (f.clause or "").strip()
    print(f"[RLS] id={f.id} name={f.name!r} clause={clause!r}")
    if "current_username" in clause or '"userID"' in clause:
        db.session.delete(f)
        deleted += 1

db.session.commit()
print(f"Deleted {deleted} UI-level RLS filter(s).")
