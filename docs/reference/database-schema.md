# Database Schema Reference

Complete database schema documentation for TracKaMate Backend.

---

## Overview

All models use **UUID (string 36 chars)** as primary keys. Foreign keys reference parent UUIDs.

### Database Conventions

- **Primary Keys**: UUID strings (36 characters)
- **Timestamps**: UTC datetime
- **Decimal Fields**: DECIMAL(10,2) for money, DECIMAL(5,2) for nutrition
- **Enum Fields**: Predefined string values
- **Nullable Fields**: Marked explicitly where applicable

---

## Entity Relationship Diagram

```
User (1) ──< (M) Income (1) ──< (M) Burn
   │                │
   │                ├──< (M) Invest
   │                │
   │                └──< (M) Commitment (1) ──< (M) Meal
   │                                             ↑
   │                                             │
   └─────────────────────────────────────────────┘
   │
   ├──< (M) Goal
   │
   └──< (M) Reminder
```

---

## Models

### User Model

**Table**: `Users`

Stores user account information and settings.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| username | String(100) | UNIQUE, NOT NULL | Username for login |
| email | String(100) | UNIQUE, NOT NULL | Email address |
| password_hash | String(255) | NOT NULL | Bcrypt hashed password |
| name | String(100) | NOT NULL | Display name |
| daily_limit_food | Integer | NULL | Daily calorie limit |
| daily_supply_food | Integer | NULL | Daily food supply amount |
| daily_limit_burn | Integer | NULL | Daily burn spending limit |
| daily_supply_burn | Integer | NULL | Daily burn supply amount |
| created_at | DateTime | NOT NULL | Account creation timestamp |

**Relationships**:
- One-to-many: `incomes`
- One-to-many: `meals`
- One-to-many: `goals`
- One-to-many: `reminders`

**Indexes**:
- Primary: `id`
- Unique: `username`, `email`

---

### Income Model

**Table**: `incomes`

Tracks income sources with automatic pool allocation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| user_id | String(36) | FK, NOT NULL | References Users.id |
| source | String(50) | NOT NULL | Income source name (e.g., "Salary") |
| amount | DECIMAL(10,2) | NOT NULL | Total income amount |
| photo_url | Text | NULL | Receipt/proof photo URL |
| burn_pool | Integer | NOT NULL | Allocated burn pool (20%) |
| invest_pool | Integer | NOT NULL | Allocated invest pool (30%) |
| commit_pool | Integer | NOT NULL | Allocated commit pool (50%) |
| income_date | Date | NOT NULL | Date income received |
| created_at | DateTime | NOT NULL | Record creation timestamp |

**Relationships**:
- Belongs to: `user`
- One-to-many: `burns`
- One-to-many: `invests`
- One-to-many: `commitments`

**Indexes**:
- Primary: `id`
- Foreign: `user_id`
- Index: `income_date`

**Pool Allocation Logic**:
```python
burn_pool = floor(amount * 0.20)      # 20%
invest_pool = floor(amount * 0.30)    # 30%
commit_pool = floor(amount * 0.50)    # 50%

# Handle rounding difference
total = burn_pool + invest_pool + commit_pool
difference = amount - total
commit_pool += difference  # Remainder goes to commit
```

**Example**:
- Income: RM 5000
- Burn: RM 1000 (20%)
- Invest: RM 1500 (30%)
- Commit: RM 2500 (50%)

---

### Burn Model

**Table**: `burns`

Tracks discretionary spending (fun money).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| income_id | String(36) | FK, NOT NULL | References incomes.id |
| category | Enum | NOT NULL | Spending category |
| amount | DECIMAL(10,2) | NOT NULL | Spending amount |
| description | Text | NULL | Spending description |
| photo_url | Text | NULL | Receipt photo URL |
| burn_date | Date | NOT NULL | Date of spending |
| created_at | DateTime | NOT NULL | Record creation timestamp |

**Categories (Enum)**:
- `Stupid` - Impulse/frivolous spending
- `Health` - Health-related expenses
- `Therapeutic` - Mental health/self-care
- `Tech` - Technology purchases
- `1year` - Items with 1-year lifespan
- `fam` - Family expenses
- `normal` - Regular discretionary spending

