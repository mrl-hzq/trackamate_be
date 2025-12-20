from flask import Blueprint, request, jsonify
from app.models import Meal, WeightGoal, NutritionReview
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func
from app.views.utils.weight_utils import calculate_adherence_score, calculate_grade, get_current_phase_info
from openai import OpenAI
import os

nutrition_bp = Blueprint('nutrition', __name__)

# Initialize OpenAI client
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("WARNING: OPENAI_API_KEY not found in environment variables!")
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"ERROR: Failed to initialize OpenAI client: {e}")
    client = None


def generate_daily_nutrition_feedback(totals, targets, phase_info, user_weight, user_height):
    """Generate AI feedback for daily nutrition"""
    if client is None:
        return "Great effort today! Keep tracking your meals and staying consistent with your targets."

    # Calculate percentages
    percentages = {
        'calories': int((totals['calories'] / targets['calories']) * 100) if targets['calories'] > 0 else 0,
        'protein': int((totals['protein'] / targets['protein']) * 100) if targets['protein'] > 0 else 0,
        'carbs': int((totals.get('carbs', 0) / targets.get('carbs', 1)) * 100) if targets.get('carbs') else 0,
        'fat': int((totals.get('fat', 0) / targets.get('fat', 1)) * 100) if targets.get('fat') else 0
    }

    prompt = f"""You are a nutrition coach reviewing a Malaysian user's daily food intake for weight loss.

USER PROFILE:
- Current Weight: {user_weight}kg
- Height: {user_height}cm
- Goal: Lose weight sustainably from 106kg to 80kg
- Location: Kuala Lumpur, Malaysia
- Current Phase: {phase_info['phase_name']} (Day {phase_info['day_in_phase']} of {phase_info['total_days']})
- Phase Goal: {phase_info['phase_description']}

TODAY'S INTAKE:
- Calories: {totals['calories']} / {targets['calories']} ({percentages['calories']}%)
- Protein: {totals['protein']}g / {targets['protein']}g ({percentages['protein']}%)
- Carbs: {totals.get('carbs', 0)}g / {targets.get('carbs', 0)}g ({percentages['carbs']}%)
- Fat: {totals.get('fat', 0)}g / {targets.get('fat', 0)}g ({percentages['fat']}%)

CONTEXT:
- User follows 16:8 intermittent fasting (12pm-8pm eating window)
- Works 9-5 office job (sedentary)
- Eats Malaysian food (nasi campur, chicken rice, ayam bakar, etc.)
- Previously plateaued at 100kg due to too-aggressive deficit
- This time using sustainable approach to prevent plateau

INSTRUCTIONS:
Provide a concise review (3-4 sentences max) that:
1. Acknowledges what they did well (be specific)
2. Provides ONE actionable suggestion for improvement if needed
3. Keeps tone encouraging and positive
4. References Malaysian food/context when relevant
5. Considers their current phase goals

Be concise, friendly, and motivating. No bullet points - write as flowing text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert nutrition coach specializing in sustainable weight loss for Asian populations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )

        feedback = response.choices[0].message.content.strip()
        return feedback

    except Exception as e:
        print(f"Error generating AI feedback: {str(e)}")
        return "Great effort today! Keep tracking your meals and staying consistent with your targets."


@nutrition_bp.route('/daily-review', methods=['POST'])
def daily_review():
    """Generate AI-powered daily nutrition review"""
    try:
        data = request.get_json()

        if not data.get('user_id') or not data.get('date'):
            return jsonify({"error": "user_id and date are required"}), 400

        user_id = data['user_id']

        # Parse date
        try:
            review_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Get user's weight goal
        weight_goal = WeightGoal.query.filter_by(user_id=user_id).first()
        if not weight_goal:
            return jsonify({"error": "No weight goal found. Please set up your weight goal first."}), 404

        # Get all meals for the date
        meals = Meal.query.filter(
            Meal.user_id == user_id,
            Meal.meal_date == review_date
        ).all()

        if not meals:
            return jsonify({"error": "No meals found for this date"}), 404

        # Sum up totals
        total_calories = sum([m.calories or 0 for m in meals])
        total_protein = sum([float(m.protein or 0) for m in meals])
        total_carbs = sum([float(m.carbs or 0) for m in meals])
        total_fat = sum([float(m.fat or 0) for m in meals])

        totals = {
            'calories': total_calories,
            'protein': total_protein,
            'carbs': total_carbs,
            'fat': total_fat
        }

        targets = {
            'calories': weight_goal.daily_calorie_target,
            'protein': weight_goal.daily_protein_target,
            'carbs': weight_goal.daily_carbs_target or 0,
            'fat': weight_goal.daily_fat_target or 0
        }

        # Calculate adherence score and grade
        adherence_score = calculate_adherence_score(totals, targets)
        grade = calculate_grade(adherence_score)

        # Get phase info
        phase_info = get_current_phase_info(weight_goal)

        # Generate AI feedback
        ai_feedback = generate_daily_nutrition_feedback(
            totals,
            targets,
            phase_info,
            float(weight_goal.current_weight),
            weight_goal.height_cm
        )

        # Calculate percentages
        percentages = {
            'calories': int((totals['calories'] / targets['calories']) * 100) if targets['calories'] > 0 else 0,
            'protein': int((totals['protein'] / targets['protein']) * 100) if targets['protein'] > 0 else 0,
            'carbs': int((totals['carbs'] / targets['carbs']) * 100) if targets.get('carbs') and targets['carbs'] > 0 else 0,
            'fat': int((totals['fat'] / targets['fat']) * 100) if targets.get('fat') and targets['fat'] > 0 else 0
        }

        # Save review to database
        existing_review = NutritionReview.query.filter_by(
            user_id=user_id,
            review_date=review_date
        ).first()

        if existing_review:
            # Update existing review
            existing_review.total_calories = total_calories
            existing_review.total_protein = total_protein
            existing_review.total_carbs = total_carbs
            existing_review.total_fat = total_fat
            existing_review.calorie_target = weight_goal.daily_calorie_target
            existing_review.protein_target = weight_goal.daily_protein_target
            existing_review.adherence_score = adherence_score
            existing_review.ai_feedback = ai_feedback
            existing_review.grade = grade
        else:
            # Create new review
            review = NutritionReview(
                user_id=user_id,
                review_date=review_date,
                total_calories=total_calories,
                total_protein=total_protein,
                total_carbs=total_carbs,
                total_fat=total_fat,
                calorie_target=weight_goal.daily_calorie_target,
                protein_target=weight_goal.daily_protein_target,
                adherence_score=adherence_score,
                ai_feedback=ai_feedback,
                grade=grade
            )
            db.session.add(review)

        db.session.commit()

        # Generate recommendations
        recommendations = []
        if percentages['protein'] >= 95:
            recommendations.append("Protein intake is perfect - keep this up!")
        elif percentages['protein'] < 80:
            recommendations.append(f"Try to increase protein to at least {targets['protein']}g")

        if 90 <= percentages['calories'] <= 110:
            recommendations.append("Calorie intake is right on target!")
        elif percentages['calories'] < 90:
            recommendations.append("Calories are a bit low - make sure you're eating enough")
        elif percentages['calories'] > 120:
            recommendations.append("Calories are above target - try to reduce portions tomorrow")

        if not recommendations:
            recommendations.append("Overall adherence is excellent")

        return jsonify({
            'success': True,
            'data': {
                'review_date': review_date.isoformat(),
                'totals': {
                    'calories': total_calories,
                    'protein': round(total_protein, 1),
                    'carbs': round(total_carbs, 1),
                    'fat': round(total_fat, 1)
                },
                'targets': targets,
                'percentages': percentages,
                'adherence_score': adherence_score,
                'grade': grade,
                'ai_feedback': ai_feedback,
                'phase': weight_goal.current_phase,
                'recommendations': recommendations
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@nutrition_bp.route('/weekly-summary/<string:user_id>', methods=['GET'])
def weekly_summary(user_id):
    """Get weekly nutrition summary and trends"""
    try:
        # Get week_start from query params or default to last Monday
        week_start_str = request.args.get('week_start')

        if week_start_str:
            try:
                week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Invalid week_start format. Use YYYY-MM-DD"}), 400
        else:
            # Get last Monday
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        # Get weight goal
        weight_goal = WeightGoal.query.filter_by(user_id=user_id).first()
        if not weight_goal:
            return jsonify({"error": "No weight goal found"}), 404

        # Get all reviews for the week
        reviews = NutritionReview.query.filter(
            NutritionReview.user_id == user_id,
            NutritionReview.review_date >= week_start,
            NutritionReview.review_date <= week_end
        ).all()

        days_tracked = len(reviews)

        if days_tracked == 0:
            return jsonify({
                'success': True,
                'data': {
                    'week_start': week_start.isoformat(),
                    'week_end': week_end.isoformat(),
                    'days_tracked': 0,
                    'message': 'No nutrition data for this week'
                }
            }), 200

        # Calculate averages
        avg_calories = int(sum([r.total_calories for r in reviews]) / days_tracked)
        avg_protein = round(sum([float(r.total_protein) for r in reviews]) / days_tracked, 1)
        avg_carbs = round(sum([float(r.total_carbs) for r in reviews]) / days_tracked, 1)
        avg_fat = round(sum([float(r.total_fat) for r in reviews]) / days_tracked, 1)

        # Calculate adherence
        calorie_adherence = int((avg_calories / weight_goal.daily_calorie_target) * 100) if weight_goal.daily_calorie_target > 0 else 0
        protein_days_hit = sum([1 for r in reviews if float(r.total_protein) >= weight_goal.daily_protein_target * 0.95])
        days_on_track = sum([1 for r in reviews if r.adherence_score >= 80])

        # Calculate overall grade
        avg_adherence = int(sum([r.adherence_score for r in reviews]) / days_tracked)
        grade = calculate_grade(avg_adherence)

        # Determine trend
        if avg_adherence >= 90:
            trend = 'excellent'
        elif avg_adherence >= 80:
            trend = 'consistent'
        elif avg_adherence >= 70:
            trend = 'improving'
        else:
            trend = 'needs_attention'

        # Generate AI summary (simplified version)
        ai_summary = f"Good week! You tracked {days_tracked} out of 7 days and maintained {calorie_adherence}% calorie adherence. You hit protein targets {protein_days_hit} out of {days_tracked} days. Keep up the consistency!"

        return jsonify({
            'success': True,
            'data': {
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'days_tracked': days_tracked,
                'daily_averages': {
                    'calories': avg_calories,
                    'protein': avg_protein,
                    'carbs': avg_carbs,
                    'fat': avg_fat
                },
                'targets': {
                    'calories': weight_goal.daily_calorie_target,
                    'protein': weight_goal.daily_protein_target
                },
                'adherence': {
                    'calorie_adherence': calorie_adherence,
                    'protein_days_hit': protein_days_hit,
                    'days_on_track': days_on_track
                },
                'grade': grade,
                'trend': trend,
                'ai_summary': ai_summary
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@nutrition_bp.route('/reviews/<string:user_id>', methods=['GET'])
def get_reviews(user_id):
    """Get nutrition review history"""
    try:
        limit = request.args.get('limit', 30, type=int)

        reviews = NutritionReview.query.filter_by(user_id=user_id).order_by(
            NutritionReview.review_date.desc()
        ).limit(limit).all()

        return jsonify({
            'success': True,
            'data': [review.to_dict() for review in reviews],
            'count': len(reviews)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@nutrition_bp.route('/meal-timing/<string:user_id>', methods=['GET'])
def meal_timing(user_id):
    """Analyze meal timing patterns"""
    try:
        # Get number of days to analyze
        days = request.args.get('days', 7, type=int)

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # Get all meals in the date range
        meals = Meal.query.filter(
            Meal.user_id == user_id,
            Meal.meal_date >= start_date,
            Meal.meal_date <= end_date
        ).order_by(Meal.meal_date.asc(), Meal.created_at.asc()).all()

        if not meals:
            return jsonify({
                'success': True,
                'data': {
                    'message': 'No meal data available for analysis',
                    'days_analyzed': days
                }
            }), 200

        # Group meals by date
        meals_by_date = {}
        for meal in meals:
            date_key = meal.meal_date.isoformat()
            if date_key not in meals_by_date:
                meals_by_date[date_key] = []
            meals_by_date[date_key].append(meal)

        # Analyze eating window for each day
        daily_windows = []
        total_first_meal_minutes = 0
        total_last_meal_minutes = 0
        days_within_window = 0
        total_days_with_meals = len(meals_by_date)

        # Target eating window (12pm - 8pm)
        target_start_hour = 12
        target_end_hour = 20

        for date_str, day_meals in meals_by_date.items():
            # Filter meals that have meal_time set, fallback to created_at for legacy data
            day_meals_with_time = []
            for meal in day_meals:
                if meal.meal_time:
                    # Use meal_time (TIME column)
                    meal_datetime = datetime.combine(datetime.today(), meal.meal_time)
                else:
                    # Fallback to created_at for backward compatibility
                    meal_datetime = meal.created_at
                day_meals_with_time.append((meal, meal_datetime))

            # Sort by time
            day_meals_sorted = sorted(day_meals_with_time, key=lambda x: x[1])

            first_meal_time = day_meals_sorted[0][1]
            last_meal_time = day_meals_sorted[-1][1]

            # Convert to minutes from midnight
            first_meal_minutes = first_meal_time.hour * 60 + first_meal_time.minute
            last_meal_minutes = last_meal_time.hour * 60 + last_meal_time.minute

            total_first_meal_minutes += first_meal_minutes
            total_last_meal_minutes += last_meal_minutes

            # Calculate eating window in hours
            window_minutes = last_meal_minutes - first_meal_minutes
            window_hours = window_minutes / 60

            # Check if within target window (12pm - 8pm)
            first_hour = first_meal_time.hour + (first_meal_time.minute / 60)
            last_hour = last_meal_time.hour + (last_meal_time.minute / 60)

            is_within_window = (first_hour >= target_start_hour and last_hour <= target_end_hour)
            if is_within_window:
                days_within_window += 1

            daily_windows.append({
                'date': date_str,
                'first_meal_time': first_meal_time.strftime('%I:%M %p'),
                'last_meal_time': last_meal_time.strftime('%I:%M %p'),
                'window_hours': round(window_hours, 2),
                'within_target': is_within_window
            })

        # Calculate averages
        avg_first_meal_minutes = int(total_first_meal_minutes / total_days_with_meals)
        avg_last_meal_minutes = int(total_last_meal_minutes / total_days_with_meals)

        avg_first_hour = avg_first_meal_minutes // 60
        avg_first_min = avg_first_meal_minutes % 60
        avg_last_hour = avg_last_meal_minutes // 60
        avg_last_min = avg_last_meal_minutes % 60

        # Format times
        avg_first_meal = datetime.strptime(f"{avg_first_hour}:{avg_first_min}", "%H:%M").strftime("%I:%M %p")
        avg_last_meal = datetime.strptime(f"{avg_last_hour}:{avg_last_min}", "%H:%M").strftime("%I:%M %p")

        avg_window_hours = round((avg_last_meal_minutes - avg_first_meal_minutes) / 60, 2)

        # Analyze meal distribution by type
        meal_distribution = {}
        meal_types = ['breakfast', 'lunch', 'snack', 'dinner']

        for meal_type in meal_types:
            type_meals = [m for m in meals if m.meal_type == meal_type]
            if type_meals:
                avg_time_minutes = sum([m.created_at.hour * 60 + m.created_at.minute for m in type_meals]) / len(type_meals)
                avg_hour = int(avg_time_minutes // 60)
                avg_min = int(avg_time_minutes % 60)
                avg_time = datetime.strptime(f"{avg_hour}:{avg_min}", "%H:%M").strftime("%I:%M %p")

                avg_calories = int(sum([m.calories or 0 for m in type_meals]) / len(type_meals))

                meal_distribution[meal_type] = {
                    'avg_time': avg_time,
                    'avg_calories': avg_calories,
                    'count': len(type_meals)
                }

        # Generate recommendations
        recommendations = []
        compliance_percentage = int((days_within_window / total_days_with_meals) * 100) if total_days_with_meals > 0 else 0

        if compliance_percentage >= 85:
            recommendations.append(f"Great job staying within eating window {days_within_window}/{total_days_with_meals} days!")
        elif compliance_percentage >= 70:
            recommendations.append(f"Good progress on eating window - {days_within_window}/{total_days_with_meals} days compliant")
        else:
            recommendations.append(f"Try to improve eating window compliance - currently {days_within_window}/{total_days_with_meals} days")

        if avg_last_hour < target_end_hour:
            recommendations.append(f"Average last meal at {avg_last_meal} is perfect (before {target_end_hour}:00 cutoff)")
        else:
            recommendations.append(f"Try to finish last meal before {target_end_hour}:00 - currently averaging {avg_last_meal}")

        if avg_window_hours <= 8:
            recommendations.append("Meal timing supports good intermittent fasting compliance")
        else:
            recommendations.append(f"Consider shortening eating window - currently {avg_window_hours} hours")

        return jsonify({
            'success': True,
            'data': {
                'days_analyzed': days,
                'eating_window': {
                    'avg_first_meal': avg_first_meal,
                    'avg_last_meal': avg_last_meal,
                    'avg_window_hours': avg_window_hours,
                    'target_window': f"{target_start_hour}:00 PM - {target_end_hour}:00 PM"
                },
                'compliance': {
                    'days_within_window': days_within_window,
                    'total_days': total_days_with_meals,
                    'percentage': compliance_percentage
                },
                'meal_distribution': meal_distribution,
                'daily_windows': daily_windows,
                'recommendations': recommendations
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
