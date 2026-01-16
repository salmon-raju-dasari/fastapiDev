"""
Migration script to change employees.avatar_blob to avatar_url and thumbnail_url
This will drop the avatar_blob column and add avatar_url and thumbnail_url columns
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Get database URL
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

def migrate_employee_avatar():
    """Migrate employee avatar from blob to URL"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Starting migration: employees.avatar_blob -> avatar_url/thumbnail_url")
        
        # Check if avatar_blob column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'employees' AND column_name = 'avatar_blob'
        """))
        has_blob = result.fetchone() is not None
        
        # Check if avatar_url column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'employees' AND column_name = 'avatar_url'
        """))
        has_url = result.fetchone() is not None
        
        if has_blob and not has_url:
            print("✓ Found avatar_blob column, adding new URL columns...")
            
            # Add avatar_url column
            conn.execute(text("""
                ALTER TABLE employees 
                ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)
            """))
            print("✓ Added avatar_url column")
            
            # Add thumbnail_url column
            conn.execute(text("""
                ALTER TABLE employees 
                ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500)
            """))
            print("✓ Added thumbnail_url column")
            
            # Drop avatar_blob column
            conn.execute(text("""
                ALTER TABLE employees 
                DROP COLUMN IF EXISTS avatar_blob
            """))
            print("✓ Dropped avatar_blob column")
            
            conn.commit()
            print("✅ Migration completed successfully!")
            print("Note: Existing avatar blobs have been removed. Users will need to re-upload their avatars.")
            
        elif not has_blob and has_url:
            print("✓ Migration already completed - avatar_url columns exist")
            
        elif has_blob and has_url:
            print("⚠️  Both avatar_blob and avatar_url exist. Dropping avatar_blob...")
            conn.execute(text("""
                ALTER TABLE employees 
                DROP COLUMN IF EXISTS avatar_blob
            """))
            conn.commit()
            print("✓ Dropped avatar_blob column")
            
        else:
            print("⚠️  Neither avatar_blob nor avatar_url found. Adding URL columns...")
            conn.execute(text("""
                ALTER TABLE employees 
                ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500),
                ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500)
            """))
            conn.commit()
            print("✓ Added avatar URL columns")
        
        print("\n✅ Database schema updated successfully!")

if __name__ == "__main__":
    try:
        migrate_employee_avatar()
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)
