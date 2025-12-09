"""
Migration script to allow emp_id to be NULL in employee_labels table.
This enables storing template/predefined label values that aren't associated with specific employees.
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL database configuration (same as app/database.py)
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "supermarket_db")

# Create PostgreSQL database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

def alter_employee_labels_table():
    """Alter employee_labels table to make emp_id nullable"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Start transaction
            trans = conn.begin()
            
            print("Altering employee_labels table to allow NULL emp_id...")
            
            # Make emp_id nullable
            conn.execute(text("""
                ALTER TABLE employee_labels 
                ALTER COLUMN emp_id DROP NOT NULL;
            """))
            
            print("✓ Successfully altered emp_id column to nullable")
            
            # Commit transaction
            trans.commit()
            print("✓ Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"✗ Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    alter_employee_labels_table()
