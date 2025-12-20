# TracKaMate Backend - Development Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Database Models](#database-models)
5. [API Endpoints](#api-endpoints)
6. [Business Logic](#business-logic)
7. [Setup & Configuration](#setup--configuration)
8. [Development Guide](#development-guide)
9. [Security](#security)

---

## Project Overview

**TracKaMate** is a personal finance and nutrition tracking backend application built with Flask. It helps users manage their income, allocate funds to different spending categories (burn/invest/commit), track meals and nutrition, set goals, and receive reminders.

### Key Features
- User authentication with JWT tokens
- Income tracking with automatic allocation to spending pools
- Discretionary spending (burn) management
- Investment tracking
- Committed expenses (bills, groceries, etc.)
- Meal and nutrition tracking with AI-powered analysis
- **Weight management system** with goal tracking and phase-based nutrition targets
- **Daily nutrition reviews** with automated grading and feedback
- **Intermittent fasting compliance** tracking
- **Plateau detection** with personalized recommendations
- Goals and reminders
- Salary cycle-based financial tracking (25th to 24th)

---

## Technology Stack

### Core Framework
- **Flask 3.1.1** - Web framework
- **Python 3.13** - Programming language

### Database & ORM
- **SQLAlchemy 2.0.42** - ORM library
- **Flask-SQLAlchemy 3.1.1** - Flask SQLAlchemy integration
- **PyMySQL 1.1.1** - MySQL database driver
- **MySQL** - Database (connection via DATABASE_URI env variable)

### Authentication & Security
- **Flask-JWT-Extended 4.7.1** - JWT token authentication
- **Flask-Bcrypt 1.0.1** - Password hashing
- **PyJWT 2.10.1** - JWT implementation

### Data Validation
- **Marshmallow 4.0.0** - Serialization/validation

### Utilities
- **python-dotenv 1.1.1** - Environment variable management
- **Flask-CORS** - Cross-origin resource sharing
- **Click 8.2.1** - CLI framework

---

## Project Structure

```
trackamate_be/
├── app/                          # Main application package
│   ├── __init__.py              # Flask app factory (create_app)
│   ├── models/                  # SQLAlchemy database models
│   │   └── __init__.py         # User, Income, Burn, Invest, Commitment, Meal, Goal, Reminder, WeightGoal, WeightEntry, NutritionReview
│   ├── schemas/                 # Marshmallow validation schemas
│   │   └── user_schema.py
│   └── views/                   # Blueprint route handlers
│       ├── auth/                # Authentication endpoints
│       │   └── __init__.py     # /register, /login, /me
│       ├── food/                # Meal tracking endpoints
│       │   └── __init__.py
│       ├── income/              # Income management endpoints
│       │   └── __init__.py     # /add_income, /get_pools
│       ├── burn/                # Discretionary spending endpoints
│       │   └── __init__.py
│       ├── invest/              # Investment tracking endpoints
│       │   └── __init__.py
│       ├── commit/              # Committed expenses endpoints
│       │   └── __init__.py
│       ├── weight/              # Weight management endpoints
│       │   └── __init__.py     # /setup-goal, /entry, /daily-review, /weekly-summary, /plateau-check, /meal-timing
│       └── utils/               # Shared utility functions
│           └── __init__.py     # get_salary_cycle, get_available_to_invest
├── config.py                    # Configuration class (loads from .env)
├── run.py                       # Application entry point
├── setup_db.py                  # Database initialization script
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
└── DEVELOPMENT.md              # This file
```

---

## Database Models

All models use UUID (string 36 chars) as primary keys. Foreign keys reference parent UUIDs.

### User Model
**Table**: `Users`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| username | String(100) Unique | Username for login |
| email | String(100) Unique | Email address |
| password_hash | String(255) | Bcrypt hashed password |
| name | String(100) | Display name |
| daily_limit_food | Integer | Daily food calorie limit |
| daily_supply_food | Integer | Daily food supply amount |
| daily_limit_burn | Integer | Daily burn spending limit |
| daily_supply_burn | Integer | Daily burn supply amount |
| created_at | DateTime | Account creation timestamp |

**Relationships**:
- One-to-many: `incomes`, `goals`, `reminders`

---

### Income Model
**Table**: `incomes`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| user_id | String(36) FK | References Users.id |
| source | String(50) | Income source name |
| amount | DECIMAL(10,2) | Total income amount |
| photo_url | Text | Receipt/proof photo URL |
| burn_pool | Integer | Allocated burn pool (20%) |
| invest_pool | Integer | Allocated invest pool (30%) |
| commit_pool | Integer | Allocated commit pool (50%) |
| income_date | Date | Date income received |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `user`
- One-to-many: `burns`, `invests`, `commitments`

**Pool Allocation Logic**:
- Burn Pool: 20% (discretionary/fun spending)
- Invest Pool: 30% (investments)
- Commit Pool: 50% (committed expenses, bills, food)
- Uses floor rounding, difference added to commit_pool

---

### Burn Model
**Table**: `burns`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| income_id | String(36) FK | References incomes.id |
| category | Enum | 'Stupid', 'Health', 'Therapeutic', 'Tech', '1year', 'fam', 'normal' |
| amount | DECIMAL(10,2) | Spending amount |
| description | Text | Spending description |
| photo_url | Text | Receipt photo URL |
| burn_date | Date | Date of spending |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `income`

**Categories**:
- **Stupid**: Impulse/frivolous spending
- **Health**: Health-related expenses
- **Therapeutic**: Mental health/self-care
- **Tech**: Technology purchases
- **1year**: Items with 1-year lifespan
- **fam**: Family expenses
- **normal**: Regular discretionary spending

---

### Invest Model
**Table**: `invests`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| income_id | String(36) FK | References incomes.id |
| category | Enum | 'High Risks', 'Med Risks', 'Low Risks' |
| amount | DECIMAL(10,2) | Investment amount |
| description | Text | Investment description |
| is_done | Boolean | Investment completed |
| is_recurring | Boolean | Recurring investment |
| photo_url | Text | Proof/screenshot URL |
| invest_date | Date | Date of investment |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `income`

**Categories**:
- **High Risks**: High-risk investments (stocks, crypto, etc.)
- **Med Risks**: Medium-risk investments
- **Low Risks**: Low-risk investments (bonds, savings, etc.)

---

### Commitment Model
**Table**: `commitments`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| income_id | String(36) FK | References incomes.id |
| amount | DECIMAL(10,2) | Commitment amount |
| category | Enum | 'Daily Food', 'Groceries', 'Transport', 'Home', 'PAMA', 'Perlindungan' |
| description | Text | Commitment description |
| is_done | Boolean | Commitment paid |
| is_recurring | Boolean | Recurring commitment |
| photo_url | Text | Bill/receipt photo URL |
| commit_date | Date | Date of commitment |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `income`
- One-to-many: `meals`

**Categories**:
- **Daily Food**: Daily meal expenses
- **Groceries**: Grocery shopping
- **Transport**: Transportation costs
- **Home**: Rent, utilities, home expenses
- **PAMA**: (Custom category - likely insurance/protection)
- **Perlindungan**: (Protection/insurance in Indonesian)

---

### Meal Model
**Table**: `meals`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| user_id | String(36) FK | References Users.id |
| commit_id | String(36) FK Nullable | References commitments.id (if paid via commit pool) |
| burn_id | String(36) FK Nullable | References burns.id (if paid via burn pool) |
| meal_type | Enum | 'breakfast', 'lunch', 'dinner', 'snack' |
| reply_description | Text | Meal description/notes |
| calories | Integer | Calorie count |
| protein | DECIMAL(5,2) | Protein in grams |
| fat | DECIMAL(5,2) | Fat in grams |
| carbs | DECIMAL(5,2) | Carbohydrates in grams |
| meal_date | Date | Date of meal |
| meal_time | Time Nullable | **NEW** Actual time meal was consumed (HH:MM:SS) |
| photo_url | Text | Food photo URL |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `user`
- Optionally belongs to: `commitment` or `burn`

**Note**: `meal_time` field added to track actual meal consumption time separately from record creation time (`created_at`). This enables accurate meal timing analysis for intermittent fasting tracking.

---

### Goal Model
**Table**: `goals`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| user_id | String(36) FK | References Users.id |
| goal_type | Enum | 'savings', 'calories', 'custom' |
| target_value | DECIMAL(10,2) | Target amount/value |
| current_value | DECIMAL(10,2) | Current progress |
| start_date | Date | Goal start date |
| end_date | Date | Goal end date |
| description | Text | Goal description |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `user`

---

### Reminder Model
**Table**: `reminders`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| user_id | String(36) FK | References Users.id |
| type | Enum | 'bill', 'meal', 'custom' |
| message | Text | Reminder message |
| reminder_date | Date | Reminder date |
| reminder_time | Time | Reminder time |
| repeat_interval | Enum | 'none', 'daily', 'weekly', 'monthly' |
| is_done | Boolean | Reminder completed |
| done_date | DateTime | Completion timestamp |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `user`

---

### WeightGoal Model
**Table**: `weight_goals`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| user_id | String(36) FK Unique | References Users.id (one goal per user) |
| starting_weight | DECIMAL(5,2) | Initial weight in kg |
| current_weight | DECIMAL(5,2) | Current weight in kg |
| goal_weight | DECIMAL(5,2) | Target weight in kg |
| height_cm | Integer | Height in centimeters |
| target_date | Date | Goal completion date |
| current_phase | Enum | 'priming', 'fat_loss', 'diet_break', 'final_push' |
| phase_start_date | Date | When current phase started |
| daily_calorie_target | Integer | Daily calorie goal |
| daily_protein_target | Integer | Daily protein goal (grams) |
| daily_carbs_target | Integer Nullable | Daily carbs goal (grams) |
| daily_fat_target | Integer Nullable | Daily fat goal (grams) |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Last update timestamp |

**Relationships**:
- Belongs to: `user` (one-to-one)

**Phases**:
- **priming**: Initial 2-4 weeks, body adaptation
- **fat_loss**: Active weight loss phase
- **diet_break**: 1-2 weeks eating at maintenance
- **final_push**: Final weeks to reach goal

---

### WeightEntry Model
**Table**: `weight_entries`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| user_id | String(36) FK | References Users.id |
| weight_kg | DECIMAL(5,2) | Weight measurement in kg |
| date | Date | Measurement date |
| notes | Text Nullable | Optional notes |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `user`

---

### NutritionReview Model
**Table**: `nutrition_reviews`

| Field | Type | Description |
|-------|------|-------------|
| id | String(36) PK | UUID primary key |
| user_id | String(36) FK | References Users.id |
| review_date | Date | Date being reviewed |
| total_calories | Integer | Total calories consumed |
| total_protein | DECIMAL(5,2) | Total protein (grams) |
| total_carbs | DECIMAL(5,2) | Total carbs (grams) |
| total_fat | DECIMAL(5,2) | Total fat (grams) |
| calorie_target | Integer | Target calories for that day |
| protein_target | Integer | Target protein for that day |
| adherence_score | Integer Nullable | Compliance score (0-100) |
| ai_feedback | Text | Generated feedback |
| grade | String(2) Nullable | Grade (A, B, C, D, F) |
| created_at | DateTime | Record creation timestamp |

**Relationships**:
- Belongs to: `user`

---

## API Endpoints

### Authentication (`/user`)

#### POST /user/register
Register a new user account.

**Request Body**:
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response** (201):
```json
{
  "id": "uuid",
  "username": "johndoe",
  "email": "john@example.com",
  "name": "John Doe",
  "created_at": "2024-01-01T00:00:00"
}
```

---

#### POST /user/login
Login and receive JWT access token.

**Request Body**:
```json
{
  "username": "johndoe",
  "password": "securepassword"
}
```

**Response** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

#### GET /user/me
Get current user profile (requires JWT token).

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200):
```json
{
  "id": "uuid",
  "username": "johndoe",
  "email": "john@example.com",
  "name": "John Doe",
  "daily_limit_food": 2000,
  "daily_supply_food": 50,
  "daily_limit_burn": 100,
  "daily_supply_burn": 500
}
```

---

### Income (`/income`)

#### POST /income/add_income
Add new income and automatically allocate to pools.

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "source": "Salary",
  "amount": 5000,
  "income_date": "2024-01-15"
}
```

**Response** (201):
```json
{
  "message": "Income created successfully",
  "income": {
    "id": "income-uuid",
    "user_id": "user-uuid",
    "source": "Salary",
    "amount": "5000.00",
    "burn_pool": 1000,
    "invest_pool": 1500,
    "commit_pool": 2500,
    "income_date": "2024-01-15",
    "created_at": "2024-01-15T10:00:00"
  }
}
```

**Allocation Logic**:
- Burn Pool = floor(amount * 0.2)
- Invest Pool = floor(amount * 0.3)
- Commit Pool = floor(amount * 0.5) + rounding_difference

---

#### GET /income/get_pools/:user_id
Get aggregated income pools for current salary cycle.

**Response** (200):
```json
{
  "user_id": "user-uuid",
  "cycle_start": "2024-01-25",
  "cycle_end": "2024-02-24",
  "income": 5000.00,
  "burn_pool": 1000,
  "invest_pool": 1500,
  "commit_pool": 2500
}
```

---

### Burn (`/burn`)

#### POST /burn/add_burn
Add discretionary spending.

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "amount": 50,
  "category": "Tech",
  "description": "New headphones",
  "burn_date": "2024-01-20"
}
```

**Response** (201):
```json
{
  "message": "Burn added successfully",
  "burn": {
    "id": "burn-uuid",
    "income_id": "income-uuid",
    "category": "Tech",
    "amount": "50.00",
    "description": "New headphones",
    "burn_date": "2024-01-20"
  },
  "available_to_burn": 950.00
}
```

---

#### PUT /burn/update_burn/:id
Update existing burn record.

**Request Body**:
```json
{
  "amount": 60,
  "description": "Updated description"
}
```

---

#### DELETE /burn/delete_burn/:id
Delete a burn record.

**Response** (200):
```json
{
  "message": "Burn deleted successfully",
  "burn_id": "burn-uuid"
}
```

---

#### GET /burn/total_burn/:user_id
Get all burns for current salary cycle.

**Response** (200):
```json
{
  "burns": [
    {
      "id": "burn-uuid",
      "category": "Tech",
      "amount": 50.00,
      "description": "New headphones",
      "burn_date": "2024-01-20"
    }
  ],
  "burn_pool": 1000,
  "burn_remainder": 950
}
```

---

### Invest (`/invest`)

#### POST /invest/add_invest
Add new investment.

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "amount": 500,
  "category": "Med Risks",
  "description": "Index fund",
  "is_done": false,
  "is_recurring": true,
  "invest_date": "2024-01-20"
}
```

**Response** (201):
```json
{
  "message": "Investment added successfully",
  "invest": {
    "id": "invest-uuid",
    "income_id": "income-uuid",
    "category": "Med Risks",
    "amount": "500.00",
    "description": "Index fund",
    "is_done": false,
    "is_recurring": true,
    "invest_date": "2024-01-20"
  },
  "available_to_invest": 1000.00
}
```

---

#### PUT /invest/edit_invest/:invest_id
Update existing investment.

---

#### DELETE /invest/delete_invest/:invest_id
Delete an investment record.

**Response** (200):
```json
{
  "message": "Investment deleted successfully",
  "invest_id": "invest-uuid"
}
```

---

#### GET /invest/total_invest/:user_id
Get all investments for current salary cycle.

**Response** (200):
```json
{
  "invests": [
    {
      "id": "invest-uuid",
      "category": "Med Risks",
      "amount": 500.00,
      "description": "Index fund",
      "invest_date": "2024-01-20"
    }
  ],
  "invest_pool": 1500,
  "invest_remainder": 1000
}
```

---

### Commit (`/commit`)

#### POST /commit/add_commit
Add committed expense.

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "amount": 800,
  "category": "Home",
  "description": "Monthly rent",
  "is_done": false,
  "is_recurring": true,
  "commit_date": "2024-01-25"
}
```

---

#### PUT /commit/edit_commit/:commit_id
Update existing commitment.

---

#### DELETE /commit/delete_commit/:commit_id
Delete a commitment record.

**Response** (200):
```json
{
  "message": "Commitment deleted successfully",
  "commit_id": "commit-uuid"
}
```

---

#### GET /commit/total_commit/:user_id
Get all commitments for current salary cycle.

---

### Food (`/food`)

#### POST /food/add_food
Add meal/nutrition entry.

#### PUT /food/edit_food/:meal_id
Update meal entry.

#### GET /food/get_food/:user_id
Get all meals for a user.

#### POST /food/add_food_setting/:user_id
Add food tracking settings.

#### PUT /food/edit_food_setting/:user_id
Update food settings.

#### GET /food/view_food_setting/:user_id
View food settings.

---

### Weight Management (`/weight`)

#### POST /weight/setup-goal
Initial setup for weight loss journey. Creates weight goal with calculated macro targets.

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "starting_weight": 85.5,
  "goal_weight": 75.0,
  "height_cm": 175,
  "target_date": "2025-06-01"
}
```

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "goal-uuid",
    "user_id": "user-uuid",
    "starting_weight": 85.5,
    "current_weight": 85.5,
    "goal_weight": 75.0,
    "height_cm": 175,
    "target_date": "2025-06-01",
    "current_phase": "priming",
    "phase_start_date": "2025-12-03",
    "daily_calorie_target": 1800,
    "daily_protein_target": 150,
    "phases": [...]
  }
}
```

---

#### POST /weight/entry
Add a weight measurement.

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "weight_kg": 84.2,
  "date": "2025-12-03",
  "notes": "Morning weight"
}
```

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "entry-uuid",
    "user_id": "user-uuid",
    "weight_kg": 84.2,
    "date": "2025-12-03",
    "notes": "Morning weight",
    "created_at": "2025-12-03T07:30:00"
  }
}
```

