from flask import Blueprint, request, jsonify
from app.models import WeightEntry, WeightGoal, NutritionReview, Meal
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func
from app.views.utils.weight_utils import check_for_plateau, get_current_phase_info

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/progress-dashboard/<string:user_id>', methods=['GET'])
def progress_dashboard(user_id):
    """Comprehensive progress dashboard data"""
    try:
        # Get weight goal
        weight_goal = WeightGoal.query.filter_by(user_id=user_id).first()
        if not weight_goal:
            return jsonify({"error": "No weight goal found"}), 404

        # Get phase info
        phase_info = get_current_phase_info(weight_goal)

        # Calculate overview metrics
        weight_lost = float(weight_goal.starting_weight) - float(weight_goal.current_weight)
        weight_remaining = float(weight_goal.current_weight) - float(weight_goal.goal_weight)
        total_to_lose = float(weight_goal.starting_weight) - float(weight_goal.goal_weight)
        percentage_complete = (weight_lost / total_to_lose * 100) if total_to_lose > 0 else 0

        # Calculate days
        today = datetime.now().date()
        days_elapsed = (today - weight_goal.created_at.date()).days
        days_remaining = (weight_goal.target_date - today).days

        # Get weekly nutrition stats (last 7 days)
        week_ago = today - timedelta(days=7)
        weekly_reviews = NutritionReview.query.filter(
            NutritionReview.user_id == user_id,
            NutritionReview.review_date >= week_ago
        ).all()

        if weekly_reviews:
            avg_daily_calories = int(sum([r.total_calories for r in weekly_reviews]) / len(weekly_reviews))
            avg_protein = int(sum([float(r.total_protein) for r in weekly_reviews]) / len(weekly_reviews))
            days_on_track = sum([1 for r in weekly_reviews if r.adherence_score >= 80])
            avg_adherence = int(sum([r.adherence_score for r in weekly_reviews]) / len(weekly_reviews))
        else:
            avg_daily_calories = 0
            avg_protein = 0
            days_on_track = 0
            avg_adherence = 0

        # Get weight trend
        week_entries = WeightEntry.query.filter(
            WeightEntry.user_id == user_id,
            WeightEntry.date >= week_ago
        ).order_by(WeightEntry.date.asc()).all()

        month_ago = today - timedelta(days=30)
        month_entries = WeightEntry.query.filter(
            WeightEntry.user_id == user_id,
            WeightEntry.date >= month_ago
        ).order_by(WeightEntry.date.asc()).all()

        if len(week_entries) >= 2:
            last_7_days_change = float(week_entries[-1].weight_kg) - float(week_entries[0].weight_kg)
        else:
            last_7_days_change = 0

        if len(month_entries) >= 2:
            last_30_days_change = float(month_entries[-1].weight_kg) - float(month_entries[0].weight_kg)
        else:
            last_30_days_change = 0

        # Determine trend status
        if last_7_days_change < -0.2:
            trend = 'on_track'
        elif last_7_days_change > 0.2:
            trend = 'gaining'
        else:
            trend = 'maintaining'

        # Calculate next milestone (round down to nearest 5kg)
        current_weight_int = int(float(weight_goal.current_weight))
        next_milestone_weight = (current_weight_int // 5) * 5

        # If already at a milestone, go to next one
        if next_milestone_weight >= current_weight_int:
            next_milestone_weight -= 5

        # Estimate date based on current rate
        if last_30_days_change < 0:
            kg_per_month = abs(last_30_days_change)
            kg_to_milestone = float(weight_goal.current_weight) - next_milestone_weight
            months_to_milestone = kg_to_milestone / kg_per_month if kg_per_month > 0 else 0
            estimated_date = today + timedelta(days=int(months_to_milestone * 30))
            days_away = (estimated_date - today).days
        else:
            estimated_date = today + timedelta(days=90)
            days_away = 90

        return jsonify({
            'success': True,
            'data': {
                'overview': {
                    'starting_weight': float(weight_goal.starting_weight),
                    'current_weight': float(weight_goal.current_weight),
                    'goal_weight': float(weight_goal.goal_weight),
                    'weight_lost': round(weight_lost, 1),
                    'weight_remaining': round(weight_remaining, 1),
                    'percentage_complete': round(percentage_complete, 1),
                    'days_elapsed': days_elapsed,
                    'days_remaining': max(days_remaining, 0),
                    'current_phase': weight_goal.current_phase
                },
                'weekly_stats': {
                    'avg_daily_calories': avg_daily_calories,
                    'avg_protein': avg_protein,
                    'days_on_track': days_on_track,
                    'adherence_score': avg_adherence
                },
                'weight_trend': {
                    'last_7_days': round(last_7_days_change, 2),
                    'last_30_days': round(last_30_days_change, 2),
                    'trend': trend
                },
                'next_milestone': {
                    'target_weight': next_milestone_weight,
                    'estimated_date': estimated_date.isoformat(),
                    'days_away': days_away
                }
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route('/plateau-check/<string:user_id>', methods=['POST'])
def plateau_check(user_id):
    """Check if user is experiencing a plateau and suggest actions"""
    try:
        weeks_threshold = request.json.get('weeks_threshold', 2) if request.json else 2

        result = check_for_plateau(user_id, weeks_threshold)

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route('/daily-totals/<string:user_id>', methods=['GET'])
def daily_totals(user_id):
    """Get nutrition totals for a specific date"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            date = datetime.now().date()
        else:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Get all meals for the date
        meals = Meal.query.filter(
            Meal.user_id == user_id,
            Meal.meal_date == date
        ).all()

        # Sum up totals
        total_calories = sum([m.calories or 0 for m in meals])
        total_protein = sum([float(m.protein or 0) for m in meals])
        total_carbs = sum([float(m.carbs or 0) for m in meals])
        total_fat = sum([float(m.fat or 0) for m in meals])

        # Get targets
        weight_goal = WeightGoal.query.filter_by(user_id=user_id).first()

        if weight_goal:
            targets = {
                'calories': weight_goal.daily_calorie_target,
                'protein': weight_goal.daily_protein_target,
                'carbs': weight_goal.daily_carbs_target or 0,
                'fat': weight_goal.daily_fat_target or 0
            }

            percentages = {
                'calories': int((total_calories / targets['calories']) * 100) if targets['calories'] > 0 else 0,
                'protein': int((total_protein / targets['protein']) * 100) if targets['protein'] > 0 else 0,
                'carbs': int((total_carbs / targets['carbs']) * 100) if targets.get('carbs') and targets['carbs'] > 0 else 0,
                'fat': int((total_fat / targets['fat']) * 100) if targets.get('fat') and targets['fat'] > 0 else 0
            }
        else:
            targets = None
            percentages = None

        return jsonify({
            'success': True,
            'data': {
                'date': date.isoformat(),
                'totals': {
                    'calories': total_calories,
                    'protein': round(total_protein, 1),
                    'carbs': round(total_carbs, 1),
                    'fat': round(total_fat, 1)
                },
                'targets': targets,
                'percentages': percentages,
                'meal_count': len(meals)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route('/monthly-summary/<string:user_id>', methods=['GET'])
def monthly_summary(user_id):
    """Get monthly nutrition and weight summary"""
    try:
        # Get month from query params or default to current month
        month_str = request.args.get('month')  # Format: YYYY-MM

        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                start_date = datetime(year, month, 1).date()
            except ValueError:
                return jsonify({"error": "Invalid month format. Use YYYY-MM"}), 400
        else:
            today = datetime.now().date()
            start_date = datetime(today.year, today.month, 1).date()

        # Calculate end date
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1).date() - timedelta(days=1)

        # Get nutrition reviews for the month
        reviews = NutritionReview.query.filter(
            NutritionReview.user_id == user_id,
            NutritionReview.review_date >= start_date,
            NutritionReview.review_date <= end_date
        ).all()

        # Get weight entries for the month
        weight_entries = WeightEntry.query.filter(
            WeightEntry.user_id == user_id,
            WeightEntry.date >= start_date,
            WeightEntry.date <= end_date
        ).order_by(WeightEntry.date.asc()).all()

        days_tracked = len(reviews)

        if reviews:
            avg_calories = int(sum([r.total_calories for r in reviews]) / days_tracked)
            avg_protein = round(sum([float(r.total_protein) for r in reviews]) / days_tracked, 1)
            avg_adherence = int(sum([r.adherence_score for r in reviews]) / days_tracked)
            days_on_track = sum([1 for r in reviews if r.adherence_score >= 80])
        else:
            avg_calories = 0
            avg_protein = 0
            avg_adherence = 0
            days_on_track = 0

        if len(weight_entries) >= 2:
            weight_change = float(weight_entries[-1].weight_kg) - float(weight_entries[0].weight_kg)
        else:
            weight_change = 0

        return jsonify({
            'success': True,
            'data': {
                'month': start_date.strftime('%Y-%m'),
                'month_name': start_date.strftime('%B %Y'),
                'days_in_month': (end_date - start_date).days + 1,
                'days_tracked': days_tracked,
                'nutrition': {
                    'avg_calories': avg_calories,
                    'avg_protein': avg_protein,
                    'avg_adherence': avg_adherence,
                    'days_on_track': days_on_track
                },
                'weight': {
                    'entries_count': len(weight_entries),
                    'weight_change': round(weight_change, 1),
                    'start_weight': float(weight_entries[0].weight_kg) if weight_entries else None,
                    'end_weight': float(weight_entries[-1].weight_kg) if weight_entries else None
                }
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
