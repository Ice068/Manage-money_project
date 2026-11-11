from datetime import date, timedelta


def transaction_payload(kind, amount, when, category="ทั่วไป"):
    return {
        "type": kind,
        "amount_satangs": amount,
        "date": when,
        "category": category,
    }


def test_dashboard_summarizes_period_and_estimates_runway(client):
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 10000, "2026-11-01", "อาหาร"),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload("income", 50000, "2026-11-05", "เงินเดือน"),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 20000, "2026-11-10", "เดินทาง"),
    )
    client.put(
        "/api/dashboard/settings",
        json={"opening_balance_satangs": 100000, "opening_balance_date": "2026-11-01"},
    )

    response = client.get(
        "/api/dashboard/summary",
        params={"start_date": "2026-11-01", "end_date": "2026-11-10"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 10
    assert data["income_satangs"] == 50000
    assert data["expense_satangs"] == 30000
    assert data["net_satangs"] == 20000
    assert data["current_balance_satangs"] == 120000
    assert data["average_daily_expense_satangs"] == 3000
    assert data["runway_days"] == 40


def test_dashboard_excludes_transactions_before_opening_date_from_balance(client):
    client.post(
        "/api/transactions",
        json=transaction_payload("income", 90000, "2026-11-01"),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 10000, "2026-11-05"),
    )
    client.put(
        "/api/dashboard/settings",
        json={"opening_balance_satangs": 50000, "opening_balance_date": "2026-11-03"},
    )

    response = client.get(
        "/api/dashboard/summary",
        params={"start_date": "2026-11-01", "end_date": "2026-11-05"},
    )

    assert response.status_code == 200
    assert response.json()["income_satangs"] == 90000
    assert response.json()["current_balance_satangs"] == 40000


def test_dashboard_returns_no_runway_when_period_has_no_expenses(client):
    response = client.get(
        "/api/dashboard/summary",
        params={"start_date": "2026-11-01", "end_date": "2026-11-10"},
    )

    assert response.status_code == 200
    assert response.json()["average_daily_expense_satangs"] is None
    assert response.json()["runway_days"] is None


def test_dashboard_reports_zero_runway_when_balance_is_not_positive(client):
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 10000, "2026-11-05"),
    )

    response = client.get(
        "/api/dashboard/summary",
        params={"start_date": "2026-11-01", "end_date": "2026-11-10"},
    )

    assert response.status_code == 200
    assert response.json()["current_balance_satangs"] == -10000
    assert response.json()["runway_days"] == 0


def test_dashboard_rejects_reversed_and_future_ranges(client):
    reversed_range = client.get(
        "/api/dashboard/summary",
        params={"start_date": "2026-11-10", "end_date": "2026-11-01"},
    )
    future_date = date.today() + timedelta(days=1)
    future_range = client.get(
        "/api/dashboard/summary",
        params={"start_date": date.today().isoformat(), "end_date": future_date.isoformat()},
    )

    assert reversed_range.status_code == 422
    assert future_range.status_code == 422


def test_dashboard_settings_validate_values_and_reject_extra_fields(client):
    negative = client.put(
        "/api/dashboard/settings",
        json={"opening_balance_satangs": -1, "opening_balance_date": "2026-11-01"},
    )
    excessive = client.put(
        "/api/dashboard/settings",
        json={
            "opening_balance_satangs": 1_000_000_000_001,
            "opening_balance_date": "2026-11-01",
        },
    )
    extra = client.put(
        "/api/dashboard/settings",
        json={
            "opening_balance_satangs": 1,
            "opening_balance_date": "2026-11-01",
            "id": 50,
        },
    )
    future_date = client.put(
        "/api/dashboard/settings",
        json={
            "opening_balance_satangs": 1,
            "opening_balance_date": (date.today() + timedelta(days=1)).isoformat(),
        },
    )

    assert negative.status_code == 422
    assert excessive.status_code == 422
    assert extra.status_code == 422
    assert future_date.status_code == 422


def test_default_dashboard_settings_do_not_need_a_write(client):
    response = client.get("/api/dashboard/settings")

    assert response.status_code == 200
    assert response.json()["opening_balance_satangs"] == 0
    assert response.json()["opening_balance_date"] == date.today().isoformat()
