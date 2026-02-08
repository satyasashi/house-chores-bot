from flask import Blueprint, request, abort, jsonify
from datetime import date, datetime

from app.config import Config
from app.services.scheduler import generate_weekly_assignments
from app.services.reminders import send_due_reminders


cron_bp = Blueprint("cron", __name__, url_prefix="/cron")


def require_cron_secret():
    secret = request.headers.get("X-CRON-SECRET")
    if not secret or secret != Config.CRON_SECRET:
        abort(401)


@cron_bp.post("/ping")
def ping():
    require_cron_secret()
    return jsonify({"ok": True})


@cron_bp.post("/generate-weekly-assignments")
def cron_generate_weekly_assignments():
    require_cron_secret()
    created = generate_weekly_assignments(today=date.today())
    return jsonify({
        "created_count": len(created),
        "created": [
            {"id": a.id, "chore": a.chore.name, "user": a.user.name, "due": str(a.due_date)}
            for a in created
        ]
    })

@cron_bp.post("/send-reminders")
def cron_send_reminders():
    require_cron_secret()
    # sent = send_due_reminders(now=datetime.now())
    sent = send_due_reminders(now=datetime.now())
    return jsonify({"sent_count": sent})


@cron_bp.post("/send-reminders-force")
def cron_send_reminders_force():
    require_cron_secret()
    sent = send_due_reminders(now=datetime.now(), force=True)
    return jsonify({"sent_count": sent, "forced": True})
