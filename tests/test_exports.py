import csv
import io
import sqlite3
from datetime import date, timedelta


def transaction_payload(kind, amount, when, category, note):
    return {
        "type": kind,
        "amount_satangs": amount,
        "date": when,
        "category": category,
        "note": note,
    }


def test_csv_export_uses_excel_friendly_utf8_and_escapes_formula_cells(client):
    client.post(
        "/api/transactions",
        json=transaction_payload(
            "expense",
            12345,
            date.today().isoformat(),
            "@SUM(1,1)",
            "=HYPERLINK('https://example.com')",
        ),
    )

    response = client.get("/api/exports/transactions.csv")

    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"transactions_" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert rows[1][2] == "123.45"
    assert rows[1][3] == "'@SUM(1,1)"
    assert rows[1][4].startswith("'=HYPERLINK")


def test_csv_export_date_filters_and_invalid_range(client):
    today = date.today()
    earlier = today - timedelta(days=2)
    client.post(
        "/api/transactions",
        json=transaction_payload("income", 50000, earlier.isoformat(), "งาน", "ก่อนหน้า"),
    )
    client.post(
        "/api/transactions",
        json=transaction_payload("expense", 10000, today.isoformat(), "อาหาร", "วันนี้"),
    )

    filtered = client.get(
        "/api/exports/transactions.csv",
        params={"start_date": today.isoformat(), "end_date": today.isoformat()},
    )
    invalid = client.get(
        "/api/exports/transactions.csv",
        params={"start_date": today.isoformat(), "end_date": earlier.isoformat()},
    )

    rows = list(csv.reader(io.StringIO(filtered.content.decode("utf-8-sig"))))
    assert filtered.status_code == 200
    assert len(rows) == 2
    assert rows[1][0] == today.isoformat()
    assert invalid.status_code == 422


def test_sqlite_backup_download_is_a_valid_full_database(client, tmp_path):
    client.post(
        "/api/transactions",
        json=transaction_payload("income", 50000, date.today().isoformat(), "งาน", "สำรองนี้"),
    )

    response = client.get("/api/exports/sqlite-backup")

    assert response.status_code == 200
    assert response.content.startswith(b"SQLite format 3\x00")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].endswith(".sqlite3\"")

    backup_path = tmp_path / "download.sqlite3"
    backup_path.write_bytes(response.content)
    with sqlite3.connect(backup_path) as backup:
        result = backup.execute(
            "SELECT amount_satangs, note FROM transactions WHERE note = ?", ("สำรองนี้",)
        ).fetchone()
        integrity = backup.execute("PRAGMA integrity_check").fetchone()[0]

    assert result == (50000, "สำรองนี้")
    assert integrity == "ok"
