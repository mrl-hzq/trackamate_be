from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, or_, case
from app.models import Note, Burn, Invest, Commitment, User
from app import db
from app.schemas.note_schema import NoteSchema
from app.views.utils import get_salary_cycle
from datetime import datetime, timedelta, date
from marshmallow import ValidationError

note_bp = Blueprint('note', __name__)
note_schema = NoteSchema()
notes_schema = NoteSchema(many=True)

def calculate_next_due_date(current_date, interval_days):
    """Helper function to calculate next due date"""
    if not interval_days or interval_days < 1:
        return None
    return current_date + timedelta(days=interval_days)

def validate_notification_fields(notification_enabled, notification_type, notification_datetime,
                                notification_minutes_before, next_due_date):
    """
    Helper function to validate notification field combinations
    Returns: (is_valid, error_message)
    """
    if not notification_enabled:
        return True, None

    if not notification_type:
        return False, "notification_type must be either 'specific' or 'relative' when notification_enabled is True"

    if notification_type not in ['specific', 'relative']:
        return False, "notification_type must be 'specific' or 'relative'"

    if notification_type == 'specific':
        if not notification_datetime:
            return False, "notification_datetime is required when notification_type is 'specific'"

    elif notification_type == 'relative':
        if notification_minutes_before is None:
            return False, "notification_minutes_before is required when notification_type is 'relative'"
        if int(notification_minutes_before) <= 0:
            return False, "notification_minutes_before must be greater than 0"
        if not next_due_date:
            return False, "Cannot set relative notification without a due date"

    return True, None

