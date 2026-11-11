

def payload(**overrides):
    data = {
        "type": "expense",
        "amount_satangs": 12500,
        "date": "2026-11-11",
        "category": "อาหาร",
        "note": "มื้อกลางวัน",
    }
    data.update(overrides)
    return data


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_read_transaction(client):
    created = client.post("/api/transactions", json=payload())

    assert created.status_code == 201
    body = created.json()
    assert body["id"] > 0
    assert body["amount_satangs"] == 12500
    assert body["type"] == "expense"

    fetched = client.get(f"/api/transactions/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["category"] == "อาหาร"


def test_list_filters_by_type_and_date_range(client):
    client.post("/api/transactions", json=payload())
    client.post(
        "/api/transactions",
        json=payload(type="income", amount_satangs=300000, date="2026-11-12"),
    )

    response = client.get(
        "/api/transactions",
        params={"type": "income", "start_date": "2026-11-12", "end_date": "2026-11-12"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["type"] == "income"


def test_list_rejects_invalid_type_and_reversed_dates(client):
    invalid_type = client.get("/api/transactions", params={"type": "transfer"})
    reversed_dates = client.get(
        "/api/transactions",
        params={"start_date": "2026-11-12", "end_date": "2026-11-11"},
    )

    assert invalid_type.status_code == 422
    assert reversed_dates.status_code == 422


def test_create_rejects_invalid_values(client):
    bad_type = client.post("/api/transactions", json=payload(type="transfer"))
    zero_amount = client.post("/api/transactions", json=payload(amount_satangs=0))
    negative_amount = client.post("/api/transactions", json=payload(amount_satangs=-1))
    missing_category = client.post("/api/transactions", json=payload(category=""))
    client_supplied_id = client.post("/api/transactions", json=payload(id=999))

    assert bad_type.status_code == 422
    assert zero_amount.status_code == 422
    assert negative_amount.status_code == 422
    assert missing_category.status_code == 422
    assert client_supplied_id.status_code == 422


def test_transaction_text_is_stored_as_data(client):
    marker = "<script>alert('x')</script>"
    created = client.post("/api/transactions", json=payload(note=marker))

    assert created.status_code == 201
    assert created.json()["note"] == marker


def test_sql_looking_category_is_treated_as_plain_data(client):
    marker = "' OR 1=1 --"
    created = client.post("/api/transactions", json=payload(category=marker))

    assert created.status_code == 201
    assert created.json()["category"] == marker
    assert len(client.get("/api/transactions").json()) == 1


def test_update_transaction(client):
    created = client.post("/api/transactions", json=payload())
    transaction_id = created.json()["id"]

    updated = client.put(
        f"/api/transactions/{transaction_id}",
        json=payload(type="income", amount_satangs=500000, category="เงินเดือน"),
    )

    assert updated.status_code == 200
    assert updated.json()["type"] == "income"
    assert updated.json()["amount_satangs"] == 500000
    assert updated.json()["category"] == "เงินเดือน"


def test_delete_transaction_and_return_not_found_afterward(client):
    created = client.post("/api/transactions", json=payload())
    transaction_id = created.json()["id"]

    deleted = client.delete(f"/api/transactions/{transaction_id}")

    assert deleted.status_code == 204
    assert client.get(f"/api/transactions/{transaction_id}").status_code == 404


def test_missing_transaction_returns_not_found(client):
    assert client.get("/api/transactions/999").status_code == 404
    assert client.put("/api/transactions/999", json=payload()).status_code == 404
    assert client.delete("/api/transactions/999").status_code == 404


def test_cors_allows_only_local_frontend_origin(client):
    allowed = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    disallowed = client.get("/health", headers={"Origin": "https://example.com"})

    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-origin" not in disallowed.headers
