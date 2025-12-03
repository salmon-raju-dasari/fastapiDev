# Run FastAPI with HTTPS
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ssl-keyfile=key.pem --ssl-certfile=cert.pem
