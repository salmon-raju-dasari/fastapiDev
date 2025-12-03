# PostgreSQL Setup Instructions

## Prerequisites
1. Install PostgreSQL on Windows:
   - Download from: https://www.postgresql.org/download/windows/
   - Or use chocolatey: `choco install postgresql`

## Database Setup

### Option 1: Using psql command line
```bash
# Login to PostgreSQL (default user is postgres)
psql -U postgres

# Create the database
CREATE DATABASE supermarket_db;

# Verify database created
\l

# Exit psql
\q
```

### Option 2: Using pgAdmin (GUI)
1. Open pgAdmin
2. Right-click on "Databases"
3. Select "Create" -> "Database"
4. Enter database name: `supermarket_db`
5. Click Save

## Environment Configuration

Update `.env` file in fastapiDev directory with your PostgreSQL credentials:

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=supermarket_db
```

## Run Migrations

After setting up PostgreSQL, run the FastAPI server to create tables:

```bash
cd fastapiDev
uvicorn main:app --reload
```

The tables will be automatically created on first run.

## Verify Setup

1. Check that tables were created:
```sql
psql -U postgres -d supermarket_db

\dt  -- List all tables

-- You should see: employees, products, categories tables
```

2. Test employee creation with emp_id starting from 1000:
```sql
SELECT * FROM employees;
```

## Troubleshooting

### Connection Error
- Verify PostgreSQL is running: `pg_ctl status`
- Check credentials in .env file
- Ensure database exists: `psql -U postgres -l`

### Permission Issues
- Grant permissions: `GRANT ALL PRIVILEGES ON DATABASE supermarket_db TO postgres;`