---

#### GET /weight/entries/:user_id
Get weight entries for a user.

**Query Params**:
- `limit` (optional): Number of entries (default: 30)
- `start_date` (optional): Filter from date (YYYY-MM-DD)
- `end_date` (optional): Filter to date (YYYY-MM-DD)

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "id": "entry-uuid",
      "weight_kg": 84.2,
      "date": "2025-12-03",
      "notes": "Morning weight"
    }
  ],
  "count": 15
}
```

---

#### GET /weight/trend/:user_id
Get weight trend data for charts.

**Query Params**:
- `days` (optional): Number of days (default: 30)

**Response** (200):
```json
{
  "success": true,
  "data": {
    "entries": [
      {"date": "2025-11-03", "weight_kg": 85.5},
      {"date": "2025-11-10", "weight_kg": 84.8}
    ],
    "trend": "decreasing",
    "avg_weekly_loss": -0.5,
    "total_loss": -1.3
  }
}
```

---

#### GET /weight/goal/:user_id
Get weight goal for a user.

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "goal-uuid",
    "current_weight": 84.2,
    "goal_weight": 75.0,
    "daily_calorie_target": 1800,
    "daily_protein_target": 150,
    "current_phase": "fat_loss"
  }
}
```

---

#### GET /weight/current-phase/:user_id
Get current phase information and nutrition targets.

