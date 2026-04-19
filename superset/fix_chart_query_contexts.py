"""Patch the 6 FINSURE charts so guest-token embedded requests stop 403ing
with "Guest user cannot modify chart payload".

Background:
    Superset's `query_context_modified()` check (security/manager.py) compares
    the incoming `metrics` / `columns` / `groupby` arrays against what is
    stored on the chart. It looks at BOTH `chart.params_dict.get(key)` AND
    `chart.query_context -> queries[].<key>`.

    `setup_charts.py` only saved `params`, and for the `big_number_total` /
    `pie` charts it used `metric` (singular), so `params_dict.get("metrics")`
    returns empty -> every request looks "modified" -> 403.

    This script PUTs a `query_context` JSON on each existing chart with
    metrics / columns / groupby populated so the subset check passes.

Run (from repo root):
    python FINSURE_BACKEND/superset/fix_chart_query_contexts.py
"""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx

SUPERSET = "http://localhost:8088"
ADMIN = "admin"
PASSWORD = "finsure123"


def die(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def login(client: httpx.Client) -> dict[str, str]:
    r = client.post(
        f"{SUPERSET}/api/v1/security/login",
        json={"username": ADMIN, "password": PASSWORD, "provider": "db", "refresh": True},
    )
    if r.status_code != 200:
        die(f"login failed ({r.status_code}): {r.text[:300]}")
    access = r.json()["access_token"]
    r = client.get(
        f"{SUPERSET}/api/v1/security/csrf_token/",
        headers={"Authorization": f"Bearer {access}"},
    )
    if r.status_code != 200:
        die(f"csrf fetch failed ({r.status_code}): {r.text[:300]}")
    csrf = r.json()["result"]
    return {
        "Authorization": f"Bearer {access}",
        "X-CSRFToken": csrf,
        "Referer": SUPERSET,
        "Content-Type": "application/json",
    }


def list_charts(client: httpx.Client, headers: dict[str, str]) -> list[dict[str, Any]]:
    r = client.get(f"{SUPERSET}/api/v1/chart/?q=(page_size:100)", headers=headers)
    if r.status_code != 200:
        die(f"list charts failed ({r.status_code}): {r.text[:300]}")
    return r.json()["result"]


def get_chart(client: httpx.Client, headers: dict[str, str], cid: int) -> dict[str, Any]:
    r = client.get(f"{SUPERSET}/api/v1/chart/{cid}", headers=headers)
    if r.status_code != 200:
        die(f"get chart {cid} failed ({r.status_code}): {r.text[:300]}")
    return r.json()["result"]


# Declared per chart name so we don't depend on params being correct.
# Keys must match slice_name exactly as created by setup_charts.py.
CHART_QC_SPEC: dict[str, dict[str, list[Any]]] = {
    "Total Net Amount": {
        "metrics": ["SUM_AMOUNT"],
        "columns": [],
        "groupby": [],
    },
    "Transactions (Count)": {
        "metrics": ["COUNT_TRXID"],
        "columns": [],
        "groupby": [],
    },
    "Amount by Transaction Type": {
        "metrics": ["SUM_AMOUNT"],
        "columns": ["trxType"],
        "groupby": ["trxType"],
    },
    "Monthly Amount by Type": {
        "metrics": ["SUM_AMOUNT"],
        "columns": ["date", "trxType"],
        "groupby": ["trxType"],
    },
    "Cash Flow Trend": {
        "metrics": ["SUM_AMOUNT"],
        "columns": ["date"],
        "groupby": [],
    },
    "Recent Transactions": {
        "metrics": [],
        "columns": ["date", "trxDetail", "trxType", "amount"],
        "groupby": [],
    },
}


SUM_AMOUNT_METRIC = {
    "expressionType": "SIMPLE",
    "column": {"column_name": "amount", "type": "NUMERIC"},
    "aggregate": "SUM",
    "label": "Sum Amount",
    "optionName": "metric_sum_amount",
}
COUNT_TRXID_METRIC = {
    "expressionType": "SIMPLE",
    "column": {"column_name": "trxID", "type": "NUMERIC"},
    "aggregate": "COUNT",
    "label": "Transactions",
    "optionName": "metric_count_trxid",
}

METRIC_LOOKUP = {"SUM_AMOUNT": SUM_AMOUNT_METRIC, "COUNT_TRXID": COUNT_TRXID_METRIC}


def build_query_context(
    chart: dict[str, Any], spec: dict[str, list[Any]], ds_id: int
) -> dict[str, Any]:
    """Build a minimal query_context JSON with metrics/columns/groupby so the
    guest-token `query_context_modified` subset check passes."""
    params = json.loads(chart["params"]) if chart.get("params") else {}

    metrics = [METRIC_LOOKUP[m] for m in spec["metrics"]]

    # Ensure form_data mirrors params plus the plural `metrics` key (covers
    # the `params_dict.get("metrics")` branch in query_context_modified).
    form_data = dict(params)
    if metrics and not form_data.get("metrics"):
        form_data["metrics"] = metrics
    form_data.setdefault("columns", spec["columns"])
    form_data.setdefault("groupby", spec["groupby"])

    return {
        "datasource": {"id": ds_id, "type": "table"},
        "force": False,
        "queries": [
            {
                "time_range": params.get("time_range", "No filter"),
                "filters": [],
                "extras": {"having": "", "where": ""},
                "applied_time_extras": {},
                "columns": spec["columns"],
                "metrics": metrics,
                "orderby": [],
                "annotation_layers": [],
                "row_limit": params.get("row_limit", 1000),
                "series_limit": 0,
                "order_desc": True,
                "url_params": {},
                "custom_params": {},
                "custom_form_data": {},
            }
        ],
        "form_data": form_data,
        "result_format": "json",
        "result_type": "full",
    }


def patch_chart(
    client: httpx.Client, headers: dict[str, str], cid: int, payload: dict[str, Any]
) -> None:
    r = client.put(
        f"{SUPERSET}/api/v1/chart/{cid}",
        headers=headers,
        content=json.dumps(payload),
    )
    if r.status_code not in (200, 201):
        die(f"PUT chart {cid} failed ({r.status_code}): {r.text[:400]}")


def main() -> None:
    with httpx.Client(timeout=30.0) as client:
        headers = login(client)
        charts = list_charts(client, headers)
        by_name = {c["slice_name"]: c for c in charts}

        missing = [n for n in CHART_QC_SPEC if n not in by_name]
        if missing:
            die(f"charts not found: {missing}. Run setup_charts.py first.")

        for name, spec in CHART_QC_SPEC.items():
            summary = by_name[name]
            full = get_chart(client, headers, summary["id"])
            # datasource_id lives on the list-summary but not always on the
            # full GET -> derive from `datasource` field or fall back.
            ds_id = summary.get("datasource_id")
            if ds_id is None and full.get("datasource"):
                # datasource field can look like "1__table" or "1"
                ds_id = int(str(full["datasource"]).split("__")[0])
            if ds_id is None:
                die(f"could not determine ds_id for chart #{summary['id']} ({name})")
            qc = build_query_context(full, spec, ds_id)

            # Also patch params to include `metrics` plural so
            # params_dict.get("metrics") isn't empty for big_number / pie.
            params = json.loads(full["params"]) if full.get("params") else {}
            if spec["metrics"] and not params.get("metrics"):
                params["metrics"] = qc["queries"][0]["metrics"]

            patch_chart(
                client,
                headers,
                summary["id"],
                {
                    "query_context": json.dumps(qc),
                    "params": json.dumps(params),
                },
            )
            print(f"  patched #{summary['id']}: {name}")

    print("Done. Reload the dashboard in the browser.")


if __name__ == "__main__":
    main()
