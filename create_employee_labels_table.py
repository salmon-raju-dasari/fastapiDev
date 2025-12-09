import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Construct DATABASE_URL from environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "pos_system")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

def create_employee_labels_table():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            print("\n" + "=" * 60)
            print("CREATING EMPLOYEE_LABELS TABLE")
            print("=" * 60)
            
            # Create employee_labels table
            print("\n1. Creating employee_labels table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employee_labels (
                    id SERIAL PRIMARY KEY,
                    emp_id INTEGER NOT NULL REFERENCES employees(emp_id) ON DELETE CASCADE,
                    business_id INTEGER NOT NULL,
                    label_name VARCHAR(100) NOT NULL,
                    label_value VARCHAR(500) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("   ✓ employee_labels table created")
            
            # Create indexes
            print("\n2. Creating indexes...")
            
            print("   - Creating index on emp_id...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employee_labels_emp_id 
                ON employee_labels(emp_id);
            """))
            
            print("   - Creating index on business_id...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employee_labels_business_id 
                ON employee_labels(business_id);
            """))
            
            print("   - Creating index on label_name...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employee_labels_label_name 
                ON employee_labels(label_name);
            """))
            
            print("   - Creating composite index on (emp_id, business_id, label_name)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_emp_business_label 
                ON employee_labels(emp_id, business_id, label_name);
            """))
            
            print("   - Creating composite index on (business_id, label_name)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_business_label 
                ON employee_labels(business_id, label_name);
            """))
            
            print("   ✓ All indexes created")
            
            # Migrate existing custom_fields data from employees table
            print("\n3. Migrating existing custom_fields data...")
            
            # Get all employees with custom_fields
            result = conn.execute(text("""
                SELECT emp_id, business_id, custom_fields 
                FROM employees 
                WHERE custom_fields IS NOT NULL 
                AND custom_fields::text != '[]';
            """))
            
            employees_with_labels = result.fetchall()
            migrated_count = 0
            
            if employees_with_labels:
                print(f"   Found {len(employees_with_labels)} employees with custom fields")
                
                for emp_id, business_id, custom_fields in employees_with_labels:
                    if custom_fields:
                        # custom_fields is a list of dicts like [{"Blood Group": "A+"}, {"Department": "Sales"}]
                        for field_obj in custom_fields:
                            for label_name, label_value in field_obj.items():
                                conn.execute(text("""
                                    INSERT INTO employee_labels (emp_id, business_id, label_name, label_value)
                                    VALUES (:emp_id, :business_id, :label_name, :label_value)
                                """), {
                                    "emp_id": emp_id,
                                    "business_id": business_id,
                                    "label_name": label_name,
                                    "label_value": label_value
                                })
                                migrated_count += 1
                
                print(f"   ✓ Migrated {migrated_count} custom labels from {len(employees_with_labels)} employees")
            else:
                print("   No custom fields to migrate")
            
            # Verify migration
            print("\n4. Verifying migration...")
            result = conn.execute(text("""
                SELECT COUNT(*) FROM employee_labels;
            """))
            total_labels = result.fetchone()[0]
            print(f"   ✓ Total labels in new table: {total_labels}")
            
            trans.commit()
            print("\n" + "=" * 60)
            print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("\nResults:")
            print(f"  - employee_labels table created")
            print(f"  - {len(employees_with_labels)} employees migrated")
            print(f"  - {migrated_count} custom labels migrated")
            print(f"  - 5 indexes created for performance")
            print("\nNext steps:")
            print("  1. Update backend routes to use employee_labels table")
            print("  2. Test the new implementation")
            print("  3. Optionally drop custom_fields column from employees table")
            
        except Exception as e:
            trans.rollback()
            print(f"\n✗ Error during migration: {e}")
            raise

if __name__ == "__main__":
    create_employee_labels_table()