**Response** (200):
```json
{
  "success": true,
  "data": {
    "current_phase": "fat_loss",
    "phase_description": "Active weight loss phase",
    "daily_calorie_target": 1800,
    "daily_protein_target": 150,
    "daily_carbs_target": 180,
    "daily_fat_target": 60,
    "current_weight": 84.2,
    "goal_weight": 75.0,
    "weight_lost": 1.3,
    "weight_remaining": 9.2
  }
}
```

---

#### PUT /weight/update-phase
Manually update phase (for diet breaks, transitions).

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "new_phase": "diet_break",
  "daily_calorie_target": 2200,
  "daily_protein_target": 150
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "current_phase": "diet_break",
    "phase_start_date": "2025-12-03"
  }
}
```

---

#### GET /weight/daily-review/:user_id
Get daily nutrition review with AI feedback and grade.

**Query Params**:
- `date` (optional): Date to review (YYYY-MM-DD, default: today)

**Response** (200):
```json
{
  "success": true,
  "data": {
    "date": "2025-12-03",
    "total_calories": 1850,
    "total_protein": 145,
    "total_carbs": 180,
    "total_fat": 65,
    "calorie_target": 1800,
    "protein_target": 150,
    "calorie_variance": 50,
    "protein_variance": -5,
    "grade": "B",
    "ai_feedback": "You're 50 kcal over target. Protein intake is spot on! Keep up the great work!"
  }
}
```

**Grading System**:
- **Grade A**: Both calories and protein within ±5% of targets
- **Grade B**: Both within ±10% of targets
- **Grade C**: Both within ±20% of targets
- **Grade D**: Both within ±30% of targets
- **Grade F**: Either metric more than 30% off target

---

#### GET /weight/weekly-summary/:user_id
Get weekly aggregated nutrition statistics.

**Query Params**:
- `weeks` (optional): Number of weeks (2, 4, or 8, default: 4)

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "week_start": "2025-11-04",
      "week_end": "2025-11-10",
      "avg_calories": 1820,
      "avg_protein": 148,
      "avg_carbs": 175,
      "avg_fat": 62,
      "target_calories": 1800,
      "target_protein": 150,
      "compliance_rate": 92.5
    }
  ]
}
```

