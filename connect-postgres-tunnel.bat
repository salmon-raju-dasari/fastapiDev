@echo off
echo Creating SSH tunnel to PostgreSQL on VM...
echo.
echo Once connected, use these pgAdmin settings:
echo   Host: localhost (or 127.0.0.1)
echo   Port: 5433
echo   Database: pos_inventory
echo   Username: pos_inventory
echo   Password: 9491316460Aa!
echo.
echo Press Ctrl+C to close the tunnel
echo.

gcloud compute ssh pos-app --zone=us-central1-a -- -NL 5433:localhost:5432
