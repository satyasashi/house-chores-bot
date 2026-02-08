import json
from datetime import date
from app import create_app
from app.extensions import db
from app.models import User, Chore, Debt, Absence


def upsert_user(name: str, phone: str):
    u = User.query.filter_by(name=name).first()
    if u:
        u.phone_e164 = phone
        u.is_active = True
        return u

    u = User(name=name, phone_e164=phone, is_active=True)
    db.session.add(u)
    return u


def upsert_chore(name: str, frequency_type: str, day_of_week: int, reminder_rules: list):
    c = Chore.query.filter_by(name=name).first()
    if c:
        c.frequency_type = frequency_type
        c.day_of_week = day_of_week
        c.reminder_rules_json = json.dumps(reminder_rules)
        return c

    c = Chore(
        name=name,
        frequency_type=frequency_type,
        day_of_week=day_of_week,
        reminder_rules_json=json.dumps(reminder_rules),
    )
    db.session.add(c)
    return c


def ensure_debts(users, chores):
    for u in users:
        for c in chores:
            existing = Debt.query.filter_by(user_id=u.id, chore_id=c.id).first()
            if not existing:
                db.session.add(Debt(user_id=u.id, chore_id=c.id, debt_count=0))


def upsert_absence(user_id: int, start: date, end: date, reason: str | None = None):
    existing = Absence.query.filter_by(
        user_id=user_id,
        start_date=start,
        end_date=end
    ).first()

    if existing:
        existing.reason = reason
        return existing

    a = Absence(
        user_id=user_id,
        start_date=start,
        end_date=end,
        reason=reason
    )
    db.session.add(a)
    return a



def main():
    app = create_app()
    with app.app_context():
        # ---------------- USERS ----------------
        # For testing: same phone number for everyone is OK
        # (since you removed unique=True)
        users = [
            upsert_user("Sashi", "+16476854531"),
            upsert_user("Raja", "+16476854531"),
            upsert_user("Guru", "+16476854531"),
            upsert_user("Naveen", "+16476854531"),
            upsert_user("Veenus", "+16476854531"),
        ]

        db.session.commit()

        # ---------------- CHORES ----------------
        chores = [
            # Garbage: weekly Friday
            upsert_chore(
                name="Garbage Cleanup",
                frequency_type="weekly",
                day_of_week=4,  # Friday
                reminder_rules=[
                    {"key": "monday", "dow": 0, "hour": 9},
                    {"key": "thursday", "dow": 3, "hour": 19},
                    {"key": "sunday", "dow": 6, "hour": 14}
                ],
            ),

            # Washroom: biweekly Sunday
            upsert_chore(
                name="Washroom Cleaning",
                frequency_type="biweekly",
                day_of_week=6,  # Sunday
                reminder_rules=[
                    {"key": "friday", "dow": 4, "hour": 10},
                ],
            ),

            # Kitchen: biweekly Sunday
            upsert_chore(
                name="Kitchen Cleaning",
                frequency_type="biweekly",
                day_of_week=6,  # Sunday
                reminder_rules=[
                    {"key": "friday", "dow": 4, "hour": 10},
                ],
            ),
        ]

        db.session.commit()

        # ---------------- DEBTS ----------------
        ensure_debts(users, chores)
        db.session.commit()

                # ---------------- ABSENCES (TEST DATA) ----------------
        # Example:
        # Alex away for 10 days (>= 7) => no debt increase if missed during that period
        # Satya away for 3 days (< 7)  => debt still increases if missed
        # name_to_user = {u.name: u for u in users}

        # upsert_absence(
        #     user_id=name_to_user["Raja"].id,
        #     start=date(2026, 2, 10),
        #     end=date(2026, 2, 19),
        #     reason="Out of country"
        # )

        # upsert_absence(
        #     user_id=name_to_user["Sashi"].id,
        #     start=date(2026, 2, 11),
        #     end=date(2026, 2, 13),
        #     reason="Short trip"
        # )

        # db.session.commit()


        print("✅ Seed complete.")
        print(f"Users: {len(users)}")
        print(f"Chores: {len(chores)}")


if __name__ == "__main__":
    main()
