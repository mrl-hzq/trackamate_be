from flask import Blueprint, request, jsonify, send_file
from app.models import *
from app import db
from decimal import Decimal
from sqlalchemy import desc
from openai import OpenAI, OpenAIError
import os
import base64
import json
from werkzeug.utils import secure_filename
import uuid as uuid_lib
from app.views.utils.file_upload import save_upload_file, delete_upload_file

from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

food_bp = Blueprint('food', __name__)

# Initialize OpenAI client
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("WARNING: OPENAI_API_KEY not found in environment variables!")
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"ERROR: Failed to initialize OpenAI client: {e}")
    client = None

# Allowed file extensions for image uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@food_bp.route('/analyze_food', methods=['POST'])
def analyze_food():
    """
    Analyze food image using OpenAI Vision API
    Accepts: multipart/form-data with 'photo' file
    Returns: JSON with nutrition data
    """
    try:
        # Check if OpenAI client is initialized
        if client is None:
            return jsonify({"error": "OpenAI client not initialized. Check OPENAI_API_KEY in .env file"}), 500

        # Check if image was uploaded
        if 'photo' not in request.files:
            return jsonify({"error": "No photo uploaded"}), 400

        file = request.files['photo']

        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use JPG, PNG, or HEIC"}), 400

        # Read and encode image to base64
        image_data = file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')

        print(f"Image size: {len(image_data)} bytes")
        print(f"Base64 size: {len(base64_image)} characters")

        # Call OpenAI Vision API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this Malaysian/Asian food image and return nutrition data as JSON.

Use ASEAN Food Composition Database and Malaysia Ministry of Health guidelines when possible.

Return ONLY this exact JSON format:
{
  "food_name": "name of the main dish in English",
  "calories": total estimated calories in kcal (integer),
  "protein": total grams of protein (number with 1 decimal place),
  "carbohydrates": total grams of carbohydrates (number with 1 decimal place),
  "fat": total grams of fat (number with 1 decimal place)
}

If multiple food items are visible, sum up the total nutrition values.
Return ONLY valid JSON, no additional text or explanation."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        # Check if response has content
        if not response.choices or len(response.choices) == 0:
            return jsonify({"error": "No response from OpenAI API"}), 500

        message_content = response.choices[0].message.content

        if message_content is None:
            return jsonify({
                "error": "OpenAI returned empty response",
                "details": "The AI did not generate any content. Please try again."
            }), 500

        # Parse response
        nutrition_data = json.loads(message_content)

        # Validate required fields
        required_fields = ['food_name', 'calories', 'protein', 'carbohydrates', 'fat']
        for field in required_fields:
            if field not in nutrition_data:
                return jsonify({"error": f"AI response missing {field}"}), 500

        return jsonify({
            "success": True,
            "nutrition": {
                "food_name": nutrition_data['food_name'],
                "calories": int(nutrition_data['calories']),
                "protein": round(float(nutrition_data['protein']), 1),
                "carbohydrates": round(float(nutrition_data['carbohydrates']), 1),
                "fat": round(float(nutrition_data['fat']), 1)
            }
        }), 200

    except OpenAIError as e:
        return jsonify({
            "error": "OpenAI API error",
            "details": str(e)
        }), 500
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "Failed to parse AI response as JSON",
            "raw_response": message_content if 'message_content' in locals() else None,
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Failed to analyze image: {str(e)}",
            "type": type(e).__name__
        }), 500

@food_bp.route('/add_food_setting/<string:user_id>', methods=['POST'])
def add_food_setting(user_id):
    data = request.get_json()
    daily_limit_food = data.get('daily_limit_food')
    daily_supply_food = data.get('daily_supply_food')

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.daily_limit_food = daily_limit_food
    user.daily_supply_food = daily_supply_food
    db.session.commit()

    return jsonify({
        "message": "Food settings added successfully",
        "user_id": user.id,
        "daily_limit_food": user.daily_limit_food,
        "daily_supply_food": user.daily_supply_food
    }), 200

@food_bp.route('/edit_food_setting/<string:user_id>', methods=['PUT'])
def edit_food_setting(user_id):
    data = request.get_json()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if "daily_limit_food" in data:
        user.daily_limit_food = data["daily_limit_food"]
    if "daily_supply_food" in data:
        user.daily_supply_food = data["daily_supply_food"]

    db.session.commit()

    return jsonify({
        "message": "Food settings updated successfully",
        "user_id": user.id,
        "daily_limit_food": user.daily_limit_food,
        "daily_supply_food": user.daily_supply_food
    }), 200

@food_bp.route('/view_food_setting/<string:user_id>', methods=['GET'])
def view_food_settings(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user_id": user.id,
        "daily_limit_food": user.daily_limit_food,
        "daily_supply_food": user.daily_supply_food
    }), 200

