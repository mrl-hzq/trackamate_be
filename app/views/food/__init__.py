from flask import Blueprint, request, jsonify
from app.models import *
from app import db
from decimal import Decimal
from sqlalchemy import desc

from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

food_bp = Blueprint('food', __name__)

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
    data = request.json

    try:
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
        photo_url = data.get("photo_url")

        if not meal_type:
            return jsonify({"error": "meal_type is required"}), 400

        # If commit_id is provided, check it exists
        if commit_id:
            commitment = Commitment.query.get(commit_id)
            if not commitment:
                return jsonify({"error": "Commitment not found"}), 404

        # If burn_id is provided, check it exists
        if burn_id:
            burn = Burn.query.get(burn_id)
            if not burn:
                return jsonify({"error": "Burn not found"}), 404

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
            photo_url=photo_url
        )

        db.session.add(new_meal)
        db.session.commit()

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
                "photo_url": new_meal.photo_url,
                "created_at": str(new_meal.created_at)
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# belum up untuk burn id
@food_bp.route('/edit_food/<string:meal_id>', methods=['PUT'])
def edit_meal(meal_id):
    data = request.json

    try:
        meal = Meal.query.get(meal_id)
        if not meal:
            return jsonify({"error": "Meal record not found"}), 404

        commit_id = data.get("commit_id")  # optional
        if commit_id:
            commitment = Commitment.query.get(commit_id)
            if not commitment:
                return jsonify({"error": "Commitment not found"}), 404
            meal.commit_id = commit_id

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
        if "photo_url" in data:
            meal.photo_url = data["photo_url"]

        db.session.commit()

        return jsonify({
            "message": "Meal updated successfully",
            "meal": {
                "id": meal.id,
                "commit_id": meal.commit_id,
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
                "photo_url": meal.photo_url,
                "created_at": str(meal.created_at)
            })

        return jsonify({
            "meals": meals_list,
            "count": len(meals_list)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
