"""
Migration script to alter productid column to be nullable
This allows auto-generation of productid after insertion
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL database configuration
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "supermarket")

# Create PostgreSQL database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB]):
    raise ValueError("Database configuration not found in environment variables")

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def alter_productid_nullable():
    """Alter productid column to allow NULL values"""
    db = SessionLocal()
    try:
        print("Altering productid column to be nullable...")
        
        # Alter column to allow NULL
        alter_query = text("""
            ALTER TABLE products 
            ALTER COLUMN productid DROP NOT NULL;
        """)
        
        db.execute(alter_query)
        db.commit()
        
        print("✅ Successfully altered productid column to allow NULL values!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("ALTER PRODUCTID COLUMN TO NULLABLE")
    print("=" * 60)
    print("This will allow productid to be NULL (for auto-generation)")
    print()
    
    confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
    if confirm == 'yes':
        alter_productid_nullable()
        print("\n✅ Migration complete!")
    else:
        print("Migration cancelled.")
