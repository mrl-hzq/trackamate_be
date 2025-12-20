"""
Utility functions for weight management and nutrition calculations
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models import WeightEntry


def calculate_phases(starting_weight, goal_weight, target_date, start_date=None):
    """
    Calculate all phases with dates and targets based on weight loss plan.

    Args:
        starting_weight: Current weight in kg
        goal_weight: Target weight in kg
        target_date: Target completion date
        start_date: Start date (default: today)

    Returns:
        List of phase dictionaries with dates, calories, protein targets
    """
    if start_date is None:
        start_date = datetime.now().date()

    phases = []
    current_date = start_date

    # Phase 0: Metabolic Priming (1 month)
    phases.append({
        'name': 'Month 1 - Metabolic Priming',
        'phase': 'priming',
        'start_date': current_date.isoformat(),
        'end_date': (current_date + relativedelta(months=1)).isoformat(),
        'duration_days': 30,
        'daily_calorie_target': 2350,
        'daily_protein_target': int(starting_weight * 1.65),
        'daily_carbs_target': 250,
        'daily_fat_target': 70,
        'expected_loss_kg': '0.5-1',
        'description': 'Restore metabolic function before dieting'
    })
    current_date += relativedelta(months=1)

    # Phase 1: Fat Loss (9 months)
    phases.append({
        'name': 'Phase 1 - Fat Loss',
        'phase': 'fat_loss',
        'start_date': current_date.isoformat(),
        'end_date': (current_date + relativedelta(months=9)).isoformat(),
        'duration_days': 270,
        'daily_calorie_target': 2050,
        'daily_protein_target': int(starting_weight * 1.75),
        'daily_carbs_target': 200,
        'daily_fat_target': 65,
        'expected_loss_kg': '18-20',
        'description': 'Sustainable fat loss with muscle preservation'
    })
    current_date += relativedelta(months=9)

    # Diet Break (2 weeks)
    phases.append({
        'name': 'Diet Break',
        'phase': 'diet_break',
        'start_date': current_date.isoformat(),
        'end_date': (current_date + timedelta(days=14)).isoformat(),
        'duration_days': 14,
        'daily_calorie_target': 2400,
        'daily_protein_target': int(starting_weight * 1.65),
        'daily_carbs_target': 300,
        'daily_fat_target': 70,
        'expected_loss_kg': '0',
        'description': 'Restore hormones and take psychological break'
    })
    current_date += timedelta(days=14)

    # Phase 3: Final Push (remaining time to target_date)
    days_remaining = (target_date - current_date).days
    phases.append({
        'name': 'Phase 3 - Final Push',
        'phase': 'final_push',
        'start_date': current_date.isoformat(),
        'end_date': target_date.isoformat(),
        'duration_days': days_remaining,
        'daily_calorie_target': 1950,
        'daily_protein_target': int(starting_weight * 1.80),
        'daily_carbs_target': 180,
        'daily_fat_target': 60,
        'expected_loss_kg': '6-8',
        'description': 'Final push to goal weight'
    })

    return phases


def get_current_phase_info(weight_goal):
    """
    Get detailed info about user's current phase.

    Args:
        weight_goal: WeightGoal model instance

    Returns:
        dict with phase information
    """
    today = datetime.now().date()
    phase_start = weight_goal.phase_start_date
    days_in_phase = (today - phase_start).days

    # Determine phase duration
    phase_durations = {
        'priming': 30,
        'fat_loss': 270,
        'diet_break': 14,
        'final_push': (weight_goal.target_date - today).days
    }

    total_days = phase_durations.get(weight_goal.current_phase, 30)
    days_remaining = max(0, total_days - days_in_phase)

    phase_names = {
        'priming': 'Month 1 - Metabolic Priming',
        'fat_loss': 'Phase 1 - Fat Loss',
        'diet_break': 'Diet Break',
        'final_push': 'Phase 3 - Final Push'
    }

    phase_descriptions = {
        'priming': 'Restoring metabolism, building sustainable habits',
        'fat_loss': 'Active fat loss with muscle preservation',
        'diet_break': 'Maintenance phase to restore hormones',
        'final_push': 'Final phase to reach goal weight'
    }

    expected_changes = {
        'priming': '-0.5 to -1kg this month',
        'fat_loss': '-2 to -3kg per month',
        'diet_break': 'Maintain current weight',
        'final_push': '-1.5 to -2kg per month'
    }

    return {
        'phase': weight_goal.current_phase,
        'phase_name': phase_names[weight_goal.current_phase],
        'phase_description': phase_descriptions[weight_goal.current_phase],
        'day_in_phase': days_in_phase,
        'total_days': total_days,
        'days_remaining': days_remaining,
        'expected_change': expected_changes[weight_goal.current_phase]
    }


def calculate_adherence_score(totals, targets):
    """
    Calculate overall adherence score (0-100) based on hitting targets.

    Args:
        totals: dict with calories, protein, carbs, fat
        targets: dict with calorie and protein targets

    Returns:
        int score from 0-100
    """
    scores = []

    # Calorie adherence (90-110% of target = 100 points)
    cal_percentage = (totals['calories'] / targets['calories']) * 100
    if 90 <= cal_percentage <= 110:
        cal_score = 100
    elif 80 <= cal_percentage < 90 or 110 < cal_percentage <= 120:
        cal_score = 80
    else:
        cal_score = max(0, 100 - abs(100 - cal_percentage))
    scores.append(cal_score * 0.4)  # 40% weight

    # Protein adherence (>95% of target = 100 points)
    protein_percentage = (totals['protein'] / targets['protein']) * 100
    if protein_percentage >= 95:
        protein_score = 100
    elif protein_percentage >= 80:
        protein_score = 80
    else:
        protein_score = protein_percentage
    scores.append(protein_score * 0.4)  # 40% weight

    # Macro balance (20% weight)
    macro_score = 100  # Default, can add more complex logic
    scores.append(macro_score * 0.2)

    return int(sum(scores))


def calculate_grade(adherence_score):
    """Convert adherence score to letter grade."""
    if adherence_score >= 90:
        return 'A'
    elif adherence_score >= 80:
        return 'B'
    elif adherence_score >= 70:
        return 'C'
    elif adherence_score >= 60:
        return 'D'
    else:
        return 'F'


def calculate_bmr_tdee(weight_kg, height_cm, age, sex='male', activity_level='sedentary'):
    """
    Calculate BMR using Mifflin-St Jeor equation and TDEE.

    Args:
        weight_kg: Weight in kg
        height_cm: Height in cm
        age: Age in years
        sex: 'male' or 'female'
        activity_level: sedentary, light, moderate, active, very_active

    Returns:
        dict with bmr and tdee
    """
    if sex == 'male':
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }

    tdee = bmr * activity_multipliers.get(activity_level, 1.2)

    return {
        'bmr': int(bmr),
        'tdee': int(tdee)
    }


def check_for_plateau(user_id, weeks_threshold=2):
    """
    Check if user has been at same weight for specified weeks.

    Args:
        user_id: User ID
        weeks_threshold: Number of weeks to check for plateau

    Returns:
        dict with plateau status and recommendations
    """
    # Get weight entries for last N weeks
    cutoff_date = datetime.now().date() - timedelta(weeks=weeks_threshold)

    entries = WeightEntry.query.filter(
        WeightEntry.user_id == user_id,
        WeightEntry.date >= cutoff_date
    ).order_by(WeightEntry.date.asc()).all()

    if len(entries) < 2:
        return {
            'is_plateau': False,
            'message': 'Not enough data to determine plateau',
            'weeks_at_same_weight': 0
        }

    first_weight = float(entries[0].weight_kg)
    last_weight = float(entries[-1].weight_kg)
    weight_change = abs(last_weight - first_weight)

    # Plateau if less than 0.5kg change in the period
    is_plateau = weight_change < 0.5

    if is_plateau:
        weeks = len(entries) // 7 if len(entries) >= 7 else len(entries) / 7

        # Get recommendations based on duration
        if weeks >= 4:
            action = 'diet_break'
            recommendations = [
                "Take a 1-week diet break at maintenance calories (2,400-2,500)",
                "Increase daily steps by 2,000",
                "Focus on strength gains in the gym",
                "Check body measurements - you may still be losing fat",
                "Consider if you're at 100kg barrier (expected per your history)"
            ]
        elif weeks >= 3:
            action = 'activity_increase'
            recommendations = [
                "Increase NEAT (add 2,000 steps daily)",
                "Add one more cardio session this week",
                "Check food tracking accuracy",
                "Take progress photos and measurements",
                "Be patient - plateaus are normal"
            ]
        else:
            action = 'monitor'
            recommendations = [
                "Continue current plan",
                "Weight fluctuates normally",
                "Focus on non-scale victories",
                "Check again next week if no change"
            ]

        return {
            'is_plateau': True,
            'weeks_at_same_weight': int(weeks),
            'current_weight': last_weight,
            'message': f"You've been at {last_weight}kg for {int(weeks)} weeks.",
            'action_needed': action,
            'recommendations': recommendations,
            'reassurance': "Plateaus are expected and manageable. You're not failing - your body is adapting."
        }
    else:
        return {
            'is_plateau': False,
            'weeks_at_same_weight': 0,
            'message': 'Weight is trending down normally. Keep going!',
            'action_needed': None
        }
