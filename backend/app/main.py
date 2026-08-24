from fastapi import FastAPI

from app.routers.health import router as health_router


app = FastAPI(
    title="Novatech Backend",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(health_router)