**Relationships**:
- Belongs to: `income`
- One-to-many: `meals` (optional - if meal paid via burn)

**Indexes**:
- Primary: `id`
- Foreign: `income_id`
- Index: `burn_date`, `category`

---

### Invest Model

**Table**: `invests`

Tracks investments with risk categorization.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| income_id | String(36) | FK, NOT NULL | References incomes.id |
| category | Enum | NOT NULL | Investment risk category |
| amount | DECIMAL(10,2) | NOT NULL | Investment amount |
| description | Text | NULL | Investment description |
| is_done | Boolean | DEFAULT FALSE | Investment completed |
| is_recurring | Boolean | DEFAULT FALSE | Recurring investment |
| photo_url | Text | NULL | Proof/screenshot URL |
| invest_date | Date | NOT NULL | Date of investment |
| created_at | DateTime | NOT NULL | Record creation timestamp |

**Categories (Enum)**:
- `High Risks` - High-risk investments (stocks, crypto, etc.)
- `Med Risks` - Medium-risk investments
- `Low Risks` - Low-risk investments (bonds, savings, etc.)

**Relationships**:
- Belongs to: `income`

**Indexes**:
- Primary: `id`
- Foreign: `income_id`
- Index: `invest_date`, `category`

---

### Commitment Model

**Table**: `commitments`

Tracks committed/fixed expenses.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| income_id | String(36) | FK, NOT NULL | References incomes.id |
| amount | DECIMAL(10,2) | NOT NULL | Commitment amount |
| category | Enum | NOT NULL | Commitment category |
| description | Text | NULL | Commitment description |
| is_done | Boolean | DEFAULT FALSE | Commitment paid |
| is_recurring | Boolean | DEFAULT FALSE | Recurring commitment |
| photo_url | Text | NULL | Bill/receipt photo URL |
| commit_date | Date | NOT NULL | Date of commitment |
| created_at | DateTime | NOT NULL | Record creation timestamp |

**Categories (Enum)**:
- `Daily Food` - Daily meal expenses
- `Groceries` - Grocery shopping
- `Transport` - Transportation costs
- `Home` - Rent, utilities, home expenses
- `PAMA` - Custom category (insurance/protection)
- `Perlindungan` - Protection/insurance

**Relationships**:
- Belongs to: `income`
- One-to-many: `meals` (optional - if meal paid via commit)

**Indexes**:
- Primary: `id`
- Foreign: `income_id`
- Index: `commit_date`, `category`

---

### Meal Model

**Table**: `meals`

Tracks meals with nutrition information.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| user_id | String(36) | FK, NOT NULL | References Users.id |
| commit_id | String(36) | FK, NULL | References commitments.id (if paid) |
| burn_id | String(36) | FK, NULL | References burns.id (if paid) |
| meal_type | Enum | NOT NULL | Meal type |
| reply_description | Text | NULL | Meal description/notes |
| calories | Integer | NOT NULL | Calorie count |
| protein | DECIMAL(5,2) | NOT NULL | Protein in grams |
| fat | DECIMAL(5,2) | NOT NULL | Fat in grams |
| carbs | DECIMAL(5,2) | NOT NULL | Carbohydrates in grams |
| meal_date | Date | NOT NULL | Date of meal |
| photo_url | Text | NULL | Food photo URL |
| created_at | DateTime | NOT NULL | Record creation timestamp |

**Meal Types (Enum)**:
- `breakfast`
- `lunch`
- `dinner`
- `snack`

**Relationships**:
- Belongs to: `user`
- Optionally belongs to: `commitment` (if paid via commit pool)
- Optionally belongs to: `burn` (if paid via burn pool)

**Indexes**:
- Primary: `id`
- Foreign: `user_id`, `commit_id`, `burn_id`
- Index: `meal_date`, `meal_type`

**Notes**:
- Either `commit_id` OR `burn_id` can be set, not both
- Both can be NULL if meal was free/homemade

---

### Goal Model

**Table**: `goals`

Tracks user financial and health goals.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| user_id | String(36) | FK, NOT NULL | References Users.id |
| goal_type | Enum | NOT NULL | Type of goal |
| target_value | DECIMAL(10,2) | NOT NULL | Target amount/value |
| current_value | DECIMAL(10,2) | DEFAULT 0 | Current progress |
| start_date | Date | NOT NULL | Goal start date |
| end_date | Date | NOT NULL | Goal end date |
| description | Text | NULL | Goal description |
| created_at | DateTime | NOT NULL | Record creation timestamp |

