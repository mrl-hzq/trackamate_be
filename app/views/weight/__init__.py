from flask import Blueprint, request, jsonify
from app.models import WeightEntry, WeightGoal
from app import db
from datetime import datetime, timedelta
from sqlalchemy import desc
from app.views.utils.weight_utils import calculate_phases, get_current_phase_info

weight_bp = Blueprint('weight', __name__)


@weight_bp.route('/entry', methods=['POST'])
def add_weight_entry():
    """Add a new weight entry"""
    try:
        data = request.get_json()

        if not data.get('user_id') or not data.get('weight_kg') or not data.get('date'):
            return jsonify({"error": "user_id, weight_kg, and date are required"}), 400

        # Parse date
        try:
            entry_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Create weight entry
        entry = WeightEntry(
            user_id=data['user_id'],
            weight_kg=data['weight_kg'],
            date=entry_date,
            notes=data.get('notes')
        )

        db.session.add(entry)

        # Update current_weight in weight_goal if exists
        goal = WeightGoal.query.filter_by(user_id=data['user_id']).first()
        if goal:
            goal.current_weight = data['weight_kg']

        db.session.commit()

        return jsonify({
            'success': True,
            'data': entry.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@weight_bp.route('/entries/<string:user_id>', methods=['GET'])
def get_weight_entries(user_id):
    """Get all weight entries for a user"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 30, type=int)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Build query
        query = WeightEntry.query.filter_by(user_id=user_id)

        # Apply date filters
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                query = query.filter(WeightEntry.date >= start_date)
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(WeightEntry.date <= end_date)
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

        # Get entries
        entries = query.order_by(desc(WeightEntry.date)).limit(limit).all()

        return jsonify({
            'success': True,
            'data': [entry.to_dict() for entry in entries],
            'count': len(entries)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@weight_bp.route('/trend/<string:user_id>', methods=['GET'])
def get_weight_trend(user_id):
    """Get weight trend data for charts"""
    try:
        days = request.args.get('days', 30, type=int)

        # Get entries for last N days
        cutoff_date = datetime.now().date() - timedelta(days=days)
        entries = WeightEntry.query.filter(
            WeightEntry.user_id == user_id,
            WeightEntry.date >= cutoff_date
        ).order_by(WeightEntry.date.asc()).all()

        if not entries:
            return jsonify({
                'success': True,
                'data': {
                    'entries': [],
                    'trend': 'no_data',
                    'avg_weekly_loss': 0,
                    'total_loss': 0
                }
            }), 200

        # Calculate trend
        entry_data = [{'date': e.date.isoformat(), 'weight_kg': float(e.weight_kg)} for e in entries]

        first_weight = float(entries[0].weight_kg)
        last_weight = float(entries[-1].weight_kg)
        total_loss = last_weight - first_weight

        # Calculate average weekly loss
        days_span = (entries[-1].date - entries[0].date).days
        weeks = max(days_span / 7, 1)
        avg_weekly_loss = total_loss / weeks if weeks > 0 else 0

        # Determine trend
        if total_loss < -0.5:
            trend = 'decreasing'
        elif total_loss > 0.5:
            trend = 'increasing'
        else:
            trend = 'stable'

        return jsonify({
            'success': True,
            'data': {
                'entries': entry_data,
                'trend': trend,
                'avg_weekly_loss': round(avg_weekly_loss, 2),
                'total_loss': round(total_loss, 2)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@weight_bp.route('/setup-goal', methods=['POST'])
def setup_goal():
    """Initial setup for weight loss journey"""
    try:
        data = request.get_json()

        # Validate required fields
        required = ['user_id', 'starting_weight', 'goal_weight', 'height_cm', 'target_date']
        for field in required:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Parse target date
        try:
            target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid target_date format. Use YYYY-MM-DD"}), 400

        # Check if goal already exists
        existing_goal = WeightGoal.query.filter_by(user_id=data['user_id']).first()
        if existing_goal:
            return jsonify({"error": "Weight goal already exists for this user. Use update endpoint instead."}), 400

        # Calculate phases
        phases = calculate_phases(
            data['starting_weight'],
            data['goal_weight'],
            target_date
        )

        # Create weight goal with first phase settings
        today = datetime.now().date()
        first_phase = phases[0]

        goal = WeightGoal(
            user_id=data['user_id'],
            starting_weight=data['starting_weight'],
            current_weight=data['starting_weight'],
            goal_weight=data['goal_weight'],
            height_cm=data['height_cm'],
            target_date=target_date,
            current_phase='priming',
            phase_start_date=today,
            daily_calorie_target=first_phase['daily_calorie_target'],
            daily_protein_target=first_phase['daily_protein_target'],
            daily_carbs_target=first_phase['daily_carbs_target'],
            daily_fat_target=first_phase['daily_fat_target']
        )

        db.session.add(goal)
        db.session.commit()

        return jsonify({
            'success': True,
            'data': {
                **goal.to_dict(),
                'phases': phases
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@weight_bp.route('/current-phase/<string:user_id>', methods=['GET'])
def get_current_phase(user_id):
    """Get current phase information and targets"""
    try:
        goal = WeightGoal.query.filter_by(user_id=user_id).first()

        if not goal:
            return jsonify({"error": "No weight goal found for this user"}), 404

        # Get phase info
        phase_info = get_current_phase_info(goal)

        # Calculate progress
        weight_lost = float(goal.starting_weight) - float(goal.current_weight)
        weight_remaining = float(goal.current_weight) - float(goal.goal_weight)

        return jsonify({
            'success': True,
            'data': {
                **phase_info,
                'daily_calorie_target': goal.daily_calorie_target,
                'daily_protein_target': goal.daily_protein_target,
                'daily_carbs_target': goal.daily_carbs_target,
                'daily_fat_target': goal.daily_fat_target,
                'current_weight': float(goal.current_weight),
                'goal_weight': float(goal.goal_weight),
                'weight_lost': round(weight_lost, 1),
                'weight_remaining': round(weight_remaining, 1)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@weight_bp.route('/update-phase', methods=['PUT'])
def update_phase():
    """Manually update phase (for diet breaks, transitions)"""
    try:
        data = request.get_json()

        if not data.get('user_id') or not data.get('new_phase'):
            return jsonify({"error": "user_id and new_phase are required"}), 400

        goal = WeightGoal.query.filter_by(user_id=data['user_id']).first()

        if not goal:
            return jsonify({"error": "No weight goal found for this user"}), 404

        # Update phase
        goal.current_phase = data['new_phase']
        goal.phase_start_date = datetime.now().date()

        # Update targets if provided
        if 'daily_calorie_target' in data:
            goal.daily_calorie_target = data['daily_calorie_target']
        if 'daily_protein_target' in data:
            goal.daily_protein_target = data['daily_protein_target']
        if 'daily_carbs_target' in data:
            goal.daily_carbs_target = data['daily_carbs_target']
        if 'daily_fat_target' in data:
            goal.daily_fat_target = data['daily_fat_target']

        db.session.commit()

        return jsonify({
            'success': True,
            'data': goal.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@weight_bp.route('/goal/<string:user_id>', methods=['GET'])
def get_weight_goal(user_id):
    """Get weight goal for a user"""
    try:
        goal = WeightGoal.query.filter_by(user_id=user_id).first()

        if not goal:
            return jsonify({"error": "No weight goal found for this user"}), 404

        return jsonify({
            'success': True,
            'data': goal.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@weight_bp.route('/daily-review/<string:user_id>', methods=['GET'])
def get_daily_review(user_id):
    """
    Get daily nutrition review with AI feedback
    Query params: date (optional, defaults to today)
    """
    try:
        from app.models import Meal, WeightGoal
        from sqlalchemy import func

        # Get date parameter or default to today
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

        try:
            review_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Get all meals for the date
        meals = Meal.query.filter(
            Meal.user_id == user_id,
            Meal.meal_date == review_date
        ).all()

        if not meals:
            return jsonify({'success': False, 'error': 'No meals found for this date'}), 404

        # Calculate totals
        total_calories = sum(meal.calories or 0 for meal in meals)
        total_protein = sum(float(meal.protein or 0) for meal in meals)
        total_carbs = sum(float(meal.carbs or 0) for meal in meals)
        total_fat = sum(float(meal.fat or 0) for meal in meals)

        # Get weight goal for targets
        goal = WeightGoal.query.filter_by(user_id=user_id).first()
        if not goal:
            return jsonify({'success': False, 'error': 'No weight goal found. Please set up your weight goal first.'}), 404

        calorie_target = goal.daily_calorie_target
        protein_target = goal.daily_protein_target

        # Calculate variances
        calorie_variance = total_calories - calorie_target
        protein_variance = total_protein - protein_target

        # Calculate grade based on percentage deviations
        cal_percent_off = abs(calorie_variance) / calorie_target * 100 if calorie_target > 0 else 0
        pro_percent_off = abs(protein_variance) / protein_target * 100 if protein_target > 0 else 0
        max_percent_off = max(cal_percent_off, pro_percent_off)

        if max_percent_off <= 5:
            grade = 'A'
        elif max_percent_off <= 10:
            grade = 'B'
        elif max_percent_off <= 20:
            grade = 'C'
        elif max_percent_off <= 30:
            grade = 'D'
        else:
            grade = 'F'

        # Generate AI feedback (rule-based for now)
        ai_feedback = generate_nutrition_feedback(
            total_calories, total_protein, total_carbs, total_fat,
            calorie_target, protein_target, grade
        )

        return jsonify({
            'success': True,
            'data': {
                'date': date_str,
                'total_calories': round(total_calories, 1),
                'total_protein': round(total_protein, 1),
                'total_carbs': round(total_carbs, 1),
                'total_fat': round(total_fat, 1),
                'calorie_target': calorie_target,
                'protein_target': protein_target,
                'calorie_variance': round(calorie_variance, 1),
                'protein_variance': round(protein_variance, 1),
                'grade': grade,
                'ai_feedback': ai_feedback
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_nutrition_feedback(total_calories, total_protein, total_carbs, total_fat,
                                 calorie_target, protein_target, grade):
    """Generate rule-based nutrition feedback"""
    feedback_parts = []

    # Calorie analysis
    cal_variance = total_calories - calorie_target
    if abs(cal_variance) <= 50:
        feedback_parts.append("Excellent calorie control!")
    elif cal_variance > 0:
        feedback_parts.append(f"You're {abs(cal_variance):.0f} kcal over target.")
    else:
        feedback_parts.append(f"You're {abs(cal_variance):.0f} kcal under target.")

    # Protein analysis
    pro_variance = total_protein - protein_target
    if abs(pro_variance) <= 10:
        feedback_parts.append("Protein intake is spot on!")
    elif pro_variance < -20:
        feedback_parts.append(f"Increase protein by {abs(pro_variance):.0f}g tomorrow.")
    elif pro_variance > 0:
        feedback_parts.append("Great protein intake!")

    # Macro balance suggestion
    if total_calories > 0:
        carb_percent = (total_carbs * 4) / total_calories * 100
        if carb_percent > 50:
            feedback_parts.append("Consider reducing carbs and increasing protein/fat.")

    # Overall encouragement
    if grade in ['A', 'B']:
        feedback_parts.append("Keep up the great work!")
    elif grade == 'C':
        feedback_parts.append("You're close to target, small adjustments will help!")
    else:
        feedback_parts.append("Let's refocus tomorrow and hit those targets!")

    return " ".join(feedback_parts)


@weight_bp.route('/weekly-summary/<string:user_id>', methods=['GET'])
def get_weekly_summary(user_id):
    """
    Get weekly nutrition summary
    Query params: weeks (optional, default 4, accepts 2/4/8)
    """
    try:
        from app.models import Meal, WeightGoal
        from collections import defaultdict

        weeks = int(request.args.get('weeks', 4))
        if weeks not in [2, 4, 8]:
            weeks = 4  # Default to 4 if invalid

        # Get weight goal for targets
        goal = WeightGoal.query.filter_by(user_id=user_id).first()
        if not goal:
            return jsonify({'success': False, 'error': 'No weight goal found'}), 404

        calorie_target = goal.daily_calorie_target
        protein_target = goal.daily_protein_target

        # Calculate date range
        today = datetime.now().date()

        weeks_data = []

        for week_num in range(weeks):
            # Calculate week start (Monday) and end (Sunday)
            days_back = (week_num + 1) * 7
            week_end = today - timedelta(days=days_back)
            week_end = week_end + timedelta(days=(6 - week_end.weekday()))  # Move to Sunday
            week_start = week_end - timedelta(days=6)  # Monday

            # Get all meals in this week
            meals = Meal.query.filter(
                Meal.user_id == user_id,
                Meal.meal_date >= week_start,
                Meal.meal_date <= week_end
            ).all()

            if not meals:
                continue

            # Group by date and calculate daily totals
            daily_totals = defaultdict(lambda: {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0})

            for meal in meals:
                date_key = meal.meal_date.isoformat()
                daily_totals[date_key]['calories'] += meal.calories or 0
                daily_totals[date_key]['protein'] += float(meal.protein or 0)
                daily_totals[date_key]['carbs'] += float(meal.carbs or 0)
                daily_totals[date_key]['fat'] += float(meal.fat or 0)

            if not daily_totals:
                continue

            # Calculate weekly averages
            num_days = len(daily_totals)
            avg_calories = sum(d['calories'] for d in daily_totals.values()) / num_days
            avg_protein = sum(d['protein'] for d in daily_totals.values()) / num_days
            avg_carbs = sum(d['carbs'] for d in daily_totals.values()) / num_days
            avg_fat = sum(d['fat'] for d in daily_totals.values()) / num_days

            # Calculate compliance rate (% of days within ±10% of targets)
            compliant_days = 0
            for day_data in daily_totals.values():
                cal_within = abs(day_data['calories'] - calorie_target) / calorie_target <= 0.10
                pro_within = abs(day_data['protein'] - protein_target) / protein_target <= 0.10
                if cal_within and pro_within:
                    compliant_days += 1

            compliance_rate = (compliant_days / num_days) * 100 if num_days > 0 else 0

            weeks_data.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'avg_calories': round(avg_calories, 1),
                'avg_protein': round(avg_protein, 1),
                'avg_carbs': round(avg_carbs, 1),
                'avg_fat': round(avg_fat, 1),
                'target_calories': calorie_target,
                'target_protein': protein_target,
                'compliance_rate': round(compliance_rate, 1)
            })

        # Sort by week_start ascending (oldest first)
        weeks_data.sort(key=lambda x: x['week_start'])

        return jsonify({
            'success': True,
            'data': weeks_data
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@weight_bp.route('/plateau-check/<string:user_id>', methods=['GET'])
def check_plateau(user_id):
    """
    Detect if weight loss has plateaued
    Returns plateau status and recommendations
    """
    try:
        from collections import defaultdict

        # Get last 4 weeks of weight entries
        four_weeks_ago = datetime.now().date() - timedelta(weeks=4)
        entries = WeightEntry.query.filter(
            WeightEntry.user_id == user_id,
            WeightEntry.date >= four_weeks_ago
        ).order_by(WeightEntry.date.asc()).all()

        if len(entries) < 8:  # Need at least 2 entries per week
            return jsonify({
                'success': False,
                'error': 'Insufficient data. Need at least 8 weight entries over 4 weeks for plateau detection.'
            }), 404

        # Group by week and calculate weekly averages
        weekly_weights = defaultdict(list)

        for entry in entries:
            # Get week number from date
            week_num = (entry.date - four_weeks_ago).days // 7
            weekly_weights[week_num].append(float(entry.weight_kg))

        # Calculate weekly averages
        weekly_avgs = []
        for week in sorted(weekly_weights.keys()):
            if weekly_weights[week]:
                avg = sum(weekly_weights[week]) / len(weekly_weights[week])
                weekly_avgs.append(avg)

        if len(weekly_avgs) < 3:
            return jsonify({
                'success': False,
                'error': 'Need data from at least 3 weeks for plateau detection.'
            }), 404

        # Check for plateau (3+ consecutive weeks with <0.25kg change)
        weeks_stalled = 0
        max_stall = 0

        for i in range(1, len(weekly_avgs)):
            change = abs(weekly_avgs[i] - weekly_avgs[i-1])
            if change < 0.25:
                weeks_stalled += 1
                max_stall = max(max_stall, weeks_stalled)
            else:
                weeks_stalled = 0

        is_plateau = max_stall >= 3

        # Calculate last weight change over stall period
        if is_plateau and max_stall > 0:
            last_weight_change = weekly_avgs[-1] - weekly_avgs[-max_stall-1]
        else:
            last_weight_change = weekly_avgs[-1] - weekly_avgs[0] if len(weekly_avgs) > 1 else 0

        # Generate recommendation
        recommendation = ""
        if is_plateau:
            # Get current phase to tailor recommendation
            goal = WeightGoal.query.filter_by(user_id=user_id).first()
            phase = goal.current_phase if goal else 'fat_loss'

            if max_stall >= 4:
                recommendation = "Your weight has been stable for 4+ weeks. Consider implementing a 2-week diet break (eating at maintenance calories) to reset your metabolism before resuming fat loss."
            elif max_stall == 3:
                recommendation = "Your weight has been stable for 3 weeks. Consider implementing a refeed day (eating at maintenance calories) or adding 30 minutes of cardio 3x per week to break through this plateau."

            if phase == 'diet_break':
                recommendation = "You're in a diet break phase. Weight stability is normal and expected. Continue with your maintenance calories."
            elif phase == 'fat_loss':
                recommendation += " You could also try reducing daily calories by 100-150 kcal."

        return jsonify({
            'success': True,
            'data': {
                'is_plateau': is_plateau,
                'weeks_stalled': max_stall,
                'last_weight_change': round(last_weight_change, 2),
                'recommendation': recommendation
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@weight_bp.route('/meal-timing/<string:user_id>', methods=['GET'])
def get_meal_timing(user_id):
    """
    Analyze meal timing for intermittent fasting compliance
    Query params: days (optional, default 7, accepts 7/14/30)
    """
    try:
        from app.models import Meal
        from collections import defaultdict

        days = int(request.args.get('days', 7))
        if days not in [7, 14, 30]:
            days = 7  # Default to 7 if invalid

        # Calculate date range
        start_date = datetime.now().date() - timedelta(days=days)

        # Get all meals in date range
        meals = Meal.query.filter(
            Meal.user_id == user_id,
            Meal.meal_date >= start_date
        ).order_by(Meal.meal_date.asc()).all()

        if not meals:
            return jsonify({
                'success': True,
                'data': []
            }), 200

        # Group by date
        meals_by_date = defaultdict(list)
        for meal in meals:
            meals_by_date[meal.meal_date.isoformat()].append(meal)

        timing_data = []

        # Analyze each date
        for date_str in sorted(meals_by_date.keys()):
            day_meals = meals_by_date[date_str]

            if not day_meals:
                continue

            # Get meal times (use meal_time if available, fallback to created_at)
            meal_datetimes = []
            for meal in day_meals:
                if meal.meal_time:
                    # Use meal_time (TIME column)
                    meal_dt = datetime.combine(datetime.today(), meal.meal_time)
                else:
                    # Fallback to created_at
                    meal_dt = meal.created_at

                meal_datetimes.append(meal_dt)

            # Sort by time
            meal_datetimes.sort()

            if len(meal_datetimes) < 2:
                # Only 1 meal = 0 hour window (compliant)
                first_time = meal_datetimes[0] if meal_datetimes else None
                if first_time:
                    timing_data.append({
                        'date': date_str,
                        'first_meal_time': first_time.strftime('%H:%M'),
                        'last_meal_time': first_time.strftime('%H:%M'),
                        'eating_window_hours': 0.0,
                        'is_16_8_compliant': True
                    })
                continue

            # Get first and last meal times
            first_meal = meal_datetimes[0]
            last_meal = meal_datetimes[-1]

            # Calculate eating window in hours
            window_delta = last_meal - first_meal
            window_hours = window_delta.total_seconds() / 3600

            # 16:8 compliance = eating window <= 8 hours
            is_compliant = window_hours <= 8.0

            timing_data.append({
                'date': date_str,
                'first_meal_time': first_meal.strftime('%H:%M'),
                'last_meal_time': last_meal.strftime('%H:%M'),
                'eating_window_hours': round(window_hours, 2),
                'is_16_8_compliant': is_compliant
            })

        return jsonify({
            'success': True,
            'data': timing_data
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
