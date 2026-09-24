from fastapi import APIRouter

from app.routes.v1.auth_routes import router as auth_router
from app.routes.v1.building_routes import router as building_router
from app.routes.v1.employee_routes import router as employee_router
from app.routes.v1.floor_routes import router as floor_router
from app.routes.v1.team_routes import router as team_router
from app.routes.v1.user_routes import router as user_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(building_router)
api_v1_router.include_router(floor_router)
api_v1_router.include_router(team_router)
api_v1_router.include_router(employee_router)
api_v1_router.include_router(user_router)

__all__ = [
    "api_v1_router",
    "auth_router",
    "building_router",
    "floor_router",
    "team_router",
    "employee_router",
    "user_router",
]
