from flask import Blueprint, request, jsonify
from app.models import *
from app.views.utils import *
from datetime import datetime
import math

income_bp = Blueprint('income', __name__)

# Create a new income
@income_bp.route('/add_income', methods=['POST'])
def add_income():
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))

        # Step 1: Calculate raw splits
        burn_raw = amount * 0.2
        invest_raw = amount * 0.3
        commit_raw = amount * 0.5

        # Step 2: Round down to whole numbers
        burn_pool = math.floor(burn_raw)
        invest_pool = math.floor(invest_raw)
        commit_pool = math.floor(commit_raw)

        # Step 3: Fix rounding difference
        total_allocated = burn_pool + invest_pool + commit_pool
        difference = round(amount - total_allocated)

        # Add the difference to commit_pool (or whichever you prefer)
        commit_pool += difference

        new_income = Income(
            user_id=data.get('user_id'),
            source=data.get('source'),
            amount=amount,
            burn_pool=burn_pool,
            invest_pool=invest_pool,
            commit_pool=commit_pool,
            income_date=datetime.strptime(data.get('income_date'), '%Y-%m-%d').date()
                if data.get('income_date') else None
        )

        db.session.add(new_income)
        db.session.commit()

        return jsonify({
            "message": "Income created successfully",
            "income": {
                "id": new_income.id,
                "user_id": new_income.user_id,
                "source": new_income.source,
                "amount": str(new_income.amount),
                "burn_pool": new_income.burn_pool,
                "invest_pool": new_income.invest_pool,
                "commit_pool": new_income.commit_pool,
                "income_date": new_income.income_date.isoformat() if new_income.income_date else None,
                "created_at": new_income.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@income_bp.route('/get_pools/<string:user_id>', methods=['GET'])
def get_income_pools(user_id):
    try:
        today = datetime.today()
        start_date, end_date = get_salary_cycle(today)

        # Query incomes in the cycle
        incomes = (
            Income.query
            .filter(
                Income.user_id == user_id,
                Income.income_date >= start_date,
                Income.income_date <= end_date
            )
            .all()
        )

        if not incomes:
            return jsonify({"error": "No income record found for this user in current cycle"}), 404

        # Sum up pools
        # total_income = Income.amount
        total_income = sum(i.amount for i in incomes if i.amount)
        total_burn = sum(i.burn_pool for i in incomes if i.burn_pool)
        total_invest = sum(i.invest_pool for i in incomes if i.invest_pool)
        total_commit = sum(i.commit_pool for i in incomes if i.commit_pool)

        return jsonify({
            "user_id": user_id,
            "cycle_start": start_date.strftime('%Y-%m-%d'),
            "cycle_end": end_date.strftime('%Y-%m-%d'),
            "income": total_income,
            "burn_pool": total_burn,
            "invest_pool": total_invest,
            "commit_pool": total_commit
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

