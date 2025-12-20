import uuid
from datetime import datetime
from sqlalchemy import (Column, String, Integer, DECIMAL, Text, Date, DateTime, Time, Enum, ForeignKey, Boolean)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from app import db

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    __tablename__ = 'Users'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    daily_limit_food = Column(Integer)
    daily_supply_food = Column(Integer)
    daily_limit_burn = Column(Integer)
    daily_supply_burn = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    incomes = relationship('Income', backref='user', lazy=True, cascade="all, delete-orphan")
    goals = relationship('Goal', backref='user', lazy=True, cascade="all, delete-orphan")
    notes = relationship('Note', backref='user', lazy=True, cascade="all, delete-orphan")
    weight_entries = relationship('WeightEntry', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    weight_goal = relationship('WeightGoal', backref='user', uselist=False, cascade="all, delete-orphan")
    nutrition_reviews = relationship('NutritionReview', backref='user', lazy='dynamic', cascade="all, delete-orphan")


class Income(db.Model):
    __tablename__ = 'incomes'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    source = Column(String(50))
    amount = Column(DECIMAL(10, 2))
    photo_url = Column(Text)
    burn_pool = Column(Integer)
    invest_pool = Column(Integer)
    commit_pool = Column(Integer)
    income_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    burns = relationship('Burn', backref='income', lazy=True, cascade="all, delete-orphan")
    invests = relationship('Invest', backref='income', lazy=True, cascade="all, delete-orphan")
    commitments = relationship('Commitment', backref='income', lazy=True, cascade="all, delete-orphan")


class Burn(db.Model):
    __tablename__ = 'burns'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    income_id = Column(String(36), ForeignKey('incomes.id'), nullable=False)
    category = Column(Enum('Stupid', 'Health', 'Therapeutic', 'Tech', '1year', 'fam', 'normal'))
    amount = Column(DECIMAL(10, 2))
    description = Column(Text)
    photo_url = Column(Text)
    burn_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    meals = relationship('Meal', backref='burn', lazy=True, cascade="all, delete-orphan")


class Invest(db.Model):
    __tablename__ = 'invests'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    income_id = Column(String(36), ForeignKey('incomes.id'), nullable=False)
    category = Column(Enum('High Risks', 'Med Risks', 'Low Risks'))
    amount = Column(DECIMAL(10, 2))
    description = Column(Text)
    is_done = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    photo_url = Column(Text)
    invest_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)


class Commitment(db.Model):
    __tablename__ = 'commitments'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    income_id = Column(String(36), ForeignKey('incomes.id'), nullable=False)
    amount = Column(DECIMAL(10, 2))
    category = Column(Enum('Daily Food', 'Groceries', 'Transport', 'Home', 'PAMA', 'Perlindungan'))
    description = Column(Text)
    is_done = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    photo_url = Column(Text)
    commit_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    meals = relationship('Meal', backref='commitment', lazy=True, cascade="all, delete-orphan")


class Meal(db.Model):
    __tablename__ = 'meals'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    commit_id = Column(String(36), ForeignKey('commitments.id'), nullable=True)
    burn_id = Column(String(36), ForeignKey('burns.id'), nullable=True)
    meal_type = Column(Enum('breakfast', 'lunch', 'dinner', 'snack'))
    reply_description = Column(Text)
    calories = Column(Integer)
    protein = Column(DECIMAL(5, 2))
    fat = Column(DECIMAL(5, 2))
    carbs = Column(DECIMAL(5, 2))
    meal_date = Column(Date)
    meal_time = Column(Time, nullable=True)
    photo_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Goal(db.Model):
    __tablename__ = 'goals'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    goal_type = Column(Enum('savings', 'calories', 'custom'))
    target_value = Column(DECIMAL(10, 2))
    current_value = Column(DECIMAL(10, 2))
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Note(db.Model):
    __tablename__ = 'notes'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50))
    note_type = Column(Enum('one-time', 'recurring'), nullable=False)
    recurrence_interval_days = Column(Integer)
    last_reset_date = Column(Date)
    next_due_date = Column(Date)
    is_done = Column(Boolean, default=False)
    done_date = Column(DateTime)
    burn_id = Column(String(36), ForeignKey('burns.id', ondelete='SET NULL'))
    invest_id = Column(String(36), ForeignKey('invests.id', ondelete='SET NULL'))
    commitment_id = Column(String(36), ForeignKey('commitments.id', ondelete='SET NULL'))
    notification_enabled = Column(Boolean, default=False)
    notification_type = Column(String(20))
    notification_datetime = Column(DateTime)
    notification_minutes_before = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class WeightEntry(db.Model):
    __tablename__ = 'weight_entries'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    weight_kg = Column(DECIMAL(5, 2), nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'weight_kg': float(self.weight_kg),
            'date': self.date.isoformat(),
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }


class WeightGoal(db.Model):
    __tablename__ = 'weight_goals'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False, unique=True)
    starting_weight = Column(DECIMAL(5, 2), nullable=False)
    current_weight = Column(DECIMAL(5, 2), nullable=False)
    goal_weight = Column(DECIMAL(5, 2), nullable=False)
    height_cm = Column(Integer, nullable=False)
    target_date = Column(Date, nullable=False)
    current_phase = Column(Enum('priming', 'fat_loss', 'diet_break', 'final_push'), default='priming')
    phase_start_date = Column(Date, nullable=False)
    daily_calorie_target = Column(Integer, nullable=False)
    daily_protein_target = Column(Integer, nullable=False)
    daily_carbs_target = Column(Integer)
    daily_fat_target = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'starting_weight': float(self.starting_weight),
            'current_weight': float(self.current_weight),
            'goal_weight': float(self.goal_weight),
            'height_cm': self.height_cm,
            'target_date': self.target_date.isoformat(),
            'current_phase': self.current_phase,
            'phase_start_date': self.phase_start_date.isoformat(),
            'daily_calorie_target': self.daily_calorie_target,
            'daily_protein_target': self.daily_protein_target,
            'daily_carbs_target': self.daily_carbs_target,
            'daily_fat_target': self.daily_fat_target,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class NutritionReview(db.Model):
    __tablename__ = 'nutrition_reviews'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('Users.id'), nullable=False)
    review_date = Column(Date, nullable=False)
    total_calories = Column(Integer, nullable=False)
    total_protein = Column(DECIMAL(5, 2), nullable=False)
    total_carbs = Column(DECIMAL(5, 2), nullable=False)
    total_fat = Column(DECIMAL(5, 2), nullable=False)
    calorie_target = Column(Integer, nullable=False)
    protein_target = Column(Integer, nullable=False)
    adherence_score = Column(Integer)
    ai_feedback = Column(Text, nullable=False)
    grade = Column(String(2))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'review_date': self.review_date.isoformat(),
            'total_calories': self.total_calories,
            'total_protein': float(self.total_protein),
            'total_carbs': float(self.total_carbs),
            'total_fat': float(self.total_fat),
            'calorie_target': self.calorie_target,
            'protein_target': self.protein_target,
            'adherence_score': self.adherence_score,
            'ai_feedback': self.ai_feedback,
            'grade': self.grade,
            'created_at': self.created_at.isoformat()
        }
