"""
Migration script to update employee_labels table structure:
1. Add label_values column (array type for template values)
2. Make label_value nullable
3. Add unique constraint for template labels (business_id + label_name where emp_id IS NULL)
4. Migrate existing template data to use array structure
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

def migrate_employee_labels():
    """Update employee_labels table structure and migrate data"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Start transaction
            trans = conn.begin()
            
            print("Step 1: Adding label_values column (array type)...")
            conn.execute(text("""
                ALTER TABLE employee_labels 
                ADD COLUMN IF NOT EXISTS label_values TEXT[];
            """))
            print("✓ Added label_values column")
            
            print("\nStep 2: Making label_value nullable...")
            conn.execute(text("""
                ALTER TABLE employee_labels 
                ALTER COLUMN label_value DROP NOT NULL;
            """))
            print("✓ Made label_value nullable")
            
            print("\nStep 3: Migrating template data (emp_id IS NULL) to array format...")
            # Group existing template records by business_id and label_name, aggregate values into array
            result = conn.execute(text("""
                SELECT business_id, label_name, array_agg(DISTINCT label_value) as values
                FROM employee_labels
                WHERE emp_id IS NULL AND label_value IS NOT NULL
                GROUP BY business_id, label_name
                HAVING COUNT(*) > 0;
            """))
            
            templates = result.fetchall()
            print(f"Found {len(templates)} template label(s) to migrate")
            
            # Delete old template records
            if templates:
                conn.execute(text("""
                    DELETE FROM employee_labels 
                    WHERE emp_id IS NULL;
                """))
                print("✓ Deleted old template records")
                
                # Insert new template records with array values
                for business_id, label_name, values in templates:
                    conn.execute(text("""
                        INSERT INTO employee_labels (emp_id, business_id, label_name, label_value, label_values)
                        VALUES (NULL, :business_id, :label_name, NULL, :values)
                    """), {"business_id": business_id, "label_name": label_name, "values": list(values)})
                    print(f"  ✓ Migrated template: {label_name} with {len(values)} value(s) for business {business_id}")
            else:
                print("No template records to migrate")
            
            print("\nStep 4: Adding unique constraint for templates...")
            # Drop existing constraint if it exists
            conn.execute(text("""
                ALTER TABLE employee_labels 
                DROP CONSTRAINT IF EXISTS uq_business_label_template;
            """))
            
            # Add unique constraint: only one template per label_name per business (where emp_id IS NULL)
            conn.execute(text("""
                CREATE UNIQUE INDEX uq_business_label_template 
                ON employee_labels (business_id, label_name) 
                WHERE emp_id IS NULL;
            """))
            print("✓ Added unique constraint for template labels")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            print("\nSummary:")
            print("- Added label_values column for storing arrays")
            print("- Made label_value nullable")
            print(f"- Migrated {len(templates)} template label(s) to array format")
            print("- Added unique constraint for template labels")
            
        except Exception as e:
            trans.rollback()
            print(f"\n✗ Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    migrate_employee_labels()
