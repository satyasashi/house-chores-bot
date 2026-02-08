from datetime import datetime, date
from flask_login import UserMixin
from app.extensions import db, login_manager


class AdminUser(UserMixin):
    """
    We are NOT storing admin in DB.
    Flask-Login still needs a user object.
    """
    def __init__(self, id="admin"):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    if user_id == "admin":
        return AdminUser()
    return None


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone_e164 = db.Column(db.String(32), nullable=False, unique=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Chore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)

    # weekly or biweekly
    frequency_type = db.Column(db.String(20), nullable=False)

    # 0=Monday ... 6=Sunday
    day_of_week = db.Column(db.Integer, nullable=False)

    # JSON string: reminder rules
    reminder_rules_json = db.Column(db.Text, nullable=False, default="[]")

    created_at = db.Column(db.DateTime, default=datetime.now)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    chore_id = db.Column(db.Integer, db.ForeignKey("chore.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    week_start_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    previous_user_ids_json = db.Column(db.Text, nullable=False, default="[]")

    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    chore = db.relationship("Chore")
    user = db.relationship("User")


class Debt(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chore_id = db.Column(db.Integer, db.ForeignKey("chore.id"), nullable=False)

    debt_count = db.Column(db.Integer, default=0, nullable=False)

    user = db.relationship("User")
    chore = db.relationship("Chore")

    __table_args__ = (
        db.UniqueConstraint("user_id", "chore_id", name="uq_user_chore_debt"),
    )


class Absence(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    reason = db.Column(db.String(255), nullable=True)

    user = db.relationship("User")


class ReminderLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    assignment_id = db.Column(db.Integer, db.ForeignKey("assignment.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)

    # monday / thursday / etc
    reminder_key = db.Column(db.String(50), nullable=False)

    assignment = db.relationship("Assignment")

    __table_args__ = (
        db.UniqueConstraint("assignment_id", "reminder_key", name="uq_assignment_reminder"),
    )


class ChoreUserExclusion(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    chore_id = db.Column(db.Integer, db.ForeignKey("chore.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    chore = db.relationship("Chore")
    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("chore_id", "user_id", name="uq_chore_user_exclusion"),
    )
