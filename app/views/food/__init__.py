from flask import Blueprint, request, jsonify
from app.models import *
from app import db
from decimal import Decimal

from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

food_bp = Blueprint('food', __name__)

# Add expense
@food_bp.route('/add_food_expenses', methods=['POST'])
def add_food_expense():
    data = request.json
    try:
        expense = FoodExpense(
            user_id=data['user_id'],
            date=datetime.strptime(data['date'], "%Y-%m-%d").date(),
            amount=Decimal(str(data['amount'])),
            description=data.get('description', '')
        )
        db.session.add(expense)
        db.session.commit()
        return jsonify({"message": "Expense added successfully", "id": expense.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

# Fetch expenses (optional date range)
@food_bp.route('/get_food_expenses', methods=['GET'])
def get_food_expenses():
    user_id = request.args.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = FoodExpense.query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(FoodExpense.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(FoodExpense.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    expenses = query.order_by(FoodExpense.date.desc()).all()
    return jsonify([
        {
            "id": e.id,
            "date": e.date.strftime("%Y-%m-%d"),
            "amount": float(e.amount),
            "description": e.description
        } for e in expenses
    ])

# Delete expense
@food_bp.route('/delete_food_expenses/<expense_id>', methods=['DELETE'])
def delete_food_expense(expense_id):
    expense = FoodExpense.query.get(expense_id)
    if not expense:
        return jsonify({"error": "Expense not found"}), 404
    try:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"message": "Expense deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
