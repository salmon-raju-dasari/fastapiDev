"""
Migration script to convert logo storage from file path to database binary storage
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get database configuration from environment
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "supermarket_db")

# Create PostgreSQL database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

print(f"Connecting to database: {POSTGRES_DB} at {POSTGRES_HOST}:{POSTGRES_PORT}")

# Create engine
engine = create_engine(DATABASE_URL)

def migrate_logo_storage():
    """Migrate from logo_path to logo_data columns"""
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check if business table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'business'
                    );
                """))
                
                if not result.scalar():
                    print("Business table does not exist. Creating new table with logo_data columns...")
                    trans.commit()
                    return
                
                # Check if logo_data column already exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'business' AND column_name = 'logo_data';
                """))
                
                if result.fetchone():
                    print("logo_data column already exists. Migration already completed.")
                    trans.commit()
                    return
                
                print("Adding logo_data and logo_content_type columns...")
                
                # Add new columns
                conn.execute(text("""
                    ALTER TABLE business 
                    ADD COLUMN IF NOT EXISTS logo_data BYTEA,
                    ADD COLUMN IF NOT EXISTS logo_content_type VARCHAR(50);
                """))
                
                print("New columns added successfully!")
                
                # Drop old logo_path column if it exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'business' AND column_name = 'logo_path';
                """))
                
                if result.fetchone():
                    print("Dropping old logo_path column...")
                    conn.execute(text("""
                        ALTER TABLE business DROP COLUMN IF EXISTS logo_path;
                    """))
                    print("Old logo_path column dropped.")
                
                # Commit transaction
                trans.commit()
                print("\n✅ Migration completed successfully!")
                print("Logo storage has been migrated to database binary storage.")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {str(e)}")
                raise
                
    except Exception as e:
        print(f"\n❌ Connection error: {str(e)}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("Logo Storage Migration Script")
    print("Converting from file path to database binary storage")
    print("=" * 60)
    print()
    
    migrate_logo_storage()
