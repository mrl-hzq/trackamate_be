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

class Expense(db.Model):
    __tablename__ = 'Expenses'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('Users.id'))
    category = db.Column(db.String(50))
    amount = db.Column(DECIMAL(10, 2))
    description = db.Column(db.Text)
    expense_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Income(db.Model):
    __tablename__ = 'Incomes'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('Users.id'))
    source = db.Column(db.String(50))
    amount = db.Column(DECIMAL(10, 2))
    income_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Meal(db.Model):
    __tablename__ = 'Meals'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('Users.id'))
    meal_type = db.Column(ENUM('breakfast', 'lunch', 'dinner', 'snack'))
    description = db.Column(db.Text)
    calories = db.Column(db.Integer)
    protein = db.Column(DECIMAL(5, 2))
    fat = db.Column(DECIMAL(5, 2))
    carbs = db.Column(DECIMAL(5, 2))
    meal_date = db.Column(db.Date)
    photo_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Goal(db.Model):
    __tablename__ = 'Goals'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('Users.id'))
    goal_type = db.Column(ENUM('savings', 'calories', 'custom'))
    target_value = db.Column(DECIMAL(10, 2))
    current_value = db.Column(DECIMAL(10, 2))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Reminder(db.Model):
    __tablename__ = 'Reminders'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('Users.id'))
    type = db.Column(ENUM('bill', 'meal', 'custom'))
    message = db.Column(db.Text)
    reminder_date = db.Column(db.Date)
    reminder_time = db.Column(db.Time)
    repeat_interval = db.Column(ENUM('none', 'daily', 'weekly', 'monthly'))
    is_done = db.Column(TINYINT(1), default=0)
    done_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Budget(db.Model):
    __tablename__ = 'Budgets'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('Users.id'))
    category = db.Column(db.String(50))
    limit_amount = db.Column(DECIMAL(10, 2))
    month_year = db.Column(db.String(7))  # Format: YYYY-MM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FoodExpense(db.Model):
    __tablename__ = 'food_expenses'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('Users.id'), nullable=False)  # match table name
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(DECIMAL(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship back to User
    user = db.relationship('User', backref=db.backref('food_expenses', lazy=True))

    def __repr__(self):
        return f"<FoodExpense {self.date} RM {self.amount}>"



