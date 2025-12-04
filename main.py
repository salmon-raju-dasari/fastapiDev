from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.database import Base, engine

# import models so they are registered on the metadata
# import app.models.user  # noqa: F401  # Commented out - using employees table now
import app.models.employees  # noqa: F401
import app.models.products  # noqa: F401
import app.models.categories  # noqa: F401
import app.models.business  # noqa: F401
import app.models.stores  # noqa: F401
import app.models.payment  # noqa: F401

# from app.routes.user import router as users_router  # Commented out - using employees routes now
from app.routes.employees import router as employees_router
from app.routes.products import router as products_router
from app.routes.categories import router as categories_router
from app.routes.business import router as business_router
from app.routes.stores import router as stores_router
from app.routes.payment import router as payment_router

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create tables (after models are imported)
Base.metadata.create_all(bind=engine)

# app.include_router(users_router, prefix="/api/users", tags=["users"])  # Commented out - using employees now
app.include_router(employees_router, prefix="/api/employees", tags=["employees"])
app.include_router(products_router, prefix="/api/products", tags=["products"])
app.include_router(categories_router, prefix="/api/categories", tags=["categories"])
app.include_router(business_router, prefix="/api/business", tags=["business"])
app.include_router(stores_router, prefix="/api/stores", tags=["stores"])
app.include_router(payment_router, prefix="/api/payment", tags=["payment"])

@app.get("/")
def read_root():
    return {"status": "ok"}