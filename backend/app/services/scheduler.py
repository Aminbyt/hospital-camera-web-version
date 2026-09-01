"""Background jobs - ported from heartbeat_worker.py / send_daily_reports.py.

Same behaviour (hourly heartbeat ping, a daily master-summary bot message,
a monthly Excel rollup sent to the bot), just driven by APScheduler against
the SQLite `events` table instead of scanning the LOGS folder for Excel
files that may or may not exist.
"""
import io
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import Event
from app.services import settings_store as cfg

scheduler = BackgroundScheduler()


def send_heartbeat():
    bot_api_url = cfg.get("bot_api_url")
    bot_chat_id = cfg.get("bot_chat_id")
    if not bot_api_url or not bot_chat_id:
        return
    try:
        requests.post(bot_api_url, json={"chat_id": bot_chat_id, "text": "System heartbeat: ACTIVE"},
                      timeout=cfg.get("bot_timeout", 3))
        logging.info("[HEARTBEAT] Sent heartbeat message.")
    except Exception as e:
        logging.error(f"[HEARTBEAT ERROR] {e}")


def send_daily_summary():
    bot_api_url = cfg.get("bot_api_url")
    bot_chat_id = cfg.get("bot_chat_id")
    if not bot_api_url or not bot_chat_id:
        return

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        rows = db.query(Event).filter(Event.date == yesterday).all()
    finally:
        db.close()

    if not rows:
        return

    total = len(rows)
    compliant = sum(1 for r in rows if r.washing_complete == "YES" and r.mask == "YES" and r.hat == "YES")
    message = (
        f"Daily Hygiene Summary for {yesterday}\n"
        f"Total visits: {total}\n"
        f"Fully compliant: {compliant}\n"
        f"Non-compliant: {total - compliant}"
    )
    try:
        requests.post(bot_api_url, json={"chat_id": bot_chat_id, "text": message},
                      timeout=cfg.get("bot_timeout", 3))
        logging.info("[REPORTS] Sent daily summary.")
    except Exception as e:
        logging.error(f"[REPORTS ERROR] {e}")


def send_monthly_report():
    bot_api_url = cfg.get("bot_api_url")
    bot_chat_id = cfg.get("bot_chat_id")
    if not bot_api_url or not bot_chat_id:
        return

    last_month_date = datetime.now().replace(day=1) - timedelta(days=1)
    target_month_str = last_month_date.strftime("%Y-%m")

    db = SessionLocal()
    try:
        rows = db.query(Event).filter(Event.date.like(f"{target_month_str}%")).all()
    finally:
        db.close()

    if not rows:
        return

    df = pd.DataFrame([{
        "Date": r.date, "Time": r.time, "Sink": r.camera_name,
        "First Name": r.first_name, "Last Name": r.last_name, "Role": r.role,
        "Mask": r.mask, "Hat": r.hat, "Washing Complete": r.washing_complete,
        "Wash Duration (s)": r.wash_duration, "All WHO Steps": r.all_who_steps,
    } for r in rows])

    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)

    try:
        base_url = bot_api_url.replace("sendMessage", "sendDocument")
        files = {"document": (f"Monthly_Report_{target_month_str}.xlsx", buf)}
        data = {"chat_id": bot_chat_id, "caption": f"Monthly Handwashing Report for {target_month_str}"}
        requests.post(base_url, data=data, files=files, timeout=60)
        logging.info("[REPORTS] Sent monthly report.")
    except Exception as e:
        logging.error(f"[REPORTS ERROR] Monthly report failed: {e}")


def start_scheduler():
    scheduler.add_job(send_heartbeat, "interval", hours=1, id="heartbeat", replace_existing=True)
    scheduler.add_job(send_daily_summary, "cron", hour=8, minute=0, id="daily_summary", replace_existing=True)
    scheduler.add_job(send_monthly_report, "cron", day=1, hour=8, minute=0, id="monthly_report", replace_existing=True)
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)
