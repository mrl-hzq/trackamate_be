from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import func

from app.views.utils import get_salary_cycle, get_available_to_burn
from app.views.utils.file_upload import save_upload_file, delete_upload_file
from app.models import *
from datetime import datetime
import os

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

    # Handle file upload (optional)
    photo_url = None
    if file:
        photo_url = save_upload_file(file, 'burn')
        if not photo_url:
            return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp, pdf"}), 400

    new_burn = Burn(
        income_id=income.id,
        category=category,
        amount=amount,
        description=description,
        burn_date=burn_date,
        photo_url=photo_url
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
            "burn_date": str(new_burn.burn_date),
            "photo_url": new_burn.photo_url
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
                "burn_date": b.burn_date.isoformat() if b.burn_date else None,
                "photo_url": b.photo_url
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
        burn = Burn.query.get(id)
        if not burn:
            return jsonify({"error": "Burn record not found"}), 404

        user_id = burn.income.user_id  # get user from linked income
        new_amount = data.get("amount", burn.amount)

        income, available_to_burn, _ = get_available_to_burn(user_id)
        if not income:
            return jsonify({"error": "No income found for current salary cycle"}), 400

        # Adjust available_to_burn to include current burn amount
        adjusted_available = available_to_burn + float(burn.amount)
        if float(new_amount) > adjusted_available:
            return jsonify({
                "error": "Insufficient burn pool",
                "available_to_burn": adjusted_available
            }), 400

        category = data.get("category")
        description = data.get("description")
        burn_date = data.get("burn_date")

        if category:
            burn.category = category
        if new_amount:
            burn.amount = new_amount
        if description:
            burn.description = description
        if burn_date:
            try:
                burn.burn_date = datetime.fromisoformat(burn_date).date()
            except ValueError:
                return jsonify({"error": "Invalid date format, use ISO format (YYYY-MM-DD)"}), 400

        # Handle photo upload using utility function
        if file:
            # Delete old photo if exists
            if burn.photo_url:
                delete_upload_file(burn.photo_url)

            # Save new photo
            photo_url = save_upload_file(file, 'burn')
            if not photo_url:
                return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp, pdf"}), 400
            burn.photo_url = photo_url

        db.session.commit()

        return jsonify({
            "message": "Burn record updated successfully",
            "burn": {
                "id": burn.id,
                "income_id": burn.income_id,
                "category": burn.category,
                "amount": str(burn.amount),
                "description": burn.description,
                "photo_url": burn.photo_url,
                "burn_date": str(burn.burn_date),
                "created_at": str(burn.created_at)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@burn_bp.route('/delete_burn/<string:id>', methods=['DELETE'])
def delete_burn(id):
    try:
        burn = Burn.query.get(id)
        if not burn:
            return jsonify({"error": "Burn record not found"}), 404

        # Delete associated photo file if it exists
        if burn.photo_url:
            delete_upload_file(burn.photo_url)

        db.session.delete(burn)
        db.session.commit()

        return jsonify({
            "message": "Burn record deleted successfully",
            "burn_id": id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@burn_bp.route('/get_burn/<string:id>', methods=['GET'])
def get_burn(id):
    """Get a single burn record by ID with photo URL"""
    try:
        burn = Burn.query.get(id)
        if not burn:
            return jsonify({"error": "Burn record not found"}), 404

        return jsonify({
            "burn": {
                "id": burn.id,
                "income_id": burn.income_id,
                "category": burn.category,
                "amount": float(burn.amount),
                "description": burn.description,
                "burn_date": burn.burn_date.isoformat() if burn.burn_date else None,
                "photo_url": burn.photo_url,
                "created_at": burn.created_at.isoformat() if burn.created_at else None
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@burn_bp.route('/get_burn_image/<string:id>', methods=['GET'])
def get_burn_image(id):
    """Get the actual image file for a burn record"""
    try:
        burn = Burn.query.get(id)
        if not burn:
            return jsonify({"error": "Burn record not found"}), 404

        if not burn.photo_url:
            return jsonify({"error": "No image attached to this burn"}), 404

        # Build full file path
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), burn.photo_url)

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

@burn_bp.route('/get_burns_by_cycle/<string:user_id>', methods=['GET'])
def get_burns_by_cycle(user_id):
    """Get all burns for a specific date range (cycle)"""
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

        # Get burns in the specified date range
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

        burn_list = []
        for b in burns:
            burn_list.append({
                "id": b.id,
                "category": b.category,
                "amount": float(b.amount),
                "description": b.description,
                "burn_date": b.burn_date.isoformat() if b.burn_date else None,
                "photo_url": b.photo_url
            })

        return jsonify({
            "burns": burn_list,
            "cycle_start": start_date_str,
            "cycle_end": end_date_str
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
