import json
from datetime import date, timedelta
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import User, Chore, Assignment, Debt, Absence, ReminderLog, ChoreUserExclusion
from app.services.fairness import (
    get_or_create_debt,
    user_is_away_more_than_week_on_date,
    pick_assignee_for_chore
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# @admin_bp.get("/")
# @login_required
# def dashboard():
#     today = date.today()
#     week_start = today - timedelta(days=today.weekday())

#     assignments = (
#         Assignment.query
#         .filter(Assignment.week_start_date == week_start)
#         .order_by(Assignment.due_date.asc())
#         .all()
#     )

#     return render_template("admin/dashboard.html", assignments=assignments, week_start=week_start)

@admin_bp.get("/")
@login_required
def dashboard():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    assignments = (
        Assignment.query
        .filter(Assignment.week_start_date == week_start)
        .order_by(Assignment.due_date.asc())
        .all()
    )

    # Week counts
    pending_count = sum(1 for a in assignments if a.status == "pending")
    done_count = sum(1 for a in assignments if a.status == "done")
    missed_count = sum(1 for a in assignments if a.status == "missed")
    reassigned_count = sum(1 for a in assignments if a.status == "reassigned")

    # Reminders sent this week
    reminders_sent = (
        ReminderLog.query
        .join(Assignment, ReminderLog.assignment_id == Assignment.id)
        .filter(Assignment.week_start_date == week_start)
        .count()
    )

    # Debt leaderboard
    users = User.query.filter_by(is_active=True).all()
    chores = Chore.query.all()

    debt_rows = []
    for u in users:
        row = {"user": u.name, "total": 0, "per_chore": {}}
        for c in chores:
            d = Debt.query.filter_by(user_id=u.id, chore_id=c.id).first()
            count = d.debt_count if d else 0
            row["per_chore"][c.name] = count
            row["total"] += count
        debt_rows.append(row)

    debt_rows.sort(key=lambda x: x["total"], reverse=True)

    # Monthly stats (simple)
    month_start = date(today.year, today.month, 1)

    completed_this_month = (
        db.session.query(User.name, func.count(Assignment.id))
        .join(Assignment, Assignment.user_id == User.id)
        .filter(Assignment.status == "done")
        .filter(Assignment.due_date >= month_start)
        .group_by(User.name)
        .all()
    )

    missed_this_month = (
        db.session.query(User.name, func.count(Assignment.id))
        .join(Assignment, Assignment.user_id == User.id)
        .filter(Assignment.status == "missed")
        .filter(Assignment.due_date >= month_start)
        .group_by(User.name)
        .all()
    )

    completed_map = {name: count for name, count in completed_this_month}
    missed_map = {name: count for name, count in missed_this_month}

    monthly_rows = []
    for u in users:
        monthly_rows.append({
            "user": u.name,
            "done": completed_map.get(u.name, 0),
            "missed": missed_map.get(u.name, 0),
        })

    monthly_rows.sort(key=lambda x: x["done"], reverse=True)

    return render_template(
        "admin/dashboard.html",
        week_start=week_start,
        assignments=assignments,
        pending_count=pending_count,
        done_count=done_count,
        missed_count=missed_count,
        reassigned_count=reassigned_count,
        reminders_sent=reminders_sent,
        debt_rows=debt_rows,
        chores=chores,
        monthly_rows=monthly_rows,
        month_start=month_start
    )


# ---------------- USERS ----------------

@admin_bp.get("/users")
@login_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_bp.post("/users/create")
@login_required
def users_create():
    name = request.form["name"].strip()
    phone = request.form["phone_e164"].strip()

    if not phone.startswith("+"):
        flash("Phone must be E.164 format, like +1647...")
        return redirect(url_for("admin.users"))

    user = User(name=name, phone_e164=phone)
    db.session.add(user)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Phone already exists.")
        return redirect(url_for("admin.users"))

    # create debts for all chores (optional later)
    flash("User created.")
    return redirect(url_for("admin.users"))


@admin_bp.post("/users/<int:user_id>/toggle")
@login_required
def users_toggle(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return redirect(url_for("admin.users"))


# ---------------- CHORES ----------------

@admin_bp.get("/chores")
@login_required
def chores():
    chores = Chore.query.order_by(Chore.created_at.desc()).all()
    return render_template("admin/chores.html", chores=chores)


@admin_bp.post("/chores/create")
@login_required
def chores_create():
    name = request.form["name"].strip()
    frequency_type = request.form["frequency_type"]
    day_of_week = int(request.form["day_of_week"])

    # default reminder rules
    reminder_rules = request.form.get("reminder_rules_json", "").strip()
    if not reminder_rules:
        reminder_rules = "[]"

    try:
        json.loads(reminder_rules)
    except Exception:
        flash("Reminder rules must be valid JSON.")
        return redirect(url_for("admin.chores"))

    chore = Chore(
        name=name,
        frequency_type=frequency_type,
        day_of_week=day_of_week,
        reminder_rules_json=reminder_rules
    )
    db.session.add(chore)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Chore name already exists.")
        return redirect(url_for("admin.chores"))

    flash("Chore created.")
    return redirect(url_for("admin.chores"))


# ---------------- ASSIGNMENTS ----------------

@admin_bp.get("/assignments")
@login_required
def assignments():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    assignments = (
        Assignment.query
        .filter(Assignment.week_start_date == week_start)
        .order_by(Assignment.due_date.asc())
        .all()
    )

    users = User.query.filter_by(is_active=True).all()
    chores = Chore.query.all()

    return render_template(
        "admin/assignments.html",
        assignments=assignments,
        users=users,
        chores=chores,
        week_start=week_start
    )


@admin_bp.post("/assignments/<int:assignment_id>/done")
@login_required
def assignment_done(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)

    if a.status != "done":
        a.status = "done"
        a.completed_at = datetime.now()

        # Reduce debt if any
        debt = get_or_create_debt(a.user_id, a.chore_id)
        if debt.debt_count > 0:
            debt.debt_count -= 1

        db.session.commit()

    return redirect(url_for("admin.assignments"))


@admin_bp.post("/assignments/<int:assignment_id>/missed")
@login_required
def assignment_missed(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)

    if a.status != "missed":
        a.status = "missed"
        a.completed_at = None

        # Debt increases ONLY if not away > 1 week
        if not user_is_away_more_than_week_on_date(a.user_id, a.due_date):
            debt = get_or_create_debt(a.user_id, a.chore_id)
            debt.debt_count += 1

        db.session.commit()

    return redirect(url_for("admin.assignments"))


@admin_bp.post("/assignments/<int:assignment_id>/reassign")
@login_required
def assignment_reassign(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)

    # Track history
    prev_ids = set(json.loads(a.previous_user_ids_json or "[]"))
    prev_ids.add(a.user_id)  # current user becomes part of history

    # Who already has a chore this week
    week_assignments = Assignment.query.filter_by(week_start_date=a.week_start_date).all()
    already_assigned = {x.user_id for x in week_assignments}

    # --- Phase 1: avoid duplicates + avoid history ---
    exclude_ids = already_assigned.union(prev_ids)

    new_user = pick_assignee_for_chore(
        a.chore_id,
        a.due_date,
        exclude_user_ids=exclude_ids
    )

    # --- Phase 2 fallback: allow duplicates, but still avoid history ---
    if not new_user:
        new_user = pick_assignee_for_chore(
            a.chore_id,
            a.due_date,
            exclude_user_ids=prev_ids
        )

    if not new_user:
        flash("No eligible user found to reassign (everyone already tried).")
        return redirect(url_for("admin.assignments"))

    # Save new assignment
    a.previous_user_ids_json = json.dumps(sorted(list(prev_ids)))
    a.user_id = new_user.id
    a.status = "reassigned"
    db.session.commit()

    flash(f"Reassigned to {new_user.name}.")
    return redirect(url_for("admin.assignments"))


# ---------------- DEBTS ----------------

@admin_bp.get("/debts")
@login_required
def debts():
    users = User.query.order_by(User.name.asc()).all()
    chores = Chore.query.order_by(Chore.name.asc()).all()

    # Build matrix for display
    debt_map = {}
    for u in users:
        for c in chores:
            debt = Debt.query.filter_by(user_id=u.id, chore_id=c.id).first()
            if not debt:
                debt = Debt(user_id=u.id, chore_id=c.id, debt_count=0)
                db.session.add(debt)
                db.session.commit()
            debt_map[(u.id, c.id)] = debt.debt_count

    return render_template(
        "admin/debts.html",
        users=users,
        chores=chores,
        debt_map=debt_map
    )


# ---------------- ABSENCES ----------------

@admin_bp.get("/absences")
@login_required
def absences():
    absences = (
        Absence.query
        .order_by(Absence.start_date.desc())
        .all()
    )
    users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    return render_template(
        "admin/absences.html",
        absences=absences,
        users=users
    )


@admin_bp.post("/absences/create")
@login_required
def absences_create():
    user_id = int(request.form["user_id"])
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]
    reason = request.form.get("reason", "").strip() or None

    a = Absence(
        user_id=user_id,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        reason=reason
    )
    db.session.add(a)
    db.session.commit()

    flash("Absence added.")
    return redirect(url_for("admin.absences"))


@admin_bp.post("/absences/<int:absence_id>/delete")
@login_required
def absences_delete(absence_id):
    a = Absence.query.get_or_404(absence_id)
    db.session.delete(a)
    db.session.commit()
    flash("Absence deleted.")
    return redirect(url_for("admin.absences"))


# ---------------- REMINDER LOGS ----------------

@admin_bp.get("/reminder-logs")
@login_required
def reminder_logs():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    logs = (
        ReminderLog.query
        .join(Assignment, ReminderLog.assignment_id == Assignment.id)
        .filter(Assignment.week_start_date == week_start)
        .order_by(ReminderLog.sent_at.desc())
        .all()
    )

    return render_template(
        "admin/reminder_logs.html",
        logs=logs,
        week_start=week_start
    )

# ---------------- CHORE EXCLUSIONS ----------------

@admin_bp.get("/chore-exclusions")
@login_required
def chore_exclusions():
    exclusions = (
        ChoreUserExclusion.query
        .order_by(ChoreUserExclusion.id.desc())
        .all()
    )

    users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    chores = Chore.query.order_by(Chore.name.asc()).all()

    return render_template(
        "admin/chore_exclusions.html",
        exclusions=exclusions,
        users=users,
        chores=chores
    )


@admin_bp.post("/chore-exclusions/create")
@login_required
def chore_exclusions_create():
    chore_id = int(request.form["chore_id"])
    user_id = int(request.form["user_id"])

    existing = ChoreUserExclusion.query.filter_by(chore_id=chore_id, user_id=user_id).first()
    if existing:
        flash("Exclusion already exists.")
        return redirect(url_for("admin.chore_exclusions"))

    db.session.add(ChoreUserExclusion(chore_id=chore_id, user_id=user_id))
    db.session.commit()

    flash("Exclusion added.")
    return redirect(url_for("admin.chore_exclusions"))


@admin_bp.post("/chore-exclusions/<int:exclusion_id>/delete")
@login_required
def chore_exclusions_delete(exclusion_id):
    e = ChoreUserExclusion.query.get_or_404(exclusion_id)
    db.session.delete(e)
    db.session.commit()
    flash("Exclusion removed.")
    return redirect(url_for("admin.chore_exclusions"))