**Compliance Rate**: Percentage of days where both calories AND protein are within ±10% of targets.

---

#### GET /weight/plateau-check/:user_id
Detect if weight loss has plateaued and provide recommendations.

**Response** (200):
```json
{
  "success": true,
  "data": {
    "is_plateau": true,
    "weeks_stalled": 3,
    "last_weight_change": 0.2,
    "recommendation": "Your weight has been stable for 3 weeks. Consider implementing a refeed day (eating at maintenance calories) or adding 30 minutes of cardio 3x per week to break through this plateau."
  }
}
```

**Plateau Detection**: 3+ consecutive weeks with <0.25kg change. Requires at least 8 weight entries over 4 weeks.

---

#### GET /weight/meal-timing/:user_id
Analyze meal timing for intermittent fasting (16:8) compliance.

**Query Params**:
- `days` (optional): Number of days (7, 14, or 30, default: 7)

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "date": "2025-12-01",
      "first_meal_time": "12:30",
      "last_meal_time": "19:45",
      "eating_window_hours": 7.25,
      "is_16_8_compliant": true
    },
    {
      "date": "2025-12-02",
      "first_meal_time": "11:00",
      "last_meal_time": "21:30",
      "eating_window_hours": 10.5,
      "is_16_8_compliant": false
    }
  ]
}
```

**16:8 Compliance**: `eating_window_hours <= 8.0`

---

### Health Check

#### GET /status
Health check endpoint.

**Response** (200):
```
OK
```

---

## Business Logic

### Salary Cycle (25th to 24th)
The application uses a custom salary cycle that runs from the 25th of one month to the 24th of the next month.

**Utility Function**: `get_salary_cycle(today: datetime)` in `app/views/utils/__init__.py:5`

**Logic**:
- If today's day >= 25: Cycle is (current month 25th → next month 24th)
- If today's day < 25: Cycle is (previous month 25th → current month 24th)
- Handles year wrap (December → January)

**Example**:
- Date: Jan 15, 2024 → Cycle: Dec 25, 2023 to Jan 24, 2024
- Date: Jan 30, 2024 → Cycle: Jan 25, 2024 to Feb 24, 2024

---

### Income Pool Allocation
When income is added, the amount is automatically split into three pools.

**Utility Function**: `add_income()` in `app/views/income/__init__.py:11`

**Formula**:
```python
burn_pool = floor(amount * 0.20)      # 20%
invest_pool = floor(amount * 0.30)    # 30%
commit_pool = floor(amount * 0.50)    # 50%

