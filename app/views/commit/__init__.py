from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.models import *
from app.views.utils import get_salary_cycle


commit_bp = Blueprint('commit', __name__)

def get_available_to_commit(user_id):
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

    commit_pool = float(income.commit_pool) if income.commit_pool else 0.0

    total_committed = (
        db.session.query(func.coalesce(func.sum(Commitment.amount), 0))
        .filter(
            Commitment.income_id == income.id,
            Commitment.commit_date >= start_date,
            Commitment.commit_date <= end_date
        )
        .scalar()
    )

    available_to_commit = commit_pool - float(total_committed or 0)
    return income, available_to_commit, (start_date, end_date)


@commit_bp.route('/add_commit', methods=['POST'])
def add_commitment():
    data = request.json
    user_id = data.get("user_id")
    amount = data.get("amount")
    category = data.get("category")
    description = data.get("description")
    is_done = data.get("is_done", False)
    is_recurring = data.get("is_recurring", False)
    commit_date = data.get("commit_date")

    if not user_id or not amount or not category:
        return jsonify({"error": "Missing required fields"}), 400

    income, available_to_commit, _ = get_available_to_commit(user_id)
    if not income:
        return jsonify({"error": "No income found for current salary cycle"}), 400

    if float(amount) > available_to_commit:
        return jsonify({
            "error": "Insufficient commit pool",
            "available_to_commit": available_to_commit
        }), 400

    today = datetime.today()
    new_commit = Commitment(
        income_id=income.id,
        category=category,
        amount=amount,
        description=description,
        is_done=is_done,
        is_recurring=is_recurring,
        commit_date=datetime.fromisoformat(commit_date).date() if commit_date else today.date()
    )

    db.session.add(new_commit)
    db.session.commit()

    return jsonify({
        "message": "Commitment added successfully",
        "commitment": {
            "id": new_commit.id,
            "income_id": new_commit.income_id,
            "category": new_commit.category,
            "amount": str(new_commit.amount),
            "description": new_commit.description,
            "is_done": new_commit.is_done,
            "is_recurring": new_commit.is_recurring,
            "photo_url": new_commit.photo_url,
            "commit_date": str(new_commit.commit_date),
            "created_at": str(new_commit.created_at)
        },
        "available_to_commit": available_to_commit - float(amount)
    }), 201


@commit_bp.route('/edit_commit/<string:commit_id>', methods=['PUT'])
def edit_commitment(commit_id):
    data = request.json

    try:
        commit = Commitment.query.get(commit_id)
        if not commit:
            return jsonify({"error": "Commitment record not found"}), 404

        user_id = commit.income.user_id
        new_amount = data.get("amount", commit.amount)

        income, available_to_commit, _ = get_available_to_commit(user_id)
        if not income:
            return jsonify({"error": "No income found for current salary cycle"}), 400

        adjusted_available = available_to_commit + float(commit.amount)
        if float(new_amount) > adjusted_available:
            return jsonify({
                "error": "Insufficient commit pool",
                "available_to_commit": adjusted_available
            }), 400

        category = data.get("category")
        description = data.get("description")
        is_done = data.get("is_done")
        is_recurring = data.get("is_recurring")
        photo_url = data.get("photo_url")
        commit_date = data.get("commit_date")

        if category:
            commit.category = category
        if new_amount:
            commit.amount = new_amount
        if description:
            commit.description = description
        if is_done is not None:
            commit.is_done = is_done
        if is_recurring is not None:
            commit.is_recurring = is_recurring
        if photo_url:
            commit.photo_url = photo_url
        if commit_date:
            try:
                commit.commit_date = datetime.fromisoformat(commit_date).date()
            except ValueError:
                return jsonify({"error": "Invalid date format, use ISO format (YYYY-MM-DD)"}), 400

        db.session.commit()

        return jsonify({
            "message": "Commitment updated successfully",
            "commitment": {
                "id": commit.id,
                "income_id": commit.income_id,
                "category": commit.category,
                "amount": str(commit.amount),
                "description": commit.description,
                "is_done": commit.is_done,
                "is_recurring": commit.is_recurring,
                "photo_url": commit.photo_url,
                "commit_date": str(commit.commit_date),
                "created_at": str(commit.created_at)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@commit_bp.route('/total_commit/<string:user_id>', methods=['GET'])
def total_commit(user_id):
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

        commit_pool = float(income.commit_pool) if income.commit_pool else 0.0

        # Get commit in the cycle
        commits = (
            db.session.query(Commitment)
            .join(Income, Commitment.income_id == Income.id)
            .filter(
                Income.user_id == user_id,
                Commitment.commit_date >= start_date,
                Commitment.commit_date <= end_date
            )
            .order_by(Commitment.commit_date.desc())
            .all()
        )

        # Calculate total commit in the cycle
        total_commit = (
            db.session.query(func.coalesce(func.sum(Commitment.amount), 0))
            .join(Income, Commitment.income_id == Income.id)
            .filter(
                Income.user_id == user_id,
                Commitment.commit_date >= start_date,
                Commitment.commit_date <= end_date
            )
            .scalar()
        )

        commit_remainder = commit_pool - float(total_commit or 0)

        commit_list = []
        for b in commits:
            commit_list.append({
                "id": b.id,
                "category": b.category,
                "amount": float(b.amount),
                "description": b.description,
                "commit_date": b.commit_date.isoformat() if b.commit_date else None
            })

        return jsonify({
            "commits": commit_list,
            "commit_pool": commit_pool,
            "commit_remainder": commit_remainder
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
