import csv
import sqlite3
import tempfile
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.database import get_db
from app.models import Transaction

router = APIRouter()


def _safe_spreadsheet_text(value: str | None) -> str:
    text = value or ""
    if text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


@router.get("/transactions.csv")
def export_transactions_csv(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")

    statement = select(Transaction)
    if start_date:
        statement = statement.where(Transaction.date >= start_date)
    if end_date:
        statement = statement.where(Transaction.date <= end_date)
    statement = statement.order_by(Transaction.date.desc(), Transaction.id.desc())
    transactions = db.scalars(statement).all()

    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["วันที่", "ประเภท", "จำนวนเงิน (บาท)", "หมวดหมู่", "หมายเหตุ", "สร้างเมื่อ"])
    for item in transactions:
        amount_baht = Decimal(item.amount_satangs) / Decimal(100)
        writer.writerow(
            [
                item.date.isoformat(),
                "รายรับ" if item.type == "income" else "รายจ่าย",
                format(amount_baht, ".2f"),
                _safe_spreadsheet_text(item.category),
                _safe_spreadsheet_text(item.note),
                item.created_at.isoformat(),
            ]
        )

    filename = f"transactions_{date.today():%Y%m%d}.csv"
    content = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


def _remove_backup(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


@router.get("/sqlite-backup")
def download_sqlite_backup(db: Session = Depends(get_db)):
    if db.get_bind().dialect.name != "sqlite":
        raise HTTPException(status_code=501, detail="SQLite backup is available only for SQLite")

    with tempfile.NamedTemporaryFile(
        prefix="money-backup-", suffix=".sqlite3", delete=False
    ) as file:
        backup_path = file.name

    try:
        source = db.connection().connection.driver_connection
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
    except (AttributeError, sqlite3.Error) as error:
        _remove_backup(backup_path)
        raise HTTPException(status_code=500, detail="Could not create database backup") from error

    filename = f"money_backup_{datetime.now():%Y%m%d_%H%M%S}.sqlite3"
    return FileResponse(
        backup_path,
        media_type="application/vnd.sqlite3",
        filename=filename,
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(_remove_backup, backup_path),
    )