# Handle rounding difference
total_allocated = burn_pool + invest_pool + commit_pool
difference = round(amount - total_allocated)
commit_pool += difference  # Add remainder to commit pool
```

**Example** (amount = 5000):
- burn_pool = 1000
- invest_pool = 1500
- commit_pool = 2500

---

### Available Pool Calculation
Before adding burns/invests/commits, the system checks available funds in the respective pool.

**Utility Function**: `get_available_to_invest(user_id)` in `app/views/utils/__init__.py:28`

**Logic**:
1. Get current salary cycle dates
2. Find most recent income in cycle
3. Get total spent in category (e.g., total invests)
4. Calculate: `available = pool_amount - total_spent`
5. Reject if new transaction exceeds available amount

**Similar logic applies to**:
- Burn pool availability
- Commit pool availability

---

### Edit with Pool Recalculation
When editing a burn/invest/commit, the system:
1. Gets current record amount
2. Adds it back to available pool
3. Checks if new amount fits in adjusted pool
4. Updates if valid, rejects if insufficient

**Example** in `app/views/invest/__init__.py:76`:
```python
adjusted_available = available_to_invest + float(invest.amount)
if float(new_amount) > adjusted_available:
    return error
```

---

## Setup & Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_URI=mysql+pymysql://username:password@localhost/trackamate_db
```

