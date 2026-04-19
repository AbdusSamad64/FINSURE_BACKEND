"""One-shot script that creates a FINSURE dashboard + charts in Superset.

Run once after the Superset stack is up and the `transactions` dataset exists.
Logs in as admin, then POSTs chart + dashboard payloads via the REST API.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx

SUPERSET = "http://localhost:8088"
ADMIN = "admin"
PASSWORD = "finsure123"
DATASET_NAME = "transactions"
DASHBOARD_TITLE = "FINSURE Financial Overview"


def die(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def login(client: httpx.Client) -> tuple[str, str]:
    r = client.post(
        f"{SUPERSET}/api/v1/security/login",
        json={
            "username": ADMIN,
            "password": PASSWORD,
            "provider": "db",
            "refresh": True,
        },
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
    return access, csrf


def auth_headers(access: str, csrf: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access}",
        "X-CSRFToken": csrf,
        "Referer": SUPERSET,
        "Content-Type": "application/json",
    }


def find_dataset_id(client: httpx.Client, headers: dict[str, str]) -> int:
    q = '(filters:!((col:table_name,opr:eq,value:%s)))' % DATASET_NAME
    r = client.get(f"{SUPERSET}/api/v1/dataset/?q={q}", headers=headers)
    if r.status_code != 200:
        die(f"dataset lookup failed ({r.status_code}): {r.text[:300]}")
    result = r.json()["result"]
    if not result:
        die(f"no dataset named '{DATASET_NAME}' found in Superset")
    return int(result[0]["id"])


# --- chart payload builders -------------------------------------------------

def _base_params(ds_id: int, viz_type: str) -> dict[str, Any]:
    return {
        "datasource": f"{ds_id}__table",
        "viz_type": viz_type,
        "adhoc_filters": [],
        "extra_form_data": {},
        "dashboards": [],
    }


def _sum_amount_metric(label: str = "Sum Amount") -> dict[str, Any]:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": "amount", "type": "NUMERIC"},
        "aggregate": "SUM",
        "label": label,
        "optionName": f"metric_sum_amount_{label}",
    }


def chart_big_number(ds_id: int) -> dict[str, Any]:
    params = _base_params(ds_id, "big_number_total")
    params.update({
        "metric": _sum_amount_metric("Total Net Amount"),
        "header_font_size": 0.4,
        "subheader_font_size": 0.15,
        "y_axis_format": "SMART_NUMBER",
    })
    return {
        "slice_name": "Total Net Amount",
        "viz_type": "big_number_total",
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }


def chart_big_number_txn_count(ds_id: int) -> dict[str, Any]:
    params = _base_params(ds_id, "big_number_total")
    params.update({
        "metric": {
            "expressionType": "SIMPLE",
            "column": {"column_name": "trxID", "type": "NUMERIC"},
            "aggregate": "COUNT",
            "label": "Transactions",
            "optionName": "metric_count_trxid",
        },
        "y_axis_format": "SMART_NUMBER",
    })
    return {
        "slice_name": "Transactions (Count)",
        "viz_type": "big_number_total",
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }


def chart_pie_by_type(ds_id: int) -> dict[str, Any]:
    params = _base_params(ds_id, "pie")
    params.update({
        "groupby": ["trxType"],
        "metric": _sum_amount_metric("Sum Amount"),
        "row_limit": 25,
        "show_legend": True,
        "label_type": "key_value",
        "number_format": "SMART_NUMBER",
    })
    return {
        "slice_name": "Amount by Transaction Type",
        "viz_type": "pie",
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }


def chart_bar_monthly(ds_id: int) -> dict[str, Any]:
    params = _base_params(ds_id, "echarts_timeseries_bar")
    params.update({
        "x_axis": "date",
        "time_grain_sqla": "P1M",
        "metrics": [_sum_amount_metric("Sum Amount")],
        "groupby": ["trxType"],
        "row_limit": 1000,
        "show_legend": True,
        "x_axis_title": "Month",
        "y_axis_title": "Amount",
        "y_axis_format": "SMART_NUMBER",
        "orientation": "vertical",
    })
    return {
        "slice_name": "Monthly Amount by Type",
        "viz_type": "echarts_timeseries_bar",
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }


def chart_line_cumulative(ds_id: int) -> dict[str, Any]:
    params = _base_params(ds_id, "echarts_timeseries_line")
    params.update({
        "x_axis": "date",
        "time_grain_sqla": "P1D",
        "metrics": [_sum_amount_metric("Sum Amount")],
        "row_limit": 10000,
        "show_legend": True,
        "x_axis_title": "Date",
        "y_axis_title": "Cumulative Amount",
        "y_axis_format": "SMART_NUMBER",
        "opacity": 0.2,
        "markerEnabled": False,
    })
    return {
        "slice_name": "Cash Flow Trend",
        "viz_type": "echarts_timeseries_line",
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }


def chart_table_recent(ds_id: int) -> dict[str, Any]:
    params = _base_params(ds_id, "table")
    params.update({
        "query_mode": "raw",
        "all_columns": ["date", "trxDetail", "trxType", "amount"],
        "order_by_cols": ['["date",false]'],
        "row_limit": 25,
        "table_timestamp_format": "smart_date",
    })
    return {
        "slice_name": "Recent Transactions",
        "viz_type": "table",
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }


# --- main orchestration -----------------------------------------------------

def create_chart(client: httpx.Client, headers: dict[str, str], payload: dict) -> tuple[int, str]:
    r = client.post(f"{SUPERSET}/api/v1/chart/", headers=headers, content=json.dumps(payload))
    if r.status_code not in (200, 201):
        die(f"chart '{payload['slice_name']}' create failed ({r.status_code}): {r.text[:400]}")
    data = r.json()
    return int(data["id"]), data["result"]["slice_name"]


def make_position_json(charts: list[tuple[int, str]]) -> dict[str, Any]:
    """Build a valid dashboard `position_json` with each chart in its own row."""
    pos: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": DASHBOARD_TITLE}},
    }

    # two charts per row, width 6 each (grid is 12 wide)
    row_idx = 0
    for i in range(0, len(charts), 2):
        row_id = f"ROW-{row_idx}"
        row_children: list[str] = []
        for j, (chart_id, chart_name) in enumerate(charts[i : i + 2]):
            ch_id = f"CHART-{chart_id}"
            row_children.append(ch_id)
            pos[ch_id] = {
                "type": "CHART",
                "id": ch_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {
                    "width": 6,
                    "height": 50,
                    "chartId": chart_id,
                    "sliceName": chart_name,
                },
            }
        pos[row_id] = {
            "type": "ROW",
            "id": row_id,
            "children": row_children,
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        pos["GRID_ID"]["children"].append(row_id)
        row_idx += 1

    return pos


def create_dashboard(
    client: httpx.Client, headers: dict[str, str], charts: list[tuple[int, str]]
) -> int:
    position = make_position_json(charts)
    payload = {
        "dashboard_title": DASHBOARD_TITLE,
        "slug": "finsure-overview",
        "published": True,
        "position_json": json.dumps(position),
    }
    r = client.post(f"{SUPERSET}/api/v1/dashboard/", headers=headers, content=json.dumps(payload))
    if r.status_code not in (200, 201):
        die(f"dashboard create failed ({r.status_code}): {r.text[:400]}")
    dash_id = int(r.json()["id"])

    # attach charts to the dashboard via PUT on each chart
    for chart_id, _ in charts:
        r = client.put(
            f"{SUPERSET}/api/v1/chart/{chart_id}",
            headers=headers,
            content=json.dumps({"dashboards": [dash_id]}),
        )
        if r.status_code not in (200, 201):
            print(
                f"WARN: could not link chart {chart_id} to dashboard "
                f"({r.status_code}): {r.text[:200]}"
            )
    return dash_id


def main() -> None:
    with httpx.Client(timeout=30.0) as client:
        access, csrf = login(client)
        headers = auth_headers(access, csrf)
        ds_id = find_dataset_id(client, headers)
        print(f"Found dataset '{DATASET_NAME}' id={ds_id}")

        builders = [
            chart_big_number,
            chart_big_number_txn_count,
            chart_pie_by_type,
            chart_bar_monthly,
            chart_line_cumulative,
            chart_table_recent,
        ]
        charts: list[tuple[int, str]] = []
        for b in builders:
            payload = b(ds_id)
            cid, name = create_chart(client, headers, payload)
            print(f"  + chart #{cid}: {name}")
            charts.append((cid, name))

        dash_id = create_dashboard(client, headers, charts)
        print(f"Dashboard created: id={dash_id}  title='{DASHBOARD_TITLE}'")
        print(f"Open http://localhost:8088/superset/dashboard/{dash_id}/")


if __name__ == "__main__":
    main()
