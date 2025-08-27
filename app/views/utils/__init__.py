from datetime import datetime
from app.models import *
from sqlalchemy import func

def get_salary_cycle(today: datetime):
    """Return the start and end dates of the salary cycle for a given date."""
    year, month = today.year, today.month

    if today.day >= 25:
        # Cycle starts this month (25th) and ends next month (24th)
        start_date = datetime(year, month, 25).date()
        # Handle December → January wrap
        if month == 12:
            end_date = datetime(year + 1, 1, 24).date()
        else:
            end_date = datetime(year, month + 1, 24).date()
    else:
        # Cycle started last month (25th) and ends this month (24th)
        if month == 1:  # January → December of prev year
            start_date = datetime(year - 1, 12, 25).date()
        else:
            start_date = datetime(year, month - 1, 25).date()
        end_date = datetime(year, month, 24).date()

    return start_date, end_date


def get_available_to_invest(user_id):
    today = datetime.today()
    start_date, end_date = get_salary_cycle(today)

    income = (
        Income.query.filter(
            Income.user_id == user_id,
            Income.income_date >= start_date,
            Income.income_date <= end_date
        )
        .order_by(Income.income_date.desc())
        .first()
    )

    if not income:
        return None, None, None

    invest_pool = float(income.invest_pool) if income.invest_pool else 0.0

    total_invested = (
        db.session.query(func.coalesce(func.sum(Invest.amount), 0))
        .filter(
            Invest.income_id == income.id,
            Invest.invest_date >= start_date,
            Invest.invest_date <= end_date
        )
        .scalar()
    )

    available_to_invest = invest_pool - float(total_invested or 0)
    return income, available_to_invest, (start_date, end_date)