**Required Variables**:
- `SECRET_KEY`: Flask session security key
- `JWT_SECRET_KEY`: JWT token signing key
- `DATABASE_URI`: MySQL connection string

**Connection String Format**:
```
mysql+pymysql://username:password@host:port/database_name
```

---

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd trackamate_be
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
Create `.env` file with required variables (see above).

5. **Initialize database**:
```bash
python setup_db.py
```

This creates all tables in the MySQL database.

6. **Run the application**:
```bash
python run.py
```

Server runs on `http://localhost:5000` by default.

---

### Database Setup

**MySQL Database Creation**:
```sql
CREATE DATABASE trackamate_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'trackamate_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON trackamate_db.* TO 'trackamate_user'@'localhost';
FLUSH PRIVILEGES;
```

**Table Creation**:
Run `python setup_db.py` to create all tables via SQLAlchemy.

---

## Development Guide

### Adding a New Endpoint

1. **Create route in appropriate blueprint** (`app/views/<module>/__init__.py`):
```python
@blueprint_name.route('/new_endpoint', methods=['POST'])
def new_endpoint():
    data = request.json
    # Your logic here
    return jsonify({"message": "Success"}), 200
```

2. **Add validation** (if needed):
```python
if not data.get('required_field'):
    return jsonify({"error": "Missing required field"}), 400
```