@food_bp.route('/add_food', methods=['POST'])
def add_meal():
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

    try:
        print(f"DEBUG: ALL DATA RECEIVED: {dict(data)}")
        print(f"DEBUG: DATA KEYS: {data.keys()}")

        user_id = data.get("user_id")
        commit_id = data.get("commit_id")  # optional
        burn_id = data.get("burn_id")  # optional
        meal_type = data.get("meal_type")
        reply_description = data.get("reply_description")
        calories = data.get("calories")
        protein = data.get("protein")
        fat = data.get("fat")
        carbs = data.get("carbs")
        meal_date = data.get("meal_date")
        meal_time = data.get("meal_time")  # optional: "HH:MM" or "HH:MM:SS"

        print(f"DEBUG: Received commit_id = '{commit_id}' (type: {type(commit_id)})")
        print(f"DEBUG: Received burn_id = '{burn_id}' (type: {type(burn_id)})")

        if not meal_type:
            return jsonify({"error": "meal_type is required"}), 400

        # If commit_id is provided, check it exists
        commitment = None
        if commit_id and commit_id != 'null' and commit_id != '':
            print(f"DEBUG: Looking up commitment with ID: {commit_id}")
            commitment = Commitment.query.get(commit_id)
            print(f"DEBUG: Commitment lookup result: {commitment}")
            if not commitment:
                return jsonify({"error": "Commitment not found"}), 404

        # If burn_id is provided, check it exists
        burn = None
        if burn_id and burn_id != 'null' and burn_id != '':
            print(f"DEBUG: Looking up burn with ID: {burn_id}")
            burn = Burn.query.get(burn_id)
            print(f"DEBUG: Burn lookup result: {burn}")
            if not burn:
                return jsonify({"error": "Burn not found"}), 404

        # Handle file upload (optional)
        photo_url = None
        photo_url_commit = None
        photo_url_burn = None

        if file:
            # Save to food folder
            photo_url = save_upload_file(file, 'food')
            if not photo_url:
                return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, heic"}), 400

            # If linked to commitment, also save to commit folder
            if commitment:
                # Read file again for second save
                file.stream.seek(0)
                photo_url_commit = save_upload_file(file, 'commit')
                print(f"DEBUG: photo_url_commit = {photo_url_commit}")
                if photo_url_commit:
                    print(f"DEBUG: Setting commitment.photo_url to {photo_url_commit}")
                    print(f"DEBUG: Commitment ID: {commitment.id}, Current photo_url: {commitment.photo_url}")
                    commitment.photo_url = photo_url_commit
                    db.session.add(commitment)  # Explicitly add to session
                    print(f"DEBUG: After setting - commitment.photo_url = {commitment.photo_url}")
                else:
                    print(f"DEBUG: photo_url_commit was None or empty!")

            # If linked to burn, also save to burn folder
            if burn:
                # Read file again for second save
                file.stream.seek(0)
                photo_url_burn = save_upload_file(file, 'burn')
                if photo_url_burn:
                    burn.photo_url = photo_url_burn
                    db.session.add(burn)  # Explicitly add to session

        # Parse meal_time if provided (accepts "HH:MM" or "HH:MM:SS")
        parsed_meal_time = None
        if meal_time:
            try:
                # Try parsing with seconds first
                parsed_meal_time = datetime.strptime(meal_time, '%H:%M:%S').time()
            except ValueError:
                try:
                    # Try parsing without seconds
                    parsed_meal_time = datetime.strptime(meal_time, '%H:%M').time()
                except ValueError:
                    # Invalid format, leave as None
                    print(f"WARNING: Invalid meal_time format: {meal_time}. Expected HH:MM or HH:MM:SS")

        new_meal = Meal(
            user_id=user_id,
            commit_id=commit_id,
            burn_id=burn_id,
            meal_type=meal_type,
            reply_description=reply_description,
            calories=calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            meal_date=datetime.fromisoformat(meal_date).date() if meal_date else datetime.today().date(),
            meal_time=parsed_meal_time,
            photo_url=photo_url
        )

        db.session.add(new_meal)
        db.session.flush()  # Flush changes before commit
        print(f"DEBUG: Before commit - commitment photo_url in DB: {commitment.photo_url if commitment else 'N/A'}")
        print(f"DEBUG: Before commit - burn photo_url in DB: {burn.photo_url if burn else 'N/A'}")
        db.session.commit()
        print(f"DEBUG: After commit - commitment photo_url in DB: {commitment.photo_url if commitment else 'N/A'}")
        print(f"DEBUG: After commit - burn photo_url in DB: {burn.photo_url if burn else 'N/A'}")

        return jsonify({
            "message": "Meal added successfully",
            "meal": {
                "id": new_meal.id,
                "commit_id": new_meal.commit_id,
                "burn_id": new_meal.burn_id,
                "meal_type": new_meal.meal_type,
                "reply_description": new_meal.reply_description,
                "calories": new_meal.calories,
                "protein": str(new_meal.protein) if new_meal.protein else None,
                "fat": str(new_meal.fat) if new_meal.fat else None,
                "carbs": str(new_meal.carbs) if new_meal.carbs else None,
                "meal_date": str(new_meal.meal_date),
                "meal_time": new_meal.meal_time.strftime('%H:%M:%S') if new_meal.meal_time else None,
                "photo_url": new_meal.photo_url,
                "created_at": str(new_meal.created_at)
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@food_bp.route('/edit_food/<string:meal_id>', methods=['PUT'])
def edit_meal(meal_id):
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

    try:
        meal = Meal.query.get(meal_id)
        if not meal:
            return jsonify({"error": "Meal record not found"}), 404

        # Get current linked records
        current_commitment = Commitment.query.get(meal.commit_id) if meal.commit_id else None
        current_burn = Burn.query.get(meal.burn_id) if meal.burn_id else None

        # Handle commit_id change
        commit_id = data.get("commit_id")  # optional
        new_commitment = None
        if commit_id:
            new_commitment = Commitment.query.get(commit_id)
            if not new_commitment:
                return jsonify({"error": "Commitment not found"}), 404
            meal.commit_id = commit_id

        # Handle burn_id change
        burn_id = data.get("burn_id")  # optional
        new_burn = None
        if burn_id:
            new_burn = Burn.query.get(burn_id)
            if not new_burn:
                return jsonify({"error": "Burn not found"}), 404
            meal.burn_id = burn_id

        if "meal_type" in data:
            meal.meal_type = data["meal_type"]
        if "reply_description" in data:
            meal.reply_description = data["reply_description"]
        if "calories" in data:
            meal.calories = data["calories"]
        if "protein" in data:
            meal.protein = data["protein"]
        if "fat" in data:
            meal.fat = data["fat"]
        if "carbs" in data:
            meal.carbs = data["carbs"]
        if "meal_date" in data:
            try:
                meal.meal_date = datetime.fromisoformat(data["meal_date"]).date()
            except ValueError:
                return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400

        # Handle file upload (optional)
        if file:
            # Delete old photo from meal folder
            if meal.photo_url:
                delete_upload_file(meal.photo_url)

            # Delete old photos from commit/burn if they were linked
            if current_commitment and current_commitment.photo_url:
                delete_upload_file(current_commitment.photo_url)
            if current_burn and current_burn.photo_url:
                delete_upload_file(current_burn.photo_url)

            # Save new photo to food folder
            photo_url = save_upload_file(file, 'food')
            if not photo_url:
                return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, heic"}), 400
            meal.photo_url = photo_url

            # Save to linked commit folder if exists
            final_commitment = new_commitment or current_commitment
            if final_commitment:
                file.stream.seek(0)
                photo_url_commit = save_upload_file(file, 'commit')
                if photo_url_commit:
                    final_commitment.photo_url = photo_url_commit
                    db.session.add(final_commitment)  # Explicitly add to session

            # Save to linked burn folder if exists
            final_burn = new_burn or current_burn
            if final_burn:
                file.stream.seek(0)
                photo_url_burn = save_upload_file(file, 'burn')
                if photo_url_burn:
                    final_burn.photo_url = photo_url_burn
                    db.session.add(final_burn)  # Explicitly add to session

        db.session.commit()

        return jsonify({
            "message": "Meal updated successfully",
            "meal": {
                "id": meal.id,
                "commit_id": meal.commit_id,
                "burn_id": meal.burn_id,
                "meal_type": meal.meal_type,
                "reply_description": meal.reply_description,
                "calories": meal.calories,
                "protein": str(meal.protein) if meal.protein else None,
                "fat": str(meal.fat) if meal.fat else None,
                "carbs": str(meal.carbs) if meal.carbs else None,
                "meal_date": str(meal.meal_date),
                "photo_url": meal.photo_url,
                "created_at": str(meal.created_at)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@food_bp.route('/get_food/<string:user_id>', methods=['GET'])
def get_foods(user_id):
    try:
        meals = Meal.query.filter_by(user_id=user_id).order_by(desc(Meal.meal_date)).all()

        if not meals:
            return jsonify({"message": "No meals found for this user"}), 404

        meals_list = []
        for meal in meals:
            meals_list.append({
                "id": meal.id,
                "user_id": meal.user_id,
                "commit_id": meal.commit_id,
                "burn_id": meal.burn_id,
                "meal_type": meal.meal_type,
                "reply_description": meal.reply_description,
                "calories": meal.calories,
                "protein": str(meal.protein) if meal.protein else None,
                "fat": str(meal.fat) if meal.fat else None,
                "carbs": str(meal.carbs) if meal.carbs else None,
                "meal_date": str(meal.meal_date),
                "meal_time": meal.meal_time.strftime('%H:%M:%S') if meal.meal_time else None,
                "photo_url": meal.photo_url,
                "created_at": str(meal.created_at)
            })

        return jsonify({
            "meals": meals_list,
            "count": len(meals_list)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@food_bp.route('/delete_food/<string:meal_id>', methods=['DELETE'])
def delete_meal(meal_id):
    """
    Delete a meal record and its associated burn or commit record if they exist.
    This endpoint performs cascade deletion on the financial records linked to the meal.
    """
    try:
        meal = Meal.query.get(meal_id)
        if not meal:
            return jsonify({"error": "Meal record not found"}), 404

        deleted_info = {
            "meal_id": meal.id,
            "deleted_burn": None,
            "deleted_commit": None
        }

        # Delete associated photo file if it exists
        if meal.photo_url:
            delete_upload_file(meal.photo_url)

        # Check and delete associated Burn record
        if meal.burn_id:
            burn = Burn.query.get(meal.burn_id)
            if burn:
                # Delete burn's photo if exists
                if burn.photo_url:
                    delete_upload_file(burn.photo_url)

                deleted_info["deleted_burn"] = burn.id
                db.session.delete(burn)

        # Check and delete associated Commitment record
        if meal.commit_id:
            commit = Commitment.query.get(meal.commit_id)
            if commit:
                # Delete commit's photo if exists
                if commit.photo_url:
                    delete_upload_file(commit.photo_url)

                deleted_info["deleted_commit"] = commit.id
                db.session.delete(commit)

        # Delete the meal record
        db.session.delete(meal)
        db.session.commit()

        return jsonify({
            "message": "Meal and associated records deleted successfully",
            **deleted_info
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@food_bp.route('/get_meal/<string:meal_id>', methods=['GET'])
def get_meal(meal_id):
    """Get a single meal record by ID with photo URL"""
    try:
        meal = Meal.query.get(meal_id)
        if not meal:
            return jsonify({"error": "Meal record not found"}), 404

        return jsonify({
            "meal": {
                "id": meal.id,
                "user_id": meal.user_id,
                "commit_id": meal.commit_id,
                "burn_id": meal.burn_id,
                "meal_type": meal.meal_type,
                "reply_description": meal.reply_description,
                "calories": meal.calories,
                "protein": str(meal.protein) if meal.protein else None,
                "fat": str(meal.fat) if meal.fat else None,
                "carbs": str(meal.carbs) if meal.carbs else None,
                "meal_date": meal.meal_date.isoformat() if meal.meal_date else None,
                "photo_url": meal.photo_url,
                "created_at": meal.created_at.isoformat() if meal.created_at else None
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@food_bp.route('/get_food_image/<string:meal_id>', methods=['GET'])
def get_food_image(meal_id):
    """Get the actual image file for a meal record"""
    try:
        meal = Meal.query.get(meal_id)
        if not meal:
            return jsonify({"error": "Meal record not found"}), 404

        if not meal.photo_url:
            return jsonify({"error": "No image attached to this meal"}), 404

        # Build full file path
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), meal.photo_url)

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

@food_bp.route('/get_meals_by_cycle/<string:user_id>', methods=['GET'])
def get_meals_by_cycle(user_id):
    """Get all meals for a specific date range (cycle)"""
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

        # Get meals in the specified date range
        meals = (
            Meal.query.filter(
                Meal.user_id == user_id,
                Meal.meal_date >= start_date,
                Meal.meal_date <= end_date
            )
            .order_by(Meal.meal_date.desc())
            .all()
        )

        meals_list = []
        for m in meals:
            meals_list.append({
                "id": m.id,
                "user_id": m.user_id,
                "commit_id": m.commit_id,
                "burn_id": m.burn_id,
                "meal_type": m.meal_type,
                "reply_description": m.reply_description,
                "calories": m.calories,
                "protein": str(m.protein) if m.protein else None,
                "fat": str(m.fat) if m.fat else None,
                "carbs": str(m.carbs) if m.carbs else None,
                "meal_date": m.meal_date.isoformat() if m.meal_date else None,
                "photo_url": m.photo_url,
                "created_at": m.created_at.isoformat() if m.created_at else None
            })

        return jsonify({
            "meals": meals_list,
            "cycle_start": start_date_str,
            "cycle_end": end_date_str
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
