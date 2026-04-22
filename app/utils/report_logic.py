# ---------------------------------------------------------------------------
# Income vs Expense
# ---------------------------------------------------------------------------
def build_income_expense_report(report, user_id: int, cursor):
    start_date = report["from"]
    end_date = report["to"]

    # Fetch transactions in range
    cursor.execute(
        """
        SELECT "trxID", date, amount, "trxType"
        FROM transactions
        WHERE "userID" = %s
          AND date BETWEEN %s AND %s
        ORDER BY date ASC;
        """,
        (user_id, start_date, end_date)
    )
    rows = cursor.fetchall()

    total_income = 0.0
    total_expense = 0.0
    transactions = []

    for trx in rows:
        if trx["trxType"] == "credit":
            total_income += trx["amount"]
            trx_type = "income"
        else:
            total_expense += trx["amount"]
            trx_type = "expense"

        transactions.append({
            "id": trx["trxID"],
            "date": trx["date"].date().isoformat(),
            "amount": trx["amount"],
            "type": trx_type
        })

    net_balance = total_income - total_expense
    profit_margin = (
        round((net_balance / total_income) * 100, 2)
        if total_income > 0 else 0
    )

    # Monthly aggregation (Post-processing) — preserves chronological order
    monthly = {}
    for trx in rows:
        # YYYY-MM key so ordering is stable across years
        key = trx["date"].strftime("%Y-%m")
        label = trx["date"].strftime("%B %Y")
        monthly.setdefault(key, {"label": label, "income": 0, "expenses": 0})
        if trx["trxType"] == "credit":
            monthly[key]["income"] += trx["amount"]
        else:
            monthly[key]["expenses"] += trx["amount"]

    monthly_data = [
        {
            "month": v["label"],
            "income": round(v["income"], 2),
            "expenses": round(v["expenses"], 2),
            "net": round(v["income"] - v["expenses"], 2),
        }
        for _, v in sorted(monthly.items())
    ]

    # P&L insights
    months_profitable = sum(1 for m in monthly_data if m["net"] > 0)
    months_in_loss = sum(1 for m in monthly_data if m["net"] < 0)
    num_months = max(len(monthly_data), 1)
    avg_monthly_income = total_income / num_months
    avg_monthly_expense = total_expense / num_months
    savings_rate = (
        round((net_balance / total_income) * 100, 1) if total_income > 0 else 0.0
    )

    best_month = max(monthly_data, key=lambda m: m["net"]) if monthly_data else None
    worst_month = min(monthly_data, key=lambda m: m["net"]) if monthly_data else None

    return {
        "reportId": str(report["report_id"]),
        "type": report["report_type"],
        "title": report["title"],
        "dateRange": f"{start_date} to {end_date}",
        "generatedDate": report["generated_on"].isoformat(),
        "summary": {
            "totalIncome": round(total_income, 2),
            "totalExpenses": round(total_expense, 2),
            "netBalance": round(net_balance, 2),
            "profitMargin": profit_margin,
            "avgMonthlyIncome": round(avg_monthly_income, 2),
            "avgMonthlyExpense": round(avg_monthly_expense, 2),
            "savingsRate": savings_rate,
            "monthsProfitable": months_profitable,
            "monthsInLoss": months_in_loss,
            "bestMonth": best_month,
            "worstMonth": worst_month,
        },
        "transactions": transactions,
        "monthlyData": monthly_data,
    }


