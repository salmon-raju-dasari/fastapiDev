from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine

# import models so they are registered on the metadata
import app.models.user  # noqa: F401
import app.models.products  # noqa: F401

from app.routes.user import router as users_router
from app.routes.products import router as products_router
from app.routes.barcode import router as barcode_router

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://192.168.1.2:5173", 
        "https://192.168.1.2:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create tables (after models are imported)
Base.metadata.create_all(bind=engine)

app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(products_router, prefix="/products", tags=["products"])
app.include_router(barcode_router, prefix="/api", tags=["barcode"])

@app.get("/")
def read_root():
    return {"status": "ok"}