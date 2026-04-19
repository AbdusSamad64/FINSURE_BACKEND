"""Grant the minimum permissions the Superset `Public` role needs so that
guest-token embedded dashboards can load.

Runs *inside* the Superset container (via `docker exec ... superset shell`),
so we can reach the FAB security manager directly and avoid the limited roles
REST API.

Usage (from host):
    docker cp grant_public_perms.py finsure-superset:/tmp/grant_public_perms.py
    docker exec finsure-superset superset shell < /tmp/grant_public_perms.py

Or pipe it in one shot (what our runner does).
"""

from superset import security_manager, db  # type: ignore  # noqa: E402


ROLE_NAME = "Public"

REQUIRED = [
    ("can_read", "Dashboard"),
    ("can_read", "Chart"),
    ("can_read", "Dataset"),
    ("can_read", "Database"),
    ("can_read", "Explore"),
    ("can_explore", "Superset"),
    ("can_samples", "Datasource"),
    ("can_csrf_token", "SecurityRestApi"),
    ("can_dashboard", "Superset"),
    ("can_time_range", "Api"),
    ("can_list", "DynamicPlugin"),
    ("can_drill_to_detail", "Dashboard"),
    ("can_get_or_create_dataset", "DatasetRestApi"),
    ("can_read", "Annotation"),
    ("can_read", "AnnotationLayer"),
    ("can_read", "CssTemplate"),
    ("can_read", "Query"),
    ("can_read", "SavedQuery"),
    ("can_read", "Log"),
    ("can_read", "EmbeddedDashboard"),
]

role = security_manager.find_role(ROLE_NAME)
if role is None:
    raise SystemExit(f"role '{ROLE_NAME}' not found")

added = 0
for perm_name, view_name in REQUIRED:
    pv = security_manager.find_permission_view_menu(perm_name, view_name)
    if pv is None:
        # create it so embedded flow doesn't break if Superset didn't register it
        pv = security_manager.add_permission_view_menu(perm_name, view_name)
    if pv not in role.permissions:
        role.permissions.append(pv)
        added += 1

db.session.commit()
print(f"Added {added} permissions to role '{ROLE_NAME}' (total: {len(role.permissions)})")
