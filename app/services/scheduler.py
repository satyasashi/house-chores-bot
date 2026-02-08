from datetime import date, timedelta
from app.extensions import db
from app.models import Chore, Assignment
from app.services.fairness import pick_assignee_for_chore


def get_week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def should_generate_for_week(chore: Chore, week_start: date) -> bool:
    if chore.frequency_type == "weekly":
        return True

    if chore.frequency_type == "biweekly":
        # Biweekly rule:
        # We'll anchor based on a fixed Monday reference.
        # Example: 2026-02-02 is a Monday (your current week)
        reference = date(2026, 2, 2)
        diff_weeks = (week_start - reference).days // 7
        return diff_weeks % 2 == 0

    return False


def due_date_for_week(chore: Chore, week_start: date) -> date:
    # day_of_week: 0=Mon ... 6=Sun
    return week_start + timedelta(days=chore.day_of_week)


def generate_weekly_assignments(today: date | None = None):
    """
    Creates assignments for current week.
    Safe to run multiple times (won't duplicate).
    """
    if not today:
        today = date.today()

    week_start = get_week_start(today)
    chores = Chore.query.all()

    created = []
    already_assigned_user_ids = set()

    for chore in chores:
        if not should_generate_for_week(chore, week_start):
            continue

        due_date = due_date_for_week(chore, week_start)

        existing = Assignment.query.filter_by(
            chore_id=chore.id,
            week_start_date=week_start
        ).first()
        if existing:
            already_assigned_user_ids.add(existing.user_id)
            continue

        # 1) First try: avoid assigning someone already assigned this week
        assignee = pick_assignee_for_chore(
            chore.id,
            due_date,
            exclude_user_ids=already_assigned_user_ids
        )

        # 2) Fallback: if not possible, allow duplicates
        if not assignee:
            assignee = pick_assignee_for_chore(chore.id, due_date, exclude_user_ids=set())

        if not assignee:
            continue

        assignment = Assignment(
            chore_id=chore.id,
            user_id=assignee.id,
            week_start_date=week_start,
            due_date=due_date,
            status="pending"
        )

        db.session.add(assignment)
        created.append(assignment)
        already_assigned_user_ids.add(assignee.id)

    db.session.commit()
    return created