# ---------------------------------------------------------------------------
# Cash Flow Summary
#
# Opening balance = net of all transactions BEFORE start_date.
# Closing balance = opening + inflows - outflows (within the window).
# Plus week-by-week aggregation for the PDF table.
# ---------------------------------------------------------------------------
def build_cashflow_report(report, user_id: int, cursor):
    start_date = report["from"]
    end_date = report["to"]

    # 1) Opening balance (everything BEFORE the window)
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN "trxType" = 'credit' THEN amount ELSE 0 END), 0) AS inflow_prior,
            COALESCE(SUM(CASE WHEN "trxType" <> 'credit' THEN amount ELSE 0 END), 0) AS outflow_prior
        FROM transactions
        WHERE "userID" = %s
          AND date < %s;
        """,
        (user_id, start_date)
    )
    prior = cursor.fetchone()
    opening_balance = (prior["inflow_prior"] or 0) - (prior["outflow_prior"] or 0)

    # 2) Transactions in the window
    cursor.execute(
        """
        SELECT "trxID", date, amount, "trxType"
        FROM transactions
        WHERE "userID" = %s
          AND date BETWEEN %s AND %s
        ORDER BY date ASC;
        """,
        (user_id, start_date, end_date)
    )
    rows = cursor.fetchall()

    total_inflows = 0.0
    total_outflows = 0.0
    transactions = []

    for trx in rows:
        if trx["trxType"] == "credit":
            total_inflows += trx["amount"]
            flow_type = "credit"
        else:
            total_outflows += trx["amount"]
            flow_type = "debit"

        transactions.append({
            "id": trx["trxID"],
            "date": trx["date"].date().isoformat(),
            "amount": trx["amount"],
            "flowType": flow_type,
        })

    closing_balance = opening_balance + total_inflows - total_outflows
    net_cash_change = total_inflows - total_outflows

    # 3) Weekly aggregation — group by ISO week within the window
    weekly = {}  # { "YYYY-Www": {"inflow": ..., "outflow": ...} }
    for trx in rows:
        iso_year, iso_week, _ = trx["date"].isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        weekly.setdefault(key, {"inflow": 0.0, "outflow": 0.0})
        if trx["trxType"] == "credit":
            weekly[key]["inflow"] += trx["amount"]
        else:
            weekly[key]["outflow"] += trx["amount"]

    # Walk weeks chronologically, carrying a running balance forward.
    running = opening_balance
    weekly_data = []
    for k, v in sorted(weekly.items()):
        net = v["inflow"] - v["outflow"]
        running += net
        weekly_data.append({
            "week": k,
            "inflow": round(v["inflow"], 2),
            "outflow": round(v["outflow"], 2),
            "net": round(net, 2),
            "runningBalance": round(running, 2),
        })

    # Extremes — largest single transaction on each side
    largest_inflow = max(
        (r for r in rows if r["trxType"] == "credit"),
        key=lambda r: r["amount"],
        default=None,
    )
    largest_outflow = max(
        (r for r in rows if r["trxType"] != "credit"),
        key=lambda r: r["amount"],
        default=None,
    )

    def _fmt_extreme(r):
        if not r:
            return None
        return {
            "amount": round(r["amount"], 2),
            "date": r["date"].date().isoformat(),
        }

    return {
        "reportId": str(report["report_id"]),
        "type": report["report_type"],
        "title": report["title"],
        "dateRange": f"{start_date} to {end_date}",
        "generatedDate": report["generated_on"].isoformat(),
        "summary": {
            "openingBalance": round(opening_balance, 2),
            "totalInflows": round(total_inflows, 2),
            "totalOutflows": round(total_outflows, 2),
            "closingBalance": round(closing_balance, 2),
            "netCashChange": round(net_cash_change, 2),
            "weeksCount": len(weekly_data),
            "largestInflow": _fmt_extreme(largest_inflow),
            "largestOutflow": _fmt_extreme(largest_outflow),
        },
        "transactions": transactions,
        "weeklyData": weekly_data,
    }


# ---------------------------------------------------------------------------
# Category Breakdown
#
# Joins transactions with the `categories` table (populated by the rule engine
# + LLM worker) and gives each category's share of inflows and outflows in
# the window.
# ---------------------------------------------------------------------------
def build_category_breakdown_report(report, user_id: int, cursor):
    start_date = report["from"]
    end_date = report["to"]

    # Per-category aggregation. LEFT JOIN so uncategorized txns still count
    # (they bucket into "Uncategorized").
    cursor.execute(
        """
        SELECT
            COALESCE(c.name, 'Uncategorized') AS category,
            t."trxType" AS trx_type,
            COUNT(*) AS txn_count,
            COALESCE(SUM(t.amount), 0) AS total_amount
        FROM transactions t
        LEFT JOIN categories c ON c."categID" = t."categID"
        WHERE t."userID" = %s
          AND t.date BETWEEN %s AND %s
        GROUP BY COALESCE(c.name, 'Uncategorized'), t."trxType"
        ORDER BY total_amount DESC;
        """,
        (user_id, start_date, end_date)
    )
    agg_rows = cursor.fetchall()

    total_income = 0.0
    total_expenses = 0.0
    by_category: dict[str, dict] = {}

    for row in agg_rows:
        name = row["category"]
        amount = float(row["total_amount"] or 0)
        count = int(row["txn_count"] or 0)
        ttype = "income" if row["trx_type"] == "credit" else "expense"

        if ttype == "income":
            total_income += amount
        else:
            total_expenses += amount

        # One bucket per (category, type) so Uber income != Uber refund
        key = f"{name}__{ttype}"
        by_category[key] = {
            "name": name,
            "type": ttype,
            "amount": round(amount, 2),
            "transactionCount": count,
        }

    # Attach percentages (of the matching side)
    breakdown = []
    for entry in by_category.values():
        base = total_income if entry["type"] == "income" else total_expenses
        entry["percentage"] = (
            round((entry["amount"] / base) * 100, 1) if base > 0 else 0.0
        )
        breakdown.append(entry)

    # Sort: expenses descending first, then income descending
    breakdown.sort(key=lambda x: (x["type"] != "expense", -x["amount"]))

    # Top categories for the summary cards
    expense_entries = [b for b in breakdown if b["type"] == "expense"]
    income_entries = [b for b in breakdown if b["type"] == "income"]
    top_expense = expense_entries[0] if expense_entries else None
    top_income = income_entries[0] if income_entries else None

    # Fetch raw transactions for the detail table (with category name)
    cursor.execute(
        """
        SELECT
            t."trxID",
            t.date,
            t.amount,
            t."trxType",
            COALESCE(c.name, 'Uncategorized') AS category
        FROM transactions t
        LEFT JOIN categories c ON c."categID" = t."categID"
        WHERE t."userID" = %s
          AND t.date BETWEEN %s AND %s
        ORDER BY t.date ASC;
        """,
        (user_id, start_date, end_date)
    )
    trx_rows = cursor.fetchall()

    transactions = [
        {
            "id": r["trxID"],
            "date": r["date"].date().isoformat(),
            "amount": r["amount"],
            "type": "income" if r["trxType"] == "credit" else "expense",
            "category": r["category"],
        }
        for r in trx_rows
    ]

    return {
        "reportId": str(report["report_id"]),
        "type": report["report_type"],
        "title": report["title"],
        "dateRange": f"{start_date} to {end_date}",
        "generatedDate": report["generated_on"].isoformat(),
        "summary": {
            "totalIncome": round(total_income, 2),
            "totalExpenses": round(total_expenses, 2),
            "categoriesCount": len({b["name"] for b in breakdown}),
            "topExpenseCategory": top_expense["name"] if top_expense else "—",
            "topExpenseAmount": top_expense["amount"] if top_expense else 0,
            "topIncomeCategory": top_income["name"] if top_income else "—",
            "topIncomeAmount": top_income["amount"] if top_income else 0,
        },
        "categoryBreakdown": breakdown,
        "transactions": transactions,
    }
