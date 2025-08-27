from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app.models import *
from app.views.utils import get_salary_cycle, get_available_to_invest

invest_bp = Blueprint('invest', __name__)

@invest_bp.route('/add_invest', methods=['POST'])
def add_invest():
    data = request.json
    user_id = data.get("user_id")
    amount = data.get("amount")
    category = data.get("category")
    description = data.get("description")
    is_done = data.get("is_done", False)
    is_recurring = data.get("is_recurring", False)
    invest_date = data.get("invest_date")

    if not user_id or not amount or not category:
        return jsonify({"error": "Missing required fields"}), 400

    income, available_to_invest, _ = get_available_to_invest(user_id)
    if not income:
        return jsonify({"error": "No income found for current salary cycle"}), 400

    if float(amount) > available_to_invest:
        return jsonify({
            "error": "Insufficient invest pool",
            "available_to_invest": available_to_invest
        }), 400

    today = datetime.today()
    new_invest = Invest(
        income_id=income.id,
        category=category,
        amount=amount,
        description=description,
        is_done=is_done,
        is_recurring=is_recurring,
        invest_date=datetime.fromisoformat(invest_date).date() if invest_date else today.date()
    )

    db.session.add(new_invest)
    db.session.commit()

    return jsonify({
        "message": "Investment added successfully",
        "invest": {
            "id": new_invest.id,
            "income_id": new_invest.income_id,
            "category": new_invest.category,
            "amount": str(new_invest.amount),
            "description": new_invest.description,
            "is_done": new_invest.is_done,
            "is_recurring": new_invest.is_recurring,
            "photo_url": new_invest.photo_url,
            "invest_date": str(new_invest.invest_date),
            "created_at": str(new_invest.created_at)
        },
        "available_to_invest": available_to_invest - float(amount)
    }), 201


@invest_bp.route('/edit_invest/<string:invest_id>', methods=['PUT'])
def edit_invest(invest_id):
    data = request.json

    try:
        invest = Invest.query.get(invest_id)
        if not invest:
            return jsonify({"error": "Investment record not found"}), 404

        user_id = invest.income.user_id  # get user from linked income
        new_amount = data.get("amount", invest.amount)

        income, available_to_invest, _ = get_available_to_invest(user_id)
        if not income:
            return jsonify({"error": "No income found for current salary cycle"}), 400

        # Adjust available_to_invest to include current investment amount
        adjusted_available = available_to_invest + float(invest.amount)
        if float(new_amount) > adjusted_available:
            return jsonify({
                "error": "Insufficient invest pool",
                "available_to_invest": adjusted_available
            }), 400

        category = data.get("category")
        description = data.get("description")
        is_done = data.get("is_done")
        is_recurring = data.get("is_recurring")
        photo_url = data.get("photo_url")
        invest_date = data.get("invest_date")

        if category:
            invest.category = category
        if new_amount:
            invest.amount = new_amount
        if description:
            invest.description = description
        if is_done is not None:
            invest.is_done = is_done
        if is_recurring is not None:
            invest.is_recurring = is_recurring
        if photo_url:
            invest.photo_url = photo_url
        if invest_date:
            try:
                invest.invest_date = datetime.fromisoformat(invest_date).date()
            except ValueError:
                return jsonify({"error": "Invalid date format, use ISO format (YYYY-MM-DD)"}), 400

        db.session.commit()

        return jsonify({
            "message": "Investment updated successfully",
            "invest": {
                "id": invest.id,
                "income_id": invest.income_id,
                "category": invest.category,
                "amount": str(invest.amount),
                "description": invest.description,
                "is_done": invest.is_done,
                "is_recurring": invest.is_recurring,
                "photo_url": invest.photo_url,
                "invest_date": str(invest.invest_date),
                "created_at": str(invest.created_at)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@invest_bp.route('/total_invest/<string:user_id>', methods=['GET'])
def total_invest(user_id):
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

        invest_pool = float(income.invest_pool) if income.invest_pool else 0.0

        # Get invest in the cycle
        invests = (
            db.session.query(Invest)
            .join(Income, Invest.income_id == Income.id)
            .filter(
                Income.user_id == user_id,
                Invest.invest_date >= start_date,
                Invest.invest_date <= end_date
            )
            .order_by(Invest.invest_date.desc())
            .all()
        )

        # Calculate total burn in the cycle
        total_invest = (
            db.session.query(func.coalesce(func.sum(Invest.amount), 0))
            .join(Income, Invest.income_id == Income.id)
            .filter(
                Income.user_id == user_id,
                Invest.invest_date >= start_date,
                Invest.invest_date <= end_date
            )
            .scalar()
        )

        invest_remainder = invest_pool - float(total_invest or 0)

        invest_list = []
        for b in invests:
            invest_list.append({
                "id": b.id,
                "category": b.category,
                "amount": float(b.amount),
                "description": b.description,
                "invest_date": b.invest_date.isoformat() if b.invest_date else None
            })

        return jsonify({
            "invests": invest_list,
            "invest_pool": invest_pool,
            "invest_remainder": invest_remainder
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

