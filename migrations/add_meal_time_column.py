"""
Migration: Add meal_time column to meals table
Date: 2025-12-03
Description: Adds a TIME column to store the actual meal time separately from created_at timestamp
"""

import sys
import os

# Add parent directory to path to import app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add meal_time column to meals table"""
    app = create_app()

    with app.app_context():
        try:
            # Add meal_time column
            print("Adding meal_time column to meals table...")
            db.session.execute(text(
                "ALTER TABLE meals ADD COLUMN meal_time TIME NULL AFTER meal_date"
            ))
            db.session.commit()
            print("✓ Successfully added meal_time column")

            # Optional: Migrate existing data - set meal_time from created_at
            print("\nMigrating existing data...")
            db.session.execute(text(
                "UPDATE meals SET meal_time = TIME(created_at) WHERE meal_time IS NULL"
            ))
            db.session.commit()
            print("✓ Successfully migrated existing meal times from created_at")

            print("\n✓ Migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {str(e)}")
            raise

def downgrade():
    """Remove meal_time column from meals table"""
    app = create_app()

    with app.app_context():
        try:
            print("Removing meal_time column from meals table...")
            db.session.execute(text(
                "ALTER TABLE meals DROP COLUMN meal_time"
            ))
            db.session.commit()
            print("✓ Successfully removed meal_time column")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Rollback failed: {str(e)}")
            raise

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python migrations/add_meal_time_column.py [upgrade|downgrade]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'upgrade':
        upgrade()
    elif command == 'downgrade':
        downgrade()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python migrations/add_meal_time_column.py [upgrade|downgrade]")
        sys.exit(1)
