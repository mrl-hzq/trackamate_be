from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import func

from app.models import *
from app.views.utils import get_salary_cycle
from app.views.utils.file_upload import save_upload_file, delete_upload_file
import os


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

    print(data)
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

    # Handle file upload (optional)
    photo_url = None
    if file:
        photo_url = save_upload_file(file, 'commit')
        if not photo_url:
            return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp, pdf"}), 400

    today = datetime.today()
    new_commit = Commitment(
        income_id=income.id,
        category=category,
        amount=amount,
        description=description,
        is_done=is_done,
        is_recurring=is_recurring,
        commit_date=datetime.fromisoformat(commit_date).date() if commit_date else today.date(),
        photo_url=photo_url
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

        # Handle boolean fields from FormData (string) or JSON (boolean)
        is_done = data.get("is_done")
        if isinstance(is_done, str):
            is_done = is_done.lower() in ['true', '1']

        is_recurring = data.get("is_recurring")
        if isinstance(is_recurring, str):
            is_recurring = is_recurring.lower() in ['true', '1']

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
        if commit_date:
            try:
                commit.commit_date = datetime.fromisoformat(commit_date).date()
            except ValueError:
                return jsonify({"error": "Invalid date format, use ISO format (YYYY-MM-DD)"}), 400

        # Handle photo upload using utility function
        if file:
            # Delete old photo if exists
            if commit.photo_url:
                delete_upload_file(commit.photo_url)

            # Save new photo
            photo_url = save_upload_file(file, 'commit')
            if not photo_url:
                return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp, pdf"}), 400
            commit.photo_url = photo_url

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

@commit_bp.route('/delete_commit/<string:commit_id>', methods=['DELETE'])
def delete_commitment(commit_id):
    try:
        commit = Commitment.query.get(commit_id)
        if not commit:
            return jsonify({"error": "Commitment record not found"}), 404

        # Delete associated photo file if it exists
        if commit.photo_url:
            delete_upload_file(commit.photo_url)

        db.session.delete(commit)
        db.session.commit()

        return jsonify({
            "message": "Commitment deleted successfully",
            "commitment_id": commit_id
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
                "commit_date": b.commit_date.isoformat() if b.commit_date else None,
                "photo_url": b.photo_url,
                "is_done": b.is_done,
                "is_recurring": b.is_recurring
            })

        return jsonify({
            "commits": commit_list,
            "commit_pool": commit_pool,
            "commit_remainder": commit_remainder
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@commit_bp.route('/get_commit/<string:commit_id>', methods=['GET'])
def get_commitment(commit_id):
    """Get a single commitment record by ID with photo URL"""
    try:
        commit = Commitment.query.get(commit_id)
        if not commit:
            return jsonify({"error": "Commitment record not found"}), 404

        return jsonify({
            "commitment": {
                "id": commit.id,
                "income_id": commit.income_id,
                "category": commit.category,
                "amount": float(commit.amount),
                "description": commit.description,
                "commit_date": commit.commit_date.isoformat() if commit.commit_date else None,
                "photo_url": commit.photo_url,
                "is_done": commit.is_done,
                "is_recurring": commit.is_recurring,
                "created_at": commit.created_at.isoformat() if commit.created_at else None
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@commit_bp.route('/get_commit_image/<string:commit_id>', methods=['GET'])
def get_commit_image(commit_id):
    """Get the actual image file for a commitment record"""
    try:
        commit = Commitment.query.get(commit_id)
        if not commit:
            return jsonify({"error": "Commitment record not found"}), 404

        if not commit.photo_url:
            return jsonify({"error": "No image attached to this commitment"}), 404

        # Build full file path
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), commit.photo_url)

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

@commit_bp.route('/get_commits_by_cycle/<string:user_id>', methods=['GET'])
def get_commits_by_cycle(user_id):
    """Get all commitments for a specific date range (cycle)"""
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

        # Get commits in the specified date range
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

        commit_list = []
        for c in commits:
            commit_list.append({
                "id": c.id,
                "category": c.category,
                "amount": float(c.amount),
                "description": c.description,
                "commit_date": c.commit_date.isoformat() if c.commit_date else None,
                "photo_url": c.photo_url,
                "is_done": c.is_done,
                "is_recurring": c.is_recurring
            })

        return jsonify({
            "commits": commit_list,
            "cycle_start": start_date_str,
            "cycle_end": end_date_str
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
