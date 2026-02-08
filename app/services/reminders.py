import json
from datetime import datetime, date, timedelta
from app.extensions import db
from app.models import Assignment, ReminderLog
from app.services.twilio_client import send_whatsapp_message
from app.services.garbage_cycle import garbage_bins_text


def get_week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def should_send_for_rule(rule: dict, now: datetime) -> bool:
    # rule: {"key":"monday","dow":0,"hour":9}
    return now.weekday() == int(rule["dow"]) and now.hour == int(rule["hour"])


def build_message(assignment: Assignment, rule_key: str) -> str:
    chore = assignment.chore.name
    user = assignment.user.name
    due = assignment.due_date

    if "Garbage" in chore:
        bins = garbage_bins_text(due)

        if rule_key == "thursday":
            return (
                f"🚨 HIGH ALERT: \n\n Hey {user}, it's your turn for {chore}.\n"
                f"Bins: {bins}\n\n"
                f"Tonight:\n"
                f"- Keep in-house garbage clear\n"
                f"- Place bins near the curb\n\n"
                f"Pickup: {due} (Friday morning)\n\n Thanks!"
            )

        return (
            f"🗑️ Reminder: \n\n Hey {user}, you are assigned: {chore}.\n\n"
            f"Bins: {bins}\n\n"
            f"This week:\n"
            f"- If in-house bins are full, empty them into outside containers\n\n"
            f"Pickup: {due} (Friday morning)\n\n Thanks!"
        )

    # default for other chores
    if "Washroom" in chore:
        return (
            f"🧼 Reminder: \n\n Hey {user}, it's your turn for: {chore}.\n\n"
            f"Due date: {due}\n\n"
            f"Please focus on:\n"
            f"- Toilet, sink, and shower\n"
            f"- Replace shower curtain if needed\n"
            f"- Mop the floor\n\n"
            f"Drop a message in '44 Perivale Cres' group chat with:\n"
            f"- Done (✅)\n"
            f"- Skip (❌)\n"
            f"- Reassign (⏰)\n\nThanks!"
        )
    # Kitchen or other chores
    return (
        f"🧹 Reminder: \n\n Hey {user}, it's your turn for: {chore}\n\n"
        f"Please focus on:\n"
        f"- Sink\n"
        f"- Kitchen Countertop\n"
        f"- Kitchen Stove\n"
        f"- Mop the floor\n\n"
        f"Drop a message in '44 Perivale Cres' group chat with:\n"
        f"- Done (✅)\n"
        f"- Skip (❌)\n"
        f"- Reassign (⏰)\n\nThanks!"
    )


def send_due_reminders(now: datetime | None = None, force: bool = False):
    if not now:
        now = datetime.now()

    week_start = get_week_start(now.date())

    assignments = (
        Assignment.query
        .filter(Assignment.week_start_date == week_start)
        .filter(Assignment.status == "pending")
        .all()
    )

    sent_count = 0

    for a in assignments:
        rules = json.loads(a.chore.reminder_rules_json)

        for rule in rules:
            if not force and not should_send_for_rule(rule, now):
                continue

            reminder_key = rule["key"]

            # prevent duplicates
            already_sent = ReminderLog.query.filter_by(
                assignment_id=a.id,
                reminder_key=reminder_key
            ).first()

            if already_sent:
                continue

            msg = build_message(a, reminder_key)
            send_whatsapp_message(a.user.phone_e164, msg)

            db.session.add(ReminderLog(
                assignment_id=a.id,
                reminder_key=reminder_key
            ))
            db.session.commit()

            sent_count += 1

    return sent_count
