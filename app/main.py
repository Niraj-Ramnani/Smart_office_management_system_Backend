from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import load_azure_openid_config
from app.core.config import settings
from app.routes.v1 import (
    auth_router,
    building_router,
    employee_router,
    floor_router,
    team_router,
    user_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_azure_openid_config()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": settings.AZURE_CLIENT_ID,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(building_router, prefix="/api/v1")
app.include_router(floor_router, prefix="/api/v1")
app.include_router(team_router, prefix="/api/v1")
app.include_router(employee_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Smart Office Management System API"}


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}