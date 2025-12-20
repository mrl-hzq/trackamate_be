from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import func
from app.models import *
from app.views.utils import get_salary_cycle, get_available_to_invest
from app.views.utils.file_upload import save_upload_file, delete_upload_file
import os

invest_bp = Blueprint('invest', __name__)

@invest_bp.route('/add_invest', methods=['POST'])
def add_invest():
    # Check if request has form data (multipart/form-data) or JSON
    try:
        if request.files or (request.content_type and 'multipart/form-data' in request.content_type):
            # Handle multipart/form-data (with or without file)
            data = request.form
            file = request.files.get('photo')
        else:
            # Handle JSON
            data = request.get_json(force=True, silent=True)
            file = None

            if not data:
                return jsonify({"error": "Invalid request format. Send JSON or multipart/form-data"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse request: {str(e)}"}), 400

    user_id = data.get("user_id")
    amount = data.get("amount")
    category = data.get("category")
    description = data.get("description")

    # Convert string booleans to actual booleans (for form data)
    is_done_raw = data.get("is_done", False)
    is_recurring_raw = data.get("is_recurring", False)

    # Handle string 'true'/'false' from form data or actual booleans from JSON
    if isinstance(is_done_raw, str):
        is_done = is_done_raw.lower() in ('true', '1', 'yes')
    else:
        is_done = bool(is_done_raw)

    if isinstance(is_recurring_raw, str):
        is_recurring = is_recurring_raw.lower() in ('true', '1', 'yes')
    else:
        is_recurring = bool(is_recurring_raw)

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

    # Handle file upload (optional)
    photo_url = None
    if file:
        photo_url = save_upload_file(file, 'invest')
        if not photo_url:
            return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp, pdf"}), 400

    today = datetime.today()
    new_invest = Invest(
        income_id=income.id,
        category=category,
        amount=amount,
        description=description,
        is_done=is_done,
        is_recurring=is_recurring,
        invest_date=datetime.fromisoformat(invest_date).date() if invest_date else today.date(),
        photo_url=photo_url
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
    # Check if request contains files (FormData) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle FormData (with photo)
        data = request.form
        file = request.files.get('photo')
    else:
        # Handle JSON (no photo)
        data = request.json if request.json else request.form
        file = None

    try:
        invest = Invest.query.get(invest_id)
        if not invest:
            return jsonify({"error": "Investment record not found"}), 404

        user_id = invest.income.user_id
        new_amount = data.get("amount", invest.amount)

        income, available_to_invest, _ = get_available_to_invest(user_id)
        if not income:
            return jsonify({"error": "No income found for current salary cycle"}), 400

        adjusted_available = available_to_invest + float(invest.amount)
        if float(new_amount) > adjusted_available:
            return jsonify({
                "error": "Insufficient invest pool",
                "available_to_invest": adjusted_available
            }), 400

        # Update fields
        category = data.get("category")
        description = data.get("description")

        # Handle boolean fields from FormData (string) or JSON (boolean)
        is_done = data.get("is_done")
        if isinstance(is_done, str):
            is_done = is_done.lower() in ['true', '1']

        is_recurring = data.get("is_recurring")
        if isinstance(is_recurring, str):
            is_recurring = is_recurring.lower() in ['true', '1']

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
        if invest_date:
            try:
                invest.invest_date = datetime.fromisoformat(invest_date).date()
            except ValueError:
                return jsonify({"error": "Invalid date format, use ISO format (YYYY-MM-DD)"}), 400

        # Handle photo upload using utility function
        if file:
            # Delete old photo if exists
            if invest.photo_url:
                delete_upload_file(invest.photo_url)

            # Save new photo
            photo_url = save_upload_file(file, 'invest')
            if not photo_url:
                return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp, pdf"}), 400
            invest.photo_url = photo_url

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

@invest_bp.route('/delete_invest/<string:invest_id>', methods=['DELETE'])
def delete_invest(invest_id):
    try:
        invest = Invest.query.get(invest_id)
        if not invest:
            return jsonify({"error": "Investment record not found"}), 404

        # Delete associated photo file if it exists
        if invest.photo_url:
            delete_upload_file(invest.photo_url)

        db.session.delete(invest)
        db.session.commit()

        return jsonify({
            "message": "Investment deleted successfully",
            "invest_id": invest_id
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
                "invest_date": b.invest_date.isoformat() if b.invest_date else None,
                "photo_url": b.photo_url,
                "is_done": b.is_done,
                "is_recurring": b.is_recurring
            })
        return jsonify({
            "invests": invest_list,
            "invest_pool": invest_pool,
            "invest_remainder": invest_remainder
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invest_bp.route('/get_invest/<string:invest_id>', methods=['GET'])
def get_invest(invest_id):
    """Get a single invest record by ID with photo URL"""
    try:
        invest = Invest.query.get(invest_id)
        if not invest:
            return jsonify({"error": "Investment record not found"}), 404

        return jsonify({
            "invest": {
                "id": invest.id,
                "income_id": invest.income_id,
                "category": invest.category,
                "amount": float(invest.amount),
                "description": invest.description,
                "invest_date": invest.invest_date.isoformat() if invest.invest_date else None,
                "photo_url": invest.photo_url,
                "is_done": invest.is_done,
                "is_recurring": invest.is_recurring,
                "created_at": invest.created_at.isoformat() if invest.created_at else None
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invest_bp.route('/get_invest_image/<string:invest_id>', methods=['GET'])
def get_invest_image(invest_id):
    """Get the actual image file for an investment record"""
    try:
        invest = Invest.query.get(invest_id)
        if not invest:
            return jsonify({"error": "Investment record not found"}), 404

        if not invest.photo_url:
            return jsonify({"error": "No image attached to this investment"}), 404

        # Build full file path
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                                 invest.photo_url)

        if not os.path.exists(file_path):
            return jsonify({"error": "Image file not found on server"}), 404

        # Return the actual image file with no-cache headers
        response = send_file(file_path, mimetype='image/jpeg')

        # CRITICAL FIX: Disable caching to prevent 304 responses
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invest_bp.route('/get_invests_by_cycle/<string:user_id>', methods=['GET'])
def get_invests_by_cycle(user_id):
    """Get all investments for a specific date range (cycle)"""
    try:
        # Get query parameters for date range
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({"error": "start_date and end_date query parameters are required"}), 400

        try:
            start_date = datetime.fromisoformat(start_date_str).date()
            end_date = datetime.fromisoformat(end_date_str).date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Get invests in the specified date range
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

        invest_list = []
        for i in invests:
            invest_list.append({
                "id": i.id,
                "category": i.category,
                "amount": float(i.amount),
                "description": i.description,
                "invest_date": i.invest_date.isoformat() if i.invest_date else None,
                "photo_url": i.photo_url,
                "is_done": i.is_done,
                "is_recurring": i.is_recurring
            })

        return jsonify({
            "invests": invest_list,
            "cycle_start": start_date_str,
            "cycle_end": end_date_str
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
