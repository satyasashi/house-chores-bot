from datetime import date
from sqlalchemy import func
from app.models import Assignment, Debt, Absence, User, ChoreUserExclusion
from app.extensions import db


def get_or_create_debt(user_id: int, chore_id: int) -> Debt:
    debt = Debt.query.filter_by(user_id=user_id, chore_id=chore_id).first()
    if not debt:
        debt = Debt(user_id=user_id, chore_id=chore_id, debt_count=0)
        db.session.add(debt)
        db.session.commit()
    return debt


def user_is_away_more_than_week_on_date(user_id: int, check_date: date) -> bool:
    absences = Absence.query.filter_by(user_id=user_id).all()
    for a in absences:
        if a.start_date <= check_date <= a.end_date:
            duration_days = (a.end_date - a.start_date).days + 1
            return duration_days >= 7
    return False


def get_last_assignment_date(user_id: int, chore_id: int):
    last = (
        db.session.query(func.max(Assignment.week_start_date))
        .filter(Assignment.user_id == user_id, Assignment.chore_id == chore_id)
        .scalar()
    )
    return last


def pick_assignee_for_chore(chore_id: int, due_date: date, exclude_user_ids=None):
    """
    Fairness rules:
    1) Only active users
    2) Exclude users away > 1 week overlapping due_date
    3) Optionally exclude users already assigned this week
    4) Sort by:
        - highest debt_count for that chore
        - oldest last assignment date (rotation)
    """
    if exclude_user_ids is None:
        exclude_user_ids = set()

    users = User.query.filter_by(is_active=True).all()
    eligible = []

    for u in users:
        if u.id in exclude_user_ids:
            continue

        excluded = ChoreUserExclusion.query.filter_by(
            chore_id=chore_id,
            user_id=u.id
        ).first()
        if excluded:
            continue

        if user_is_away_more_than_week_on_date(u.id, due_date):
            continue

        debt = get_or_create_debt(u.id, chore_id)
        last_date = get_last_assignment_date(u.id, chore_id)

        eligible.append({
            "user": u,
            "debt": debt.debt_count,
            "last_date": last_date
        })

    if not eligible:
        return None

    def sort_key(x):
        last = x["last_date"]
        last_sort = last if last else date(1900, 1, 1)
        return (-x["debt"], last_sort)

    eligible.sort(key=sort_key)
    return eligible[0]["user"]
