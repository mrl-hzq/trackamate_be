import uuid
from datetime import datetime
from sqlalchemy import (Column, String, Integer, DECIMAL, Text, Date, DateTime, Time, Enum, ForeignKey)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from app import db

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    __tablename__ = 'Users'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    incomes = relationship('Income', backref='user', lazy=True, cascade="all, delete-orphan")
    meals = relationship('Meal', backref='user', lazy=True, cascade="all, delete-orphan")
    goals = relationship('Goal', backref='user', lazy=True, cascade="all, delete-orphan")
    reminders = relationship('Reminder', backref='user', lazy=True, cascade="all, delete-orphan")


class Income(db.Model):
    __tablename__ = 'Incomes'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    source = Column(String(50))
    amount = Column(DECIMAL(10, 2))
    photo_url = Column(Text)
    burn_pool = Column(Integer)
    daily_limit_food = Column(Integer)
    daily_supply_food = Column(Integer)
    daily_limit_burn = Column(Integer)
    daily_supply_burn = Column(Integer)
    income_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    burns = relationship('Burn', backref='income', lazy=True, cascade="all, delete-orphan")
    invests = relationship('Invest', backref='income', lazy=True, cascade="all, delete-orphan")
    commitments = relationship('Commitment', backref='income', lazy=True, cascade="all, delete-orphan")
    food_expenses = relationship('FoodExpense', backref='income', lazy=True, cascade="all, delete-orphan")


class Burn(db.Model):
    __tablename__ = 'Burn'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    income_id = Column(String(36), ForeignKey('Incomes.id'), nullable=False)
    category = Column(Enum('Stupid', 'Health', 'Therapeutic', 'Tech'))
    amount = Column(DECIMAL(10, 2))
    description = Column(Text)
    photo_url = Column(Text)
    burn_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)


class Invest(db.Model):
    __tablename__ = 'Invest'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    income_id = Column(String(36), ForeignKey('Incomes.id'), nullable=False)
    category = Column(Enum('High Risks', 'Med Risks', 'Low Risks'))
    amount = Column(DECIMAL(10, 2))
    description = Column(Text)
    is_done = Column(TINYINT(1), default=0)
    is_recurring = Column(TINYINT(1), default=0)
    photo_url = Column(Text)
    invest_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)


class Commitment(db.Model):
    __tablename__ = 'Commitment'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    income_id = Column(String(36), ForeignKey('Incomes.id'), nullable=False)
    amount = Column(DECIMAL(10, 2))
    description = Column(Text)
    is_done = Column(TINYINT(1), default=0)
    is_recurring = Column(TINYINT(1), default=0)
    photo_url = Column(Text)
    commit_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)


class FoodExpense(db.Model):
    __tablename__ = 'FoodExpenses'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    meals_id = Column(String(36), ForeignKey('Meals.id'), nullable=False)
    income_id = Column(String(36), ForeignKey('Incomes.id'), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


class Meal(db.Model):
    __tablename__ = 'Meals'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    meal_type = Column(Enum('breakfast', 'lunch', 'dinner', 'snack'))
    description = Column(Text)
    calories = Column(Integer)
    protein = Column(DECIMAL(5, 2))
    fat = Column(DECIMAL(5, 2))
    carbs = Column(DECIMAL(5, 2))
    meal_date = Column(Date)
    photo_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    food_expenses = relationship('FoodExpense', backref='meal', lazy=True, cascade="all, delete-orphan")


class Goal(db.Model):
    __tablename__ = 'Goals'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    goal_type = Column(Enum('savings', 'calories', 'custom'))
    target_value = Column(DECIMAL(10, 2))
    current_value = Column(DECIMAL(10, 2))
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Reminder(db.Model):
    __tablename__ = 'Reminders'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    type = Column(Enum('bill', 'meal', 'custom'))
    message = Column(Text)
    reminder_date = Column(Date)
    reminder_time = Column(Time)
    repeat_interval = Column(Enum('none', 'daily', 'weekly', 'monthly'))
    is_done = Column(TINYINT(1), default=0)
    done_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)



