from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.views.utils import *
from app.models import *
from datetime import datetime

burn_bp = Blueprint('burn', __name__)

@burn_bp.route('/add_burn_setting/<string:user_id>', methods=['POST'])
def add_burn_setting(user_id):
    data = request.get_json()
    daily_limit_burn = data.get('daily_limit_burn')
    daily_supply_burn = data.get('daily_supply_burn')

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.daily_limit_burn = daily_limit_burn
    user.daily_supply_burn = daily_supply_burn
    db.session.commit()

    return jsonify({
        "message": "Burn settings added successfully",
        "user_id": user.id,
        "daily_limit_burn": user.daily_limit_burn,
        "daily_supply_burn": user.daily_supply_burn
    }), 200

@burn_bp.route('/edit_burn_setting/<string:user_id>', methods=['PUT'])
def edit_burn_setting(user_id):
    data = request.get_json()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if "daily_limit_burn" in data:
        user.daily_limit_burn = data["daily_limit_burn"]
    if "daily_supply_burn" in data:
        user.daily_supply_burn = data["daily_supply_burn"]

    db.session.commit()

    return jsonify({
        "message": "Burn settings updated successfully",
        "user_id": user.id,
        "daily_limit_burn": user.daily_limit_burn,
        "daily_supply_burn": user.daily_supply_burn
    }), 200

@burn_bp.route('/view_burn_setting/<string:user_id>', methods=['GET'])
def view_burn_settings(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user_id": user.id,
        "daily_limit_burn": user.daily_limit_burn,
        "daily_supply_burn": user.daily_supply_burn
    }), 200

@burn_bp.route('/add_burn', methods=['POST'])
def add_burn():
    data = request.json
    user_id = data.get("user_id")
    amount = data.get("amount")
    category = data.get("category")
    burn_date = data.get("burn_date")
    description = data.get("description")

    if not user_id or not amount or not category:
        return jsonify({"error": "Missing required fields"}), 400

    today = datetime.today()
    start_date, end_date = get_salary_cycle(today)

    # find latest income within current cycle
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
        return jsonify({"error": "No income found for current salary cycle"}), 400

    new_burn = Burn(
        income_id=income.id,
        category=category,
        amount=amount,
        description=description,
        burn_date=burn_date
    )

    db.session.add(new_burn)
    db.session.commit()

    return jsonify({
        "message": "Burn spending added successfully",
        "burn": {
            "id": new_burn.id,
            "income_id": new_burn.income_id,
            "category": new_burn.category,
            "amount": str(new_burn.amount),
            "description": new_burn.description,
            "burn_date": str(new_burn.burn_date)
        }
    }), 201

@burn_bp.route('/total_burn/<string:user_id>', methods=['GET'])
def get_burns(user_id):
    try:
        # Get salary cycle start and end
        today = datetime.today()
        start_date, end_date = get_salary_cycle(today)

        # Get all incomes for this user
        income = (
            db.session.query(Income)
            .filter(Income.user_id == user_id)
            .first()
        )

        if not income:
            return jsonify({"error": "No income record found for user"}), 404

        burn_pool = float(income.burn_pool) if income.burn_pool else 0.0

        # Get burns in the cycle
        burns = (
            db.session.query(Burn)
            .join(Income, Burn.income_id == Income.id)
            .filter(
                Income.user_id == user_id,
                Burn.burn_date >= start_date,
                Burn.burn_date <= end_date
            )
            .order_by(Burn.burn_date.desc())
            .all()
        )

        # Calculate total burn in the cycle
        total_burn = (
            db.session.query(func.coalesce(func.sum(Burn.amount), 0))
            .join(Income, Burn.income_id == Income.id)
            .filter(
                Income.user_id == user_id,
                Burn.burn_date >= start_date,
                Burn.burn_date <= end_date
            )
            .scalar()
        )

        burn_remainder = burn_pool - float(total_burn or 0)

        burn_list = []
        for b in burns:
            burn_list.append({
                "id": b.id,
                "category": b.category,
                "amount": float(b.amount),
                "description": b.description,
                "burn_date": b.burn_date.isoformat() if b.burn_date else None
            })

        return jsonify({
            "burns": burn_list,
            "burn_pool": burn_pool,
            "burn_remainder": burn_remainder
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@burn_bp.route('/update_burn/<string:id>', methods=['PUT'])
def update_burn(id):
    data = request.json
    try:
        burn = Burn.query.get(id)
        if not burn:
            return jsonify({"error": "Burn record not found"}), 404

        category = data.get("category")
        amount = data.get("amount")
        description = data.get("description")
        burn_date = data.get("burn_date")  # optional, ISO format

        if category:
            burn.category = category
        if amount:
            burn.amount = amount
        if description:
            burn.description = description
        if burn_date:
            try:
                burn.burn_date = datetime.fromisoformat(burn_date)
            except ValueError:
                return jsonify({"error": "Invalid date format, use ISO format (YYYY-MM-DD)"}), 400

        db.session.commit()

        return jsonify({
            "message": "Burn record updated successfully",
            "burn": {
                "id": burn.id,
                "income_id": burn.income_id,
                "category": burn.category,
                "amount": str(burn.amount),
                "description": burn.description,
                "burn_date": burn.burn_date.isoformat() if burn.burn_date else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
