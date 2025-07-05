import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def migrate_password_field():
    """Migrate the password_hash field to support longer hashes"""

    # Get database URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False

    # Fix postgres:// to postgresql:// if needed
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    try:
        # Create engine
        engine = create_engine(database_url)

        # Execute migration
        with engine.connect() as conn:
            # Check if the column exists and its current type
            result = conn.execute(text("""
                SELECT column_name, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'user' AND column_name = 'password_hash'
            """))

            column_info = result.fetchone()

            if column_info:
                current_length = column_info[1]
                print(f"Current password_hash field length: {current_length}")

                if current_length < 255:
                    print("🔄 Updating password_hash field to VARCHAR(255)...")

                    # Alter the column
                    conn.execute(text("""
                        ALTER TABLE "user" 
                        ALTER COLUMN password_hash TYPE VARCHAR(255)
                    """))

                    conn.commit()
                    print("✅ Password field migration completed successfully!")
                else:
                    print("✅ Password field already has sufficient length")
            else:
                print("❌ User table or password_hash column not found")
                return False

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("🚀 Starting password field migration...")
    success = migrate_password_field()

    if success:
        print("🎉 Migration completed! You can now register users.")
    else:
        print("💥 Migration failed. Check the errors above.")