3. **Database operations**:
```python
new_record = Model(field=data.get('field'))
db.session.add(new_record)
db.session.commit()
```

4. **Error handling**:
```python
try:
    # Database operations
except Exception as e:
    db.session.rollback()
    return jsonify({"error": str(e)}), 500
```

---

### Adding a New Model

1. **Define model** in `app/models/__init__.py`:
```python
class NewModel(db.Model):
    __tablename__ = 'new_models'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    # Other fields
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. **Add relationships**:
```python
# In parent model:
children = relationship('NewModel', backref='parent', lazy=True, cascade="all, delete-orphan")

# In child model:
parent_id = Column(String(36), ForeignKey('parents.id'), nullable=False)
```

3. **Re-run database setup**:
```bash
python setup_db.py
```

---

### Testing with curl

**Register user**:
```bash
curl -X POST http://localhost:5000/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'
```

**Login**:
```bash
curl -X POST http://localhost:5000/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

**Add income**:
```bash
curl -X POST http://localhost:5000/income/add_income \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "source": "Salary",
    "amount": 5000,
    "income_date": "2024-01-15"
  }'
```

---

## Security

### Password Security
- Passwords hashed with **bcrypt** using Flask-Bcrypt
- Never store plain text passwords
- Hash generated: `bcrypt.generate_password_hash(password).decode('utf-8')`
- Verification: `bcrypt.check_password_hash(stored_hash, provided_password)`

