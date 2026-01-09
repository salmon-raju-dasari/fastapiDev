"""
Migration script to add label_type column to custom_labels table
Adds label_type to distinguish between 'employee' and 'product' labels
"""
import psycopg2
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Add label_type column to custom_labels table and update indexes"""
    try:
        # Get database configuration from environment variables
        POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
        POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        POSTGRES_DB = os.getenv("POSTGRES_DB", "supermarket_db")
        
        # Connect to PostgreSQL database
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        
        print("Connected to database successfully")
        
        # Check if label_type column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='custom_labels' AND column_name='label_type'
        """)
        
        if cursor.fetchone():
            print("⚠️  label_type column already exists. Skipping migration.")
            cursor.close()
            conn.close()
            return
        
        # Step 1: Add label_type column with default value
        print("\n1. Adding label_type column...")
        cursor.execute("""
            ALTER TABLE custom_labels 
            ADD COLUMN label_type VARCHAR(50) NOT NULL DEFAULT 'employee'
        """)
        print("✅ Added label_type column with default value 'employee'")
        
        # Step 2: Create index on label_type
        print("\n2. Creating index on label_type...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_custom_labels_label_type 
            ON custom_labels(label_type)
        """)
        print("✅ Created index on label_type")
        
        # Step 3: Drop old unique index
        print("\n3. Dropping old unique index...")
        cursor.execute("""
            DROP INDEX IF EXISTS idx_business_label_name
        """)
        print("✅ Dropped old index idx_business_label_name")
        
        # Step 4: Create new unique index with label_type
        print("\n4. Creating new unique index with label_type...")
        cursor.execute("""
            CREATE UNIQUE INDEX idx_business_label_name_type 
            ON custom_labels(business_id, label_name, label_type)
        """)
        print("✅ Created new unique index idx_business_label_name_type")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show current table structure
        print("\n📊 Current custom_labels table structure:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name='custom_labels'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Custom Labels Migration: Add label_type Column")
    print("=" * 60)
    migrate_database()
