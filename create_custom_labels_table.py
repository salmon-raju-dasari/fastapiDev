"""
Migration script to create custom_labels table.
This table stores custom label definitions with their predefined values for each business.
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

def create_custom_labels_table():
    """Create custom_labels table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Start transaction
            trans = conn.begin()
            
            print("Creating custom_labels table...")
            
            # Create custom_labels table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS custom_labels (
                    id SERIAL PRIMARY KEY,
                    label_name VARCHAR(100) NOT NULL,
                    label_values TEXT[] NOT NULL,
                    business_id INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """))
            print("✓ Created custom_labels table")
            
            print("\nCreating indexes...")
            
            # Create index on business_id
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_custom_labels_business_id 
                ON custom_labels (business_id);
            """))
            print("✓ Created index on business_id")
            
            # Create index on label_name
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_custom_labels_label_name 
                ON custom_labels (label_name);
            """))
            print("✓ Created index on label_name")
            
            # Create unique index on business_id + label_name
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_business_label_name 
                ON custom_labels (business_id, label_name);
            """))
            print("✓ Created unique index on business_id + label_name")
            
            # Create function to update updated_at timestamp
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_custom_labels_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """))
            print("✓ Created update_updated_at function")
            
            # Create trigger to automatically update updated_at
            conn.execute(text("""
                DROP TRIGGER IF EXISTS trigger_update_custom_labels_updated_at ON custom_labels;
                CREATE TRIGGER trigger_update_custom_labels_updated_at
                    BEFORE UPDATE ON custom_labels
                    FOR EACH ROW
                    EXECUTE FUNCTION update_custom_labels_updated_at();
            """))
            print("✓ Created trigger for updated_at")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            print("\nTable structure:")
            print("- id: SERIAL PRIMARY KEY")
            print("- label_name: VARCHAR(100) NOT NULL")
            print("- label_values: TEXT[] NOT NULL")
            print("- business_id: INTEGER NOT NULL")
            print("- created_at: TIMESTAMP WITH TIME ZONE")
            print("- updated_at: TIMESTAMP WITH TIME ZONE")
            print("\nIndexes:")
            print("- Unique index on (business_id, label_name)")
            print("- Index on business_id")
            print("- Index on label_name")
            
        except Exception as e:
            trans.rollback()
            print(f"\n✗ Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    create_custom_labels_table()