### JWT Authentication
- Access tokens generated on login
- Tokens include user ID (identity)
- Protected routes use `@jwt_required()` decorator
- Extract user: `get_jwt_identity()`

**Example**:
```python
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    user_id = get_jwt_identity()
    # Access user data
```

### CORS Configuration
Currently allows all origins (`*`):
```python
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
```

**Production**: Restrict to specific frontend domain:
```python
CORS(app, resources={r"/*": {"origins": "https://yourdomain.com"}}, supports_credentials=True)
```

### Environment Security
- Sensitive data in `.env` file
- `.env` should be in `.gitignore`
- Never commit secrets to version control

### SQL Injection Prevention
- SQLAlchemy ORM prevents SQL injection
- Always use ORM queries, not raw SQL
- Validate and sanitize user input

---

## Common Issues & Solutions

### Issue: Database connection fails
**Solution**: Check `DATABASE_URI` in `.env`, ensure MySQL server is running, verify credentials.

### Issue: JWT token invalid
**Solution**: Ensure `JWT_SECRET_KEY` is set in `.env`, check token expiration, verify Authorization header format.

### Issue: CORS errors
**Solution**: Check CORS configuration in `app/__init__.py`, ensure frontend origin is allowed.

### Issue: Pool insufficient errors
**Solution**: User has spent more than allocated pool in salary cycle. Check pool amounts with `/income/get_pools/:user_id`.

---

## Future Enhancements

- Add pagination to list endpoints
- Implement refresh tokens for JWT
- Add photo upload functionality (currently just URLs)
- Implement goals and reminders endpoints
- Add email notifications for reminders
- Implement data export (CSV, PDF)
- Add analytics and reporting endpoints
- Create admin panel for user management

---

## Contact & Support

For issues or questions:
- Review this documentation
- Check the codebase comments
- Refer to Flask documentation: https://flask.palletsprojects.com/
- SQLAlchemy docs: https://docs.sqlalchemy.org/

---

**Last Updated**: December 2025
**Version**: 1.1

---

## Recent Updates (v1.1 - December 2025)

### Weight Management System
- Added **WeightGoal**, **WeightEntry**, and **NutritionReview** models
- Implemented complete weight tracking and nutrition analysis system
- Added 4 new analytics endpoints:
  - `/weight/daily-review` - Daily nutrition grading with AI feedback
  - `/weight/weekly-summary` - Weekly aggregated statistics
  - `/weight/plateau-check` - Plateau detection with recommendations
  - `/weight/meal-timing` - Intermittent fasting compliance tracking

### Meal Tracking Enhancement
- Added `meal_time` field to Meal model
- Enables accurate meal timing analysis separate from record creation time
- Supports intermittent fasting tracking
- Backward compatible with existing data

### Documentation
- Complete API documentation for weight management endpoints
- Database schema documentation for new models
- Frontend integration guides available:
  - `FRONTEND_MEAL_TIME_INTEGRATION.md`
  - `WEIGHT_API_IMPLEMENTATION_SUMMARY.md`
**Author**: TracKaMate Development Team
