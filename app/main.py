from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
from app.routers import jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Bulk Certificate Generator API",
    description="Backend API for asynchronous bulk certificate PDF generation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(jobs.router)


@app.get("/")
def root():
    return {
        "message": "Bulk Certificate Generator API is running",
        "docs_url": "/docs",
    }
