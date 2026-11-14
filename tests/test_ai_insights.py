import json
from datetime import date
from types import SimpleNamespace


def transaction_payload(kind, amount, category, note):
    return {
        "type": kind,
        "amount_satangs": amount,
        "date": date.today().isoformat(),
        "category": category,
        "note": note,
    }


def test_ai_status_does_not_expose_api_key(client, monkeypatch):
    monkeypatch.setattr("app.services.ai_insights.load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    response = client.get("/api/ai/status")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "model": "test-model"}
    assert "api_key" not in response.json()


def test_ai_insights_are_disabled_without_a_key(client, monkeypatch):
    monkeypatch.setattr("app.services.ai_insights.load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post("/api/ai/insights", json={})

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_ai_receives_only_approved_aggregate_metrics(client, monkeypatch):
    import app.services.ai_insights as ai_service

    call = {}

    class FakeResponses:
        def create(self, **kwargs):
            call.update(kwargs)
            return SimpleNamespace(output_text="• ตัวเลขนี้เป็นเพียงประมาณการจากข้อมูลย้อนหลัง")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            call["client_options"] = kwargs
            self.responses = FakeResponses()

    today = date.today().isoformat()
    income = client.post(
        "/api/transactions",
        json=transaction_payload("income", 500000, "PRIVATE_CATEGORY_928", "PRIVATE_NOTE_132"),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 100000, "PRIVATE_CATEGORY_827", "PRIVATE_NOTE_231"),
    )
    goal = client.post(
        "/api/savings-goals",
        json={
            "name": "PRIVATE_GOAL_736",
            "target_amount_satangs": 900000,
            "saved_amount_satangs": 200000,
            "note": "PRIVATE_GOAL_NOTE_634",
        },
    )
    assert income.status_code == 201
    assert goal.status_code == 201

    monkeypatch.setattr(ai_service, "load_dotenv", lambda: None)
    monkeypatch.setattr(ai_service, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-sent")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    response = client.post(
        "/api/ai/insights",
        json={"start_date": today, "end_date": today, "goal_id": goal.json()["id"]},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert call["store"] is False
    assert call["max_output_tokens"] == 250
    assert call["client_options"]["timeout"] == 20.0
    sent_input = call["input"]
    assert "PRIVATE_CATEGORY_928" not in sent_input
    assert "PRIVATE_CATEGORY_827" not in sent_input
    assert "PRIVATE_NOTE_132" not in sent_input
    assert "PRIVATE_NOTE_231" not in sent_input
    assert "PRIVATE_GOAL_736" not in sent_input
    assert "PRIVATE_GOAL_NOTE_634" not in sent_input
    metrics = json.loads(sent_input)
    assert metrics["income_satangs"] == 500000
    assert metrics["expense_satangs"] == 100000
    assert metrics["savings_goal"]["target_amount_satangs"] == 900000
    assert metrics["savings_goal"]["amount_remaining_satangs"] == 700000


def test_ai_does_not_call_provider_for_unknown_goal(client, monkeypatch):
    import app.services.ai_insights as ai_service

    monkeypatch.setattr(ai_service, "load_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        ai_service,
        "OpenAI",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )

    response = client.post("/api/ai/insights", json={"goal_id": 999})

    assert response.status_code == 404