@note_bp.route('/add_note', methods=['POST'])
@jwt_required()
def add_note():
    try:
        data = request.get_json()

        # Validate required fields
        user_id = data.get('user_id')
        title = data.get('title')
        content = data.get('content')
        note_type = data.get('note_type')

        if not all([user_id, title, content, note_type]):
            return jsonify({"error": "Missing required fields: user_id, title, content, note_type"}), 400

        if note_type not in ['one-time', 'recurring']:
            return jsonify({"error": "note_type must be 'one-time' or 'recurring'"}), 400

        # Validate recurrence interval for recurring notes
        recurrence_interval_days = data.get('recurrence_interval_days')
        if note_type == 'recurring':
            if not recurrence_interval_days or int(recurrence_interval_days) < 1:
                return jsonify({"error": "recurrence_interval_days must be at least 1 for recurring notes"}), 400
            recurrence_interval_days = int(recurrence_interval_days)

        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Verify linked financial records exist if provided
        burn_id = data.get('burn_id')
        invest_id = data.get('invest_id')
        commitment_id = data.get('commitment_id')

        if burn_id and not Burn.query.get(burn_id):
            return jsonify({"error": "Burn record not found"}), 404
        if invest_id and not Invest.query.get(invest_id):
            return jsonify({"error": "Invest record not found"}), 404
        if commitment_id and not Commitment.query.get(commitment_id):
            return jsonify({"error": "Commitment record not found"}), 404

        # Calculate next_due_date for recurring notes
        next_due_date = None
        if note_type == 'recurring':
            next_due_date = calculate_next_due_date(date.today(), recurrence_interval_days)

        # Handle notification fields
        notification_enabled = data.get('notification_enabled', False)
        notification_type = data.get('notification_type')
        notification_datetime = data.get('notification_datetime')
        notification_minutes_before = data.get('notification_minutes_before')

        # Validate notification fields
        if notification_enabled:
            if not notification_type:
                return jsonify({"error": "notification_type must be either 'specific' or 'relative' when notification_enabled is True"}), 400

            if notification_type not in ['specific', 'relative']:
                return jsonify({"error": "notification_type must be 'specific' or 'relative'"}), 400

            if notification_type == 'specific':
                if not notification_datetime:
                    return jsonify({"error": "notification_datetime is required when notification_type is 'specific'"}), 400
                # Parse datetime string to datetime object
                try:
                    notification_datetime = datetime.fromisoformat(notification_datetime.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return jsonify({"error": "Invalid notification_datetime format. Use ISO 8601 format"}), 400

            elif notification_type == 'relative':
                if notification_minutes_before is None:
                    return jsonify({"error": "notification_minutes_before is required when notification_type is 'relative'"}), 400
                if int(notification_minutes_before) <= 0:
                    return jsonify({"error": "notification_minutes_before must be greater than 0"}), 400
                if not next_due_date:
                    return jsonify({"error": "Cannot set relative notification without a due date"}), 400
                notification_minutes_before = int(notification_minutes_before)

        # Create new note
        new_note = Note(
            user_id=user_id,
            title=title,
            content=content,
            category=data.get('category'),
            note_type=note_type,
            recurrence_interval_days=recurrence_interval_days,
            next_due_date=next_due_date,
            burn_id=burn_id,
            invest_id=invest_id,
            commitment_id=commitment_id,
            is_done=False,
            notification_enabled=notification_enabled,
            notification_type=notification_type if notification_enabled else None,
            notification_datetime=notification_datetime if notification_enabled and notification_type == 'specific' else None,
            notification_minutes_before=notification_minutes_before if notification_enabled and notification_type == 'relative' else None
        )

        db.session.add(new_note)
        db.session.commit()

        return jsonify({
            "message": "Note created successfully",
            "note": note_schema.dump(new_note)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create note: {str(e)}"}), 500

@note_bp.route('/get_note/<string:note_id>', methods=['GET'])
@jwt_required()
def get_note(note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    return jsonify(note_schema.dump(note)), 200

@note_bp.route('/get_notes/<string:user_id>', methods=['GET'])
@jwt_required()
def get_notes(user_id):
    # Verify user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get all notes sorted by next_due_date (nulls last), then created_at descending
    # MySQL doesn't support NULLS LAST, so we use CASE to put NULLs at the end
    notes = Note.query.filter_by(user_id=user_id)\
        .order_by(
            case((Note.next_due_date.is_(None), 1), else_=0),
            Note.next_due_date.asc(),
            Note.created_at.desc()
        ).all()

    return jsonify(notes_schema.dump(notes)), 200

@note_bp.route('/get_notes_by_cycle/<string:user_id>', methods=['GET'])
@jwt_required()
def get_notes_by_cycle(user_id):
    # Verify user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get date range from query params
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Missing start_date or end_date query parameters"}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Get notes created within the cycle
    notes = Note.query.filter(
        Note.user_id == user_id,
        Note.created_at >= start_date,
        Note.created_at <= end_date
    ).order_by(
        case((Note.next_due_date.is_(None), 1), else_=0),
        Note.next_due_date.asc(),
        Note.created_at.desc()
    ).all()

    return jsonify(notes_schema.dump(notes)), 200

@note_bp.route('/get_notes_by_category/<string:user_id>/<string:category>', methods=['GET'])
@jwt_required()
def get_notes_by_category(user_id, category):
    # Verify user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    notes = Note.query.filter_by(user_id=user_id, category=category)\
        .order_by(
            case((Note.next_due_date.is_(None), 1), else_=0),
            Note.next_due_date.asc(),
            Note.created_at.desc()
        ).all()

    return jsonify(notes_schema.dump(notes)), 200

@note_bp.route('/update_note/<string:note_id>', methods=['PUT'])
@jwt_required()
def update_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        data = request.get_json()

        # Update allowed fields
        if 'title' in data:
            note.title = data['title']
        if 'content' in data:
            note.content = data['content']
        if 'category' in data:
            note.category = data['category']
        if 'note_type' in data:
            if data['note_type'] not in ['one-time', 'recurring']:
                return jsonify({"error": "note_type must be 'one-time' or 'recurring'"}), 400
            note.note_type = data['note_type']

        # Handle recurrence interval changes
        if 'recurrence_interval_days' in data:
            if note.note_type == 'recurring':
                interval = int(data['recurrence_interval_days'])
                if interval < 1:
                    return jsonify({"error": "recurrence_interval_days must be at least 1"}), 400
                note.recurrence_interval_days = interval
                # Recalculate next_due_date if needed
                if note.last_reset_date:
                    note.next_due_date = calculate_next_due_date(note.last_reset_date, interval)
                else:
                    note.next_due_date = calculate_next_due_date(date.today(), interval)
            else:
                note.recurrence_interval_days = None
                note.next_due_date = None

        # Update financial links
        if 'burn_id' in data:
            if data['burn_id'] and not Burn.query.get(data['burn_id']):
                return jsonify({"error": "Burn record not found"}), 404
            note.burn_id = data['burn_id']

        if 'invest_id' in data:
            if data['invest_id'] and not Invest.query.get(data['invest_id']):
                return jsonify({"error": "Invest record not found"}), 404
            note.invest_id = data['invest_id']

        if 'commitment_id' in data:
            if data['commitment_id'] and not Commitment.query.get(data['commitment_id']):
                return jsonify({"error": "Commitment record not found"}), 404
            note.commitment_id = data['commitment_id']

        # Handle notification field updates
        if 'notification_enabled' in data:
            notification_enabled = data['notification_enabled']
            note.notification_enabled = notification_enabled

            # If disabling notifications, clear all notification fields
            if not notification_enabled:
                note.notification_type = None
                note.notification_datetime = None
                note.notification_minutes_before = None
            else:
                # If enabling notifications, validate required fields
                notification_type = data.get('notification_type', note.notification_type)

                if not notification_type:
                    return jsonify({"error": "notification_type must be either 'specific' or 'relative' when notification_enabled is True"}), 400

                if notification_type not in ['specific', 'relative']:
                    return jsonify({"error": "notification_type must be 'specific' or 'relative'"}), 400

                note.notification_type = notification_type

                if notification_type == 'specific':
                    notification_datetime = data.get('notification_datetime', note.notification_datetime)
                    if not notification_datetime:
                        return jsonify({"error": "notification_datetime is required when notification_type is 'specific'"}), 400
                    # Parse datetime if it's a string
                    if isinstance(notification_datetime, str):
                        try:
                            notification_datetime = datetime.fromisoformat(notification_datetime.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            return jsonify({"error": "Invalid notification_datetime format. Use ISO 8601 format"}), 400
                    note.notification_datetime = notification_datetime
                    note.notification_minutes_before = None  # Clear relative field

                elif notification_type == 'relative':
                    notification_minutes_before = data.get('notification_minutes_before', note.notification_minutes_before)
                    if notification_minutes_before is None:
                        return jsonify({"error": "notification_minutes_before is required when notification_type is 'relative'"}), 400
                    if int(notification_minutes_before) <= 0:
                        return jsonify({"error": "notification_minutes_before must be greater than 0"}), 400
                    if not note.next_due_date:
                        return jsonify({"error": "Cannot set relative notification without a due date"}), 400
                    note.notification_minutes_before = int(notification_minutes_before)
                    note.notification_datetime = None  # Clear specific field

        # Allow updating individual notification fields if notification is already enabled
        elif note.notification_enabled:
            if 'notification_type' in data:
                notification_type = data['notification_type']
                if notification_type not in ['specific', 'relative']:
                    return jsonify({"error": "notification_type must be 'specific' or 'relative'"}), 400
                note.notification_type = notification_type

            if 'notification_datetime' in data:
                if note.notification_type == 'specific':
                    notification_datetime = data['notification_datetime']
                    if isinstance(notification_datetime, str):
                        try:
                            notification_datetime = datetime.fromisoformat(notification_datetime.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            return jsonify({"error": "Invalid notification_datetime format. Use ISO 8601 format"}), 400
                    note.notification_datetime = notification_datetime

            if 'notification_minutes_before' in data:
                if note.notification_type == 'relative':
                    notification_minutes_before = data['notification_minutes_before']
                    if int(notification_minutes_before) <= 0:
                        return jsonify({"error": "notification_minutes_before must be greater than 0"}), 400
                    if not note.next_due_date:
                        return jsonify({"error": "Cannot set relative notification without a due date"}), 400
                    note.notification_minutes_before = int(notification_minutes_before)

        note.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "message": "Note updated successfully",
            "note": note_schema.dump(note)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update note: {str(e)}"}), 500

@note_bp.route('/delete_note/<string:note_id>', methods=['DELETE'])
@jwt_required()
def delete_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        db.session.delete(note)
        db.session.commit()

        return jsonify({"message": "Note deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete note: {str(e)}"}), 500

@note_bp.route('/check_note/<string:note_id>', methods=['POST'])
@jwt_required()
def check_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        note.is_done = True
        note.done_date = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "message": "Note marked as done",
            "note": note_schema.dump(note)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to check note: {str(e)}"}), 500

@note_bp.route('/uncheck_note/<string:note_id>', methods=['POST'])
@jwt_required()
def uncheck_note(note_id):
    try:
        note = Note.query.get(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        note.is_done = False
        note.done_date = None
        db.session.commit()

        return jsonify({
            "message": "Note unmarked",
            "note": note_schema.dump(note)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to uncheck note: {str(e)}"}), 500

@note_bp.route('/get_pending_notes/<string:user_id>', methods=['GET'])
@jwt_required()
def get_pending_notes(user_id):
    # Verify user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get all unchecked notes
    notes = Note.query.filter_by(user_id=user_id, is_done=False)\
        .order_by(
            case((Note.next_due_date.is_(None), 1), else_=0),
            Note.next_due_date.asc(),
            Note.created_at.desc()
        ).all()

    return jsonify(notes_schema.dump(notes)), 200

@note_bp.route('/reset_notes/<string:user_id>', methods=['POST'])
@jwt_required()
def reset_notes(user_id):
    """
    Auto-reset recurring notes that are past their due date.
    This should be called by frontend on app load or daily.
    """
    try:
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        today = date.today()

        # Find all recurring notes that are:
        # 1. Belong to this user
        # 2. Are marked as done
        # 3. Have a next_due_date that is today or in the past
        notes_to_reset = Note.query.filter(
            Note.user_id == user_id,
            Note.note_type == 'recurring',
            Note.is_done == True,
            Note.next_due_date <= today
        ).all()

        reset_count = 0
        for note in notes_to_reset:
            # Reset the note
            note.is_done = False
            note.done_date = None
            note.last_reset_date = today

            # Calculate new next_due_date
            if note.recurrence_interval_days:
                note.next_due_date = calculate_next_due_date(today, note.recurrence_interval_days)

            reset_count += 1

        db.session.commit()

        return jsonify({
            "message": f"Successfully reset {reset_count} recurring note(s)",
            "reset_count": reset_count,
            "notes": notes_schema.dump(notes_to_reset)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to reset notes: {str(e)}"}), 500
