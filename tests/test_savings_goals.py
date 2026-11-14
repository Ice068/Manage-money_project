from datetime import date, timedelta


def transaction_payload(kind, amount, when):
    return {
        "type": kind,
        "amount_satangs": amount,
        "date": when,
        "category": "ทดสอบ",
    }


def goal_payload(**overrides):
    payload = {
        "name": "จักรยาน",
        "target_amount_satangs": 500000,
        "saved_amount_satangs": 100000,
        "note": "สำหรับเดินทาง",
    }
    payload.update(overrides)
    return payload


def test_goal_includes_remaining_progress_and_estimated_date(client):
    today = date.today()
    start = today - timedelta(days=9)
    client.post(
        "/api/transactions",
        json=transaction_payload("income", 300000, start.isoformat()),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 100000, today.isoformat()),
    )

    response = client.post("/api/savings-goals", json=goal_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["amount_remaining_satangs"] == 400000
    assert data["progress_percent"] == 20
    assert data["average_daily_net_savings_satangs"] == 20000
    assert data["estimated_days"] == 20
    assert data["estimated_date"] == (today + timedelta(days=20)).isoformat()


def test_goal_has_no_date_estimate_when_net_savings_are_not_positive(client):
    today = date.today()
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 100000, today.isoformat()),
    )

    response = client.post("/api/savings-goals", json=goal_payload())

    assert response.status_code == 201
    assert response.json()["average_daily_net_savings_satangs"] is None
    assert response.json()["estimated_days"] is None
    assert response.json()["estimated_date"] is None


def test_completed_goal_reports_zero_remaining_and_full_progress(client):
    response = client.post(
        "/api/savings-goals",
        json=goal_payload(saved_amount_satangs=600000),
    )

    assert response.status_code == 201
    assert response.json()["amount_remaining_satangs"] == 0
    assert response.json()["progress_percent"] == 100
    assert response.json()["estimated_days"] == 0
    assert response.json()["estimated_date"] == date.today().isoformat()


def test_goal_create_read_update_delete(client):
    created = client.post("/api/savings-goals", json=goal_payload())
    goal_id = created.json()["id"]

    fetched = client.get(f"/api/savings-goals/{goal_id}")
    updated = client.put(
        f"/api/savings-goals/{goal_id}",
        json=goal_payload(name="กล้อง", target_amount_satangs=700000),
    )
    listed = client.get("/api/savings-goals")
    deleted = client.delete(f"/api/savings-goals/{goal_id}")

    assert fetched.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["name"] == "กล้อง"
    assert updated.json()["target_amount_satangs"] == 700000
    assert len(listed.json()) == 1
    assert deleted.status_code == 204
    assert client.get(f"/api/savings-goals/{goal_id}").status_code == 404


def test_goal_validation_rejects_invalid_or_extra_fields(client):
    blank_name = client.post("/api/savings-goals", json=goal_payload(name="   "))
    zero_target = client.post(
        "/api/savings-goals", json=goal_payload(target_amount_satangs=0)
    )
    negative_saved = client.post(
        "/api/savings-goals", json=goal_payload(saved_amount_satangs=-1)
    )
    extra_id = client.post("/api/savings-goals", json=goal_payload(id=999))

    assert blank_name.status_code == 422
    assert zero_target.status_code == 422
    assert negative_saved.status_code == 422
    assert extra_id.status_code == 422


def test_goal_name_is_returned_as_plain_text_data(client):
    marker = "<script>alert('x')</script>"
    response = client.post("/api/savings-goals", json=goal_payload(name=marker))

    assert response.status_code == 201
    assert response.json()["name"] == marker


def test_missing_goal_returns_not_found_for_read_update_and_delete(client):
    assert client.get("/api/savings-goals/999").status_code == 404
    assert client.put("/api/savings-goals/999", json=goal_payload()).status_code == 404
    assert client.delete("/api/savings-goals/999").status_code == 404