**Goal Types (Enum)**:
- `savings` - Savings goals
- `calories` - Calorie goals
- `custom` - Custom goals

**Relationships**:
- Belongs to: `user`

**Indexes**:
- Primary: `id`
- Foreign: `user_id`
- Index: `goal_type`, `end_date`

---

### Reminder Model

**Table**: `reminders`

Scheduled reminders for bills, meals, and custom events.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(36) | PK | UUID primary key |
| user_id | String(36) | FK, NOT NULL | References Users.id |
| type | Enum | NOT NULL | Reminder type |
| message | Text | NOT NULL | Reminder message |
| reminder_date | Date | NOT NULL | Reminder date |
| reminder_time | Time | NOT NULL | Reminder time |
| repeat_interval | Enum | DEFAULT 'none' | Repeat frequency |
| is_done | Boolean | DEFAULT FALSE | Reminder completed |
| done_date | DateTime | NULL | Completion timestamp |
| created_at | DateTime | NOT NULL | Record creation timestamp |

**Reminder Types (Enum)**:
- `bill` - Bill payment reminders
- `meal` - Meal tracking reminders
- `custom` - Custom reminders

**Repeat Intervals (Enum)**:
- `none` - One-time reminder
- `daily` - Repeat daily
- `weekly` - Repeat weekly
- `monthly` - Repeat monthly

**Relationships**:
- Belongs to: `user`

**Indexes**:
- Primary: `id`
- Foreign: `user_id`
- Index: `reminder_date`, `is_done`

---

## Database Migrations

### Initial Setup

```bash
python setup_db.py
```

This creates all tables with proper relationships and indexes.

### Future Migrations

For schema changes, use Alembic:

```bash
# Install Alembic
pip install alembic

# Initialize migrations
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Business Rules

### Salary Cycle (25th to 24th)

All financial calculations use a custom salary cycle:
- **Cycle Start**: 25th of the month
- **Cycle End**: 24th of the next month

**Example**:
- Today: Jan 15, 2024 → Cycle: Dec 25, 2023 to Jan 24, 2024
- Today: Jan 30, 2024 → Cycle: Jan 25, 2024 to Feb 24, 2024

### Pool Availability Validation

Before adding burn/invest/commit transactions:
1. Get current salary cycle dates
2. Find most recent income in cycle
3. Calculate total spent in category
4. Validate: `new_amount <= (pool_amount - total_spent)`

### Edit Transaction Rules

When editing a transaction:
1. Add current amount back to available pool
2. Validate new amount against adjusted pool
3. Update if valid, reject if insufficient

---

## Sample Queries

### Get User Income for Current Cycle

```sql
SELECT * FROM incomes
WHERE user_id = 'user-uuid'
  AND income_date BETWEEN '2024-01-25' AND '2024-02-24'
ORDER BY income_date DESC;
```

### Get Total Burn Spending

```sql
SELECT SUM(amount) as total_burned
FROM burns b
JOIN incomes i ON b.income_id = i.id
WHERE i.user_id = 'user-uuid'
  AND b.burn_date BETWEEN '2024-01-25' AND '2024-02-24';
```

### Get Daily Nutrition Summary

```sql
SELECT
  SUM(calories) as total_calories,
  SUM(protein) as total_protein,
  SUM(carbs) as total_carbs,
  SUM(fat) as total_fat
FROM meals
WHERE user_id = 'user-uuid'
  AND meal_date = '2024-01-15';
```

---

## Data Integrity

### Foreign Key Constraints

All foreign keys are configured with:
- `ON DELETE CASCADE` - Deleting parent deletes children
- `ON UPDATE CASCADE` - Updating parent ID updates children

### Validation Rules

**At Database Level**:
- NOT NULL constraints on required fields
- UNIQUE constraints on username/email
- ENUM constraints on category fields
- DECIMAL precision for monetary values

**At Application Level** (in Flask):
- Amount must be positive
- Dates must be valid
- Pool amounts cannot be negative
- File uploads must be valid types

---

**Last Updated**: October 2025
**Version**: 1.0
