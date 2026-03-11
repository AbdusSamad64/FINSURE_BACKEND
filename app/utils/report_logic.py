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

    # Monthly aggregation (Post-processing)
    monthly = {}
    for trx in rows:
        month = trx["date"].strftime("%B")
        monthly.setdefault(month, {"income": 0, "expenses": 0})

        if trx["trxType"] == "credit":
            monthly[month]["income"] += trx["amount"]
        else:
            monthly[month]["expenses"] += trx["amount"]

    monthly_data = [
        {
            "month": m,
            "income": v["income"],
            "expenses": v["expenses"],
            "net": v["income"] - v["expenses"]
        }
        for m, v in monthly.items()
    ]

    # Final response
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
            "profitMargin": profit_margin
        },
        "transactions": transactions,
        "monthlyData": monthly_data
    }
