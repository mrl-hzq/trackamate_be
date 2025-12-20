"""
Database migration script to add weight management tables
Run this script to create the new tables for weight tracking, goals, and nutrition reviews.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

app = create_app()


def upgrade():
    """Create new tables for weight management features"""
    with app.app_context():
        print("Creating weight management tables...")

        # Weight entries table
        print("Creating weight_entries table...")
        db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS weight_entries (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            weight_kg DECIMAL(5,2) NOT NULL,
            date DATE NOT NULL,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            INDEX idx_user_date (user_id, date)
        )
        """))

        # Weight goals table
        print("Creating weight_goals table...")
        db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS weight_goals (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL UNIQUE,
            starting_weight DECIMAL(5,2) NOT NULL,
            current_weight DECIMAL(5,2) NOT NULL,
            goal_weight DECIMAL(5,2) NOT NULL,
            height_cm INTEGER NOT NULL,
            target_date DATE NOT NULL,
            current_phase ENUM('priming', 'fat_loss', 'diet_break', 'final_push') DEFAULT 'priming',
            phase_start_date DATE NOT NULL,
            daily_calorie_target INTEGER NOT NULL,
            daily_protein_target INTEGER NOT NULL,
            daily_carbs_target INTEGER,
            daily_fat_target INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
        )
        """))

        # Nutrition reviews table
        print("Creating nutrition_reviews table...")
        db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS nutrition_reviews (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            review_date DATE NOT NULL,
            total_calories INTEGER NOT NULL,
            total_protein DECIMAL(5,2) NOT NULL,
            total_carbs DECIMAL(5,2) NOT NULL,
            total_fat DECIMAL(5,2) NOT NULL,
            calorie_target INTEGER NOT NULL,
            protein_target INTEGER NOT NULL,
            adherence_score INTEGER,
            ai_feedback TEXT NOT NULL,
            grade VARCHAR(2),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_date (user_id, review_date),
            INDEX idx_user_date (user_id, review_date)
        )
        """))

        db.session.commit()
        print("✅ All tables created successfully!")


def downgrade():
    """Drop weight management tables"""
    with app.app_context():
        print("Dropping weight management tables...")

        db.session.execute(text("DROP TABLE IF EXISTS nutrition_reviews"))
        db.session.execute(text("DROP TABLE IF EXISTS weight_goals"))
        db.session.execute(text("DROP TABLE IF EXISTS weight_entries"))

        db.session.commit()
        print("✅ All tables dropped successfully!")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        print("⚠️  Running DOWNGRADE - This will delete all weight management data!")
        confirm = input("Are you sure? Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            downgrade()
        else:
            print("❌ Downgrade cancelled")
    else:
        print("Running UPGRADE - Creating new tables...")
        upgrade()
