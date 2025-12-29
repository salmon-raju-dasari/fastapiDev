"""
Migration script to add foreign key constraint on employees.store_id
This ensures that when a store is deleted, employee.store_id is automatically set to NULL
"""
import sys
from sqlalchemy import create_engine, text
from app.database import SQLALCHEMY_DATABASE_URL

def add_store_fk_constraint():
    """Add foreign key constraint to employees.store_id with ON DELETE SET NULL"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()
            
            try:
                print("Checking if foreign key constraint already exists...")
                
                # Check if constraint exists (PostgreSQL specific)
                check_constraint = text("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'employees' 
                    AND constraint_type = 'FOREIGN KEY'
                    AND constraint_name LIKE '%store%'
                """)
                
                result = connection.execute(check_constraint)
                existing_constraints = result.fetchall()
                
                if existing_constraints:
                    print(f"Found existing store foreign key constraint(s): {existing_constraints}")
                    print("Dropping existing constraint(s)...")
                    
                    for constraint in existing_constraints:
                        drop_constraint = text(f"""
                            ALTER TABLE employees 
                            DROP CONSTRAINT {constraint[0]}
                        """)
                        connection.execute(drop_constraint)
                        print(f"Dropped constraint: {constraint[0]}")
                
                print("Checking for orphaned store_id references...")
                
                # Find employees with store_id that doesn't exist in stores table
                check_orphans = text("""
                    SELECT COUNT(*) 
                    FROM employees 
                    WHERE store_id IS NOT NULL 
                    AND store_id NOT IN (SELECT id FROM stores)
                """)
                
                result = connection.execute(check_orphans)
                orphan_count = result.scalar()
                
                if orphan_count > 0:
                    print(f"Found {orphan_count} employees with invalid store_id references")
                    print("Cleaning up orphaned store_id values (setting to NULL)...")
                    
                    # Set orphaned store_id values to NULL
                    cleanup_orphans = text("""
                        UPDATE employees 
                        SET store_id = NULL 
                        WHERE store_id IS NOT NULL 
                        AND store_id NOT IN (SELECT id FROM stores)
                    """)
                    
                    connection.execute(cleanup_orphans)
                    print(f"✓ Cleaned up {orphan_count} orphaned store_id references")
                else:
                    print("✓ No orphaned store_id references found")
                
                print("Adding new foreign key constraint with ON DELETE SET NULL...")
                
                # Add the new foreign key constraint
                add_constraint = text("""
                    ALTER TABLE employees 
                    ADD CONSTRAINT fk_employees_store_id 
                    FOREIGN KEY (store_id) 
                    REFERENCES stores(id) 
                    ON DELETE SET NULL
                """)
                
                connection.execute(add_constraint)
                trans.commit()
                
                print("✓ Successfully added foreign key constraint!")
                print("✓ Now when a store is deleted, employee.store_id will automatically be set to NULL")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"✗ Error during migration: {str(e)}")
                return False
                
    except Exception as e:
        print(f"✗ Failed to connect to database: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Store Foreign Key Constraint Migration")
    print("=" * 60)
    print()
    
    success = add_store_fk_constraint()
    
    print()
    if success:
        print("Migration completed successfully! ✓")
        sys.exit(0)
    else:
        print("Migration failed! ✗")
        sys.exit(1)
