"""
Database migration script to replace reminders table with notes table.
This script will:
1. Drop the existing reminders table
2. Create the new notes table with all required columns

Run this script with: python migrate_notes.py
"""

from app import create_app, db
from app.models import Note, User
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_migration():
    app = create_app()

    with app.app_context():
        try:
            print("Starting database migration...")
            print("=" * 50)

            # Check if reminders table exists
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()

            if 'reminders' in existing_tables:
                print("✓ Found 'reminders' table. Dropping it...")
                db.session.execute(db.text("DROP TABLE IF EXISTS reminders"))
                db.session.commit()
                print("✓ Successfully dropped 'reminders' table")
            else:
                print("ℹ 'reminders' table does not exist (skipping drop)")

            # Create notes table if it doesn't exist
            if 'notes' not in existing_tables:
                print("✓ Creating 'notes' table...")
                Note.__table__.create(db.engine)
                db.session.commit()
                print("✓ Successfully created 'notes' table")
            else:
                print("ℹ 'notes' table already exists (skipping creation)")

            print("=" * 50)
            print("✓ Migration completed successfully!")
            print("\nNew 'notes' table structure:")
            print("  - id (UUID primary key)")
            print("  - user_id (Foreign key to Users)")
            print("  - title (String 200, required)")
            print("  - content (Text, required)")
            print("  - category (String 50)")
            print("  - note_type (Enum: 'one-time', 'recurring')")
            print("  - recurrence_interval_days (Integer)")
            print("  - last_reset_date (Date)")
            print("  - next_due_date (Date)")
            print("  - is_done (Boolean)")
            print("  - done_date (DateTime)")
            print("  - burn_id (Foreign key to burns)")
            print("  - invest_id (Foreign key to invests)")
            print("  - commitment_id (Foreign key to commitments)")
            print("  - created_at (DateTime)")
            print("  - updated_at (DateTime)")

            return True

        except Exception as e:
            print(f"\n✗ Migration failed: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
