import uuid
from datetime import datetime
from sqlalchemy.dialects.mysql import ENUM, DECIMAL, TINYINT
from app import db

def generate_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenses = db.relationship('Expense', backref='user', lazy=True)
    incomes = db.relationship('Income', backref='user', lazy=True)
    meals = db.relationship('Meal', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)
    reminders = db.relationship('Reminder', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)